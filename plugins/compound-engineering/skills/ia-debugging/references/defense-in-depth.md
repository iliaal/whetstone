# Defense-in-Depth Validation

When you fix a bug caused by invalid data, adding validation at one place feels sufficient. But that single check can be bypassed by different code paths, refactoring, or mocks.

**Core principle:** Validate at EVERY layer data passes through. Make the bug structurally impossible.

## Why Multiple Layers

Single validation: "We fixed the bug."
Multiple layers: "We made the bug impossible."

Different layers catch different failure modes:
- Entry validation catches most invalid input
- Business logic catches domain-specific edge cases
- Environment guards prevent context-specific dangers (e.g., destructive operations in test)
- Debug instrumentation captures forensic context when other layers fail

## The Four Layers

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
    if (empty($projectDir)) {
        throw new \RuntimeException('projectDir required for workspace initialization');
    }
    // ... proceed
}
```

### Layer 3: Environment Guards

Prevent dangerous operations in specific contexts (test, staging, CI).

```python
async def git_init(directory: str) -> None:
    if os.environ.get("NODE_ENV") == "test":
        normalized = os.path.realpath(directory)
        tmp_dir = os.path.realpath(tempfile.gettempdir())
        if not normalized.startswith(tmp_dir):
            raise RuntimeError(
                f"Refusing git init outside temp dir during tests: {directory}"
            )
    # ... proceed
```

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

When you fix a bug:

1. **Trace the data flow** -- where does the bad value originate? Where is it consumed?
2. **Map all checkpoints** -- list every function/boundary data passes through
3. **Add validation at each layer** -- entry, business logic, environment, instrumentation
4. **Test each layer independently** -- bypass layer 1, verify layer 2 catches it

## Key Insight

All four layers are typically necessary. During testing, each layer catches bugs the others miss:
- Different code paths bypass entry validation
- Mocks bypass business logic checks
- Edge cases on different platforms need environment guards
- Debug logging identifies structural misuse patterns

Don't stop at one validation point.
