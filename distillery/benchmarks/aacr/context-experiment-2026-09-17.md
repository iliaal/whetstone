# Frozen context experiment, 2026-09-17

**VERIFIED ANSWER:** the tested CodeSage context recipe produced no additional verified defects in either review workflow. All four conditions found the same four of five selected AACR defects. Context increased input tokens by 10.8–11.8% and summed reviewer time by 24.9–26.5% in these runs.

The strongest counterargument is that this was a narrow retrieval policy: one query built from file paths, three primary results, a 7,000-byte packet, and reviewers restricted to supplied inputs. It missed the dependency needed for the one consistently missed defect. This result cannot establish that CodeSage retrieval generally fails or that OCR's interactive delegate workflow adds no value.

Keep the existing diff-only default. Retain OCR as a reference and optional tool; this experiment does not support substituting it for dual-review's independent Flow B or automatically attaching these packets. The next useful experiment would select context from changed symbols and their contracts, then test on independently selected cases. Do not repeat this exact path-only recipe at larger scale first.

## Observed review results

Twenty real subscription-backed Codex executions used `gpt-5.6-sol` with reasoning effort `high`. Every execution completed with valid output, a unique native execution identity, and full declared file coverage. There were no retries or unresolved adjudications.

| Workflow | Input | Selected defects detected | Distinct supported defects | False positives |
|---|---|---:|---:|---:|
| Flow B-style discovery | Diff only | 4/5 | 6 | 0 |
| Flow B-style discovery | Diff + context | 4/5 | 6 | 0 |
| OCR delegated criteria | Diff only | 4/5 | 5 | 1 |
| OCR delegated criteria | Diff + context | 4/5 | 5 | 1 |

Counts are deduplicated within each case and condition. The Flow B-style reviews each produced five findings containing six independently actionable defects: one browser-use finding covered both nullable and out-of-range ports. Counting that validation finding as one issue instead would reduce both Flow B totals to five and leave the paired conclusion unchanged. These single passes do not establish a general quality ranking between workflows.

Every condition detected the selected Valkey formatting defect, SDL null dereference, browser-use nullable-port failure, and ComfyUI causal-mask initialization defect. Every condition also found an SDL cleanup defect outside the selected positive inventory: non-presenting submissions skip command-buffer cleanup, empty-allocation reclamation, and deferred destruction. Both Flow B-style conditions additionally identified the unconstrained integer-port range. No condition repeated any of the five selected negative claims.

OCR's two false positives were different. Diff-only alleged that `asyncio.create_subprocess_exec(..., shell=False)` fails through a duplicate argument; an isolated Python 3.11 probe launched successfully. Context alleged that n8n's unscoped transfer locator matches multiple user-row actions; the actual action list contains no transfer action. Context removed one unsupported claim and introduced another, leaving its total unchanged. This is an observed exchange, not evidence of a repeatable correction mechanism.

## The missed contract

All four reviews missed n8n's default-user assertion. The [new test](https://github.com/n8n-io/n8n/blob/ebe680fbcacd9210aa219ab01d98012ac1d6faae/packages/testing/playwright/tests/ui/user-service.spec.ts#L4) calls `api.users.create()` without overrides and requires `lastName` to equal `User`. The [helper](https://github.com/n8n-io/n8n/blob/ebe680fbcacd9210aa219ab01d98012ac1d6faae/packages/testing/playwright/services/user-api-helper.ts#L26) appends an eight-character suffix and returns that value unchanged.

The frozen n8n packet included parts of `SettingsUsersPage.ts`, unrelated portions of `39-projects.spec.ts`, and imports from `n8nPage.ts`. Neither the packet nor the raw export included `user-api-helper.ts`, `lastName`, or `nanoid`. All selected review files were indexed, so this miss concerns retrieval selection rather than an absent test index. Source-anchored retrieval of the changed call's implementation is the next mechanism worth testing; a larger arbitrary context cap alone would not recover this absent helper.

## Measured cost

Token and time totals below cover five reviewer executions per row, including native wrapper overhead. Time is the sum of per-review elapsed time, not concurrent wall time or a latency forecast. Each context condition added exactly 9,094 input tokens over its paired baseline.

| Workflow / input | Input tokens | Output tokens | Cached input tokens | Review seconds |
|---|---:|---:|---:|---:|
| Flow B / diff only | 77,348 | 5,576 | 8,448 | 150.4 |
| Flow B / context | 86,442 | 5,663 | 8,448 | 187.9 |
| OCR / diff only | 84,061 | 4,622 | 0 | 131.4 |
| OCR / context | 93,155 | 5,227 | 8,448 | 166.1 |

These are API-reported token counts. Cache hits differed across conditions, and each cell ran only once, so timing and billing extrapolations would be unreliable. Currency cost is unknown under the existing subscription.

Fresh indexing took 3,057.4 seconds in total, about 51 minutes; the five queries took another 35.5 seconds. This is setup cost for fresh historical checkouts. It is not a measured recurring cost for an already indexed repository.

| Repository | Index seconds | Packet bytes | Included / omitted excerpts |
|---|---:|---:|---:|
| Valkey | 170.1 | 6,506 | 4 / 2 |
| SDL | 733.4 | 3,958 | 3 / 0 |
| n8n | 1,967.4 | 6,259 | 4 / 2 |
| browser-use | 17.9 | 6,636 | 5 / 1 |
| ComfyUI | 168.7 | 5,136 | 3 / 3 |

## Scope and verification

The five [prepared cases](./README.md) retain their pinned merge bases, heads, and selected file scopes: 1/1/3/1/1 files. Both arms within each workflow share the diff, instructions, review plan, configuration, and scope. Only `frozen_context` differs. Both workflows receive the same packet for a given case. The exact diff appears in both the evidence-bound input bundle and the native diff artifact, identically across conditions.

