import os
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "plugins/whetstone/skills/ia-debugging/scripts/collect-diagnostics.sh"
ISOLATION = ROOT / "plugins/whetstone/skills/ia-verification-before-completion/references/isolated-verification.md"


class DiagnosticCaptureTests(unittest.TestCase):
    def test_remote_credentials_are_removed_before_both_outputs(self):
        cases = (
            ("https://alice:FIXTURE-PASSWORD@git.example.invalid:8443/org/repo.git",
             "https://<REDACTED>@git.example.invalid:8443/org/repo.git"),
            ("https://FIXTURE-TOKEN@git.example.invalid/org/repo.git",
             "https://<REDACTED>@git.example.invalid/org/repo.git"),
            ("https://git.example.invalid/org/repo.git?access_token=FIXTURE-QUERY#FIXTURE-FRAGMENT",
             "https://git.example.invalid/org/repo.git"),
            ("https://git.example.invalid/org/repo.git", "https://git.example.invalid/org/repo.git"),
            ("git@git.example.invalid:org/repo.git", "git@git.example.invalid:org/repo.git"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            bin_dir = directory / "bin"
            bin_dir.mkdir()
            for tool in ("bash", "date", "uname", "whoami", "df", "head", "tail", "awk", "wc", "tr"):
                executable = shutil.which(tool)
                self.assertIsNotNone(executable, tool)
                (bin_dir / tool).symlink_to(executable)
            fake_git = bin_dir / "git"
            fake_git.write_text(
                '#!/bin/sh\ncase "$*" in\n'
                '  "rev-parse --is-inside-work-tree") printf "true\\n" ;;\n'
                '  "branch --show-current") printf "fixture\\n" ;;\n'
                '  "remote get-url origin") printf "%s\\n" "$REMOTE_FIXTURE" ;;\n'
                'esac\n',
                encoding="utf-8",
            )
            fake_git.chmod(0o755)
            for remote, expected in cases:
                with self.subTest(remote=remote):
                    env = {"PATH": str(bin_dir), "REMOTE_FIXTURE": remote}
                    displayed = subprocess.run(
                        [shutil.which("bash"), str(COLLECTOR)], cwd=directory, env=env,
                        text=True, capture_output=True, timeout=10,
                    )
                    self.assertEqual(displayed.returncode, 0, displayed.stderr)
                    artifact = directory / "diagnostics.md"
                    saved = subprocess.run(
                        [shutil.which("bash"), str(COLLECTOR), str(artifact)], cwd=directory, env=env,
                        text=True, capture_output=True, timeout=10,
                    )
                    self.assertEqual(saved.returncode, 0, saved.stderr)
                    for output in (displayed.stdout, artifact.read_text(encoding="utf-8")):
                        self.assertIn(f"| Remote | {expected} |", output)
                        self.assertNotIn("FIXTURE-", output)


class IsolationRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repo = self.directory / "caller"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        self.git("config", "core.hooksPath", str(self.directory / "empty-hooks"))
        for name in ("committed", "staged", "caller"):
            (self.repo / f"{name}.py").write_text("VALUE = 0\n", encoding="utf-8")
        (self.repo / "mixed.py").write_text("OWNED = 0\nCALLER = 0\n", encoding="utf-8")
        self.git("add", "committed.py", "staged.py", "caller.py", "mixed.py")
        self.git("commit", "-qm", "fixture base")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *arguments, cwd=None):
        return subprocess.run(
            ["git", "-C", str(cwd or self.repo), *arguments],
            text=True, capture_output=True, check=True, timeout=10,
        )

    def caller_state(self):
        files = {}
        for path in self.repo.rglob("*"):
            relative = path.relative_to(self.repo)
            if ".git" in relative.parts or path.is_dir():
                continue
            files[str(relative)] = (path.lstat().st_mode, os.readlink(path) if path.is_symlink() else path.read_bytes())
        return files, (self.repo / ".git/index").read_bytes()

    def run_recipe(self, paths, assertions, patch=None):
        source = ISOLATION.read_text(encoding="utf-8")
        recipe = re.search(r"```bash\n(.*?)\n```", source, re.DOTALL).group(1)
        recipe = recipe.replace("<known-good-commit>", self.base)
        recipe = re.sub(r"^owned_paths=.*$", "owned_paths=(" + " ".join(map(shlex.quote, paths)) + ")", recipe, flags=re.MULTILINE)
        recipe = recipe.replace('owned_patch=""', "owned_patch=" + shlex.quote(str(patch)) if patch else 'owned_patch=""')
        recipe = recipe.replace("<build-command>", "python3 -m compileall -q .")
        recipe = recipe.replace("<test-command>", "python3 -c " + shlex.quote(assertions))
        before = self.caller_state()
        env = dict(os.environ, TMPDIR=str(self.directory), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            ["bash", "-c", recipe], cwd=self.repo, env=env,
            text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(self.caller_state(), before, "caller files or index changed")
        return result

    def test_committed_staged_and_selected_untracked_bytes_are_exercised(self):
        (self.repo / "committed.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.git("add", "committed.py")
        self.git("commit", "-qm", "owned committed change")
        (self.repo / "staged.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.git("add", "staged.py")
        (self.repo / "selected_new.py").write_text("VALUE = 3\n", encoding="utf-8")
        (self.repo / "caller.py").write_text("VALUE = 99\n", encoding="utf-8")
        self.git("add", "caller.py")
        (self.repo / "unselected.py").write_text("VALUE = 99\n", encoding="utf-8")
        result = self.run_recipe(
            ["committed.py", "staged.py", "selected_new.py"],
            "import committed, staged, selected_new, caller; from pathlib import Path; "
            "assert (committed.VALUE, staged.VALUE, selected_new.VALUE) == (1, 2, 3); "
            "assert caller.VALUE == 0; assert not Path('unselected.py').exists()",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def owned_patch(self, include_caller=False):
        prepared = self.directory / "owned-source"
        self.git("worktree", "add", "--detach", str(prepared), self.base)
        (prepared / "mixed.py").write_text("OWNED = 1\nCALLER = 0\n", encoding="utf-8")
        (prepared / "new_owned.py").write_text("VALUE = 2\n", encoding="utf-8")
        self.git("add", "mixed.py", "new_owned.py", cwd=prepared)
        if include_caller:
            (prepared / "caller.py").write_text("VALUE = 77\n", encoding="utf-8")
            self.git("add", "caller.py", cwd=prepared)
        patch = self.directory / "reviewed-owned.patch"
        patch.write_text(self.git("diff", "--cached", "--no-textconv", "--no-ext-diff", "--binary", self.base, cwd=prepared).stdout, encoding="utf-8")
        return patch

    def test_reviewed_patch_excludes_staged_caller_hunks_in_the_same_file(self):
        (self.repo / "mixed.py").write_text("OWNED = 1\nCALLER = 99\n", encoding="utf-8")
        self.git("add", "mixed.py")
        result = self.run_recipe(
            ["mixed.py", "new_owned.py"],
            "import mixed, new_owned; assert (mixed.OWNED, mixed.CALLER, new_owned.VALUE) == (1, 0, 2)",
            self.owned_patch(),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_patch_outside_selected_manifest_cannot_run_the_proof_command(self):
        marker = self.directory / "proof-ran"
        result = self.run_recipe(
            ["mixed.py", "new_owned.py"],
            "from pathlib import Path; Path(" + repr(str(marker)) + ").touch()",
            self.owned_patch(include_caller=True),
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(marker.exists(), "unselected patch content reached the proof command")
