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

## Component TypeScript

- Extend native elements with `ComponentPropsWithoutRef<'button'>`, add custom props via intersection
- Use `React.ReactNode` for children, `React.ReactElement` for single element, render prop `(data: T) => ReactNode`
- Discriminated unions for variant props -- TypeScript narrows automatically in branches
- Generic components: `<T>` with `keyof T` for column keys, `T extends { id: string }` for constraints
- Event types: `React.MouseEvent<HTMLButtonElement>`, `FormEvent<HTMLFormElement>`, `ChangeEvent<HTMLInputElement>`
- `as const` for custom hook tuple returns
- `useRef<HTMLInputElement>(null)` for DOM (use `?.`), `useRef<number>(0)` for mutable values
- Explicit `useState<User | null>(null)` for unions/null
- useReducer actions as discriminated unions: `{ type: 'set'; payload: number } | { type: 'reset' }`
- useContext null guard: throw in custom `useX()` hook if context is null

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

## Concurrency & Race Classes

Five race classes survive type-checking and unit tests -- hunt each one during review (cleanup/cancellation mechanics: Effect rules above):

| Class | Production signal | Fix |
|-------|-------------------|-----|
| Lifecycle cleanup gap | "state update on unmounted component" warnings, leaks under rapid navigation | Return cleanup from every effect that registers a listener/timer/observer |
| Remount-timing mistake | Async callback mutates state/DOM after route change/unmount (`fetch().then(setData)` resolves post-navigation) | Cancel per the cancellation hierarchy |
| Boolean-as-state for non-binary UI | Contradictory combos (`isLoading: true, error: Error`) | State constant (`'idle' \| 'loading' \| 'success' \| 'error'`) + transition function; invalid states unreachable |
| Stale promise/timer, no cancel path | Promise chain or `setTimeout` holds `setState` after the component moved on | Bind every async op to a cancel mechanism; test the cleanup path |
| Per-element handlers on large lists | N closures/subscriptions per row, stale-closure bugs on rapid re-renders | Delegate: one parent handler + `event.target.closest(...)` when >~50 items or frequent updates |
| Gate keyed on a child's success-only callback | Parent's submit stays locked behind "still loading, try again in a moment" copy that never resolves; only a page reload escapes | Report failures up (`onLoadError`) as well as successes, and split the flag into loading / loaded / failed -- a boolean cannot carry a terminal state. Keep the action blocked in both if proceeding on unknown data is unsafe; the fix is honest copy plus a real in-place retry, not unblocking |
| `inert` toggled from a blur-managed flag | First `Tab` *inside* the subtree sends focus to `<body>`; the next `Tab` restarts at the top of the document and skips the (now inert) subtree entirely | React maps `onBlur` to native `focusout`, which fires on intra-subtree moves, and `focusin`/`focusout` are `DiscreteEventPriority` -- React commits `inert` synchronously *between* the two events, landing it on the already-focused incoming control. Stand down only when focus truly leaves: `if (e.currentTarget.contains(e.relatedTarget)) return;` |

**Focus-ownership rules:**
- Never toggle `inert` on a subtree that currently holds focus. The blunt version has no guard at all -- a scroll-driven `inert={!isVisible}` on a sticky bar, drawer, or collapsing panel strands the user on a control that is invisible, inert, and unactivatable. Hand focus to the equivalent visible control before hiding, and pass `focus({ preventScroll: true })` when the handoff fires from a scroll handler, or `focus()` scrolls its target into view and fights the scroll the user is performing. If the handoff target carries the same focus listeners that feed the guard, `focus()` arms the flag as a side effect of doing its job and the subtree never goes inert again -- make the handoff symmetric (two effects guarding opposite values of one flag) rather than adding an exception to the guard. `aria-hidden` without `inert` fixes double announcement but leaves the duplicate tab stops. Assert on what the user can *do* (does the handler fire, where does `Tab` go), not on `document.activeElement` -- Chromium resolves the unfocusing steps lazily and it reads back inconsistently
- A blur-managed "focus is inside" flag cannot be cleared by a blur that never fires. Headless popover primitives restore focus to the element that *opened* the content on close; when the popover is anchored to an input with no trigger element, that restore no-ops, the library preventDefaults the focus-scope restore, and focus lands on `document.body` -- the input never receives another `blur`, so the flag sticks `true` for the component's lifetime and anything gated on it (a "re-seed local text from `props.value`" effect, for instance) is silently dead. Clear it explicitly in the select handler and on close when `document.activeElement` is not the input. The same design usually adds `onOpenAutoFocus={e => e.preventDefault()}` to avoid stealing typing focus, which leaves the content pointer-only: no trigger to Tab to and no auto-focus in. Add an explicit affordance plus `aria-haspopup`/`aria-expanded`. Browser-dependent -- Chromium and Firefox blur the input on `mousedown`, Safari does not, so "works on my machine" from Safari proves nothing

