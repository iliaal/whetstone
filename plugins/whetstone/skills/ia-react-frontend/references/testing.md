# Testing React (Vitest + RTL)

> When to read: when adding or fixing component tests with Vitest + React Testing Library — setup, queries, user-event, async assertions, mocking.

## Setup

Vitest config: `environment: 'jsdom'`, `globals: true`, `setupFiles` pointing to a file that imports `@testing-library/jest-dom/vitest`. Use `@vitejs/plugin-react` and mirror path aliases from `tsconfig.json`.

## Component Test

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('@/api/client');

describe('UserForm', () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it('should submit valid form data', async () => {
    const onSubmit = vi.fn();
    render(<UserForm onSubmit={onSubmit} />);

    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ email: 'test@example.com' }),
      );
    });
  });
});
```

## Hook Test

```typescript
import { renderHook, act } from '@testing-library/react';

it('should debounce value updates', () => {
  vi.useFakeTimers();
  const { result, rerender } = renderHook(
    ({ value }) => useDebounce(value, 300),
    { initialProps: { value: 'initial' } },
  );
  rerender({ value: 'updated' });
  expect(result.current).toBe('initial');
  act(() => { vi.advanceTimersByTime(300); });
  expect(result.current).toBe('updated');
  vi.useRealTimers();
});
```

## Mocking Patterns

```typescript
// Service mock -- mock the module, not the transport layer
vi.mock('@/server-api/me/me.service', () => ({
  MeService: { retrieveMe: vi.fn() },
}));

// QueryClient wrapper for components using TanStack Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};
render(<Component />, { wrapper: createWrapper() });
```

## Test Classification

| Type | Tool | Target | File pattern |
|------|------|--------|-------------|
| Unit | Vitest | Pure functions, utilities, services | Co-located `*.test.ts` |
| Component | Vitest + RTL | React components | Co-located `*.test.tsx` |
| Hook | Vitest + RTL | Custom hooks | Co-located `*.test.ts` |
| E2E | Playwright | User flows, critical paths | Separate `e2e/` directory |

## Running Tests

```bash
npx vitest                         # Watch mode
npx vitest run                     # Single run (CI)
npx vitest run src/features/       # Test specific directory
npx vitest --coverage              # Coverage report
```

## Timing, Fidelity, and Interaction-Mode Pitfalls

Report from `useLayoutEffect`, not `useEffect`, in a child stub whose report feeds a gate under test. A `useEffect` report lands a tick late: `render()` returns, the test queries and clicks before the report's `setState` has committed, and the click reads the pre-report state. RTL flushes layout effects *and their state updates* synchronously inside `render()`'s `act`. Awaiting a settled-state text papers over it only where there is a positive DOM signal -- a gate-*unsatisfiable* case has none, so it flakes or silently asserts the wrong branch.

jsdom and happy-dom are not evidence about a browser-rendered artifact. Where the behavior is decided by a parser, layout, or print engine -- a serialized DOM re-parsed by Chromium, `inert`, `postMessage` across an opaque origin -- execute it in the *sink's* engine (Playwright/Chromium against the repo's own dependency) and carry a known-bad control in the same batch. jsdom does not enforce the radio-group invariant on parse and does not enforce the opaque-origin `targetOrigin` check, so the natural regression test passes while the bug ships. Engine fidelity and path fidelity are separate requirements: load the committed artifact verbatim and drive it through its real entry point, because a hand-rebuilt reconstruction can invert the result while looking like executed evidence.

Use `userEvent.setup({ delay: null })` in component tests. A bare `setup()` inserts a `setTimeout(0)` macrotask between every simulated keystroke and pointer event -- pure idle time in a test DOM, and the single largest source of a slow suite's tail.

`vi.useFakeTimers()` freezes `findBy`/`waitFor` polling **and** `userEvent` (v14 awaits real timers internally), so the two do not compose. Under fake timers drive with `fireEvent` plus an explicit settle -- `await act(async () => { await vi.runOnlyPendingTimersAsync(); })`, or `advanceTimersByTimeAsync(N)` for a debounce window -- and assert both sides of the boundary: not-called at N-1ms, called once at Nms. A one-sided assertion passes against an eager implementation.

Fill forms with one `fireEvent.change` per field when typing is not the behavior under test. `user.type` into a `mode: 'onChange'` react-hook-form field pays a full-schema re-validation per keystroke, and it focuses the input, which mounts whatever popover is attached (a date field re-renders a 42-day calendar grid on every keystroke). Keep one keystroke-level test per form for validation coverage and convert the rest. `fireEvent` cannot drive components that need a real pointer sequence (a combobox opening on input click, a menu opening on `pointerdown`) -- those keep `userEvent`.
