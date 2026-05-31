"""Whetstone fixture-task dataloader.

Reads a ``split_dir`` with ``train/``, ``val/``, ``test/`` subdirs, each holding
one JSON array of task items. Each item references a fixture directory (buggy
source + a failing test) by name; this loader resolves it to an absolute path
(``_fixture_dir``) so the rollout can copy it into the agent's workspace.

Item schema (one entry of train/items.json):

    {
      "id": "dbg-001",
      "question": "<bug report shown to the agent>",
      "context": "<repo tree + failing test output>",
      "fixture": "dbg-001",                 # dir under <tasks_root>/
      "test_cmd": ["-m", "pytest", "-q"]    # args after the python interpreter
    }
"""
from __future__ import annotations

import os

from skillopt.datasets.base import SplitDataLoader


def _resolve_fixture_dir(tasks_root: str, item: dict) -> str:
    """Resolve a task's fixture dir, refusing any path that escapes tasks_root.

    `fixture`/`id` come from the split JSON; an absolute or ``..``-laden value
    would otherwise let ``os.path.join`` point copytree at an arbitrary host
    directory (whose contents would then be copied into the bypassPermissions
    workspace and whose ``test_*.py`` would be executed). The realpath +
    commonpath check keeps the fixture inside the curated tree even if the split
    file is wrong or hostile.
    """
    fixture = str(item.get("fixture") or item.get("id") or "").strip()
    if not fixture:
        raise ValueError(
            f"Task {item.get('id')!r} has neither 'fixture' nor 'id'; "
            "cannot resolve a fixture directory."
        )
    root = os.path.realpath(tasks_root)
    fixture_dir = os.path.realpath(os.path.join(root, fixture))
    if os.path.commonpath([root, fixture_dir]) != root:
        raise ValueError(
            f"Fixture {fixture!r} for task {item.get('id')!r} escapes tasks_root ({root})."
        )
    if not os.path.isdir(fixture_dir):
        raise FileNotFoundError(
            f"Fixture dir not found for task {item.get('id')!r}: {fixture_dir}"
        )
    return fixture_dir


class WhetstoneDataLoader(SplitDataLoader):
    """Fixture-backed dataloader. Only ``split_mode=split_dir`` is supported for
    the pilot (curated fixtures, not a ratio split of raw data)."""

    def __init__(self, *args, tasks_root: str = "", **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tasks_root = tasks_root

    def setup(self, cfg: dict) -> None:
        if not self._tasks_root:
            self._tasks_root = cfg.get("tasks_root", "")
        super().setup(cfg)

    def _resolve_tasks_root(self) -> str:
        if self._tasks_root:
            return os.path.abspath(self._tasks_root)
        # Default: a sibling `tasks/` dir next to the split_dir.
        return os.path.abspath(os.path.join(self.split_dir, os.pardir, "tasks"))

    def load_split_items(self, split_path: str) -> list[dict]:
        items = super().load_split_items(split_path)
        tasks_root = self._resolve_tasks_root()
        for item in items:
            item["_fixture_dir"] = _resolve_fixture_dir(tasks_root, item)
        return items