## State Management

```
Local UI state       → useState, useReducer
Shared client state  → Zustand (simple) | Redux Toolkit (complex)
Atomic/granular      → Jotai
Server/remote data   → React Query (TanStack Query)
URL state            → nuqs, router search params
Form state           → React Hook Form
```

**Key patterns:**
- Zustand: `create<State>()(devtools(persist((set) => ({...}))))` -- use slices for scale, selective subscriptions to prevent re-renders
- React Query: query keys factory (`['users', 'detail', id] as const`), `staleTime`/`gcTime`, optimistic updates with `onMutate`/`onError` rollback
- React Query `isError` means *a fetch failed*, not *there is no data* -- a failed refetch sets `status: 'error'` while retaining the last successful payload, so the usual `isLoading ? spinner : isError ? errorPanel : content` ladder routes a working, fully cached list into the error panel. The defaults compose into it: `refetchOnMount: true` + `staleTime: 0` refetch on every mount, `retry: false` makes one blip terminal, and `gcTime: 5min` keeps the cache alive across a modal's unmount/remount. Gate the branch on data-absence -- `isLoadingError` (`isError && !hasData`), or `isError && derived.length === 0` when the suite mocks the hook and leaves `isLoadingError` undefined. Audit the side effects with it: `useEffect(() => { if (isError) toast(...) }, [isError])` fires over the live list too
- The mirror case has the same tell: under `retry: false` a first load that fails leaves `data` `undefined` forever, so a branch gated on `data !== undefined` folds *failed* into *pending* and renders "Loading…" permanently. Whether it is recoverable is decided by mount topology, not by open/closed state -- a component rendered unconditionally inside a ref-driven popup is mounted for the life of the page, so `refetchOnMount` never fires again. Any remedy that adds a branch on `isError` must itself be gated on data-absence, or it re-introduces the previous bullet
- Never duplicate server data (React Query) in a client store (Zustand)
- Colocate state close to where it's used

## Performance

**Critical -- eliminate waterfalls:**
- `Promise.all()` for independent async operations
- Move `await` into branches where actually needed
- Suspense boundaries to stream slow content

**Critical -- bundle size:**
- Import directly from modules, avoid barrel files (`index.ts` re-exports)
- `next/dynamic` or `React.lazy()` for heavy components
- Defer third-party scripts (analytics, logging) until after hydration
- Preload on hover/focus for perceived speed
- `content-visibility: auto` + `contain-intrinsic-size` on long lists -- skips off-screen layout/paint

**Re-render optimization:**
- Never define a component inside another component. Each parent render creates a new function identity, and React compares element *types* to decide whether to update or replace -- a new type means the whole subtree unmounts and remounts, so local state is lost, effects re-run, and DOM nodes are recreated. Symptoms are behavioral, not slow: an input loses focus on every keystroke, animations restart, scroll position resets. Hoist the component to module scope and pass what it needed via props. The React Compiler does not save this one -- the type identity changes before memoization applies
- Derive state during render, not in effects
- Subscribe to derived booleans, not raw objects (`state.items.length > 0` not `state.items`)
- Functional setState for stable callbacks: `setCount(c => c + 1)`
- Lazy state init: `useState(() => expensiveComputation())`
- `useTransition` for non-urgent updates (search filtering)
- `useDeferredValue` for expensive derived UI
- Don't subscribe to searchParams/state read only in callbacks -- read on demand
- Use ternary (`condition ? <A /> : <B />`), not `&&` for conditionals
- `React.memo` only for expensive subtrees with stable props
- Hoist static JSX outside components

**React Compiler** (React 19): auto-memoizes -- write idiomatic React, remove manual `useMemo`/`useCallback`/`memo`. Enable via `reactCompiler: true` in next.config (non-framework: `babel-plugin-react-compiler`). Keep components pure.

## React 19

