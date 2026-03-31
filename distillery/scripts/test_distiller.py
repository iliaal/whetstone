"""Tests for distiller.py"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import urllib.error

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))
import distiller


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Set up a temporary project directory with distiller paths."""
    monkeypatch.setattr(distiller, "STAGING_DIR", tmp_path / ".skill-distiller" / "sources")
    monkeypatch.setattr(distiller, "GENERATED_DIR", tmp_path / "generated-skills")
    monkeypatch.setattr(distiller, "SKILLS_AGENT_DIR", tmp_path / ".agents" / "skills")
    monkeypatch.setattr(distiller, "SKILLS_SYMLINK_DIR", tmp_path / ".claude" / "skills")
    monkeypatch.setattr(distiller, "ENV_FILE", tmp_path / ".env")
    (tmp_path / "generated-skills").mkdir()
    return tmp_path


@pytest.fixture
def sample_skill(tmp_project):
    """Create a sample generated skill with manifest."""
    skill_dir = tmp_project / "generated-skills" / "test-skill"
    skill_dir.mkdir()
    skill_md = skill_dir / "SKILL.md"
    # Body needs ~100+ tokens (350+ bytes) to pass "not suspiciously short" check
    body_lines = "\n".join(f"- Rule {i}: do pattern-{i} instead of anti-pattern-{i}" for i in range(30))
    skill_md.write_text(
        "---\n"
        "name: test-skill\n"
        "description: >-\n"
        "  This skill should be used when testing the distiller.\n"
        "---\n\n"
        "# Test Skill\n\n"
        "## Section One\n\n"
        f"{body_lines}\n"
    )
    manifest = {
        "query": "test-skill",
        "search_queries": ["test", "testing"],
        "generated": "2026-01-01",
        "token_count": 100,
        "sources": [
            {"id": "owner/repo/skill-a", "installs": 500, "sha1": "abc123"},
            {"id": "owner/repo/skill-b", "installs": 200, "sha1": "def456"},
        ],
    }
    (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return skill_dir


def _make_search_response(skills):
    """Helper to build a skills.sh API search response."""
    return {"skills": skills}


def _make_skill(sid, installs=500, source=None):
    """Helper to build a skill dict as returned by skills.sh API."""
    parts = sid.split("/")
    return {
        "id": sid,
        "skillId": parts[-1] if len(parts) >= 3 else sid,
        "name": parts[-1] if len(parts) >= 3 else sid,
        "installs": installs,
        "source": source or "/".join(parts[:2]) if len(parts) >= 3 else "",
    }


# ---------------------------------------------------------------------------
# compute_sha1
# ---------------------------------------------------------------------------

class TestComputeSha1:
    def test_known_content(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("hello world")
        expected = hashlib.sha1(b"hello world").hexdigest()
        assert distiller.compute_sha1(str(f)) == expected

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        expected = hashlib.sha1(b"").hexdigest()
        assert distiller.compute_sha1(str(f)) == expected

    def test_binary_content(self, tmp_path):
        f = tmp_path / "bin.dat"
        data = bytes(range(256))
        f.write_bytes(data)
        expected = hashlib.sha1(data).hexdigest()
        assert distiller.compute_sha1(str(f)) == expected


# ---------------------------------------------------------------------------
# token_count
# ---------------------------------------------------------------------------

class TestTokenCount:
    def test_basic(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("x" * 350)  # 350 bytes → 350/3.5 = 100
        assert distiller.token_count(str(f)) == 100

    def test_empty(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        assert distiller.token_count(str(f)) == 0

    def test_utf8(self, tmp_path):
        f = tmp_path / "utf8.md"
        content = "emoji: 🎉" * 10  # multi-byte chars
        f.write_text(content)
        expected = round(len(content.encode("utf-8")) / 3.5)
        assert distiller.token_count(str(f)) == expected


# ---------------------------------------------------------------------------
# get_engagement_threshold
# ---------------------------------------------------------------------------

class TestEngagementThreshold:
    def test_high(self):
        assert distiller.get_engagement_threshold(10000) == 50
        assert distiller.get_engagement_threshold(50000) == 50

    def test_medium(self):
        assert distiller.get_engagement_threshold(1000) == 10
        assert distiller.get_engagement_threshold(9999) == 10

    def test_low(self):
        assert distiller.get_engagement_threshold(999) == 3
        assert distiller.get_engagement_threshold(0) == 3


# ---------------------------------------------------------------------------
# load_env
# ---------------------------------------------------------------------------

class TestLoadEnv:
    def test_basic(self, tmp_project, monkeypatch):
        monkeypatch.delenv("TEST_KEY", raising=False)
        env = tmp_project / ".env"
        env.write_text("TEST_KEY=hello\n")
        distiller.load_env()
        assert os.environ.get("TEST_KEY") == "hello"
        monkeypatch.delenv("TEST_KEY")

    def test_quotes_stripped(self, tmp_project, monkeypatch):
        monkeypatch.delenv("QUOTED_KEY", raising=False)
        env = tmp_project / ".env"
        env.write_text('QUOTED_KEY="some value"\n')
        distiller.load_env()
        assert os.environ.get("QUOTED_KEY") == "some value"
        monkeypatch.delenv("QUOTED_KEY")

    def test_single_quotes(self, tmp_project, monkeypatch):
        monkeypatch.delenv("SQ_KEY", raising=False)
        env = tmp_project / ".env"
        env.write_text("SQ_KEY='single'\n")
        distiller.load_env()
        assert os.environ.get("SQ_KEY") == "single"
        monkeypatch.delenv("SQ_KEY")

    def test_comments_skipped(self, tmp_project, monkeypatch):
        monkeypatch.delenv("REAL_KEY", raising=False)
        env = tmp_project / ".env"
        env.write_text("# comment\nREAL_KEY=value\n")
        distiller.load_env()
        assert os.environ.get("REAL_KEY") == "value"
        monkeypatch.delenv("REAL_KEY")

    def test_no_overwrite_existing(self, tmp_project, monkeypatch):
        monkeypatch.setenv("EXISTING", "original")
        env = tmp_project / ".env"
        env.write_text("EXISTING=new_value\n")
        distiller.load_env()
        assert os.environ.get("EXISTING") == "original"

    def test_missing_env_file(self, tmp_project):
        # Should not raise
        distiller.load_env()


# ---------------------------------------------------------------------------
# search_skills
# ---------------------------------------------------------------------------

class TestSearchSkills:
    def test_basic_search(self):
        skills = [
            _make_skill("owner/repo/skill-a", 500),
            _make_skill("owner/repo/skill-b", 200),
            _make_skill("owner/repo/skill-c", 150),
        ]
        with mock.patch.object(distiller, "_http_request", return_value=_make_search_response(skills)):
            result = distiller.search_skills(["test"])
        assert len(result) == 3
        assert result[0]["installs"] == 500  # sorted descending

    def test_filters_below_100(self):
        skills = [
            _make_skill("a/b/s1", 500),
            _make_skill("a/b/s2", 50),  # below threshold
            _make_skill("a/b/s3", 200),
            _make_skill("a/b/s4", 150),
        ]
        with mock.patch.object(distiller, "_http_request", return_value=_make_search_response(skills)):
            result = distiller.search_skills(["test"])
        assert len(result) == 3
        ids = [r["id"] for r in result]
        assert "a/b/s2" not in ids

    def test_top_10_limit(self):
        skills = [_make_skill(f"a/b/s{i}", 1000 - i) for i in range(15)]
        with mock.patch.object(distiller, "_http_request", return_value=_make_search_response(skills)):
            result = distiller.search_skills(["test"])
        assert len(result) == 10

    def test_fallback_threshold(self):
        """When fewer than 3 qualify at >=100, drops to >=50."""
        skills = [
            _make_skill("a/b/s1", 120),
            _make_skill("a/b/s2", 80),
            _make_skill("a/b/s3", 60),
            _make_skill("a/b/s4", 30),  # still below 50
        ]
        with mock.patch.object(distiller, "_http_request", return_value=_make_search_response(skills)):
            result = distiller.search_skills(["test"])
        assert len(result) == 3  # s1 (120), s2 (80), s3 (60)

    def test_deduplication_across_queries(self):
        skills = [_make_skill("a/b/skill-one", 500)]
        with mock.patch.object(distiller, "_http_request", return_value=_make_search_response(skills)):
            result = distiller.search_skills(["query1", "query2"])
        assert len(result) == 1

    def test_partial_failure_warns(self):
        def side_effect(url):
            if "fail" in url:
                raise RuntimeError("boom")
            return _make_search_response([_make_skill("a/b/s1", 500)])

        with mock.patch.object(distiller, "_http_request", side_effect=side_effect):
            result = distiller.search_skills(["test", "fail"])
        assert len(result) == 1

    def test_all_queries_fail_exits(self):
        with mock.patch.object(distiller, "_http_request", side_effect=RuntimeError("boom")):
            with pytest.raises(SystemExit):
                distiller.search_skills(["fail1", "fail2"])


# ---------------------------------------------------------------------------
# _resolve_moved_skill
# ---------------------------------------------------------------------------

class TestResolveMovedSkill:
    def test_finds_match(self):
        response = _make_search_response([
            _make_skill("owner/new-repo/my-skill", 300),
            _make_skill("other/repo/my-skill", 100),
        ])
        with mock.patch.object(distiller, "_http_request", return_value=response):
            result = distiller._resolve_moved_skill("owner/old-repo/my-skill")
        assert result is not None
        assert result["id"] == "owner/new-repo/my-skill"
        assert result["source"] == "owner/new-repo"
        assert result["installs"] == 300

    def test_no_match_different_owner(self):
        response = _make_search_response([
            _make_skill("other/repo/my-skill", 300),
        ])
        with mock.patch.object(distiller, "_http_request", return_value=response):
            result = distiller._resolve_moved_skill("owner/old-repo/my-skill")
        assert result is None

    def test_no_match_different_skill_name(self):
        response = _make_search_response([
            _make_skill("owner/repo/different-skill", 300),
        ])
        with mock.patch.object(distiller, "_http_request", return_value=response):
            result = distiller._resolve_moved_skill("owner/old-repo/my-skill")
        assert result is None

    def test_bad_id_format(self):
        result = distiller._resolve_moved_skill("no-slashes")
        assert result is None

    def test_api_error_returns_none(self):
        with mock.patch.object(distiller, "_http_request", side_effect=RuntimeError("boom")):
            result = distiller._resolve_moved_skill("owner/repo/skill")
        assert result is None


# ---------------------------------------------------------------------------
# _stage_skill
# ---------------------------------------------------------------------------

class TestStageSkill:
    def test_moves_agent_to_staging(self, tmp_project):
        staging = tmp_project / ".skill-distiller" / "sources"
        staging.mkdir(parents=True)
        agent_dir = tmp_project / ".agents" / "skills" / "my-skill"
        agent_dir.mkdir(parents=True)
        (agent_dir / "SKILL.md").write_text("content")

        distiller._stage_skill("my-skill")

        assert not agent_dir.exists()
        assert (staging / "my-skill" / "SKILL.md").exists()

    def test_removes_symlink(self, tmp_project):
        staging = tmp_project / ".skill-distiller" / "sources"
        staging.mkdir(parents=True)
        symlink_dir = tmp_project / ".claude" / "skills"
        symlink_dir.mkdir(parents=True)
        target = tmp_project / "target"
        target.mkdir()
        (symlink_dir / "my-skill").symlink_to(target)

        distiller._stage_skill("my-skill")

        assert not (symlink_dir / "my-skill").exists()

    def test_overwrites_existing_staging(self, tmp_project):
        staging = tmp_project / ".skill-distiller" / "sources"
        staging.mkdir(parents=True)
        old_staged = staging / "my-skill"
        old_staged.mkdir()
        (old_staged / "OLD.md").write_text("old")

        agent_dir = tmp_project / ".agents" / "skills" / "my-skill"
        agent_dir.mkdir(parents=True)
        (agent_dir / "SKILL.md").write_text("new")

        distiller._stage_skill("my-skill")

        assert (staging / "my-skill" / "SKILL.md").read_text() == "new"
        assert not (staging / "my-skill" / "OLD.md").exists()


# ---------------------------------------------------------------------------
# fetch_skills
# ---------------------------------------------------------------------------

class TestFetchSkills:
    def _make_agent_skill(self, tmp_project, skill_id, content="# Skill"):
        """Create a skill in the agent directory (simulating npx fetch)."""
        agent_dir = tmp_project / ".agents" / "skills" / skill_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "SKILL.md").write_text(content)

    @mock.patch.object(distiller, "_check_npx_skills")
    @mock.patch("subprocess.run")
    def test_successful_fetch(self, mock_run, mock_check, tmp_project):
        content = "# Test Skill"
        def run_side_effect(cmd, **kwargs):
            # Simulate npx creating the skill
            self._make_agent_skill(tmp_project, "skill-a", content)
            return mock.Mock(returncode=0)

        mock_run.side_effect = run_side_effect
        skills = [{"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"}]
        results = distiller.fetch_skills(skills)

        assert len(results) == 1
        assert results[0]["id"] == "owner/repo/skill-a"
        assert "sha1" in results[0]
        assert results[0]["sha1"] == hashlib.sha1(content.encode()).hexdigest()

    @mock.patch.object(distiller, "_check_npx_skills")
    @mock.patch.object(distiller, "_resolve_moved_skill", return_value=None)
    @mock.patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "npx", stderr="fail"))
    def test_fetch_failure_reported(self, mock_run, mock_resolve, mock_check, tmp_project):
        skills = [{"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"}]
        results = distiller.fetch_skills(skills)

        failed = [r for r in results if r.get("status") == "fetch_failed"]
        assert len(failed) == 1

    @mock.patch.object(distiller, "_check_npx_skills")
    @mock.patch("subprocess.run")
    def test_github_url_used(self, mock_run, mock_check, tmp_project):
        mock_run.return_value = mock.Mock(returncode=0)
        skills = [{"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"}]
        distiller.fetch_skills(skills)

        cmd = mock_run.call_args[0][0]
        assert "https://github.com/owner/repo" in cmd

    @mock.patch.object(distiller, "_check_npx_skills")
    @mock.patch("subprocess.run")
    def test_groups_by_source(self, mock_run, mock_check, tmp_project):
        mock_run.return_value = mock.Mock(returncode=0)
        skills = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 300, "source": "owner/repo"},
            {"id": "other/repo/skill-c", "skillId": "skill-c", "installs": 200, "source": "other/repo"},
        ]
        distiller.fetch_skills(skills)

        assert mock_run.call_count == 2  # two source groups

    @mock.patch.object(distiller, "_check_npx_skills")
    @mock.patch("subprocess.run")
    def test_resolve_on_failure(self, mock_run, mock_check, tmp_project):
        """When fetch fails, resolve the moved skill and retry."""
        content = "# Resolved"
        call_count = [0]

        def run_side_effect(cmd, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise subprocess.CalledProcessError(1, "npx", stderr="not found")
            # Second call (retry) succeeds
            self._make_agent_skill(tmp_project, "skill-a", content)
            return mock.Mock(returncode=0)

        mock_run.side_effect = run_side_effect
        resolved = {"id": "owner/new-repo/skill-a", "source": "owner/new-repo", "installs": 600}

        with mock.patch.object(distiller, "_resolve_moved_skill", return_value=resolved):
            skills = [{"id": "owner/old-repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/old-repo"}]
            results = distiller.fetch_skills(skills)

        ok = [r for r in results if "sha1" in r]
        assert len(ok) == 1
        assert ok[0]["id"] == "owner/new-repo/skill-a"  # updated


# ---------------------------------------------------------------------------
# update_manifest
# ---------------------------------------------------------------------------

class TestUpdateManifest:
    def test_preserves_fields(self, sample_skill):
        new_sources = json.dumps([{"id": "x/y/z", "installs": 100, "sha1": "aaa"}])
        distiller.update_manifest("test-skill", 999, new_sources)

        manifest = json.loads((sample_skill / "manifest.json").read_text())
        assert manifest["query"] == "test-skill"
        assert manifest["search_queries"] == ["test", "testing"]
        assert manifest["token_count"] == 999
        assert len(manifest["sources"]) == 1
        assert manifest["sources"][0]["id"] == "x/y/z"

    def test_updates_date(self, sample_skill):
        distiller.update_manifest("test-skill", 100, "[]")
        manifest = json.loads((sample_skill / "manifest.json").read_text())
        from datetime import date
        assert manifest["generated"] == date.today().isoformat()

    def test_missing_manifest_exits(self, tmp_project):
        (tmp_project / "generated-skills" / "nonexistent").mkdir()
        with pytest.raises(SystemExit):
            distiller.update_manifest("nonexistent", 100, "[]")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class TestValidate:
    def test_valid_skill(self, sample_skill):
        result = distiller.validate("test-skill")
        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["passed"] is True
        assert result["score"] == result["max_score"]
        assert "gates" in result
        assert all(g["pass"] for g in result["gates"].values())

    def test_scoring_structure(self, sample_skill):
        result = distiller.validate("test-skill")
        assert result["max_score"] == 7
        expected_gates = {"frontmatter", "name", "description", "token_budget", "no_placeholders", "completeness", "manifest"}
        assert set(result["gates"].keys()) == expected_gates

    def test_missing_skill_file(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "missing"
        skill_dir.mkdir()
        result = distiller.validate("missing")
        assert result["valid"] is False
        assert result["passed"] is False
        assert result["score"] == 0
        assert any("SKILL.md not found" in i for i in result["issues"])

    def test_missing_manifest(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "no-manifest"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-manifest\ndescription: Short description.\n---\n\n# Content\n\n" + "x " * 200
        )
        result = distiller.validate("no-manifest")
        assert result["gates"]["manifest"]["pass"] is False
        assert any("manifest.json not found" in i for i in result["issues"])

    def test_missing_name(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "no-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\ndescription: A description.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("no-name")
        assert result["gates"]["name"]["pass"] is False
        assert any("Missing name" in i for i in result["issues"])

    def test_missing_description(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "no-desc"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-desc\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("no-desc")
        assert result["gates"]["description"]["pass"] is False

    def test_name_uppercase_rejected(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "bad-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: BadName\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("bad-name")
        assert result["gates"]["name"]["pass"] is False

    def test_name_too_long(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "long-name"
        skill_dir.mkdir()
        long_name = "a" * 65
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {long_name}\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("long-name")
        assert result["gates"]["name"]["pass"] is False

    def test_banned_name_claude(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "banned"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: claude-helper\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("banned")
        assert result["gates"]["name"]["pass"] is False

    def test_inert_fields_flagged(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "inert"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: inert\ndescription: Short.\nauthor: someone\ntags: [a]\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("inert")
        assert result["gates"]["frontmatter"]["pass"] is False

    def test_body_over_2k_is_issue(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "huge"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: huge\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 4000
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("huge")
        assert result["valid"] is False
        assert result["gates"]["token_budget"]["pass"] is False

    def test_body_over_1k_is_warning(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "medium"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: medium\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 840
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("medium")
        assert result["gates"]["token_budget"]["pass"] is True  # warning, not failure
        assert any("1K ideal" in w for w in result["warnings"])

    def test_short_body_is_issue(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "tiny"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: tiny\ndescription: Short.\n---\n\nHi\n"
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("tiny")
        assert result["gates"]["token_budget"]["pass"] is False

    def test_second_person_warning(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "second"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: second\ndescription: Short.\n---\n\n# Content\n\n"
            "You should always test. You must validate. " + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("second")
        assert any("Second person" in w for w in result["warnings"])

    def test_missing_search_queries_in_manifest(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "no-sq"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-sq\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("no-sq")
        assert result["gates"]["manifest"]["pass"] is False

    def test_missing_sha1_warning(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "no-sha"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-sha\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        (skill_dir / "manifest.json").write_text(
            '{"search_queries":["a"],"sources":[{"id":"a/b/c","installs":100}]}'
        )
        result = distiller.validate("no-sha")
        assert result["gates"]["manifest"]["pass"] is True  # sha1 missing is a warning, not failure
        assert any("missing sha1" in w.lower() for w in result["warnings"])

    def test_references_counted(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "with-refs"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: with-refs\ndescription: Short.\n---\n\n# Content\n\n" + "word " * 200
        )
        refs = skill_dir / "references"
        refs.mkdir()
        (refs / "extra.md").write_text("extra " * 500)
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("with-refs")
        assert result["total_tokens"] > result["body_tokens"]

    def test_placeholder_text_detected(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "placeholder"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: placeholder\ndescription: Short.\n---\n\n# Content\n\n"
            "Do [TODO fill this in] and also TBD later. " + "word " * 200
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("placeholder")
        assert result["gates"]["no_placeholders"]["pass"] is False

    def test_empty_section_detected(self, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "empty-sec"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: empty-sec\ndescription: Short.\n---\n\n# Content\n\n## Filled\n\n"
            + "word " * 150
            + "\n\n## Empty\n\n## Also Empty\n\n## Has Content\n\n" + "word " * 50
        )
        (skill_dir / "manifest.json").write_text('{"search_queries":["a"],"sources":[{"id":"a/b/c","sha1":"x"}]}')
        result = distiller.validate("empty-sec")
        assert result["gates"]["completeness"]["pass"] is False

    def test_pass_threshold_allows_one_failure(self, tmp_project):
        """A skill missing only the manifest still passes (6/7)."""
        skill_dir = tmp_project / "generated-skills" / "almost"
        skill_dir.mkdir()
        body_lines = "\n".join(f"- Rule {i}: do pattern-{i}" for i in range(30))
        (skill_dir / "SKILL.md").write_text(
            "---\nname: almost\ndescription: A short description.\n---\n\n# Content\n\n" + body_lines + "\n"
        )
        # No manifest.json — fails gate 7 only
        result = distiller.validate("almost")
        assert result["passed"] is True
        assert result["score"] == 6
        assert result["valid"] is False  # still has issues


# ---------------------------------------------------------------------------
# check_updates
# ---------------------------------------------------------------------------

class TestCheckUpdates:
    @mock.patch.object(distiller, "cleanup")
    @mock.patch.object(distiller, "fetch_skills")
    @mock.patch.object(distiller, "search_skills")
    def test_no_updates(self, mock_search, mock_fetch, mock_cleanup, sample_skill):
        mock_search.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "source": "owner/repo"},
        ]
        mock_fetch.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "sha1": "abc123", "path": "p1"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "sha1": "def456", "path": "p2"},
        ]
        result = distiller.check_updates("test-skill")
        assert result["status"] == "no_updates"
        mock_cleanup.assert_called_once()

    @mock.patch.object(distiller, "fetch_skills")
    @mock.patch.object(distiller, "search_skills")
    def test_changed_source(self, mock_search, mock_fetch, sample_skill):
        mock_search.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "source": "owner/repo"},
        ]
        mock_fetch.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "sha1": "NEW_SHA", "path": "p1"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "sha1": "def456", "path": "p2"},
        ]
        result = distiller.check_updates("test-skill")
        assert result["status"] == "updates_available"
        assert len(result["changed"]) == 1
        assert result["changed"][0]["new_sha1"] == "NEW_SHA"

    @mock.patch.object(distiller, "fetch_skills")
    @mock.patch.object(distiller, "search_skills")
    def test_new_source(self, mock_search, mock_fetch, sample_skill):
        mock_search.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "source": "owner/repo"},
            {"id": "new/repo/skill-c", "skillId": "skill-c", "installs": 300, "source": "new/repo"},
        ]
        mock_fetch.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "sha1": "abc123", "path": "p1"},
            {"id": "owner/repo/skill-b", "skillId": "skill-b", "installs": 200, "sha1": "def456", "path": "p2"},
            {"id": "new/repo/skill-c", "skillId": "skill-c", "installs": 300, "sha1": "new111", "path": "p3"},
        ]
        result = distiller.check_updates("test-skill")
        assert result["status"] == "updates_available"
        assert len(result["new"]) == 1
        assert result["new"][0]["id"] == "new/repo/skill-c"

    @mock.patch.object(distiller, "fetch_skills")
    @mock.patch.object(distiller, "search_skills")
    def test_removed_source(self, mock_search, mock_fetch, sample_skill):
        # Only skill-a comes back from search, skill-b was removed
        mock_search.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "source": "owner/repo"},
        ]
        mock_fetch.return_value = [
            {"id": "owner/repo/skill-a", "skillId": "skill-a", "installs": 500, "sha1": "abc123", "path": "p1"},
        ]
        result = distiller.check_updates("test-skill")
        assert result["status"] == "updates_available"
        assert len(result["removed"]) == 1
        assert result["removed"][0]["id"] == "owner/repo/skill-b"


# ---------------------------------------------------------------------------
# backfill_sha1
# ---------------------------------------------------------------------------

class TestBackfillSha1:
    @mock.patch.object(distiller, "cleanup")
    @mock.patch.object(distiller, "fetch_skills")
    def test_backfills_missing(self, mock_fetch, mock_cleanup, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "bf-test"
        skill_dir.mkdir()
        manifest = {
            "query": "bf-test",
            "search_queries": ["bf"],
            "sources": [
                {"id": "a/b/s1", "installs": 500, "sha1": "existing"},
                {"id": "a/b/s2", "installs": 200},
            ],
        }
        (skill_dir / "manifest.json").write_text(json.dumps(manifest))

        mock_fetch.return_value = [
            {"id": "a/b/s2", "skillId": "s2", "installs": 200, "sha1": "new_sha"},
        ]

        result = distiller.backfill_sha1("bf-test")
        updated = json.loads((skill_dir / "manifest.json").read_text())
        assert updated["sources"][0]["sha1"] == "existing"
        assert updated["sources"][1]["sha1"] == "new_sha"

    @mock.patch.object(distiller, "cleanup")
    @mock.patch.object(distiller, "fetch_skills")
    def test_skips_if_all_have_sha1(self, mock_fetch, mock_cleanup, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "complete"
        skill_dir.mkdir()
        manifest = {
            "query": "complete",
            "search_queries": ["c"],
            "sources": [
                {"id": "a/b/s1", "installs": 500, "sha1": "aaa"},
            ],
        }
        (skill_dir / "manifest.json").write_text(json.dumps(manifest))

        distiller.backfill_sha1("complete")
        mock_fetch.assert_not_called()

    @mock.patch.object(distiller, "cleanup")
    @mock.patch.object(distiller, "fetch_skills")
    def test_handles_fetch_failure(self, mock_fetch, mock_cleanup, tmp_project):
        skill_dir = tmp_project / "generated-skills" / "fail-bf"
        skill_dir.mkdir()
        manifest = {
            "query": "fail-bf",
            "search_queries": ["f"],
            "sources": [
                {"id": "a/b/s1", "installs": 500},
            ],
        }
        (skill_dir / "manifest.json").write_text(json.dumps(manifest))

        mock_fetch.return_value = [
            {"id": "a/b/s1", "status": "fetch_failed", "error": "gone"},
        ]

        distiller.backfill_sha1("fail-bf")
        updated = json.loads((skill_dir / "manifest.json").read_text())
        assert "sha1" not in updated["sources"][0]


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    def test_removes_staging(self, tmp_project, monkeypatch):
        staging = tmp_project / ".skill-distiller"
        staging.mkdir()
        (staging / "file.txt").write_text("data")
        monkeypatch.setattr(distiller, "DISTILLERY_DIR", tmp_project)
        distiller.cleanup()
        assert not staging.exists()

    def test_no_error_if_missing(self, tmp_project, monkeypatch):
        monkeypatch.setattr(distiller, "DISTILLERY_DIR", tmp_project)
        distiller.cleanup()  # should not raise


# ---------------------------------------------------------------------------
# _http_request (retry behavior)
# ---------------------------------------------------------------------------

class TestHttpRequest:
    @mock.patch("urllib.request.urlopen")
    def test_success(self, mock_urlopen):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = mock.Mock(return_value=mock_resp)
        mock_resp.__exit__ = mock.Mock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = distiller._http_request("https://example.com/api", retries=0)
        assert result == {"ok": True}

    @mock.patch("time.sleep")  # don't actually sleep
    @mock.patch("urllib.request.urlopen")
    def test_retries_on_429(self, mock_urlopen, mock_sleep):
        error = urllib.error.HTTPError("url", 429, "rate limited", {}, None)
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = mock.Mock(return_value=mock_resp)
        mock_resp.__exit__ = mock.Mock(return_value=False)

        mock_urlopen.side_effect = [error, mock_resp]
        result = distiller._http_request("https://example.com/api", retries=1)
        assert result == {"ok": True}
        assert mock_urlopen.call_count == 2

    @mock.patch("time.sleep")
    @mock.patch("urllib.request.urlopen")
    def test_no_retry_on_404(self, mock_urlopen, mock_sleep):
        error = urllib.error.HTTPError("url", 404, "not found", {}, None)
        mock_urlopen.side_effect = error

        with pytest.raises(RuntimeError, match="HTTP 404"):
            distiller._http_request("https://example.com/api", retries=2)
        assert mock_urlopen.call_count == 1  # no retries

    @mock.patch("time.sleep")
    @mock.patch("urllib.request.urlopen")
    def test_retries_on_timeout(self, mock_urlopen, mock_sleep):
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_resp.__enter__ = mock.Mock(return_value=mock_resp)
        mock_resp.__exit__ = mock.Mock(return_value=False)

        mock_urlopen.side_effect = [TimeoutError("timed out"), mock_resp]
        result = distiller._http_request("https://example.com/api", retries=1)
        assert result == {"ok": True}


# ---------------------------------------------------------------------------
# grok_query (response parsing)
# ---------------------------------------------------------------------------

class TestGrokQueryParsing:
    """Test grok_query response parsing without making real API calls."""

    @mock.patch.object(distiller, "load_env")
    @mock.patch.object(distiller, "_http_request")
    def test_parses_clean_json(self, mock_http, mock_env, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "test-key")
        mock_http.return_value = {
            "choices": [{"message": {"content": '{"findings": [], "summary": "Nothing found."}'}}]
        }
        result = distiller.grok_query("test", 1000)
        assert result["findings"] == []
        assert result["summary"] == "Nothing found."

    @mock.patch.object(distiller, "load_env")
    @mock.patch.object(distiller, "_http_request")
    def test_strips_markdown_fences(self, mock_http, mock_env, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "test-key")
        mock_http.return_value = {
            "choices": [{"message": {"content": '```json\n{"findings": [], "summary": "Fenced."}\n```'}}]
        }
        result = distiller.grok_query("test", 1000)
        assert result["summary"] == "Fenced."

    @mock.patch.object(distiller, "load_env")
    @mock.patch.object(distiller, "_http_request")
    def test_invalid_json_returns_raw(self, mock_http, mock_env, monkeypatch):
        monkeypatch.setenv("GROK_API_KEY", "test-key")
        mock_http.return_value = {
            "choices": [{"message": {"content": "This is not JSON at all"}}]
        }
        result = distiller.grok_query("test", 1000)
        assert "raw" in result
        assert result["findings"] == []

    def test_missing_api_key_exits(self, monkeypatch):
        monkeypatch.delenv("GROK_API_KEY", raising=False)
        monkeypatch.setattr(distiller, "ENV_FILE", Path("/nonexistent/.env"))
        with pytest.raises(SystemExit):
            distiller.grok_query("test", 1000)


# ---------------------------------------------------------------------------
# _parse_model_spec
# ---------------------------------------------------------------------------

class TestParseModelSpec:
    def test_simple_model(self):
        model_id, provider = distiller._parse_model_spec("x-ai/grok-4.1-fast")
        assert model_id == "x-ai/grok-4.1-fast"
        assert provider is None

    def test_model_with_provider(self):
        model_id, provider = distiller._parse_model_spec("anthropic/claude-sonnet-4.5:google-vertex")
        assert model_id == "anthropic/claude-sonnet-4.5"
        assert provider == "google-vertex"

    def test_model_with_colon_in_name(self):
        model_id, provider = distiller._parse_model_spec("moonshotai/kimi-k2.5:moonshotai")
        assert model_id == "moonshotai/kimi-k2.5"
        assert provider == "moonshotai"

    def test_no_slash(self):
        model_id, provider = distiller._parse_model_spec("gpt-4")
        assert model_id == "gpt-4"
        assert provider is None


# ---------------------------------------------------------------------------
# _openrouter_request
# ---------------------------------------------------------------------------

class TestOpenrouterRequest:
    @mock.patch.object(distiller, "_http_request")
    def test_successful_request(self, mock_http):
        mock_http.return_value = {
            "choices": [{"message": {"content": "response text"}}],
            "usage": {"total_tokens": 500},
        }
        result = distiller._openrouter_request("key", "model/id", None, [{"role": "user", "content": "hi"}], 2000)
        assert result["status"] == "ok"
        assert result["response"] == "response text"
        assert result["tokens"] == 500

    @mock.patch.object(distiller, "_http_request")
    def test_with_provider(self, mock_http):
        mock_http.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"total_tokens": 100},
        }
        distiller._openrouter_request("key", "model/id", "vertex", [{"role": "user", "content": "hi"}], 2000)
        # Verify provider was included in the request payload
        call_args = mock_http.call_args
        payload = json.loads(call_args[1]["data"] if "data" in call_args[1] else call_args[0][1])
        assert payload["provider"] == {"order": ["vertex"], "allow_fallbacks": False}

    @mock.patch.object(distiller, "_http_request", side_effect=RuntimeError("boom"))
    def test_error_handling(self, mock_http):
        result = distiller._openrouter_request("key", "model/id", None, [{"role": "user", "content": "hi"}], 2000)
        assert result["status"] == "error"
        assert "boom" in result["error"]


# ---------------------------------------------------------------------------
# _load_skill_pattern
# ---------------------------------------------------------------------------

class TestLoadSkillPattern:
    def test_loads_single_quote_pattern(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text(
            "declare -A SKILL_PATTERNS\n"
            "SKILL_PATTERNS[php-laravel]='\\bphp\\b|laravel|eloquent'\n"
        )
        result = distiller._load_skill_pattern("php-laravel", str(patterns_file))
        assert result == "\\bphp\\b|laravel|eloquent"

    def test_loads_double_quote_pattern(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text('SKILL_PATTERNS[test-skill]="test|pattern"\n')
        result = distiller._load_skill_pattern("test-skill", str(patterns_file))
        assert result == "test|pattern"

    def test_returns_none_for_missing_skill(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text("declare -A SKILL_PATTERNS\n")
        result = distiller._load_skill_pattern("nonexistent", str(patterns_file))
        assert result is None

    def test_returns_none_for_missing_file(self):
        result = distiller._load_skill_pattern("anything", "/nonexistent/path")
        assert result is None

    def test_uses_default_path(self, monkeypatch):
        monkeypatch.setattr(distiller, "SKILL_PATTERNS_DEFAULT", Path("/nonexistent/default"))
        result = distiller._load_skill_pattern("anything")
        assert result is None


# ---------------------------------------------------------------------------
# eval_triggers
# ---------------------------------------------------------------------------

class TestEvalTriggers:
    def test_perfect_score(self):
        queries = {
            "should_trigger": ["I need help with laravel"],
            "should_not_trigger": ["Write a python script"],
        }
        result = distiller.eval_triggers("test", queries, pattern=r"laravel")
        assert result["metrics"]["precision"] == 1.0
        assert result["metrics"]["recall"] == 1.0
        assert result["metrics"]["f1"] == 1.0
        assert result["metrics"]["accuracy"] == 1.0

    def test_false_negative(self):
        queries = {
            "should_trigger": ["Fix this blade template", "laravel migration"],
            "should_not_trigger": [],
        }
        result = distiller.eval_triggers("test", queries, pattern=r"laravel")
        assert result["metrics"]["true_positives"] == 1
        assert result["metrics"]["false_negatives"] == 1
        assert result["metrics"]["recall"] == 0.5

    def test_false_positive(self):
        queries = {
            "should_trigger": [],
            "should_not_trigger": ["I need a php script for my python project"],
        }
        result = distiller.eval_triggers("test", queries, pattern=r"\bphp\b")
        assert result["metrics"]["false_positives"] == 1
        assert result["metrics"]["precision"] == 0.0  # tp=0, fp=1 -> 0/(0+1)=0

    def test_false_positive_precision(self):
        """Verify precision is 0 when all positive predictions are wrong."""
        queries = {
            "should_trigger": [],
            "should_not_trigger": ["I need a php script for my python project"],
        }
        result = distiller.eval_triggers("test", queries, pattern=r"\bphp\b")
        assert result["metrics"]["precision"] == 0.0

    def test_case_insensitive_matching(self):
        queries = {
            "should_trigger": ["Help with LARAVEL routing"],
            "should_not_trigger": [],
        }
        result = distiller.eval_triggers("test", queries, pattern=r"laravel")
        assert result["metrics"]["true_positives"] == 1

    def test_loads_pattern_from_file(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text("SKILL_PATTERNS[my-skill]='my.?skill|test.?pattern'\n")
        queries = {
            "should_trigger": ["help with my skill"],
            "should_not_trigger": ["unrelated query"],
        }
        result = distiller.eval_triggers("my-skill", queries, patterns_file=str(patterns_file))
        assert result["metrics"]["accuracy"] == 1.0

    def test_missing_pattern_exits(self):
        queries = {"should_trigger": ["x"], "should_not_trigger": []}
        with pytest.raises(SystemExit):
            distiller.eval_triggers("nonexistent", queries, patterns_file="/nonexistent")

    def test_empty_queries(self):
        queries = {"should_trigger": [], "should_not_trigger": []}
        result = distiller.eval_triggers("test", queries, pattern=r"test")
        assert result["metrics"]["accuracy"] == 0.0
        assert result["matches"] == []

    def test_output_structure(self):
        queries = {
            "should_trigger": ["test this"],
            "should_not_trigger": ["other thing"],
        }
        result = distiller.eval_triggers("my-skill", queries, pattern=r"test")
        assert result["skill"] == "my-skill"
        assert result["pattern"] == "test"
        assert len(result["matches"]) == 2
        assert all(k in result["matches"][0] for k in ("query", "expected", "matched", "correct"))
        assert all(k in result["metrics"] for k in ("precision", "recall", "f1", "accuracy"))


# ---------------------------------------------------------------------------
# test_triggers
# ---------------------------------------------------------------------------

class TestTestTriggers:
    def test_perfect_fixture_passes(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text("SKILL_PATTERNS[my-skill]='hello|world'\n")
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "my-skill.jsonl").write_text(
            '{"prompt": "hello there", "expect": true}\n'
            '{"prompt": "goodbye now", "expect": false}\n'
        )
        # Temporarily override the patterns file path
        old_default = distiller.SKILL_PATTERNS_DEFAULT
        distiller.SKILL_PATTERNS_DEFAULT = patterns_file
        try:
            result = distiller.test_triggers(fixtures_dir=str(fixtures_dir))
        finally:
            distiller.SKILL_PATTERNS_DEFAULT = old_default
        assert result["all_passed"]
        assert len(result["results"]) == 1
        assert result["results"][0]["skill"] == "my-skill"
        assert result["results"][0]["passed"]

    def test_regression_failure_detected(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text("SKILL_PATTERNS[my-skill]='hello'\n")
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "my-skill.jsonl").write_text(
            '{"prompt": "hello there", "expect": true}\n'
            '{"prompt": "hello world", "expect": false}\n'
        )
        old_default = distiller.SKILL_PATTERNS_DEFAULT
        distiller.SKILL_PATTERNS_DEFAULT = patterns_file
        try:
            result = distiller.test_triggers(fixtures_dir=str(fixtures_dir))
        finally:
            distiller.SKILL_PATTERNS_DEFAULT = old_default
        assert not result["all_passed"]
        assert len(result["results"][0]["failures"]) == 1
        assert result["results"][0]["failures"][0]["query"] == "hello world"

    def test_skill_filter(self, tmp_path):
        patterns_file = tmp_path / "skill-patterns.sh"
        patterns_file.write_text(
            "SKILL_PATTERNS[alpha]='alpha'\n"
            "SKILL_PATTERNS[beta]='beta'\n"
        )
        fixtures_dir = tmp_path / "fixtures"
        fixtures_dir.mkdir()
        (fixtures_dir / "alpha.jsonl").write_text('{"prompt": "alpha test", "expect": true}\n')
        (fixtures_dir / "beta.jsonl").write_text('{"prompt": "beta test", "expect": true}\n')
        old_default = distiller.SKILL_PATTERNS_DEFAULT
        distiller.SKILL_PATTERNS_DEFAULT = patterns_file
        try:
            result = distiller.test_triggers(skill_filter="alpha", fixtures_dir=str(fixtures_dir))
        finally:
            distiller.SKILL_PATTERNS_DEFAULT = old_default
        assert len(result["results"]) == 1
        assert result["results"][0]["skill"] == "alpha"

    def test_empty_fixtures_dir_exits(self, tmp_path):
        fixtures_dir = tmp_path / "empty"
        fixtures_dir.mkdir()
        with pytest.raises(SystemExit):
            distiller.test_triggers(fixtures_dir=str(fixtures_dir))
