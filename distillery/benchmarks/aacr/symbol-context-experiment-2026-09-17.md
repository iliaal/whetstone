# Changed-symbol context experiment, 2026-09-17

**VERIFIED ANSWER:** changed-symbol context had mixed results in 20 real Sol/high reviews. Supported discoveries fell from six to four in Flow B-style review and rose from three to five under OCR delegated criteria. Context added one refuted Flow B claim and increased input tokens by 11.9–13.1%. Every supported defect found with context was also found by diff-only Flow B.

The strongest counterargument is that these are single stochastic passes on five exploratory cases, with a conservative selector that resolves few changed-line calls. OCR's two additional discoveries are real observations, both from Cline; all supported findings come from just two cases. The experiment does not establish a general quality ranking or prove that context caused either improvement or regression.

Keep the existing default. Retain the corrected [standalone selector](./README.md#build-experimental-symbol-context) as an explicit experiment, without automatically attaching it to dual-review or replacing Flow B with OCR. Before another review matrix, require a retrieval mechanism to resolve the known receiver-dependent development miss. Another batch of arbitrary packets would leave that mechanism untested.

## Review outcomes

All 20 evaluated reviews completed with unique native execution identities, Sol/high configuration, valid output, and full declared file coverage. Two earlier launches failed before model execution and received the documented infrastructure retries below. No valid result was rerun. Four fresh Sol/high adjudicators checked 31 pooled claim texts with workflow and arm identities hidden; vLLM produced no claims to adjudicate. The parent checked decisive source evidence and library probes. No adjudications remain unresolved.

| Workflow | Input | Supported defect groups | Refuted groups | Non-actionable groups |
|---|---|---:|---:|---:|
| Flow B-style | Diff only | 6 | 1 | 1 |
| Flow B-style | Diff + context | 4 | 2 | 1 |
| OCR delegated criteria | Diff only | 3 | 1 | 2 |
| OCR delegated criteria | Diff + context | 5 | 1 | 3 |

Counts are deduplicated within each case and condition. Refuted means the claimed defect does not hold up against source or the supported contract. Non-actionable means a real observation lacks demonstrated functional harm or a reachable production trigger. Svelte's two unused JSDoc imports form one cleanup group; counting them separately would raise OCR/context's non-actionable count from three to four without changing the decision. No whole-review recall, clean-review accuracy, or population precision is claimed.

Flow B's context pass missed two defects found by its diff-only pass: Cline's byte-order-mark loss and Immich's loss of album date-range precision. OCR's context pass added Cline's byte-order-mark loss and read-before-size-check defect. OCR also added the unused JSDoc observations. Neither workflow's context pass found a defect beyond diff-only Flow B's six-group inventory.

The four supported Cline defects concern ASCII re-encoding that replaces new Unicode characters, binary bytes accepted as text, allocating a whole file before enforcing the 300 KiB limit, and removing byte-order marks during the new post-save rewrite. The [encoding rewrite](https://github.com/cline/cline/blob/7d18fb9df620c61420c6939df22fb6f7af836bb2/src/integrations/editor/DiffViewProvider.ts#L234) and [extraction branch](https://github.com/cline/cline/blob/7d18fb9df620c61420c6939df22fb6f7af836bb2/src/integrations/misc/extract-text.ts#L25) establish the changed paths. Isolated jschardet 3.1.4, isbinaryfile 5.0.2, and iconv-lite 0.6.3 probes confirmed ASCII detection, binary misclassification, character replacement, and BOM removal. The head declares jschardet `^3.1.4` without a matching lockfile entry; the probe tests an allowed version, not a reproduced locked installation. The VS Code save flow was traced, not run end to end.

Immich's [new date casts](https://github.com/immich-app/immich/blob/966c3f22d034c230a14bb21b02627ef6d00eec68/server/src/repositories/album.repository.ts#L141) lose time-of-day precision in two independently used values: album range boundaries used for sorting, and the asset-modification marker used by mobile synchronization. Same-day changes can collapse to equal values. These verdicts use the pinned query, API, and consumer source; no database or app runtime test was run.

All four conditions claimed that RAGFlow loses node keywords, but its entity nodes do not use that field; keyword merging belongs to edges. All four also noted serial edge deletion. That loop is serial, but the inspected production producer fails earlier on an unchanged `set.extend` call, before populating removed edges; the alleged production latency regression is unestablished. Flow B/context additionally claimed a Svelte compiler/runtime compatibility break. Mixing the old compiler's boolean with the new runtime's tuple parameter does throw, but [Svelte's project guidance](https://github.com/sveltejs/svelte/discussions/14573) requires matching compiler/runtime versions, and the pinned compiler marks the internal runtime private. Confirming an exception was insufficient to establish a supported-use defect.

## Reviewer cost

Each context condition added 9,922 input tokens over its five paired controls. Times are summed per-review elapsed seconds, not concurrent wall time. Cache hits and output lengths differed, and each cell ran once; the lower observed time with context is not evidence of a reliable latency improvement. Currency cost under the existing subscription is unknown.

| Workflow / input | Input tokens | Output tokens | Cached input tokens | Review seconds |
|---|---:|---:|---:|---:|
| Flow B / diff only | 75,834 | 12,471 | 8,448 | 365.0 |
| Flow B / context | 85,756 | 11,634 | 17,024 | 322.6 |
| OCR / diff only | 83,506 | 10,016 | 8,576 | 312.0 |
| OCR / context | 93,428 | 10,967 | 8,448 | 302.8 |

## Retrieval result

The standalone [symbol context selector](./symbol_context.py) builds source-verified packets from CodeSage 0.33.1 structural indexes without embeddings. It prioritizes calls on changed lines, then changed enclosing symbols, then other calls within those symbols. Each priority balances selected files; whole numbered spans must fit within 7,000 UTF-8 bytes. Definitions are name-based candidates reached through local imports/includes, at most three edges away. Ambiguous targets and untyped receivers remain unresolved.

The known n8n development miss remains unresolved. `api.users.create()` needs receiver-type resolution; the selector records `untyped-receiver` and does not retrieve `user-api-helper.ts`. This experiment therefore tests a conservative changed-symbol policy, not a demonstrated solution to that missing contract. The original five PRs are retired from confirmatory use because their earlier outcomes informed the policy.

Fresh structural indexing of the five new repositories took 22.7 seconds in summed index-command time. Packet generation took another 0.85 seconds. These figures exclude repository downloads and case preparation. The previous experiment's roughly 51-minute indexing total used different repositories and semantic embeddings, so it is not a controlled speed comparison.

| Case | Selected review files | Index seconds | Packet bytes | Selected spans | Budget omissions |
|---|---:|---:|---:|---:|---:|
| Cline #2347 | 2 | 0.92 | 6,487 | 6 | 9 |
| Immich #17124 | 2 | 3.44 | 5,700 | 5 | 0 |
| Svelte #15250 | 4 | 3.65 | 6,583 | 5 | 14 |
| RAGFlow #6691 | 3 | 2.75 | 6,685 | 3 | 9 |
| vLLM #24425 | 1 | 11.92 | 5,538 | 3 | 1 |

The 22 spans comprise one changed-line call candidate, 12 changed symbols, and nine enclosing-symbol call candidates. Five spans come from files outside the selected review paths, across Cline, Svelte, and vLLM. Name matching and dependency reachability do not prove an import binding or runtime target. All five indexes are fresh with zero failed files, but CodeSage reported parser errors in 16/8/7/1/138 files respectively; freshness does not establish complete graph extraction.

## Selection and reference quality

An independent curator ordered 200 AACR PR records by a fixed hash seed, using metadata, supported stack, source availability, and resource limits before reading annotation text. The first complete pass admitted only Cline and Immich. A documented second tier relaxed source-file, changed-path, and diff-size limits before selecting Svelte, RAGFlow, and vLLM. Cases and scopes remained fixed after annotation inspection. This is an exploratory sample with a resource-driven selection amendment.

The 15 selected AACR `Code Defect` comments contain no source-verified actionable correctness positive: 14 claims do not hold up as introduced defects at the pinned head, and one vLLM claim describes repeated exception text without demonstrated functional impact. Immich has no positive comment in that category. RAGFlow's alleged `.nodes` error describes code removed by the patch; Svelte's alleged malformed hydration marker parses as intended. The original annotations remain preserved. No PR is established as clean, and selected-defect recall would be meaningless for this cohort.

Matching labels after blind adjudication exposed the opposite error too: AACR marks Immich's asset-modification precision claim as negative comment index 2. All four reviews reported it, and the pinned mobile synchronization caller substantiates its impact. Treating every negative annotation as a false positive would therefore penalize a valid finding in every condition. The original label remains unchanged as provenance; source-based adjudication controls this report's counts.

## Paired execution and deviations

The fixed matrix contains five cases, two workflows, and two inputs: 20 reviews using `gpt-5.6-sol` with reasoning effort `high`. The workflows are supplied-input Flow B-style discovery and OCR delegated criteria. Reviewers receive the same source identity, selected diff, scope, prompt, and configuration within each pair; only `frozen_context` changes. Both workflows use the same packet for a case. Actors have no repository tools, labels, curation notes, previous outputs, or other-arm results. This does not exercise production Flow B or OCR's interactive source exploration.

The selector developer used synthetic fixtures and the retired development cases. An auditor crossed that boundary by running a provisional selector on the new source inputs before code freeze, inspecting aggregate counts and selected path/rank/origin tuples. It read no new labels or review results and stopped when instructed. A generic priority-order bug had been identified before that access and was reproduced synthetically before correction. The selector developer received no new-case identities or output. Nevertheless, retrieval exposure prevents treating these cases as an untouched confirmatory holdout.

All final packets and requests were frozen and independently checked before model execution. Order uses seed `20260918`, at most two concurrent actors, and a 600-second native backend deadline. Two initial launches failed before any model ran because the copied native manifest gained a trailing newline and no longer matched its helper-issued byte hash. The correction restored the exact helper-issued manifest; each failed cell received one fresh retry with an unchanged review payload. Original failed requests, stderr, plan, and manifest remain retained.

## Decision stress test

Confidence is high in the retained execution counts, byte comparisons, and these source-based judgments; confidence in generalization is low. Selection limits changed, one auditor saw preliminary retrieval metadata, public training exposure is unknown, and fresh contexts provide no model-family diversity. The source-verified AACR annotations were incomplete: the six supported groups above emerged from reviewer claims rather than that selected positive inventory.

The premortem predicted unresolved receivers, oversized symbols consuming the budget, and source excerpts encouraging unsupported assumptions. The first two occurred mechanically; unsupported and non-actionable claims occurred in the reviews, without enough replication to establish causation. Cheap structural indexing solves setup cost but does not establish useful contract retrieval.

The next-best alternative is unchanged diff-only discovery followed by targeted verification of concrete contracts. Reconsider automatic context only after receiver/import resolution retrieves relevant contracts in development, then repeated paired reviews on independently selected, fully adjudicated defective and clean scopes improve supported discoveries without unacceptable noise or cost. The current five cases are now evaluation-exposed; do not tune against them and call a later run confirmatory. Production prompts, defaults, and quality gates remain unchanged.

## Versions and verification

OCR is v1.12.5 at `189be5b024d3309dd10fdc8cd8ee31b2530c210b`, matching upstream HEAD when rechecked on 2026-09-17. AACR is pinned to `68a569759289a83654a59d06db2a72910edf0a4a`. The native actor uses Codex 0.154.0. No API credentials were added. The shared OCR reference checkout remains older; the experiment uses the separate current checkout.

The selector verifies prepared base/head bytes, the structural-index revision, full source blobs, and exact span hashes. Thirty-three preparation and selector tests pass, including a real synthetic three-edge Python import chain, ambiguous candidates, budget ordering, provenance refusal, and parser call shapes. Ruff passes. Native AACR import and all five actual OCR delegate previews pass; each treatment preview differs only in background. OCR's Git-version and recommended-background-length warnings remain as in the prior experiment. The upstream projects' full suites were not run.

An independent utility audit during the frozen review runs found two generic bugs: deduplicating call names before checking receivers could suppress a later valid call, and Unicode `splitlines()` could disagree with CodeSage's LF-based source rows. The corrected standalone utility preserves distinct call sites, uses LF consistently, and refuses ambiguous bare CR. New synthetic regressions and independent verification cover both fixes. None of the evaluated source files contained the problematic Unicode separators. A fresh mechanical comparison found identical selected metadata and source bodies across all five cases after correction; only omission-count summaries changed. No valid reviewer was rerun, and these review outcomes remain bound to the original complete packets.

The evaluated selector is retained locally as `frozen-selector-v1.py`, SHA256 `cf3cb9e64265e1c5db94d478a5edc840204bc26dfc8f745f70ff49690e1da8dd`. The corrected utility's SHA256 is `f9858e495122f3e29c435d5c15c08e347a499c01664d9708435c724397d4a7e0`. The corrected packets have been exercised mechanically, not scored through another model comparison.

Local evidence lives under `distillery/.eval-data/aacr-symbol-context-experiment-20260917/`: selection history, pinned sources, reference checks, indexing logs, development and new packets, preregistration, native/OCR preparation, requests, and execution records. These ignored artifacts are retained locally and are not a redistributed source bundle.

| Artifact | SHA256 |
|---|---|
| `results.json` | `e419832065956ea93a6345ab8af8133d6b1ad0a86fb7f28bc65f3a3cbe3ecb18` |
| `run-plan.json` | `74df54c46ce4596f28e15ac6ddfff8d761421a65f2846fe7166ef9ed01561a95` |
| `contexts/manifest.json` | `397c92dba646065a22c4c294cc4b793c5ab558910896db9406e0b3dc90b75f4b` |
| `ocr/manifest.json` | `3a9d7662f52f484dc6aaa27c65272860e68bcbc59dbff34cec70028d08db0367` |
