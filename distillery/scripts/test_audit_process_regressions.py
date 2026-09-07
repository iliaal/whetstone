"""Exercise shipped process helpers and executable documentation examples."""

import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import pytest


SKILLS = Path(__file__).resolve().parents[2] / "plugins/whetstone/skills"
MANAGER = SKILLS / "ia-git-worktree/scripts/worktree-manager.sh"
VALIDATOR = SKILLS / "ia-compound-docs/scripts/validate-frontmatter.sh"


def run(args, cwd, **kwargs):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, **kwargs)


def git(repo, *args):
    result = run(["git", *args], repo)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo with spaces"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Fixture")
    git(root, "config", "core.hooksPath", "/dev/null")
    (root / ".gitignore").write_text(".worktrees\n.env\ncache/\n")
    (root / "tracked").write_text("original")
    git(root, "add", ".gitignore", "tracked")
    git(root, "commit", "-m", "baseline")
    return root


def manager(repo, *args, session="owner-one", answer=""):
    env = {**os.environ, "WORKTREE_SESSION_ID": session}
    return run(["bash", str(MANAGER), *args], repo, env=env, input=answer)


def create(repo, name="feature/topic"):
    result = manager(repo, "create", name)
    assert result.returncode == 0, result.stdout + result.stderr
    return repo / ".worktrees" / name


def test_worktree_list_and_path_from_linked_subdirectory(repo):
    before = git(repo, "rev-parse", "HEAD")
    tree = create(repo)
    nested = tree / "nested"
    nested.mkdir()
    listed = manager(nested, "list")
    assert listed.returncode == 0
    assert str(repo) in listed.stdout and str(tree) in listed.stdout
    resolved = manager(nested, "switch", "feature/topic")
    assert resolved.returncode == 0 and resolved.stdout.strip() == str(tree)
    applied = run(["env", "-C", resolved.stdout.strip(), "git", "rev-parse", "--show-toplevel"], repo)
    assert applied.returncode == 0 and applied.stdout.strip() == str(tree)
    assert git(repo, "rev-parse", "HEAD") == before
    assert git(repo, "branch", "--show-current") == "main"


def test_copy_env_from_linked_subdirectory_uses_main_checkout(repo):
    tree = create(repo)
    (tree / "nested").mkdir()
    (repo / ".env").write_text("LOCAL_FIXTURE=yes\n")
    result = manager(tree / "nested", "copy-env")
    assert result.returncode == 0, result.stderr
    assert (tree / ".env").read_text() == "LOCAL_FIXTURE=yes\n"
    assert not (tree / "nested/.env").exists()


@pytest.mark.parametrize("kind", ["tracked", "staged", "untracked", "ignored"])
def test_cleanup_preserves_changes(repo, kind):
    tree = create(repo)
    target = tree / ("tracked" if kind in {"tracked", "staged"} else ".env" if kind == "ignored" else "user-data")
    target.write_text("keep this user data")
    if kind == "staged":
        git(tree, "add", "tracked")
    result = manager(repo, "cleanup", "feature/topic", answer="y\n")
    assert result.returncode != 0
    assert target.read_text() == "keep this user data"


def test_cleanup_requires_named_owned_quiescent_tree(repo):
    tree = create(repo)
    for args, session in [((), "owner-one"), (("feature/topic",), "other-owner"), (("feature/topic",), "")]:
        result = manager(repo, "cleanup", *args, session=session, answer="y\n")
        assert result.returncode != 0 and tree.exists()
    assert manager(tree, "cleanup", "feature/topic", answer="y\n").returncode != 0
    git(repo, "worktree", "lock", str(tree))
    locked = manager(repo, "cleanup", "feature/topic", answer="y\n")
    assert locked.returncode != 0 and "Removed:" not in locked.stdout and tree.exists()
    git(repo, "worktree", "unlock", str(tree))
    cancelled = manager(repo, "cleanup", "feature/topic", answer="n\n")
    assert cancelled.returncode == 0 and tree.exists()
    removed = manager(repo, "cleanup", "feature/topic", answer="y\n")
    assert removed.returncode == 0 and not tree.exists()
    assert "Removed:" in removed.stdout


