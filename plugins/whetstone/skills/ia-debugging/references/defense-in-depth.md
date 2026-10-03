# Defense-in-Depth Validation

After verifying a fix for invalid data, inspect whether the invalid state can still be constructed through another reachable path. Prefer an existing validated type, constructor, or shared helper when the affected callers can use it within the repair's scope.

**Core principle:** Prevent invalid construction where possible. Add checks at boundaries that catch distinct failure classes or remain reachable without earlier validation.

## Why Multiple Layers

Use multiple layers when the layers enforce different requirements:
- Entry validation catches most invalid input
- Business logic catches domain-specific edge cases
- Environment guards prevent context-specific dangers (e.g., destructive operations in test)
- Debug instrumentation captures forensic context when checks fail; logging does not enforce an invariant

## Possible Layers

Select the layers required by the observed data flow. Repeating the same check at every function adds maintenance cost without preventing a new failure path.

### Layer 1: Entry Point Validation

Reject obviously invalid input at the API/function boundary. This is the first line of defense.

```php
function createProject(string $name, string $workingDirectory): Project
{
    if (empty($workingDirectory)) {
        throw new \InvalidArgumentException('workingDirectory cannot be empty');
    }
    if (!is_dir($workingDirectory)) {
        throw new \InvalidArgumentException("workingDirectory does not exist: {$workingDirectory}");
    }
    // ... proceed
}
```

### Layer 2: Business Logic Validation

Ensure data makes sense for this specific operation, even if it passed entry validation.

```php
function initializeWorkspace(string $projectDir, string $sessionId): void
{
    if ($sessionId === '') {
        throw new \RuntimeException('sessionId required for workspace initialization');
    }
    // ... proceed
}
```

### Layer 3: Environment Guards

Prevent dangerous operations in specific contexts (test, staging, CI).

```python
import os
import tempfile


async def git_init(directory: str) -> None:
    if os.environ.get("NODE_ENV") == "test":
        normalized = os.path.realpath(directory)
        tmp_dir = os.path.realpath(tempfile.gettempdir())
        if normalized == tmp_dir or os.path.commonpath([normalized, tmp_dir]) != tmp_dir:
            raise RuntimeError(
                f"Refusing git init outside temp dir during tests: {directory}"
            )
    # ... proceed
```

Resolve symlinks before comparing path components; a string prefix also accepts sibling paths such as `/tmp-other`. Restrict the operation to a child of the temporary root, not the root itself. This check assumes the test owns the directory and no concurrent actor can replace its path components; use an isolated workspace or descriptor-relative operations when that assumption does not hold.

### Layer 4: Debug Instrumentation

Capture context for forensics when the other layers fail.

```typescript
async function gitInit(directory: string) {
  const stack = new Error().stack;
  console.error('About to git init', { directory, cwd: process.cwd(), stack });
  // ... proceed
}
```

Use `console.error()` in tests (not logger, which may be suppressed). Log BEFORE the dangerous operation, not after it fails. Include context: cwd, env vars, timestamps, stack trace.

## Applying the Pattern

After verifying the minimal fix:

1. **Trace the data flow**: identify where the bad value originates and where it is consumed.
2. **Inspect construction**: check whether an existing type, constructor, or helper can enforce the invariant for the affected callers.
3. **Keep prevention scoped**: reuse that mechanism where the repair's scope permits it. Report wider interface changes or refactoring separately.
4. **Choose distinct checks**: retain guards for independent domain or environment requirements, and for callers that can bypass earlier validation. Remove duplication only after proving those paths cannot bypass the shared mechanism.
5. **Verify recurrence prevention**: exercise the original trigger and nearby invalid inputs. Test each retained guard through its own reachable failure path; report a missing seam rather than substituting a mock-only bypass.

## Key Insight

The number of checks is not the success criterion. Verify that invalid construction is prevented where feasible and that each retained boundary covers a distinct, reachable failure mode. Keep diagnostic instrumentation only when it serves an ongoing operational need.
