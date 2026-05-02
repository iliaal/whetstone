# System-Wide Test Check

Before marking a task done, pause and trace the blast radius of the change. This catches integration failures that pass-in-isolation testing misses.

| Question | What to do |
|----------|------------|
| **What fires when this runs?** Callbacks, middleware, observers, event handlers -- trace two levels out from the change. | Read the actual code (not docs) for callbacks on models touched, middleware in the request chain, `after_*` hooks. |
| **Do tests exercise the real chain?** If every dependency is mocked, the test proves logic works in isolation -- it says nothing about the interaction. | Write at least one integration test that uses real objects through the full callback/middleware chain. No mocks for layers that interact. |
| **Can failure leave orphaned state?** If code persists state (DB row, cache, file) before calling an external service, what happens when the service fails? Does retry create duplicates? | Trace the failure path with real objects. If state is created before the risky call, test that failure cleans up or that retry is idempotent. |
| **What other interfaces expose this?** Mixins, DSLs, alternative entry points. | Grep for the method/behavior in related classes. If parity is needed, add it now. |
| **Do error strategies align across layers?** Retry middleware + application fallback + framework error handling -- do they conflict or create double execution? | List the specific error classes at each layer. Verify the rescue list matches what the lower layer actually raises. |

**When to skip:** Leaf-node changes with no callbacks, no state persistence, no parallel interfaces. Purely additive changes (new helper, new view partial) take 10 seconds to verify "nothing fires."

**When this matters most:** Changes touching models with callbacks, error handling with fallback/retry, or functionality exposed through multiple interfaces.
