import importlib.util
import locale
import os
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


@pytest.mark.parametrize('remove', [False, True], ids=['configure', 'remove'])
@pytest.mark.parametrize('dry_run', [False, True], ids=['write', 'dry-run'])
def test_cli_reads_utf8_config_in_ascii_locale(tmp_path, remove, dry_run):
    home = tmp_path / 'codex'
    home.mkdir()
    config = home / 'config.toml'
    original = 'model = "café-🛠"\n'
    block = MODULE.render_block([Path('/existing/🛠/SKILL.md')])
    initial = MODULE.replace_managed_block(original, block) if remove else original
    config.write_text(initial, encoding='utf-8')
    # Disable Python's UTF-8 mode and locale coercion, while keeping stdout UTF-8.
    env = {**os.environ, 'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '0',
           'PYTHONCOERCECLOCALE': '0', 'PYTHONIOENCODING': 'utf-8'}
    command = [sys.executable, str(SCRIPT), '--codex-home', str(home)]
    if remove:
        command.append('--remove')
    if dry_run:
        command.append('--dry-run')
    result = subprocess.run(command, env=env, check=True, capture_output=True)
    expected = original if remove else MODULE.replace_managed_block(
        original, MODULE.render_block(MODULE.skill_paths(SCRIPT.resolve().parent.parent)))
    if dry_run:
        assert result.stdout.decode('utf-8') == expected
        assert config.read_bytes() == initial.encode('utf-8')
    else:
        assert config.read_bytes() == expected.encode('utf-8')
        subprocess.run(command, env=env, check=True, capture_output=True)
        assert config.read_bytes() == expected.encode('utf-8')


@pytest.mark.parametrize('remove', [False, True], ids=['configure', 'remove'])
@pytest.mark.parametrize('locale_name', ['ascii', 'de_DE.iso88591'])
def test_dry_run_emits_utf8_bytes(tmp_path, remove, locale_name):
    home = tmp_path / 'codex'
    home.mkdir()
    config = home / 'config.toml'
    original = 'model = "café-🛠"\n'
    initial = MODULE.replace_managed_block(
        original, MODULE.render_block([Path('/existing/🛠/SKILL.md')])) if remove else original
    config.write_text(initial, encoding='utf-8')
    env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
    if locale_name == 'ascii':
        # Exercise ASCII stdout even on hosts where Python coerces C to UTF-8.
        env.update(LC_ALL='C', PYTHONUTF8='0', PYTHONCOERCECLOCALE='0')
    else:
        previous = locale.setlocale(locale.LC_CTYPE)
        try:
            locale.setlocale(locale.LC_CTYPE, locale_name)
        except locale.Error:
            pytest.skip()  # The parametrized real locale is not installed.
        finally:
            locale.setlocale(locale.LC_CTYPE, previous)
        # A real non-UTF-8 locale with Python's default encoding settings.
        env['LC_ALL'] = locale_name
    command = [sys.executable, str(SCRIPT), '--codex-home', str(home), '--dry-run']
    if remove:
        command.append('--remove')
    result = subprocess.run(command, env=env, check=True, capture_output=True)
    expected = original if remove else MODULE.replace_managed_block(
        original, MODULE.render_block(MODULE.skill_paths(SCRIPT.resolve().parent.parent)))
    assert result.stdout == expected.encode('utf-8')
    assert config.read_bytes() == initial.encode('utf-8')
