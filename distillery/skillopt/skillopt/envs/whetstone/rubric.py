"""Per-skill process rubrics + the verbatim-evidence judge.

Salvaged and adapted from the prior hand-rolled skillopt package's rubrics.py
and judge.py -- the one genuinely useful artifact from that attempt. Each
criterion is ``(weight, evidence_definition)``; weights per skill sum to 1.0.
The evidence_definition is fed verbatim to the judge and defines what a
trajectory quote must demonstrate to earn a non-zero score.

Mirror the skill's own rules here. When a SKILL.md changes its rules, update
the matching rubric or the optimizer trains against a stale target. The
ia-debugging criteria below track that skill's Iron Law, Process steps, and
Three-Fix Threshold.

The verbatim-evidence guard is CODE-ENFORCED, not merely a judge instruction:
``score_criteria`` zeroes any criterion whose ``evidence`` does not share a
contiguous run with the trajectory (un-escaped + case/whitespace-normalized --
see ``_grounded``). A judge that hallucinates or omits a supporting quote
cannot raise ``soft``. The trajectory it grounds against is the target's full
tool-use transcript (Read/Bash/Edit events, captured as stream-json) plus the
harness-verified artifacts ``evaluator.py`` prepends (real pre/post test runs +
the agent's diff) -- evidence the agent cannot fabricate.
"""
from __future__ import annotations

import json
import re
from typing import Callable, Protocol

Rubric = dict[str, tuple[float, str]]


class CompleteFn(Protocol):
    def __call__(self, system: str, user: str) -> str: ...


RUBRICS: dict[str, Rubric] = {
    "ia-debugging": {
        "reproduced_first":      (0.20, "a reproduction step (running the failing test or a repro harness) is executed BEFORE any source edit"),
        "root_cause_evidence":   (0.30, "the root cause is stated with a file:line reference grounded in the actual code, at least two levels deep (not just 'it failed here' but why), quoted from the trajectory"),
        "one_change_at_a_time":  (0.15, "fixes are applied and validated one hypothesis at a time; no shotgun multi-file change without testing in between"),
        "failing_test_first":    (0.20, "the failing test is run/confirmed red before the fix and re-run green after -- the red->green transition is visible in the trajectory"),
        "escalated_not_guessed": (0.15, "after repeated failed attempts the agent re-grounds (re-reads the code path, invalidates the prior hypothesis explicitly) rather than guessing variants of the same theory"),
    },
}


def get(skill: str) -> Rubric:
    if skill not in RUBRICS:
        raise KeyError(
            f"No rubric for {skill!r}. Add one to rubric.RUBRICS before training it. "
            f"Known: {sorted(RUBRICS)}"
        )
    return RUBRICS[skill]


JUDGE_SYSTEM = (
    "You score whether an agent FOLLOWED a debugging process, not whether the result looks polished.\n"
    "For each criterion give a score 0.0-1.0 and a VERBATIM quote from the trajectory as evidence.\n"
    "If no supporting evidence exists in the trajectory, the score is 0.0. Do not infer. Do not be generous.\n"
    "A claim without a concrete artifact (a command that ran, a file:line, a test result) is not evidence.\n"
    'Return ONLY minified JSON: {"criteria":{"<name>":{"score":<float>,"evidence":"<verbatim quote>"}}}'
)


def _build_user_prompt(rubric: Rubric, task: str, trajectory_text: str) -> str:
    crit = "\n".join(f"- {name}: {defn}" for name, (_, defn) in rubric.items())
    return f"TASK:\n{task}\n\nCRITERIA:\n{crit}\n\nTRAJECTORY:\n{trajectory_text}"


def _coerce(raw: str) -> dict:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        # strip a leading ```json fence if the model added one
        raw = raw.split("```", 2)[1].removeprefix("json").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _regex_extract(raw: str, rubric: Rubric) -> dict[str, dict]:
    """Robust fallback when strict JSON parsing fails.

    The judge embeds VERBATIM trajectory quotes in the `evidence` field; those
    quotes routinely contain unescaped quotes/newlines that break json.loads.
    The score is what `soft` needs, so pull it per-criterion by regex and grab
    a best-effort evidence snippet (empty if the quoting is hopeless).
    """
    out: dict[str, dict] = {}
    for name in rubric:
        score, evidence = 0.0, ""
        m = re.search(rf'"{re.escape(name)}"\s*:\s*\{{\s*"score"\s*:\s*(-?[0-9]*\.?[0-9]+)', raw)
        if m:
            try:
                score = float(m.group(1))
            except ValueError:
                score = 0.0
            em = re.search(
                rf'"{re.escape(name)}"\s*:\s*\{{\s*"score"\s*:\s*-?[0-9]*\.?[0-9]+\s*,\s*"evidence"\s*:\s*"(.*?)"\s*\}}',
                raw, re.DOTALL,
            )
            if em:
                evidence = em.group(1)
        out[name] = {"score": max(0.0, min(1.0, score)), "evidence": evidence}
    return out


