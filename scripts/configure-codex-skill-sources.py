#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
import tomllib


BEGIN_MARKER = "# BEGIN WHETSTONE CODEX SKILL SOURCE EXCLUSIONS"
END_MARKER = "# END WHETSTONE CODEX SKILL SOURCE EXCLUSIONS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Disable direct Whetstone skill sources when the native Codex plugin owns them."
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the managed exclusions when the native plugin is inactive.",
    )
    return parser.parse_args()


def skill_paths(repo_root: Path) -> list[Path]:
    skills_root = repo_root / "plugins" / "whetstone" / "skills"
    return sorted(
        path.resolve()
        for path in skills_root.glob("*/SKILL.md")
        if path.is_file()
    )


def render_block(paths: list[Path]) -> str:
    lines = [
        BEGIN_MARKER,
        "# The native Whetstone plugin supplies these skills from its versioned cache.",
        "# Disable the same sources reached through ~/.agents/skills to avoid duplicates.",
    ]
    for path in paths:
        lines.extend(
            [
                "",
                "[[skills.config]]",
                f"path = {json.dumps(str(path))}",
                "enabled = false",
            ]
        )
    lines.extend([END_MARKER, ""])
    return "\n".join(lines)


def replace_managed_block(text: str, block: str) -> str:
    begin_count = text.count(BEGIN_MARKER)
    end_count = text.count(END_MARKER)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("config.toml has an incomplete or duplicated Whetstone managed block")

    if begin_count == 1:
        start = text.index(BEGIN_MARKER)
        end = text.index(END_MARKER, start) + len(END_MARKER)
        return f"{text[:start].rstrip()}\n\n{block}{text[end:].lstrip()}"

    if not text:
        return block
    return f"{text.rstrip()}\n\n{block}"


def remove_managed_block(text: str) -> str:
    begin_count = text.count(BEGIN_MARKER)
    end_count = text.count(END_MARKER)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("config.toml has an incomplete or duplicated Whetstone managed block")
    if begin_count == 0:
        return text

    start = text.index(BEGIN_MARKER)
    end = text.index(END_MARKER, start) + len(END_MARKER)
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    if before and after:
        return f"{before}\n\n{after}"
    if before:
        return f"{before}\n"
    return after


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else None
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    if mode is not None:
        temporary.chmod(mode)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    config_link = args.codex_home.expanduser().resolve() / "config.toml"
    if config_link.is_symlink():
        try:
            config_path = config_link.resolve(strict=True)
        except FileNotFoundError as exc:
            raise SystemExit(f"refusing to replace dangling config symlink: {config_link}") from exc
    else:
        config_path = config_link
    current = config_path.read_text() if config_path.exists() else ""
    updated = (
        remove_managed_block(current)
        if args.remove
        else replace_managed_block(current, render_block(skill_paths(repo_root)))
    )
    tomllib.loads(updated)

    if args.dry_run:
        print(updated, end="")
        return
    if updated != current:
        atomic_write(config_path, updated)
    action = "Removed" if args.remove else "Configured"
    print(f"{action} Whetstone Codex skill-source exclusions in {config_path}")


if __name__ == "__main__":
    main()
