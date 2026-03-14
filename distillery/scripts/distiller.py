#!/usr/bin/env python3
"""Skill distiller helper — mechanical operations for search, fetch, staging, checksums, and manifest management."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from collections import defaultdict
from datetime import date
from pathlib import Path

DISTILLERY_DIR = Path(__file__).resolve().parent.parent
STAGING_DIR = DISTILLERY_DIR / ".skill-distiller" / "sources"
GENERATED_DIR = DISTILLERY_DIR / "generated-skills"
ENV_FILE = DISTILLERY_DIR / ".env"
PLUGIN_DIR = DISTILLERY_DIR.parent / "plugins" / "compound-engineering"
# CWD-relative paths for npx skills add cleanup (fetch creates these in CWD)
SKILLS_AGENT_DIR = Path(".agents/skills")
SKILLS_SYMLINK_DIR = Path(".claude/skills")
GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = "grok-4-1-fast-reasoning"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_TEST_MODELS = [
    "x-ai/grok-4.1-fast",
    "google/gemini-3-flash-preview",
    "moonshotai/kimi-k2.5:moonshotai",
    "anthropic/claude-sonnet-4.5:google-vertex",
]

MIN_INSTALLS = 100
MIN_INSTALLS_FALLBACK = 50
MIN_QUALIFYING = 3
TOP_N = 10

MAX_RETRIES = 2
RETRY_DELAY = 1.0


def _http_request(url, data=None, headers=None, timeout=30, retries=MAX_RETRIES):
    """Make an HTTP request with retries on transient errors. Returns parsed JSON."""
    headers = headers or {}
    headers.setdefault("User-Agent", "skill-distiller/1.0")

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()
            except Exception:
                pass
            # Retry on 429 and 5xx
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"HTTP {e.code} for {url}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {body[:200]}") from e
        except urllib.error.URLError as e:
            if attempt < retries:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"Connection error for {url}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Connection failed: {e.reason}") from e
        except (TimeoutError, OSError) as e:
            if attempt < retries:
                wait = RETRY_DELAY * (2 ** attempt)
                print(f"Timeout for {url}, retrying in {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Request timed out: {e}") from e


def search_skills(queries):
    """Search skills.sh API for each query, filter and deduplicate results."""
    all_skills = {}
    failed_queries = []

    for query in queries:
        encoded = urllib.parse.quote(query)
        url = f"https://skills.sh/api/search?q={encoded}&limit=50"
        try:
            data = _http_request(url)
        except RuntimeError as e:
            print(f"Error: search failed for '{query}': {e}", file=sys.stderr)
            failed_queries.append({"query": query, "error": str(e)})
            continue

        skills = data.get("skills", [])
        for skill in skills:
            sid = skill.get("id")
            if sid and sid not in all_skills:
                all_skills[sid] = {
                    "id": sid,
                    "skillId": skill.get("skillId", ""),
                    "name": skill.get("name", ""),
                    "installs": skill.get("installs", 0),
                    "source": skill.get("source", ""),
                }

    # If ALL queries failed, exit with error
    if failed_queries and not all_skills:
        print(f"Error: all {len(failed_queries)} search queries failed", file=sys.stderr)
        sys.exit(1)

    # Sort by installs descending
    ranked = sorted(all_skills.values(), key=lambda s: s["installs"], reverse=True)

    # Filter: installs >= 100, top 10
    qualified = [s for s in ranked if s["installs"] >= MIN_INSTALLS][:TOP_N]

    # Fallback: if fewer than 3, lower threshold
    if len(qualified) < MIN_QUALIFYING:
        qualified = [s for s in ranked if s["installs"] >= MIN_INSTALLS_FALLBACK][:TOP_N]

    # Include warnings about partial failures in stderr
    if failed_queries and all_skills:
        print(f"Warning: {len(failed_queries)}/{len(queries)} search queries failed: "
              f"{', '.join(q['query'] for q in failed_queries)}", file=sys.stderr)

    return qualified


def _check_npx_skills():
    """Verify npx skills CLI is available. Exits with error if not."""
    try:
        result = subprocess.run(
            ["npx", "skills", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            print(f"Error: 'npx skills' is not available or returned an error: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("Error: 'npx' is not installed or not in PATH", file=sys.stderr)
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: 'npx skills --version' timed out", file=sys.stderr)
        sys.exit(1)


def compute_sha1(filepath):
    """Compute SHA-1 hex digest of a file."""
    h = hashlib.sha1()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_moved_skill(old_id):
    """Search skills.sh for a skill that may have moved repos. Returns new id and source, or None."""
    parts = old_id.split("/")
    if len(parts) < 3:
        return None
    owner = parts[0]
    skill_name = parts[-1]
    encoded = urllib.parse.quote(skill_name)
    url = f"https://skills.sh/api/search?q={encoded}&limit=50"
    try:
        data = _http_request(url)
    except RuntimeError:
        return None
    for s in data.get("skills", []):
        sid = s.get("id", "")
        s_parts = sid.split("/")
        if len(s_parts) >= 3 and s_parts[0] == owner and s_parts[-1] == skill_name:
            new_source = "/".join(s_parts[:2])
            return {"id": sid, "source": new_source, "installs": s.get("installs", 0)}
    return None


def _stage_skill(skill_id):
    """Move a fetched skill to staging and remove symlinks."""
    agent_path = SKILLS_AGENT_DIR / skill_id
    staging_path = STAGING_DIR / skill_id
    symlink_path = SKILLS_SYMLINK_DIR / skill_id

    if agent_path.exists():
        if staging_path.exists():
            shutil.rmtree(staging_path)
        shutil.move(str(agent_path), str(staging_path))

    if symlink_path.is_symlink() or symlink_path.exists():
        if symlink_path.is_dir() and not symlink_path.is_symlink():
            shutil.rmtree(symlink_path)
        else:
            symlink_path.unlink()


def fetch_skills(skills_list):
    """Fetch, stage, and checksum skills. Returns enriched list with sha1 and path."""
    _check_npx_skills()
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    # Group by source
    by_source = defaultdict(list)
    for skill in skills_list:
        by_source[skill["source"]].append(skill)

    fetch_failures = []

    # Fetch each source group
    for source, group in by_source.items():
        skill_ids = [s["skillId"] for s in group]
        # npx skills add requires full GitHub URL
        source_url = source if source.startswith("http") else f"https://github.com/{source}"
        cmd = ["npx", "skills", "add", source_url, "-s"] + skill_ids + ["-y", "--agent", "claude-code"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            err_msg = e.stderr.strip()[:200] if hasattr(e, "stderr") and e.stderr else "timeout" if isinstance(e, subprocess.TimeoutExpired) else "unknown error"
            print(f"Error: fetch failed for {source}: {err_msg}", file=sys.stderr)
            # Try to resolve moved repos
            for skill in group:
                resolved = _resolve_moved_skill(skill["id"])
                if resolved:
                    new_source_url = f"https://github.com/{resolved['source']}"
                    retry_cmd = ["npx", "skills", "add", new_source_url, "-s", skill["skillId"], "-y", "--agent", "claude-code"]
                    print(f"  Resolved: {skill['id']} -> {resolved['id']}", file=sys.stderr)
                    try:
                        subprocess.run(retry_cmd, check=True, capture_output=True, text=True, timeout=120)
                        skill["id"] = resolved["id"]
                        skill["source"] = resolved["source"]
                        skill["installs"] = resolved["installs"]
                        _stage_skill(skill["skillId"])
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        print(f"  Retry also failed for {resolved['id']}", file=sys.stderr)
                        fetch_failures.append({"id": skill["id"], "source": source, "error": err_msg})
                else:
                    fetch_failures.append({"id": skill["id"], "source": source, "error": err_msg})
            continue

        # Move to staging and remove symlinks
        for skill in group:
            _stage_skill(skill["skillId"])

    # If ALL fetches failed, report error (caller decides severity)
    if fetch_failures and len(fetch_failures) == len(skills_list):
        print(f"Error: all {len(fetch_failures)} skill fetches failed", file=sys.stderr)

    # Compute checksums and build result
    results = []
    for skill in skills_list:
        sid = skill["skillId"]
        skill_md = STAGING_DIR / sid / "SKILL.md"
        if skill_md.exists():
            results.append({
                "id": skill["id"],
                "skillId": sid,
                "installs": skill["installs"],
                "sha1": compute_sha1(skill_md),
                "path": str(skill_md),
            })
        else:
            # Check if this was a known fetch failure
            is_known_failure = any(f["id"] == skill["id"] for f in fetch_failures)
            if not is_known_failure:
                results.append({
                    "id": skill["id"],
                    "skillId": sid,
                    "installs": skill["installs"],
                    "status": "missing",
                    "error": f"SKILL.md not found at {skill_md}",
                })

    # Append fetch failures as explicit entries
    for failure in fetch_failures:
        results.append({
            "id": failure["id"],
            "status": "fetch_failed",
            "error": failure["error"],
        })

    # Clean up any leftover artifacts from npx skills add
    # (e.g. skills with colons in IDs that don't match expected paths)
    _cleanup_fetch_artifacts()

    return results


def _cleanup_fetch_artifacts():
    """Remove leftover .agents/ entries and orphan symlinks in .claude/skills/."""
    # Remove any remaining entries in .agents/skills/
    if SKILLS_AGENT_DIR.exists():
        for entry in list(SKILLS_AGENT_DIR.iterdir()):
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        # Remove .agents/skills/ and .agents/ if empty
        try:
            SKILLS_AGENT_DIR.rmdir()
        except OSError:
            pass
        try:
            SKILLS_AGENT_DIR.parent.rmdir()
        except OSError:
            pass

    # Remove symlinks/dirs in .claude/skills/ that point into .agents/
    if SKILLS_SYMLINK_DIR.exists():
        agents_abs = str(SKILLS_AGENT_DIR.parent.resolve())
        for entry in list(SKILLS_SYMLINK_DIR.iterdir()):
            if entry.is_symlink():
                try:
                    target = str(Path(os.readlink(entry)).resolve())
                except OSError:
                    target = ""
                if ".agents" in target or agents_abs in target:
                    entry.unlink()


def check_updates(name):
    """Check for updates to a generated skill. Returns diff report."""
    manifest_path = GENERATED_DIR / name / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    search_queries = manifest.get("search_queries", [manifest.get("query", name)])
    old_sources = {s["id"]: s for s in manifest.get("sources", [])}
    instructions = manifest.get("instructions", None)

    # Re-search
    fresh_skills = search_skills(search_queries)
    fresh_ids = {s["id"] for s in fresh_skills}
    old_ids = set(old_sources.keys())

    # Fetch all (existing + new)
    fetched = fetch_skills(fresh_skills)
    # Separate successful fetches from failures
    fetched_ok = {f["id"]: f for f in fetched if "sha1" in f}
    fetched_failed = [f for f in fetched if f.get("status") in ("fetch_failed", "missing")]

    # Categorize
    unchanged = []
    changed = []
    new_sources = []
    removed = []

    for fid, fdata in fetched_ok.items():
        if fid in old_sources:
            old_sha1 = old_sources[fid].get("sha1")
            if old_sha1 and old_sha1 == fdata["sha1"]:
                unchanged.append({"id": fid, "sha1": fdata["sha1"]})
            else:
                changed.append({
                    "id": fid,
                    "old_sha1": old_sha1 or "unknown",
                    "new_sha1": fdata["sha1"],
                    "path": fdata["path"],
                })
        else:
            new_sources.append({
                "id": fid,
                "installs": fdata["installs"],
                "sha1": fdata["sha1"],
                "path": fdata["path"],
            })

    for oid in old_ids:
        if oid not in fetched_ok and oid not in fresh_ids:
            removed.append({"id": oid})

    # Early exit check
    if not changed and not new_sources and not removed:
        cleanup()
        return {"status": "no_updates"}

    result = {
        "status": "updates_available",
        "unchanged": unchanged,
        "changed": changed,
        "new": new_sources,
        "removed": removed,
    }
    if instructions:
        result["instructions"] = instructions
    if fetched_failed:
        result["fetch_failures"] = fetched_failed

    return result


def update_manifest(name, tok_count, sources_json):
    """Update manifest.json preserving query, search_queries, instructions."""
    manifest_path = GENERATED_DIR / name / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    sources = json.loads(sources_json) if isinstance(sources_json, str) else sources_json

    manifest["generated"] = date.today().isoformat()
    manifest["token_count"] = tok_count
    manifest["sources"] = sources

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    print(f"Updated {manifest_path}", file=sys.stderr)


def token_count(filepath):
    """Estimate token count using byte-based heuristic (better for markdown/code)."""
    size = os.path.getsize(filepath)
    # bytes / 3.5 is more accurate for markdown-heavy content than words * 4/3
    return round(size / 3.5)


def token_budget_report(skill_dir):
    """Token budget with SkillsBench effectiveness rating.

    Optimal SKILL.md: 2K-8K chars (+18.8pp). Over 15K: -2.9pp.
    """
    skill_path = Path(skill_dir) / "SKILL.md"
    refs_dir = Path(skill_dir) / "references"

    if not skill_path.exists():
        return {"error": f"SKILL.md not found in {skill_dir}"}

    body_chars = skill_path.stat().st_size
    body_tokens = round(body_chars / 3.5)

    ref_tokens = {}
    if refs_dir.exists():
        for ref in refs_dir.glob("*.md"):
            ref_tokens[ref.name] = round(ref.stat().st_size / 3.5)

    total = body_tokens + sum(ref_tokens.values())

    if body_chars > 15000:
        rating = "OVER_BUDGET"
    elif body_chars > 8000:
        rating = "VERBOSE"
    elif body_chars >= 2000:
        rating = "OPTIMAL"
    elif body_chars >= 1000:
        rating = "BRIEF"
    else:
        rating = "TOO_SHORT"

    return {
        "body_tokens": body_tokens,
        "body_chars": body_chars,
        "ref_tokens": ref_tokens,
        "total_tokens": total,
        "rating": rating,
    }


def load_env():
    """Load key=value pairs from .env file."""
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip().strip("'\"")
                os.environ.setdefault(key.strip(), value)


def get_engagement_threshold(top_installs):
    """Return minimum likes threshold based on topic popularity."""
    if top_installs >= 10000:
        return 50
    elif top_installs >= 1000:
        return 10
    else:
        return 3


def grok_query(topic, top_installs, instructions=None):
    """Query Grok for recent X posts about a topic. Returns structured insights."""
    load_env()
    api_key = os.environ.get("GROK_API_KEY", "")
    if not api_key:
        print("Error: GROK_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    min_likes = get_engagement_threshold(top_installs)

    system_prompt = f"""Search X (Twitter) posts from the last 30 days about: {topic}

