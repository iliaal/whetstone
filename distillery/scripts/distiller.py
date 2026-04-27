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
from collections import Counter, defaultdict
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
DEFAULT_EVAL_MODEL = "deepseek/deepseek-v3.2"
DEFAULT_EVAL_REASONING = True

MIN_INSTALLS = 100
MIN_INSTALLS_FALLBACK = 50
MIN_QUALIFYING = 3
TOP_N = 10

MAX_RETRIES = 2
RETRY_DELAY = 1.0

# LLM-as-judge rubric for skill eval scoring.
# Weights: correctness 0.5, procedure_following 0.3, conciseness 0.2
_JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator scoring an AI agent's response quality.

You will receive:
- SKILL INSTRUCTIONS: A methodology/skill the agent had available during this task
- TASK INPUT: What the user asked the agent to do
- AGENT OUTPUT: What the agent actually produced (may be truncated from a longer conversation)

Important context: The skill was automatically injected based on keyword matching. The skill may or may not be directly relevant to this specific task. Score procedure_following based on how well the agent applied APPLICABLE parts of the skill -- if the skill isn't relevant to this task, score procedure_following as 5 (neutral, not penalized).

Score each dimension 0-10 (integers only):

1. CORRECTNESS: Did the agent correctly address the task? Did it produce accurate, relevant output? (0=completely wrong, 10=perfectly correct)

2. PROCEDURE_FOLLOWING: Did the agent follow applicable parts of the skill's methodology? (0=ignored relevant skill guidance, 5=skill not applicable to this task, 10=followed every applicable step)

3. CONCISENESS: Was the response appropriately concise without omitting important information? (0=extremely verbose/repetitive or critically incomplete, 10=perfect density)

Respond with ONLY valid JSON, no other text:
{"correctness": <0-10>, "procedure_following": <0-10>, "conciseness": <0-10>, "notes": "<one sentence justification>"}"""

_JUDGE_USER_TEMPLATE = """\
SKILL INSTRUCTIONS:
{skill_text}

TASK INPUT:
{task_input}

