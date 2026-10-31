import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name('configure-codex-skill-sources.py')
SPEC = importlib.util.spec_from_file_location('codex_skill_sources', SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load the Codex skill source helper")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


@pytest.mark.parametrize('name', [
    'ascii', 'café', '🛠', '𐐀', 'quote"', 'back\\slash', 'tab\t',
    'newline\n', 'return\r', 'backspace\b', 'formfeed\f', 'delete\x7f',
    'separator\u2028\u2029', *[f'control{chr(value)}' for value in range(32)],
])
def test_paths_round_trip_through_toml(name):
    path = Path('/checkout') / name / 'SKILL.md'
    parsed = tomllib.loads(MODULE.render_block([path]))
    assert parsed['skills']['config'] == [{'path': str(path), 'enabled': False}]


def test_cli_preserves_config_and_unicode_paths(tmp_path):
    repo = tmp_path / 'checkout-🛠-café'
    script = repo / 'scripts' / SCRIPT.name
    script.parent.mkdir(parents=True)
    shutil.copyfile(SCRIPT, script)
    skill = repo / 'plugins/whetstone/skills/ia-example/SKILL.md'
    skill.parent.mkdir(parents=True)
    skill.write_text('# Example\n', encoding='utf-8')
    home = tmp_path / 'codex'
    home.mkdir()
    config = home / 'config.toml'
    original = 'model = "existing-model"\n'
    config.write_text(original, encoding='utf-8')
    command = [sys.executable, str(script), '--codex-home', str(home)]
    dry = subprocess.run([*command, '--dry-run'], check=True, capture_output=True, text=True)
    assert config.read_text(encoding='utf-8') == original
    expected = {'model': 'existing-model', 'skills': {'config': [
        {'path': str(skill.resolve()), 'enabled': False},
    ]}}
    assert tomllib.loads(dry.stdout) == expected
    subprocess.run(command, check=True, capture_output=True)
    first = config.read_bytes()
    assert tomllib.loads(first.decode('utf-8')) == expected
    subprocess.run(command, check=True, capture_output=True)
    assert config.read_bytes() == first
    subprocess.run([*command, '--remove'], check=True, capture_output=True)
    assert config.read_text(encoding='utf-8') == original
