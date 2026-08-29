---
name: ia-meta-prompting
class: meta
description: >-
  Structured decision modifiers (/think, /verify, /adversarial, /edge,
  /confidence, /assumptions, etc.) to stress-test conclusions, evidence,
  assumptions, alternatives, and edge cases. Use when validating an important
  design, architecture decision, or ambiguous plan before committing.
---

# Meta-Prompting

Stress-test decisions via `/commands` or natural language. Commands combine
left-to-right: `/verify /adversarial`. Auto-trigger when context warrants and
note which pattern applied. Output a decision record with the conclusion,
decisive evidence, alternatives, uncertainty, and the applicable marker (e.g.,
`VERIFIED ANSWER:`, `REVISED ANSWER:`, confidence tier).

## Patterns

**`/think`** | `/show` -- Present a concise decision record: conclusion,
decisive evidence, alternatives considered, rejection reasons, and material
uncertainty. With `/think doubt`, state what evidence could overturn each
material conclusion.

**`/adversarial`** | `/argue` -- After answering, steelman the opposing case. 3 strongest counterarguments ranked by severity. Identify blind spots and unstated assumptions.

**`/constrain`** | `/strict` -- Tight constraints: 3 sentences max, cite sources, no hedging. Override inline: `/constrain 5 sentences`.

**`/json`** | `/format` -- Respond in valid JSON code block, no surrounding prose unless asked. Default schema:
```json
{"analysis": "string", "confidence_score": 85, "methodology": "string", "limitations": ["string"]}
```
Custom keys: `/json {keys: summary, risks, recommendation}`

**`/budget`** | `/deep` -- Extended decision record (~500 words) covering
evidence, the strongest counterargument, alternatives, trade-offs, and
uncertainty, followed by a clearly separated final answer.

**`/compare`** | `/vs` -- Compare options as table. Default dimensions: speed, accuracy, cost, complexity, maintenance. Custom: `/compare [dim1, dim2]`.

**`/confidence`** | `/conf` -- Rate each claim 0-100. Flag below 70 as SPECULATIVE. Group by tier: HIGH (85+), MEDIUM (70-84), LOW (<70). Include assumptions made and rate each 1-10 on confidence.

**`/edge`** | `/break` -- 5+ inputs/scenarios that break the approach. Code: null/empty, concurrency, overflow, encoding, auth bypass. Strategies: market conditions, timing, dependencies.
*Auto-triggers on: security, validation, parsing contexts.*

**`/verify-think`** | `/check` -- Three phases: (1) **Answer** direct response, (2) **Challenge** 3 ways it could be wrong, (3) **Verify** investigate each, update if needed. Mark final as `VERIFIED ANSWER:` or `REVISED ANSWER:`. Distinct from the `/ia-verify` slash command, which runs the full pre-PR verification pipeline.
*Auto-triggers on: architecture decisions, critical choices, "Am I right?"*

**`/flip`** | `/alt` -- Identify the approach you'd take by default and state it. Then propose an alternative that uses a different mechanism (different data structure, different layer, different abstraction). State the conditions under which the alternative beats the default. Override: `/flip 3` for top 3 alternatives.
*Auto-triggers on: architecture decisions where the "easy" answer may break at scale.*

**`/assumptions`** | `/presume` -- Before answering, list every implicit assumption in the question/task. Then answer with assumptions explicit. The assumption list is often more valuable than the answer.
*Auto-triggers on: architecture reviews, ambiguous requirements.*

**`/premortem`** | `/postmortem` -- Assume the decision/project has already failed. Work backwards: what caused the failure? List 3-5 failure modes by likelihood. Focus on systemic risks, not edge cases.

**`/blindspot`** | `/unknowns` -- For unfamiliar territory (new codebase area, new domain, unfamiliar craft). Surface the *user's* unknown unknowns: what they'd need to know to prompt well but don't know to ask. Search the codebase/docs first, then report (1) the questions they should be asking, (2) prior art, conventions, and landmines in this area, (3) what "good" looks like here. Goal is to *teach enough to prompt better*, not to solve the task. Distinct from `/adversarial` (attacks a proposed answer) and `/premortem` (assumes the plan failed) -- this runs *before* an answer exists, aimed at the user's knowledge gaps, not the solution's.
*Auto-triggers on: "I know nothing about X", "blindspot pass", "unknown unknowns", entering an unfamiliar area.*

**`/tensions`** | `/perspectives` -- Answer from two named opposing perspectives (e.g., security engineer vs. shipping PM). Focus output on where they *disagree* -- that's where the real insight lives. Override roles: `/tensions [devops, security]`.

## Combos

**`/analyze`** = `/think` + `/edge` + `/verify-think` -- Code reviews, architecture, security-sensitive work. Synthesize findings into a unified recommendation -- don't just concatenate pattern outputs.
*Auto-triggers on: code review requests.*

**`/trade`** = `/confidence` + `/adversarial` + `/edge` -- Trade ideas, position analysis, market thesis.
*Auto-triggers on: trade/position discussions.*

## Conventions

- Separate combined pattern outputs with `---`
- Keep core answer prominent -- patterns enhance, not bury the response
- Present decision-relevant rationale and evidence. Do not narrate private
  step-by-step reasoning or dead ends.
- Accept new pattern definitions mid-conversation ("Add `/eli5` for explain like I'm 5") -- apply for the session

## Verify

- Pattern marker present in output (e.g., `VERIFIED ANSWER:` for /verify)
- Core answer appears before any pattern-output separator (`---`)
- Decision records distinguish observed evidence, inference, assumptions, and
  uncertainty
