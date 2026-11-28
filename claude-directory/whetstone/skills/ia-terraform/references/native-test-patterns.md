# Native test patterns

## Testing

| Situation | Approach |
|-----------|----------|
| Quick validation | `terraform fmt -check && terraform validate` |
| Pre-commit | + `tflint` + `trivy config .` / `checkov -d .` |
| Logic validation (1.6+) | Native `terraform test` with `command = plan` |
| Provider-free unit tests (1.7+) | Native plan or apply tests with mocked providers and no external effects |
| Real infra validation | Native tests with `command = apply`, or Terratest (Go) |

**Native test essentials** (`.tftest.hcl` in `tests/`):
- `command = plan` checks planned values; `command = apply` checks resulting state (default). Mocked apply is also a unit-test option.
- Place `condition` and `error_message` on separate lines inside each `assert` block; multiple assertions are allowed per run.
- `expect_failures = [var.name]` for negative testing (validate rejection of bad input)
- `mock_provider` replaces provider operations for both plan and apply. Computed values are generated during apply by default; use `override_during = plan` when a plan assertion needs them. Mock every provider used by the selected run, including aliases. Inspect provisioners, external commands, and built-in resources separately; mocking one provider does not make the whole test safe.
- `variables {}` at file level (all runs) or within a `run` block (override)
- Reference prior run outputs: `run.setup.vpc_id`
- `parallel = true` on independent runs with separate state; creates sync point at next sequential run
- `state_key = "name"` required for `parallel = true` runs with independent state
- File naming: `*_unit_test.tftest.hcl` for verified local/mocked effects; `*_integration_test.tftest.hcl` for real services or infrastructure, regardless of command mode.
- A `module {}` block inside a `run` accepts local paths and registry modules only, not git or HTTP sources. Repos consuming git-sourced modules must vendor or localize them before they can be tested.
- After a test file completes, resources are destroyed in **reverse run-block order**. Order dependent runs accordingly (create the bucket before the run that puts objects in it), or the destroy fails and leaves billable resources behind. There is no CLI flag to skip cleanup; inspect a failure with `-verbose`.

**Running them:**

```bash
terraform test                                     # all *.tftest.hcl under tests/
terraform test -filter=tests/vpc_unit_test.tftest.hcl # root-relative FILE, not a run name
terraform test -verbose                            # show the plan/apply per run block
terraform test -test-directory=path                # non-default test dir
```

An unknown filter can emit only a warning and finish with zero tests. Check the selected file and a nonzero passed-run count after a successful command:

```bash
set -euo pipefail
test_file=tests/vpc_unit_test.tftest.hcl
report=$(mktemp)
trap 'rm -f -- "$report"' EXIT
if terraform test -json "-filter=$test_file" >"$report"; then
    :
else
    status=$?
    cat "$report" >&2
    exit "$status"
fi
jq -e -s --arg file "$test_file" '
  any(.[]; .type == "test_run" and .test_run.path == $file
      and .test_run.progress == "complete" and .test_run.status == "pass")
  and any(.[]; .type == "test_summary" and .test_summary.status == "pass"
          and .test_summary.passed > 0)
' "$report"
```

For this local `main.tf`, a mocked apply can check a computed ID without contacting a provider service:

```hcl
resource "terraform_data" "item" {
  input = "unit-test"
}

output "item_id" {
  value = terraform_data.item.id
}
```

Place the following test in `tests/vpc_unit_test.tftest.hcl` for the selection recipe above. The built-in provider is mocked; no provisioner or external command runs:

```hcl
mock_provider "terraform" {
  mock_resource "terraform_data" {
    defaults = {
      id = "unit-test-id"
    }
  }
}

run "computed_output" {
  command = apply

  assert {
    condition     = output.item_id == "unit-test-id"
    error_message = "The module must expose the computed ID."
  }
}
```

Run verified local/mocked suites on every PR. Run real-service or infrastructure suites only with the required authorization, credentials, cost budget, and cleanup checks.
