# PR and MR Description Style

Rules for writing pull-request and merge-request descriptions that senior engineers actually read, not skim.

## Sizing matrix

Match the description length to the change complexity. Overwriting a trivial patch with a narrative wastes reviewer time; underwriting a structural change hides intent.

| Change shape | Description size |
|--------------|------------------|
| Typo, comment fix, single-line bug fix, dependency bump with no behavior change | 1 sentence |
| Small feature or fix touching 1-3 files, no architectural implications | 2-4 sentences |
| Non-trivial feature, new endpoint, new skill, multi-file refactor | Full narrative: Before / After / Scope rationale |
| Architecturally significant change, new module, migration, subsystem rewrite | Full narrative + rationale for decisions NOT taken |

Skip the template for trivial PRs. "Bump lodash to 4.17.21 for CVE-2021-23337." is complete on its own -- do not pad it.

## Narrative frame (for non-trivial PRs)

Use three sections, in order:

**Before** -- what the code did / the system looked like before this change. One paragraph. Name the concrete state, not the abstract shape. "The `renderMessage` function serialized markdown synchronously in the request handler" beats "messaging was slow."

**After** -- what the code does / the system looks like now. Same paragraph shape. Describe the *net end state*, not the journey. The reviewer doesn't need to know you tried three approaches; they need to know what they're merging.

**Scope rationale** -- why this PR draws the line where it does. What's intentionally NOT included and why. This is the most-skipped section and the one reviewers value most -- it prevents "why didn't you also fix X?" review comments.

```
## Before
Authentication tokens were validated in each route handler via a helper call.
Token parsing logic was duplicated across 12 handlers, and the JWT secret
was read from env on every request.

## After
Authentication runs once in the `authRequired` middleware before any handler.
Token parsing is centralized; the secret is read once at process start.

## Scope rationale
- NOT changing the token format -- that's a separate migration in #1247
- NOT touching refresh-token flow -- the middleware is read-only for this PR
- NOT adding role-based authorization -- tracked in #1301
```

## Describe net end state, not iteration journey

The commit log is the journey. The description is the destination. If you wrote three approaches and kept the third, the description describes the third -- not all three.

**Don't**: "First I tried X but it didn't work because Y. Then I tried Z, which almost worked but ran into W. Finally I settled on V which handles both."

**Do**: "V replaces the previous X-based approach because V handles both the Y and W cases without the performance regression Z introduced."

Review drafts for "first I... then I... eventually..." phrasing -- rewrite toward the final state.

## Visual choice: Mermaid vs table

When the change benefits from a visual, pick the shape based on what you're showing:

- **Mermaid diagram** -- topology with edges. Components that send messages to each other, request flow across services, a state machine's transitions, a dependency graph. Anything where the *relationships* are the point.
- **Markdown table** -- rows with parallel attributes. A before/after comparison of config values, a list of endpoints with their verbs and paths, a comparison of options with their tradeoffs. Anything where the *structure is grid-shaped*.

Mermaid for topology; table for grid. Neither for content that's genuinely prose -- don't force structure where it doesn't serve understanding.

## GitHub-specific hazards

- **Never prefix list items with `#<number>`**: GitHub auto-links `#123` at the start of any line as an issue/PR reference. Use a dash and backticks instead:
  - Wrong: `# 1. Fixed bug`
  - Wrong: `#1 - Fixed bug`
  - Right: `1. Fixed bug` or `- Fixed bug`
- **Headings stay at H2 and below**: `#` (H1) is reserved for the PR title. Use `##` for section headings.
- **Code blocks use triple backticks, not quadruple** -- GitHub renders quadruple-backtick blocks inconsistently across web vs API views.

## Anti-patterns to strip

Apply the parent writing skill's banned-phrases list (no "delve", "leverage", "crucial", "game-changer", "in today's rapidly evolving landscape", etc.) in addition to these PR-specific offenders:

- "This PR..." opener -- redundant; the reader already knows it's a PR. Lead with the change.
- "Made some changes to..." -- say which changes. "Some" is an AI tell.
- "This should fix #1234" -- use "Fixes #1234" for auto-close, or "Related to #1234" if unsure. "Should" is hedging.
- Laundry-list commit message dumps in the description. The commit log is already there. Summarize the commits' net effect, don't reprint them.
- Emoji decoration on section headings. Sentence case, no emoji.

## Test plan

Every non-trivial PR needs a Test Plan section. Bulleted markdown checklist so reviewers can see exactly what was exercised:

```
## Test plan
- [ ] `npm test` passes locally
- [ ] Manual: sign in with new SAML IdP, verify redirect to dashboard
- [ ] Manual: sign in with existing OAuth flow, verify no regression
- [ ] Staging: load test middleware at 500 rps for 5 min, p95 < 80ms
```

Be concrete. "Tested manually" is not a test plan. "Signed in with new SAML IdP, verified redirect" is.

## Self-check before posting

Run these checks on the draft:

1. Can a reviewer who hasn't read the linked issue still understand what this PR does? If no, add context.
2. Is anything in the diff NOT mentioned in the description? Either describe it or question whether it belongs in this PR (scope drift).
3. Is the description longer than the diff deserves? Cut.
4. Did you use the word "simply" or "just"? Cut.
5. Did you claim the PR is "ready to merge"? Delete -- that's the reviewer's call.
