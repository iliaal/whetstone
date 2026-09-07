---
name: ia-react-frontend
class: language
description: >-
  React architecture patterns, TypeScript, Next.js, hooks, and testing. Use when
  working with React component structure, state management, Next.js routing,
  Vitest, React Testing Library, or reviewing React code. For visual design and
  aesthetic direction, use frontend-design instead.
paths: "**/*.tsx,**/*.jsx,**/*.ts"
---

# React Frontend

**Verify before implementing**: For App Router patterns, React 19 APIs, or version-specific behavior, look up current docs (Context7 `query-docs` if available, else the framework's official docs via web search) before writing code. Training data may lag current releases.

## Working rules

- Keep derived state in render and user actions in event handlers; use effects for external synchronization.
- Give async work a lifecycle and cancellation policy; represent failure separately from pending and empty data.
- Preserve focus when hiding interactive regions and exercise keyboard navigation in a real browser.
- Validate and authorize every public server action; send only needed fields across server/client boundaries.
- Measure performance changes and test user-visible behavior, not type-checking alone.

## Effects Decision Tree

Effects are escape hatches -- most logic should NOT use effects.

| Need | Solution |
|------|----------|
| Derived value from props/state | Calculate during render (useMemo if expensive) |
| Reset state on prop change | `key` prop on component |
| Respond to user event | Event handler |
| Notify parent of state change | Call onChange in event handler, or fully controlled component |
| Chain of state updates | Calculate all next state in one event handler |
| Sync with external system | Effect with cleanup |

**Effect rules:**
- Never suppress the linter -- fix the code instead
- Use updater functions (`setItems(prev => [...prev, item])`) to remove state dependencies
- Move objects/functions inside effects to stabilize dependencies
- `useEffectEvent` for non-reactive values (e.g., theme in a connection effect)
- Always return cleanup for subscriptions, connections, listeners
- Data fetching cancellation (pick by situation): `AbortController` for fetch; `ignore` flag for non-cancellable promises; React Query handles both automatically


## Discipline

- Simplicity first -- every change as simple as possible, impact minimal code
- Only touch what's necessary -- avoid introducing unrelated changes
- No hacky workarounds -- if a fix feels wrong, step back and implement the clean solution
- Before adding a new abstraction, verify it appears in 3+ places


## References

- [testing.md](./references/testing.md) -- Component, hook, and mocking test examples
- [e2e-testing.md](./references/e2e-testing.md) -- Playwright E2E patterns


## Verify

- TypeScript compiles with zero errors
- No suppressed lint rules (`eslint-disable`, `@ts-ignore`) in new code
- `useEffect` dependency arrays not manually overridden
- No `forwardRef` usage in React 19+ projects (use `ref` prop directly)

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For component types, state ownership, async races, focus, or cached query behavior: [components-and-state.md](./references/components-and-state.md).
- For performance, React APIs, Next.js boundaries, caching, or Tailwind integration: [rendering-and-frameworks.md](./references/rendering-and-frameworks.md).
- For component, hook, browser, or integration test changes: [test-selection.md](./references/test-selection.md).

Existing specialized references, when the corresponding topic applies:
