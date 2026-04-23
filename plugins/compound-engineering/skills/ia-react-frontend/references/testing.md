# Testing React (Vitest + RTL)

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
