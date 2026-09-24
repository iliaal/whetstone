# Rendering and framework patterns

## Performance

**Critical: eliminate waterfalls:**
- `Promise.all()` for independent async operations
- Move `await` into branches where actually needed
- Suspense boundaries to stream slow content

**Critical: bundle size:**
- Import directly from modules, avoid barrel files (`index.ts` re-exports)
- `next/dynamic` or `React.lazy()` for heavy components
- Defer third-party scripts (analytics, logging) until after hydration
- Preload on hover/focus for perceived speed
- `content-visibility: auto` + `contain-intrinsic-size` on long lists skips off-screen layout/paint

**Re-render optimization:**
- Never define a component inside another component. Each parent render creates a new function identity, and React compares element *types* to decide whether to update or replace: a new type means the whole subtree unmounts and remounts, so local state is lost, effects re-run, and DOM nodes are recreated. Symptoms are behavioral, not slow: an input loses focus on every keystroke, animations restart, scroll position resets. Hoist the component to module scope and pass what it needed via props. The React Compiler does not save this one; the type identity changes before memoization applies
- Derive state during render, not in effects
- Subscribe to derived booleans, not raw objects (`state.items.length > 0` not `state.items`)
- Functional setState for stable callbacks: `setCount(c => c + 1)`
- Lazy state init: `useState(() => expensiveComputation())`
- `useTransition` for non-urgent updates (search filtering)
- `useDeferredValue` for expensive derived UI
- Don't subscribe to searchParams/state read only in callbacks; read on demand
- Use ternary (`condition ? <A /> : <B />`), not `&&` for conditionals
- `React.memo` only for expensive subtrees with stable props
- Hoist static JSX outside components

**React Compiler** (React 19): auto-memoizes, so write idiomatic React and remove manual `useMemo`/`useCallback`/`memo`. Enable via `reactCompiler: true` in next.config (non-framework: `babel-plugin-react-compiler`). Keep components pure.


## React 19

- **ref as prop**: `forwardRef` deprecated. Accept `ref?: React.Ref<HTMLElement>` as regular prop
- **useActionState**: replaces `useFormState`: `const [state, formAction, isPending] = useActionState(action, initialState)`
- **use()**: unwrap Promise or Context during render (not in callbacks/effects). Enables conditional context reads
- **useOptimistic**: `const [optimistic, addOptimistic] = useOptimistic(state, mergeFn)` for instant UI feedback
- **useFormStatus**: `const { pending } = useFormStatus()` in child of `<form action={...}>`
- **Server Components**: default in App Router. Async, access DB/secrets directly. No hooks, no event handlers
- **Server Actions**: `'use server'` directive. Validate inputs (Zod), `revalidateTag`/`revalidatePath` after mutations. **Server Actions are public endpoints**; always verify auth/authz inside each action, not just in middleware or layout guards
- **`<Activity mode='visible'|'hidden'>`** preserves state/DOM for toggled components (experimental)


## Next.js App Router

**File conventions:** `page.tsx` (route UI), `layout.tsx` (shared wrapper), `template.tsx` (re-mounted on navigation, unlike layout), `loading.tsx` (Suspense), `error.tsx` (error boundary), `not-found.tsx` (404), `default.tsx` (parallel route fallback), `route.ts` (API endpoint)

**Rendering modes:** Server Components (default) | Client (`'use client'`) | Static (build) | Dynamic (request) | Streaming (progressive)

**Decision:** Server Component unless it needs hooks, event handlers, or browser APIs. Split: server parent + client child. Isolate interactive components as `'use client'` leaf components; keep server components static with no global state or event handlers.

**Server → client boundary:** pass only the fields a client component actually uses, not whole ORM rows or fetch objects. Every prop crossing the `'use client'` boundary is serialized into the payload, so a 50-field `user` object read for one field still ships all 50.

**Client-only state that drives first paint** (theme, locale, feature flag, auth hint): reading `localStorage` during render breaks SSR, and reading it in `useEffect` paints the default first, so the correct value arrives one frame later as a visible flash. Set the value on the document with a small synchronous inline script that runs before hydration, typically writing a `class` or `data-` attribute on `<html>` that CSS already keys on. The script is developer-authored and must never interpolate user, request, or database data; it is the one place `dangerouslySetInnerHTML` is warranted, and only for a literal string.

**Routing patterns:**
- Route groups `(name)`: organize without affecting URL
- Parallel routes `@slot`: independent loading states in same layout
- Intercepting routes `(.)`: modal overlays with full-page fallback

**Caching:**
- `fetch(url, { cache: 'force-cache' })`: static
- `fetch(url, { next: { revalidate: 60 } })`: ISR
- `fetch(url, { cache: 'no-store' })`: dynamic
- Tag-based: `fetch(url, { next: { tags: ['products'] } })` then `revalidateTag('products')`

**Data fetching:**
- Fetch in Server Components where data is used
- Use Suspense boundaries for slow queries
- `React.cache()` for per-request dedup
- `generateStaticParams` for static generation
- `generateMetadata` for dynamic SEO
- Static metadata with `title: { default: 'App', template: '%s | App' }` for cascading page titles
- `after()` for non-blocking side effects (logging, analytics); runs after response is sent
- Hoist static I/O (fonts, config) to module level; runs once, not per request
- Never hold request-scoped or user data in module-level mutable state: server renders run concurrently in one process, so shared module state leaks across requests (one user's data surfacing in another's response). Hoist only immutable static I/O; keep request data local to the render tree (pass as props)


## Tailwind Integration

For Tailwind v4 configuration, utility patterns, dark mode, and component variants, see [tailwind.md](./tailwind.md).

**Class sorting in JSX**: keep Tailwind classes in canonical order (enforce via `eslint-plugin-better-tailwindcss`).