All context was frozen before the first review. Each complete source repository received a fresh CodeSage 0.33.1 index with default embedding/reranking settings, built-in exclusions, and watching disabled. One path-derived query requested three primary results plus callers and callees. Packets preserved primary/related order and complete source spans within 7,000 UTF-8 bytes. Returned symbol-definition metadata remained in the raw exports and was not rendered. Full source lines replaced clipped chunk boundaries uniformly before any review ran.

All five indexes were fresh, every selected review path had structural and semantic coverage, and all packets included code outside the diff. Independent checks rehashed 45 preparation artifacts and verified all 19 included spans against exact Git objects. Indexing reported zero failed files, but parsing reported syntax errors in 317 Valkey, 527 SDL, and 27 n8n files; aggregate index freshness does not establish complete graph extraction.

Review order was shuffled with seed `20260917`; two isolated native actors ran concurrently at most. Review actors had no repository, tool, or label access. The Flow B condition used a supplied-input discovery prompt through dual-review's native baseline actor, not the full production Flow B workflow. OCR used its actual generated delegate rules and curated scope, but its usual interactive source exploration was disabled to preserve the comparison. OCR's native API agent loop was not tested.

Five fresh Sol/high adjudicators checked the pooled claims with workflow and arm identities hidden, then the parent independently checked decisive source evidence. Adjudication used separate contexts, not model-family diversity. Twenty-two claim texts reduced to six supported defect groups and two unsupported groups across the entire experiment. Matching to AACR's selected labels happened afterward. Source inspection and isolated compiler, socket, subprocess, and CPU tensor probes supported the judgments; the upstream applications, GPU failure paths, and DirectML runtime were not exercised. The tensor probe illustrated permitted mask contents, not an observed DirectML allocation.

Relevant additional evidence includes [SDL's guarded cleanup](https://github.com/libsdl-org/SDL/blob/96dfef35c4b0b89f2f8d9c2ecc4f5e3a25d3e7a0/src/gpu/vulkan/SDL_gpu_vulkan.c#L10532), [browser-use's port field](https://github.com/browser-use/browser-use/blob/0b21e50ca640581ecd46990475c8b223eaa05045/browser_use/browser/browser.py#L111), and [n8n's actual action list](https://github.com/n8n-io/n8n/blob/ebe680fbcacd9210aa219ab01d98012ac1d6faae/packages/frontend/editor-ui/src/views/SettingsUsersView.vue#L70). Some findings overstated secondary details: the Valkey trigger depends on unconsumed bytes and logging conditions; explicit remote browser endpoints bypass the local port; explicit SDL waits do not reclaim empty allocations; and a one-token sequence has no future-token mask entry. Those qualifications do not change the supported core defects or paired counts.

## Decision stress test

Confidence is high in the recorded outcomes and absence of incremental discoveries in these exact runs. Confidence in generalization is low: there are five publicly available, selectively scoped defective PRs, no clean-review population, one stochastic run per cell, incomplete benchmark labels, and unknown training exposure. Four selected defects were already detectable without additional context, leaving little measured headroom.

The premortem remains concrete: path similarity retrieves nearby code while missing the contract; broad context adds unsupported inference; cap omissions remove useful evidence; and an already capable model leaves little room for measured gains. The missing contract occurred here, and the OCR context condition produced an unsupported inference. A single run cannot establish that context caused that inference. No production defaults or quality gates were changed.

The next-best alternative is the unchanged diff-only reviewer with targeted investigation when a concrete contract needs verification. Reconsider automatic frozen context only after a changed-symbol retrieval policy demonstrably retrieves the needed contracts and repeated paired runs on independently selected, clean and defective cases improve supported discoveries without increasing false positives at an acceptable token/latency cost. These five PRs must leave any confirmatory holdout if their outcomes guide that policy's tuning.

## Versions and retained evidence

OCR was [v1.12.5](https://github.com/alibaba/open-code-review/releases/tag/v1.12.5), commit `189be5b024d3309dd10fdc8cd8ee31b2530c210b`, still upstream HEAD when rechecked after the runs on 2026-09-17. AACR used `68a569759289a83654a59d06db2a72910edf0a4a`, verified against upstream HEAD during preparation. The shared OCR reference checkout remains at v1.12.0; the experiment used the separate current checkout. OCR warned that installed Git 2.34.1 is below its supported 2.41.0 and that packets exceed its recommended 2,000 characters; all actual preparation commands succeeded within its hard 8,000-character limit.

The model runner used the official Codex 0.154.0 binary, with `gpt-5.6-sol` / `high` in every actor request and receipt. Its installed binary hash was verified against the npm package before refreshing the local backend trust digest. No new API credentials were configured.

Local evidence is retained under `distillery/.eval-data/aacr-context-experiment-20260917/`: preregistration, preparation/run/collection scripts, source and OCR manifests, frozen requests, native responses and receipts, blinded claims, adjudications, and `results.json`. This ignored directory is local evidence, not a published benchmark bundle.

| Artifact | SHA256 |
|---|---|
| `results.json` | `e47285d35f8112307318f30a60dea30b68842b2d05f1855742fbc12753243c97` |
| `run-plan.json` | `04a4eae81e3e58f4e2e9d35afe8257d50ba1d5f88bd4d3561e4b87d95f2c8407` |
| `contexts/manifest.json` | `29ee0734be9619de98db7463560b40ce66f1bb4394ce5fc47efd2570ad1d0ed7` |
| `ocr/manifest.json` | `e115cf17d58189e48378826a27b0dada630bb10d00edce1d3f7e5551eb266caf` |
