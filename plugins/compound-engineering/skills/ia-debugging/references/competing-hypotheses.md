# Analysis of Competing Hypotheses (ACH)

When the root cause is unclear -- especially across multiple components -- systematic hypothesis analysis prevents premature commitment to an incorrect explanation.

## When to Use

- Multiple plausible explanations for a failure
- Bug spans component boundaries (API -> service -> DB)
- Three-Fix Threshold reached (3 failed attempts)
- Intermittent failures with no clear reproduction pattern

## Six Failure Categories

Generate hypotheses across these categories. Most bugs start as one category but have root causes in another.

| Category | Symptoms | Example |
|----------|----------|---------|
| **Logic error** | Wrong output for valid input, off-by-one, incorrect branching | `<=` vs `<` in loop boundary |
| **Data issue** | Unexpected null, wrong type, stale cache, encoding mismatch | JSON field renamed upstream, cached value from previous schema |
| **State problem** | Race condition, leaked global state, order-dependent initialization | Test passes alone, fails in suite due to shared DB state |
| **Integration failure** | Contract mismatch at boundary, wrong endpoint, auth expired | Service A sends `user_id`, service B expects `userId` |
| **Resource exhaustion** | Timeout, OOM, connection pool depleted, disk full | DB pool max hit under load, queries queue indefinitely |
| **Environment** | Config drift, wrong version, missing dependency, OS difference | Works on macOS, fails on Linux due to case-sensitive filesystem |

## Evidence Strength Scale

Not all evidence is equal. Rank each piece:

| Strength | Type | Example |
|----------|------|---------|
| **Strong** | Direct observation | Stack trace pointing to exact line, failing test output |
| **Medium** | Correlational | Bug appeared after deploy X, timing correlates with load spike |
| **Weak** | Testimonial | "I think I saw this before when..." (no logs or reproduction) |
| **Variable** | Absence of evidence | "This component has no errors in its logs" (absence != proof) |

## The ACH Process

### 1. List hypotheses

For each failure category, generate at least one hypothesis. Be specific: "data issue" is not a hypothesis; "the `user.email` field is null because the upstream API changed its response format" is.

### 2. Collect evidence

For each hypothesis, gather evidence FOR and AGAINST:

```
H1: Race condition in session initialization
  FOR:  Intermittent (strong), only under concurrent requests (medium)
  AGAINST: Single-threaded test also fails (strong)
  → WEAKENED by counter-evidence

H2: Stale config cached after deploy
  FOR:  Timestamp of first failure matches deploy (medium), restart fixes it (strong)
  AGAINST: None found
  → STRONGEST candidate
```

### 3. Score confidence

| Confidence | Meaning | Action |
|------------|---------|--------|
| **>80%** | Strong evidence, weak counter-evidence | Proceed with fix, but verify |
| **50-80%** | Mixed evidence | Investigate further before fixing |
| **<50%** | Weak or contradictory evidence | Do NOT attempt a fix yet |

### 4. Investigate the top hypothesis

Test the highest-confidence hypothesis first. One change at a time. Fully revert if wrong.

If the top two hypotheses are equally supported (within 10%), suspect a compound cause -- both may be true simultaneously.

## Anti-Patterns

- **Anchoring**: committing to the first hypothesis that seems plausible
- **Confirmation bias**: only looking for evidence that supports your preferred hypothesis
- **Premature closure**: stopping investigation after one piece of supporting evidence
- **Ignoring absence**: "no errors in this component" doesn't mean the component is innocent
