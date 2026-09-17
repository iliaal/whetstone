import copy
import io
import json
import tempfile
import unittest
import urllib.error
import uuid
from pathlib import Path
from unittest.mock import patch

import prepare


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.selection = self.root / "selection.json"
        self.output = self.root / "output"
        self.cache = self.root / "cache"
        self.secret = "forbidden-annotation-" + uuid.uuid4().hex
        self.comment = {"path": "src/file.py", "side": "right", "from_line": 1, "to_line": 1,
                        "category": "Code Defect", "context": "Diff Level", "note": self.secret,
                        "is_ai_comment": True, "source_model": "upstream-model"}
        row = {"githubPrUrl": "https://github.com/owner/project/pull/7", "source_commit": "1" * 40,
               "target_commit": "2" * 40, "comments": [self.comment], "project_main_language": "Python"}
        self.rows = {name: [copy.deepcopy(row)] for name in prepare.DATASETS}
        self.rows[prepare.DATASETS[1]][0]["comments"][0]["note"] = "negative-" + self.secret
        self.case = {"id": "case-one", "pr_url": row["githubPrUrl"], "language": "Python",
                     "source_commit": "1" * 40, "target_commit": "2" * 40, "merge_base_commit": "3" * 40,
                     "positive_comment_indices": [0], "negative_comment_indices": [0],
                     "context_paths": ["src/context.py"], "claims": [{"evidence": self.secret}]}
        self.manifest = {"source": {"revision": prepare.REVISION, "files": {}}, "cases": [self.case]}
        self.remote = {}
        for commit, body in (("3" * 40, b"value = 1\n"), ("2" * 40, b"value = 0\n")):
            for path in ("src/file.py", "src/context.py"):
                self.remote[f"https://raw.githubusercontent.com/owner/project/{commit}/{path}"] = body
        self.save()

    def save(self):
        for name, rows in self.rows.items():
            raw = json.dumps(rows).encode()
            (self.source / name).write_bytes(raw)
            url = f"https://raw.githubusercontent.com/alibaba/aacr-bench/{prepare.REVISION}/dataset/{name}"
            self.manifest["source"]["files"][name] = {"url": url, "sha256": prepare.digest(raw)}
            self.remote[url] = raw
        self.selection.write_text(json.dumps(self.manifest))

    def open_url(self, url, timeout=30):
        value = self.remote.get(url)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise urllib.error.HTTPError(url, 404, "Missing", {}, None)
        return io.BytesIO(value)

    def run_prepare(self, **kwargs):
        with patch("urllib.request.urlopen", side_effect=self.open_url, autospec=True):
            return prepare.prepare(self.selection, self.output, self.source, **kwargs)

    def assert_no_labels(self):
        for file in (self.output / "reviewer").rglob("*"):
            if file.is_file():
                self.assertNotIn(self.secret, file.read_text(), str(file))

    def test_prepares_merge_base_diff_and_separates_exact_labels(self):
        self.assertEqual(self.run_prepare(), 1)
        row = json.loads((self.output / "reviewer/inputs.jsonl").read_text())
        self.assertEqual(row["base_commit"], "3" * 40)
        self.assertEqual(set(row), {"id", "repo", "base_commit", "head_commit", "language", "scope", "files"})
        self.assertIn("not the full PR", row["scope"])
        diff = (self.output / "reviewer/case-one/diff.patch").read_text()
        self.assertIn("-value = 1\n+value = 0\n", diff)
        self.assertNotIn("context.py", diff)
        self.assertEqual((self.output / "reviewer/case-one/base/src/file.py").read_bytes(), b"value = 1\n")
        label = json.loads((self.output / "refs/labels.jsonl").read_text())
        self.assertEqual(label["positive_comments"], [{"index": 0, **self.comment}])
        self.assertEqual(label["negative_comments"][0]["note"], "negative-" + self.secret)
        self.assertEqual(label["claims"], self.case["claims"])
        self.assert_no_labels()
        target = self.output / "reviewer/inputs.jsonl"
        clean = target.read_text()
        target.write_text(clean + self.secret)
        self.assertIn(self.secret, target.read_text())
        with self.assertRaisesRegex(AssertionError, self.secret):
            self.assert_no_labels()
        target.write_text(clean)
        self.assert_no_labels()

    def test_tampered_source_fails_before_output_or_downloads(self):
        (self.source / prepare.DATASETS[1]).write_bytes(b"tampered and not JSON")
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            with self.assertRaisesRegex(ValueError, "Source hash mismatch"):
                prepare.prepare(self.selection, self.output, self.source)
        self.assertFalse(self.output.exists())

    def test_output_refuses_existing_directory_and_preserves_contents(self):
        self.output.mkdir()
        sentinel = self.output / "sentinel"
        sentinel.write_text(self.secret)
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.run_prepare()
        self.assertEqual(sentinel.read_text(), self.secret)

    def test_malformed_selections_rejected(self):
        original = copy.deepcopy(self.manifest)
        mutations = [lambda c: c.update(id="../escape"), lambda c: c.update(context_paths=["../escape"]),
                     lambda c: c.update(source_commit="main"), lambda c: c.update(merge_base_commit="main"),
                     lambda c: c.update(target_commit="4" * 40), lambda c: c.update(positive_comment_indices=[-1]),
                     lambda c: c.update(positive_comment_indices=[True]), lambda c: c.update(positive_comment_indices=[0, 0]),
                     lambda c: c.update(pr_url="https://github.com/owner/project/pull/7?x=1"),
                     lambda c: c.update(language="unknown")]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.manifest = copy.deepcopy(original)
                mutation(self.manifest["cases"][0])
                self.save()
                with self.assertRaises(ValueError):
                    self.run_prepare()
                self.assertFalse(self.output.exists())

    def test_duplicate_pr_refused(self):
        self.manifest["cases"].append({**self.case, "id": "case-two"})
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.run_prepare()

    def test_non_defect_positive_refused(self):
        self.rows[prepare.DATASETS[0]][0]["comments"][0]["category"] = "Performance"
        self.save()
        with self.assertRaisesRegex(ValueError, "Code Defect"):
            self.run_prepare()

    def test_absent_negative_record_permitted_only_without_selected_indices(self):
        self.rows[prepare.DATASETS[1]] = []
        self.save()
        with self.assertRaisesRegex(ValueError, "Expected one negative"):
            self.run_prepare()
        self.case["negative_comment_indices"] = []
        self.save()
        self.run_prepare()
        labels = json.loads((self.output / "refs/labels.jsonl").read_text())
        self.assertEqual(labels["negative_comments"], [])

    def test_project_language_mismatch_refused(self):
        self.case["language"] = "PHP"
        self.save()
        with self.assertRaisesRegex(ValueError, "Language mismatch"):
            self.run_prepare()

    def test_pinned_license_included_and_bad_hash_refused(self):
        url = f"https://raw.githubusercontent.com/alibaba/aacr-bench/{prepare.REVISION}/LICENSE"
        self.remote[url] = b"example license"
        self.manifest["source"]["license"] = {"url": url, "sha256": "0" * 64}
        self.save()
        with self.assertRaisesRegex(ValueError, "License hash mismatch"):
            self.run_prepare()
        self.manifest["source"]["license"]["sha256"] = prepare.digest(self.remote[url])
        self.save()
        self.run_prepare()
        self.assertEqual((self.output / "refs/LICENSE.aacr-bench").read_bytes(), self.remote[url])

    def test_external_context_is_pinned_and_reason_stays_private(self):
        context = {"repository": "https://github.com/owner/dependency", "commit": "4" * 40,
                   "version": "v1.2", "paths": ["docs/api.md"], "reason": self.secret}
        self.case["external_context"] = [context]
        url = f"https://raw.githubusercontent.com/owner/dependency/{'4' * 40}/docs/api.md"
        self.remote[url] = b"Official API reference\n"
        self.save()
        self.run_prepare()
        self.assert_no_labels()
        row = json.loads((self.output / "reviewer/inputs.jsonl").read_text())
        metadata = row["external_context"][0]
        self.assertEqual(set(metadata), {"repository", "commit", "version", "paths"})
        self.assertEqual(metadata["commit"], "4" * 40)
        self.assertEqual((self.output / "reviewer" / metadata["paths"][0]).read_bytes(), self.remote[url])

    def test_missing_external_context_fails_without_output(self):
        self.case["external_context"] = [{"repository": "https://github.com/owner/dependency",
                                          "commit": "4" * 40, "version": "v1.2", "paths": ["docs/api.md"]}]
        self.save()
        with self.assertRaisesRegex(ValueError, "External context missing"):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_external_repository_traversal_refused(self):
        self.case["external_context"] = [{"repository": "https://github.com/../..",
                                          "commit": "4" * 40, "version": "v1", "paths": ["stolen.md"]}]
        self.save()
        with self.assertRaisesRegex(ValueError, "Unsafe repository path"):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_external_versions_preserved_separately(self):
        self.case["external_context"] = []
        for sha, version in (("4" * 40, "v1"), ("5" * 40, "v2")):
            self.case["external_context"].append({"repository": "https://github.com/owner/dependency",
                                                  "commit": sha, "version": version, "paths": ["api.md"]})
            self.remote[f"https://raw.githubusercontent.com/owner/dependency/{sha}/api.md"] = version.encode()
        self.save()
        self.run_prepare()
        contexts = json.loads((self.output / "reviewer/inputs.jsonl").read_text())["external_context"]
        paths = [context["paths"][0] for context in contexts]
        self.assertNotEqual(paths[0], paths[1])
        self.assertEqual([(self.output / "reviewer" / p).read_text() for p in paths], ["v1", "v2"])

    def test_missing_both_files_removes_staging_and_leaves_no_output(self):
        self.remote = {}
        with self.assertRaisesRegex(ValueError, "Both versions missing"):
            self.run_prepare()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".aacr-*")), [])

    def test_one_sided_addition_preserves_absence(self):
        del self.remote[f"https://raw.githubusercontent.com/owner/project/{'3' * 40}/src/file.py"]
        self.run_prepare()
        self.assertFalse((self.output / "reviewer/case-one/base/src/file.py").exists())
        self.assertIn("--- /dev/null", (self.output / "reviewer/case-one/diff.patch").read_text())

    def test_one_sided_deletion_uses_left_anchor(self):
        for rows in self.rows.values():
            rows[0]["comments"][0]["side"] = "left"
        del self.remote[f"https://raw.githubusercontent.com/owner/project/{'2' * 40}/src/file.py"]
        self.save()
        self.run_prepare()
        self.assertFalse((self.output / "reviewer/case-one/head/src/file.py").exists())
        self.assertIn("+++ /dev/null", (self.output / "reviewer/case-one/diff.patch").read_text())

    def test_non_404_failure_is_not_treated_as_absence(self):
        url = next(iter(self.remote))
        self.remote[url] = urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            self.run_prepare()
        self.assertFalse(self.output.exists())

    def test_out_of_range_anchor_refused(self):
        self.rows[prepare.DATASETS[0]][0]["comments"][0]["to_line"] = 2
        self.save()
        with self.assertRaisesRegex(ValueError, "anchor outside"):
            self.run_prepare()

    def test_unchanged_positive_file_refused(self):
        self.remote[f"https://raw.githubusercontent.com/owner/project/{'2' * 40}/src/file.py"] = b"value = 1\n"
        with self.assertRaisesRegex(ValueError, "Positive path unchanged"):
            self.run_prepare()

    def test_complete_cache_replays_without_network(self):
        with patch("urllib.request.urlopen", side_effect=self.open_url, autospec=True):
            prepare.prepare(self.selection, self.output, cache=self.cache)
        replay = self.root / "replay"
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            prepare.prepare(self.selection, replay, cache=self.cache, offline=True)
        expected = {str(p.relative_to(self.output)): p.read_bytes() for p in self.output.rglob("*") if p.is_file()}
        actual = {str(p.relative_to(replay)): p.read_bytes() for p in replay.rglob("*") if p.is_file()}
        self.assertEqual(actual, expected)

    def test_incomplete_cache_offline_fails(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network forbidden")):
            with self.assertRaisesRegex(ValueError, "Offline cache miss"):
                prepare.prepare(self.selection, self.output, cache=self.cache, offline=True)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
