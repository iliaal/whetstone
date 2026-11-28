import os
from pathlib import Path
import subprocess
import time

import pytest


ROOT = Path(__file__).resolve().parents[2]
MANAGER = ROOT / "plugins/whetstone/skills/ia-git-worktree/scripts/worktree-manager.sh"
PLANNER = ROOT / "plugins/whetstone/skills/ia-planning/scripts/init-plan.sh"


@pytest.fixture
def git_env():
    return {
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
        "WORKTREE_SESSION_ID": "workflow-script-test",
    }


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
    ignore = repo / (".gitignore" if tool == "plan" else ".git/info/exclude")
    ignore.unlink(missing_ok=True)
    if initial is not None:
        ignore.write_bytes(initial)
    rule = b".plan/" if tool == "plan" else b"/.worktrees/"
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


@pytest.mark.parametrize("tracked_rule", [b"/.worktrees/\n", b"build/\n"])
def test_read_only_worktree_preserves_tracked_ignore_rules(
    tmp_path, git_env, tracked_rule
):
    repo = make_repo(tmp_path / "repo", git_env)
    ignore = repo / ".gitignore"
    ignore.write_bytes(tracked_rule)
    run(repo, git_env, "git", "add", ".gitignore")
    run(
        repo,
        git_env,
        "git",
        "-c",
        "user.name=Workflow test",
        "-c",
        "user.email=workflow@example.invalid",
        "commit",
        "-qm",
        "ignore rules",
    )
    exclude = repo / ".git/info/exclude"
    original_exclude = exclude.read_bytes()
    run(repo, git_env, "bash", str(MANAGER), "create", "--no-env", "review", "main")

    assert (repo / ".worktrees/review/README.md").read_text() == "workflow fixture\n"
    assert run(repo, git_env, "git", "status", "--porcelain").stdout == ""
    assert ignore.read_bytes() == tracked_rule
    if tracked_rule == b"/.worktrees/\n":
        assert exclude.read_bytes() == original_exclude
    else:
        assert exclude.read_bytes() == original_exclude + b"/.worktrees/\n"


