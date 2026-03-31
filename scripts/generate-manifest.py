#!/usr/bin/env python3
"""Generate .skill-versions.json -- tracks content and pattern hashes per skill.

Computes SHA256 of each skill's SKILL.md and its regex pattern block in
skill-patterns.sh. Compares against the prior manifest (if it exists) to
determine which skills have changed since the last release. Unchanged entries
preserve their prior *_changed version.

On first run (no prior manifest), all skills are set to the current plugin
version, establishing a clean baseline for staleness tracking.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "compound-engineering"
SKILLS_DIR = PLUGIN_DIR / "skills"
PATTERNS_FILE = PLUGIN_DIR / "hooks" / "skill-patterns.sh"
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MANIFEST_PATH = REPO_ROOT / "distillery" / ".skill-versions.json"


def _sha256_file(path: Path) -> str:
    """SHA256 hex digest of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_string(text: str) -> str:
    """SHA256 hex digest of a normalized string (whitespace-collapsed)."""
    normalized = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _extract_pattern_block(skill_name: str, patterns_content: str) -> str | None:
    """Extract the regex pattern value for a skill from skill-patterns.sh content."""
    m = re.search(rf"SKILL_PATTERNS\[{re.escape(skill_name)}\]='([^']+)'", patterns_content)
    if not m:
        m = re.search(rf'SKILL_PATTERNS\[{re.escape(skill_name)}\]="([^"]+)"', patterns_content)
    return m.group(1) if m else None


def _read_current_version() -> str:
    """Read current plugin version from plugin.json."""
    with open(PLUGIN_JSON) as f:
        return json.load(f)["version"]


def generate() -> dict:
    """Generate the skill change manifest.

    Reads the existing manifest (if any), computes current hashes, and updates
    entries where content or patterns have changed. Returns the manifest dict.
    """
    version = _read_current_version()

    # Load existing manifest for comparison
    prior = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            prior = json.load(f).get("skills", {})

    # Read patterns file once
    patterns_content = ""
    if PATTERNS_FILE.exists():
        patterns_content = PATTERNS_FILE.read_text()

    skills = {}
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue

        skill_name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        # Content hash
        content_hash = _sha256_file(skill_file)

        # Pattern hash
        pattern_text = _extract_pattern_block(skill_name, patterns_content)
        pattern_hash = _sha256_string(pattern_text) if pattern_text else None

        # Compare against prior manifest
        prev = prior.get(skill_name, {})
        prev_content_hash = prev.get("content_hash")
        prev_pattern_hash = prev.get("pattern_hash")

        content_changed = prev.get("content_changed", version)
        if prev_content_hash != content_hash:
            content_changed = version

        pattern_changed = prev.get("pattern_changed", version)
        if pattern_hash is not None and prev_pattern_hash != pattern_hash:
            pattern_changed = version

        entry = {
            "content_hash": content_hash,
            "content_changed": content_changed,
        }
        if pattern_hash is not None:
            entry["pattern_hash"] = pattern_hash
            entry["pattern_changed"] = pattern_changed

        skills[skill_name] = entry

    return {
        "plugin_version": version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skills": skills,
    }


def main():
    manifest = generate()
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    skill_count = len(manifest["skills"])
    print(f"Written {skill_count} skills to {MANIFEST_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
