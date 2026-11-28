# Root Cause Tracing

Bugs often manifest deep in the call stack. The instinct is to fix where the error appears, but that treats a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

**Legitimacy test:** first ask whether the state that triggered the symptom is one the system may legitimately be in (an empty list, a null the contract allows, a reconnect mid-request). If it is, the code that broke on it is the root cause and handling the state there is the fix; do not walk upstream to "fix" a valid producer or add validation that rejects a valid state. If the state should never exist, a check at the crash site hides the bug behind a guard, retry, swallowed error, clamped value, or discarded state; trace what produced it.

## When to Use

- Error happens deep in execution (not at entry point)
- Stack trace shows long call chain
- Unclear where invalid data originated
- Need to identify which test/caller triggers the problem

## The Tracing Process

### 1. Observe the symptom

```
Error: git init failed in <repo-root>/packages/core
```

### 2. Find the immediate cause

What code directly triggers this?

```typescript
await execFileAsync('git', ['init'], { cwd: projectDir });
```

### 3. Trace callers upward

```
WorktreeManager.createSessionWorktree(projectDir, sessionId)
  <- Session.initializeWorkspace()
  <- Session.create()
  <- test at Project.create()
```

### 4. Track the bad value

At each level, ask: what value was passed, and where did it come from?

- `projectDir = ''` (empty string)
- Empty string as `cwd` resolves to `process.cwd()`
- That's the source code directory, not the temp dir

### 5. Find the original trigger

Where did the empty string originate?

```typescript
const context = setupCoreTest(); // Returns { tempDir: '' }
Project.create('name', context.tempDir); // Accessed before beforeEach ran!
```

Root cause: top-level variable initialization accessing a value that isn't set until `beforeEach`.

## Adding Stack Traces for Instrumentation

When manual tracing hits a dead end, add instrumentation:

```typescript
async function gitInit(directory: string) {
  console.error('DEBUG git init:', {
    directory,
    cwd: process.cwd(),
    nodeEnv: process.env.NODE_ENV,
    stack: new Error().stack,
  });
  await execFileAsync('git', ['init'], { cwd: directory });
}
```

Use `console.error()` in tests (not logger, which may be suppressed). Log BEFORE the operation, not after failure. Capture and filter:

```bash
npm test 2>&1 | grep 'DEBUG git init'
```

## Finding Test Pollution

When a test passes in isolation but fails in the suite, another test is polluting shared state.

**Victim-order bisection:** First confirm that the failing test passes alone and fails after the tests that preceded it in the failing run. Recover that order from the CI log or shard listing and configure the runner to preserve it in the same process or shared environment.

1. Run half of the predecessor list, in its original order, followed by the victim from a fresh initial state.
2. Retain the half that still triggers the victim's failure, then repeat until one polluting file remains. Check the other half when the first passes; if neither reproduces the failure, investigate an interaction between subsets or an uncontrolled condition instead of blaming one file.
3. Identify the leaked state: environment variable, working directory, module singleton or cache, unrestored mock, listening server, shared temporary path, or global timer. Repair cleanup at the polluter; a victim-only reset hides the broken isolation contract.

**Artifact scan:** When pollution leaves a concrete artifact, run files individually and check for that artifact after each run. This linear scan serves a different case from victim-order bisection.

```bash
# Run each test file individually, check if artifact appears after each
for f in $(find src -name '*.test.ts'); do
  npx jest "$f" --forceExit 2>/dev/null
  if [ -d ".git/worktrees/phantom" ]; then
    echo "POLLUTER: $f"
    break
  fi
done
```

Analyze stack traces from instrumentation to find the pattern (same test? same parameter? same setup function?).

## Key Principle

Never fix just where the error appears unless the legitimacy test places the defect there. Trace back to find the original trigger. When the state should never exist, after fixing its source check whether another reachable path can still construct it, and add guards only for distinct reachable failure classes (see [defense-in-depth.md](./defense-in-depth.md)).