Filters — apply strictly:
- Posts with at least {min_likes} likes only
- Standalone posts and threads only — exclude isolated replies
- Exclude: course/tutorial pitches, hiring posts, self-promotional content ("check out my repo", "just launched")

Extract and return ONLY posts that contain:
- Recent breaking changes or deprecations in {topic}
- Emerging patterns or conventions the community is converging on
- Common pitfalls practitioners are actively reporting
- New tooling gaining real adoption

For each finding, provide:
- The insight (one concise sentence)
- Source context (paraphrased, not verbatim — who said it, approximate engagement)
- Relevance: HIGH / MEDIUM / LOW"""

    if instructions:
        system_prompt += f"\n\nAdditional scope constraints — apply these when filtering results:\n{instructions}"

    system_prompt += """

Output format — return valid JSON only, no markdown wrapping:
{
  "findings": [
    {
      "insight": "...",
      "source_context": "...",
      "relevance": "HIGH|MEDIUM|LOW",
      "category": "breaking_change|emerging_pattern|pitfall|new_tooling"
    }
  ],
  "summary": "One paragraph overview of the current state of practitioner discussion"
}

If no qualifying posts are found, return: {"findings": [], "summary": "No significant recent discussion found."}"""

    payload = json.dumps({
        "model": GROK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"What are the most notable recent developments, best practices, and pitfalls being discussed about {topic} on X in the last 30 days?"},
        ],
        "temperature": 0.1,
    }).encode()

    try:
        data = _http_request(
            GROK_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=120,
        )
    except RuntimeError as e:
        print(f"Error: Grok API request failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Check for API-level errors
    if "error" in data:
        print(f"Error: Grok API returned error: {data['error']}", file=sys.stderr)
        sys.exit(1)

    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    # Parse JSON from response, stripping markdown fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw": content, "findings": [], "summary": "Failed to parse structured response."}


def backfill_sha1(name):
    """Fetch all sources for a skill and add sha1 checksums to the manifest."""
    manifest_path = GENERATED_DIR / name / "manifest.json"
    if not manifest_path.exists():
        print(f"Error: {manifest_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    sources = manifest.get("sources", [])
    # Check if any source already has sha1
    needs_backfill = any("sha1" not in s for s in sources)
    if not needs_backfill:
        print(f"All sources in {name} already have sha1", file=sys.stderr)
        return manifest

    # Build skill list directly from manifest sources (not re-search, which filters)
    skills_for_fetch = []
    for source in sources:
        if "sha1" in source:
            continue  # already has checksum
        sid = source["id"]
        parts = sid.split("/")
        # id format: "owner/repo/skill-name" → source="owner/repo", skillId="skill-name"
        if len(parts) >= 3:
            skills_for_fetch.append({
                "id": sid,
                "skillId": parts[-1],
                "installs": source.get("installs", 0),
                "source": "/".join(parts[:2]),
            })

    if not skills_for_fetch:
        print(f"All sources in {name} already have sha1", file=sys.stderr)
        return manifest

    fetched = fetch_skills(skills_for_fetch)
    fetched_by_id = {f["id"]: f for f in fetched if "sha1" in f}

    # Update sources with sha1
    updated_sources = []
    for source in sources:
        sid = source["id"]
        if "sha1" in source:
            pass  # already has checksum
        elif sid in fetched_by_id:
            source["sha1"] = fetched_by_id[sid]["sha1"]
        else:
            print(f"Warning: could not fetch {sid} for sha1 backfill", file=sys.stderr)
        updated_sources.append(source)

    manifest["sources"] = updated_sources

    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")

    cleanup()
    print(f"Backfilled sha1 for {name}: {sum(1 for s in updated_sources if 'sha1' in s)}/{len(updated_sources)} sources", file=sys.stderr)
    return manifest


def validate(name):
    """Validate a generated skill using multi-gate scoring. Returns JSON with gates, score, and pass/fail."""
    import re
    import yaml  # lazy import — only needed here

    skill_dir = GENERATED_DIR / name
    skill_path = skill_dir / "SKILL.md"
    manifest_path = skill_dir / "manifest.json"
    issues = []
    warnings = []
    gates = {}

    # --- File existence ---
    if not skill_path.exists():
        return {
            "valid": False, "score": 0, "max_score": 7, "passed": False,
            "gates": {"file_exists": {"pass": False, "detail": f"SKILL.md not found at {skill_path}"}},
            "body_tokens": 0, "total_tokens": 0, "issues": [f"SKILL.md not found at {skill_path}"], "warnings": [],
        }

    content = skill_path.read_text()

    # --- Gate 1: YAML frontmatter ---
    frontmatter = {}
    body = content
    gate1_issues = []
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except Exception as e:
                gate1_issues.append(f"Invalid YAML: {e}")
            body = parts[2].strip()
        else:
            gate1_issues.append("Opening --- without closing ---")
    else:
        gate1_issues.append("No YAML frontmatter found")

    inert_fields = {"triggers", "role", "scope", "domain", "output-format", "author",
                    "version", "license", "related-skills", "tags"}
    found_inert = inert_fields & set(frontmatter.keys())
    if found_inert:
        gate1_issues.append(f"Inert fields: {', '.join(sorted(found_inert))}")

    gates["frontmatter"] = {"pass": len(gate1_issues) == 0, "detail": "; ".join(gate1_issues) if gate1_issues else "ok"}
    issues.extend(gate1_issues)

    # --- Gate 2: Name constraints ---
    gate2_issues = []
    if "name" not in frontmatter:
        gate2_issues.append("Missing name")
    else:
        fm_name = frontmatter["name"]
        if not re.match(r'^[a-z0-9][a-z0-9-]*$', fm_name):
            gate2_issues.append(f"Must be lowercase/numbers/hyphens: '{fm_name}'")
        if len(fm_name) > 64:
            gate2_issues.append(f"Exceeds 64 chars: {len(fm_name)}")
        for banned in ("anthropic", "claude"):
            if banned in fm_name.lower():
                gate2_issues.append(f"Must not contain '{banned}'")

    gates["name"] = {"pass": len(gate2_issues) == 0, "detail": "; ".join(gate2_issues) if gate2_issues else "ok"}
    issues.extend(gate2_issues)

    # --- Gate 3: Description constraints ---
    gate3_issues = []
    if "description" not in frontmatter:
        gate3_issues.append("Missing description")
    else:
        desc = frontmatter["description"]
        desc_tokens = round(len(desc.encode()) / 3.5)
        if desc_tokens > 80:
            gate3_issues.append(f"Exceeds 80 tokens (~{desc_tokens})")

    gates["description"] = {"pass": len(gate3_issues) == 0, "detail": "; ".join(gate3_issues) if gate3_issues else "ok"}
    issues.extend(gate3_issues)

    # --- Gate 4: Body token budget ---
    body_tokens = round(len(body.encode()) / 3.5)
    gate4_issues = []
    if body_tokens > 2000:
        gate4_issues.append(f"Exceeds 2K hard cap (~{body_tokens} tokens)")
    elif body_tokens > 1000:
        warnings.append(f"Body above 1K ideal (~{body_tokens} tokens) — consider trimming or splitting into references/")
    if body_tokens < 100:
        gate4_issues.append(f"Suspiciously short (~{body_tokens} tokens)")

    gates["token_budget"] = {"pass": len(gate4_issues) == 0, "detail": "; ".join(gate4_issues) if gate4_issues else f"~{body_tokens} tokens"}
    issues.extend(gate4_issues)

    # --- Gate 5: No placeholder text ---
    placeholder_patterns = [
        r'\[TODO\b', r'\[FILL\s*IN\b', r'\[INSERT\b', r'\[REPLACE\b',
        r'\bTBD\b', r'\bFIXME\b', r'\bXXX\b', r'\[YOUR\b', r'\[EXAMPLE\b',
        r'<your[_-]', r'<insert[_-]', r'<add[_-]',
    ]
    placeholder_hits = []
    for pat in placeholder_patterns:
        matches = re.findall(pat, body, re.IGNORECASE)
        if matches:
            placeholder_hits.extend(matches)
    gate5_issues = []
    if placeholder_hits:
        gate5_issues.append(f"Found {len(placeholder_hits)} placeholder(s): {', '.join(placeholder_hits[:5])}")

    gates["no_placeholders"] = {"pass": len(gate5_issues) == 0, "detail": "; ".join(gate5_issues) if gate5_issues else "ok"}
    issues.extend(gate5_issues)

    # --- Gate 6: Completeness ---
    gate6_issues = []
    has_heading = bool(re.search(r'^#+\s+\S', body, re.MULTILINE))
    if not has_heading:
        gate6_issues.append("No markdown headings found")
    # Check for empty sections (heading followed by same-or-lower-level heading or end, not parent→child)
    empty_sections = []
    for m in re.finditer(r'^(#+)\s+([^\n]+)', body, re.MULTILINE):
        level = len(m.group(1))
        after = body[m.end():].lstrip('\n')
        next_heading = re.match(r'^(#+)\s+', after)
        if not after or (next_heading and len(next_heading.group(1)) <= level):
            empty_sections.append(m.group(0).strip())
    if empty_sections:
        gate6_issues.append(f"{len(empty_sections)} empty section(s): {', '.join(s.strip()[:30] for s in empty_sections[:3])}")

    gates["completeness"] = {"pass": len(gate6_issues) == 0, "detail": "; ".join(gate6_issues) if gate6_issues else "ok"}
    issues.extend(gate6_issues)

    # --- Gate 7: Manifest integrity ---
    gate7_issues = []
    if not manifest_path.exists():
        gate7_issues.append(f"manifest.json not found")
    else:
        with open(manifest_path) as f:
            manifest = json.load(f)

        if "search_queries" not in manifest:
            gate7_issues.append("Missing search_queries")
        if "sources" not in manifest or not manifest["sources"]:
            gate7_issues.append("No sources")
        else:
            missing_sha1 = [s["id"] for s in manifest["sources"] if "sha1" not in s]
            if missing_sha1:
                warnings.append(f"Sources missing sha1: {', '.join(missing_sha1)}")

        # Token count drift
        if "token_count" in manifest:
            actual = token_count(str(skill_path))
            recorded = manifest["token_count"]
            drift = abs(actual - recorded)
            if drift > 50:
                warnings.append(f"Token count drift: manifest says {recorded}, actual ~{actual}")

    gates["manifest"] = {"pass": len(gate7_issues) == 0, "detail": "; ".join(gate7_issues) if gate7_issues else "ok"}
    issues.extend(gate7_issues)

    # --- Style warnings (not gated) ---
    second_person = re.findall(r'\byou\s+(?:should|must|can|need|might|could|would)\b', body, re.IGNORECASE)
    if second_person:
        warnings.append(f"Second person found ({len(second_person)}x) — use imperative instead of 'you should...'")

    naked_negs = re.findall(r"(?:^|\n)[^\n]*(?:don't|do not|never|avoid)\b[^\n]*$", body, re.IGNORECASE | re.MULTILINE)
    without_alternative = [n.strip() for n in naked_negs if " instead" not in n.lower() and " use " not in n.lower() and " — " not in n]
    if without_alternative:
        warnings.append(f"Possible naked negations (no alternative given): {len(without_alternative)} lines")

    # --- References check ---
    refs_dir = skill_dir / "references"
    if refs_dir.exists():
        for ref_file in refs_dir.iterdir():
            if ref_file.suffix == ".md":
                ref_tokens = round(ref_file.stat().st_size / 3.5)
                if ref_tokens > 2000:
                    issues.append(f"Reference {ref_file.name} exceeds 2K tokens (~{ref_tokens})")

    # --- Scoring ---
    total_tokens = body_tokens
    if refs_dir.exists():
        for ref_file in refs_dir.iterdir():
            if ref_file.suffix == ".md":
                total_tokens += round(ref_file.stat().st_size / 3.5)

    score = sum(1 for g in gates.values() if g["pass"])
    max_score = len(gates)
    passed = score >= max_score - 1  # pass threshold: miss at most 1 gate

    return {
        "valid": len(issues) == 0,
        "passed": passed,
        "score": score,
        "max_score": max_score,
        "gates": gates,
        "body_tokens": body_tokens,
        "total_tokens": total_tokens,
        "issues": issues,
        "warnings": warnings,
    }


def _parse_model_spec(model):
    """Parse 'owner/model:provider' into (model_id, provider_slug|None)."""
    model_id = model
    provider_slug = None
    parts = model.split("/", 1)
    if len(parts) == 2 and ":" in parts[1]:
        name_part, provider_slug = parts[1].rsplit(":", 1)
        model_id = f"{parts[0]}/{name_part}"
    return model_id, provider_slug


def _openrouter_request(api_key, model_id, provider_slug, messages, max_tokens, temperature=0.2):
    """Single OpenRouter API call. Returns dict with response/tokens/status or error."""
    body = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if provider_slug:
        body["provider"] = {"order": [provider_slug], "allow_fallbacks": False}

    payload = json.dumps(body).encode()
    try:
        data = _http_request(
            OPENROUTER_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=120,
        )
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return {"response": response, "tokens": usage.get("total_tokens", 0), "status": "ok"}
    except RuntimeError as e:
        return {"response": "", "error": str(e), "status": "error"}


def test_skill(name, prompts, models=None, max_tokens=2000):
    """Test a skill against multiple models via OpenRouter. Returns per-model, per-prompt results."""
    load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    skill_path = GENERATED_DIR / name / "SKILL.md"
    if not skill_path.exists():
        print(f"Error: {skill_path} not found", file=sys.stderr)
        sys.exit(1)

    skill_content = skill_path.read_text()
    models = models or DEFAULT_TEST_MODELS

    results = []
    for model in models:
        for i, prompt in enumerate(prompts):
            model_id, provider_slug = _parse_model_spec(model)
            result = _openrouter_request(
                api_key, model_id, provider_slug,
                [{"role": "system", "content": skill_content}, {"role": "user", "content": prompt}],
                max_tokens,
            )
            results.append({"model": model, "prompt": prompt, **result})
            print(f"  {model} × prompt {i+1}: {result['status']}", file=sys.stderr)

    return {"skill": name, "models": models, "results": results}


SKILL_PATTERNS_DEFAULT = PLUGIN_DIR / "hooks" / "skill-patterns.sh"


def _load_skill_pattern(name, patterns_file=None):
    """Extract regex pattern for a skill from skill-patterns.sh. Returns pattern string or None."""
    import re as _re
    path = Path(patterns_file) if patterns_file else SKILL_PATTERNS_DEFAULT
    if not path.exists():
        return None
    content = path.read_text()
    m = _re.search(rf"SKILL_PATTERNS\[{_re.escape(name)}\]='([^']+)'", content)
    if not m:
        m = _re.search(rf'SKILL_PATTERNS\[{_re.escape(name)}\]="([^"]+)"', content)
    return m.group(1) if m else None


def eval_triggers(name, queries, pattern=None, patterns_file=None):
    """Test trigger regex patterns against should/shouldn't-trigger queries. Returns match results with precision/recall."""
    import re as _re

    if pattern is None:
        pattern = _load_skill_pattern(name, patterns_file)
    if pattern is None:
        print(f"Error: no pattern found for '{name}'. Provide --pattern or ensure skill-patterns.sh exists.", file=sys.stderr)
        sys.exit(1)

    should_trigger = queries.get("should_trigger", [])
    should_not_trigger = queries.get("should_not_trigger", [])

    matches = []
    tp, fp, tn, fn = 0, 0, 0, 0

    for query in should_trigger:
        matched = bool(_re.search(pattern, query.lower()))
        matches.append({"query": query, "expected": True, "matched": matched, "correct": matched})
        if matched:
            tp += 1
        else:
            fn += 1

    for query in should_not_trigger:
        matched = bool(_re.search(pattern, query.lower()))
        matches.append({"query": query, "expected": False, "matched": matched, "correct": not matched})
        if matched:
            fp += 1
        else:
            tn += 1

    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "skill": name,
        "pattern": pattern,
        "matches": matches,
        "metrics": {
            "true_positives": tp, "false_positives": fp,
            "true_negatives": tn, "false_negatives": fn,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "accuracy": round((tp + tn) / total, 3) if total > 0 else 0.0,
        },
    }


