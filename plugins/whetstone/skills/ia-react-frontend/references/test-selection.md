# Test selection

## Testing (Vitest + React Testing Library)

- **Component tests**: Vitest + RTL, co-located `*.test.tsx`. Default for React components.
- **Hook tests**: `renderHook` + `act`, co-located `*.test.ts`
- **Unit tests**: Vitest for pure functions, utilities, services
- **E2E**: Playwright for user flows and critical paths
- **Query priority**: `getByRole` > `getByLabelText` > `getByPlaceholderText` > `getByText` > `getByTestId`
- Mock API services and external providers; render child components real for integration confidence
- One behavior per test with AAA structure. Name: `should <behavior> when <condition>`
- Use `userEvent` over `fireEvent` for realistic interactions
- `findBy*` for async elements, `waitFor` after state-triggering actions
- `vi.clearAllMocks()` in `beforeEach`. Recreate state per test.
- Timing (`useLayoutEffect` vs `useEffect` report races), engine fidelity (jsdom/happy-dom vs a real browser engine for parser/layout-dependent behavior), interaction-mode pitfalls (`userEvent` delay, fake-timer incompatibility, `fireEvent` vs `userEvent` tradeoffs), and runner/environment failures (`vmThreads` OOM, happy-dom swallowing `console.*`): see [testing.md](./testing.md)
General testing discipline (anti-patterns, rationalization resistance): see the `ia-writing-tests` skill.
See [testing patterns and examples](./testing.md) for component, hook, and mocking examples.
See [e2e testing](./e2e-testing.md) for Playwright patterns.