def test_worktree_does_not_override_project_reinclude_rule(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    ignore = repo / ".gitignore"
    ignore.write_bytes(b"!/.worktrees/\n")

    refused = run(
        repo, git_env, "bash", str(MANAGER), "create", "--no-env", "review", "main",
        check=False,
    )

    assert refused.returncode == 1
    assert "cannot exclude .worktrees/review/" in refused.stderr
    assert ignore.read_bytes() == b"!/.worktrees/\n"
    assert not (repo / ".worktrees").exists()
    ref = run(repo, git_env, "git", "show-ref", "--verify", "refs/heads/review", check=False)
    assert ref.returncode != 0


def test_worktree_checkout_hooks_respect_explicit_and_inferred_trust(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    hooks = tmp_path / "configured hooks"
    hooks.mkdir()
    post_checkout = hooks / "post-checkout"
    post_checkout.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'fixture hook ran' > hook-marker\n"
    )
    post_checkout.chmod(0o755)
    run(repo, git_env, "git", "config", "core.hooksPath", str(hooks))
    run(repo, git_env, "git", "update-ref", "refs/review/frozen", "HEAD")

    run(repo, git_env, "bash", str(MANAGER), "create", "trusted", "main")
    run(repo, git_env, "bash", str(MANAGER), "create", "--no-env", "explicit", "main")
    run(repo, git_env, "bash", str(MANAGER), "create", "inferred", "refs/review/frozen")

    trees = repo / ".worktrees"
    assert (trees / "trusted/hook-marker").read_text() == "fixture hook ran\n"
    for branch in ["explicit", "inferred"]:
        assert (trees / branch / "README.md").is_file()
        assert not (trees / branch / "hook-marker").exists()
    configured_path = run(repo, git_env, "git", "config", "core.hooksPath").stdout
    assert configured_path.strip() == str(hooks)


def test_planner_refuses_skill_directory_inside_a_repository(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    skill = repo / "plugins/skills/ia-planning"
    (skill / "scripts").mkdir(parents=True)
    script = skill / "scripts/init-plan.sh"
    script.write_bytes(PLANNER.read_bytes())

    for cwd in [skill, skill / "scripts"]:
        refused = run(cwd, git_env, "bash", str(script), "task", check=False)
        assert refused.returncode == 2, refused.stdout + refused.stderr
        assert "not the skill directory" in refused.stderr
    assert not (repo / ".plan").exists()
    assert not (skill / ".plan").exists()
    assert not (repo / ".gitignore").exists()


def test_planner_subdirectory_rerun_keeps_unchecked_root_plan(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    run(repo, git_env, "bash", str(PLANNER), "first")
    plan = repo / ".plan/task_plan.md"
    original = plan.read_bytes()
    nested = repo / "src/module"
    nested.mkdir(parents=True)

    refused = run(nested, git_env, "bash", str(PLANNER), "second", check=False)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "unchecked tasks" in refused.stderr
    assert plan.read_bytes() == original
    assert not (nested / ".plan").exists()

    run(nested, git_env, "bash", str(PLANNER), "second", "--force")
    assert plan.read_text().startswith("# Plan: second\n")
    assert not (nested / ".plan").exists()


def test_planner_outside_repository_uses_working_directory(tmp_path, git_env):
    outside = tmp_path / "plain"
    outside.mkdir()
    env = dict(git_env, GIT_CEILING_DIRECTORIES=str(tmp_path))
    run(outside, env, "bash", str(PLANNER), "task")
    assert (outside / ".plan/task_plan.md").read_text().startswith("# Plan: task\n")
    assert (outside / ".gitignore").read_bytes() == b".plan/\n"


def test_competing_plan_initializers_preserve_the_winning_plan(tmp_path, git_env):
    repo = make_repo(tmp_path / "repo", git_env)
    plan = repo / ".plan/task_plan.md"
    plan.parent.mkdir()
    previous = "# Plan: completed\n- [x] Implement the previous plan\n"
    plan.write_text(previous)

    commands = tmp_path / "commands"
    commands.mkdir()
    cat = commands / "cat"
    cat.write_text(
        "#!/bin/bash\n"
        ": > \"$PLAN_WRITE_STARTED\"\n"
        "while [[ ! -e \"$PLAN_WRITE_RELEASED\" ]]; do sleep 0.01; done\n"
        "exec /bin/cat \"$@\"\n"
    )
    cat.chmod(0o755)
    started = tmp_path / "write-started"
    released = tmp_path / "write-released"
    paused_env = dict(
        git_env,
        PATH=f"{commands}{os.pathsep}{git_env['PATH']}",
        PLAN_WRITE_STARTED=str(started),
        PLAN_WRITE_RELEASED=str(released),
    )
    with subprocess.Popen(
        ["bash", str(PLANNER), "first"],
        cwd=repo,
        env=paused_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as first:
        try:
            deadline = time.monotonic() + 5
            while (
                not started.exists()
                and first.poll() is None
                and time.monotonic() < deadline
            ):
                time.sleep(0.01)
            assert started.exists(), "the first initializer did not start generating its plan"
            during_write = plan.read_text()
            with subprocess.Popen(
                ["bash", str(PLANNER), "second"],
                cwd=repo,
                env=git_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ) as second:
                try:
                    with pytest.raises(subprocess.TimeoutExpired):
                        second.wait(timeout=1)
                finally:
                    released.touch()
                first_out, first_err = first.communicate(timeout=10)
                second_out, second_err = second.communicate(timeout=10)
        finally:
            released.touch()

    assert during_write == previous
    assert first.returncode == 0, first_out + first_err
    assert second.returncode == 1, second_out + second_err
    assert "unchecked tasks" in second_err
    assert plan.read_text().startswith("# Plan: first\n")
    assert (repo / ".gitignore").read_bytes() == b".plan/\n"
