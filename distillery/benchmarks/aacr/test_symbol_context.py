import hashlib
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import symbol_context


class SymbolContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.reviewer = self.root / "reviewer"
        self.reviewer.mkdir()
        subprocess.run(["git", "-C", str(self.source), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(self.source), "config", "user.email", "test@example.invalid"], check=True)
        self.case = {"id": "example-one", "head_commit": "", "files": [
            {"path": "app/main.py", "role": "review", "base": "example-one/base/app/main.py",
             "head": "example-one/head/app/main.py"}]}

    def create_case(self, files, base, symbols, refs, review_bases=None):
        baselines = {"app/main.py": base, **(review_bases or {})}
        for path, body in files.items():
            initial = baselines.get(path, body)
            if initial is None:
                continue
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(initial, encoding="utf-8")
        subprocess.run(["git", "-C", str(self.source), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "base"], check=True)
        self.case["base_commit"] = subprocess.check_output(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        self.case["files"] = []
        for path, initial in baselines.items():
            body = files[path]
            target = self.source / path
            if body is None:
                target.unlink()
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")
            record = {"path": path, "role": "review", "base": None, "head": None}
            for version, content in (("base", initial), ("head", body)):
                if content is None:
                    continue
                relative = f"example-one/{version}/{path}"
                prepared = self.reviewer / relative
                prepared.parent.mkdir(parents=True, exist_ok=True)
                prepared.write_text(content, encoding="utf-8")
                record[version] = relative
            self.case["files"].append(record)
        subprocess.run(["git", "-C", str(self.source), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(self.source), "commit", "-qm", "fixture"], check=True)
        self.case["head_commit"] = subprocess.check_output(
            ["git", "-C", str(self.source), "rev-parse", "HEAD"], text=True).strip()
        index_dir = self.source / ".codesage"
        index_dir.mkdir()
        db = sqlite3.connect(index_dir / "index.db")
        db.executescript("""
            CREATE TABLE files (id INTEGER PRIMARY KEY, path TEXT, content_hash TEXT);
            CREATE TABLE symbols (id INTEGER PRIMARY KEY, file_id INTEGER, name TEXT,
                qualified_name TEXT, kind TEXT, line_start INTEGER, line_end INTEGER);
            CREATE TABLE refs (from_file_id INTEGER, from_symbol TEXT, to_name TEXT,
                to_name_tail TEXT, kind TEXT, line INTEGER, col INTEGER);
            CREATE TABLE structural_index_state (id INTEGER, last_sha TEXT);
        """)
        ids = {}
        for ident, path in enumerate(sorted(files), 1):
            if files[path] is None:
                continue
            ids[path] = ident
            db.execute("INSERT INTO files VALUES (?,?,?)", (ident, path,
                       hashlib.sha256(files[path].encode()).hexdigest()))
        for path, name, kind, start, end in symbols:
            db.execute("INSERT INTO symbols (file_id,name,qualified_name,kind,line_start,line_end) "
                       "VALUES (?,?,?,?,?,?)", (ids[path], name, name, kind, start, end))
        for ref in refs:
            path, name, kind, line = ref[:4]
            from_symbol = ref[4] if len(ref) == 5 else None
            tail = name.rsplit(".", 1)[-1]
            col = symbol_context.lf_lines(files[path])[line - 1].find(tail) if kind == "call" else 0
            db.execute("INSERT INTO refs VALUES (?,?,?,?,?,?,?)", (ids[path], from_symbol, name,
                       tail, kind, line, col))
        db.execute("INSERT INTO structural_index_state VALUES (1,?)", (self.case["head_commit"],))
        db.commit()
        db.close()

    def test_changed_call_reaches_defaulted_helper_through_three_dependencies(self):
        files = {"app/main.py": "from app.bridge import helper\n\ndef invoke():\n    return helper()\n",
                 "app/bridge.py": "from app.middle import helper\n",
                 "app/middle.py": "from app.helper import helper\n",
                 "app/helper.py": "def helper(enabled=False):\n    return enabled\n"}
        symbols = [("app/main.py", "invoke", "function", 3, 4),
                   ("app/helper.py", "helper", "function", 1, 2)]
        refs = [("app/main.py", "app.bridge", "import", 1),
                ("app/main.py", "app.bridge.helper", "import", 1),
                ("app/main.py", "helper", "import_binding", 1),
                ("app/main.py", "helper", "call", 4),
                ("app/bridge.py", "app.middle", "import", 1),
                ("app/bridge.py", "app.middle.helper", "import", 1),
                ("app/middle.py", "app.helper", "import", 1)]
        self.create_case(files, "from app.bridge import helper\n\ndef invoke():\n    return 0\n", symbols, refs)
        subprocess.run([sys.executable, "-c", "from app.main import invoke; assert invoke() is False"],
                       cwd=self.source, check=True)
        result = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertLessEqual(result["bytes"], 7000)
        self.assertIn("def helper(enabled=False):", result["context"])
        self.assertIn("dependency distance=3", result["context"])
        self.assertEqual(result["selected"][0]["path"], "app/helper.py")
        self.assertEqual(result["selected"][0]["origin"], "changed-line call")
        self.assertEqual(result["selected"][0]["resolution_basis"], "name-based candidate")
        self.assertEqual(result["selected"][0]["span_sha256"], hashlib.sha256(files["app/helper.py"].encode()).hexdigest())

    def test_same_tier_overloads_are_reported_without_selected_contract(self):
        files = {"app/main.py": "from app.first import first\nfrom app.second import second\n\ndef invoke():\n    return helper()\n",
                 "app/first.py": "def helper(flag=False):\n    return flag\n",
                 "app/second.py": "def helper(flag=True):\n    return flag\n"}
        symbols = [("app/main.py", "invoke", "function", 4, 5),
                   ("app/first.py", "helper", "function", 1, 2),
                   ("app/second.py", "helper", "function", 1, 2)]
        refs = [("app/main.py", "app.first", "import", 1),
                ("app/main.py", "app.second", "import", 2),
                ("app/main.py", "helper", "call", 5)]
        self.create_case(files, "from app.first import first\nfrom app.second import second\n\ndef invoke():\n    return 0\n", symbols, refs)
        result = symbol_context.build_context(self.case, self.reviewer, self.source)
        ambiguous = [item for item in result["issues"] if item["reason"] == "ambiguous"]
        self.assertEqual(len(ambiguous), 1)
        self.assertEqual(len(ambiguous[0]["candidates"]), 2)
        self.assertNotIn("def helper(", result["context"])

    def test_budget_and_dirty_source_refuse_unverified_or_partial_span(self):
        files = {"app/main.py": "from app.helper import helper\n\ndef invoke():\n    return helper()\n",
                 "app/helper.py": "def helper(enabled=False):\n    return enabled\n"}
        symbols = [("app/main.py", "invoke", "function", 3, 4),
                   ("app/helper.py", "helper", "function", 1, 2)]
        refs = [("app/main.py", "app.helper", "import", 1),
                ("app/main.py", "helper", "call", 4)]
        self.create_case(files, "from app.helper import helper\n\ndef invoke():\n    return 0\n", symbols, refs)
        base_path = self.reviewer / self.case["files"][0]["base"]
        base_path.write_text("tampered base\n")
        with self.assertRaisesRegex(ValueError, "Prepared base differs"):
            symbol_context.build_context(self.case, self.reviewer, self.source)
        base_path.write_text("from app.helper import helper\n\ndef invoke():\n    return 0\n")
        small = symbol_context.build_context(self.case, self.reviewer, self.source, budget=360)
        self.assertLessEqual(small["bytes"], 360)
        self.assertNotIn("def helper(", small["context"])
        self.assertTrue(any(item["reason"] == "budget" for item in small["issues"]))
        (self.source / "app/helper.py").write_text("def helper(enabled=True):\n    return enabled\n")
        dirty = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertNotIn("def helper(", dirty["context"])
        self.assertTrue(any(item["reason"] == "provenance" for item in dirty["issues"]))
        db = sqlite3.connect(self.source / ".codesage/index.db")
        db.execute("UPDATE files SET content_hash=? WHERE path='app/helper.py'", (
            hashlib.sha256((self.source / "app/helper.py").read_bytes()).hexdigest(),))
        db.commit()
        db.close()
        forged = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertNotIn("def helper(", forged["context"])
        self.assertTrue(any(item["reason"] == "provenance" for item in forged["issues"]))

    def test_untyped_member_call_cannot_resolve_to_unrelated_local_method(self):
        files = {"app/main.py": "class Client:\n    def click(self): return False\n    def run(self):\n        return self.driver.click()\n"}
        symbols = [("app/main.py", "Client", "class", 1, 4),
                   ("app/main.py", "click", "method", 2, 2),
                   ("app/main.py", "run", "method", 3, 4)]
        refs = [("app/main.py", "click", "call", 4, "Client.run")]
        self.create_case(files, "class Client:\n    def click(self): return False\n    def run(self):\n        return False\n", symbols, refs)
        db = sqlite3.connect(self.source / ".codesage/index.db")
        db.execute("UPDATE symbols SET qualified_name='Client.click' WHERE name='click'")
        db.execute("UPDATE symbols SET qualified_name='Client.run' WHERE name='run'")
        db.commit()
        db.close()
        result = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertNotIn("def click(self)", result["context"])
        self.assertTrue(any(item["reason"] == "untyped-receiver" for item in result["issues"]))
        index = symbol_context.Index(self.source, self.case["head_commit"])
        try:
            self.assertEqual(index.resolve("app/main.py", "click"), (None, []))
        finally:
            index.close()

    def test_call_columns_accept_character_or_utf8_byte_offsets(self):
        ref = {"to_name": "helper", "to_name_tail": "helper", "col": 2}
        self.assertEqual(symbol_context.call_receiver("⚑ helper()", ref), "bare-call")
        ref["col"] = len("⚑ ".encode())
        self.assertEqual(symbol_context.call_receiver("⚑ helper()", ref), "bare-call")

    def test_qualified_template_and_bare_decorator_call_shapes(self):
        qualified = {"to_name": "ns::helper", "to_name_tail": "helper", "col": 0}
        self.assertEqual(symbol_context.call_receiver("ns::helper<int>()", qualified), "qualified-call")
        bare = {"to_name": "helper", "to_name_tail": "helper", "col": 0}
        self.assertEqual(symbol_context.call_receiver("helper<int>()", bare), "bare-call")
        bare["col"] = 4
        self.assertEqual(symbol_context.call_receiver("obj.helper<int>()", bare), "untyped-receiver")
        decorator = {"to_name": "retry", "to_name_tail": "retry", "col": 1}
        self.assertEqual(symbol_context.call_receiver("@retry", decorator), "bare-call")

    def test_untyped_call_does_not_hide_later_bare_call_with_same_name(self):
        files = {"app/main.py": "from app.helper import helper\n\ndef run(obj):\n    obj.helper()\n    return helper()\n",
                 "app/helper.py": "def helper(enabled=False):\n    return enabled\n"}
        base = "from app.helper import helper\n\ndef run(obj):\n    pass\n    return 0\n"
        symbols = [("app/main.py", "run", "function", 3, 5),
                   ("app/helper.py", "helper", "function", 1, 2)]
        refs = [("app/main.py", "app.helper", "import", 1),
                ("app/main.py", "helper", "call", 4),
                ("app/main.py", "helper", "call", 5)]
        self.create_case(files, base, symbols, refs)
        result = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertTrue(any(item["reason"] == "untyped-receiver" and item["line"] == 4
                            for item in result["issues"]))
        self.assertEqual(result["selected"][0]["path"], "app/helper.py")
        self.assertEqual(result["selected"][0]["source"], "app/main.py:5")

    def test_unicode_line_separator_keeps_lf_anchors_and_exact_span(self):
        prefix = "from app.helper import helper\n\ndef run():\n    note = 'a\u2028b'\n"
        files = {"app/main.py": prefix + "    return helper()\n",
                 "app/helper.py": "def helper(enabled=False):\n    return enabled\n"}
        base = prefix + "    return 0\n"
        symbols = [("app/main.py", "run", "function", 3, 5),
                   ("app/helper.py", "helper", "function", 1, 2)]
        refs = [("app/main.py", "app.helper", "import", 1),
                ("app/main.py", "helper", "call", 5)]
        self.create_case(files, base, symbols, refs)
        subprocess.run([sys.executable, "-c", "from app.main import run; assert run() is False"],
                       cwd=self.source, check=True)
        self.assertEqual(symbol_context.changed_head_lines(base, files["app/main.py"]), {5})
        result = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertEqual(result["selected"][0]["source"], "app/main.py:5")
        selected = next(item for item in result["selected"] if item["path"] == "app/main.py")
        self.assertEqual((selected["start"], selected["end"]), (3, 5))
        raw_span = b"".join(symbol_context.lf_raw_lines(files["app/main.py"].encode())[2:5])
        self.assertEqual(selected["span_sha256"], hashlib.sha256(raw_span).hexdigest())
        rendered = result["context"].split("\n")
        title = next(index for index, line in enumerate(rendered) if "app/main.py:3-5 | changed symbol" in line)
        restored = "".join(line.split(" ", 1)[1] + "\n" for line in rendered[title + 1:title + 4])
        self.assertEqual(restored.encode(), raw_span)

    def test_lf_line_policy_rejects_bare_cr_and_preserves_crlf(self):
        self.assertEqual(symbol_context.lf_raw_lines(b"a\r\nb\r\n"), [b"a\r\n", b"b\r\n"])
        with self.assertRaisesRegex(ValueError, "Bare CR"):
            symbol_context.changed_head_lines("a\rb", "a\nb")
        with self.assertRaisesRegex(ValueError, "Bare CR"):
            symbol_context.lf_raw_lines(b"a\rb")

    def test_addition_matches_git_base_absence(self):
        files = {"app/main.py": "value = 1\n", "app/helper.py": "value = 2\n"}
        self.create_case(files, None, [], [])
        added = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertFalse(any(item["reason"] == "deleted-file" for item in added["issues"]))

    def test_deletion_matches_git_head_absence(self):
        self.create_case({"app/main.py": None, "app/helper.py": "value = 2\n"}, "value = 1\n", [], [])
        deleted = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertTrue(any(item["reason"] == "deleted-file" for item in deleted["issues"]))

    def test_all_direct_calls_precede_enclosing_symbols_across_files(self):
        main_prefix = "from app.ahelpers import ahelper\n\ndef main_task():\n    marker = '" + "x" * 850 + "'\n"
        other_prefix = "from app.bhelpers import bhelper, chelper\n\ndef other_task():\n"
        files = {"app/main.py": main_prefix + "    return ahelper()\n",
                 "app/other.py": other_prefix + "    value = bhelper()\n    return chelper()\n",
                 "app/ahelpers.py": "def ahelper():\n    return 1\n",
                 "app/bhelpers.py": "def bhelper():\n    value = '" + "b" * 300 + "'\n    return value\n\n"
                                    "def chelper():\n    value = '" + "c" * 300 + "'\n    return value\n"}
        symbols = [("app/main.py", "main_task", "function", 3, 5),
                   ("app/other.py", "other_task", "function", 3, 5),
                   ("app/ahelpers.py", "ahelper", "function", 1, 2),
                   ("app/bhelpers.py", "bhelper", "function", 1, 3),
                   ("app/bhelpers.py", "chelper", "function", 5, 7)]
        refs = [("app/main.py", "app.ahelpers", "import", 1),
                ("app/main.py", "ahelper", "call", 5),
                ("app/other.py", "app.bhelpers", "import", 1),
                ("app/other.py", "bhelper", "call", 4),
                ("app/other.py", "chelper", "call", 5)]
        self.create_case(files, main_prefix + "    return 0\n", symbols, refs,
                         review_bases={"app/other.py": other_prefix + "    value = 0\n    return 0\n"})
        result = symbol_context.build_context(self.case, self.reviewer, self.source, budget=2250)
        self.assertLessEqual(result["bytes"], 2250)
        self.assertEqual([item["rank"] for item in result["selected"]], sorted(item["rank"] for item in result["selected"]))
        self.assertIn("app/bhelpers.py:5-7", result["context"])
        self.assertTrue(any(item["reason"] == "budget" and item["path"] == "app/main.py"
                            for item in result["issues"]))


if __name__ == "__main__":
    unittest.main()
