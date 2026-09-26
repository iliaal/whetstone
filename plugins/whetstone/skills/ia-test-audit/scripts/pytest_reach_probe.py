"""Pytest plugin: record every nonzero subprocess result per test.

Answers "which guard actually refused?" for suites that drive a CLI through
`subprocess` (`run`, or `Popen(...).communicate()`). Each nonzero result becomes one JSON line: test node id, argv[0]
basename, exit code, and the first and last non-empty stderr lines.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<skill>/scripts REACH_PROBE_OUT=/tmp/reach.jsonl \
        pytest -p pytest_reach_probe <candidate tests>

    python3 <skill>/scripts/pytest_reach_probe.py /tmp/reach.jsonl [--grep TEXT]

The second form prints, per test, the LAST nonzero call (usually the one the assertion
checks) and its last stderr line (the refusal, after any warnings), so each can be compared with the guard the test is
named for. The plugin only observes; it never changes a result. The output file is
truncated once per session, so rows from an earlier run never mix in. Without
REACH_PROBE_OUT it is reach-probe-<pid>.jsonl in the system temp directory, and the path
is printed in the terminal summary. It works under xdist: the controller truncates and
picks the path, and each worker appends its own lines. A test module that binds `from subprocess
import Popen` before the plugin loads still goes through the patched method, because
the patch is on the class.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

_current: dict[str, str | None] = {"nodeid": None}
_original_communicate = subprocess.Popen.communicate


def _refusal_lines(data: object) -> tuple[str, str]:
    """First and last non-empty stderr lines; a refusal usually ends the stream after warnings."""
    if isinstance(data, bytes):
        data = data.decode("utf-8", "replace")
    if not isinstance(data, str):
        return "", ""
    lines = [line.strip() for line in data.splitlines() if line.strip()]
    return (lines[0][:400], lines[-1][:400]) if lines else ("", "")


def _recording_communicate(self, *args, **kwargs):
    result = _original_communicate(self, *args, **kwargs)
    if self.returncode not in (0, None) and _current["nodeid"] is not None:
        argv = self.args
        first, last = _refusal_lines(result[1] if isinstance(result, tuple) else None)
        head = argv[0] if isinstance(argv, list | tuple) and argv else argv
        row = {
            "test": _current["nodeid"],
            "program": os.path.basename(os.fsdecode(head))
            if isinstance(head, str | bytes | os.PathLike)
            else str(head),
            "rc": self.returncode,
            "stderr_first": first,
            "stderr_last": last,
        }
        with _output_path().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    return result


def _output_path() -> Path:
    return Path(os.environ.get("REACH_PROBE_OUT") or Path(tempfile.gettempdir()) / f"reach-probe-{os.getpid()}.jsonl")


def pytest_configure(config):
    if not hasattr(config, "workerinput"):
        # xdist workers inherit the environment, so they append to the controller's file.
        os.environ["REACH_PROBE_OUT"] = str(_output_path())
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        os.close(os.open(os.environ["REACH_PROBE_OUT"], flags, 0o600))
    subprocess.Popen.communicate = _recording_communicate


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not hasattr(config, "workerinput"):
        terminalreporter.write_line(f"reach probe rows: {os.environ.get('REACH_PROBE_OUT')}")


def pytest_unconfigure(config):
    subprocess.Popen.communicate = _original_communicate


def pytest_runtest_setup(item):
    _current["nodeid"] = item.nodeid


def pytest_runtest_teardown(item, nextitem):
    _current["nodeid"] = None


def _report() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="summarise a reach-probe JSONL file")
    parser.add_argument("jsonl")
    parser.add_argument("--grep", help="only tests whose id contains TEXT")
    args = parser.parse_args()
    last: dict[str, dict] = {}
    calls: dict[str, int] = {}
    for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        last[row["test"]] = row
        calls[row["test"]] = calls.get(row["test"], 0) + 1
    for test, row in last.items():
        if args.grep and args.grep not in test:
            continue
        print(
            f"{test}\n    rc {row['rc']}  {row['program']}  ({calls[test]} nonzero calls)\n    last:  {row['stderr_last']}"
        )
        if row["stderr_first"] != row["stderr_last"]:
            print(f"    first: {row['stderr_first']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_report())
