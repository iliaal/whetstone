"""Exercise local sync with a copied script and a synthetic home."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest


SCRIPT = Path(__file__).with_name("sync-to-tools.sh")


@pytest.mark.parametrize("source", ["missing", "file", "empty"])
@pytest.mark.parametrize("dry_run", [False, True])
def test_sync_source_availability(source, dry_run):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        scripts = root / "checkout" / "scripts"
        scripts.mkdir(parents=True)
        shutil.copyfile(SCRIPT, scripts / SCRIPT.name)
        skills = scripts.parent / "plugins" / "whetstone" / "skills"
        skills.parent.mkdir(parents=True)
        if source == "file":
            skills.write_text("not a directory")
        elif source == "empty":
            skills.mkdir()

        home = root / "home"
        codex = home / ".codex"
        fake_bin = root / "bin"
        fake_bin.mkdir()
        probe = root / "codex-probed"
        helper = root / "helper-called"
        (fake_bin / "codex").write_text(
            '#!/bin/sh\ntouch "$PROBE"\nprintf \'%s\\n\' '
            '\'{"installed":[{"pluginId":"whetstone@whetstone","installed":true,"enabled":true}]}\'\n'
        )
        (fake_bin / "codex").chmod(0o755)
        (scripts / "configure-codex-skill-sources.py").write_text(
            'import os\nfrom pathlib import Path\nPath(os.environ["HELPER"]).touch()\n'
        )

        links = []
        for parent in (home / ".agents", home / ".kilocode", codex):
            dest = parent / "skills"
            dest.mkdir(parents=True)
            link = dest / "ia-retired"
            link.symlink_to(skills / link.name)
            links.append(link)
            (dest / "unowned").write_text("preserve")
        result = subprocess.run(
            ["bash", str(scripts / SCRIPT.name), *(["--dry-run"] if dry_run else [])],
            env={**os.environ, "HOME": str(home), "CODEX_HOME": str(codex),
                 "PATH": str(fake_bin) + os.pathsep + os.environ["PATH"],
                 "PROBE": str(probe), "HELPER": str(helper)},
            capture_output=True, text=True, timeout=10,
        )
        if source != "empty":
            assert result.returncode == 1, result
            assert f"Skills source directory is missing or not a directory: {skills}" in result.stderr
            assert "Synced" not in result.stdout
            assert not probe.exists()
            assert not helper.exists()
        else:
            assert result.returncode == 0, result
            assert "Synced 0 skills to 2 tools: +0 -3 =0" in result.stdout
            assert probe.is_file()
            assert helper.is_file()

        for link in links:
            assert link.is_symlink() == (source != "empty" or dry_run)
            assert (link.parent / "unowned").read_text() == "preserve"
