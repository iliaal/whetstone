#!/usr/bin/env python3
"""Prepare pinned, file-scoped AACR review inputs without exposing annotations."""

import argparse
import base64
import difflib
import hashlib
import json
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REVISION = "68a569759289a83654a59d06db2a72910edf0a4a"
DATASETS = ("positive_samples.json", "negative_samples.json")
SHA = re.compile(r"[0-9a-f]{40}")
PR = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)/pull/([1-9][0-9]*)")
REPO = re.compile(r"https://github\.com/([\w.-]+/[\w.-]+)")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def safe_path(value):
    require(isinstance(value, str) and value and "\\" not in value,
            f"Invalid repository path: {value!r}")
    require(not value.startswith("/") and all(p not in ("", ".", "..") for p in value.split("/"))
            and not any(ord(c) < 32 for c in value), f"Unsafe repository path: {value!r}")
    return value


def fetch(url, cache=None, offline=False):
    entry = cache / (digest(url.encode()) + ".json") if cache else None
    if entry and entry.exists():
        record = json.loads(entry.read_text())
        data = base64.b64decode(record["body"], validate=True) if record["status"] == 200 else None
        require(record["url"] == url and record["status"] in (200, 404), "Invalid cache entry")
        require(record["sha256"] == (digest(data) if data is not None else None), "Cache hash mismatch")
        return data
    require(not offline, f"Offline cache miss: {url}")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        data = None
    if entry:
        entry.parent.mkdir(parents=True, exist_ok=True)
        record = {"url": url, "status": 200 if data is not None else 404,
                  "sha256": digest(data) if data is not None else None,
                  "body": base64.b64encode(data).decode() if data is not None else ""}
        with entry.open("x") as stream:
            json.dump(record, stream)
    return data


def load_sources(manifest, source_dir, cache, offline):
    require(manifest["source"]["revision"] == REVISION, "Unexpected source revision")
    sources = {}
    receipts = []
    for name in DATASETS:
        spec = manifest["source"]["files"][name]
        expected_url = f"https://raw.githubusercontent.com/alibaba/aacr-bench/{REVISION}/dataset/{name}"
        require(spec["url"] == expected_url, f"Source URL is not pinned: {name}")
        raw = (source_dir / name).read_bytes() if source_dir else fetch(spec["url"], cache, offline)
        require(raw is not None and digest(raw) == spec["sha256"], f"Source hash mismatch: {name}")
        sources[name] = raw
        receipts.append({"url": spec["url"], "sha256": digest(raw)})
    return {name: json.loads(raw) for name, raw in sources.items()}, receipts


