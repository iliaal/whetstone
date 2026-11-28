import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[2] / "plugins" / "whetstone" / "skills" / "ia-test-audit" / "scripts"


class DetectorCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True, capture_output=True)

    def write(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return path

    def run_detector(self, script, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / script), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_bare_javascript_throws_are_candidates(self):
        self.write(
            "test.js",
            'test("sync", () => { expect(() => run()).toThrow(); });\n'
            'test("spaced", () => { expect(() => run()).toThrow( ); });\n'
            'test("async", async () => { await expect(run()).rejects.toThrow(); });\n',
        )
        result = self.run_detector("weak_negatives.py", "test.js")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count("[bare-throw]"), 3, result.stdout)

    def test_explicit_javascript_error_expectations_are_retained(self):
        self.write(
            "test.js",
            'test("message", () => { expect(() => run()).toThrow("bad input"); });\n'
            'test("type", () => { expect(() => run()).toThrow(SpecificError); });\n'
            'test("regex", () => { expect(() => run()).toThrow(/bad input/); });\n',
        )
        result = self.run_detector("weak_negatives.py", "test.js")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("[bare-throw]", result.stdout)

    def test_missing_glob_and_unsupported_only_input_are_not_clean_scans(self):
        self.write("notes.txt", "test definitions are not in a supported language")
        for script in ("weak_negatives.py", "duplicate_tests.py"):
            for pattern in ("missing/*.py", "notes.txt"):
                with self.subTest(script=script, pattern=pattern):
                    result = self.run_detector(script, pattern)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("no supported files", result.stderr)

    def test_python_parse_failure_is_not_a_clean_scan(self):
        self.write("test_bad.py", "def test_broken(:\n    pass\n")
        for script in ("weak_negatives.py", "duplicate_tests.py"):
            with self.subTest(script=script):
                result = self.run_detector(script, "test_bad.py")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("test_bad.py", result.stderr)
                self.assertIn("invalid syntax", result.stderr)

    def test_missing_pattern_preserves_valid_findings_but_marks_input_incomplete(self):
        self.write(
            "test_valid.py",
            "def test_first():\n    result = run(1)\n    assert result.status_code == 400\n\n"
            "def test_second():\n    result = run(1)\n    assert result.status_code == 400\n",
        )
        for script in ("weak_negatives.py", "duplicate_tests.py"):
            with self.subTest(script=script):
                options = ["--json", "--jobs", "1"] if script == "duplicate_tests.py" else []
                result = self.run_detector(script, "test_valid.py", "missing/*.py", *options)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("unmatched pattern", result.stderr)
                self.assertIn("missing/*.py", result.stderr)
                if script == "duplicate_tests.py":
                    report = json.loads(result.stdout)
                    self.assertEqual(report["tests"], 2)
                    self.assertEqual(report["counts"]["REDUNDANT"], 1)
                    self.assertEqual(report["unmatched_patterns"], ["missing/*.py"])
                    self.assertFalse(report["input_complete"])
                else:
                    self.assertEqual(result.stdout.count("[status-only]"), 2, result.stdout)

    def test_matched_overlapping_patterns_scan_each_file_once(self):
        self.write("test_valid.py", "def test_refusal():\n    assert response.status_code == 400\n")
        for script in ("weak_negatives.py", "duplicate_tests.py"):
            with self.subTest(script=script):
                options = ["--json", "--jobs", "1"] if script == "duplicate_tests.py" else []
                result = self.run_detector(script, "test_valid.py", "test_*.py", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("unmatched pattern (no eligible files)", result.stderr)
                if script == "duplicate_tests.py":
                    report = json.loads(result.stdout)
                    self.assertEqual(report["files"], 1)
                    self.assertEqual(report["tests"], 1)
                    self.assertEqual(report["unmatched_patterns"], [])
                    self.assertTrue(report["input_complete"])
                else:
                    self.assertEqual(result.stdout.count("[status-only]"), 1, result.stdout)

    def test_duplicate_json_keeps_partial_results_and_identifies_unparsed_file(self):
        self.write("test_bad.py", "def test_broken(:\n    pass\n")
        self.write(
            "test_good.py",
            "def test_first():\n    result = run(1)\n    assert result == 3\n\n"
            "def test_second():\n    result = run(1)\n    assert result == 3\n",
        )
        result = self.run_detector("duplicate_tests.py", "*.py", "--json", "--jobs", "2")
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["tests"], 2)
        self.assertEqual(report["counts"]["REDUNDANT"], 1)
        self.assertEqual([row["file"] for row in report["unparsed_files"]], ["test_bad.py"])
        self.assertFalse(report["input_complete"])

    def test_unrecognized_test_syntax_is_reported_without_a_clean_claim(self):
        self.write("test.js", 'test.for([1, 2])("case %s", n => expect(n).toBe(n));')
        result = self.run_detector("duplicate_tests.py", "test.js", "--json", "--jobs", "1")
        self.assertEqual(result.returncode, 2, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["unrecognized_files"], ["test.js"])
        self.assertFalse(report["input_complete"])

    def test_statically_inactive_js_tests_do_not_replace_active_duplicates(self):
        body = "{ const result = run(1); expect(result).toBe(3); }"
        self.write(
            "test.js",
            f'test("active original", () => {body});\n'
            f'test.skip("skipped copy", () => {body});\n'
            f'describe.skip("disabled suite", () => {{ it("nested copy", () => {body}); }});\n'
            'test.todo("pending");\n'
            f'it("active copy", () => {body});\n',
        )
        result = self.run_detector("duplicate_tests.py", "test.js", "--json", "--jobs", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(len(report["groups"]), 1)
        group = report["groups"][0]
        self.assertEqual((group["kind"], group["match"]), ("REDUNDANT", "exact"))
        self.assertEqual([member["test"] for member in group["members"]], ["active original", "active copy"])
        self.assertEqual(
            {member["test"]: member["reason"] for member in report["inactive_tests"]},
            {"skipped copy": "skip", "nested copy": "skipped suite", "pending": "todo"},
        )

    def write_junit(self, *classnames):
        cases = "".join(f'<testcase classname="{c}" name="test_ok"/>' for c in classnames)
        return self.write("r.xml", f'<testsuite name="pytest">{cases}</testsuite>')

    def test_census_does_not_count_a_prefix_of_a_collected_file_as_collected(self):
        (self.root / "tests").mkdir()
        for name in ("test_user.py", "test_user_admin.py", "UserTest.php", "AdminUserTest.php"):
            self.write(f"tests/{name}", "")
        self.write_junit("tests.test_user_admin", "Tests\\AdminUserTest")
        result = self.run_detector("junit_census.py", "r.xml", "--test-files", "tests/*")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(2 of 4)", result.stdout)
        unseen = result.stdout.split("never mentioned by any report", 1)[1]
        self.assertIn("tests/test_user.py", unseen)
        self.assertIn("tests/UserTest.php", unseen)
        self.assertNotIn("tests/test_user_admin.py", unseen)
        self.assertNotIn("tests/AdminUserTest.php", unseen)

    def test_census_matches_collected_files_through_path_and_class_mentions(self):
        (self.root / "tests").mkdir()
        self.write("tests/test_user.py", "")
        self.write("tests/UserTest.php", "")
        self.write_junit("tests.test_user.TestUser", "Tests\\Unit\\UserTest")
        result = self.run_detector("junit_census.py", "r.xml", "--test-files", "tests/*")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("(0 of 2)", result.stdout)

    def test_census_resolves_exact_file_identity_before_basename_fallback(self):
        for layer in ("unit", "integration"):
            (self.root / "tests" / layer).mkdir(parents=True)
            for leaf in ("test_file.py", "test_module.py"):
                self.write(f"tests/{layer}/{leaf}", "")
        self.write(
            "r.xml",
            '<testsuite name="pytest">'
            '<testcase file="tests/unit/test_file.py" classname="test_file" name="test_ok"/>'
            '<testcase classname="tests.unit.test_module.TestModule" name="test_ok"/>'
            '</testsuite>',
        )
        result = self.run_detector("junit_census.py", "r.xml", "--test-files", "tests/**/*.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        unseen = result.stdout.split("never mentioned by any report (2 of 4)", 1)[1]
        self.assertEqual(
            [line.strip() for line in unseen.splitlines() if line.startswith("  tests/")],
            ["tests/integration/test_file.py", "tests/integration/test_module.py"],
        )

    def test_census_reports_ambiguous_short_names_without_crediting_either_path(self):
        self.write("test_unique.py", "")
        for layer in ("unit", "integration"):
            (self.root / layer).mkdir()
            self.write(f"{layer}/test_same.py", "")
        self.write_junit("test_same", "test_unique")
        result = self.run_detector("junit_census.py", "r.xml", "--test-files", "**/*.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("never mentioned by any report (0 of 3)", result.stdout)
        ambiguous = result.stdout.split("collection ambiguous from short names", 1)[1]
        self.assertIn("integration/test_same.py", ambiguous)
        self.assertIn("unit/test_same.py", ambiguous)
        self.assertNotIn("test_unique.py", ambiguous)

    def test_census_unmatched_glob_and_unreadable_report_are_incomplete_input(self):
        self.write("test_a.py", "")
        self.write_junit("test_a")
        result = self.run_detector("junit_census.py", "r.xml", "--test-files", "test_*.py", "--test-files", "nope/*")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("unmatched pattern (no eligible files): nope/*", result.stderr)
        self.assertIn("(0 of 1)", result.stdout)
        self.write("bad.xml", "<testsuite")
        result = self.run_detector("junit_census.py", "bad.xml")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("cannot read bad.xml", result.stderr)

    def test_guard_pins_unmatched_glob_is_incomplete_input(self):
        self.write("app.py", 'raise ValueError("amount must be a positive integer")\n')
        self.write("test_app.py", 'assert "amount must be a positive integer" in str(error)\n')
        result = self.run_detector("guard_pins.py", "--src", "app.py", "--tests", "test_app.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 distinct guard literals in 1 source files; 0 contain", result.stdout)
        for args in (("--src", "nope/**/*.py"), ("--src", "app.py", "--tests", "nope/*.py")):
            with self.subTest(args=args):
                result = self.run_detector("guard_pins.py", *args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn("unmatched pattern (no eligible files): nope/", result.stderr)

    def test_guard_pins_matches_template_fragments_inside_rendered_test_messages(self):
        self.write(
            "app.py",
            'raise ValueError(f"amount {value} must be a positive integer")\n'
            'raise ValueError("unknown currency code %s in the request" % code)\n'
            'raise ValueError(f"{field_name} is required {hint_text}")\n'
            'raise ValueError(f"price {price} exceeds the configured ceiling")\n'
            'raise ValueError("currency must be an ISO 4217 code")\n',
        )
        self.write("app.php", 'throw new RuntimeException("User $id was not found in the directory");\n')
        self.write(
            "app.js",
            "throw new Error(`token has expired and cannot be used: ${name}`);\n"
            "throw new Error(`Refusing to write ${target}: path is outside the output root`);\n",
        )
        self.write(
            "test_app.py",
            'assert "amount -3 must be a positive integer" in str(error)\n'
            'assert "unknown currency code XYZ in the request" in str(error)\n'
            'assert "email is required for signup" in str(error)\n'
            'with pytest.raises(ValueError, match="must be an ISO 4217"):\n',
        )
        self.write("test_app.php", "$this->expectExceptionMessage('User 42 was not found in the directory');\n")
        self.write(
            "test_app.js",
            'expect(() => use()).toThrow("token has expired and cannot be used: abc");\n'
            'expect(() => link()).toThrow("Refusing to write through symlink");\n',
        )
        result = self.run_detector("guard_pins.py", "--src", "app.*", "--tests", "test_app.*")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("8 distinct guard literals in 3 source files; 3 contain", result.stdout)
        rows = result.stdout.split("== first 60 unpinned\n", 1)[1].splitlines()
        self.assertEqual(
            rows,
            [
                "app.js:2  Refusing to write ${target}: path is outside the output root",
                "app.py:3  {field_name} is required {hint_text}",
                "app.py:4  price {price} exceeds the configured ceiling",
            ],
        )

    def test_guard_pins_requires_template_fragments_in_order_without_overlap(self):
        self.write(
            "app.py",
            'raise ValueError(f"first part here {x} second part here")\n'
            'raise ValueError(f"alpha bravo charlie {x} delta echo foxtrot")\n'
            'raise ValueError(f"quota exceeded now {a} quota exceeded now")\n'
            'raise ValueError(f"index out of range {i}range for the buffer")\n',
        )
        self.write(
            "test_app.py",
            'assert "second part here and first part here" in str(error)\n'
            'assert "alpha bravo charlie 7 then delta echo foxtrot" in str(error)\n'
            'assert "quota exceeded now for the account" in str(error)\n'
            'assert "index out of range for the buffer" in str(error)\n',
        )
        result = self.run_detector("guard_pins.py", "--src", "app.py", "--tests", "test_app.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 distinct guard literals in 1 source files; 3 contain", result.stdout)
        rows = result.stdout.split("== first 60 unpinned\n", 1)[1].splitlines()
        self.assertEqual(
            rows,
            [
                "app.py:1  first part here {x} second part here",
                "app.py:3  quota exceeded now {a} quota exceeded now",
                "app.py:4  index out of range {i}range for the buffer",
            ],
        )

    def test_reporters_reject_negative_limits_before_reading_input(self):
        self.write("app.py", 'raise ValueError("amount must be a positive integer")\n')
        self.write_junit("test_a")
        for script, inputs in (
            ("guard_pins.py", (("--src", "app.py"), ("--src", "missing.py"))),
            ("junit_census.py", (("r.xml",), ("missing.xml",))),
        ):
            for args in inputs:
                for value in ("-1", "-3", "-999"):
                    for option in (("--limit", value), (f"--limit={value}",)):
                        with self.subTest(script=script, args=args, option=option):
                            result = self.run_detector(script, *args, *option)
                            self.assertEqual(result.returncode, 2, result.stderr)
                            self.assertIn("--limit must be non-negative", result.stderr)
                            self.assertEqual(result.stdout, "")
                            self.assertNotIn("unmatched pattern", result.stderr)
                            self.assertNotIn("cannot read", result.stderr)

    def test_guard_limit_preserves_totals_and_bounds_detail_rows(self):
        messages = [f"guard {i:02d} requires a positive value" for i in range(65)]
        self.write("app.py", "".join(f'raise ValueError("{message}")\n' for message in messages))
        for limit in (None, 0, 1, 2, 60, 70):
            with self.subTest(limit=limit):
                options = [] if limit is None else ["--limit", str(limit)]
                result = self.run_detector("guard_pins.py", "--src", "app.py", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("65 distinct guard literals in 1 source files; 65 contain", result.stdout)
                self.assertIn("   65  app.py", result.stdout)
                expected_limit = 60 if limit is None else limit
                rows = result.stdout.split(f"== first {expected_limit} unpinned\n", 1)[1].splitlines()
                self.assertEqual(
                    rows,
                    [f"app.py:{i + 1}  {message}" for i, message in enumerate(messages[:expected_limit])],
                )

    def test_census_limit_preserves_totals_and_bounds_each_detail_section(self):
        cases = "".join(
            f'<testcase name="skip_{i:02d}"><skipped message="reason_{i:02d}"/></testcase>'
            f'<testcase name="zero_{i:02d}" assertions="0"/>'
            for i in range(25)
        )
        self.write("r.xml", f"<testsuite>{cases}</testsuite>")
        for i in range(125):
            self.write(f"test_unseen_{i:03d}.py", "")
        for limit in (None, 0, 1, 2, 20, 30):
            with self.subTest(limit=limit):
                options = [] if limit is None else ["--limit", str(limit)]
                result = self.run_detector("junit_census.py", "r.xml", "--test-files", "test_*.py", *options)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("testcases 50  skipped 25  failed/errored 0", result.stdout)
                self.assertIn("skip reasons (25 distinct)", result.stdout)
                self.assertIn("zero assertions (25)", result.stdout)
                self.assertIn("never mentioned by any report (125 of 125)", result.stdout)
                expected_limit = 20 if limit is None else limit
                lines = result.stdout.splitlines()
                self.assertEqual(
                    [line.strip() for line in lines if line.startswith("    1  reason_")],
                    [f"1  reason_{i:02d}" for i in range(min(25, expected_limit))],
                )
                self.assertEqual(
                    [line.strip() for line in lines if line.startswith("         e.g. skip_")],
                    [f"e.g. skip_{i:02d}" for i in range(min(25, expected_limit))],
                )
                self.assertEqual(
                    [line.strip() for line in lines if line.startswith("  zero_")],
                    [f"zero_{i:02d}" for i in range(min(25, expected_limit))],
                )
                self.assertEqual(
                    [line.strip() for line in lines if line.startswith("  test_unseen_")],
                    [f"test_unseen_{i:03d}.py" for i in range(min(125, expected_limit * 5))],
                )

    def run_reach_probe(self, env):
        self.write(
            "test_cli.py",
            "import subprocess, sys\n\n"
            "def test_refusal():\n"
            "    code = \"import sys; sys.stderr.write('warn\\\\nrefused: bad id\\\\n'); sys.exit(3)\"\n"
            "    result = subprocess.run([sys.executable, '-c', code], capture_output=True)\n"
            "    assert result.returncode == 3\n"
            "    assert result.stderr == b'warn\\nrefused: bad id\\n'\n",
        )
        env = {**os.environ, **env, "PYTHONPATH": str(SCRIPTS), "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("PYTEST_ADDOPTS", None)
        return subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "pytest_reach_probe", "test_cli.py"],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_reach_probe_truncates_its_output_once_per_session(self):
        out = self.root / "reach.jsonl"
        out.write_text('{"test": "stale::test", "program": "x", "rc": 1, "stderr_first": "", "stderr_last": ""}\n')
        for _ in range(2):
            result = self.run_reach_probe({"REACH_PROBE_OUT": str(out)})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            rows = [json.loads(line) for line in out.read_text().splitlines()]
            self.assertEqual([row["test"] for row in rows], ["test_cli.py::test_refusal"])
            self.assertEqual(rows[0]["rc"], 3)
            self.assertEqual(rows[0]["stderr_first"], "warn")
            self.assertEqual(rows[0]["stderr_last"], "refused: bad id")

    def test_reach_probe_defaults_to_a_per_process_file_in_the_temp_directory(self):
        tmpdir = self.root / "tmp"
        tmpdir.mkdir()
        env = {"TMPDIR": str(tmpdir)}
        result = self.run_reach_probe({**env, "REACH_PROBE_OUT": ""})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        written = list(tmpdir.glob("reach-probe-*.jsonl"))
        self.assertEqual(len(written), 1, list(tmpdir.iterdir()))
        self.assertRegex(written[0].name, r"^reach-probe-\d+\.jsonl$")
        self.assertIn(f"reach probe rows: {written[0]}", result.stdout)
        self.assertEqual(len(written[0].read_text().splitlines()), 1)

    def test_reach_probe_append_failure_preserves_subprocess_result_and_signals_incomplete(self):
        out = self.root / "reach.jsonl"
        self.write(
            "conftest.py",
            "import os\n"
            "from pathlib import Path\n"
            "import pytest\n"
            "@pytest.fixture(autouse=True)\n"
            "def make_probe_destination_unwritable():\n"
            "    out = Path(os.environ['REACH_PROBE_OUT'])\n"
            "    out.unlink()\n"
            "    out.mkdir()\n",
        )
        result = self.run_reach_probe({"REACH_PROBE_OUT": str(out)})
        self.assertTrue(out.is_dir())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 passed", result.stdout)
        self.assertIn("reach probe evidence incomplete", result.stdout)
        self.assertIn("test_cli.py::test_refusal", result.stdout)

    @unittest.skipUnless(shutil.which("python3.10"), "python3.10 not installed")
    def test_duplicate_tests_refuses_old_python_with_a_message(self):
        self.write("test_valid.py", "def test_sum():\n    assert sum([1, 2]) == 3\n")
        result = subprocess.run(
            [shutil.which("python3.10"), str(SCRIPTS / "duplicate_tests.py"), "test_valid.py"],
            cwd=self.root,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(result.stderr.strip(), "duplicate_tests: Python 3.11+ required")

    def test_valid_unique_test_is_a_successful_scan(self):
        self.write("test_valid.py", "def test_sum():\n    assert sum([1, 2]) == 3\n")
        result = self.run_detector("duplicate_tests.py", "test_valid.py", "--json", "--jobs", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["tests"], 1)
        self.assertEqual(report["groups"], [])
        self.assertTrue(report["input_complete"])


if __name__ == "__main__":
    unittest.main()