- **ref as prop** -- `forwardRef` deprecated. Accept `ref?: React.Ref<HTMLElement>` as regular prop
- **useActionState** -- replaces `useFormState`: `const [state, formAction, isPending] = useActionState(action, initialState)`
- **use()** -- unwrap Promise or Context during render (not in callbacks/effects). Enables conditional context reads
- **useOptimistic** -- `const [optimistic, addOptimistic] = useOptimistic(state, mergeFn)` for instant UI feedback
- **useFormStatus** -- `const { pending } = useFormStatus()` in child of `<form action={...}>`
- **Server Components** -- default in App Router. Async, access DB/secrets directly. No hooks, no event handlers
- **Server Actions** -- `'use server'` directive. Validate inputs (Zod), `revalidateTag`/`revalidatePath` after mutations. **Server Actions are public endpoints** -- always verify auth/authz inside each action, not just in middleware or layout guards
- **`<Activity mode='visible'|'hidden'>`** -- preserves state/DOM for toggled components (experimental)

## Next.js App Router

**File conventions:** `page.tsx` (route UI), `layout.tsx` (shared wrapper), `template.tsx` (re-mounted on navigation, unlike layout), `loading.tsx` (Suspense), `error.tsx` (error boundary), `not-found.tsx` (404), `default.tsx` (parallel route fallback), `route.ts` (API endpoint)

**Rendering modes:** Server Components (default) | Client (`'use client'`) | Static (build) | Dynamic (request) | Streaming (progressive)

**Decision:** Server Component unless it needs hooks, event handlers, or browser APIs. Split: server parent + client child. Isolate interactive components as `'use client'` leaf components -- keep server components static with no global state or event handlers.

**Server → client boundary:** pass only the fields a client component actually uses, not whole ORM rows or fetch objects. Every prop crossing the `'use client'` boundary is serialized into the payload, so a 50-field `user` object read for one field still ships all 50.

**Client-only state that drives first paint** (theme, locale, feature flag, auth hint): reading `localStorage` during render breaks SSR, and reading it in `useEffect` paints the default first, so the correct value arrives one frame later as a visible flash. Set the value on the document with a small synchronous inline script that runs before hydration -- typically writing a `class` or `data-` attribute on `<html>` that CSS already keys on. The script is developer-authored and must never interpolate user, request, or database data; it is the one place `dangerouslySetInnerHTML` is warranted, and only for a literal string.

**Routing patterns:**
- Route groups `(name)` -- organize without affecting URL
- Parallel routes `@slot` -- independent loading states in same layout
- Intercepting routes `(.)` -- modal overlays with full-page fallback

**Caching:**
- `fetch(url, { cache: 'force-cache' })` -- static
- `fetch(url, { next: { revalidate: 60 } })` -- ISR
- `fetch(url, { cache: 'no-store' })` -- dynamic
- Tag-based: `fetch(url, { next: { tags: ['products'] } })` then `revalidateTag('products')`

**Data fetching:**
- Fetch in Server Components where data is used
- Use Suspense boundaries for slow queries
- `React.cache()` for per-request dedup
- `generateStaticParams` for static generation
- `generateMetadata` for dynamic SEO
- Static metadata with `title: { default: 'App', template: '%s | App' }` for cascading page titles
- `after()` for non-blocking side effects (logging, analytics) -- runs after response is sent
- Hoist static I/O (fonts, config) to module level -- runs once, not per request
- Never hold request-scoped or user data in module-level mutable state -- server renders run concurrently in one process, so shared module state leaks across requests (one user's data surfacing in another's response). Hoist only immutable static I/O; keep request data local to the render tree (pass as props)

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
- Timing (`useLayoutEffect` vs `useEffect` report races), engine fidelity (jsdom/happy-dom vs a real browser engine for parser/layout-dependent behavior), and interaction-mode pitfalls (`userEvent` delay, fake-timer incompatibility, `fireEvent` vs `userEvent` tradeoffs): see [testing.md](./references/testing.md)
General testing discipline (anti-patterns, rationalization resistance): see the `ia-writing-tests` skill.
See [testing patterns and examples](./references/testing.md) for component, hook, and mocking examples.
See [e2e testing](./references/e2e-testing.md) for Playwright patterns.

## Tailwind Integration

For Tailwind v4 configuration, utility patterns, dark mode, and component variants, see the `ia-tailwind-css` skill.

**Class sorting in JSX**: keep Tailwind classes in canonical order (enforce via `eslint-plugin-better-tailwindcss`).

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
