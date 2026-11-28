# Plan and state safety

Read before running `apply` or `destroy`, deleting or moving a resource block, or adding `lifecycle` arguments.

## Apply only a saved, reviewed plan

Run `terraform plan -out=tfplan`, `terraform show tfplan`, then `terraform apply tfplan`. A bare `apply` re-plans, so it can execute changes nobody reviewed. A saved plan applies without a confirmation prompt, so present the plan summary (replacements, destroys, unexpected drift) and obtain explicit approval before running `apply` or `destroy`.

## `prevent_destroy` and `removed` blocks

`lifecycle { prevent_destroy = true }` fails a plan that would destroy the object only while its resource block remains in configuration; deleting the block removes the guard and the next apply destroys the object. To stop managing a resource without destroying it, replace the resource block with a `removed` block (Terraform and OpenTofu 1.7+) and confirm the plan shows no destroy:

```hcl
removed {
  from = aws_db_instance.main

  lifecycle {
    destroy = false
  }
}
```

Add `prevent_destroy` to stateful resources (databases, buckets, keys) and treat a deleted block for one as a destroy in review.

## `ignore_changes`

`lifecycle { ignore_changes = [attr] }` suppresses **updates only**, and it substitutes the prior state value at plan time, on the *first* plan after the config change, with no "first apply" exception. Two consequences reviewers get backwards: (1) on an already-provisioned resource the literal in the config is never written, and `ForceNew` never fires because `ignore_changes` erased the diff before replacement is evaluated, so a change that replaces a committed value with a placeholder scrubs the repository and leaves the remote value live; (2) `ignore_changes` does not apply on create, so any later `-replace`, taint, `state rm` + re-add, or manual deletion re-seeds the placeholder over a value that was set out of band. Keep only the container resource in configuration and provision the value entirely out of band, or state the restore step in the runbook for every replace path.
