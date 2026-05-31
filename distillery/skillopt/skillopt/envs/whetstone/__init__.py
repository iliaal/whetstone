"""Whetstone process-skill optimization environment.

Optimizes a Whetstone process SKILL.md (currently ia-debugging) by running
Claude Code agentically against seeded-bug fixtures. The reward is hybrid:

- ``hard`` (0/1): deterministic -- does the fixture's test go red -> green
  after the agent's rollout (run by the evaluator, not trusted to the agent).
- ``soft`` (0-1): a per-skill process rubric scored by the optimizer model on
  the rollout trajectory, with CODE-ENFORCED verbatim-evidence guarding (a
  criterion whose evidence is not a literal substring of the trajectory is
  zeroed -- the judge cannot raise it by claiming). The trajectory is augmented
  with harness-verified artifacts (real pre/post test runs + the agent's diff)
  so grounding bites against evidence the agent cannot fabricate.

This is the only environment registered in the vendored, trimmed SkillOpt.
See ../../../VENDORED.md for the upstream source.
"""
from .adapter import WhetstoneAdapter

__all__ = ["WhetstoneAdapter"]