def test_cleanup_does_not_adopt_existing_or_external_worktrees(repo, tmp_path):
    tree = create(repo)
    external = tmp_path / "external"
    git(repo, "worktree", "add", "-b", "external", str(external))
    for name in ["../../external", str(external), "missing"]:
        assert manager(repo, "cleanup", name, answer="y\n").returncode != 0
    assert external.exists() and tree.exists()


def test_worktree_creation_without_owner_stays_outside_cleanup(repo):
    result = manager(repo, "create", "unowned", session="")
    assert result.returncode == 0, result.stderr
    tree = repo / ".worktrees/unowned"
    assert manager(repo, "cleanup", "unowned", answer="y\n").returncode != 0
    assert tree.exists()


def test_separate_git_directory_and_redirected_create(repo, tmp_path):
    git(repo, "init", "--separate-git-dir", str(tmp_path / "separate metadata"))
    tree = create(repo)
    listed = manager(tree, "list")
    assert listed.returncode == 0 and str(tree) in listed.stdout
    assert not listed.stderr
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / ".worktrees/redirect").symlink_to(outside, target_is_directory=True)
    result = manager(repo, "create", "redirect/topic")
    assert result.returncode != 0 and not (outside / "topic").exists()


FRONTMATTER = """module: Example
date: 2026-09-07
problem_type: runtime_error
component: model
root_cause: logic_error
resolution_type: code_fix
severity: high
"""