def ab_eval(name, prompts, models=None, max_tokens=2000):
    """A/B evaluation: for each prompt x model, run baseline (no skill) and treatment (with skill). Returns paired results."""
    load_env()
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    skill_path = GENERATED_DIR / name / "SKILL.md"
    if not skill_path.exists():
        print(f"Error: {skill_path} not found", file=sys.stderr)
        sys.exit(1)

    skill_content = skill_path.read_text()
    models = models or DEFAULT_TEST_MODELS

    pairs = []
    for model in models:
        for i, prompt in enumerate(prompts):
            model_id, provider_slug = _parse_model_spec(model)

            baseline = _openrouter_request(
                api_key, model_id, provider_slug,
                [{"role": "user", "content": prompt}],
                max_tokens,
            )
            treatment = _openrouter_request(
                api_key, model_id, provider_slug,
                [{"role": "system", "content": skill_content}, {"role": "user", "content": prompt}],
                max_tokens,
            )

            pairs.append({"model": model, "prompt": prompt, "baseline": baseline, "treatment": treatment})
            print(f"  {model} × prompt {i+1}: baseline={baseline['status']}, treatment={treatment['status']}", file=sys.stderr)

    return {"skill": name, "models": models, "pairs": pairs}


def cleanup():
    """Remove staging directory."""
    staging_root = DISTILLERY_DIR / ".skill-distiller"
    if staging_root.exists():
        shutil.rmtree(staging_root)


