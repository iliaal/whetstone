# Aesthetics and interaction

## Frontend Aesthetics Guidelines

Focus on:
- **Typography** — choose fonts with character:
  - **Font selection**: avoid Inter, Roboto, Arial, system fonts. Use `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`, or context-appropriate serifs. Pair a display font with a refined body font.
  - **Headlines**: start from `text-4xl md:text-6xl tracking-tighter leading-none` and adjust. AI defaults are undersized and timid — lack presence.
  - **H1 iron rule (2-3 lines max)**: every hero H1 must render in 2-3 lines, never 4-6. The fix is always wider container + smaller font, not the reverse. Minimum container: `max-w-5xl` (wider for longer headlines); adjust font with `clamp(3rem, 5vw, 5.5rem)` so it scales down instead of wrapping. A 6-line heading wall is a catastrophic failure, not a design choice.
  - **Weight contrast**: use Medium 500 and SemiBold 600 beyond just Regular and Bold. Tighten letter-spacing, reduce line-height.
  - **Body text**: limit to ~65 characters wide, increase line-height.
  - **Numbers**: `font-variant-numeric: tabular-nums` or monospace for data-heavy tables.
  - **Orphaned words**: fix with `text-wrap: balance`.
- **Color & Theme**: Commit to a cohesive palette. Max one accent color, saturation below 80%. Dominant neutrals (Zinc/Slate) with a sharp singular accent outperform timid, evenly-distributed palettes -- that structure is right, but check the realization against Composite Looks in [banned-ai-patterns.md](./banned-ai-patterns.md), since the two default accents on near-black are themselves a tell. Use CSS variables for consistency. Tint all grays consistently (warm OR cool, never both). Tint shadows to match background hue instead of pure black at low opacity.
- **Motion**: Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions. Use spring physics over linear easing. Animate exclusively via `transform` and `opacity` (GPU-composited). Use `IntersectionObserver` for scroll reveals. Gate every non-essential animation behind `prefers-reduced-motion: no-preference`, or cut duration to near-zero under `reduce` -- staggered page-load reveals and scroll entrances are exactly what the setting exists to suppress. See [motion-patterns.md](./motion-patterns.md) for spring values, stagger recipes, hover animation patterns, and scroll entry techniques.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density. Use CSS Grid over complex flexbox percentage math (`w-[calc(33%-1rem)]`). Contain layouts with `max-w-7xl mx-auto` or similar. Use `min-h-[100dvh]` instead of `h-screen` (prevents iOS Safari viewport jumping). Bottom padding often needs to be slightly larger than top for optical balance. **Anti-card overuse:** at high density (dashboards, data-heavy UIs), don't wrap everything in card containers (border + shadow + white). Use `border-t`, `divide-y`, or negative space to separate content instead. Cards should exist only when elevation communicates hierarchy. **Bento grid archetypes:** when building dashboard grids, use named patterns: Intelligent List (filterable, sortable data), Command Input (search/action bar), Live Status (real-time metrics), Wide Data Stream (timeline/activity feed), Contextual UI (details panel that responds to selection). Apply `grid-flow-dense` to prevent empty/dead cells — see [banned-ai-patterns.md](./banned-ai-patterns.md) for the rule.
- **Backgrounds & visual details** — create atmosphere and depth, not solid colors:
  - **Textures**: apply gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, or grain overlays.
  - **Gradients**: prefer radial, noise-overlay, or mesh gradients over standard linear 45-degree fades.
  - **Double-bezel pattern** for premium depth: outer wrapper with `ring-1` hairline + padding + large radius; inner content with its own background + `shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]` + derived inner radius (`rounded-[calc(2rem-0.375rem)]`).
  - **Glassmorphism refraction**: add `border-white/10` inner borders.
  - **Placeholder images**: `https://picsum.photos/seed/{name}/800/600` when real assets unavailable.

**Utility Copy for Product UI**: Product UI copy prioritizes orientation, status, and action over promise, mood, or brand voice. If a sentence could appear in a homepage hero or ad, rewrite it until it sounds like product UI. Litmus check: if an operator scans only headings, labels, and numbers, can they understand the page immediately? Error messages: be direct ("Connection failed. Please try again."), not performative ("Oops! Something went wrong!"). No exclamation marks in success messages -- be confident, not loud.

### Mandatory Interactive States

LLMs default to "static successful state" output. Every interactive component MUST ship with all four state treatments — static success alone is an incomplete implementation:

- **Loading** — skeletal loaders that match the real layout's shape and sizing. No generic circular spinners.
- **Empty** — a composed empty state that shows how to populate the data, not the string "No data" or a bare icon.
- **Error** — inline error reporting next to the affected field or component. Never `window.alert()`, never a generic toast for form-level errors.
- **Tactile press** — on `:active`, apply `-translate-y-[1px]` or `scale-[0.98]` so clicks feel like a physical push, not a color flicker.

Missing states are the most common reported AI UI defect. Generating only the success state is incomplete work, not a stretch goal.

### Mobile Collapse + Performance Guardrails

For any layout using asymmetry, rotations, heavy animation, or complex grid variants, load [mobile-and-performance.md](./mobile-and-performance.md) — mobile collapse rules (single-column below `md:`, 44×44 touch targets, no horizontal overflow, rotations stripped on mobile) and performance guards (grain filters only on fixed pseudo-elements, transform/opacity-only animation, z-index discipline, memoized perpetual animations). These are the top two reported AI UI defects after missing interactive states.

### Server / Client Component Safety (Next.js App Router)

For Next.js App Router projects, load [rsc-client-boundaries.md](./rsc-client-boundaries.md) — it covers the Server vs Client decision table, leaf-component isolation rules, the `useMotionValue` vs `useState` rule for continuous animations, and the common failure modes (`'use client'` hoisting, context providers in Server Components, async data inside motion trees).

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

### Design Variance Parameters

To prevent aesthetic convergence across generations, calibrate these three parameters (1-10 scale, default 5) before designing. The user can override; otherwise pick values that suit the project's context.

- **DESIGN_VARIANCE** (1=conservative, 10=experimental): How far to push visual choices from conventional patterns. Low for corporate dashboards, high for creative portfolios.
- **MOTION_INTENSITY** (1=static, 10=cinematic): How much animation and transition to include. Low for data-heavy tools, high for marketing pages.
- **VISUAL_DENSITY** (1=spacious, 10=packed): Content density vs. negative space. Low for landing pages, high for dashboards and admin panels.

State the chosen values in the design philosophy comment. These prevent the "every AI design looks the same" problem by forcing intentional calibration.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

### Banned AI Design Patterns

Top detection priorities: purple/violet gradients, 3-column icon grids, icon-in-circle decorations, center-heavy layouts, uniform bubbly border-radius, generic hero copy. See [banned-ai-patterns.md](./banned-ai-patterns.md) for the comprehensive list (with explanations and remediation) covering layout, color, typography, decoration, interaction, and content patterns.

### Premium Detail Patterns + Browser Verification

For polish-level UI patterns (`<kbd>` keystrokes, faux-OS chrome, hero image fade, banned meta-labels, card-group baseline alignment) and for the "browser content is untrusted data" safety boundary during browser-automation verification, load [premium-details.md](./premium-details.md).