AGENT OUTPUT (may be truncated):
{agent_output}"""

# --- Session harvesting ---

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
EVAL_DATA_DIR = DISTILLERY_DIR / ".eval-data"
MANIFEST_PATH = DISTILLERY_DIR / ".skill-versions.json"

import re as _re

# Secret patterns — compiled once, used to scrub content before writing eval data.
# Matches common secret formats: API keys, tokens, PEM blocks, passwords, connection strings.
_SECRET_PATTERNS = _re.compile(
    r"|".join([
        r"(?:api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9_\-/.+]{16,}",
        r"(?:sk|pk|ak|rk|pat|ghp|gho|ghu|ghs|ghr|glpat|xox[bpsa])-[A-Za-z0-9_\-]{16,}",
        r"-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE|PUBLIC)\s+KEY-----",
        r"(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s'\"]+",
        r"Bearer\s+[A-Za-z0-9_\-/.+=]{20,}",
        r"AKIA[0-9A-Z]{16}",  # AWS access key
        r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}",  # JWT
    ]),
    _re.IGNORECASE,
)

# Negative signal patterns — user expressed dissatisfaction or retried.
_NEGATIVE_SIGNAL_PATTERNS = _re.compile(
    r"(?:"
    # Explicit corrections
    r"\bno[,.]?\s+(?:that'?s?\s+)?(?:not|wrong|incorrect)\b"
    r"|\bthat'?s?\s+(?:not\s+(?:what|right|correct)|wrong|incorrect)\b"
    r"|\b(?:is\s+)?(?:factually\s+)?incorrect\b"
    r"|\bnot\s+true\b"
    # Wrongness (33 hits: "is wrong", "are wrong", "everything is wrong")
    r"|\b(?:is|are)\s+wrong\b"
    r"|\beverything\s+is\s+wrong\b"
    # "should not/shouldn't be" — user correcting agent behavior (5 hits)
    r"|\bshould\s*n[o']t\s+(?:be|have|show)\b"
    # "should have been" — agent missed something (9 hits)
    r"|\bshould'?ve?\s+been\b"
    # Retry / undo requests
    r"|\btry\s+again\b"
    r"|\b(?:please\s+)?(?:undo|revert|roll\s*back)\b"
    r"|\bstart\s+over\b"
    # Direct blame / frustration
    r"|\byou\s+(?:broke|messed|screwed)\b"
    r"|\byou\s+keep\b"
    r"|\bi\s+already\s+(?:said|told|mentioned|asked)\b"
    # Wrong target
    r"|\bwrong\s+(?:file|approach|direction)\b"
    # Stop / don't
    r"|\bstop(?:\s+doing\s+that)?\b"
    r"|\bdon'?t\s+(?:do\s+that|mock|use|jump|commit)\b"
    # Persistence complaints — agent failed to fix on prior attempt (8 hits)
    r"|\bstill\s+(?:wrong|broken|failing|present|there|doesn'?t)\b"
    # Doubt — user lost confidence in agent (5 hits)
    r"|\bare\s+you\s+(?:sure|certain)\b"
    r"|\bare\s+you\s+confident\b"
    # User interrupted the agent mid-response (94 hits)
    r"|\[Request interrupted by user\b"
    # Strong negative language about agent output (5 hits)
    r"|\buseless\b|\bgarbage\b|\bjunk\b|\bcrap\b"
    r"|\bnever\s*mind\b|\bnevermind\b"
    # Short imperative fix requests (agent broke something)
    r"|\byes[,.]?\s+fix\s+(?:it|this|that)\b"
    r"|\bfix\s+(?:it|this|that)\s+(?:first|before|now|please)\b"
    # User rejecting agent's output or suggestion
    r"|\bskip\s+(?:it|this|that)\b"
    r"|\bmultiple\s+things\s+are\s+wrong\b"
    # Doesn't work / not working (6 hits)
    r"|\b(?:doesn'?t|does\s+not)\s+work\b"
    r"|\bnot\s+working\b"
    # Didn't fix / didn't work — agent's fix attempt failed (6 hits)
    r"|\b(?:didn'?t|did\s+not)\s+(?:fix|work|help|solve)\b"
    # Bug identification — user found an error in agent output (5 hits)
    r"|\bhas\s+a\s+bug\b"
    # Flat rejection at start of message (6 hits: "no, ...", "nope")
    r"|^no[,.:]\s"
    r"|^nope\b"
    # "no you are wrong" — direct contradiction (6 hits)
    r"|\bno\s+you\s+are\s+wrong\b"
    # "that's not right/it" — correction (2 hits)
    r"|\bthat'?s?\s+not\s+(?:right|correct|it)\b"
    # "seems/looks wrong" — user questioning output correctness (7+1 hits)
    r"|\b(?:seems?|looks?)\s+wrong\b"
    # "why did you" — questioning agent's decision (3 hits, all genuine)
    r"|\bwhy\s+did\s+you\b"
    # "you made things worse" — regression from agent action
    r"|\bmade\s+things\s+worse\b"
    # "something went wrong" / CI failures (2 hits)
    r"|\bsomething\s+went\s+wrong\b"
    r"|\bCI/?CD\s+(?:failed|still\s+failing)\b"
    # Latest changes broke — regression (3 hits)
    r"|\bbroke\s+things\b|\bregressed\b|\blatest\s+changes\s+broke\b"
    r")",
    _re.IGNORECASE,
)

# Skill injection header pattern — extracts skill paths from BEFORE STARTING block.
_SKILL_INJECTION_RE = _re.compile(
    r"^BEFORE STARTING:.*?(?=\nIf you cannot read)",
    _re.MULTILINE | _re.DOTALL,
)

# Extracts skill name and version from injection path like:
#   /home/.../.claude/plugins/cache/iliaal-marketplace/compound-engineering/2.47.2/skills/code-review/SKILL.md
# or local dev path like:
#   /home/.../compound-engineering-plugin/plugins/compound-engineering/skills/planning/SKILL.md
_SKILL_PATH_RE = _re.compile(
    r"/(?:compound-engineering)/(?:(\d+\.\d+\.\d+)/)?skills/([a-z0-9-]+)/SKILL\.md"
)


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
    # Strip code blocks and inline code so examples inside ``` ``` don't trigger
    body_stripped = re.sub(r'```[\s\S]*?```', '', body)
    body_stripped = re.sub(r'`[^`]*`', '', body_stripped)
    placeholder_patterns = [
        r'\[TODO\b', r'\[FILL\s*IN\b', r'\[INSERT\b', r'\[REPLACE\b',
        r'\bTBD\b', r'\bFIXME\b', r'\bXXX\b', r'\[YOUR\b', r'\[EXAMPLE\b',
        r'<your[_-]', r'<insert[_-]', r'<add[_-]',
    ]
    forbidding_context = re.compile(
        r'(?:no|never|avoid|forbid|don\'?t\s+(?:use|include|write|add)|'
        r'placeholder[s]?\s*(?:like|such\s+as|scan|check)|'
        r'without|exclude|reject|ban(?:ned)?|'
        r'skip\s+if|stop\s+if|return\s+to|prevent|disallow)\b',
        re.IGNORECASE,
    )
    placeholder_hits = []
    for pat in placeholder_patterns:
        for m in re.finditer(pat, body_stripped, re.IGNORECASE):
            start = max(0, m.start() - 200)
            end = min(len(body_stripped), m.end() + 50)
            window = body_stripped[start:end]
            if forbidding_context.search(window):
                continue
            placeholder_hits.append(m.group(0))
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


def _openrouter_request(api_key, model_id, provider_slug, messages, max_tokens, temperature=0.2, reasoning=False):
    """Single OpenRouter API call. Returns dict with response/tokens/status or error."""
    body = {
        "model": model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if provider_slug:
        body["provider"] = {"order": [provider_slug], "allow_fallbacks": False}
    if reasoning:
        body["reasoning"] = {"enabled": True}

    payload = json.dumps(body).encode()
    try:
        data = _http_request(
            OPENROUTER_API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            timeout=180,
        )
        msg = data.get("choices", [{}])[0].get("message", {})
        response = msg.get("content") or ""
        # DeepSeek V3.2 uses "reasoning" field; other models may use "reasoning_content"
        reasoning_content = msg.get("reasoning") or msg.get("reasoning_content") or ""
        usage = data.get("usage", {})
        result = {"response": response, "tokens": usage.get("total_tokens", 0), "status": "ok"}
        if reasoning_content:
            result["reasoning"] = reasoning_content
        return result
    except RuntimeError as e:
        return {"response": "", "error": str(e), "status": "error"}


DEFAULT_CLI_MODEL = "opus"

# Abstract/aspirational phrases that Opus 4.7 under-fires on. Flag when they
# appear in a component description (not body). These are puff words that
# don't convey operational meaning -- 4.7 matches descriptions literally,
# so a description of "Enhanced reasoning" won't trigger on user queries
# that actually need it. Keep conservative: only phrases where the anti-pattern
# is strong; legitimate qualifiers like "modern PHP 8.4" or "advanced React"
# are excluded.
_VAGUE_DESCRIPTION_PHRASES = (
    "first-class", "first class",
    "enhanced",
    "comprehensive",
    "best practices",
    "clean code",
    "non-trivial",
    "seamless",
    "streamlined",
    "cutting-edge", "cutting edge",
    "state-of-the-art", "state of the art",
    "sophisticated",
    "intelligent",
    "robust",
    "powerful",
)


def _find_vague_description_phrases(desc):
    """Return any vague/abstract phrases from the description lead (first ~30 words).

    Only checks the lead because late-section phrases may be legitimate
    (e.g., "remove robust error handling" as guidance content in a body).
    Descriptions are short so 30 words covers most of them regardless.
    """
    if not desc:
        return []
    lead = " ".join(desc.split()[:30]).lower()
    return [p for p in _VAGUE_DESCRIPTION_PHRASES if p in lead]


# Machine-specific filesystem paths that must not appear in published plugin files.
# The plugin is mirrored to ai-skills, shipped to ClawHub, and synced to .agents/.codex.
# Anything bound to one machine or one user's home directory leaks into strangers' tools.
_MACHINE_PATH_PATTERNS = (
    _re.compile(r"~/ai/[^\s`\"'<>)]+"),
    _re.compile(r"/home/[A-Za-z0-9_.-]+/[^\s`\"'<>)]+"),
    _re.compile(r"/Users/[A-Za-z0-9_.-]+/[^\s`\"'<>)]+"),
    _re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\[^\s`\"'<>)]+"),
    _re.compile(r"/var/folders/[^\s`\"'<>)]+"),
    _re.compile(r"/private/var/folders/[^\s`\"'<>)]+"),
)

REFERENCE_LINE_WARN = 150
REFERENCE_LINE_ERROR = 800

# Tier 2 skill class taxonomy. Every shipped skill declares one of these in its
# frontmatter. Values map to lookup-need clusters; see CLAUDE.md "Skill class taxonomy".
SKILL_CLASSES = frozenset({"language", "discipline", "workflow", "meta", "tool"})

# Tier 2 SPEC.md required headings (mirrors getsentry-skills/skill-writer).
# Maintenance contract per skill: intent, scope, triggers, sources, eval, limits, upkeep.
SPEC_REQUIRED_HEADINGS = (
    "Intent",
    "Scope",
    "Trigger Context",
    "Source And Evidence Model",
    "Evaluation",
    "Known Limitations",
    "Maintenance Notes",
)


def _find_machine_paths(text):
    """Return distinct machine-specific path matches, capped at 5 hits per source.

    Inline backtick code spans are stripped before scanning so meta-references
    (e.g. documenting `~/ai/...` as a forbidden pattern) don't trip the gate.
    Triple-backtick fenced blocks are still scanned -- example commands inside
    them must be portable to plugin users.
    """
    scrubbed = _re.sub(r"`[^`\n]+`", " ", text)
    seen = []
    for pattern in _MACHINE_PATH_PATTERNS:
        for match in pattern.finditer(scrubbed):
            hit = match.group(0)
            if hit not in seen:
                seen.append(hit)
            if len(seen) >= 5:
                return seen
    return seen

def _claude_cli_request(prompt, model=None):
    """Call claude -p and return the response. Returns dict with response/tokens/status."""
    model = model or DEFAULT_CLI_MODEL
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--effort", "medium",
        "--output-format", "json",
        "--permission-mode", "default",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            return {"response": "", "error": proc.stderr[:300], "status": "error"}

        data = json.loads(proc.stdout)
        response = data.get("result", "")
        usage = data.get("usage", {})
        total_tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        cost = data.get("total_cost_usd", 0)
        return {"response": response, "tokens": total_tokens, "cost_usd": cost, "status": "ok"}
    except subprocess.TimeoutExpired:
        return {"response": "", "error": "timeout (180s)", "status": "error"}
    except (json.JSONDecodeError, OSError) as e:
        return {"response": "", "error": str(e)[:300], "status": "error"}


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


TRIGGER_FIXTURES_DIR = DISTILLERY_DIR / "tests" / "fixtures" / "triggers"
TRIGGER_POSITIVE_FLOOR = 5
TRIGGER_NEGATIVE_FLOOR = 5


def validate_plugin(component_filter=None):
    """Run deterministic validation across all plugin skills, agents, and commands.

    Consolidates: inventory, validation gates, anti-pattern detection, structural
    checks, and reference validation into one fast pass. No AI needed.

    Args:
        component_filter: only validate this component name (optional)

    Returns structured JSON report with per-component findings.
    """
    import re
    import yaml

    skills_dir = PLUGIN_DIR / "skills"
    agents_dir = PLUGIN_DIR / "agents"
    commands_dir = PLUGIN_DIR / "commands"
    readme_path = PLUGIN_DIR / "README.md"
    patterns_file = PLUGIN_DIR / "hooks" / "skill-patterns.sh"

    # --- Build inventories ---
    known_skills = {}
    known_agents = {}
    known_commands = {}

    for d in sorted(skills_dir.iterdir()) if skills_dir.exists() else []:
        if d.is_dir() and (d / "SKILL.md").exists():
            known_skills[d.name] = d / "SKILL.md"

    # Phantom-agent guard: Claude Code registers every .md under agents/ as an
    # invokable subagent. Reference files must live outside agents/ (e.g., at
    # plugins/compound-engineering/shared-references/) or they pollute /context
    # and the agent tool list. Flag any stragglers as HIGH.
    phantom_agent_paths = []
    for f in sorted(agents_dir.rglob("*.md")) if agents_dir.exists() else []:
        if f.name == "README.md":
            continue
        rel_parts = f.relative_to(agents_dir).parts
        if "references" in rel_parts:
            phantom_agent_paths.append(f.relative_to(PLUGIN_DIR))
            continue
        known_agents[f.stem] = f

    for f in sorted(commands_dir.rglob("*.md")) if commands_dir.exists() else []:
        # Skip reference files (commands/*/references/*.md, commands/workflows/references/*.md)
        if "references" in f.relative_to(commands_dir).parts:
            continue
        known_commands[f.stem] = f

    findings = []
    inventory = []

    def add_finding(component, check, message, severity="MEDIUM"):
        findings.append({
            "component": component,
            "check": check,
            "message": message,
            "severity": severity,
        })

    for p in phantom_agent_paths:
        add_finding(
            str(p),
            "PHANTOM_AGENT",
            f"Reference file under agents/ gets registered as a subagent by Claude Code. Move to plugins/compound-engineering/shared-references/ and update link paths.",
            "HIGH",
        )

    def parse_frontmatter(content):
        """Parse YAML frontmatter from markdown content."""
        fm = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    fm = yaml.safe_load(parts[1]) or {}
                except Exception:
                    fm = {"_parse_error": True}
                body = parts[2].strip()
        return fm, body

    # --- Validate skills ---
    for skill_name, skill_path in known_skills.items():
        if component_filter and skill_name != component_filter:
            continue

        content = skill_path.read_text()
        fm, body = parse_frontmatter(content)
        body_tokens = round(len(body.encode()) / 3.5)
        desc = fm.get("description", "")
        desc_tokens = round(len(desc.encode()) / 3.5) if desc else 0

        inventory.append({
            "name": skill_name,
            "type": "skill",
            "description": desc[:200] if desc else "",
            "body_tokens": body_tokens,
        })

        # --- Frontmatter gates ---
        if not content.startswith("---"):
            add_finding(skill_name, "frontmatter", "No YAML frontmatter found", "HIGH")
        elif fm.get("_parse_error"):
            add_finding(skill_name, "frontmatter", "YAML parse error", "HIGH")

        inert_fields = {"triggers", "role", "scope", "domain", "output-format", "author",
                        "version", "license", "related-skills", "tags"}
        found_inert = inert_fields & set(fm.keys())
        if found_inert:
            add_finding(skill_name, "inert_fields", f"Inert frontmatter fields: {', '.join(sorted(found_inert))}", "MEDIUM")

        # --- Class gate (Tier 2) ---
        fm_class = fm.get("class")
        if fm_class is None:
            add_finding(skill_name, "class", "Missing 'class' field in frontmatter (one of: language, discipline, workflow, meta, tool)", "HIGH")
        elif fm_class not in SKILL_CLASSES:
            add_finding(skill_name, "class", f"Invalid class '{fm_class}' (allowed: {', '.join(sorted(SKILL_CLASSES))})", "HIGH")

        # --- Name gates ---
        fm_name = fm.get("name", "")
        if not fm_name:
            add_finding(skill_name, "name", "Missing name in frontmatter", "HIGH")
        else:
            if not re.match(r'^[a-z0-9][a-z0-9-]*$', fm_name):
                add_finding(skill_name, "name", f"Invalid name format: '{fm_name}'", "HIGH")
            if len(fm_name) > 64:
                add_finding(skill_name, "name", f"Name exceeds 64 chars: {len(fm_name)}", "HIGH")
            for banned in ("anthropic", "claude"):
                if banned in fm_name.lower():
                    add_finding(skill_name, "name", f"Name contains '{banned}'", "HIGH")
            if fm_name != skill_name:
                add_finding(skill_name, "name", f"Name '{fm_name}' doesn't match directory '{skill_name}'", "HIGH")

        # --- Description gates ---
        if not desc:
            add_finding(skill_name, "description", "Missing description", "HIGH")
        else:
            if desc_tokens > 80:
                add_finding(skill_name, "description", f"Description exceeds 80 tokens (~{desc_tokens})", "HIGH")
            if "use when" not in desc.lower():
                add_finding(skill_name, "description", "Description missing 'Use when' trigger phrase", "MEDIUM")
            vague = _find_vague_description_phrases(desc)
            if vague:
                add_finding(skill_name, "VAGUE_DESCRIPTION",
                            f"Abstract phrases in description lead: {', '.join(vague)} -- replace with concrete trigger vocabulary",
                            "MEDIUM")

        # --- Body size ---
        if body_tokens > 4000:
            add_finding(skill_name, "body_size", f"Body exceeds 4K tokens (~{body_tokens}) -- consider references/ split", "MEDIUM")
        elif body_tokens < 100:
            add_finding(skill_name, "body_size", f"Suspiciously short (~{body_tokens} tokens)", "HIGH")

        # --- Machine-specific path leak (publishing blocker) ---
        skill_path_hits = _find_machine_paths(content)
        if skill_path_hits:
            add_finding(skill_name, "MACHINE_PATH_LEAK",
                        f"Machine-specific path(s) in SKILL.md: {', '.join(skill_path_hits[:3])}",
                        "HIGH")

        # --- Placeholder text ---
        # Strip markdown links first to avoid false positives on [example-file.md](...)
        body_no_links = re.sub(r'\[[^\]]+\]\([^)]+\)', '', body)
        # Strip code blocks and inline code to avoid matching examples within them
        body_stripped = re.sub(r'```[\s\S]*?```', '', body_no_links)
        body_stripped = re.sub(r'`[^`]*`', '', body_stripped)
        placeholder_patterns = [
            r'\[TODO\b', r'\[FILL\s*IN\b', r'\[INSERT\b', r'\[REPLACE\b',
            r'\bTBD\b', r'\bFIXME\b', r'\bXXX\b', r'\[YOUR\b', r'\[EXAMPLE\b',
            r'<your[_-]', r'<insert[_-]', r'<add[_-]',
        ]
        # Sentences that FORBID placeholder tokens (the skill is telling the reader NOT to use them).
        # Matches are not findings — they're anti-pattern documentation.
        forbidding_context = re.compile(
            r'(?:no|never|avoid|forbid|don\'?t\s+(?:use|include|write|add)|'
            r'placeholder[s]?\s*(?:like|such\s+as|scan|check)|'
            r'without|exclude|reject|ban(?:ned)?|'
            r'skip\s+if|stop\s+if|return\s+to|prevent|disallow)\b',
            re.IGNORECASE,
        )
        for pat in placeholder_patterns:
            real_hits = []
            for m in re.finditer(pat, body_stripped, re.IGNORECASE):
                # Look at the surrounding sentence — find the sentence-start before the match
                # and the sentence-end (period/colon/newline) after.
                start = max(0, m.start() - 200)
                end = min(len(body_stripped), m.end() + 50)
                window = body_stripped[start:end]
                if forbidding_context.search(window):
                    continue  # match is inside a forbidding-sentence; not a finding
                real_hits.append(m.group(0))
            if real_hits:
                add_finding(skill_name, "placeholder", f"Placeholder text found: {real_hits[0]}", "HIGH")
                break

        # --- Structural: headings and empty sections ---
        if not re.search(r'^#+\s+\S', body, re.MULTILINE):
            add_finding(skill_name, "structure", "No markdown headings found", "MEDIUM")

        empty_sections = []
        for m in re.finditer(r'^(#+)\s+([^\n]+)', body, re.MULTILINE):
            level = len(m.group(1))
            after = body[m.end():].lstrip('\n')
            next_heading = re.match(r'^(#+)\s+', after)
            if not after or (next_heading and len(next_heading.group(1)) <= level):
                empty_sections.append(m.group(2).strip()[:40])
        if empty_sections:
            add_finding(skill_name, "structure", f"Empty section(s): {', '.join(empty_sections[:3])}", "MEDIUM")

        # --- Anti-patterns ---
        directive_count = len(re.findall(r'\b(?:MUST|ALWAYS|NEVER)\b', body))
        if directive_count > 15:
            add_finding(skill_name, "OVER_CONSTRAINED", f"{directive_count} MUST/ALWAYS/NEVER directives", "MEDIUM")

        line_count = body.count('\n')
        has_refs = (skill_path.parent / "references").is_dir()
        if line_count > 800 and not has_refs:
            add_finding(skill_name, "BLOATED_SKILL", f"{line_count} lines with no references/ directory", "HIGH")

        # --- Reference integrity ---
        skill_dir = skill_path.parent
        refs_dir = skill_dir / "references"
        scripts_dir_path = skill_dir / "scripts"

        if refs_dir.is_dir():
            linked_refs = set(re.findall(r'\]\(\./references/([^)]+)\)', content))
            actual_refs = {f.name for f in refs_dir.iterdir() if f.is_file()}
            orphans = actual_refs - linked_refs
            for orphan in sorted(orphans):
                add_finding(skill_name, "ORPHAN_REFERENCE", f"references/{orphan} not linked from SKILL.md", "MEDIUM")

            for ref_path in sorted(refs_dir.rglob("*.md")):
                ref_text = ref_path.read_text()
                ref_label = f"references/{ref_path.relative_to(refs_dir)}"
                line_count = ref_text.count('\n') + 1
                if line_count > REFERENCE_LINE_ERROR:
                    add_finding(skill_name, "REFERENCE_BLOAT",
                                f"{ref_label} is {line_count} lines (>{REFERENCE_LINE_ERROR}) -- split by lookup need",
                                "HIGH")
                elif line_count > REFERENCE_LINE_WARN:
                    add_finding(skill_name, "reference_length",
                                f"{ref_label} is {line_count} lines (>{REFERENCE_LINE_WARN}) -- consider splitting or adding navigation",
                                "MEDIUM")
                ref_path_hits = _find_machine_paths(ref_text)
                if ref_path_hits:
                    add_finding(skill_name, "MACHINE_PATH_LEAK",
                                f"Machine-specific path(s) in {ref_label}: {', '.join(ref_path_hits[:3])}",
                                "HIGH")

        if scripts_dir_path.is_dir():
            linked_scripts = set(re.findall(r'\]\(\./scripts/([^)]+)\)', content))
            actual_scripts = {f.name for f in scripts_dir_path.iterdir() if f.is_file()}
            orphans = actual_scripts - linked_scripts
            for orphan in sorted(orphans):
                add_finding(skill_name, "ORPHAN_REFERENCE", f"scripts/{orphan} not linked from SKILL.md", "MEDIUM")

        # --- Backtick references to nonexistent components ---
        backtick_refs = re.findall(r'`([a-z][a-z0-9-]+)`\s+(?:skill|agent|command)', body, re.IGNORECASE)
        for ref in backtick_refs:
            if ref not in known_skills and ref not in known_agents and ref not in known_commands:
                add_finding(skill_name, "DEAD_CROSS_REF", f"References nonexistent component: `{ref}`", "HIGH")

        # --- SPEC.md (Tier 2) ---
        spec_md = skill_dir / "SPEC.md"
        if not spec_md.exists():
            add_finding(skill_name, "SPEC_MISSING",
                        "SPEC.md not found -- run scripts/generate-spec.py or author manually",
                        "MEDIUM")
        else:
            spec_content = spec_md.read_text()
            missing_headings = [
                h for h in SPEC_REQUIRED_HEADINGS
                if not re.search(rf"^##\s+{re.escape(h)}\s*$", spec_content, re.MULTILINE)
            ]
            if missing_headings:
                add_finding(skill_name, "SPEC_HEADINGS",
                            f"SPEC.md missing required heading(s): {', '.join(missing_headings)}",
                            "HIGH")
            spec_path_hits = _find_machine_paths(spec_content)
            if spec_path_hits:
                add_finding(skill_name, "MACHINE_PATH_LEAK",
                            f"Machine-specific path(s) in SPEC.md: {', '.join(spec_path_hits[:3])}",
                            "HIGH")

    # --- Validate agents ---
    for agent_name, agent_path in known_agents.items():
        if component_filter and agent_name != component_filter:
            continue

        content = agent_path.read_text()
        fm, body = parse_frontmatter(content)
        body_tokens = round(len(body.encode()) / 3.5)
        desc = fm.get("description", "")

        inventory.append({
            "name": agent_name,
            "type": "agent",
            "description": desc[:200] if desc else "",
            "body_tokens": body_tokens,
        })

        desc_tokens = round(len(desc.encode()) / 3.5) if desc else 0

        if not desc or len(desc) < 20:
            add_finding(agent_name, "EMPTY_DESCRIPTION", f"Agent description too short ({len(desc)} chars)", "HIGH")
        elif desc_tokens > 80:
            add_finding(agent_name, "description", f"Description exceeds 80 tokens (~{desc_tokens}) -- trim routing guidance or redundant phrasing", "HIGH")

        if desc and "use " not in desc.lower():
            add_finding(agent_name, "MISSING_TRIGGER", "Agent description missing trigger phrase", "MEDIUM")

        if desc:
            vague = _find_vague_description_phrases(desc)
            if vague:
                add_finding(agent_name, "VAGUE_DESCRIPTION",
                            f"Abstract phrases in description lead: {', '.join(vague)} -- replace with concrete trigger vocabulary",
                            "MEDIUM")

        if body_tokens > 3000:
            add_finding(agent_name, "body_size", f"Agent body exceeds 3K tokens (~{body_tokens})", "MEDIUM")

        agent_path_hits = _find_machine_paths(content)
        if agent_path_hits:
            add_finding(agent_name, "MACHINE_PATH_LEAK",
                        f"Machine-specific path(s) in agent: {', '.join(agent_path_hits[:3])}",
                        "HIGH")

        # Cross-reference check
        skill_refs = re.findall(r'skills/([a-z][a-z0-9-]+)', body)
        for ref in skill_refs:
            if ref not in known_skills:
                add_finding(agent_name, "DEAD_CROSS_REF", f"References nonexistent skill: {ref}", "HIGH")

    # --- Validate commands ---
    for cmd_name, cmd_path in known_commands.items():
        if component_filter and cmd_name != component_filter:
            continue

        content = cmd_path.read_text()
        fm, body = parse_frontmatter(content)
        body_tokens = round(len(body.encode()) / 3.5)
        desc = fm.get("description", "")

        inventory.append({
            "name": cmd_name,
            "type": "command",
            "description": desc[:200] if desc else "",
            "body_tokens": body_tokens,
        })

        if not desc:
            add_finding(cmd_name, "EMPTY_DESCRIPTION", "Command missing description", "HIGH")
        else:
            vague = _find_vague_description_phrases(desc)
            if vague:
                add_finding(cmd_name, "VAGUE_DESCRIPTION",
                            f"Abstract phrases in description lead: {', '.join(vague)} -- replace with concrete trigger vocabulary",
                            "MEDIUM")

        if body_tokens > 4000:
            add_finding(cmd_name, "body_size", f"Command body exceeds 4K tokens (~{body_tokens})", "MEDIUM")

        if fm.get("argument-hint") and "$ARGUMENTS" not in body:
            add_finding(cmd_name, "missing_arg_handling", "Declares argument-hint but body doesn't reference $ARGUMENTS", "MEDIUM")

        cmd_path_hits = _find_machine_paths(content)
        if cmd_path_hits:
            add_finding(cmd_name, "MACHINE_PATH_LEAK",
                        f"Machine-specific path(s) in command: {', '.join(cmd_path_hits[:3])}",
                        "HIGH")

        # Cross-reference check
        skill_refs = re.findall(r'skills/([a-z][a-z0-9-]+)', body)
        for ref in skill_refs:
            if ref not in known_skills:
                add_finding(cmd_name, "DEAD_CROSS_REF", f"References nonexistent skill: {ref}", "HIGH")

    # --- Duplicate trigger detection ---
    descriptions = {}
    for item in inventory:
        if item["description"]:
            descriptions[item["name"]] = set(re.findall(r'\b[a-z]{3,}\b', item["description"].lower()))

    checked_pairs = set()
    for name_a, words_a in descriptions.items():
        if component_filter and name_a != component_filter:
            continue
        for name_b, words_b in descriptions.items():
            if name_a >= name_b:
                continue
            pair = (name_a, name_b)
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)
            if not words_a or not words_b:
                continue
            overlap = words_a & words_b
            smaller = min(len(words_a), len(words_b))
            if smaller > 0 and len(overlap) / smaller > 0.7:
                add_finding(name_a, "DUPLICATE_TRIGGER",
                            f">70% description overlap with {name_b}: {', '.join(sorted(overlap)[:5])}", "MEDIUM")

    # --- Version pin detection ---
    for name, path in {**{k: v for k, v in known_skills.items()}, **known_agents, **known_commands}.items():
        if component_filter and name != component_filter:
            continue
        content = path.read_text()
        version_pins = re.findall(r'(?:as of v\d|since 20\d{2}|if using .{3,20} \d+)', content, re.IGNORECASE)
        if version_pins:
            add_finding(name, "STALE_VERSION_PIN", f"Version-pinned statement: '{version_pins[0]}'", "LOW")

    # --- Hook pattern count check ---
    if patterns_file.exists() and not component_filter:
        patterns_content = patterns_file.read_text()
        count_match = re.search(r'Total skills:\s*(\d+)', patterns_content)
        if count_match:
            declared = int(count_match.group(1))
            actual = len(known_skills)
            if declared != actual:
                add_finding("skill-patterns.sh", "count_mismatch",
                            f"Declares {declared} skills but {actual} exist", "MEDIUM")

    # --- README count check ---
    if readme_path.exists() and not component_filter:
        readme = readme_path.read_text()
        for label, actual_count in [("skill", len(known_skills)), ("agent", len(known_agents)), ("command", len(known_commands))]:
            count_matches = re.findall(rf'\b(\d+)\s+{label}s?\b', readme, re.IGNORECASE)
            for m in count_matches:
                if int(m) != actual_count:
                    add_finding("README.md", "count_mismatch",
                                f"Says {m} {label}s but {actual_count} exist", "MEDIUM")
                    break

    # --- Sort findings by severity ---
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: (severity_order.get(f["severity"], 3), f["component"]))

    summary = {
        "high": sum(1 for f in findings if f["severity"] == "HIGH"),
        "medium": sum(1 for f in findings if f["severity"] == "MEDIUM"),
        "low": sum(1 for f in findings if f["severity"] == "LOW"),
    }

    return {
        "inventory": {
            "skills": len(known_skills),
            "agents": len(known_agents),
            "commands": len(known_commands),
            "total": len(inventory),
        },
        "findings": findings,
        "summary": summary,
        "passed": summary["high"] == 0,
    }


def test_triggers(skill_filter=None, fixtures_dir=None):
    """Run regex trigger regression tests from fixture JSONL files.

    Each fixture file is named <skill>.jsonl and contains lines with
    {"prompt": "...", "expect": true/false, ...}. Tests each skill's
    regex pattern against the fixture prompts and reports pass/fail.

    Args:
        skill_filter: test only this skill (optional)
        fixtures_dir: override fixtures directory path (optional)

    Returns dict with per-skill results and overall pass/fail.
    """
    fdir = Path(fixtures_dir) if fixtures_dir else TRIGGER_FIXTURES_DIR
    if not fdir.exists():
        print(f"Error: fixtures directory not found: {fdir}", file=sys.stderr)
        sys.exit(1)

    fixture_files = sorted(fdir.glob("*.jsonl"))
    if not fixture_files:
        print(f"Error: no fixture files in {fdir}", file=sys.stderr)
        sys.exit(1)

    results = []
    all_pass = True

    for fpath in fixture_files:
        skill_name = fpath.stem
        if skill_filter and skill_name != skill_filter:
            continue

        should_trigger = []
        should_not_trigger = []
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                if entry.get("expect"):
                    should_trigger.append(entry["prompt"])
                else:
                    should_not_trigger.append(entry["prompt"])

        if not should_trigger and not should_not_trigger:
            continue

        coverage_errors = []
        if len(should_trigger) < TRIGGER_POSITIVE_FLOOR:
            coverage_errors.append(
                f"only {len(should_trigger)} should_trigger cases (floor: {TRIGGER_POSITIVE_FLOOR})"
            )
        if len(should_not_trigger) < TRIGGER_NEGATIVE_FLOOR:
            coverage_errors.append(
                f"only {len(should_not_trigger)} should_not_trigger cases (floor: {TRIGGER_NEGATIVE_FLOOR})"
            )

        queries = {"should_trigger": should_trigger, "should_not_trigger": should_not_trigger}
        report = eval_triggers(skill_name, queries)
        f1_pass = report["metrics"]["f1"] == 1.0
        passed = f1_pass and not coverage_errors
        if not passed:
            all_pass = False

        results.append({
            "skill": skill_name,
            "passed": passed,
            "metrics": report["metrics"],
            "failures": [m for m in report["matches"] if not m["correct"]],
            "coverage_errors": coverage_errors,
        })

    return {"results": results, "all_passed": all_pass}


SEMANTIC_FIXTURES_PATH = DISTILLERY_DIR / "tests" / "fixtures" / "semantic-triggers.jsonl"


def test_semantic(max_tests=None, fixtures_path=None):
    """Run semantic injection tests via claude CLI.

    For each test case, runs claude with the prompt, captures which skills
    were injected via TEST_INJECTION_LOG, and compares against expectations.

    Args:
        max_tests: limit number of tests (controls token cost)
        fixtures_path: override path to semantic-triggers.jsonl

    Returns dict with per-test results and overall pass/fail.
    """
    fpath = Path(fixtures_path) if fixtures_path else SEMANTIC_FIXTURES_PATH
    if not fpath.exists():
        print(f"Error: fixtures file not found: {fpath}", file=sys.stderr)
        sys.exit(1)

    fixtures = []
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))

    if max_tests and len(fixtures) > max_tests:
        fixtures = fixtures[:max_tests]

    print(f"Running {len(fixtures)} semantic injection tests (costs API tokens)...", file=sys.stderr)

    results = []
    all_pass = True

    for i, fixture in enumerate(fixtures):
        prompt = fixture["prompt"]
        should_trigger = set(fixture.get("should_trigger", []))
        should_not_trigger = set(fixture.get("should_not_trigger", []))

        # Create temp file for injection log
        import tempfile
        log_fd, log_path = tempfile.mkstemp(prefix="injection-test-", suffix=".log")
        os.close(log_fd)

        try:
            env = os.environ.copy()
            env["TEST_INJECTION_LOG"] = log_path

            proc = subprocess.run(
                ["claude", "-p", prompt, "--model", DEFAULT_CLI_MODEL, "--max-turns", "2", "--output-format", "json"],
                capture_output=True, text=True, timeout=120, env=env,
            )

            # Read injected skills from log
            injected = set()
            if os.path.exists(log_path):
                with open(log_path) as lf:
                    for line in lf:
                        line = line.strip()
                        if line:
                            injected.add(line)

            # Check expectations
            missing = should_trigger - injected
            unwanted = should_not_trigger & injected
            inconclusive = not injected  # Claude didn't spawn any subagents

            passed = not missing and not unwanted and not inconclusive
            if not passed and not inconclusive:
                all_pass = False

            status = "pass" if passed else ("inconclusive" if inconclusive else "fail")

            results.append({
                "prompt": prompt[:100],
                "status": status,
                "injected": sorted(injected),
                "missing": sorted(missing),
                "unwanted": sorted(unwanted),
            })

            print(f"  [{i+1}/{len(fixtures)}] {status.upper()}: \"{prompt[:60]}...\" -> {sorted(injected) or '(no injection)'}", file=sys.stderr)

        except subprocess.TimeoutExpired:
            results.append({"prompt": prompt[:100], "status": "timeout", "injected": [], "missing": [], "unwanted": []})
            print(f"  [{i+1}/{len(fixtures)}] TIMEOUT: \"{prompt[:60]}...\"", file=sys.stderr)
        except FileNotFoundError:
            print("Error: 'claude' CLI not found. Install Claude Code to run semantic tests.", file=sys.stderr)
            sys.exit(1)
        finally:
            if os.path.exists(log_path):
                os.unlink(log_path)

    pass_count = sum(1 for r in results if r["status"] == "pass")
    fail_count = sum(1 for r in results if r["status"] == "fail")
    inconclusive_count = sum(1 for r in results if r["status"] == "inconclusive")

    return {
        "results": results,
        "all_passed": all_pass,
        "summary": {
            "total": len(results),
            "passed": pass_count,
            "failed": fail_count,
            "inconclusive": inconclusive_count,
        },
    }


def cleanup():
    """Remove staging directory."""
    staging_root = DISTILLERY_DIR / ".skill-distiller"
    if staging_root.exists():
        shutil.rmtree(staging_root)


# --- Session harvesting ---


def _load_skill_manifest():
    """Load .skill-versions.json. Returns dict or None if not found."""
    if not MANIFEST_PATH.exists():
        return None
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def _parse_semver(version_str):
    """Parse a semver string into a comparable tuple. Returns (0,0,0) for None."""
    if not version_str:
        return (0, 0, 0)
    parts = version_str.split(".")
    try:
        return tuple(int(p) for p in parts[:3])
    except (ValueError, TypeError):
        return (0, 0, 0)


def _is_example_stale(example, skill_name, manifest):
    """Check if an eval example predates the current skill content, pattern, or runtime model.

    Returns {"content_stale": bool, "pattern_stale": bool, "model_stale": bool}.
    Null skill_version (local dev) is treated as stale.
    Missing model_id passes through (unknown, can't determine) to stay backward-compatible
    with eval data harvested before model tracking landed.
    """
    if manifest is None:
        return {"content_stale": False, "pattern_stale": False, "model_stale": False}

    skill_info = manifest.get("skills", {}).get(skill_name, {})
    if not skill_info:
        return {"content_stale": False, "pattern_stale": False, "model_stale": False}

    ex_version = _parse_semver(example.get("skill_version"))

    content_changed = _parse_semver(skill_info.get("content_changed"))
    pattern_changed = _parse_semver(skill_info.get("pattern_changed"))

    # Support both old single-prefix and new list-of-prefixes manifest formats
    baselines = manifest.get("model_baseline_prefixes")
    if baselines is None:
        legacy = manifest.get("model_baseline_prefix")
        baselines = [legacy] if legacy else []
    ex_model = example.get("model_id")
    if not baselines or ex_model is None:
        model_stale = False
    else:
        model_stale = not any(ex_model.startswith(p) for p in baselines)

    return {
        "content_stale": ex_version < content_changed,
        "pattern_stale": ex_version < pattern_changed,
        "model_stale": model_stale,
    }


def _contains_secret(text):
    """Return True if text contains likely secrets."""
    return bool(_SECRET_PATTERNS.search(text))


def _scrub_secrets(text):
    """Replace detected secrets with [REDACTED]."""
    return _SECRET_PATTERNS.sub("[REDACTED]", text)


def _extract_injected_skills(prompt_text):
    """Extract skill names and versions from a BEFORE STARTING injection header.

    Returns list of dicts: [{"skill": "code-review", "version": "2.47.2"}, ...]
    Version may be None for local dev paths.
    """
    m = _SKILL_INJECTION_RE.search(prompt_text)
    if not m:
        return []
    header = m.group(0)
    skills = []
    for pm in _SKILL_PATH_RE.finditer(header):
        version, skill_name = pm.group(1), pm.group(2)
        skills.append({"skill": skill_name, "version": version})
    return skills


def _strip_injection_header(prompt_text):
    """Remove the BEFORE STARTING block from a prompt, returning the actual task."""
    m = _SKILL_INJECTION_RE.search(prompt_text)
    if not m:
        return prompt_text
    # The header ends with "If you cannot read the files, proceed with your best judgment.\n\n"
    end_marker = "If you cannot read the files, proceed with your best judgment."
    idx = prompt_text.find(end_marker)
    if idx >= 0:
        remainder = prompt_text[idx + len(end_marker):]
        return remainder.lstrip("\n")
    return prompt_text[m.end():].lstrip("\n")


def _classify_signal(user_messages):
    """Classify conversation outcome based on user messages.

    Returns: "positive", "negative", or "ambiguous".
    Heuristic: if any user message matches negative patterns, it's negative.
    If there are fewer than 2 user messages, ambiguous (too little signal).
    Otherwise positive.
    """
    if len(user_messages) < 2:
        return "ambiguous"
    for msg in user_messages:
        # Only scan short conversational messages (< 500 chars) to avoid
        # false positives from instructional content, code, or skill text
        # that the user pasted or the agent quoted back.
        if len(msg) > 500:
            continue
        # Skip tool_result content that looks like file contents (YAML frontmatter,
        # code, markdown headings). In subagent traces, tool results arrive as
        # "user" role messages and contain skill/code text with words like "stop",
        # "don't mock" that trigger false positives.
        stripped = msg.lstrip()
        if stripped.startswith("---\n") or stripped.startswith("```") or stripped.startswith("#"):
            continue
        # Skip numbered line output (cat -n format from Read tool results)
        if stripped and stripped[0].isdigit() and "\t" in stripped[:10]:
            continue
        if _NEGATIVE_SIGNAL_PATTERNS.search(msg):
            return "negative"
    return "positive"


def _parse_session(jsonl_path):
    """Parse a single JSONL session file into structured data.

    Returns dict with:
      - session_id: str
      - project: str (directory name)
      - is_subagent: bool
      - turns: list of {role, content_text, tool_calls, timestamp}
      - injected_skills: list of {skill, version} (subagents only)
      - task_prompt: str (the actual task, with injection header stripped)
      - signal: "positive" | "negative" | "ambiguous"
      - git_branch: str or None
      - claude_version: str or None
    """
    turns = []
    session_id = None
    git_branch = None
    claude_version = None
    models = []
    is_subagent = "subagents" in str(jsonl_path)

    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type", "")
            if msg_type not in ("user", "assistant"):
                continue

            msg = obj.get("message", {})
            role = msg.get("role", "")
            if not role:
                continue

            # Extract metadata from first user message
            if session_id is None:
                session_id = obj.get("sessionId")
                git_branch = obj.get("gitBranch")
                claude_version = obj.get("version")

            # Track model per assistant turn for staleness filtering
            if role == "assistant":
                turn_model = msg.get("model")
                if turn_model:
                    models.append(turn_model)

            # Extract text content
            content = msg.get("content", "")
            content_text = ""
            tool_calls = []
            tool_results = []

            if isinstance(content, str):
                content_text = content
            elif isinstance(content, list):
                text_parts = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        tool_calls.append({
                            "tool": block.get("name", ""),
                            "input_preview": json.dumps(block.get("input", {}))[:200],
                        })
                    elif block.get("type") == "tool_result":
                        # Capture tool results -- these contain the real work product
                        # (file contents after edits, bash output, grep results)
                        result_content = block.get("content", "")
                        if isinstance(result_content, list):
                            result_content = " ".join(
                                b.get("text", "") for b in result_content
                                if isinstance(b, dict) and b.get("type") == "text"
                            )
                        result_str = str(result_content)[:2000]
                        if result_str.strip():
                            tool_results.append(result_str)
                        text_parts.append(result_str[:500])
                content_text = "\n".join(text_parts)

            # Skip meta/system messages with XML tags that aren't real user input
            if role == "user" and content_text.startswith("<local-command-"):
                continue
            if role == "user" and content_text.startswith("<command-name>"):
                continue

            timestamp = obj.get("timestamp")
            turns.append({
                "role": role,
                "content_text": content_text,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "timestamp": timestamp,
            })

    if not turns:
        return None

    # Extract project name from path
    # ~/.claude/projects/<project-name>/session-id.jsonl
    # ~/.claude/projects/<project-name>/session-id/subagents/agent-xxx.jsonl
    project = ""
    parts = jsonl_path.parts
    for i, p in enumerate(parts):
        if p == "projects" and i + 1 < len(parts):
            project = parts[i + 1]
            break

    # Detect injected skills from first user message (subagent traces)
    injected_skills = []
    task_prompt = ""
    first_user = next((t for t in turns if t["role"] == "user"), None)
    if first_user:
        injected_skills = _extract_injected_skills(first_user["content_text"])
        task_prompt = _strip_injection_header(first_user["content_text"])

    # Classify success signal from user messages
    user_messages = [t["content_text"] for t in turns if t["role"] == "user"]
    signal = _classify_signal(user_messages)

    model_id = Counter(models).most_common(1)[0][0] if models else None

    return {
        "session_id": session_id or jsonl_path.stem,
        "project": project,
        "is_subagent": is_subagent,
        "turns": turns,
        "injected_skills": injected_skills,
        "task_prompt": task_prompt,
        "signal": signal,
        "git_branch": git_branch,
        "claude_version": claude_version,
        "model_id": model_id,
        "source_file": str(jsonl_path),
    }


def _build_eval_example(parsed_session):
    """Convert a parsed session into a compact eval example for a skill.

    Returns dict suitable for JSONL output, with secrets scrubbed.
    Interleaves assistant text with tool results to capture actual work product,
    not just process narration.
    """
    output_parts = []
    tools_used = set()
    total_len = 0
    max_output = 15000

    for turn in parsed_session["turns"]:
        if total_len >= max_output:
            break
        if turn["role"] == "assistant":
            # Assistant's text response
            text = turn["content_text"].strip()
            if text:
                chunk = text[:4000]
                output_parts.append(chunk)
                total_len += len(chunk)
            for tc in turn["tool_calls"]:
                tools_used.add(tc["tool"])
        elif turn["role"] == "user" and turn.get("tool_results"):
            # Tool results contain the real work product (file contents,
            # bash output, grep results) that show what the agent actually did
            for result in turn["tool_results"]:
                if total_len >= max_output:
                    break
                chunk = result[:2000]
                output_parts.append(f"[Tool Result]: {chunk}")
                total_len += len(chunk)

    agent_output = "\n---\n".join(output_parts)

    example = {
        "task_input": _scrub_secrets(parsed_session["task_prompt"][:5000]),
        "agent_output": _scrub_secrets(agent_output[:max_output]),
        "signal": parsed_session["signal"],
        "tools_used": sorted(tools_used),
        "injected_skills": parsed_session["injected_skills"],
        "turn_count": len(parsed_session["turns"]),
        "project": parsed_session["project"],
        "session_id": parsed_session["session_id"],
        "claude_version": parsed_session["claude_version"],
        "model_id": parsed_session.get("model_id"),
    }
    return example


def harvest_sessions(project_filter=None, skill_filter=None, min_turns=3, include_stale=False):
    """Walk ~/.claude/projects/, extract per-skill eval datasets.

    Args:
        project_filter: only process this project directory name (optional)
        skill_filter: only extract examples for this skill (optional)
        min_turns: minimum conversation turns to include (default 3)
        include_stale: include examples from before the skill was last changed (default False)

    Returns summary dict. Writes per-skill JSONL to distillery/.eval-data/<skill>/sessions.jsonl.
    """
    if not CLAUDE_PROJECTS_DIR.exists():
        print(f"Error: {CLAUDE_PROJECTS_DIR} not found", file=sys.stderr)
        return {"error": "no projects directory"}

    manifest = _load_skill_manifest()
    stale_count = 0

    # Discover all JSONL files
    session_files = []
    subagent_files = []

    for project_dir in sorted(CLAUDE_PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        if project_filter and project_dir.name != project_filter:
            continue

        # Main session files
        for f in project_dir.glob("*.jsonl"):
            session_files.append(f)

        # Subagent traces — inside <session-id>/subagents/
        for f in project_dir.glob("*/subagents/*.jsonl"):
            subagent_files.append(f)

    all_files = session_files + subagent_files
    print(f"Found {len(session_files)} sessions, {len(subagent_files)} subagent traces", file=sys.stderr)

    # Parse all files and group by skill
    skill_examples = defaultdict(list)
    stats = {
        "files_parsed": 0,
        "files_skipped": 0,
        "secrets_detected": 0,
        "subagent_with_skills": 0,
        "signals": {"positive": 0, "negative": 0, "ambiguous": 0},
    }

    for filepath in all_files:
        parsed = _parse_session(filepath)
        if parsed is None:
            stats["files_skipped"] += 1
            continue

        stats["files_parsed"] += 1

        # Filter by turn count
        if len(parsed["turns"]) < min_turns:
            stats["files_skipped"] += 1
            continue

        # Check for secrets in the raw task prompt
        if _contains_secret(parsed["task_prompt"]):
            stats["secrets_detected"] += 1

        stats["signals"][parsed["signal"]] += 1

        # For subagent traces with injected skills, create per-skill examples
        if parsed["injected_skills"]:
            stats["subagent_with_skills"] += 1
            for skill_info in parsed["injected_skills"]:
                skill_name = skill_info["skill"]
                if skill_filter and skill_name != skill_filter:
                    continue
                example = _build_eval_example(parsed)
                example["skill_version"] = skill_info["version"]
                staleness = _is_example_stale(example, skill_name, manifest)
                example["content_stale"] = staleness["content_stale"]
                example["pattern_stale"] = staleness["pattern_stale"]
                example["model_stale"] = staleness["model_stale"]
                if not include_stale and (staleness["content_stale"] or staleness["model_stale"]):
                    stale_count += 1
                    continue
                skill_examples[skill_name].append(example)

        # For main sessions (no injection), still useful as general task examples
        # but don't attribute to any specific skill
        elif not parsed["is_subagent"]:
            example = _build_eval_example(parsed)
            skill_examples["_unattributed"].append(example)

    # Write per-skill JSONL files
    EVAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    written = {}

    for skill_name, examples in sorted(skill_examples.items()):
        skill_dir = EVAL_DATA_DIR / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)
        out_path = skill_dir / "sessions.jsonl"

        with open(out_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")

        written[skill_name] = {
            "count": len(examples),
            "positive": sum(1 for e in examples if e["signal"] == "positive"),
            "negative": sum(1 for e in examples if e["signal"] == "negative"),
            "ambiguous": sum(1 for e in examples if e["signal"] == "ambiguous"),
            "path": str(out_path),
        }
        print(f"  {skill_name}: {len(examples)} examples → {out_path}", file=sys.stderr)

    if stale_count:
        print(f"  Filtered {stale_count} stale examples (use --include-stale to include)", file=sys.stderr)

    return {
        "stats": stats,
        "skills": written,
        "total_examples": sum(v["count"] for v in written.values()),
        "stale_filtered": stale_count,
    }


# Heuristic indicators that a short message *might* be negative even if
# _NEGATIVE_SIGNAL_PATTERNS doesn't match. Used by discover-signals to
# surface candidates for human review and potential pattern promotion.
_CANDIDATE_NEGATIVE_HINTS = _re.compile(
    r"(?:"
    r"\bwhy\s+(?:is|are|was|were|did|does|do)\b"  # questioning agent behavior
    r"|\bthat\s+(?:is|was)\s+not\b"
    r"|\bnot\s+(?:correct|right|accurate|valid|what)\b"
    r"|\bwrong\b"
    r"|\bmissing\b"
    r"|\bbug\b"
    r"|\bfail\b"
    r"|\berror\b"
    r"|\bregress\b"
    r"|\bbroke\b"
    r"|\bfix\b"
    r"|\bremove\b.*\b(?:it|this|that|crap|junk|garbage)\b"
    r"|\bi\s+(?:said|told|asked|mentioned)\b"
    r"|\binvalid\b"
    r"|\bnot\s+(?:needed|necessary|applicable|relevant)\b"
    r"|\bstop\b"
    r"|\bno\b.*\b(?:need|don'?t|shouldn'?t|won'?t)\b"
    r")",
    _re.IGNORECASE,
)


def discover_signals(top_n=30):
    """Scan session history for short user messages that might indicate undiscovered
    negative patterns. Surfaces candidates not matched by _NEGATIVE_SIGNAL_PATTERNS
    but flagged by looser heuristics, ranked by frequency.

    Returns dict with candidate patterns and example messages for human review.
    """
    if not CLAUDE_PROJECTS_DIR.exists():
        return {"error": "no projects directory"}

    # Collect all short user messages that pass our filters but are NOT
    # matched by the current negative pattern set
    unmatched_candidates = defaultdict(list)  # hint_phrase -> [messages]
    all_unmatched = []

    for jsonl in CLAUDE_PROJECTS_DIR.glob("*/*.jsonl"):
        if "subagents" in str(jsonl):
            continue
        try:
            with open(jsonl) as f:
                for line in f:
                    try:
                        obj = json.loads(line.strip())
                        if obj.get("type") != "user":
                            continue
                        msg = obj.get("message", {})
                        if msg.get("role") != "user":
                            continue
                        content = msg.get("content", "")
                        text = ""
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            for b in content:
                                if isinstance(b, dict) and b.get("type") == "text":
                                    text += b.get("text", "")
                        # Same filters as _classify_signal
                        if len(text) > 500 or len(text) < 8:
                            continue
                        stripped = text.lstrip()
                        if stripped.startswith("<"):
                            continue
                        if stripped.startswith("---\n") or stripped.startswith("```") or stripped.startswith("#"):
                            continue
                        if stripped[0].isdigit() and "\t" in stripped[:10]:
                            continue
                        # Skip if already matched by current patterns
                        if _NEGATIVE_SIGNAL_PATTERNS.search(text):
                            continue
                        # Check candidate hints
                        m = _CANDIDATE_NEGATIVE_HINTS.search(text)
                        if m:
                            hint = m.group().strip().lower()
                            unmatched_candidates[hint].append(text.strip()[:200])
                            all_unmatched.append(text.strip()[:200])
                    except (json.JSONDecodeError, IndexError):
                        continue
        except OSError:
            continue

    # Rank by frequency — most common unmatched hint phrases first
    ranked = sorted(unmatched_candidates.items(), key=lambda x: -len(x[1]))[:top_n]

    results = []
    for hint, messages in ranked:
        # Deduplicate similar messages
        unique = list(dict.fromkeys(messages))[:8]
        results.append({
            "hint_match": hint,
            "count": len(messages),
            "unique_examples": len(set(messages)),
            "examples": unique,
        })

    return {
        "total_unmatched_with_hints": len(all_unmatched),
        "distinct_hints": len(unmatched_candidates),
        "top_candidates": results,
    }


def _parse_judge_response(text):
    """Extract scores from judge JSON response. Returns dict or None on parse failure."""
    if not text:
        return None
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    if text.startswith("json"):
        text = text[4:].strip()

    # Try direct parse first, then search for JSON object in longer text
    # (reasoning models may embed the JSON within their thinking)
    data = None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        # Search for a JSON object containing "correctness"
        for m in _re.finditer(r'\{[^{}]*"correctness"[^{}]*\}', text):
            try:
                data = json.loads(m.group())
                break
            except json.JSONDecodeError:
                continue
    if data is None:
        return None

    try:
        correctness = max(0, min(10, int(data.get("correctness", 0))))
        procedure = max(0, min(10, int(data.get("procedure_following", 0))))
        conciseness = max(0, min(10, int(data.get("conciseness", 0))))
        # Normalize to 0-1 and compute weighted composite
        c, p, co = correctness / 10, procedure / 10, conciseness / 10
        composite = 0.5 * c + 0.3 * p + 0.2 * co
        return {
            "correctness": correctness,
            "procedure_following": procedure,
            "conciseness": conciseness,
            "composite": round(composite, 3),
            "notes": data.get("notes", ""),
        }
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def _find_skill_path(name):
    """Find a skill's SKILL.md path. Checks plugin dir first, then generated-skills."""
    plugin_path = PLUGIN_DIR / "skills" / name / "SKILL.md"
    if plugin_path.exists():
        return plugin_path
    generated_path = GENERATED_DIR / name / "SKILL.md"
    if generated_path.exists():
        return generated_path
    return None


def _extract_skill_keywords(skill_text):
    """Extract relevance keywords from a skill's YAML description and first section.

    Returns a set of lowercase keyword strings (2+ chars) for fast relevance checking.
    """
    keywords = set()
    # Extract description from YAML frontmatter
    if skill_text.startswith("---"):
        parts = skill_text.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            for line in frontmatter.splitlines():
                if line.strip().startswith("description:") or line.strip().startswith("name:"):
                    value = line.split(":", 1)[1].strip().strip("'\"").strip(">-").strip()
                    keywords.update(w.lower() for w in _re.findall(r'[a-zA-Z]{3,}', value))
                elif line.startswith("  ") and keywords:
                    # continuation line of description
                    keywords.update(w.lower() for w in _re.findall(r'[a-zA-Z]{3,}', line))

    # Extract from skill name (hyphen-separated)
    name_match = _re.search(r'^name:\s*(.+)', skill_text, _re.MULTILINE)
    if name_match:
        keywords.update(name_match.group(1).strip().split("-"))

    # Remove common stop words that would match everything
    stop = {"the", "and", "for", "use", "when", "with", "this", "that", "from",
            "are", "not", "all", "any", "you", "has", "can", "will", "how",
            "been", "being", "into", "also", "such", "than", "each", "does",
            "should", "before", "after", "asked", "apply", "proactively",
            "starting", "complex", "tasks"}
    keywords -= stop
    return keywords


def _check_skill_relevance(task_input, skill_keywords, threshold=2):
    """Check if a task is relevant to a skill based on keyword overlap.

    Returns (is_relevant, overlap_count).
    """
    task_lower = task_input.lower()
    task_words = set(_re.findall(r'[a-zA-Z]{3,}', task_lower))
    overlap = skill_keywords & task_words
    return len(overlap) >= threshold, len(overlap)


def _score_candidate(example, skill_keywords):
    """Heuristic quality score for a harvested example, used to rank golden dataset candidates.

    Returns a float 0-1. Higher = better candidate for golden dataset.
    Factors: signal clarity, relevance to skill, output substance, session diversity.
    """
    score = 0.0

    # Signal clarity: clear positive/negative is better than ambiguous
    signal = example.get("signal", "ambiguous")
    if signal in ("positive", "negative"):
        score += 0.3
    # Negative examples are slightly more valuable for eval (harder to get right)
    if signal == "negative":
        score += 0.1

    # Relevance: keyword overlap with skill
    task = example.get("task_input", "")
    _, overlap = _check_skill_relevance(task, skill_keywords, threshold=0)
    # Normalize: 5+ keyword overlaps = max relevance score
    score += min(overlap / 5, 1.0) * 0.3

    # Output substance: longer, more complete agent output is better for eval
    output = example.get("agent_output", "")
    output_len = len(output)
    if output_len > 2000:
        score += 0.15
    elif output_len > 500:
        score += 0.1
    elif output_len > 100:
        score += 0.05

    # Task substance: longer, more specific tasks are better eval material
    task_len = len(task)
    if task_len > 200:
        score += 0.1
    elif task_len > 50:
        score += 0.05

    # Version tracked: examples with skill_version are more useful (temporal context)
    if example.get("skill_version"):
        score += 0.05

    return round(min(score, 1.0), 3)


def build_golden(skill_name, top_n=20, auto=False):
    """Build a golden eval dataset from harvested session data.

    Ranks harvested examples by quality heuristics (relevance, output substance,
    signal clarity), applies relevance filtering, and outputs candidates.

    With --auto: writes golden.jsonl directly using heuristic labels.
    Without --auto: writes a review file (candidates.jsonl) for human annotation,
    then run build-golden --skill X --approve to promote to golden.jsonl.

    Args:
        skill_name: skill directory name
        top_n: number of candidates to select
        auto: if True, skip human review and label automatically

    Returns summary dict.
    """
    # Load skill for keyword extraction
    skill_path = _find_skill_path(skill_name)
    if not skill_path:
        print(f"Error: skill '{skill_name}' not found", file=sys.stderr)
        sys.exit(1)
    skill_text = skill_path.read_text()
    skill_keywords = _extract_skill_keywords(skill_text)

    # Load harvested sessions
    sessions_path = EVAL_DATA_DIR / skill_name / "sessions.jsonl"
    if not sessions_path.exists():
        print(f"Error: {sessions_path} not found. Run harvest-sessions first.", file=sys.stderr)
        sys.exit(1)

    examples = []
    with open(sessions_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    # Filter for relevance
    relevant = []
    for ex in examples:
        is_rel, _ = _check_skill_relevance(ex.get("task_input", ""), skill_keywords)
        if is_rel:
            relevant.append(ex)

    print(f"Loaded {len(examples)} examples, {len(relevant)} relevant to '{skill_name}'", file=sys.stderr)

    if not relevant:
        print(f"Error: no relevant examples. Keywords: {sorted(skill_keywords)}", file=sys.stderr)
        sys.exit(1)

    # Score and rank
    scored = []
    for ex in relevant:
        quality = _score_candidate(ex, skill_keywords)
        scored.append((quality, ex))
    scored.sort(key=lambda x: -x[0])

    # Take balanced sample: aim for ~50/50 positive/negative from top candidates
    top_pool = scored[:top_n * 3]  # over-select to allow balancing
    pos_pool = [(q, e) for q, e in top_pool if e.get("signal") == "positive"]
    neg_pool = [(q, e) for q, e in top_pool if e.get("signal") == "negative"]
    amb_pool = [(q, e) for q, e in top_pool if e.get("signal") == "ambiguous"]

    half = top_n // 2
    selected = pos_pool[:half] + neg_pool[:half]
    remaining = top_n - len(selected)
    if remaining > 0:
        # Fill from whichever pool has more
        extras = sorted(pos_pool[half:] + neg_pool[half:] + amb_pool, key=lambda x: -x[0])
        selected.extend(extras[:remaining])
    selected = selected[:top_n]

    # Build candidate records
    candidates = []
    for quality, ex in selected:
        candidate = {
            "task_input": ex["task_input"],
            "agent_output": ex["agent_output"],
            "signal": ex.get("signal", "ambiguous"),
            "quality_score": quality,
            "session_id": ex.get("session_id", ""),
            "skill_version": ex.get("skill_version"),
            "tools_used": ex.get("tools_used", []),
            "turn_count": ex.get("turn_count", 0),
            "project": ex.get("project", ""),
            # Label: auto-assign from signal, or "review" for human annotation
            "label": ex.get("signal", "ambiguous") if auto else "review",
        }
        candidates.append(candidate)

    # Write output
    skill_eval_dir = EVAL_DATA_DIR / skill_name
    skill_eval_dir.mkdir(parents=True, exist_ok=True)

    # Always write candidates.jsonl (keeps state consistent)
    candidates_path = skill_eval_dir / "candidates.jsonl"
    with open(candidates_path, "w") as f:
        for c in candidates:
            f.write(json.dumps(c) + "\n")

    if auto:
        # Also write golden.jsonl directly (labels already set from signal)
        golden_path = skill_eval_dir / "golden.jsonl"
        with open(golden_path, "w") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")
        out_path = golden_path
        print(f"Wrote {len(candidates)} auto-labeled examples → {golden_path}", file=sys.stderr)
    else:
        out_path = candidates_path
        print(f"Wrote {len(candidates)} candidates for review → {candidates_path}", file=sys.stderr)
        print(f"Review the file, change 'label' from 'review' to 'positive'/'negative'/'skip',", file=sys.stderr)
        print(f"then run: distiller.py approve-golden {skill_name}", file=sys.stderr)

    pos = sum(1 for c in candidates if c["signal"] == "positive")
    neg = sum(1 for c in candidates if c["signal"] == "negative")

    return {
        "skill": skill_name,
        "total_harvested": len(examples),
        "relevant": len(relevant),
        "selected": len(candidates),
        "positive": pos,
        "negative": neg,
        "mean_quality": round(sum(c["quality_score"] for c in candidates) / len(candidates), 3) if candidates else 0,
        "output": str(out_path),
        "mode": "auto" if auto else "review",
    }


def approve_golden(skill_name):
    """Promote reviewed candidates.jsonl to golden.jsonl.

    Reads candidates.jsonl, keeps entries labeled 'positive' or 'negative'
    (skips 'review' and 'skip'), writes to golden.jsonl.
    """
    candidates_path = EVAL_DATA_DIR / skill_name / "candidates.jsonl"
    if not candidates_path.exists():
        print(f"Error: {candidates_path} not found. Run build-golden first.", file=sys.stderr)
        sys.exit(1)

    candidates = []
    with open(candidates_path) as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(json.loads(line))

    approved = [c for c in candidates if c.get("label") in ("positive", "negative")]
    skipped = [c for c in candidates if c.get("label") == "skip"]
    unreviewed = [c for c in candidates if c.get("label") == "review"]

    if unreviewed:
        print(f"Warning: {len(unreviewed)} candidates still labeled 'review' (skipped)", file=sys.stderr)

    if not approved:
        print("Error: no approved candidates (label must be 'positive' or 'negative')", file=sys.stderr)
        sys.exit(1)

    golden_path = EVAL_DATA_DIR / skill_name / "golden.jsonl"
    with open(golden_path, "w") as f:
        for c in approved:
            f.write(json.dumps(c) + "\n")

    pos = sum(1 for c in approved if c["label"] == "positive")
    neg = sum(1 for c in approved if c["label"] == "negative")
    print(f"Wrote {len(approved)} golden examples ({pos} positive, {neg} negative) → {golden_path}", file=sys.stderr)

    return {
        "skill": skill_name,
        "approved": len(approved),
        "positive": pos,
        "negative": neg,
        "skipped": len(skipped),
        "unreviewed": len(unreviewed),
        "path": str(golden_path),
    }


def analyze_misfires(min_examples=30, include_stale=False):
    """Identify skills that are frequently injected into tasks where they're not needed.

    Reads all harvested session data across all skills. For each skill, checks how
    often it was injected alongside other skills (co-injection) and how often the
    task text actually relates to the skill's domain (relevance). Skills with high
    injection count but low relevance are misfiring -- their trigger regex is too broad.

    Returns ranked list of misfiring skills with suggested regex tightening.
    """
    if not EVAL_DATA_DIR.exists():
        print("Error: no eval data. Run harvest-sessions first.", file=sys.stderr)
        sys.exit(1)

    manifest = _load_skill_manifest()

    # Collect all examples across all skills
    all_examples = []
    stale_count = 0
    for skill_dir in sorted(EVAL_DATA_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name == "_unattributed":
            continue
        sessions_file = skill_dir / "sessions.jsonl"
        if not sessions_file.exists():
            continue
        with open(sessions_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                if not include_stale:
                    staleness = _is_example_stale(ex, skill_dir.name, manifest)
                    if staleness["pattern_stale"]:
                        stale_count += 1
                        continue
                all_examples.append(ex)

    if stale_count:
        print(f"  Filtered {stale_count} stale examples (use --include-stale to include)", file=sys.stderr)

    # For each skill, count: total injections, relevant injections, co-injection patterns
    skill_stats = defaultdict(lambda: {
        "injected": 0, "relevant": 0, "irrelevant": 0,
        "positive": 0, "negative": 0,
        "co_injected_with": defaultdict(int),
        "irrelevant_task_samples": [],
    })

    # Load skill keywords for relevance checking
    skill_keywords_cache = {}
    for skill_dir in (PLUGIN_DIR / "skills").iterdir():
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            skill_keywords_cache[skill_dir.name] = _extract_skill_keywords(skill_file.read_text())

    for ex in all_examples:
        injected = ex.get("injected_skills", [])
        task_input = ex.get("task_input", "")
        signal = ex.get("signal", "ambiguous")

        for skill_info in injected:
            skill_name = skill_info["skill"]
            stats = skill_stats[skill_name]
            stats["injected"] += 1

            if signal == "positive":
                stats["positive"] += 1
            elif signal == "negative":
                stats["negative"] += 1

            # Check relevance
            keywords = skill_keywords_cache.get(skill_name, set())
            if keywords:
                is_rel, overlap = _check_skill_relevance(task_input, keywords)
                if is_rel:
                    stats["relevant"] += 1
                else:
                    stats["irrelevant"] += 1
                    if len(stats["irrelevant_task_samples"]) < 3:
                        stats["irrelevant_task_samples"].append(task_input[:150])

            # Track co-injection
            for other in injected:
                if other["skill"] != skill_name:
                    stats["co_injected_with"][other["skill"]] += 1

    # Rank by misfire rate (irrelevant / injected)
    results = []
    for skill_name, stats in sorted(skill_stats.items()):
        total = stats["injected"]
        if total < min_examples:
            continue
        irrelevant = stats["irrelevant"]
        misfire_rate = irrelevant / total if total > 0 else 0
        top_co = sorted(stats["co_injected_with"].items(), key=lambda x: -x[1])[:3]

        results.append({
            "skill": skill_name,
            "injected": total,
            "relevant": stats["relevant"],
            "irrelevant": irrelevant,
            "misfire_rate": round(misfire_rate, 3),
            "positive_rate": round(stats["positive"] / total, 3) if total else 0,
            "top_co_injected": [{"skill": s, "count": c} for s, c in top_co],
            "irrelevant_samples": stats["irrelevant_task_samples"],
        })

    results.sort(key=lambda x: -x["misfire_rate"])

    return {
        "total_examples": len(all_examples),
        "skills_analyzed": len(results),
        "misfires": results,
    }


def analyze_outcomes(min_examples=5, include_stale=False):
    """Analyze skill injection outcomes by project context.

    Correlates skill injection with session signal (positive/negative) per project.
    Surfaces (skill, project) pairs where the negative rate is notably above the
    skill's global average -- indicating the skill performs worse in that context.

    Returns ranked list with anomalies (delta > 10pp) highlighted.
    """
    if not EVAL_DATA_DIR.exists():
        print("Error: no eval data. Run harvest-sessions first.", file=sys.stderr)
        sys.exit(1)

    manifest = _load_skill_manifest()

    # {skill: {project: {positive: N, negative: N, ambiguous: N}}}
    skill_project = defaultdict(lambda: defaultdict(lambda: {"positive": 0, "negative": 0, "ambiguous": 0}))
    skill_global = defaultdict(lambda: {"positive": 0, "negative": 0, "ambiguous": 0})
    stale_count = 0

    for skill_dir in sorted(EVAL_DATA_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name == "_unattributed":
            continue
        sessions_file = skill_dir / "sessions.jsonl"
        if not sessions_file.exists():
            continue
        skill_name = skill_dir.name
        with open(sessions_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                ex = json.loads(line)
                if not include_stale:
                    staleness = _is_example_stale(ex, skill_name, manifest)
                    if staleness["content_stale"] or staleness["model_stale"]:
                        stale_count += 1
                        continue
                signal = ex.get("signal", "ambiguous")
                project = ex.get("project", "_unknown")
                skill_project[skill_name][project][signal] += 1
                skill_global[skill_name][signal] += 1

    if stale_count:
        print(f"  Filtered {stale_count} stale examples (use --include-stale to include)", file=sys.stderr)

    # Find (skill, project) pairs where negative rate exceeds global average
    outcomes = []
    for sname, projects in sorted(skill_project.items()):
        g = skill_global[sname]
        g_total = g["positive"] + g["negative"] + g["ambiguous"]
        if g_total < min_examples:
            continue
        g_neg_rate = g["negative"] / g_total

        for project, stats in sorted(projects.items()):
            total = stats["positive"] + stats["negative"] + stats["ambiguous"]
            if total < min_examples:
                continue
            neg_rate = stats["negative"] / total
            delta = neg_rate - g_neg_rate

            outcomes.append({
                "skill": sname,
                "project": project,
                "injected": total,
                "positive": stats["positive"],
                "negative": stats["negative"],
                "ambiguous": stats["ambiguous"],
                "negative_rate": round(neg_rate, 3),
                "global_negative_rate": round(g_neg_rate, 3),
                "delta": round(delta, 3),
            })

    outcomes.sort(key=lambda x: -x["delta"])

    # Per-skill global summary
    global_summary = []
    for sname, stats in sorted(skill_global.items()):
        total = stats["positive"] + stats["negative"] + stats["ambiguous"]
        if total < min_examples:
            continue
        global_summary.append({
            "skill": sname,
            "total": total,
            "positive": stats["positive"],
            "negative": stats["negative"],
            "ambiguous": stats["ambiguous"],
            "negative_rate": round(stats["negative"] / total, 3),
        })
    global_summary.sort(key=lambda x: -x["negative_rate"])

    return {
        "total_skills": len(skill_global),
        "total_pairs": len(outcomes),
        "stale_filtered": stale_count,
        "anomalies": [o for o in outcomes if o["delta"] > 0.1],
        "outcomes": outcomes,
        "global_summary": global_summary,
    }


def diagnose_negatives(skill_name, max_examples=10, include_stale=False):
    """Analyze negative-signal sessions for a skill to identify concrete failure patterns.

    Reads harvested sessions where the user expressed dissatisfaction (negative signal),
    extracts the task, the agent output, and the user's negative feedback, then uses
    Claude to identify patterns and suggest specific skill text improvements.

    Args:
        skill_name: skill to diagnose
        max_examples: max negative examples to analyze (default 10)
        include_stale: include examples from before the skill was last changed (default False)

    Returns dict with failure patterns and suggested skill improvements.
    """
    # Load skill text
    skill_path = _find_skill_path(skill_name)
    if not skill_path:
        print(f"Error: skill '{skill_name}' not found", file=sys.stderr)
        sys.exit(1)
    skill_text = skill_path.read_text()

    manifest = _load_skill_manifest()

    # Load sessions and filter to negatives
    sessions_path = EVAL_DATA_DIR / skill_name / "sessions.jsonl"
    if not sessions_path.exists():
        print(f"Error: no session data for '{skill_name}'. Run harvest-sessions first.", file=sys.stderr)
        sys.exit(1)

    negatives = []
    stale_count = 0
    with open(sessions_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            if ex.get("signal") != "negative":
                continue
            if not include_stale:
                staleness = _is_example_stale(ex, skill_name, manifest)
                if staleness["content_stale"] or staleness["model_stale"]:
                    stale_count += 1
                    continue
            negatives.append(ex)

    if stale_count:
        print(f"  Filtered {stale_count} stale negative examples (use --include-stale to include)", file=sys.stderr)

    if not negatives:
        print(f"No negative-signal sessions for '{skill_name}'.", file=sys.stderr)
        return {"skill": skill_name, "negative_count": 0, "patterns": [], "suggestions": []}

    # Apply relevance filter -- only analyze negatives where the skill was actually relevant
    skill_keywords = _extract_skill_keywords(skill_text)
    relevant_negatives = []
    for ex in negatives:
        is_rel, _ = _check_skill_relevance(ex.get("task_input", ""), skill_keywords)
        if is_rel:
            relevant_negatives.append(ex)

    # Use relevant negatives if enough, otherwise fall back to all negatives
    pool = relevant_negatives if len(relevant_negatives) >= 3 else negatives
    sample = pool[:max_examples]

    print(f"Analyzing {len(sample)} negative sessions for '{skill_name}' ({len(relevant_negatives)} relevant of {len(negatives)} total)", file=sys.stderr)

    # Build a digest of negative sessions for analysis
    cases = []
    for i, ex in enumerate(sample):
        cases.append(
            f"--- CASE {i+1} (signal: negative, session: {ex.get('session_id', '?')[:12]}) ---\n"
            f"TASK: {ex.get('task_input', '')[:1000]}\n\n"
            f"AGENT OUTPUT (truncated): {ex.get('agent_output', '')[:2000]}\n"
        )

    cases_text = "\n\n".join(cases)

    # Ask Claude to analyze the failure patterns
    prompt = (
        f"You are analyzing why a skill file produces negative outcomes. "
        f"The skill is injected into AI agent sessions to guide behavior.\n\n"
        f"SKILL FILE ({skill_name}):\n{skill_text[:6000]}\n\n"
        f"NEGATIVE-SIGNAL SESSIONS (user expressed dissatisfaction):\n\n{cases_text[:12000]}\n\n"
        f"Analyze these failures and respond with ONLY valid JSON:\n"
        f'{{"patterns": ['
        f'{{"pattern": "description of recurring failure", "frequency": "N of M cases", "example_case": 1}},'
        f'...], '
        f'"suggestions": ['
        f'{{"section": "which part of the skill to change", "current": "current text (brief)", '
        f'"proposed": "proposed replacement (brief)", "rationale": "why this fixes the pattern"}},'
        f'...], '
        f'"summary": "one paragraph overall diagnosis"}}'
    )

    result = _claude_cli_request(prompt, model=DEFAULT_CLI_MODEL)

    if result["status"] != "ok":
        return {"skill": skill_name, "error": result.get("error", "unknown")}

    # Parse response
    response_text = result["response"]
    # Strip markdown fences
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1] if "\n" in response_text else response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
    if response_text.startswith("json"):
        response_text = response_text[4:].strip()

    try:
        analysis = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        for m in _re.finditer(r'\{[\s\S]*"patterns"[\s\S]*"suggestions"[\s\S]*\}', response_text):
            try:
                analysis = json.loads(m.group())
                break
            except json.JSONDecodeError:
                continue
        else:
            return {
                "skill": skill_name,
                "negative_count": len(negatives),
                "error": f"Could not parse analysis: {response_text[:200]}",
            }

    return {
        "skill": skill_name,
        "negative_count": len(negatives),
        "relevant_negatives": len(relevant_negatives),
        "analyzed": len(sample),
        "patterns": analysis.get("patterns", []),
        "suggestions": analysis.get("suggestions", []),
        "summary": analysis.get("summary", ""),
        "cost_usd": result.get("cost_usd", 0),
    }


def dspy_eval(skill_name, dataset="sessions", max_examples=20, model=None, backend="claude-cli"):
    """Score a skill's effectiveness using LLM-as-judge on harvested eval data.

    Loads the skill's SKILL.md and eval dataset, sends each example to the judge
    model and aggregates scores.

    Args:
        skill_name: skill directory name (e.g., "planning", "code-review")
        dataset: "sessions" for harvested data, or path to a custom JSONL file
        max_examples: max examples to score (default 20, controls cost)
        model: override eval model (default depends on backend)
        backend: "openrouter" (DeepSeek V3.2) or "claude-cli" (Opus 4.7 via claude -p)

    Returns dict with per-example scores and aggregated metrics.
    """
    use_cli = backend == "claude-cli"

    if not use_cli:
        load_env()
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            print("Error: OPENROUTER_API_KEY not set in .env", file=sys.stderr)
            sys.exit(1)

    # Load skill
    skill_path = _find_skill_path(skill_name)
    if not skill_path:
        print(f"Error: skill '{skill_name}' not found in plugin or generated-skills", file=sys.stderr)
        sys.exit(1)
    skill_text = skill_path.read_text()
    print(f"Loaded skill: {skill_path}", file=sys.stderr)

    # Load eval dataset
    if dataset == "sessions":
        dataset_path = EVAL_DATA_DIR / skill_name / "sessions.jsonl"
    elif dataset == "golden":
        dataset_path = EVAL_DATA_DIR / skill_name / "golden.jsonl"
    else:
        dataset_path = Path(dataset)

    if not dataset_path.exists():
        print(f"Error: dataset not found at {dataset_path}", file=sys.stderr)
        print("Run 'harvest-sessions' first to generate eval data.", file=sys.stderr)
        sys.exit(1)

    examples = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))

    if not examples:
        print(f"Error: no examples in {dataset_path}", file=sys.stderr)
        sys.exit(1)

    # Filter for relevance: only keep examples where the task is actually
    # about this skill's domain, not just where the skill was injected alongside others.
    skill_keywords = _extract_skill_keywords(skill_text)
    relevant = []
    irrelevant = 0
    for ex in examples:
        is_rel, overlap = _check_skill_relevance(ex.get("task_input", ""), skill_keywords)
        if is_rel:
            relevant.append(ex)
        else:
            irrelevant += 1

    if irrelevant:
        print(f"Filtered {irrelevant}/{len(examples)} irrelevant examples (keywords: {sorted(skill_keywords)[:10]}...)", file=sys.stderr)
    if not relevant:
        print(f"Error: no relevant examples after filtering. Keywords: {sorted(skill_keywords)}", file=sys.stderr)
        sys.exit(1)

    # Prioritize: positive examples first (skill worked), then negative (skill failed),
    # so we get a balanced sample if capped
    positive = [e for e in relevant if e.get("signal") == "positive"]
    negative = [e for e in relevant if e.get("signal") == "negative"]
    ambiguous = [e for e in relevant if e.get("signal") == "ambiguous"]

    # Take balanced sample: half positive, half negative (when available)
    half = max_examples // 2
    sampled = positive[:half] + negative[:half] + ambiguous[:max(0, max_examples - 2 * half)]
    sampled = sampled[:max_examples]

    print(f"Evaluating {len(sampled)} examples ({len(positive)} pos, {len(negative)} neg, {len(ambiguous)} amb available)", file=sys.stderr)

    # Configure model and backend
    if use_cli:
        eval_model = model or DEFAULT_CLI_MODEL
        print(f"Backend: claude-cli (model: {eval_model})", file=sys.stderr)
    else:
        eval_model = model or DEFAULT_EVAL_MODEL
        model_id, provider_slug = _parse_model_spec(eval_model)
        print(f"Backend: openrouter (model: {eval_model})", file=sys.stderr)

    # Score each example
    scored = []
    total_tokens = 0
    total_cost = 0.0

    for i, ex in enumerate(sampled):
        task_input = ex.get("task_input", "")
        agent_output = ex.get("agent_output", "")

        if not task_input or not agent_output:
            print(f"  [{i+1}/{len(sampled)}] skipped (empty input/output)", file=sys.stderr)
            continue

        judge_user = _JUDGE_USER_TEMPLATE.format(
            skill_text=skill_text[:8000],
            task_input=task_input[:5000],
            agent_output=agent_output[:12000],
        )

        if use_cli:
            # Combine system + user into a single prompt for claude -p
            full_prompt = _JUDGE_SYSTEM_PROMPT + "\n\n" + judge_user
            result = _claude_cli_request(full_prompt, model=eval_model)
        else:
            result = _openrouter_request(
                api_key, model_id, provider_slug,
                [
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": judge_user},
                ],
                max_tokens=8000,
                temperature=0.1,
                reasoning=DEFAULT_EVAL_REASONING,
            )

        if result["status"] != "ok":
            print(f"  [{i+1}/{len(sampled)}] error: {result.get('error', 'unknown')}", file=sys.stderr)
            scored.append({
                "index": i,
                "signal": ex.get("signal", ""),
                "session_id": ex.get("session_id", ""),
                "error": result.get("error", "unknown"),
            })
            continue

        total_tokens += result.get("tokens", 0)
        total_cost += result.get("cost_usd", 0)
        # Try content first; if empty (reasoning-only models), extract JSON from reasoning
        scores = _parse_judge_response(result["response"])
        if scores is None and result.get("reasoning"):
            scores = _parse_judge_response(result["reasoning"])

        if scores is None:
            print(f"  [{i+1}/{len(sampled)}] parse error: {result['response'][:100]}", file=sys.stderr)
            scored.append({
                "index": i,
                "signal": ex.get("signal", ""),
                "session_id": ex.get("session_id", ""),
                "error": f"parse_error: {result['response'][:200]}",
            })
            continue

        scored.append({
            "index": i,
            "signal": ex.get("signal", ""),
            "session_id": ex.get("session_id", ""),
            "skill_version": ex.get("skill_version"),
            **scores,
        })
        print(
            f"  [{i+1}/{len(sampled)}] {ex.get('signal', '?'):8s} "
            f"C={scores['correctness']} P={scores['procedure_following']} "
            f"Co={scores['conciseness']} composite={scores['composite']}",
            file=sys.stderr,
        )

    # Aggregate
    valid_scores = [s for s in scored if "composite" in s]
    if not valid_scores:
        return {"skill": skill_name, "error": "no valid scores", "scored": scored}

    avg = lambda key: round(sum(s[key] for s in valid_scores) / len(valid_scores), 3)

    # Split by signal
    pos_scores = [s for s in valid_scores if s["signal"] == "positive"]
    neg_scores = [s for s in valid_scores if s["signal"] == "negative"]

    summary = {
        "mean_composite": avg("composite"),
        "mean_correctness": avg("correctness"),
        "mean_procedure_following": avg("procedure_following"),
        "mean_conciseness": avg("conciseness"),
        "count": len(valid_scores),
        "errors": len(scored) - len(valid_scores),
    }

    if pos_scores:
        pos_avg = lambda key: round(sum(s[key] for s in pos_scores) / len(pos_scores), 3)
        summary["positive"] = {
            "count": len(pos_scores),
            "mean_composite": pos_avg("composite"),
        }
    if neg_scores:
        neg_avg = lambda key: round(sum(s[key] for s in neg_scores) / len(neg_scores), 3)
        summary["negative"] = {
            "count": len(neg_scores),
            "mean_composite": neg_avg("composite"),
        }

    result = {
        "skill": skill_name,
        "backend": backend,
        "model": eval_model,
        "dataset": str(dataset_path),
        "total_tokens": total_tokens,
        "summary": summary,
        "scores": scored,
    }
    if total_cost > 0:
        result["total_cost_usd"] = round(total_cost, 4)
    return result


def _save_eval_history(report):
    """Append an eval run to the skill's eval-history.jsonl. Returns the previous run (or None)."""
    from datetime import datetime, timezone

    skill_name = report.get("skill", "")
    if not skill_name or "error" in report:
        return None

    history_path = EVAL_DATA_DIR / skill_name / "eval-history.jsonl"
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Read previous runs to find the last one
    previous = None
    if history_path.exists():
        with open(history_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        previous = json.loads(line)
                    except json.JSONDecodeError:
                        continue

    # Build compact history entry (no per-example scores, just summary)
    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skill": skill_name,
        "backend": report.get("backend", ""),
        "model": report.get("model", ""),
        "dataset": report.get("dataset", "").split("/")[-1],  # just filename
        "examples": report.get("summary", {}).get("count", 0),
        "composite": report.get("summary", {}).get("mean_composite", 0),
        "correctness": report.get("summary", {}).get("mean_correctness", 0),
        "procedure": report.get("summary", {}).get("mean_procedure_following", 0),
        "conciseness": report.get("summary", {}).get("mean_conciseness", 0),
        "tokens": report.get("total_tokens", 0),
    }
    cost = report.get("total_cost_usd")
    if cost:
        entry["cost_usd"] = cost
    if report.get("summary", {}).get("positive"):
        entry["positive_composite"] = report["summary"]["positive"].get("mean_composite", 0)
    if report.get("summary", {}).get("negative"):
        entry["negative_composite"] = report["summary"]["negative"].get("mean_composite", 0)

    with open(history_path, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return previous


def _format_eval_comparison(report, previous):
    """Format eval results with comparison to previous run. Returns lines for stderr."""
    lines = []
    summary = report.get("summary", {})
    composite = summary.get("mean_composite", 0)
    correctness = summary.get("mean_correctness", 0)
    procedure = summary.get("mean_procedure_following", 0)
    conciseness = summary.get("mean_conciseness", 0)
    count = summary.get("count", 0)
    errors = summary.get("errors", 0)

    lines.append("")
    lines.append(f"  Skill: {report['skill']}  ({report.get('backend', '?')}/{report.get('model', '?')})")
    lines.append(f"  Examples: {count}  Errors: {errors}")

    def delta_str(current, prev_key, prev_data):
        if not prev_data:
            return ""
        prev_val = prev_data.get(prev_key, 0)
        if prev_val == 0:
            return ""
        diff = current - prev_val
        pct = (diff / prev_val) * 100 if prev_val else 0
        arrow = "+" if diff > 0 else ""
        return f"  ({arrow}{diff:.3f}, {arrow}{pct:.0f}%)"

    prev_s = previous  # previous is already a flat history entry
    lines.append(f"  Composite:  {composite:.3f}{delta_str(composite, 'composite', prev_s)}")
    lines.append(f"  Correct:    {correctness:.1f}/10{delta_str(correctness, 'correctness', prev_s)}")
    lines.append(f"  Procedure:  {procedure:.1f}/10{delta_str(procedure, 'procedure', prev_s)}")
    lines.append(f"  Concise:    {conciseness:.1f}/10{delta_str(conciseness, 'conciseness', prev_s)}")

    pos = summary.get("positive", {})
    neg = summary.get("negative", {})
    if pos:
        lines.append(f"  Positive:   {pos.get('mean_composite', 0):.3f} ({pos.get('count', 0)} examples)")
    if neg:
        lines.append(f"  Negative:   {neg.get('mean_composite', 0):.3f} ({neg.get('count', 0)} examples)")

    # Threshold flag
    if composite < 0.5:
        lines.append(f"  ** BELOW THRESHOLD (0.5) -- skill may need attention **")

    if report.get("total_cost_usd"):
        lines.append(f"  Cost: ${report['total_cost_usd']:.4f}")

    lines.append("")
    return lines


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

    # eval-triggers
    p_eval_trig = sub.add_parser("eval-triggers", help="Test regex trigger patterns against evaluation queries")
    p_eval_trig.add_argument("name", help="Skill name")
    p_eval_trig.add_argument("--queries", required=True, help='JSON with "should_trigger" and "should_not_trigger" arrays')
    p_eval_trig.add_argument("--pattern", default=None, help="Regex pattern to test (default: read from skill-patterns.sh)")
    p_eval_trig.add_argument("--patterns-file", default=None, help="Path to skill-patterns.sh (default: plugin repo)")

    # test-triggers
    p_tt = sub.add_parser("test-triggers", help="Run regex trigger regression tests from fixture files")
    p_tt.add_argument("--skill", default=None, help="Test only this skill")
    p_tt.add_argument("--fixtures-dir", default=None, help="Override fixtures directory")

    # test-semantic
    p_ts = sub.add_parser("test-semantic", help="Run semantic injection tests via claude CLI (costs tokens)")
    p_ts.add_argument("--max-tests", type=int, default=None, help="Limit number of tests")
    p_ts.add_argument("--fixtures", default=None, help="Path to semantic-triggers.jsonl")

    # validate-plugin
    p_vp = sub.add_parser("validate-plugin", help="Deterministic validation of all plugin components (no AI needed)")
    p_vp.add_argument("--component", default=None, help="Validate only this component name")

    # cleanup
    sub.add_parser("cleanup", help="Remove staging directory")

    # harvest-sessions
    p_harvest = sub.add_parser("harvest-sessions", help="Extract per-skill eval datasets from Claude Code session logs")
    p_harvest.add_argument("--project", default=None, help="Filter to a specific project directory name")
    p_harvest.add_argument("--skill", default=None, help="Filter to a specific skill name")
    p_harvest.add_argument("--min-turns", type=int, default=3, help="Minimum conversation turns to include (default: 3)")
    p_harvest.add_argument("--include-stale", action="store_true", help="Include examples from before the skill was last changed")

    # discover-signals
    p_discover = sub.add_parser("discover-signals", help="Surface unmatched user messages that may indicate new negative patterns")
    p_discover.add_argument("--top", type=int, default=30, help="Number of top candidate patterns to show (default: 30)")

    # dspy-eval
    p_eval = sub.add_parser("dspy-eval", help="Score a skill's effectiveness using LLM-as-judge on harvested eval data")
    p_eval.add_argument("name", help="Skill name (e.g., 'planning', 'code-review')")
    p_eval.add_argument("--dataset", default="sessions", help="Dataset: 'sessions', 'golden', or path to JSONL (default: sessions)")
    p_eval.add_argument("--max-examples", type=int, default=20, help="Max examples to score (default: 20)")
    p_eval.add_argument("--model", default=None, help=f"Override eval model (default depends on backend)")
    p_eval.add_argument("--backend", default="claude-cli", choices=["openrouter", "claude-cli"],
                         help="LLM backend: 'claude-cli' (Opus 4.7 via claude -p, default) or 'openrouter' (DeepSeek V3.2)")

    # build-golden
    p_golden = sub.add_parser("build-golden", help="Build golden eval dataset from harvested sessions")
    p_golden.add_argument("name", help="Skill name")
    p_golden.add_argument("--top", type=int, default=20, help="Number of candidates to select (default: 20)")
    p_golden.add_argument("--auto", action="store_true", help="Auto-label from signal (skip human review)")

    # approve-golden
    p_approve = sub.add_parser("approve-golden", help="Promote reviewed candidates.jsonl to golden.jsonl")
    p_approve.add_argument("name", help="Skill name")

    # analyze-misfires
    p_misfire = sub.add_parser("analyze-misfires", help="Identify skills injected into tasks where they're not needed")
    p_misfire.add_argument("--min-examples", type=int, default=30, help="Minimum injections to include (default: 30)")
    p_misfire.add_argument("--include-stale", action="store_true", help="Include examples from before the skill was last changed")

    # analyze-outcomes
    p_outcomes = sub.add_parser("analyze-outcomes", help="Analyze skill injection outcomes by project context, surface anomalies")
    p_outcomes.add_argument("--min-examples", type=int, default=5, help="Minimum examples per (skill, project) pair (default: 5)")
    p_outcomes.add_argument("--include-stale", action="store_true", help="Include examples from before the skill was last changed")

    # diagnose-negatives
    p_diag = sub.add_parser("diagnose-negatives", help="Analyze negative-signal sessions to find failure patterns and suggest skill fixes")
    p_diag.add_argument("name", help="Skill name")
    p_diag.add_argument("--max-examples", type=int, default=10, help="Max negative examples to analyze (default: 10)")
    p_diag.add_argument("--include-stale", action="store_true", help="Include examples from before the skill was last changed")

    # evolve
    p_evolve = sub.add_parser("evolve", help="Run DSPy GEPA optimization on a skill (outputs diff for review)")
    p_evolve.add_argument("name", help="Skill name")
    p_evolve.add_argument("--dataset", default="golden", help="Dataset: 'golden', 'sessions', or path to JSONL (default: golden)")
    p_evolve.add_argument("--iterations", type=int, default=5, help="Max optimization iterations (default: 5)")
    p_evolve.add_argument("--model", default=None, help="LiteLLM model for DSPy (default: openrouter/deepseek/deepseek-v3.2)")
    p_evolve.add_argument("--optimizer", default="gepa", choices=["gepa", "mipro", "bootstrap"],
                           help="Optimizer: 'gepa' (default), 'mipro', or 'bootstrap'")
    p_evolve.add_argument("--max-growth", type=int, default=20, help="Max body growth percent (default: 20)")
    p_evolve.add_argument("--fitness", default="keyword", choices=["keyword", "llm-judge"],
                           help="Fitness function: 'keyword' (fast/cheap) or 'llm-judge' (Sonnet 4.6, ~$0.10/call)")
    p_evolve.add_argument("--save", action="store_true", help="Save evolved skill to .eval-data/<skill>/evolved-SKILL.md")

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

    elif args.command == "eval-triggers":
        queries = json.loads(args.queries)
        report = eval_triggers(args.name, queries, args.pattern, args.patterns_file)
        print(json.dumps(report, indent=2))

    elif args.command == "test-triggers":
        report = test_triggers(args.skill, args.fixtures_dir)
        # Print summary table
        print(f"\n{'Skill':35s} {'TP':>4s} {'FP':>4s} {'FN':>4s} {'TN':>4s} {'F1':>6s} {'Result':>8s}", file=sys.stderr)
        print("-" * 70, file=sys.stderr)
        for r in report["results"]:
            m = r["metrics"]
            status = "PASS" if r["passed"] else "FAIL"
            print(f"{r['skill']:35s} {m['true_positives']:4d} {m['false_positives']:4d} {m['false_negatives']:4d} {m['true_negatives']:4d} {m['f1']:6.3f} {status:>8s}", file=sys.stderr)
        if not report["all_passed"]:
            failed = [r for r in report["results"] if not r["passed"]]
            print(f"\n  FAILED: {len(failed)} skill(s) have trigger regressions", file=sys.stderr)
            for r in failed:
                for f in r["failures"]:
                    expected = "should trigger" if f["expected"] else "should NOT trigger"
                    print(f"    {r['skill']}: \"{f['query']}\" — {expected} but {'matched' if f['matched'] else 'did not match'}", file=sys.stderr)
                for ce in r.get("coverage_errors", []):
                    print(f"    {r['skill']}: coverage shortfall — {ce}", file=sys.stderr)
        else:
            print(f"\n  All {len(report['results'])} skills passed", file=sys.stderr)
        print(json.dumps(report, indent=2))
        if not report["all_passed"]:
            sys.exit(1)

    elif args.command == "test-semantic":
        report = test_semantic(args.max_tests, args.fixtures)
        s = report["summary"]
        print(f"\n  Semantic tests: {s['passed']} passed, {s['failed']} failed, {s['inconclusive']} inconclusive out of {s['total']}", file=sys.stderr)
        print(json.dumps(report, indent=2))
        if not report["all_passed"]:
            sys.exit(1)

    elif args.command == "validate-plugin":
        report = validate_plugin(args.component)
        inv = report["inventory"]
        s = report["summary"]
        print(f"\n  Plugin: {inv['skills']} skills, {inv['agents']} agents, {inv['commands']} commands", file=sys.stderr)
        print(f"  Findings: {s['high']} HIGH, {s['medium']} MEDIUM, {s['low']} LOW", file=sys.stderr)
        if report["findings"]:
            print(f"\n  {'Component':35s} {'Check':25s} {'Sev':>6s}  Message", file=sys.stderr)
            print("  " + "-" * 100, file=sys.stderr)
            for f in report["findings"]:
                print(f"  {f['component']:35s} {f['check']:25s} {f['severity']:>6s}  {f['message']}", file=sys.stderr)
        else:
            print("  No findings", file=sys.stderr)
        print(json.dumps(report, indent=2))
        if not report["passed"]:
            sys.exit(1)

    elif args.command == "cleanup":
        cleanup()
        print("Cleaned up", file=sys.stderr)

    elif args.command == "harvest-sessions":
        report = harvest_sessions(args.project, args.skill, args.min_turns, args.include_stale)
        print(json.dumps(report, indent=2))

    elif args.command == "discover-signals":
        report = discover_signals(args.top)
        print(json.dumps(report, indent=2))

    elif args.command == "dspy-eval":
        report = dspy_eval(args.name, args.dataset, args.max_examples, args.model, args.backend)
        previous = _save_eval_history(report)
        for line in _format_eval_comparison(report, previous):
            print(line, file=sys.stderr)
        print(json.dumps(report, indent=2))

    elif args.command == "build-golden":
        report = build_golden(args.name, args.top, args.auto)
        print(json.dumps(report, indent=2))

    elif args.command == "approve-golden":
        report = approve_golden(args.name)
        print(json.dumps(report, indent=2))

    elif args.command == "analyze-misfires":
        report = analyze_misfires(args.min_examples, args.include_stale)
        # Print summary table to stderr
        print(f"\n{'Skill':35s} {'Injected':>8s} {'Relevant':>8s} {'Misfire%':>8s} {'Pos%':>6s}", file=sys.stderr)
        print("-" * 70, file=sys.stderr)
        for m in report["misfires"]:
            print(f"{m['skill']:35s} {m['injected']:8d} {m['relevant']:8d} {m['misfire_rate']*100:7.1f}% {m['positive_rate']*100:5.1f}%", file=sys.stderr)
        print(json.dumps(report, indent=2))

    elif args.command == "analyze-outcomes":
        report = analyze_outcomes(args.min_examples, args.include_stale)
        # Global summary table
        print(f"\n  Global skill outcomes ({len(report['global_summary'])} skills with >= {args.min_examples} examples):", file=sys.stderr)
        print(f"  {'Skill':35s} {'Total':>6s} {'Pos':>5s} {'Neg':>5s} {'Neg%':>6s}", file=sys.stderr)
        print("  " + "-" * 60, file=sys.stderr)
        for s in report["global_summary"]:
            print(f"  {s['skill']:35s} {s['total']:6d} {s['positive']:5d} {s['negative']:5d} {s['negative_rate']*100:5.1f}%", file=sys.stderr)
        # Anomalies
        anomalies = report["anomalies"]
        if anomalies:
            print(f"\n  Anomalies ({len(anomalies)} pairs with negative rate >10pp above global):", file=sys.stderr)
            print(f"  {'Skill':25s} {'Project':35s} {'N':>4s} {'Neg%':>6s} {'Global':>6s} {'Delta':>6s}", file=sys.stderr)
            print("  " + "-" * 85, file=sys.stderr)
            for o in anomalies:
                print(f"  {o['skill']:25s} {o['project']:35s} {o['injected']:4d} {o['negative_rate']*100:5.1f}% {o['global_negative_rate']*100:5.1f}% {o['delta']*100:+5.1f}%", file=sys.stderr)
        else:
            print("\n  No anomalies found (no pairs with negative rate >10pp above global)", file=sys.stderr)
        print(json.dumps(report, indent=2))

    elif args.command == "diagnose-negatives":
        report = diagnose_negatives(args.name, args.max_examples, args.include_stale)
        # Print summary to stderr
        if report.get("summary"):
            print(f"\n  Diagnosis for '{args.name}':", file=sys.stderr)
            print(f"  {report['summary']}", file=sys.stderr)
            if report.get("patterns"):
                print(f"\n  Failure patterns ({len(report['patterns'])}):", file=sys.stderr)
                for p in report["patterns"]:
                    print(f"    - {p.get('pattern', '?')} ({p.get('frequency', '?')})", file=sys.stderr)
            if report.get("suggestions"):
                print(f"\n  Suggested changes ({len(report['suggestions'])}):", file=sys.stderr)
                for s in report["suggestions"]:
                    print(f"    [{s.get('section', '?')}] {s.get('rationale', '?')}", file=sys.stderr)
            print("", file=sys.stderr)
        print(json.dumps(report, indent=2))

    elif args.command == "evolve":
        from evolve import evolve_skill

        skill_path = _find_skill_path(args.name)
        if not skill_path:
            print(f"Error: skill '{args.name}' not found", file=sys.stderr)
            sys.exit(1)

        if args.dataset == "golden":
            dataset_path = EVAL_DATA_DIR / args.name / "golden.jsonl"
        elif args.dataset == "sessions":
            dataset_path = EVAL_DATA_DIR / args.name / "sessions.jsonl"
        else:
            dataset_path = Path(args.dataset)

        if not dataset_path.exists():
            print(f"Error: dataset not found at {dataset_path}", file=sys.stderr)
            sys.exit(1)

        report = evolve_skill(
            args.name, str(skill_path), str(dataset_path),
            iterations=args.iterations,
            model=args.model,
            optimizer=args.optimizer,
            max_growth_pct=args.max_growth,
            fitness=args.fitness,
        )

        # Print diff to stderr for immediate review
        if report.get("diff"):
            print("\n" + report["diff"], file=sys.stderr)

        # Save evolved skill if requested
        if args.save and report.get("evolved_text") and report.get("constraints_pass"):
            evolved_path = EVAL_DATA_DIR / args.name / "evolved-SKILL.md"
            evolved_path.parent.mkdir(parents=True, exist_ok=True)
            evolved_path.write_text(report["evolved_text"])
            report["evolved_path"] = str(evolved_path)
            print(f"Saved evolved skill → {evolved_path}", file=sys.stderr)

        # Output JSON without the full evolved_text (it's in the file)
        print(json.dumps({k: v for k, v in report.items() if k not in ("diff", "evolved_text")}, indent=2))


if __name__ == "__main__":
    main()