def select_cases(manifest, sources):
    require(isinstance(manifest["cases"], list) and manifest["cases"], "No selected cases")
    seen_ids, seen_prs, selections = set(), set(), []
    for case in manifest["cases"]:
        ident = case["id"]
        match = PR.fullmatch(case["pr_url"])
        require(isinstance(ident, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", ident), "Invalid case id")
        require(ident not in seen_ids and case["pr_url"] not in seen_prs, "Duplicate case or PR")
        require(match is not None, "Expected canonical GitHub PR URL")
        safe_path(match.group(1))
        require(case["language"] in ("PHP", "Python", "TypeScript", "JavaScript", "C"), "Unsupported language")
        for field in ("source_commit", "target_commit", "merge_base_commit"):
            require(isinstance(case[field], str) and SHA.fullmatch(case[field]), f"Invalid {field}")
        require(isinstance(case["claims"], list), "claims must be a list")
        require(isinstance(case["context_paths"], list), "context_paths must be a list")
        for path in case["context_paths"]:
            safe_path(path)
        external = case.get("external_context", [])
        require(isinstance(external, list), "external_context must be a list")
        for context in external:
            external_repo = REPO.fullmatch(context["repository"])
            require(external_repo is not None, "Invalid external repository")
            safe_path(external_repo.group(1))
            require(SHA.fullmatch(context["commit"]) is not None, "Invalid external commit")
            require(isinstance(context["version"], str), "Invalid external version")
            require(isinstance(context["paths"], list) and context["paths"], "Missing external paths")
            for path in context["paths"]:
                safe_path(path)
        selected = {}
        for kind, name in zip(("positive", "negative"), DATASETS):
            indices = case[f"{kind}_comment_indices"]
            require(isinstance(indices, list) and all(integer(i) for i in indices), "Invalid comment indices")
            require(len(indices) == len(set(indices)), "Repeated comment index")
            matches = [row for row in sources[name] if row["githubPrUrl"] == case["pr_url"]]
            if not matches and not indices:
                selected[kind] = []
                continue
            require(len(matches) == 1, f"Expected one {kind} source record for {ident}")
            row = matches[0]
            require(row["project_main_language"] == case["language"], f"Language mismatch for {ident}")
            require(row["source_commit"] == case["source_commit"] and row["target_commit"] == case["target_commit"],
                    f"Commit mismatch for {ident}")
            selected[kind] = []
            for index in indices:
                require(0 <= index < len(row["comments"]), f"Comment index out of range: {ident}")
                comment = row["comments"][index]
                safe_path(comment["path"])
                require(comment["side"] in ("left", "right"), "Invalid comment side")
                require(integer(comment["from_line"]) and integer(comment["to_line"])
                        and 1 <= comment["from_line"] <= comment["to_line"], "Invalid comment line range")
                require(kind != "positive" or comment["category"] == "Code Defect", "Positive must be Code Defect")
                selected[kind].append({"index": index, **comment})
        require(selected["positive"] or selected["negative"], "Case selects no comments")
        seen_ids.add(ident)
        seen_prs.add(case["pr_url"])
        selections.append((case, match.group(1), selected))
    return selections


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def prepare(selection, output, source_dir=None, cache=None, offline=False):
    require(not output.exists() and not output.is_symlink(), f"Output already exists: {output}")
    require(output.parent.is_dir(), "Output parent must exist")
    manifest_bytes = selection.read_bytes()
    manifest = json.loads(manifest_bytes)
    sources, receipts = load_sources(manifest, source_dir, cache, offline)
    cases = select_cases(manifest, sources)
    license_bytes = None
    if "license" in manifest["source"]:
        license_spec = manifest["source"]["license"]
        require(license_spec["url"] == f"https://raw.githubusercontent.com/alibaba/aacr-bench/{REVISION}/LICENSE",
                "License URL is not pinned")
        license_bytes = fetch(license_spec["url"], cache, offline)
        require(license_bytes is not None and digest(license_bytes) == license_spec["sha256"], "License hash mismatch")
        receipts.append({"url": license_spec["url"], "sha256": digest(license_bytes)})
    inputs, labels = [], []
    with tempfile.TemporaryDirectory(prefix=".aacr-", dir=output.parent) as temp:
        stage = Path(temp) / "bundle"
        reviewer, refs = stage / "reviewer", stage / "refs"
        reviewer.mkdir(parents=True)
        refs.mkdir()
        if license_bytes is not None:
            (refs / "LICENSE.aacr-bench").write_bytes(license_bytes)
        for case, repo, comments in cases:
            ident = case["id"]
            case_dir = reviewer / ident
            case_dir.mkdir()
            annotated = {c["path"] for group in comments.values() for c in group}
            contents, files, patch = {}, [], []
            for path in sorted(annotated | set(case["context_paths"])):
                versions, metadata = {}, {"path": path, "role": "review" if path in annotated else "context"}
                for side, commit in (("base", case["merge_base_commit"]), ("head", case["target_commit"])):
                    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{urllib.parse.quote(path, safe='/')}"
                    raw = fetch(url, cache, offline)
                    receipts.append({"url": url, "sha256": digest(raw) if raw is not None else None,
                                     "status": 200 if raw is not None else 404})
                    versions[side] = raw.decode("utf-8") if raw is not None else None
                    metadata[side] = f"{ident}/{side}/{path}" if raw is not None else None
                    if raw is not None:
                        destination = case_dir / side / path
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(raw)
                require(any(value is not None for value in versions.values()), f"Both versions missing: {path}")
                contents[path] = versions
                files.append(metadata)
                if path in annotated:
                    lines = difflib.unified_diff((versions["base"] or "").splitlines(keepends=True),
                                                 (versions["head"] or "").splitlines(keepends=True),
                                                 fromfile=f"a/{path}" if versions["base"] is not None else "/dev/null",
                                                 tofile=f"b/{path}" if versions["head"] is not None else "/dev/null")
                    for line in lines:
                        patch.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
            for kind, group in comments.items():
                for comment in group:
                    versions = contents[comment["path"]]
                    text = versions["base" if comment["side"] == "left" else "head"]
                    require(text is not None and comment["to_line"] <= len(text.splitlines()),
                            f"Comment anchor outside file: {ident} {kind} {comment['index']}")
                    require(kind != "positive" or versions["base"] != versions["head"],
                            f"Positive path unchanged: {ident} {comment['path']}")
            (case_dir / "diff.patch").write_text("".join(patch), encoding="utf-8")
            external_inputs = []
            for context in case.get("external_context", []):
                dependency = REPO.fullmatch(context["repository"]).group(1)
                paths = []
                for path in context["paths"]:
                    url = f"https://raw.githubusercontent.com/{dependency}/{context['commit']}/{urllib.parse.quote(path, safe='/')}"
                    raw = fetch(url, cache, offline)
                    require(raw is not None, f"External context missing: {url}")
                    receipts.append({"url": url, "sha256": digest(raw), "status": 200})
                    relative = f"{ident}/external/{dependency}/{context['commit']}/{path}"
                    destination = reviewer / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(raw)
                    paths.append(relative)
                external_inputs.append({"repository": context["repository"], "commit": context["commit"],
                                        "version": context["version"], "paths": paths})
            review_input = {"id": ident, "repo": repo, "base_commit": case["merge_base_commit"],
                           "head_commit": case["target_commit"], "language": case["language"],
                           "scope": "Curated file diff only; not the full PR. Full base/head files include selected context.",
                           "files": files}
            if external_inputs:
                review_input["external_context"] = external_inputs
            inputs.append(review_input)
            labels.append({"id": ident, "pr_url": case["pr_url"], "source_commit": case["source_commit"],
                           "base_commit": case["merge_base_commit"], "head_commit": case["target_commit"],
                           "positive_comments": comments["positive"], "negative_comments": comments["negative"],
                           "claims": case["claims"]})
        write_jsonl(reviewer / "inputs.jsonl", inputs)
        write_jsonl(refs / "labels.jsonl", labels)
        (refs / "selection.json").write_bytes(manifest_bytes)
        (refs / "receipt.json").write_text(json.dumps({"selection_sha256": digest(manifest_bytes),
                                                      "source_revision": REVISION, "downloads": receipts}, indent=2) + "\n")
        require(not output.exists() and not output.is_symlink(), f"Output already exists: {output}")
        stage.rename(output)
    return len(inputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, help="Directory containing the two original pinned dataset files")
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory; parent must exist")
    parser.add_argument("--cache", type=Path, help="Reusable URL-addressed raw download cache")
    parser.add_argument("--offline", action="store_true", help="Require cached downloads; never access the network")
    args = parser.parse_args()
    try:
        count = prepare(Path(__file__).with_name("selection.json"), args.output, args.source_dir, args.cache, args.offline)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")
    print(f"Prepared {count} curated cases in {args.output}; labels are isolated under refs/.")


if __name__ == "__main__":
    main()
