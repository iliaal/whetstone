# review and delivery

**Two-stage review gate on subagent outputs.** Verify spec compliance first: does the output match what was requested? Only then evaluate quality. Structure review as two explicit passes: pass 1 rejects on spec mismatch without reading further, pass 2 assesses correctness and quality on spec-compliant outputs.

**Compare an external reference against its class list, not its instances.** Asking "is this exact string already in ours?" returns no whenever the two sources encode the same classes in different vocabularies. Extract the reference's taxonomy and diff that against yours; a source whose content is worthless can still be a valid coverage checklist.

**Split recall from precision across agents, and keep precision context out of the finder.** Handing a discovery agent mitigating context (the validating caller, the guard one layer up, a prior "this is fine" verdict) trains it to self-censor, and a dropped candidate is unrecoverable. Give the finder the target and the discovery queries only, let it over-produce, then route every candidate to a separate verifier that starts from "assume this is wrong" and has the tool access to fetch the caller itself.

### Delivery and credit discipline

Keep open implementation units tied to runnable capability; a coordination or validation unit must name the capability it gates. Make closable units vertical: implementation and its tests ship together, and a stub that merely type-checks is not delivered capability. Only the role holding closure authority closes shared work. After each wave, compare runnable units delivered against coordination, review, and governance rounds consumed: orchestration activity growing while the deliverable count stays flat means freeze the machinery and redirect the next wave to the deliverable. Full rules: [orchestration-patterns.md](./orchestration-patterns.md) (Delivery and credit discipline).

**QA retry loop.** Five fix rounds maximum per task: rounds 1-3 resume the same implementer with structured feedback ([QA FAIL template](./handoff-templates.md)); rounds 4-5 hand off to a fresh implementer on a stronger model carrying the full finding history. At the cap, every still-open finding takes a forced disposition (fixed now, recorded in the plan or ledger with a named owner, or parked with a stated reason), never a silent drop. A finding that oscillates rather than narrows after its second attempt escalates to stop-and-ask instead of a third mechanical patch. A blocked task does not halt the pipeline; continue and let final integration catch the rest. Counter resets when advancing to the next task. Round mechanics: [wave-contract.md](./wave-contract.md).

---
