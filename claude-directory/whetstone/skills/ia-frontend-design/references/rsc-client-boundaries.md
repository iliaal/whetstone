# Server / Client Component Safety (Next.js App Router)

Load when the target project uses Next.js App Router (check `package.json` for `next` ≥ 13 and the presence of an `app/` directory). These rules prevent the most common RSC-related runtime failures and mobile performance collapses.

## Hard rules

- Global state (`useState`, `useReducer`, context providers) works ONLY in Client Components. Server Components that try to use hooks fail at build time with an opaque error.
- Wrap providers in a dedicated `'use client'` component; import that wrapper from Server Components.
- Keep interactive and animated code in focused `'use client'` components. A client boundary adds its imported module dependencies to the client bundle, not server-rendered children passed in by a Server Component parent.
- For magnetic hover, mouse-tracking, or any continuous animation tied to input, use Framer Motion's `useMotionValue` + `useTransform`, NEVER `useState`. `useState` re-renders the component on every mouse move and causes catastrophic mobile performance collapse.
- For `staggerChildren` (Framer Motion), the parent `variants` and the children must live in the same Client Component subtree. If data is fetched asynchronously, pass it as props into a centralized parent motion wrapper rather than fetching inside the motion tree.

## Decision table: Server Component or Client Component?

| Component shape | Boundary |
|-----------------|----------|
| Static layout, no hooks, no event handlers | Server Component |
| Reads from database or calls server APIs on mount | Server Component (use `async` function component) |
| Uses `useState` / `useEffect` / `useReducer` / `useContext` | Client Component (`'use client'` at top) |
| Listens to DOM events (`onClick`, `onChange`) | Client Component |
| Uses `window` / `document` / `localStorage` | Client Component |
| Uses Framer Motion with `whileHover`, `animate`, `useMotionValue` | Client Component |
| Wraps children in a context provider | Client Component wrapper; children may be server-rendered |

When in doubt, default to Server Component. A Client Component cannot import and execute a server-only component. A Server Component can pass server-rendered JSX through a Client Component's `children` or other props: render `<ClientModal><ServerCart /></ClientModal>` in the server parent, with the client modal rendering its `children` prop.

## Common failure modes

1. **`'use client'` at the top of a page file**: adds the page's imported dependencies to the client bundle. Fix: move the boundary down to the interactive component and pass server-rendered content from a server parent where appropriate.
2. **Magnetic hover with `useState`**: the component re-renders on every `mousemove`, dropping frame rate below 10 fps on mid-range mobile. Fix: `useMotionValue` + `useTransform`; these update DOM values outside the React render cycle.
3. **Context provider in a Server Component**: build error. Fix: extract the provider into a `'use client'` wrapper component and import that.
4. **Asynchronous data fetching inside a motion-wrapped component**: staggered animation breaks because children mount at different times. Fix: fetch in the parent (Server Component), pass data as props to the motion wrapper (Client Component).
