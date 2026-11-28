#!/usr/bin/env python3
"""Build the Claude plugin directory edition of Whetstone.

The directory refuses command hooks, executable or non-text files, and
non-standard frontmatter from community plugins. This edition is generated from
plugins/whetstone; the source plugin, its marketplace entry, and the mirrors are
not changed.
"""

import argparse
import fnmatch
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

PACKAGING = Path("packaging/claude-directory")
TEXT_SUFFIXES = {".md", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico"}
TEXT_NAMES = {"LICENSE"}
LINK = re.compile(r"\]\((\.\.?/[^)\s]+)\)")
FRONTMATTER_KINDS = (
    ("skill", re.compile(r"^skills/[^/]+/SKILL\.md$")),
    ("command", re.compile(r"^commands/[^/]+\.md$")),
    ("agent", re.compile(r"^agents/[^/]+\.md$")),
)


class BuildError(Exception):
    pass


def excluded(relative: str, patterns: list[str]) -> bool:
    parts = PurePosixPath(relative).parts
    for pattern in patterns:
        if pattern.endswith("/"):
            if any(fnmatch.fnmatchcase("/".join(parts[:n]), pattern[:-1]) for n in range(1, len(parts))):
                return True
        elif fnmatch.fnmatchcase(relative, pattern):
            return True
    return False


def tracked_files(repo_root: Path, source: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--", source + "/"],
        cwd=repo_root, check=True, capture_output=True, timeout=30,
    ).stdout.decode("utf-8")
    prefix = source + "/"
    return sorted(p[len(prefix):] for p in out.split("\0") if p)


def scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        return inner.replace("''", "'") if value[0] == "'" else json.loads(value)
    return value


def parse_frontmatter(text: str, relative: str) -> tuple[list[tuple[str, object]], str]:
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise BuildError(f"{relative}: missing frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise BuildError(f"{relative}: unterminated frontmatter") from None
    fields: list[tuple[str, object]] = []
    i = 1
    while i < end:
        line = lines[i]
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(?: (.*))?$", line)
        if not match:
            raise BuildError(f"{relative}:{i + 1}: unsupported frontmatter line: {line!r}")
        key, raw = match.group(1), (match.group(2) or "").strip()
        i += 1
        block = []
        while i < end and (lines[i].startswith(" ") or lines[i] == ""):
            block.append(lines[i])
            i += 1
        if raw in (">-", ">", "|", "|-"):
            joiner = " " if raw.startswith(">") else "\n"
            value: object = joiner.join(b.strip() for b in block if b.strip())
        elif raw == "" and block:
            items = [b.strip() for b in block if b.strip()]
            if not all(item.startswith("- ") for item in items):
                raise BuildError(f"{relative}: unsupported nested value under {key}")
            value = [scalar(item[2:]) for item in items]
        elif block:
            raise BuildError(f"{relative}: unexpected continuation under {key}")
        elif raw.startswith("["):
            value = [scalar(v) for v in raw[1:-1].split(",") if v.strip()]
        else:
            value = scalar(raw)
        fields.append((key, value))
    return fields, "\n".join(lines[end + 1:])


def emit_value(value: object) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(json.dumps(v) for v in value) + "]"
    text = str(value)
    if text in ("true", "false") or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._/-]*", text):
        return text
    return json.dumps(text, ensure_ascii=False)


def normalize_frontmatter(relative: str, text: str, allowed: dict[str, list[str]]) -> tuple[str, list[str]]:
    kind = next((k for k, pattern in FRONTMATTER_KINDS if pattern.match(relative)), None)
    if kind is None:
        return text, []
    fields, body = parse_frontmatter(text, relative)
    keep = [(k, v) for k, v in fields if k in allowed[kind]]
    dropped = [k for k, _ in fields if k not in allowed[kind]]
    if not any(k == "description" for k, _ in keep):
        raise BuildError(f"{relative}: no description")
    head = "\n".join(f"{k}: {emit_value(v)}" for k, v in keep)
    return f"---\n{head}\n---\n{body}", dropped


def apply_patches(stage: Path, patches: list[Path]) -> None:
    for patch in patches:
        result = subprocess.run(
            ["git", "apply", "--whitespace=nowarn", "-p1", str(patch.resolve())],
            cwd=stage, capture_output=True, text=True, timeout=30,
        )
        if result.returncode:
            raise BuildError(f"{patch.name} no longer applies; re-author it against the source:\n{result.stderr.strip()}")


def validate(stage: Path, manifest: dict, removed_names: set[str]) -> list[str]:
    problems = []
    files = sorted(p for p in stage.rglob("*") if p.is_file())
    for path in files:
        relative = path.relative_to(stage).as_posix()
        if path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            problems.append(f"{relative}: file type not accepted by the directory")
            continue
        data = path.read_bytes()
        if data.startswith(b"#!"):
            problems.append(f"{relative}: starts with #!")
        if path.suffix not in {".md", ".json"} and path.name not in TEXT_NAMES:
            if b"PK\x03\x04" in data:
                problems.append(f"{relative}: image holds a zip signature")
            continue
        if b"\0" in data:
            problems.append(f"{relative}: NUL byte")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{relative}: not UTF-8")
            continue
        if path.name in {"hooks.json", ".mcp.json", ".lsp.json", "monitors.json"} or path.name.lower() in {"claude.md", "agents.md", "claude.local.md"}:
            problems.append(f"{relative}: file name refused by the directory")
        for lineno, line in enumerate(text.splitlines(), 1):
            for needle in manifest["forbidden_text"]:
                if needle in line:
                    problems.append(f"{relative}:{lineno}: mentions {needle}")
            for name in removed_names:
                if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", line):
                    problems.append(f"{relative}:{lineno}: mentions omitted file {name}")
        if path.suffix == ".md":
            for target in LINK.findall(text):
                target_path = target.split("#", 1)[0]
                if target_path and not (path.parent / target_path).resolve().is_file():
                    problems.append(f"{relative}: broken link {target}")
    plugin = json.loads((stage / ".claude-plugin/plugin.json").read_text())
    for key in ("mcpServers", "hooks", "lspServers", "monitors"):
        if key in plugin:
            problems.append(f".claude-plugin/plugin.json: declares {key}")
    return problems


def build(repo_root: Path, stage: Path) -> dict:
    manifest = json.loads((repo_root / PACKAGING / "manifest.json").read_text())
    source = repo_root / manifest["source"]
    removed_names: set[str] = set()
    dropped_keys: dict[str, int] = {}
    counts = {"agents": 0, "commands": 0, "skills": 0}
    for relative in tracked_files(repo_root, manifest["source"]):
        if excluded(relative, manifest["exclude"]):
            name = PurePosixPath(relative).name
            if relative.startswith(("commands/scripts/", "scripts/")) or re.match(r"^skills/[^/]+/scripts/", relative):
                removed_names.add(name)
            continue
        path = source / relative
        if path.is_symlink() or not path.is_file():
            raise BuildError(f"{relative}: not a regular file")
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    apply_patches(stage, sorted((repo_root / PACKAGING / "patches").glob("*.patch")))

    for path in sorted(stage.rglob("*.md")):
        relative = path.relative_to(stage).as_posix()
        text, dropped = normalize_frontmatter(relative, path.read_text(encoding="utf-8"), manifest["frontmatter_keys"])
        for key in dropped:
            dropped_keys[key] = dropped_keys.get(key, 0) + 1
        path.write_text(text, encoding="utf-8")
        if re.match(r"^agents/[^/]+\.md$", relative):
            counts["agents"] += 1
        elif re.match(r"^commands/[^/]+\.md$", relative):
            counts["commands"] += 1
        elif re.match(r"^skills/[^/]+/SKILL\.md$", relative):
            counts["skills"] += 1

    source_plugin = json.loads((source / ".claude-plugin/plugin.json").read_text())
    plugin = {k: v for k, v in source_plugin.items() if k not in ("mcpServers", "hooks", "description")}
    plugin = {"name": plugin.pop("name"), "version": plugin.pop("version"),
              "description": manifest["plugin_description"].format(**counts), **plugin}
    (stage / ".claude-plugin/plugin.json").write_text(json.dumps(plugin, indent=2) + "\n")
    shutil.copyfile(repo_root / PACKAGING / "README.md", stage / "README.md")

    problems = validate(stage, manifest, removed_names)
    if problems:
        raise BuildError("directory edition fails its checks:\n  " + "\n  ".join(problems))
    return {"counts": counts, "dropped_keys": dropped_keys, "output": manifest["output"]}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="Build and validate without writing the edition")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "whetstone"
        try:
            result = build(repo_root, stage)
        except (BuildError, OSError, ValueError, subprocess.SubprocessError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        output = repo_root / result["output"]
        if args.check:
            print(f"Directory edition builds and passes its checks ({result['output']} not written)")
            return 0
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, output)
    c = result["counts"]
    print(f"Built {result['output']}: {c['agents']} agents, {c['commands']} commands, {c['skills']} skills; "
          f"dropped frontmatter keys: {result['dropped_keys'] or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
