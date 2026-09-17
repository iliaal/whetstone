# AACR review holdout preparation

Prepare source-checked review cases from [AACR-Bench](https://github.com/alibaba/aacr-bench) without running a model. The selection is a small diagnostic holdout for future Whetstone, CodeSage, or independent-review experiments. It is not an exhaustive reference inventory or a reproduction of AACR's published scores.

The initial selection contains five PRs, five positive defect claims, and five rejected-claim negatives:

| Case | Language | Positive defect | Negative claims |
|---|---|---|---:|
| Valkey #1889 | C | Comma expressions break `snprintf` arguments | 0 |
| SDL #12718 | C | Texture dereference precedes its NULL guard | 1 |
| n8n #20210 | TypeScript | Default surname test contradicts its helper | 2 |
| browser-use #1482 | Python | An accepted nullable port reaches an integer-only socket argument | 2 |
| ComfyUI #6542 | Python | DirectML causal mask skips initialization | 0 |

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

Reserve every selected PR and its revisions from prompt tuning and development examples. If a case informs a skill change, move that whole PR out of the holdout before a confirmatory run. These are public cases; model-training exposure is unknown. Curation has inspected their labels, but no evaluated reviewer has been run as part of preparation.

## Why the source is pinned

Use GitHub revision `68a569759289a83654a59d06db2a72910edf0a4a`. Its positive file contains 196 PR records and 1,506 comments; its negative file contains 155 overlapping PR records and 639 comments.

The upstream converter combines a mutable `main` download URL with checksum `d8683cb240249bc4e0aff6428802bdffa7b7573ace600552cab1cd0cb7e905c9`, which matches older revision `ab8af8d5c74e2a4d1945d247ea4bbc49f93eb33f`. The [upstream correction](https://github.com/alibaba/aacr-bench/commit/dae864774126df619243090cbae38d7db07caa64) moved one DBeaver finding from negative to positive. The pinned Hugging Face version retains the older label. Use the GitHub pair consistently; do not disable checksum checking or combine the two label sets. The manifest records both versions and their exact hashes.

AACR's `source_commit` is not necessarily an ancestor of `target_commit`. The selection therefore preserves that pair and separately pins the verified merge base used to construct review diffs. Subtracting a diverged source directly would mix unrelated target-branch changes into the review.

## Decision record

**VERIFIED ANSWER:** use the curated subset as a diagnostic holdout, with original labels retained as provenance and each selected claim checked independently against source.

The strongest counterargument is label quality: some upstream positives describe already-fixed code or unchanged behavior, and incomplete annotations cannot establish an exhaustive truth set. Exclude those claims; do not repair the apparent score by accepting them. A private, independently adjudicated full-review cohort is the next-best alternative and is preferable for production-default decisions.

The likely failure modes are label leakage into prompts, treating rejected comments as clean PRs, and drawing retrieval conclusions from unequal scope or token budgets. Isolate grading materials, adjudicate novel findings, and hold model, effort, snapshot, and scope constant. Confidence is high in the byte provenance and narrower source-checked claims; incremental review quality remains unknown. Retire a case if its claimed defect cannot be reproduced from the pinned evidence, and replace this small cohort before making general quality claims.

## Use with dual-review

Dual-review already invokes Whetstone's `ia-code-review` and already has paired discovery canaries. Its existing fixed-candidate classifier replay measures a different task. Use these public cases as input material for a separately prepared discovery cohort, after its required independent reference and coverage pass. This directory does not implement that adapter or manufacture authenticated classifier verdicts.

If context-sensitive misses justify an experiment, compare the existing blind diff review with a frozen context bundle selected independently of the first reviewer's findings. Preserve dual-review's isolated Flow B process, snapshot binding, redaction, verification, and publication gates. Direct OCR substitution is not implied by this dataset.

## Check the preparation utility

```bash
python3 -m unittest discover -s distillery/benchmarks/aacr -p 'test_*.py'
ruff check distillery/benchmarks/aacr/prepare.py distillery/benchmarks/aacr/test_prepare.py
```

The unit tests use synthetic source records and a mocked download boundary. They check checksum refusal, label separation, merge-base selection, missing files, dependency-version separation, and offline reproducibility. A successful real-source preparation verifies availability and packaging; it does not execute the selected defects or establish review quality.

## Attribution

AACR-Bench is published by Alibaba under [Apache-2.0](https://github.com/alibaba/aacr-bench/blob/68a569759289a83654a59d06db2a72910edf0a4a/LICENSE). See [the paper](https://arxiv.org/abs/2601.19494) for its collection and annotation method. The committed selection contains locators and original curation notes; preparation retrieves the upstream annotations unchanged. Downloaded repository source remains subject to each source project's license. Preserve those licenses before redistributing source bundles.
