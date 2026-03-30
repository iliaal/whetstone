#!/usr/bin/env python3
"""Skill evolution via DSPy GEPA -- wraps SKILL.md as a DSPy module and
runs reflective prompt optimization against eval datasets.

Usage (called from distiller.py):
    from evolve import evolve_skill
    result = evolve_skill("code-review", dataset="golden", iterations=5)
"""

import json
import os
import sys
from pathlib import Path

# DSPy imports are deferred to evolve_skill() so distiller.py can load
# without DSPy installed (only Phase 4 needs it).


def _split_skill(skill_text):
    """Split SKILL.md into frontmatter and body.
    Returns (frontmatter_str, body_str). Frontmatter includes the --- delimiters.
    """
    if not skill_text.startswith("---"):
        return "", skill_text
    parts = skill_text.split("---", 2)
    if len(parts) < 3:
        return "", skill_text
    frontmatter = f"---{parts[1]}---"
    body = parts[2].lstrip("\n")
    return frontmatter, body


def _reassemble_skill(frontmatter, body):
    """Reassemble SKILL.md from frontmatter and body."""
    if frontmatter:
        return f"{frontmatter}\n\n{body}\n"
    return body


def _make_diff(original, evolved, skill_name):
    """Generate a unified diff between original and evolved skill text."""
    import difflib
    orig_lines = original.splitlines(keepends=True)
    evol_lines = evolved.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, evol_lines,
        fromfile=f"a/skills/{skill_name}/SKILL.md",
        tofile=f"b/skills/{skill_name}/SKILL.md",
    )
    return "".join(diff)


