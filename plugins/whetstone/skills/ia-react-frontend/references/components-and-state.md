# Components, state, and interaction

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
- **A parameter type whose properties are all optional is a weak type, and a mismatched argument fails to compile rather than passing `undefined`.** TypeScript requires the argument to share at least one property with a weak type, so `(record: { newField?: boolean })` rejects a generated type that does not yet carry `newField` with `TS2559: Type 'X' has no properties in common with type 'Y'`. Intersect with the base type instead (`T & { newField?: boolean }`) -- the shim then deletes cleanly once the field lands upstream


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
- The mirror case has the same tell: under `retry: false` a first load that fails leaves `data` `undefined` forever, so a branch gated on `data !== undefined` folds *failed* into *pending* and renders "Loading…" permanently. Whether it is recoverable is decided by mount topology, not by open/closed state -- a component rendered unconditionally inside a ref-driven popup is mounted for the life of the page, so `refetchOnMount` never fires again. Any remedy that adds a branch on `isError` must itself be gated on data-absence, or it re-introduces the previous bullet. Enumerate all four states before writing either gate -- `isLoading` (first load, no data yet), `isFetching` (any fetch in flight, including a background refetch over a warm cache), `isError` (last fetch failed, cache may still be present), and loaded-and-genuinely-empty -- and state the action in each: `!isFetching` misses the error state, `!isFetching && !isError` mishandles a background refetch of a legitimately empty result. The write path has the same shape, inverted: a fail-closed save gate keyed on `isError` blocks a valid submit whenever cached data is present
- A mutate-scoped `onSuccess` survives an unmount that the mutation itself caused, so "the success toast is dropped on promote/archive/delete" is usually a false finding. The mutation dispatches success on the microtask after the hook-level `onSuccess` await resolves, while query-observer notifications -- the ones that re-render the list and unmount the row -- flush on a zero-delay timer; that is an ordering guarantee, not a race. The documented "callbacks do not fire on unmount" caveat describes a different unmount (navigation, closing a drawer). Read the scheduler and run a known-bad control (remove the observer before dispatch) before accepting the finding
- Never duplicate server data (React Query) in a client store (Zustand)
- Colocate state close to where it's used
