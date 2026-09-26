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

    def run_reach_probe(self, env):
        self.write(
            "test_cli.py",
            "import subprocess, sys\n\n"
            "def test_refusal():\n"
            "    code = \"import sys; sys.stderr.write('warn\\\\nrefused: bad id\\\\n'); sys.exit(3)\"\n"
            "    assert subprocess.run([sys.executable, '-c', code], capture_output=True).returncode == 3\n",
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
