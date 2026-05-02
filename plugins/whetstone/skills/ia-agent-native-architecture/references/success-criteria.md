# Success Criteria

You've built an agent-native application when:

## Architecture
- [ ] The agent can achieve anything users can achieve through the UI (parity)
- [ ] Tools are atomic primitives; domain tools are shortcuts, not gates (granularity)
- [ ] New features can be added by writing new prompts (composability)
- [ ] The agent can accomplish tasks you didn't explicitly design for (emergent capability)
- [ ] Changing behavior means editing prompts, not refactoring code

## Implementation
- [ ] System prompt includes dynamic context about app state
- [ ] Every UI action has a corresponding agent tool (action parity)
- [ ] Agent tools are documented in system prompt with user vocabulary
- [ ] Agent and user work in the same data space (shared workspace)
- [ ] Agent actions are immediately reflected in the UI
- [ ] Every entity has full CRUD (Create, Read, Update, Delete)
- [ ] Agents explicitly signal completion (no heuristic detection)
- [ ] context.md or equivalent for accumulated knowledge

## Product
- [ ] Simple requests work immediately with no learning curve
- [ ] Power users can push the system in unexpected directions
- [ ] You're learning what users want by observing what they ask the agent to do
- [ ] Approval requirements match stakes and reversibility

## Mobile (if applicable)
- [ ] Checkpoint/resume handles app interruption
- [ ] iCloud-first storage with local fallback
- [ ] Background execution uses available time wisely
- [ ] Model tier matched to task complexity

---

## The Ultimate Test

**Describe an outcome to the agent that's within your application's domain but that you didn't build a specific feature for.**

Can it figure out how to accomplish it, operating in a loop until it succeeds?

If yes, you've built something agent-native.

If it says "I don't have a feature for that" -- your architecture is still too constrained.
