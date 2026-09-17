#!/usr/bin/env python3
"""Experimental, bounded symbol context from a pinned CodeSage structural index."""

import argparse
import difflib
import hashlib
import json
import posixpath
import re
import sqlite3
import subprocess
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import quote


DEFAULT_BUDGET = 7000
MAX_DEPENDENCY_EDGES = 3
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".c", ".h", ".cc", ".cpp", ".hpp")
SYMBOL_KINDS = {"function", "method", "class", "struct", "interface", "enum", "macro", "constant"}
BARE_CALL_KINDS = {"function", "class", "macro"}
PATH_PART = re.compile(r"^[^\x00-\x1f\\]+$")


def safe_path(value):
    if (not isinstance(value, str) or not value or value.startswith("/")
            or not PATH_PART.fullmatch(value)
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise ValueError(f"Unsafe repository path: {value!r}")
    return value


def run_git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)
    return result.stdout


def git_blob(root, commit, path):
    path = safe_path(path)
    entries = run_git(root, "ls-tree", "-z", "--full-tree", commit, "--", path)
    if not any(entry.split(b"\t", 1)[-1].decode("utf-8") == path
               for entry in entries.split(b"\0") if entry):
        return None
    return run_git(root, "cat-file", "blob", f"{commit}:{path}")


def lf_lines(text):
    if "\r" in text.replace("\r\n", ""):
        raise ValueError("Bare CR makes indexed line numbers ambiguous")
    if not text:
        return []
    lines = text.split("\n")
    return lines[:-1] if not lines[-1] else lines


def lf_raw_lines(raw):
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ValueError("Bare CR makes indexed line numbers ambiguous")
    if not raw:
        return []
    lines = raw.split(b"\n")
    return [line + b"\n" for line in lines[:-1]] + ([lines[-1]] if lines[-1] else [])


def changed_head_lines(before, after):
    old = lf_lines(before)
    new = lf_lines(after)
    result = set()
    for tag, _, _, start, end in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag in ("replace", "insert"):
            result.update(range(start + 1, end + 1))
        elif tag == "delete" and new:
            result.add(min(start + 1, len(new)))
    return result


def byte_length(text):
    return len(text.encode("utf-8"))