def main():
    parser = argparse.ArgumentParser(description="Skill distiller helper")
    sub = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = sub.add_parser("search", help="Search skills.sh for qualifying skills")
    p_search.add_argument("queries", nargs="+", help="Search queries")

    # fetch
    p_fetch = sub.add_parser("fetch", help="Fetch, stage, and checksum skills")
    p_fetch.add_argument("--skills", required=True, help="JSON array of skills from search")

    # check-updates
    p_check = sub.add_parser("check-updates", help="Check for updates to a generated skill")
    p_check.add_argument("name", help="Skill name (directory under generated-skills/)")

    # update-manifest
    p_update = sub.add_parser("update-manifest", help="Update manifest.json")
    p_update.add_argument("name", help="Skill name")
    p_update.add_argument("--token-count", type=int, required=True, help="Estimated token count")
    p_update.add_argument("--sources", required=True, help="JSON array of sources with sha1")

    # token-count
    p_tokens = sub.add_parser("token-count", help="Estimate token count for a file")
    p_tokens.add_argument("file", help="Path to file")

    # token-budget
    p_budget = sub.add_parser("token-budget", help="SkillsBench effectiveness rating for a skill")
    p_budget.add_argument("name", help="Skill name (directory under generated-skills/ or full path)")

    # grok-query
    p_grok = sub.add_parser("grok-query", help="Query Grok for recent X posts about a topic")
    p_grok.add_argument("topic", help="Topic to search for")
    p_grok.add_argument("--top-installs", type=int, default=1000, help="Highest install count from search results (sets engagement threshold)")
    p_grok.add_argument("--instructions", default=None, help="Scope/exclusion instructions to apply")

    # backfill-sha1
    p_backfill = sub.add_parser("backfill-sha1", help="Fetch sources and add sha1 checksums to manifest")
    p_backfill.add_argument("name", help="Skill name (directory under generated-skills/)")

    # validate
    p_validate = sub.add_parser("validate", help="Validate a generated skill")
    p_validate.add_argument("name", help="Skill name (directory under generated-skills/)")

    # test
    p_test = sub.add_parser("test", help="Test a skill against multiple models via OpenRouter")
    p_test.add_argument("name", help="Skill name (directory under generated-skills/)")
    p_test.add_argument("--prompts", required=True, help="JSON array of evaluation prompts")
    p_test.add_argument("--models", default=None, help="JSON array of OpenRouter model IDs (optional)")
    p_test.add_argument("--max-tokens", type=int, default=2000, help="Max response tokens per model (default: 2000)")

    # ab-eval
    p_ab = sub.add_parser("ab-eval", help="A/B evaluation: with-skill vs baseline for each prompt x model")
    p_ab.add_argument("name", help="Skill name (directory under generated-skills/)")
    p_ab.add_argument("--prompts", required=True, help="JSON array of evaluation prompts")
    p_ab.add_argument("--models", default=None, help="JSON array of OpenRouter model IDs (optional)")
    p_ab.add_argument("--max-tokens", type=int, default=2000, help="Max response tokens per request (default: 2000)")

    # eval-triggers
    p_eval_trig = sub.add_parser("eval-triggers", help="Test regex trigger patterns against evaluation queries")
    p_eval_trig.add_argument("name", help="Skill name")
    p_eval_trig.add_argument("--queries", required=True, help='JSON with "should_trigger" and "should_not_trigger" arrays')
    p_eval_trig.add_argument("--pattern", default=None, help="Regex pattern to test (default: read from skill-patterns.sh)")
    p_eval_trig.add_argument("--patterns-file", default=None, help="Path to skill-patterns.sh (default: plugin repo)")

    # cleanup
    sub.add_parser("cleanup", help="Remove staging directory")

    args = parser.parse_args()

    if args.command == "search":
        results = search_skills(args.queries)
        print(json.dumps(results, indent=2))

    elif args.command == "fetch":
        skills_list = json.loads(args.skills)
        results = fetch_skills(skills_list)
        print(json.dumps(results, indent=2))

    elif args.command == "check-updates":
        report = check_updates(args.name)
        print(json.dumps(report, indent=2))

    elif args.command == "update-manifest":
        update_manifest(args.name, args.token_count, args.sources)

    elif args.command == "token-count":
        count = token_count(args.file)
        print(count)

    elif args.command == "token-budget":
        skill_dir = GENERATED_DIR / args.name if not os.path.isabs(args.name) else Path(args.name)
        report = token_budget_report(skill_dir)
        print(json.dumps(report, indent=2))

    elif args.command == "grok-query":
        result = grok_query(args.topic, args.top_installs, args.instructions)
        print(json.dumps(result, indent=2))

    elif args.command == "backfill-sha1":
        backfill_sha1(args.name)

    elif args.command == "validate":
        report = validate(args.name)
        print(json.dumps(report, indent=2))

    elif args.command == "test":
        prompts = json.loads(args.prompts)
        models = json.loads(args.models) if args.models else None
        report = test_skill(args.name, prompts, models, args.max_tokens)
        print(json.dumps(report, indent=2))

    elif args.command == "ab-eval":
        prompts = json.loads(args.prompts)
        models = json.loads(args.models) if args.models else None
        report = ab_eval(args.name, prompts, models, args.max_tokens)
        print(json.dumps(report, indent=2))

    elif args.command == "eval-triggers":
        queries = json.loads(args.queries)
        report = eval_triggers(args.name, queries, args.pattern, args.patterns_file)
        print(json.dumps(report, indent=2))

    elif args.command == "cleanup":
        cleanup()
        print("Cleaned up", file=sys.stderr)


if __name__ == "__main__":
    main()
