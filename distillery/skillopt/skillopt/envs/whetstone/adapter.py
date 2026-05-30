"""Whetstone environment adapter for SkillOpt's ReflACT trainer.

Wires the fixture dataloader, the agentic debugging rollout, and the generic
reflect stage. Mirrors the upstream searchqa adapter's shape so the trainer and
``get_adapter`` config plumbing work unchanged; the env-specific parts are the
dataloader, the rollout (claude_code_exec), and the per-skill rubric.
"""
from __future__ import annotations

import os

from skillopt.datasets.base import BatchSpec
from skillopt.envs.base import EnvAdapter
from skillopt.gradient.reflect import run_minibatch_reflect

from .dataloader import WhetstoneDataLoader
from .rollout import optimizer_complete, run_batch
from .rubric import get as get_rubric


class WhetstoneAdapter(EnvAdapter):
    """Optimize a Whetstone process skill against curated fixtures."""

    def __init__(
        self,
        split_dir: str = "",
        data_path: str = "",
        split_mode: str = "split_dir",
        split_ratio: str = "2:1:7",
        split_seed: int = 42,
        split_output_dir: str = "",
        tasks_root: str = "",
        skill_name: str = "ia-debugging",
        target_model: str = "",
        exec_timeout: int = 300,
        test_timeout: int = 120,
        workers: int = 4,
        analyst_workers: int = 8,
        failure_only: bool = False,
        minibatch_size: int = 8,
        edit_budget: int = 4,
        seed: int = 42,
        limit: int = 0,
    ) -> None:
        self.skill_name = skill_name
        self.rubric = get_rubric(skill_name)  # fail fast if no rubric for this skill
        self.target_model = target_model
        self.exec_timeout = int(exec_timeout)
        self.test_timeout = int(test_timeout)
        self.workers = int(workers)
        self.analyst_workers = int(analyst_workers)
        self.failure_only = failure_only
        self.minibatch_size = int(minibatch_size)
        self.edit_budget = int(edit_budget)
        self.dataloader = WhetstoneDataLoader(
            split_dir=split_dir,
            data_path=data_path,
            split_mode=split_mode,
            split_ratio=split_ratio,
            split_seed=split_seed,
            split_output_dir=split_output_dir,
            tasks_root=tasks_root,
            seed=seed,
            limit=limit,
        )

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def setup(self, cfg: dict) -> None:
        super().setup(cfg)
        if not self.target_model:
            self.target_model = cfg.get("target_model", "") or ""
        self.dataloader.setup(cfg)

    def get_dataloader(self):
        return self.dataloader

    # ── Batch construction ─────────────────────────────────────────────────

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        batch = self.dataloader.build_train_batch(batch_size=batch_size, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        batch = self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed, **kwargs)
        return self.build_env_from_batch(batch, **kwargs)

    # ── Rollout / reflect ────────────────────────────────────────────────────

    def rollout(self, env_manager, skill_content: str, out_dir: str, **kwargs) -> list[dict]:
        items: list[dict] = env_manager
        return run_batch(
            items=items,
            out_root=out_dir,
            skill_content=skill_content,
            rubric=self.rubric,
            model=self.target_model,
            complete=optimizer_complete,
            exec_timeout=self.exec_timeout,
            test_timeout=self.test_timeout,
            workers=self.workers,
        )

    def reflect(self, results: list[dict], skill_content: str, out_dir: str, **kwargs) -> list[dict | None]:
        prediction_dir = kwargs.get("prediction_dir", os.path.join(out_dir, "predictions"))
        patches_dir = kwargs.get("patches_dir", os.path.join(out_dir, "patches"))
        return run_minibatch_reflect(
            results=results,
            skill_content=skill_content,
            prediction_dir=prediction_dir,
            patches_dir=patches_dir,
            workers=self.analyst_workers,
            failure_only=self.failure_only,
            minibatch_size=self.minibatch_size,
            edit_budget=self.edit_budget,
            random_seed=kwargs.get("random_seed"),
            error_system=self.get_error_minibatch_prompt(),
            success_system=self.get_success_minibatch_prompt(),
            step_buffer_context=kwargs.get("step_buffer_context", ""),
            meta_skill_context=kwargs.get("meta_skill_context", ""),
            update_mode=getattr(self, "_cfg", {}).get("skill_update_mode", "patch"),
        )

    def get_task_types(self) -> list[str]:
        return ["debugging"]