# Min length of a contiguous trajectory quote that counts as grounded. Tuned on
# the pilot: real judge quotes share 100+ char contiguous runs with the
# trajectory, while fabricated/boilerplate evidence tops out near 18 chars.
_MIN_EVIDENCE_RUN = 24


def _normalize(s: str) -> str:
    """Lowercase, un-escape the stream-json escapes the trajectory carries
    (``\\n \\t \\r \\" \\/``), and collapse whitespace.

    The target's transcript is captured as stream-json, so a verbatim judge
    quote ("AssertionError: assert [1, 2]") is compared against an *escaped*
    transcript (``...assert [1, 2]\\n...``). Without un-escaping, even an exact
    quote misses -- which is what silently zeroed every soft score in the pilot.
    """
    s = s or ""
    for esc, rep in (("\\n", " "), ("\\t", " "), ("\\r", " "), ('\\"', '"'), ("\\/", "/")):
        s = s.replace(esc, rep)
    return " ".join(s.split()).lower()


def _grounded(evidence: str, trajectory: str) -> bool:
    """True iff `evidence` shares a real contiguous run with `trajectory`.

    A cooperative judge quotes real spans but stitches them with ellipses and
    annotations, so requiring the WHOLE evidence to be a substring is too strict
    -- it zeroes genuine process (observed in the pilot). Instead require any
    ``>=_MIN_EVIDENCE_RUN`` contiguous (normalized) span of the evidence to
    appear in the trajectory: a summarizing judge still lands one long real
    span; a fabricating one cannot manufacture 24 contiguous real chars. Short
    evidence must appear in full.
    """
    e = _normalize(evidence)
    t = _normalize(trajectory)
    if not e:
        return False
    if len(e) < _MIN_EVIDENCE_RUN:
        return len(e) >= 8 and e in t
    return any(e[i:i + _MIN_EVIDENCE_RUN] in t for i in range(0, len(e) - _MIN_EVIDENCE_RUN + 1))


def score_criteria(rubric: Rubric, task: str, trajectory_text: str,
                   complete: CompleteFn) -> dict[str, dict]:
    """Return {criterion: {"score": float, "evidence": str}} for every rubric key.

    Strict JSON first; on failure fall back to a per-criterion regex extract
    (the judge's verbatim evidence quotes often break strict json.loads). Only a
    judge call that errors entirely yields all-zero criteria (conservative).
    """
    try:
        raw = complete(JUDGE_SYSTEM, _build_user_prompt(rubric, task, trajectory_text))
    except Exception:
        return {name: {"score": 0.0, "evidence": ""} for name in rubric}

    parsed: dict = {}
    try:
        parsed = _coerce(raw).get("criteria", {})
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}

    out: dict[str, dict] = {}
    missing = False
    for name in rubric:
        c = parsed.get(name)
        if not isinstance(c, dict) or "score" not in c:
            missing = True
            out[name] = {"score": 0.0, "evidence": ""}
            continue
        try:
            score = float(c.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        out[name] = {"score": max(0.0, min(1.0, score)), "evidence": str(c.get("evidence", ""))}

    # Strict parse dropped one or more criteria (usually malformed evidence
    # strings) -- recover scores by regex rather than silently scoring them 0.
    if missing:
        fallback = _regex_extract(raw, rubric)
        for name in rubric:
            if out[name]["score"] == 0.0 and not out[name]["evidence"]:
                out[name] = fallback[name]

    # Code-enforced verbatim-evidence guard: a criterion only keeps its score
    # if its evidence is an actual quote from the trajectory. This is the
    # anti-reward-hacking backstop -- it does not depend on the judge obeying
    # the "no quote -> 0.0" instruction.
    for name in rubric:
        is_grounded = _grounded(out[name]["evidence"], trajectory_text)
        out[name]["grounded"] = is_grounded
        if not is_grounded:
            out[name]["score"] = 0.0
    return out


def weighted_soft(rubric: Rubric, criteria: dict[str, dict]) -> float:
    """Weighted process score in [0, 1]. The breakdown is what drives the edit;
    this scalar is what the trainer gates on alongside hard."""
    return round(sum(w * criteria.get(name, {}).get("score", 0.0)
                     for name, (w, _) in rubric.items()), 4)
