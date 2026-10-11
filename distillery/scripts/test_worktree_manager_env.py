"""Environment-file copying in the ia-git-worktree manager against hostile checkouts."""

import os
from pathlib import Path
import subprocess

import pytest


MANAGER = Path(__file__).resolve().parents[2] / "plugins/whetstone/skills/ia-git-worktree/scripts/worktree-manager.sh"
SECRET = "API_KEY=maintainer-secret\n"


def run(args, cwd, **kwargs):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, **kwargs)


def git(repo, *args):
    result = run(["git", *args], repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    for args in [("init", "-b", "main"), ("config", "user.email", "test@example.invalid"),
                 ("config", "user.name", "Fixture"), ("config", "commit.gpgsign", "false"),
                 ("config", "core.hooksPath", "/dev/null")]:
        git(root, *args)
    (root / ".gitignore").write_text(".worktrees\n.env\n")
    git(root, "add", ".gitignore")
    git(root, "commit", "-m", "baseline")
    (root / ".env").write_text(SECRET)
    return root


@pytest.fixture
def victim(tmp_path):
    path = tmp_path / "victim-config"
    path.write_text("VICTIM_ORIGINAL=1\n")
    return path


def manager(repo, *args):
    env = {**os.environ, "WORKTREE_SESSION_ID": "owner", "HOME": str(repo.parent / "home")}
    return run(["bash", str(MANAGER), *args], repo, env=env, input="")


def commit_branch(repo, branch, setup, path=".env"):
    git(repo, "switch", "-c", branch)
    setup()
    git(repo, "add", "-f", "--", path)
    git(repo, "commit", "-m", branch)
    git(repo, "switch", "main")
    (repo / ".env").write_text(SECRET)


def assert_victim_untouched(tree, victim):
    assert victim.read_text() == "VICTIM_ORIGINAL=1\n"
    assert not (tree / ".env.backup").exists()


def test_trusted_local_branch_copies_env_private(repo):
    result = manager(repo, "create", "feature")
    assert result.returncode == 0, result.stdout + result.stderr
    copied = repo / ".worktrees/feature/.env"
    assert copied.read_text() == SECRET and not copied.is_symlink()
    assert copied.stat().st_mode & 0o777 == 0o600


def test_committed_env_symlink_on_trusted_branch_is_not_followed(repo, victim):
    commit_branch(repo, "evil", lambda: (repo / ".env").unlink() or (repo / ".env").symlink_to(victim))
    result = manager(repo, "create", "review", "evil")
    assert result.returncode == 0, result.stdout + result.stderr
    tree = repo / ".worktrees/review"
    assert (tree / ".env").is_symlink() and "already present" in result.stdout
    assert_victim_untouched(tree, victim)
    again = manager(repo, "copy-env", "review")
    assert again.returncode == 0, again.stdout + again.stderr
    assert_victim_untouched(tree, victim)


def test_committed_dangling_env_symlink_is_not_created_through(repo, tmp_path):
    target = tmp_path / "created-outside"
    commit_branch(repo, "dangling", lambda: (repo / ".env").unlink() or (repo / ".env").symlink_to(target))
    assert manager(repo, "create", "dangling-review", "dangling").returncode == 0
    assert not target.exists()


@pytest.mark.parametrize("base", ["refs/review/pr-7", "pull/7/head", "fork/feature", "SHA", "v1"])
def test_untrusted_bases_skip_env(repo, base):
    commit_branch(repo, "pr-source", lambda: (repo / "code").write_text("x"), "code")
    sha = git(repo, "rev-parse", "pr-source")
    git(repo, "update-ref", "refs/review/pr-7", sha)
    git(repo, "update-ref", "refs/pull/7/head", sha)
    git(repo, "update-ref", "refs/remotes/fork/feature", sha)
    git(repo, "update-ref", "refs/tags/v1", sha)
    result = manager(repo, "create", "pr-review", sha if base == "SHA" else base)
    assert result.returncode == 0, result.stdout + result.stderr
    assert git(repo, "rev-parse", "pr-review") == sha
    assert not (repo / ".worktrees/pr-review/.env").exists()
    assert "Skipped .env copy" in result.stdout


def test_no_env_flag_skips_trusted_branch(repo):
    result = manager(repo, "create", "--no-env", "quiet")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (repo / ".worktrees/quiet/.env").exists()


def test_symlinked_source_env_is_not_copied(repo, victim):
    (repo / ".env.local").symlink_to(victim)
    result = manager(repo, "create", "feature")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/feature/.env").read_text() == SECRET
    assert not (repo / ".worktrees/feature/.env.local").exists()


def test_existing_regular_env_is_kept_without_backup(repo):
    assert manager(repo, "create", "feature").returncode == 0
    copied = repo / ".worktrees/feature/.env"
    copied.write_text("LOCAL_EDIT=1\n")
    result = manager(repo, "copy-env", "feature")
    assert result.returncode == 0
    assert copied.read_text() == "LOCAL_EDIT=1\n"
    assert not (repo / ".worktrees/feature/.env.backup").exists()


@pytest.fixture
def origin_repo(repo, tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "origin", "main")
    git(repo, "remote", "set-head", "origin", "main")
    attacker = tmp_path / "attacker"
    git(tmp_path, "clone", "-q", str(origin), str(attacker))
    for args in [("config", "user.email", "a@example.invalid"), ("config", "user.name", "A"),
                 ("config", "commit.gpgsign", "false"), ("config", "tag.gpgsign", "false"),
                 ("config", "core.hooksPath", "/dev/null")]:
        git(attacker, *args)
    return repo, attacker


def attacker_push(attacker, branch, base="main"):
    git(attacker, "fetch", "-q", "origin")
    git(attacker, "switch", "-q", "-C", branch, f"origin/{base}")
    (attacker / "payload").write_text(branch)
    git(attacker, "add", "payload")
    git(attacker, "commit", "-q", "-m", branch)
    git(attacker, "push", "-q", "-f", "origin", f"{branch}:{branch}")


def test_origin_only_branch_skips_env(origin_repo):
    repo, attacker = origin_repo
    attacker_push(attacker, "contrib")
    result = manager(repo, "create", "review-contrib", "contrib")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review-contrib/payload").exists()
    assert not (repo / ".worktrees/review-contrib/.env").exists()
    assert "Skipped .env copy" in result.stdout


def test_local_branch_with_unseen_origin_commits_skips_env(origin_repo):
    repo, attacker = origin_repo
    git(repo, "branch", "mine", "main")
    git(repo, "push", "-q", "origin", "mine")
    attacker_push(attacker, "mine", base="mine")
    result = manager(repo, "create", "mine-review", "mine")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (repo / ".worktrees/mine-review/.env").exists()


def test_local_branch_containing_fetched_commit_copies_env(origin_repo):
    repo, _ = origin_repo
    git(repo, "branch", "mine", "main")
    git(repo, "push", "-q", "origin", "mine")
    result = manager(repo, "create", "mine-work", "mine")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/mine-work/.env").read_text() == SECRET


def test_default_branch_ahead_on_origin_copies_env(origin_repo):
    repo, attacker = origin_repo
    attacker_push(attacker, "main")
    result = manager(repo, "create", "feature-next")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/feature-next/payload").exists()
    assert (repo / ".worktrees/feature-next/.env").read_text() == SECRET


def test_new_branch_named_after_origin_only_base_skips_env(origin_repo):
    repo, attacker = origin_repo
    attacker_push(attacker, "contrib")
    result = manager(repo, "create", "contrib", "contrib")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/contrib/payload").exists()
    assert not (repo / ".worktrees/contrib/.env").exists()
    assert "Skipped .env copy" in result.stdout


def test_unset_origin_head_resolves_default_from_remote(origin_repo):
    repo, attacker = origin_repo
    git(repo, "remote", "set-head", "origin", "-d")
    attacker_push(attacker, "master")
    result = manager(repo, "create", "review-master", "master")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review-master/payload").exists()
    assert not (repo / ".worktrees/review-master/.env").exists()
    assert "Skipped .env copy" in result.stdout
    main_result = manager(repo, "create", "feature-main")
    assert main_result.returncode == 0, main_result.stdout + main_result.stderr
    assert (repo / ".worktrees/feature-main/.env").read_text() == SECRET


def test_unreachable_origin_does_not_trust_default_names(origin_repo, tmp_path):
    repo, attacker = origin_repo
    attacker_push(attacker, "master")
    git(repo, "fetch", "-q", "origin")
    git(repo, "remote", "set-head", "origin", "-d")
    git(repo, "remote", "set-url", "origin", str(tmp_path / "gone.git"))
    result = manager(repo, "create", "review-master", "origin/master")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review-master/payload").exists()
    assert not (repo / ".worktrees/review-master/.env").exists()
    assert "Skipped .env copy" in result.stdout
    local = manager(repo, "create", "feature-offline")
    assert local.returncode == 0, local.stdout + local.stderr
    assert (repo / ".worktrees/feature-offline/.env").read_text() == SECRET


def test_same_named_tag_does_not_shadow_default_branch(origin_repo):
    repo, attacker = origin_repo
    branch_sha = git(repo, "rev-parse", "main")
    attacker_push(attacker, "tagged")
    git(attacker, "tag", "main", "tagged")
    git(attacker, "push", "-q", "origin", "refs/tags/main")
    result = manager(repo, "create", "review", "main")
    assert result.returncode == 0, result.stdout + result.stderr
    tree = repo / ".worktrees/review"
    assert git(tree, "rev-parse", "HEAD") == branch_sha
    assert not (tree / "payload").exists()
    assert (tree / ".env").read_text() == SECRET


def test_tag_only_base_skips_env(origin_repo):
    repo, attacker = origin_repo
    attacker_push(attacker, "tagged")
    git(attacker, "tag", "release", "tagged")
    git(attacker, "push", "-q", "origin", "refs/tags/release")
    git(attacker, "push", "-q", "origin", "--delete", "tagged")
    result = manager(repo, "create", "review-release", "release")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review-release/payload").exists()
    assert not (repo / ".worktrees/review-release/.env").exists()


def test_tag_cannot_reshape_default_branch_spelling(origin_repo):
    repo, attacker = origin_repo
    attacker_push(attacker, "evil")
    git(attacker, "push", "-q", "origin", "evil:refs/heads/remotes/origin/main")
    git(attacker, "tag", "origin/main", "origin/main")
    git(attacker, "push", "-q", "origin", "refs/tags/origin/main:refs/tags/origin/main")
    git(repo, "fetch", "-q", "--tags", "origin")
    result = manager(repo, "create", "review", "remotes/origin/main")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review/payload").exists()
    assert not (repo / ".worktrees/review/.env").exists()


def test_renamed_remote_default_is_learned_from_origin(origin_repo, tmp_path):
    repo, attacker = origin_repo
    git(tmp_path, "--git-dir", str(tmp_path / "origin.git"), "branch", "trunk", "main")
    git(tmp_path, "--git-dir", str(tmp_path / "origin.git"), "symbolic-ref", "HEAD", "refs/heads/trunk")
    attacker_push(attacker, "main")
    result = manager(repo, "create", "review-main", "main")
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".worktrees/review-main/payload").exists()
    assert not (repo / ".worktrees/review-main/.env").exists()
