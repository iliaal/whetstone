# review modes

## Headless Mode

When invoked programmatically (by another skill or command with `mode:headless`), skip interactive prompts and return structured triage results. See [headless-mode.md](./headless-mode.md) for the classification table (AUTO-FIX / AUTO-DECLINE / ESCALATE), output format, and constraints.

Umbrella term: non-interactive context. Also called "Spawned-session behavior" in ia-orchestrating-swarms and "Headless mode" in ia-brainstorming; same rule: suppress blocking prompts when no user is present.

## Scope vs `ia-pr-comment-resolver` Agent

This skill and the `ia-pr-comment-resolver` agent handle different situations:

| | This skill (interactive) | This skill (headless) | `ia-pr-comment-resolver` agent |
|---|---|---|---|
| **When** | Interactive review requiring judgment | Programmatic triage by another skill/command | Implementing a single pre-triaged comment |
| **Approach** | Verify, evaluate, potentially push back | Auto-classify and return triage results | Implement a single pre-classified change |
| **Skepticism** | High -- check correctness first | High -- same rules, automated classification | Low -- comments are pre-triaged |
| **Use for** | Unclear suggestions, architectural feedback | Batch triage before dispatching resolvers | Clear-cut fixes, style nits, typos |

When the `ia-pr-comment-resolver` agent encounters feedback that requires judgment (architectural decisions, debatable trade-offs), it should escalate rather than implement.

## Examples

**Bad -- performative agreement:**
> Reviewer: "This should use a Map instead of an object for better performance."
> Response: "Great catch! Switching to Map now."

**Good -- verify first:**
> Reviewer: "This should use a Map instead of an object for better performance."
> Response: "Checked this -- the object has at most 5 keys (bounded by the enum). Map overhead isn't justified here. Keeping as-is."

**Bad -- blind implementation:**
> Reviewer: "Add null checks for the user parameter."
> Response: "Done, added null checks."

**Good -- verify the premise:**
> Reviewer: "Add null checks for the user parameter."
> Response: "Traced the call chain -- `user` comes from the auth middleware which guarantees non-null (throws 401 otherwise). Adding a null check here would be dead code. Should I add it anyway for defense-in-depth?"

**Good -- unclear item:**
> Reviewer: "This logic seems off."
> Response: "Can you clarify which part? The filter predicate, the sort order, or the pagination logic?"

## Verify

- All feedback items triaged (classified as correct, incorrect, or unclear)
- Ambiguous items clarified before any implementation
- Each fix verified individually (test after each, not batch)
- No performative agreement phrases in responses ("Great catch!", "Absolutely right")

## Integration

This skill pairs with:
- `ia-code-review` -- the outbound side (requesting reviews). Their action-routing tiers (`safe_auto`/`gated_auto`/`manual`/`advisory`) roughly map to this skill's AUTO-FIX / ESCALATE-for-approval / ESCALATE / FYI.
- `ia-pr-comment-resolver` agent -- for mechanical PR comment resolution (see scope table above)
- `ia-verification-before-completion` -- verify each fix before marking resolved
