import copy
import hashlib
import json
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

    def create_receiver_case(self, unicode_prefix="", multiline=False):
        other_call = "  (api\n   )();\n" if multiline else ""
        method_line = 5 if multiline else 3
        caller = ("import { UserApiHelper } from './helper';\n"
                  "export function run(api: UserApiHelper) {\n"
                  f"{other_call}"
                  f"  {unicode_prefix}return api.create();\n"
                  "}\n")
        base = caller.replace("api.create()", "0")
        helper = ("export class UserApiHelper {\n"
                  "  create(id: string) {\n"
                  "    return id;\n"
                  "  }\n"
                  "}\n")
        files = {"app/main.py": "value = 0\n", "app/main.ts": caller,
                 "app/helper.ts": helper, "tsconfig.json": '{"compilerOptions":{"strict":true}}\n'}
        symbols = [("app/main.ts", "run", "function", 2, 6 if multiline else 4),
                   ("app/helper.ts", "create", "method", 2, 4)]
        self.create_case(files, "value = 0\n", symbols,
                         [("app/main.ts", "create", "call", method_line)],
                         review_bases={"app/main.ts": base})
        db = sqlite3.connect(self.source / ".codesage/index.db")
        db.execute("UPDATE symbols SET qualified_name='UserApiHelper.create' WHERE name='create'")
        db.commit()
        db.close()
        compiler = self.root / "typescript.js"
        compiler.write_text("exports.version = '5.9.2';\n", encoding="utf-8")
        reads = [{"path": str(self.source / path), "sha256": hashlib.sha256(body.encode()).hexdigest(),
                  "role": "project"} for path, body in files.items() if path in
                 ("app/main.ts", "app/helper.ts", "tsconfig.json")]
        col = len(("  " + unicode_prefix + "return api.").encode("utf-8"))
        receipt = {"schema": 1, "kind": "typescript-contract-candidates",
                   "project": str(self.source.resolve()), "head": self.case["head_commit"],
                   "compiler": {"path": str(compiler), "version": "5.9.2",
                                "sha256": hashlib.sha256(compiler.read_bytes()).hexdigest()},
                   "scope": "explicit roots; no runtime dispatch proof", "reads": reads,
                   "calls": [{"path": "app/main.ts", "line": method_line, "col": col,
                              "name": "create", "expression": "api.create", "status": "candidate",
                              "candidate": {"path": "app/helper.ts", "start": 2, "end": 4,
                                            "name": "UserApiHelper.create"},
                              "receiver_chain": [{"expression": "api", "type": "UserApiHelper",
                                                  "declarations": [{"path": "app/main.ts", "start": 2,
                                                                    "end": 2, "col": 20}]}]}],
                   "diagnostics": {"count": 0, "codes": {}, "examples": [], "truncated": False},
                   "dependency_fallbacks": []}
        return receipt

    def test_receiver_context_is_opt_in_and_preserves_default_output(self):
        receipt = self.create_receiver_case()
        original = symbol_context.build_context(self.case, self.reviewer, self.source)
        explicit_default = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=None)
        self.assertEqual(json.dumps(original, ensure_ascii=False), json.dumps(explicit_default, ensure_ascii=False))
        self.assertNotIn("create(id: string)", original["context"])
        self.assertTrue(any(item["reason"] == "untyped-receiver" for item in original["issues"]))
        enabled = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertIn("create(id: string)", enabled["context"])
        selected = next(item for item in enabled["selected"] if item["path"] == "app/helper.ts")
        self.assertEqual(selected["resolution_basis"], "TypeScript declaration candidate")
        self.assertIsNone(selected["dependency_distance"])
        self.assertEqual(selected["receiver_chain"], receipt["calls"][0]["receiver_chain"])
        self.assertEqual(enabled["receiver_context"]["diagnostics"], receipt["diagnostics"])
        self.assertLessEqual(enabled["bytes"], 7000)

    def test_receiver_context_rejects_stale_head_and_altered_reads(self):
        receipt = self.create_receiver_case()
        receipt["head"] = self.case["base_commit"]
        with self.assertRaisesRegex(ValueError, "Git HEAD mismatch"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        receipt["head"] = self.case["head_commit"]
        receipt["reads"][1]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "read hash mismatch"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        receipt["reads"][1]["sha256"] = hashlib.sha256(
            (self.source / "app/helper.ts").read_bytes()).hexdigest()
        (self.source / "tsconfig.json").write_text('{"compilerOptions":{"strict":false}}\n', encoding="utf-8")
        receipt["reads"][2]["sha256"] = hashlib.sha256(
            (self.source / "tsconfig.json").read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "differs from Git HEAD"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)

    def test_receiver_context_rejects_unread_source_duplicate_calls_and_compiler_drift(self):
        receipt = self.create_receiver_case()
        original = copy.deepcopy(receipt)
        receipt["reads"] = [entry for entry in receipt["reads"] if not entry["path"].endswith("helper.ts")]
        with self.assertRaisesRegex(ValueError, "candidate lacks source provenance"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        receipt = original
        receipt["calls"].append(dict(receipt["calls"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate receiver-context call"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        receipt["calls"].pop()
        Path(receipt["compiler"]["path"]).write_text("modified compiler", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "compiler hash mismatch"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)

    def test_receiver_context_refusals_do_not_fall_back_to_name_resolution(self):
        receipt = self.create_receiver_case()
        call = receipt["calls"][0]
        call.pop("candidate")
        call["status"] = "unresolved"
        call["reason"] = "unresolved-or-ambiguous-receiver"
        unresolved = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertNotIn("create(id: string)", unresolved["context"])
        self.assertTrue(any(item["reason"] == "receiver-context-unresolved" for item in unresolved["issues"]))
        call["status"] = "candidate"
        call.pop("reason")
        call["candidate"] = {"path": "app/helper.ts", "start": 2, "end": 4,
                             "name": "UserApiHelper.create"}
        db = sqlite3.connect(self.source / ".codesage/index.db")
        db.execute("DELETE FROM symbols WHERE name='create'")
        db.commit()
        db.close()
        missing = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertNotIn("create(id: string)", missing["context"])
        self.assertTrue(any(item["reason"] == "receiver-context-target-missing" for item in missing["issues"]))

    def test_receiver_context_joins_utf8_byte_column_and_rejects_wrong_column(self):
        receipt = self.create_receiver_case("/* ⚑ */ ")
        db = sqlite3.connect(self.source / ".codesage/index.db")
        indexed_col = db.execute("SELECT col FROM refs WHERE to_name='create'").fetchone()[0]
        db.close()
        self.assertEqual(indexed_col, len("  /* ⚑ */ return api."))
        self.assertNotEqual(indexed_col, receipt["calls"][0]["col"])
        matched = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertTrue(any(item["resolution_basis"] == "TypeScript declaration candidate"
                            for item in matched["selected"]))
        receipt["calls"][0]["col"] -= len("⚑".encode()) - 1
        with self.assertRaisesRegex(ValueError, "call token mismatch"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)

    def test_receiver_context_cli_uses_case_receipt_and_reports_missing_receipt(self):
        receipt = self.create_receiver_case()
        self.case["id"] = "source"
        cases = self.root / "cases.jsonl"
        cases.write_text(json.dumps(self.case) + "\n", encoding="utf-8")
        receipts = self.root / "receipts"
        receipts.mkdir()
        script = str(Path(symbol_context.__file__).resolve())
        args = [sys.executable, script, "--inputs", str(cases), "--reviewer-root",
                str(self.reviewer), "--sources-root", str(self.root)]
        default = self.root / "default.jsonl"
        subprocess.run(args + ["--output", str(default)], check=True, capture_output=True)
        expected = symbol_context.build_context(self.case, self.reviewer, self.source)
        self.assertEqual(default.read_bytes(), (json.dumps(expected, ensure_ascii=False) + "\n").encode())
        missing = self.root / "missing.jsonl"
        subprocess.run(args + ["--output", str(missing),
                               "--receiver-context-directory", str(receipts)], check=True, capture_output=True)
        absent = json.loads(missing.read_text(encoding="utf-8"))
        self.assertEqual(absent["context"], expected["context"])
        self.assertTrue(any(item["reason"] == "receiver-context-missing" for item in absent["issues"]))
        (receipts / "source.json").write_text(json.dumps(receipt), encoding="utf-8")
        enabled = self.root / "enabled.jsonl"
        subprocess.run(args + ["--output", str(enabled),
                               "--receiver-context-directory", str(receipts)], check=True, capture_output=True)
        opt_in = json.loads(enabled.read_text(encoding="utf-8"))
        self.assertIn("create(id: string)", opt_in["context"])

    def test_receiver_context_allows_verified_external_receiver_declaration(self):
        receipt = self.create_receiver_case()
        declaration = self.root / "external.d.ts"
        declaration.write_text("declare interface External {};\n", encoding="utf-8")
        receipt["reads"].append({"path": str(declaration),
                                 "sha256": hashlib.sha256(declaration.read_bytes()).hexdigest(),
                                 "role": "dependency"})
        receipt["calls"][0]["receiver_chain"][0]["declarations"] = [
            {"path": str(declaration), "start": 1, "end": 1, "col": 0}]
        enabled = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertIn("create(id: string)", enabled["context"])
        receipt["reads"].pop()
        with self.assertRaisesRegex(ValueError, "declaration lacks read provenance"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)

    def test_receiver_context_validates_type_declaration_reads_and_spans(self):
        receipt = self.create_receiver_case()
        external = self.root / "external.d.ts"
        external.write_text("declare class UserApiHelper {}\n", encoding="utf-8")
        receipt["reads"].append({"path": str(external), "sha256": hashlib.sha256(external.read_bytes()).hexdigest(),
                                 "role": "dependency"})
        receiver = receipt["calls"][0]["receiver_chain"][0]
        receiver["type_declarations"] = [{"path": str(external), "start": 1, "end": 1, "col": 0}]
        self.assertIn("create(id: string)", symbol_context.build_context(
            self.case, self.reviewer, self.source, receiver_context=receipt)["context"])
        receiver["type_declarations"][0]["end"] = 2
        with self.assertRaisesRegex(ValueError, "declaration span"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        receiver["type_declarations"][0]["end"] = 1
        receipt["reads"].pop()
        with self.assertRaisesRegex(ValueError, "declaration lacks read provenance"):
            symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)

    def test_receiver_context_accepts_multiline_unsupported_call_without_selecting_it(self):
        receipt = self.create_receiver_case(multiline=True)
        receipt["calls"].append({"path": "app/main.ts", "line": 3, "col": 2,
                                 "name": "(api\n   )", "expression": "(api\n   )",
                                 "status": "unresolved", "reason": "unsupported-call-expression",
                                 "receiver_chain": []})
        result = symbol_context.build_context(self.case, self.reviewer, self.source, receiver_context=receipt)
        self.assertIn("create(id: string)", result["context"])
        self.assertFalse(any(item["reason"] == "receiver-context-target-missing" for item in result["issues"]))

    def test_receiver_context_candidate_obeys_whole_span_budget(self):
        receipt = self.create_receiver_case()
        limited = symbol_context.build_context(self.case, self.reviewer, self.source,
                                               budget=340, receiver_context=receipt)
        self.assertNotIn("create(id: string)", limited["context"])
        self.assertTrue(any(item["reason"] in ("budget", "budget-header") for item in limited["issues"]))
        self.assertEqual(limited["receiver_context"]["diagnostics"], receipt["diagnostics"])

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
