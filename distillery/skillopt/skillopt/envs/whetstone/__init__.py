"""Whetstone process-skill optimization environment.

Optimizes a Whetstone process SKILL.md (currently ia-debugging) by running
Claude Code agentically against seeded-bug fixtures. The reward is hybrid:

- ``hard`` (0/1): deterministic -- does the fixture's test go red -> green
  after the agent's rollout (run by the evaluator, not trusted to the agent).
- ``soft`` (0-1): a per-skill process rubric scored by the optimizer model on
  the rollout trajectory, with verbatim-evidence guarding (no quote -> 0.0).

This is the only environment registered in the vendored, trimmed SkillOpt.
See ../../../VENDORED.md for the upstream source.
"""
from .adapter import WhetstoneAdapter

__all__ = ["WhetstoneAdapter"]