class Index:
    """Small read-only adapter for the pinned CodeSage internal SQLite schema."""

    def __init__(self, root, expected_sha):
        self.root = Path(root)
        actual = run_git(self.root, "rev-parse", "HEAD").decode().strip()
        if actual != expected_sha:
            raise ValueError(f"Git HEAD mismatch: expected {expected_sha}, got {actual}")
        db = (self.root / ".codesage" / "index.db").resolve()
        if not db.is_file():
            raise ValueError(f"Missing pinned CodeSage index: {db}")
        self.db = sqlite3.connect(f"file:{quote(str(db))}?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA query_only=ON")
        self.db.execute("BEGIN")
        required = {"files": {"id", "path", "content_hash"},
                    "symbols": {"id", "file_id", "name", "qualified_name", "kind", "line_start", "line_end"},
                    "refs": {"from_file_id", "from_symbol", "to_name", "to_name_tail", "kind", "line", "col"},
                    "structural_index_state": {"last_sha"}}
        for table, columns in required.items():
            actual_columns = {row["name"] for row in self.db.execute(f"PRAGMA table_info({table})")}
            if not columns <= actual_columns:
                raise ValueError(f"Unsupported pinned CodeSage schema: {table}")
        state = self.db.execute("SELECT last_sha FROM structural_index_state WHERE id=1").fetchone()
        if state is None or state[0] != expected_sha:
            raise ValueError("CodeSage structural index does not match Git HEAD")
        self.files = {row["path"]: dict(row) for row in self.db.execute(
            "SELECT id, path, content_hash FROM files")}
        self._verified = {}
        self._raw = {}
        self._hashes = {}
        self._symbols = {}
        self._refs = {}
        self._distance = {}

    def close(self):
        self.db.close()

    def source(self, path):
        safe_path(path)
        if path in self._verified:
            return self._verified[path]
        row = self.files.get(path)
        if row is None:
            raise ValueError(f"File absent from structural index: {path}")
        raw = (self.root / path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != row["content_hash"]:
            raise ValueError(f"Index content hash mismatch: {path}")
        tracked = run_git(self.root, "cat-file", "blob", f"HEAD:{path}")
        if raw != tracked:
            raise ValueError(f"Source differs from Git HEAD: {path}")
        text = raw.decode("utf-8")
        self._verified[path] = text
        self._raw[path] = raw
        self._hashes[path] = digest
        return text

    def raw(self, path):
        self.source(path)
        return self._raw[path]

    def blob_hash(self, path):
        self.source(path)
        return self._hashes[path]

    def symbols(self, path):
        if path not in self._symbols:
            row = self.files.get(path)
            if row is None:
                return []
            self._symbols[path] = [dict(x) | {"path": path} for x in self.db.execute(
                "SELECT id, name, qualified_name, kind, line_start, line_end "
                "FROM symbols WHERE file_id=? ORDER BY line_start, line_end, id", (row["id"],))]
        return self._symbols[path]

    def refs(self, path):
        if path not in self._refs:
            row = self.files.get(path)
            if row is None:
                return []
            self._refs[path] = [dict(x) for x in self.db.execute(
                "SELECT from_symbol, to_name, to_name_tail, kind, line, col "
                "FROM refs WHERE from_file_id=? ORDER BY line, to_name, kind", (row["id"],))]
        return self._refs[path]

    def dependency_targets(self, path):
        parent = Path(path).parent
        targets = set()
        for ref in self.refs(path):
            if ref["kind"] not in ("import", "include"):
                continue
            name = ref["to_name"].strip().strip('"<>')
            if not name or name.startswith("@"):
                continue
            stems = []
            if name.startswith("."):
                if name.startswith("./") or name.startswith("../"):
                    stems.append((parent / name).as_posix())
                elif path.endswith(".py"):
                    dots = len(name) - len(name.lstrip("."))
                    base = parent
                    for _ in range(dots - 1):
                        base = base.parent
                    stems.append((base / name[dots:].replace(".", "/")).as_posix())
            elif "/" in name or name.endswith(CODE_SUFFIXES):
                stems.extend(((parent / name).as_posix(), name))
            elif path.endswith(".py"):
                stems.extend(((parent / name.replace(".", "/")).as_posix(), name.replace(".", "/")))
            else:
                stems.append((parent / name).as_posix())
            for stem in stems:
                normalized = posixpath.normpath(stem)
                if normalized == ".." or normalized.startswith("../") or normalized.startswith("/"):
                    continue
                forms = {normalized}
                if not normalized.endswith(CODE_SUFFIXES):
                    forms.update(normalized + suffix for suffix in CODE_SUFFIXES)
                    forms.update(normalized + "/index" + suffix for suffix in CODE_SUFFIXES)
                    forms.add(normalized + "/__init__.py")
                targets.update(forms & self.files.keys())
        return sorted(targets - {path})

    def distances(self, path):
        if path not in self._distance:
            distances = {path: 0}
            queue = deque([path])
            while queue:
                current = queue.popleft()
                if distances[current] >= MAX_DEPENDENCY_EDGES:
                    continue
                for target in self.dependency_targets(current):
                    if target not in distances:
                        distances[target] = distances[current] + 1
                        queue.append(target)
            self._distance[path] = distances
        return self._distance[path]

    def resolve(self, caller, name, qualified=False):
        tail = name.rsplit(".", 1)[-1]
        for distance in range(MAX_DEPENDENCY_EDGES + 1):
            matches = [symbol for path, steps in self.distances(caller).items() if steps == distance
                       for symbol in self.symbols(path)
                       if ((symbol["qualified_name"] == name and symbol["kind"] in BARE_CALL_KINDS | {"method"})
                           if qualified else (symbol["name"] == tail and symbol["kind"] in BARE_CALL_KINDS))]
            if matches:
                matches.sort(key=lambda s: (s["path"], s["line_start"], s["line_end"], s["id"]))
                return distance, matches
        return None, []


def enclosing_symbol(symbols, line):
    candidates = [symbol for symbol in symbols if symbol["line_start"] <= line <= symbol["line_end"]
                  and symbol["kind"] in SYMBOL_KINDS]
    return min(candidates, key=lambda s: (s["line_end"] - s["line_start"], s["line_start"], s["id"])) if candidates else None


def call_suffix(suffix, decorated):
    suffix = suffix.lstrip()
    if suffix.startswith("("):
        return True
    if decorated and (not suffix or suffix.startswith("#")):
        return True
    if not suffix.startswith("<"):
        return False
    depth = 0
    for offset, char in enumerate(suffix):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return suffix[offset + 1:].lstrip().startswith("(")
        elif char in ";{}":
            return False
    return False


def call_receiver(line, ref):
    names = (ref["to_name"], ref["to_name_tail"] or ref["to_name"])
    col = ref["col"]
    match = None
    if col >= 0:
        for name in names:
            if line[col:col + len(name)] == name and call_suffix(
                    line[col + len(name):], line[:col].rstrip().endswith("@")):
                match = (line[:col].rstrip(), name)
                break
        if match is None:
            raw = line.encode("utf-8")
            for name in names:
                encoded = name.encode("utf-8")
                if raw[col:col + len(encoded)] != encoded:
                    continue
                prefix = raw[:col].decode("utf-8").rstrip()
                suffix = raw[col + len(encoded):].decode("utf-8")
                if call_suffix(suffix, prefix.endswith("@")):
                    match = (prefix, name)
                    break
    if match is None:
        return "call-site-mismatch"
    prefix, matched_name = match
    if "::" in matched_name and matched_name == ref["to_name"] and not prefix.endswith((".", "->", "::")):
        return "qualified-call"
    for operator in ("->", "::", "."):
        if prefix.endswith(operator):
            before = prefix[:-len(operator)].rstrip()
            receiver = re.search(r"[A-Za-z_$][A-Za-z0-9_$]*$", before)
            if receiver is None:
                return "untyped-receiver"
            previous = before[:receiver.start()].rstrip()
            if receiver.group() in ("self", "this") and not previous.endswith((".", "->", "::")):
                return "local-receiver"
            return "untyped-receiver"
    if "." in matched_name:
        return "untyped-receiver"
    return "bare-call"


def build_context(case, reviewer_root, source_root, budget=DEFAULT_BUDGET):
    if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
        raise ValueError("Budget must be a nonnegative integer")
    ident = safe_path(case["id"])
    reviewer_root = Path(reviewer_root)
    index = Index(source_root, case["head_commit"])
    try:
        base_commit = case["base_commit"]
        if run_git(source_root, "cat-file", "-t", base_commit).strip() != b"commit":
            raise ValueError(f"Invalid base commit: {base_commit}")
        queues = defaultdict(list)
        issues = []
        seen_sites = set()
        changed_paths = []
        for file in sorted(case["files"], key=lambda item: item["path"]):
            if file["role"] != "review":
                continue
            path = safe_path(file["path"])
            changed_paths.append(path)
            base_blob = git_blob(source_root, base_commit, path)
            if file["base"] is None:
                if base_blob is not None:
                    raise ValueError(f"Prepared base is absent but Git base has file: {path}")
                base = ""
            else:
                base_raw = (reviewer_root / safe_path(file["base"])).read_bytes()
                if base_blob != base_raw:
                    raise ValueError(f"Prepared base differs from Git base: {path}")
                base = base_raw.decode("utf-8")
            if file["head"] is None:
                if git_blob(source_root, case["head_commit"], path) is not None:
                    raise ValueError(f"Prepared head is absent but Git HEAD has file: {path}")
                issues.append({"reason": "deleted-file", "path": path})
                continue
            head_path = safe_path(file["head"])
            head_raw = (reviewer_root / head_path).read_bytes()
            if head_raw != index.raw(path):
                raise ValueError(f"Prepared head differs from verified source: {path}")
            head = head_raw.decode("utf-8")
            changed = changed_head_lines(base, head)
            symbols = index.symbols(path)
            refs = index.refs(path)
            enclosing = {}
            for line in sorted(changed):
                symbol = enclosing_symbol(symbols, line)
                if symbol is not None:
                    enclosing[symbol["id"]] = symbol
            direct_calls = [ref for ref in refs if ref["kind"] == "call" and ref["line"] in changed]
            if changed and not enclosing and not direct_calls:
                issues.append({"reason": "no-indexed-symbol-or-call", "path": path})
            for ref in direct_calls:
                site = (path, ref["line"], ref["col"], ref["to_name"], ref["from_symbol"])
                if site in seen_sites:
                    continue
                seen_sites.add(site)
                queues[path].append((0, ref["line"], "changed-line call", ref, None))
            for symbol in sorted(enclosing.values(), key=lambda s: (s["line_start"], s["id"])):
                queues[path].append((1, symbol["line_start"], "changed symbol", None, symbol))
                for ref in refs:
                    if ref["kind"] != "call" or not symbol["line_start"] <= ref["line"] <= symbol["line_end"]:
                        continue
                    site = (path, ref["line"], ref["col"], ref["to_name"], ref["from_symbol"])
                    if site in seen_sites:
                        continue
                    seen_sites.add(site)
                    queues[path].append((2, ref["line"], "enclosing-symbol call", ref, None))
            queues[path].sort(key=lambda item: (item[0], item[1], item[3]["to_name"] if item[3] else ""))

        header = (f"Experimental symbol context | case={ident} | head={case['head_commit']}\n"
                  "Source: pinned CodeSage internal index, verified against Git blobs and file hashes.\n"
                  "Call links are name-based candidates; receiver types are not inferred.\n")
        if byte_length(header) > budget:
            return {"id": ident, "context": "", "bytes": 0, "selected": [],
                    "issues": issues + [{"reason": "budget-header", "budget": budget}]}
        text = header
        selected = []
        emitted = set()
        ordered = deque()
        for priority in range(3):
            grouped = {path: [item for item in queues[path] if item[0] == priority] for path in changed_paths}
            for offset in range(max((len(items) for items in grouped.values()), default=0)):
                for path in changed_paths:
                    if offset < len(grouped[path]):
                        ordered.append((path, grouped[path][offset]))
        while ordered:
            for _ in changed_paths:
                if not ordered:
                    break
                path, (rank, line, origin, ref, symbol) = ordered.popleft()
                distance = 0
                if ref is not None:
                    name = ref["to_name_tail"] or ref["to_name"]
                    source_lines = lf_lines(index.source(path))
                    if not 1 <= line <= len(source_lines):
                        issues.append({"reason": "call-site-mismatch", "path": path, "line": line, "name": name})
                        continue
                    receiver = call_receiver(source_lines[line - 1], ref)
                    if receiver in ("untyped-receiver", "call-site-mismatch"):
                        issues.append({"reason": receiver, "path": path, "line": line, "name": name,
                                       "origin": origin})
                        continue
                    if receiver == "local-receiver":
                        owner = (ref["from_symbol"] or "").rsplit(".", 1)
                        qualified = owner[0] + "." + name if len(owner) == 2 else None
                        matches = [candidate for candidate in index.symbols(path)
                                   if candidate["qualified_name"] == qualified and candidate["kind"] == "method"]
                    elif receiver == "qualified-call":
                        distance, matches = index.resolve(path, ref["to_name"], qualified=True)
                    else:
                        distance, matches = index.resolve(path, name)
                    if not matches:
                        issues.append({"reason": "unresolved", "path": path, "line": line, "name": name,
                                       "origin": origin, "receiver": receiver})
                        continue
                    if len(matches) > 1:
                        issues.append({"reason": "ambiguous", "path": path, "line": line, "name": name,
                                       "origin": origin, "distance": distance,
                                       "candidates": [f"{s['path']}:{s['line_start']}-{s['line_end']}" for s in matches]})
                        continue
                    symbol = matches[0]
                key = (symbol["path"], symbol["line_start"], symbol["line_end"])
                if key in emitted:
                    continue
                try:
                    lines = lf_lines(index.source(symbol["path"]))
                except (ValueError, OSError, UnicodeError, subprocess.CalledProcessError) as error:
                    issues.append({"reason": "provenance", "path": symbol["path"], "detail": str(error)})
                    continue
                start, end = symbol["line_start"], symbol["line_end"]
                if start < 1 or end < start or end > len(lines):
                    issues.append({"reason": "invalid-span", "path": symbol["path"], "start": start, "end": end})
                    continue
                location = f"{symbol['path']}:{start}-{end}"
                source_line = f"{path}:{line}"
                title = f"[{len(selected) + 1}] {location} | {origin} at {source_line}"
                if ref is not None:
                    title += f" -> {ref['to_name']} | name-based candidate, dependency distance={distance}"
                body = "\n".join(f"{number} {lines[number - 1]}" for number in range(start, end + 1))
                block = f"{title}\n{body}\n"
                if byte_length(text + block) > budget - min(320, budget // 10):
                    issues.append({"reason": "budget", "path": symbol["path"], "start": start, "end": end,
                                   "origin": origin, "bytes": byte_length(block)})
                    continue
                emitted.add(key)
                raw_lines = lf_raw_lines(index.raw(symbol["path"]))
                span_hash = hashlib.sha256(b"".join(raw_lines[start - 1:end])).hexdigest()
                selected.append({"path": symbol["path"], "start": start, "end": end, "kind": symbol["kind"],
                                 "name": symbol["qualified_name"], "origin": origin, "source": source_line,
                                 "rank": rank, "dependency_distance": distance,
                                 "resolution_basis": "name-based candidate" if ref is not None else "indexed changed symbol",
                                 "source_blob_sha256": index.blob_hash(symbol["path"]),
                                 "span_sha256": span_hash})
                text += block
        counts = {reason: sum(item["reason"] == reason for item in issues)
                  for reason in sorted({item["reason"] for item in issues})}
        summary = f"Issues: {json.dumps(counts, sort_keys=True)}; full details in issues metadata.\n"
        if byte_length(text + summary) <= budget:
            text += summary
        else:
            issues.append({"reason": "budget-summary"})
        return {"id": ident, "context": text, "bytes": byte_length(text),
                "selected": selected, "issues": issues}
    finally:
        index.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--reviewer-root", type=Path, required=True)
    parser.add_argument("--sources-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error(f"Output already exists: {args.output}")
    if not args.output.parent.is_dir():
        parser.error(f"Output parent does not exist: {args.output.parent}")
    rows = [json.loads(line) for line in args.inputs.read_text(encoding="utf-8").split("\n") if line.strip()]
    result = [build_context(row, args.reviewer_root, args.sources_root / safe_path(row["id"]), args.budget)
              for row in rows]
    with args.output.open("x", encoding="utf-8") as stream:
        for item in result:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
