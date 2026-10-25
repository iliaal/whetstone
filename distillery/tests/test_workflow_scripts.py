import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANAGER = ROOT / "plugins/whetstone/skills/ia-git-worktree/scripts/worktree-manager.sh"
PLANNER = ROOT / "plugins/whetstone/skills/ia-planning/scripts/init-plan.sh"


@pytest.fixture
def git_env():
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("GIT_")
    }
    env.update(
        GIT_CONFIG_GLOBAL="/dev/null",
        GIT_CONFIG_SYSTEM="/dev/null",
        GIT_TERMINAL_PROMPT="0",
        WORKTREE_SESSION_ID="workflow-script-test",
    )
    return env


def run(cwd, env, *args, input=None, check=True):
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input,
        text=True,
        capture_output=True,
        timeout=15,
    )
    if check:
        assert result.returncode == 0, result.stdout + result.stderr
    return result


def make_repo(path, env):
    path.mkdir()
    run(path, env, "git", "init", "-q", "-b", "main")
    (path / "README.md").write_text("workflow fixture\n")
    run(path, env, "git", "add", "README.md")
    run(
        path,
        env,
        "git",
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.invalid",
        "commit",
        "-qm",
        "baseline",
    )
    return path


def make_bare(tmp_path, env):
    source = make_repo(tmp_path / "source", env)
    bare = tmp_path / "bare repo.git"
    run(tmp_path, env, "git", "clone", "--bare", str(source), str(bare))
    return bare


@pytest.mark.parametrize("initial", [None, b"", b"build/\n", b"build/"])
@pytest.mark.parametrize("tool", ["plan", "worktree"])
def test_ignore_append_preserves_rules_and_is_idempotent(
    tmp_path, git_env, initial, tool
):
    repo = make_repo(tmp_path / "repo", git_env)
    ignore = repo / ".gitignore"
    if initial is not None:
        ignore.write_bytes(initial)
    rule = b".plan/" if tool == "plan" else b".worktrees"
    prefix = initial or b""
    if prefix and not prefix.endswith(b"\n"):
        prefix += b"\n"
    expected = prefix + rule + b"\n"

    for branch in ["first", "second"]:
        if tool == "plan":
            run(repo, git_env, "bash", str(PLANNER), branch, "--force")
            generated = ".plan/task_plan.md"
        else:
            run(
                repo,
                git_env,
                "bash",
                str(MANAGER),
                "create",
                "--no-env",
                branch,
                "main",
            )
            generated = f".worktrees/{branch}/README.md"
        assert ignore.read_bytes() == expected
        run(repo, git_env, "git", "check-ignore", "-q", generated)
        if initial and b"build/" in initial:
            run(repo, git_env, "git", "check-ignore", "-q", "build/artifact")


def test_bare_creation_and_linked_creation_preserve_base_and_owner(tmp_path, git_env):
    bare = make_bare(tmp_path, git_env)
    (bare / ".env").write_text("BARE_ADMIN_SECRET=must-not-copy\n")
    base = run(bare, git_env, "git", "rev-parse", "main").stdout.strip()
    run(bare, git_env, "bash", str(MANAGER), "create", "first", "main")
    first = bare / ".worktrees/first"
    nested = first / "nested"
    nested.mkdir()
    run(nested, git_env, "bash", str(MANAGER), "create", "--no-env", "second", "main")
    second = bare / ".worktrees/second"

    for checkout in [first, second]:
        assert run(checkout, git_env, "git", "rev-parse", "HEAD").stdout.strip() == base
        assert (checkout / "README.md").read_text() == "workflow fixture\n"
        assert not (checkout / ".env").exists()
        owner = run(
            checkout, git_env, "git", "rev-parse", "--git-path", "whetstone-owner"
        ).stdout.strip()
        assert Path(owner).read_text().strip() == git_env["WORKTREE_SESSION_ID"]
        assert run(
            bare, git_env, "bash", str(MANAGER), "switch", checkout.name
        ).stdout.strip() == str(checkout)
        assert run(
            checkout, git_env, "bash", str(MANAGER), "switch", "first"
        ).stdout.strip() == str(first)
        refused = run(
            bare, git_env, "bash", str(MANAGER), "copy-env", checkout.name, check=False
        )
        assert refused.returncode != 0
        assert "no main checkout" in refused.stderr
        assert not (checkout / ".env").exists()
    assert not (bare / ".gitignore").exists()
    assert not (bare / "whetstone-main-root").exists()
    assert (bare / ".env").read_text() == "BARE_ADMIN_SECRET=must-not-copy\n"


def test_bare_cleanup_preserves_current_unowned_dirty_and_locked_trees(
    tmp_path, git_env
):
    bare = make_bare(tmp_path, git_env)
    run(bare, git_env, "bash", str(MANAGER), "create", "--no-env", "feature", "main")
    checkout = bare / ".worktrees/feature"
    for cwd, env in [
        (checkout, git_env),
        (bare, dict(git_env, WORKTREE_SESSION_ID="other-session")),
    ]:
        refused = run(
            cwd,
            env,
            "bash",
            str(MANAGER),
            "cleanup",
            "feature",
            input="y\n",
            check=False,
        )
        assert refused.returncode != 0
        assert checkout.is_dir()

    dirty = checkout / "keep.txt"
    dirty.write_text("caller work\n")
    refused = run(
        bare,
        git_env,
        "bash",
        str(MANAGER),
        "cleanup",
        "feature",
        input="y\n",
        check=False,
    )
    assert refused.returncode != 0
    assert dirty.read_text() == "caller work\n"
    dirty.unlink()

    run(bare, git_env, "git", "worktree", "lock", str(checkout))
    refused = run(
        bare,
        git_env,
        "bash",
        str(MANAGER),
        "cleanup",
        "feature",
        input="y\n",
        check=False,
    )
    assert refused.returncode != 0
    assert checkout.is_dir()
    run(bare, git_env, "git", "worktree", "unlock", str(checkout))
    run(bare, git_env, "bash", str(MANAGER), "cleanup", "feature", input="y\n")
    assert not checkout.exists()
    run(bare, git_env, "git", "show-ref", "--verify", "refs/heads/feature")


def test_bare_creation_refuses_redirected_destination(tmp_path, git_env):
    bare = make_bare(tmp_path, git_env)
    outside = tmp_path / "outside"
    outside.mkdir()
    (bare / ".worktrees").symlink_to(outside, target_is_directory=True)
    refused = run(
        bare,
        git_env,
        "bash",
        str(MANAGER),
        "create",
        "--no-env",
        "feature",
        "main",
        check=False,
    )
    assert refused.returncode != 0
    assert "symlinked worktree directory" in refused.stderr
    assert not list(outside.iterdir())
    assert (
        run(
            bare,
            git_env,
            "git",
            "show-ref",
            "--verify",
            "refs/heads/feature",
            check=False,
        ).returncode
        != 0
    )


def test_ordinary_repository_still_copies_trusted_env(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    (repo / ".env").write_text("LOCAL_TEST_TOKEN=fixture\n")
    run(repo, git_env, "bash", str(MANAGER), "create", "feature", "main")
    checkout = repo / ".worktrees/feature"
    assert (checkout / ".env").read_bytes() == (repo / ".env").read_bytes()
    assert (checkout / ".env").stat().st_mode & 0o777 == 0o600
    assert (repo / ".git/whetstone-main-root").read_text().strip() == str(repo)
