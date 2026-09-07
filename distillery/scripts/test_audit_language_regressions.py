import re
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def atomic_write_example():
    reference = (
        Path(__file__).resolve().parents[2]
        / "plugins/whetstone/skills/ia-linux-bash-scripting/references/production-patterns.md"
    ).read_text()
    block = re.search(r"```bash\n(atomic_write\(\).*?)\n```", reference, re.DOTALL)
    assert block is not None
    return block.group(1).rsplit("\natomic_write ", 1)[0]


@pytest.mark.parametrize("producer_status", [0, 17])
def test_atomic_write_commits_only_successful_generation(
    tmp_path, atomic_write_example, producer_status
):
    target = tmp_path / "config with spaces.yml"
    target.write_bytes(b"known-good\n")
    script = "set -Eeuo pipefail\n" + atomic_write_example + """
generate_config() { printf '%s' "$2"; return "$1"; }
atomic_write "$1" generate_config "$2" "$3"
"""
    result = subprocess.run(
        ["bash", "-c", script, "test", str(target), str(producer_status), "new-content"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == producer_status, result.stderr
    assert target.read_bytes() == (
        b"new-content" if producer_status == 0 else b"known-good\n"
    )
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_cleans_staging_file_when_rename_fails(tmp_path, atomic_write_example):
    target = tmp_path / "existing-directory"
    target.mkdir()
    sentinel = target / "keep"
    sentinel.write_bytes(b"original")
    script = "set -Eeuo pipefail\n" + atomic_write_example + """
atomic_write "$1" printf '%s' new-content
"""
    result = subprocess.run(
        ["bash", "-c", script, "test", str(target)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert sentinel.read_bytes() == b"original"
    assert list(target.iterdir()) == [sentinel]
    assert list(tmp_path.iterdir()) == [target]
