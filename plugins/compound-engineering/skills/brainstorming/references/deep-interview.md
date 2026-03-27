# Deep Interview Layer

Apply the deep interview protocol on top of the baseline questions above. Assumption probing and contradiction tracking always run. Research-backed challenges and second-order effects run when the scope warrants it (multi-system changes, infrastructure decisions, technology selection).

**Assumption probing:** After each substantive answer, identify what the user assumed but didn't state. "You described X -- are you assuming Y is already in place?" Surface hidden dependencies and unstated constraints.

**Second-order effects:** For features that touch shared infrastructure or data models, ask what success creates downstream. "If this works and gets adopted, what pressure does it put on [related system]?"

**Research-backed challenges:** Fire background research on technology choices and claims. When findings contradict, challenge directly with citation. When findings support, briefly confirm to build confidence in the decision.

**Contradiction tracking:** If the user's answer contradicts something said earlier, flag it immediately: "Earlier you said X, but this implies Y. Which takes priority?"

**Anti-requirements:** When the user rejects an approach or says "definitely not X," capture the rejection and rationale inline with the related decision. Don't force this -- capture organically when it surfaces.

**Question clustering:** When probing a single dimension (e.g., data model, auth flow), ask 2-3 related questions together using AskUserQuestion's multi-question support. Switch to one-at-a-time when jumping between dimensions.

**Completeness assessment:** Track which dimensions have been explored. Before proposing to move to Phase 2, assess coverage and signal confidence: "We've covered purpose, users, and constraints well. Data flow and failure modes are still thin -- want to explore those, or proceed?"
