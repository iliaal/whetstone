#!/usr/bin/env python3
"""Build Whetstone's skills-only OpenAI submission ZIP."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def package_files(repo_root: Path) -> dict[str, bytes]:
    plugin_root = repo_root / "plugins/whetstone"
    source_manifest = json.loads((plugin_root / ".codex-plugin/plugin.json").read_text())
    manifest = {
        key: source_manifest[key]
        for key in (
            "name", "version", "description", "author", "homepage",
            "repository", "license", "keywords",
        )
        if key in source_manifest
    }
    manifest["interface"] = json.loads(
        (repo_root / "packaging/openai/interface.json").read_text()
    )
    manifest["skills"] = "./skills/"
    if len(manifest["interface"]["shortDescription"]) > 30:
        raise ValueError("Public short description exceeds 30 characters")

    tracked = subprocess.run(
        ["git", "ls-files", "-z", "--", "plugins/whetstone/skills/"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8").split("\0")
    files = {
        ".codex-plugin/plugin.json": (json.dumps(manifest, indent=2) + "\n").encode(),
        "assets/whetstone.svg": (repo_root / "packaging/openai/whetstone.svg").read_bytes(),
        "LICENSE": (plugin_root / "LICENSE").read_bytes(),
    }
    for relative in tracked:
        if not relative:
            continue
        path = repo_root / relative
        if path.name == "SPEC.md":
            continue
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Skill resource must be a regular file: {relative}")
        files[path.relative_to(plugin_root).as_posix()] = path.read_bytes()
    if not any(name.endswith("/SKILL.md") for name in files):
        raise ValueError("Package has no tracked skills")
    return files


def build_archive(repo_root: Path, output: Path) -> int:
    files = package_files(repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, contents in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, contents)
    return sum(name.endswith("/SKILL.md") for name in files)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = json.loads(
        (repo_root / "plugins/whetstone/.codex-plugin/plugin.json").read_text()
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / f"dist/openai/whetstone-{manifest['version']}.zip",
        help="Destination ZIP; an existing file is never overwritten",
    )
    args = parser.parse_args()
    try:
        count = build_archive(repo_root, args.output)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Built {args.output.resolve()} with {count} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