def evolve_skill(skill_name, skill_path, dataset_path, iterations=5, model=None,
                 optimizer="gepa", max_growth_pct=20, fitness="keyword"):
    """Run DSPy optimization on a skill's body text.

    Args:
        skill_name: skill directory name
        skill_path: path to SKILL.md
        dataset_path: path to eval JSONL (golden.jsonl or sessions.jsonl)
        iterations: max optimization steps (GEPA max_full_evals)
        model: LiteLLM model string for DSPy (default: openrouter/deepseek/deepseek-v3.2)
        optimizer: "gepa" (default), "mipro", or "bootstrap"
        max_growth_pct: max allowed growth of skill body (default: 20%)
        fitness: "keyword" (fast, cheap) or "llm-judge" (Sonnet 4.6 via claude -p, ~$0.10/call)

    Returns dict with original text, evolved text, diff, and metrics.
    """
    try:
        import dspy
        from dspy.teleprompt.gepa.gepa import ScoreWithFeedback
    except ImportError:
        print("Error: DSPy not installed. Run: pip install dspy", file=sys.stderr)
        sys.exit(1)

    # Load env for API key
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Load skill
    skill_text = Path(skill_path).read_text()
    frontmatter, body = _split_skill(skill_text)
    baseline_body_len = len(body)
    print(f"Loaded skill: {skill_path} ({baseline_body_len} chars body)", file=sys.stderr)

    # Load eval dataset
    examples_raw = []
    with open(dataset_path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples_raw.append(json.loads(line))
    print(f"Loaded {len(examples_raw)} eval examples from {dataset_path}", file=sys.stderr)

    # Configure DSPy LM
    model = model or "openrouter/deepseek/deepseek-v3.2"
    lm = dspy.LM(
        model,
        api_key=api_key,
        api_base="https://openrouter.ai/api/v1",
        max_tokens=4000,
        temperature=0.3,
    )
    dspy.configure(lm=lm)

    # --- SkillModule: wraps skill body as the optimizable parameter ---
    # The skill body becomes the signature instructions (docstring), which is what
    # GEPA/MIPROv2 evolve. Input is just the task; the skill text IS the prompt.

    class TaskWithSkill(dspy.Signature):
        __doc__ = body  # skill body as the instruction -- this is what GEPA rewrites
        task_input: str = dspy.InputField(desc="What the user asked the agent to do")
        output: str = dspy.OutputField(desc="The agent's response to the task")

    class SkillModule(dspy.Module):
        def __init__(self):
            super().__init__()
            self.predictor = dspy.ChainOfThought(TaskWithSkill)

        def forward(self, task_input):
            return self.predictor(task_input=task_input)

    # --- Fitness metric with feedback for GEPA ---

    # Import judge infrastructure from distiller for LLM-judge fitness
    if fitness == "llm-judge":
        import subprocess as _sp
        _judge_system = (
            "You are an expert evaluator scoring an AI agent's response quality.\n\n"
            "You will receive:\n"
            "- SKILL INSTRUCTIONS: A methodology/skill the agent had available\n"
            "- TASK INPUT: What the user asked\n"
            "- AGENT OUTPUT: What the agent produced\n\n"
            "Score each dimension 0-10 (integers only):\n"
            "1. CORRECTNESS: Did the agent correctly address the task? (0=wrong, 10=perfect)\n"
            "2. PROCEDURE_FOLLOWING: Did the agent follow the skill's methodology? "
            "(0=ignored, 5=not applicable, 10=followed every step)\n"
            "3. CONCISENESS: Appropriately concise? (0=verbose/incomplete, 10=perfect density)\n\n"
            "Also provide one sentence of FEEDBACK explaining the biggest weakness.\n\n"
            "Respond with ONLY valid JSON:\n"
            '{"correctness": <0-10>, "procedure_following": <0-10>, "conciseness": <0-10>, '
            '"feedback": "<one sentence on biggest weakness>"}'
        )
        _judge_calls = [0]  # mutable counter for tracking cost

    def skill_fitness(gold, pred, trace=None, pred_name=None, pred_trace=None):
        """Score the predicted output against the gold example.
        Returns ScoreWithFeedback for GEPA's reflective evolution.
        """
        expected_signal = gold.get("signal", "positive")
        output_text = pred.output if hasattr(pred, "output") else str(pred)

        if not output_text or len(output_text.strip()) < 10:
            return ScoreWithFeedback(score=0.0, feedback="Empty or trivially short output.")

        if fitness == "llm-judge":
            return _llm_judge_fitness(gold, output_text, expected_signal)
        else:
            return _keyword_fitness(gold, output_text, expected_signal)

    def _keyword_fitness(gold, output_text, expected_signal):
        """Fast keyword-overlap fitness. Cheap but coarse."""
        gold_output = gold.get("agent_output", "")
        if gold_output:
            gold_words = {w for w in gold_output.lower().split() if len(w) >= 4}
            pred_words = {w for w in output_text.lower().split() if len(w) >= 4}
            overlap = len(gold_words & pred_words) / len(gold_words) if gold_words else 0.5
        else:
            overlap = 0.5

        score = 0.3 + 0.5 * overlap
        output_len = len(output_text)
        gold_len = len(gold_output) if gold_output else 1000
        ratio = output_len / max(gold_len, 1)
        if ratio > 2.0:
            score -= 0.15
        elif ratio < 0.1:
            score -= 0.2
        score = max(0.0, min(1.0, score))

        feedback_parts = []
        if overlap < 0.3:
            feedback_parts.append("Low content overlap -- skill instructions may be too vague.")
        if ratio > 2.0:
            feedback_parts.append("Output excessively verbose.")
        if ratio < 0.1:
            feedback_parts.append("Output far too short.")
        if expected_signal == "negative":
            feedback_parts.append("Historically negative example -- original skill failed here.")
        feedback = " ".join(feedback_parts) if feedback_parts else "Acceptable output."
        return ScoreWithFeedback(score=round(score, 3), feedback=feedback)

    def _llm_judge_fitness(gold, output_text, expected_signal):
        """LLM-as-judge fitness via claude -p. Expensive but accurate."""
        import re as _re_local
        task_input = gold.get("task_input", "")[:3000]

        prompt = (
            f"{_judge_system}\n\n"
            f"SKILL INSTRUCTIONS:\n{body[:6000]}\n\n"
            f"TASK INPUT:\n{task_input}\n\n"
            f"AGENT OUTPUT (may be truncated):\n{output_text[:5000]}"
        )

        _judge_calls[0] += 1
        try:
            proc = _sp.run(
                ["claude", "-p", prompt, "--model", "sonnet", "--effort", "medium",
                 "--output-format", "json", "--permission-mode", "default"],
                capture_output=True, text=True, timeout=120,
            )
            if proc.returncode != 0:
                return ScoreWithFeedback(score=0.3, feedback=f"Judge call failed: {proc.stderr[:100]}")

            data = json.loads(proc.stdout)
            result_text = data.get("result", "")

            # Strip markdown fences
            result_text = result_text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1] if "\n" in result_text else result_text[3:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                result_text = result_text.strip()
            if result_text.startswith("json"):
                result_text = result_text[4:].strip()

            # Parse JSON -- try direct first, then search
            scores = None
            try:
                scores = json.loads(result_text)
            except json.JSONDecodeError:
                for m in _re_local.finditer(r'\{[^{}]*"correctness"[^{}]*\}', result_text):
                    try:
                        scores = json.loads(m.group())
                        break
                    except json.JSONDecodeError:
                        continue

            if not scores:
                return ScoreWithFeedback(score=0.3, feedback=f"Judge parse failed: {result_text[:100]}")

            c = max(0, min(10, int(scores.get("correctness", 5)))) / 10
            p = max(0, min(10, int(scores.get("procedure_following", 5)))) / 10
            co = max(0, min(10, int(scores.get("conciseness", 5)))) / 10
            composite = 0.5 * c + 0.3 * p + 0.2 * co

            feedback = scores.get("feedback", "")
            if expected_signal == "negative":
                feedback += " (historically negative example)"

            return ScoreWithFeedback(score=round(composite, 3), feedback=feedback)

        except (_sp.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            return ScoreWithFeedback(score=0.3, feedback=f"Judge error: {str(e)[:100]}")

    # --- Convert eval data to DSPy Examples ---

    train_examples = []
    val_examples = []
    for i, ex in enumerate(examples_raw):
        dspy_ex = dspy.Example(
            task_input=ex.get("task_input", "")[:3000],
            agent_output=ex.get("agent_output", "")[:5000],
            signal=ex.get("signal", "ambiguous"),
        ).with_inputs("task_input")

        # 60/40 train/val split
        if i % 5 < 3:
            train_examples.append(dspy_ex)
        else:
            val_examples.append(dspy_ex)

    if not train_examples:
        return {"error": "no training examples"}

    print(f"Train: {len(train_examples)}, Val: {len(val_examples)}", file=sys.stderr)

    # --- Run optimizer ---

    baseline_module = SkillModule()
    print(f"Running {optimizer} optimizer ({iterations} iterations)...", file=sys.stderr)

    try:
        if optimizer == "gepa":
            # GEPA requires a reflection LM for trace analysis and instruction proposals
            reflection_lm = dspy.LM(
                model,
                api_key=api_key,
                api_base="https://openrouter.ai/api/v1",
                max_tokens=8000,
                temperature=1.0,
            )
            opt = dspy.GEPA(
                metric=skill_fitness,
                max_full_evals=iterations,
                reflection_lm=reflection_lm,
            )
            optimized = opt.compile(
                baseline_module,
                trainset=train_examples,
                valset=val_examples if val_examples else None,
            )
        elif optimizer == "mipro":
            opt = dspy.MIPROv2(
                metric=skill_fitness,
                auto="light",
            )
            optimized = opt.compile(
                baseline_module,
                trainset=train_examples,
            )
        elif optimizer == "bootstrap":
            opt = dspy.BootstrapFewShot(
                metric=skill_fitness,
                max_bootstrapped_demos=3,
            )
            optimized = opt.compile(
                baseline_module,
                trainset=train_examples,
            )
        else:
            print(f"Error: unknown optimizer '{optimizer}'", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Optimizer failed: {e}", file=sys.stderr)
        # Fallback to MIPROv2 if GEPA fails
        if optimizer == "gepa":
            print("Falling back to MIPROv2...", file=sys.stderr)
            try:
                opt = dspy.MIPROv2(metric=skill_fitness, auto="light")
                optimized = opt.compile(baseline_module, trainset=train_examples)
            except Exception as e2:
                return {"error": f"Both GEPA and MIPROv2 failed: {e}; {e2}"}
        else:
            return {"error": str(e)}

    if fitness == "llm-judge":
        print(f"  LLM judge calls: {_judge_calls[0]}", file=sys.stderr)

    # --- Extract evolved skill text ---

    # DSPy optimizers modify the predictor state:
    # - GEPA/MIPROv2: rewrite signature.instructions (the prompt text)
    # - BootstrapFewShot: add demos (few-shot examples from successful traces)
    # The actual predictor is at optimized.predictor.predict (ChainOfThought wraps Predict)
    evolved_body = body  # default: unchanged
    try:
        # Navigate to the inner Predict module
        for name, pred in optimized.named_predictors():
            state = pred.dump_state()
            sig = state.get("signature", {})

            # Check if instructions were rewritten (GEPA/MIPROv2)
            # The original instructions are the skill body text we set as __doc__
            new_instructions = sig.get("instructions", "")
            if new_instructions and new_instructions.strip() != body.strip():
                evolved_body = new_instructions
                print(f"  Extracted evolved instructions from {name}", file=sys.stderr)

            # Check for demos (BootstrapFewShot)
            demos = state.get("demos", [])
            if demos:
                demo_text = "\n\n## Examples from successful traces\n\n"
                for demo in demos[:2]:  # cap at 2 to control growth
                    task = demo.get("task_input", demo.get("inp", ""))
                    output = demo.get("output", demo.get("out", ""))
                    if task and output:
                        demo_text += f"**Task:** {task[:300]}\n**Output:** {output[:500]}\n\n"
                if len(demo_text) > 50:
                    evolved_body = body + demo_text
                    print(f"  Appended {len(demos)} demos from {name}", file=sys.stderr)
    except Exception as e:
        print(f"Warning: could not extract evolved text: {e}", file=sys.stderr)

    # --- Constraint checks ---

    growth = ((len(evolved_body) - baseline_body_len) / baseline_body_len * 100) if baseline_body_len else 0
    constraints = {
        "size_ok": len(evolved_body) <= 15000,
        "growth_ok": growth <= max_growth_pct,
        "non_empty": len(evolved_body.strip()) > 0,
        "has_content": len(evolved_body) >= 100,
    }
    all_pass = all(constraints.values())

    if not all_pass:
        print(f"Warning: constraints violated: {constraints}", file=sys.stderr)
        if not constraints["growth_ok"]:
            print(f"  Growth: {growth:.1f}% (max {max_growth_pct}%)", file=sys.stderr)

    # --- Reassemble and diff ---

    evolved_skill = _reassemble_skill(frontmatter, evolved_body)
    diff = _make_diff(skill_text, evolved_skill, skill_name)
    changed = evolved_body != body

    return {
        "skill": skill_name,
        "optimizer": optimizer,
        "model": model,
        "changed": changed,
        "baseline_chars": baseline_body_len,
        "evolved_chars": len(evolved_body),
        "growth_pct": round(growth, 1),
        "constraints": constraints,
        "constraints_pass": all_pass,
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "diff": diff if changed else "(no changes)",
        "evolved_text": evolved_skill if changed else None,
    }
