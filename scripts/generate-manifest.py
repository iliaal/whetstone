#!/usr/bin/env python3
"""Generate .skill-versions.json -- tracks content and pattern hashes per skill.

Computes SHA256 of each skill's SKILL.md, of its whole publishable bundle, and
of its regex pattern block in skill-patterns.sh. Compares against the prior
manifest (if it exists) to determine which skills have changed since the last
release. Unchanged entries preserve their prior *_changed version.

content_hash/content_changed cover SKILL.md only and drive eval staleness
filtering in distiller.py. bundle_hash/bundle_changed cover every file a
publish uploads (SKILL.md, references/, scripts/, assets/) and drive
publish-clawhub.sh change detection, so a references-only edit republishes
without invalidating harvested eval examples.

On first run (no prior manifest), all skills are set to the current plugin
version, establishing a clean baseline for staleness tracking.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "whetstone"
SKILLS_DIR = PLUGIN_DIR / "skills"
PATTERNS_FILE = PLUGIN_DIR / "hooks" / "skill-patterns.sh"
PLUGIN_JSON = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
MANIFEST_PATH = REPO_ROOT / "distillery" / ".skill-versions.json"

# Accepted model prefixes for skill-behavior eval. Sessions whose assistant turns
# don't start with any of these are filtered. Must include each model that legitimately
# runs skills today: opus for main sessions, haiku for built-in subagents (Plan, Explore).
# Env override: SKILL_MODEL_BASELINE (comma-separated prefixes).
MODEL_BASELINE_PREFIXES = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-fable-5", "claude-mythos-5"]


def _sha256_file(path: Path) -> str:
    """SHA256 hex digest of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_files(skill_dir: Path) -> list[str]:
    """Repo-relative paths of the files `git add -A` would commit for a skill dir.

    Tracked plus untracked-but-not-ignored files, so gitignored build artifacts
    (__pycache__, eval results) never change the hash while a new reference file
    added during the release cycle does. Tracked files deleted from the working
    tree are dropped, matching what the release commit will contain.
    """
    out = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z", "--cached", "--others",
         "--exclude-standard", "--", str(skill_dir.relative_to(REPO_ROOT))],
        check=True, capture_output=True,
    ).stdout
    paths = {p.decode() for p in out.split(b"\0") if p}
    return sorted(p for p in paths if (REPO_ROOT / p).is_file())


def _sha256_bundle(skill_dir: Path) -> str:
    """SHA256 over the sorted (skill-relative path, file bytes) pairs of a skill bundle."""
    h = hashlib.sha256()
    for rel in _bundle_files(skill_dir):
        data = (REPO_ROOT / rel).read_bytes()
        name = Path(rel).relative_to(skill_dir.relative_to(REPO_ROOT)).as_posix().encode()
        h.update(len(name).to_bytes(8, "big") + name)
        h.update(len(data).to_bytes(8, "big") + data)
    return h.hexdigest()


def _sha256_string(text: str) -> str:
    """SHA256 hex digest of a normalized string (whitespace-collapsed)."""
    normalized = re.sub(r"\s+", " ", text.strip())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _extract_pattern_block(skill_name: str, patterns_content: str) -> str | None:
    """Extract a skill's trigger regexes from skill-patterns.sh content.

    Concatenates SKILL_PATTERNS with any SKILL_NEGATIVE entry, because a
    suppression change alters which prompts fire the skill just as a positive
    change does, and staleness filtering keys off this hash.
    """
    m = re.search(rf"SKILL_PATTERNS\[{re.escape(skill_name)}\]='([^']+)'", patterns_content)
    if not m:
        m = re.search(rf'SKILL_PATTERNS\[{re.escape(skill_name)}\]="([^"]+)"', patterns_content)
    if not m:
        return None
    pattern = m.group(1)

    n = re.search(rf"SKILL_NEGATIVE\[{re.escape(skill_name)}\]='([^']+)'", patterns_content)
    if not n:
        n = re.search(rf'SKILL_NEGATIVE\[{re.escape(skill_name)}\]="([^"]+)"', patterns_content)
    return f"{pattern}\x00!{n.group(1)}" if n else pattern


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

    prior = {}
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH) as f:
            prior = json.load(f).get("skills", {})

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

        content_hash = _sha256_file(skill_file)
        bundle_hash = _sha256_bundle(skill_dir)

        pattern_text = _extract_pattern_block(skill_name, patterns_content)
        pattern_hash = _sha256_string(pattern_text) if pattern_text else None

        prev = prior.get(skill_name, {})
        prev_content_hash = prev.get("content_hash")
        prev_pattern_hash = prev.get("pattern_hash")

        content_changed = prev.get("content_changed", version)
        if prev_content_hash != content_hash:
            content_changed = version

        # A prior manifest without bundle_hash (pre-bundle format) stamps every
        # skill at the current version once, so the next publish re-uploads all
        # bundles and repairs references-only edits earlier releases skipped.
        bundle_changed = prev.get("bundle_changed", version)
        if prev.get("bundle_hash") != bundle_hash:
            bundle_changed = version

        pattern_changed = prev.get("pattern_changed", version)
        if pattern_hash is not None and prev_pattern_hash != pattern_hash:
            pattern_changed = version

        entry = {
            "content_hash": content_hash,
            "content_changed": content_changed,
            "bundle_hash": bundle_hash,
            "bundle_changed": bundle_changed,
        }
        if pattern_hash is not None:
            entry["pattern_hash"] = pattern_hash
            entry["pattern_changed"] = pattern_changed

        skills[skill_name] = entry

    env_baseline = os.environ.get("SKILL_MODEL_BASELINE")
    if env_baseline:
        model_baseline = [p.strip() for p in env_baseline.split(",") if p.strip()]
    else:
        model_baseline = list(MODEL_BASELINE_PREFIXES)

    return {
        "plugin_version": version,
        "model_baseline_prefixes": model_baseline,
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
