# Native test patterns

## Testing

| Situation | Approach |
|-----------|----------|
| Quick validation | `terraform fmt -check && terraform validate` |
| Pre-commit | + `tflint` + `trivy config .` / `checkov -d .` |
| Logic validation (1.6+) | Native `terraform test` with `command = plan` |
| Cost-free unit tests (1.7+) | Native tests + `mock_provider` |
| Real infra validation | Native tests with `command = apply`, or Terratest (Go) |

**Native test essentials** (`.tftest.hcl` in `tests/`):
- `command = plan` for fast unit tests; `command = apply` for integration (default)
- `assert { condition = expr; error_message = "..." }`: multiple per run block
- `expect_failures = [var.name]` for negative testing (validate rejection of bad input)
- `mock_provider "aws" { mock_resource "..." { defaults = { ... } } }`: plan-mode only, no credentials, fast CI
- `variables {}` at file level (all runs) or within a `run` block (override)
- Reference prior run outputs: `run.setup.vpc_id`
- `parallel = true` on independent runs with separate state; creates sync point at next sequential run
- `state_key = "name"` required for `parallel = true` runs with independent state
- File naming: `*_unit_test.tftest.hcl` (plan mode) vs `*_integration_test.tftest.hcl` (apply mode)
- A `module {}` block inside a `run` accepts local paths and registry modules only, not git or HTTP sources. Repos consuming git-sourced modules must vendor or localize them before they can be tested.
- After a test file completes, resources are destroyed in **reverse run-block order**. Order dependent runs accordingly (create the bucket before the run that puts objects in it), or the destroy fails and leaves billable resources behind. There is no CLI flag to skip cleanup; inspect a failure with `-verbose`.

**Running them:**

```bash
terraform test                                     # all *.tftest.hcl under tests/
terraform test -filter=vpc_unit_test.tftest.hcl    # one test FILE (not a run-block name)
terraform test -verbose                            # show the plan/apply per run block
terraform test -test-directory=path                # non-default test dir
```

Split by cost in CI: plan-mode unit tests on every PR, apply-mode integration tests on merge only.
