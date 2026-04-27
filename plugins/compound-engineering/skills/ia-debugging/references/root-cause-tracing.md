# Root Cause Tracing

Bugs often manifest deep in the call stack. The instinct is to fix where the error appears, but that treats a symptom.

**Core principle:** Trace backward through the call chain until you find the original trigger, then fix at the source.

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

Use `console.error()` in tests (not logger -- may be suppressed). Log BEFORE the operation, not after failure. Capture and filter:

```bash
npm test 2>&1 | grep 'DEBUG git init'
```

## Finding Test Pollution

When a test passes in isolation but fails in the suite, another test is polluting shared state.

**Bisection approach:** Run tests one at a time until the polluter is found.

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

Never fix just where the error appears. Trace back to find the original trigger. After finding the source, also add defense-in-depth validation at each layer the data passes through (see [defense-in-depth.md](./defense-in-depth.md)).
