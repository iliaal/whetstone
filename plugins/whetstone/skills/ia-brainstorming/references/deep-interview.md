# Deep Interview Layer

Apply the deep interview protocol on top of the baseline questions above. Assumption probing and contradiction tracking always run. Research-backed challenges and second-order effects run when the scope warrants it (multi-system changes, infrastructure decisions, technology selection).

**Assumption probing:** After each substantive answer, identify what the user assumed but didn't state. "You described X -- are you assuming Y is already in place?" Surface hidden dependencies and unstated constraints.

**Second-order effects:** For features that touch shared infrastructure or data models, ask what success creates downstream. "If this works and gets adopted, what pressure does it put on [related system]?"

**Research-backed challenges:** Fire background research on technology choices and claims. When findings contradict, challenge directly with citation. When findings support, briefly confirm to build confidence in the decision.

**Contradiction tracking:** If the user's answer contradicts something said earlier, flag it immediately: "Earlier you said X, but this implies Y. Which takes priority?"

**Anti-requirements:** When the user rejects an approach or says "definitely not X," capture the rejection and rationale inline with the related decision. Don't force this -- capture organically when it surfaces.

**Question clustering:** When probing a single dimension (e.g., data model, auth flow), ask 2-3 related questions together using AskUserQuestion's multi-question support. Switch to one-at-a-time when jumping between dimensions.

**Completeness assessment:** Track which dimensions have been explored. Before proposing to move to Phase 2, assess coverage and signal confidence: "We've covered purpose, users, and constraints well. Data flow and failure modes are still thin -- want to explore those, or proceed?"

## Rigor Probes for Ambiguous Gaps

When a user answer leaves a gap on evidence, specificity, counterfactual, or attachment, fire ONE open-ended probe per gap — *not* a multiple-choice menu. Menus signal which axes the agent thinks matter, biasing the user toward those axes; open-ended forces actual observation:

- **Evidence:** "What's the most concrete thing someone's already done about this — paid for it, built a workaround, quit a tool over it?"
- **Specificity:** "Can you name a team you've actually watched hit this, or are you reasoning?"
- **Counterfactual:** "What do teams do today when this breaks — who reconciles?"
- **Attachment:** "What's the smallest version that would still prove the bet right, and what's excluded?"

Interleave with narrowing moves; do not stack multiple probes in one turn.

## Integration Check Before Phase 1 Exit

Before exiting Phase 1, mentally combine what the user has stated so far. If stated-A + stated-B + agent-default-C produces a downstream effect the user is unlikely to have tracked (e.g., "if mute lives on the rule AND we don't warn on delete, rule-delete silently loses pause state"), fire one open probe per genuine combination. Phase 2.5's call-outs are a safety net for residuals — *not* a punt list for consequences you should have surfaced here.
