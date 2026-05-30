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
            fixture = str(item.get("fixture") or item.get("id"))
            fixture_dir = os.path.join(tasks_root, fixture)
            if not os.path.isdir(fixture_dir):
                raise FileNotFoundError(
                    f"Fixture dir not found for task {item.get('id')!r}: {fixture_dir}"
                )
            item["_fixture_dir"] = fixture_dir
        return items
