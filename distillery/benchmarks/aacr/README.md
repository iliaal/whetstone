# AACR review case preparation

Prepare source-checked review cases from [AACR-Bench](https://github.com/alibaba/aacr-bench) without running a model. The initial five cases are development diagnostics for Whetstone, CodeSage, and independent-review experiments. They were retired from confirmatory holdout use on 2026-09-17 because their observed results informed the changed-symbol context policy. They are not an exhaustive reference inventory or a reproduction of AACR's published scores.

The initial selection contains five PRs, five positive defect claims, and five rejected-claim negatives:

| Case | Language | Positive defect | Negative claims |
|---|---|---|---:|
| Valkey #1889 | C | Comma expressions break `snprintf` arguments | 0 |
| SDL #12718 | C | Texture dereference precedes its NULL guard | 1 |
| n8n #20210 | TypeScript | Default surname test contradicts its helper | 2 |
| browser-use #1482 | Python | An accepted nullable port reaches an integer-only socket argument | 2 |
| ComfyUI #6542 | Python | DirectML causal mask skips initialization | 0 |

The [2026-09-17 frozen-context experiment](./context-experiment-2026-09-17.md) records 20 real Sol/high reviews through native discovery and OCR delegated criteria. The tested context recipe added no verified discoveries; it remains an experimental input, not a production default.

The subsequent [changed-symbol experiment](./symbol-context-experiment-2026-09-17.md) used five different cases and 20 more Sol/high reviews. In those runs, diff-only versus context yielded six versus four supported Flow B-style discoveries and three versus five OCR discoveries, with 11.9–13.1% more input tokens for context. These exploratory results leave the production default unchanged.

The positive annotations span one diff-level, two file-level, and two repository-level cases. No PHP positive passed the source-evidence threshold. The manifest records rejected candidates and leaves Appwrite's domain-guard change unscored until its interaction with DNS and duplicate-rule checks is established.

## Prepare the inputs

Use Python 3.10 or newer and a network connection for the first preparation:

```bash
mkdir -p distillery/.eval-data
python3 distillery/benchmarks/aacr/prepare.py \
  --cache distillery/.eval-data/aacr-cache \
  --output distillery/.eval-data/aacr-prepared
```

The output directory must not exist. The command verifies the pinned dataset checksums, downloads source files at immutable commits, and publishes the output only after all cases succeed. It neither installs nor executes the reviewed projects and makes no model requests.

To use an existing AACR checkout, add `--source-dir /path/to/aacr-bench/dataset`. Its files must match the selected revision's exact checksums. After a successful preparation, you can add `--offline` and choose a fresh output directory to reproduce the bundle from the cache.

- `reviewer/inputs.jsonl` identifies each case, its merge base and reviewed head, and the available files. Each case directory contains a scoped `diff.patch` plus complete base/head files for the selected paths and supporting context.
- `refs/labels.jsonl` preserves the selected positive and negative comments, original context/category annotations, and source-verification notes. These are grading materials.
- `refs/selection.json` preserves source provenance and curation decisions; `refs/LICENSE.aacr-bench` preserves the AACR license. `refs/receipt.json` records fetched content hashes.

Give the reviewer only `reviewer/` in an isolated workspace. Do not expose `selection.json`, `refs/`, this directory, the download cache, or the source dataset to the evaluated process. Directory separation alone does not enforce that boundary. The curated file selection itself provides localization hints, so comparisons must use the same input scope.

## What the cases establish

Review only the selected file changes, using the supplied context. The bundle deliberately does not claim to contain the full PR diff or repository. Compare each selected positive claim against code at the pinned merge base and head; the curation notes describe a concrete introduced failure. The verification is source inspection, not execution of the upstream project's test suite.

Treat negative labels as **specific rejected review claims**, not clean PRs. A reviewer can correctly find a different bug on the same PR. Likewise, an unmatched finding is unadjudicated, not automatically false. Deduplicate equivalent findings before counting them. Report selected-defect detection and recurrence of selected false claims separately; do not call those measurements whole-review recall or precision.

Preserve upstream `Diff Level`, `File Level`, and `Repo Level` annotations as provenance. They are not measured minimum-context requirements. Run a paired diff-only versus supplied-context comparison before attributing a result to retrieval.

Reserve newly selected evaluation PRs and their revisions from prompt tuning and development examples. If a case informs a policy or skill change, move that whole PR out of the holdout before a confirmatory run. The five initial PRs above have now been retired to development, including all their revisions. These are public cases; model-training exposure is unknown. The preparation utility itself does not run evaluated reviewers.

## Why the source is pinned

Use GitHub revision `68a569759289a83654a59d06db2a72910edf0a4a`. Its positive file contains 196 PR records and 1,506 comments; its negative file contains 155 overlapping PR records and 639 comments.

The upstream converter combines a mutable `main` download URL with checksum `d8683cb240249bc4e0aff6428802bdffa7b7573ace600552cab1cd0cb7e905c9`, which matches older revision `ab8af8d5c74e2a4d1945d247ea4bbc49f93eb33f`. The [upstream correction](https://github.com/alibaba/aacr-bench/commit/dae864774126df619243090cbae38d7db07caa64) moved one DBeaver finding from negative to positive. The pinned Hugging Face version retains the older label. Use the GitHub pair consistently; do not disable checksum checking or combine the two label sets. The manifest records both versions and their exact hashes.

AACR's `source_commit` is not necessarily an ancestor of `target_commit`. The selection therefore preserves that pair and separately pins the verified merge base used to construct review diffs. Subtracting a diverged source directly would mix unrelated target-branch changes into the review.

## Decision record

**VERIFIED ANSWER:** use the initial curated subset as development diagnostics, with original labels retained as provenance and each selected claim checked independently against source. Select independent cases for subsequent evaluation.

The strongest counterargument is label quality: some upstream positives describe already-fixed code or unchanged behavior, and incomplete annotations cannot establish an exhaustive truth set. Exclude those claims; do not repair the apparent score by accepting them. A private, independently adjudicated full-review cohort is the next-best alternative and is preferable for production-default decisions.

The likely failure modes are label leakage into prompts, treating rejected comments as clean PRs, and drawing retrieval conclusions from unequal scope or token budgets. Isolate grading materials, adjudicate novel findings, and hold model, effort, snapshot, and scope constant. Confidence is high in the byte provenance and narrower source-checked claims; incremental review quality remains unknown. Retire a case if its claimed defect cannot be reproduced from the pinned evidence, and replace this small cohort before making general quality claims.

## Use with dual-review

Dual-review already invokes Whetstone's `ia-code-review` and has paired discovery canaries. Its existing fixed-candidate classifier replay measures a different task. The native `dual-review-canary discovery-aacr-prepare` command imports this bundle without launching models or copying annotations into reviewer inputs. After independent native reference passes and a passing development experiment, `discovery-aacr-freeze` binds the cohort to those results. Follow [dual-review's evaluation guide](https://github.com/iliaal/dual-review/blob/main/docs/replay-evaluation.md#prepare-a-curated-aacr-holdout) for commands and prerequisites.

The current five-case seed lacks an independently clean review and mostly contains single-file review scopes. It cannot satisfy the existing clean-review and feature-shard gates as selected. Keep it as diagnostic input; select additional clean and multi-file cases independently before attempting a passing confirmatory comparison. Neither adapter command manufactures classifier verdicts or relaxes those gates.

If context-sensitive misses justify an experiment, compare the existing blind diff review with a frozen context bundle selected independently of the first reviewer's findings. Preserve dual-review's isolated Flow B process, snapshot binding, redaction, verification, and publication gates. Direct OCR substitution is not implied by this dataset.

## Build experimental symbol context

Use [symbol_context.py](./symbol_context.py) to select bounded source excerpts around changed calls and symbols. This standalone prototype reads the CodeSage 0.33.1 structural index; it does not change CodeSage or dual-review defaults and makes no model requests.

Create a checkout at each case's exact head under `sources/<case-id>`, with its base commit available. Run `codesage init` and `codesage index --full --no-semantic` in each checkout, then:

```bash
python3 distillery/benchmarks/aacr/symbol_context.py \
  --inputs distillery/.eval-data/aacr-prepared/reviewer/inputs.jsonl \
  --reviewer-root distillery/.eval-data/aacr-prepared/reviewer \
  --sources-root /path/to/sources \
  --output /path/to/new-contexts.jsonl \
  --budget 7000
```

The output must not exist. Each JSONL row contains a UTF-8 context packet, selected spans with source hashes, and unresolved or omitted candidates. The selector verifies prepared base/head bytes, index freshness, and emitted source against Git. It preserves whole numbered spans within the byte limit and prioritizes changed-line calls before enclosing symbols and their other calls, balancing files within each priority. Source rows use LF boundaries; ambiguous bare-CR files are refused.

Call definitions are **name-based candidates**, not proven runtime targets. The prototype follows local import/include paths through at most three edges, with no global-name fallback; it withholds ambiguous matches and untyped receivers. Dependency reachability does not establish an import binding, and dynamic dispatch, aliases, package resolution, large symbols, and parser gaps can leave useful contracts unresolved. Inspect the recorded omissions before interpreting an empty or partial packet as adequate context. Keep labels and grading artifacts separate from reviewers.

## Check the preparation and context utilities

```bash
python3 -m unittest discover -s distillery/benchmarks/aacr -p 'test_*.py'
ruff check distillery/benchmarks/aacr/*.py
```

The preparation tests use synthetic source records and a mocked download boundary. They check checksum refusal, label separation, merge-base selection, missing files, dependency-version separation, and offline reproducibility. Selector tests use temporary Git repositories and structural-index fixtures to check candidate resolution, ambiguity, budget ordering, call-site identity, line boundaries, and source hashes. A successful real-source preparation verifies availability and packaging; it does not execute the selected defects or establish review quality.

## Attribution

AACR-Bench is published by Alibaba under [Apache-2.0](https://github.com/alibaba/aacr-bench/blob/68a569759289a83654a59d06db2a72910edf0a4a/LICENSE). See [the paper](https://arxiv.org/abs/2601.19494) for its collection and annotation method. The committed selection contains locators and original curation notes; preparation retrieves the upstream annotations unchanged. Downloaded repository source remains subject to each source project's license. Preserve those licenses before redistributing source bundles.
