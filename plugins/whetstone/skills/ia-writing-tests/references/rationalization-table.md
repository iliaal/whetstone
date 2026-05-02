# Rationalization Table

Load this reference when you catch yourself arguing against writing a test. Each rationalization below is the excuse; the reality column is why the excuse is wrong.

| Rationalization | Reality |
|----------------|---------|
| "This is too simple to need tests" | Simple code still breaks. Tests document expected behavior. |
| "I manually tested it" | Manual testing is ephemeral — it can't be re-run, it proves nothing to the next person |
| "Tests will slow me down" | Debugging without tests slows you down more. Tests catch bugs at write time instead of production. |
| "I'll add tests later" | Later never comes. The context you have now is gone later. |
| "The tests would just test the framework" | Then you're not testing your logic. Find the logic and test that. |
| "It's just a refactor, behavior didn't change" | Run the existing tests. If they pass, you're done. If none exist, this is exactly when to add them. |
| "100% coverage is overkill" | Nobody said 100%. But 0% is negligence. Test the important paths. |
| "Mocks are faster" | Mocks are faster to run and slower to maintain. They test assumptions, not behavior. |
| "I already wrote the implementation" | Sunk cost. Tests written after pass immediately and prove nothing about the original bug. |
| "The test is too hard to write" | Hard-to-test code signals a design problem. Simplify the interface, not the test. |
| "I need to understand the code first" | Write the test to express what you expect. The test IS your understanding, made executable. |
| "This is a prototype / throwaway" | Prototypes become production code. Every time. The test costs 5 minutes now vs. hours debugging later. |
| "The deadline is too tight for tests" | The deadline is too tight to debug without tests. Tests catch bugs at write time, not in production under deadline pressure. |
