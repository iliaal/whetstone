"""Whetstone process-skill optimization environment.

Optimizes a Whetstone process SKILL.md (currently ia-debugging) by running
Claude Code agentically against seeded-bug fixtures. The reward is hybrid:

- ``hard`` (0/1): deterministic -- does the fixture's test go red -> green
  after the agent's rollout (run by the evaluator, not trusted to the agent).
- ``soft`` (0-1): a per-skill process rubric scored by the optimizer model on
  the rollout trajectory, with CODE-ENFORCED verbatim-evidence grounding (a
  criterion whose evidence shares no contiguous run with the trajectory is
  zeroed -- the judge cannot raise it by claiming). The trajectory is the
  target's tool-use transcript (full ordered stream only when nested in a Claude
  Code session, CLAUDE_CODE_COORDINATOR_MODE=1; else the final message) plus
  always-present harness-verified artifacts (real pre/post test runs + the
  agent's diff) the agent cannot fabricate.

Note: the vendored gate accepts on ``hard`` only; ``soft`` informs the
analyst's reflection but does not decide accept/reject. Calibrate fixtures so
baseline ``hard`` < 1.0, or no edit can be accepted.

This is the only environment registered in the vendored, trimmed SkillOpt.
See ../../../VENDORED.md for the upstream source.
"""
from .adapter import WhetstoneAdapter

__all__ = ["WhetstoneAdapter"]