@pytest.mark.parametrize("symptoms", [
    'symptoms: ["one, two, three, four, five, six"]\n',
    'symptoms:\n  - "quoted: punctuation, and brackets []"\n',
    'symptoms:\n- one\n- two\n- three\n- four\n- five\n',
    'symptoms: ["escaped \\"quote\\" text"]\n'.replace('\\\\', '\\'),
])
def test_valid_yaml_arrays_pass(tmp_path, symptoms):
    doc = tmp_path / "solution.md"
    doc.write_text("---\n" + FRONTMATTER + symptoms + "tags:\n  - example\n---\n# Solution\n")
    result = run(["bash", str(VALIDATOR), str(doc)], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("fields", [
    "tags:\n  - unrelated\n",
    "symptoms: []\n",
    "symptoms: text\n",
    "symptoms: [a,b,c,d,e,f]\n",
    "symptoms: [null]\n",
    "symptoms: [true]\n",
    "symptoms: ['']\n",
    "symptoms: [valid]\nsymptoms: [duplicate]\n",
    "symptoms: [unterminated\n",
])
def test_invalid_yaml_arrays_fail(tmp_path, fields):
    doc = tmp_path / "solution.md"
    doc.write_text("---\n" + FRONTMATTER + fields + "---\n")
    assert run(["bash", str(VALIDATOR), str(doc)], tmp_path).returncode != 0


@pytest.mark.parametrize("content", [
    "prefix\n---\n" + FRONTMATTER + "symptoms: [valid]\n---\n",
    "---\n" + FRONTMATTER + "symptoms: [valid]\n",
    "---\n- not-a-mapping\n---\n",
])
def test_frontmatter_delimiters_and_mapping_are_required(tmp_path, content):
    doc = tmp_path / "solution.md"
    doc.write_text(content)
    assert run(["bash", str(VALIDATOR), str(doc)], tmp_path).returncode != 0


def test_yaml_merge_and_optional_version_warning(tmp_path):
    doc = tmp_path / "solution.md"
    doc.write_text("---\n" + FRONTMATTER + "defaults: &defaults\n  symptoms: [valid]\n<<: *defaults\nframework_version: preview\n---\n")
    result = run(["bash", str(VALIDATOR), str(doc)], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARNINGS" in result.stdout and "framework_version" in result.stdout


def test_documented_debugging_guard_checks_path_components(tmp_path, monkeypatch):
    text = (SKILLS / "ia-debugging/references/defense-in-depth.md").read_text()
    code = re.search(r"```python\n(.*?)\n```", text, re.S).group(1)
    scope = {}
    exec(code, scope)
    safe = tmp_path / "temporary"
    safe.mkdir()
    outside = tmp_path / "temporary-sibling"
    outside.mkdir()
    (safe / "link").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("NODE_ENV", "test")
    monkeypatch.setattr(scope["tempfile"], "gettempdir", lambda: str(safe))
    asyncio.run(scope["git_init"](str(safe / "owned-child")))
    for path in (safe, outside, safe / "link", safe / "../temporary-sibling"):
        with pytest.raises(RuntimeError, match="outside temp dir"):
            asyncio.run(scope["git_init"](str(path)))


def test_documented_read_refactor_preserves_authorization(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node required to execute TypeScript-free reference example")
    text = (SKILLS / "ia-agent-native-architecture/references/refactoring-to-prompt-native.md").read_text()
    section = text.split("**Step 5:", 1)[1].split("**Step 6:", 1)[0]
    code = re.search(r"```typescript\n(.*?)\n```", section, re.S).group(1)
    runner = """const handlers=[];
const tool=(name, handler)=>handlers.push(handler);
const REPORT_FILES=['report'];
const isAllowed=path=>['report','authorized-other'].includes(path);
const readFile=path=>path;
""" + code + """
(async()=>{
  const after=handlers[1];
  if(await after({path:'authorized-other'})!=='authorized-other')process.exit(1);
  for(const path of ['secret','../secret']){
    try{await after({path});process.exit(2)}catch(error){if(error.message!=='Forbidden')throw error}
  }
})();
"""
    result = run(["node", "-e", runner], tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("break_build", [False, True, "rollback-fails"])
def test_documented_deploy_positive_and_post_merge_rollback(repo, tmp_path, break_build):
    if not shutil.which("node") or not shutil.which("npm"):
        pytest.skip("Node and npm required for deployment recipe")
    (repo / "package.json").write_text(json.dumps({"scripts": {"build": "node build.cjs"}}))
    (repo / "build.cjs").write_text("if(process.env.FAIL_ROLLBACK)throw new Error('rollback build failed');require('fs').writeFileSync('dist.txt','baseline')")
    with (repo / ".gitignore").open("a") as stream:
        stream.write("dist.txt\n")
    git(repo, "add", "package.json", "build.cjs", ".gitignore")
    git(repo, "commit", "-m", "working build")
    previous = git(repo, "rev-parse", "HEAD")
    remote = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", str(remote))
    git(repo, "remote", "add", "origin", str(remote))
    (repo / "build.cjs").write_text("throw new Error('broken build')" if break_build else "require('fs').writeFileSync('dist.txt','candidate')")
    git(repo, "add", "build.cjs")
    git(repo, "commit", "-m", "candidate")
    candidate = git(repo, "rev-parse", "HEAD")
    git(repo, "push", "origin", "main")
    git(repo, "reset", "--hard", previous)
    text = (SKILLS / "ia-agent-native-architecture/references/self-modification.md").read_text()
    code = next(block for block in re.findall(r"```typescript\n(.*?)\n```", text, re.S) if 'tool("self_deploy"' in block)
    runner = """const {execFileSync,execSync}=require('child_process');
let deploy,restarted=false;
const tool=(name,handler)=>{deploy=handler};
const runGit=cmd=>execFileSync('git',cmd.split(' '),{encoding:'utf8'});
const runCommand=(cmd,options)=>execSync(cmd,{...options,encoding:'utf8'});
const scheduleRestart=()=>{restarted=true};
""" + code + "\ndeploy().then(result=>console.log(JSON.stringify({result,restarted})));"
    env = dict(os.environ)
    if break_build == "rollback-fails":
        env["FAIL_ROLLBACK"] = "1"
    result = run(["node", "-e", runner], repo, env=env)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout.strip().splitlines()[-1])
    assert output["restarted"] is (not break_build)
    assert git(repo, "rev-parse", "HEAD") == (previous if break_build else candidate)
    if break_build == "rollback-fails":
        assert "rollback failed" in output["result"]["text"]
    else:
        assert (repo / "dist.txt").read_text() == ("baseline" if break_build else "candidate")
    if break_build:
        assert output["result"]["isError"] is True
