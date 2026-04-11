---
name: frontend-design
description: >-
  Visual design and aesthetic direction for frontend interfaces. Use when
  building web pages, landing pages, dashboards, or applications where visual
  identity matters. For React patterns and testing, use react-frontend.
paths: "**/*.html,**/*.css,**/*.tsx,**/*.jsx"
---

# Frontend Design

Read the user's frontend requirements: a component, page, application, or interface to build. Note context about purpose, audience, or technical constraints.

## Context Detection

Before designing, assess the existing design environment. Count design signals in the project: design tokens/CSS variables, component library (shadcn, MUI, Ant), CSS framework config (Tailwind, styled-components), font imports, color system, animation patterns, spacing scale.

- **4+ signals** = Existing system. Match it. Do not impose new aesthetics -- extend what's there.
- **1-3 signals** = Partial system. Blend: respect existing choices, fill gaps with this skill's guidance.
- **0 signals** = Greenfield. Apply the full Design Philosophy below.

When in doubt, check `package.json`, `tailwind.config.*`, global CSS files, and existing components before deciding.

## Design Philosophy (Write First, Code Second)

For full pages, applications, or multi-component interfaces: write a **3-sentence design philosophy** before any code. This forces a coherent aesthetic direction and prevents generic output.

1. **Sentence 1 -- Intent**: What emotional response should this interface provoke? (Not "clean and modern" -- that's every AI default. Be specific: "controlled tension between density and breathing room" or "the quiet confidence of a well-bound book.")
2. **Sentence 2 -- Signature**: What single visual choice makes this unmistakable? (A typeface, a color relationship, a spatial pattern, a motion behavior.)
3. **Sentence 3 -- Constraint**: What will this design deliberately NOT do? (The constraint shapes the identity as much as the choices.)

Write the philosophy as a comment or in conversation before implementation begins. The philosophy constrains implementation without being prescriptive -- it's a compass, not a blueprint.

For small components or quick additions to existing interfaces, skip the philosophy and match the surrounding design system.

## Design Thinking

With the philosophy written, commit to the specifics:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work -- the key is intentionality, not intensity.

Before importing any third-party library (framer-motion, lucide-react, zustand, etc.), check `package.json`. If the package is missing, output the install command before the code. Never assume a library exists.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography** — choose fonts with character:
  - **Font selection**: avoid Inter, Roboto, Arial, system fonts. Use `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`, or context-appropriate serifs. Pair a display font with a refined body font.
  - **Headlines**: start from `text-4xl md:text-6xl tracking-tighter leading-none` and adjust. AI defaults are undersized and timid — lack presence.
  - **Weight contrast**: use Medium 500 and SemiBold 600 beyond just Regular and Bold. Tighten letter-spacing, reduce line-height.
  - **Body text**: limit to ~65 characters wide, increase line-height.
  - **Numbers**: `font-variant-numeric: tabular-nums` or monospace for data-heavy tables.
  - **Orphaned words**: fix with `text-wrap: balance`.
- **Color & Theme**: Commit to a cohesive palette. Max one accent color, saturation below 80%. Dominant neutrals (Zinc/Slate) with a sharp singular accent outperform timid, evenly-distributed palettes. Use CSS variables for consistency. Tint all grays consistently (warm OR cool, never both). Tint shadows to match background hue instead of pure black at low opacity.
- **Motion**: Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions. Use spring physics over linear easing. Animate exclusively via `transform` and `opacity` (GPU-composited). Use `IntersectionObserver` for scroll reveals. See [motion-patterns.md](./references/motion-patterns.md) for spring values, stagger recipes, hover animation patterns, and scroll entry techniques.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density. Use CSS Grid over complex flexbox percentage math (`w-[calc(33%-1rem)]`). Contain layouts with `max-w-7xl mx-auto` or similar. Use `min-h-[100dvh]` instead of `h-screen` (prevents iOS Safari viewport jumping). Bottom padding often needs to be slightly larger than top for optical balance. **Anti-card overuse:** at high density (dashboards, data-heavy UIs), don't wrap everything in card containers (border + shadow + white). Use `border-t`, `divide-y`, or negative space to separate content instead. Cards should exist only when elevation communicates hierarchy. **Bento grid archetypes:** when building dashboard grids, use named patterns: Intelligent List (filterable, sortable data), Command Input (search/action bar), Live Status (real-time metrics), Wide Data Stream (timeline/activity feed), Contextual UI (details panel that responds to selection).
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

### Performance Guardrails

These are architecture-level errors, not style preferences. Violating any one of them causes continuous GPU repaints, mobile jank, or z-index collisions that are hard to undo later.

- **Grain and noise filters** apply exclusively to fixed, `pointer-events-none` pseudo-elements (e.g., `fixed inset-0 z-50 pointer-events-none`). Never on scrolling containers — the filter re-rasterizes every scroll frame and collapses mobile performance.
- **Animate only `transform` and `opacity`**. Never animate `top`, `left`, `width`, or `height` — these trigger layout on every frame and cannot be GPU-composited.
- **Z-index restraint**: reserve `z-*` values for systemic layer contexts (sticky navbars, modals, overlays). Never spam arbitrary `z-10` or `z-50` to push elements around — that's what stacking contexts and DOM order are for.
- **Perpetual animations must be memoized and isolated** in their own tiny Client Component (`React.memo`-wrapped). An infinite loop inside a large layout causes the parent to re-render every frame.

### Server / Client Component Safety (Next.js App Router)

For Next.js App Router projects, load [rsc-client-boundaries.md](./references/rsc-client-boundaries.md) — it covers the Server vs Client decision table, leaf-component isolation rules, the `useMotionValue` vs `useState` rule for continuous animations, and the common failure modes (`'use client'` hoisting, context providers in Server Components, async data inside motion trees).

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

### Design Variance Parameters

To prevent aesthetic convergence across generations, calibrate these three parameters (1-10 scale, default 5) before designing. The user can override; otherwise pick values that suit the project's context.

- **DESIGN_VARIANCE** (1=conservative, 10=experimental): How far to push visual choices from conventional patterns. Low for corporate dashboards, high for creative portfolios.
- **MOTION_INTENSITY** (1=static, 10=cinematic): How much animation and transition to include. Low for data-heavy tools, high for marketing pages.
- **VISUAL_DENSITY** (1=spacious, 10=packed): Content density vs. negative space. Low for landing pages, high for dashboards and admin panels.

State the chosen values in the design philosophy comment. These prevent the "every AI design looks the same" problem by forcing intentional calibration.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

### Banned AI Design Patterns

These patterns are hallmarks of AI-generated interfaces. Avoid them. See [banned-ai-patterns.md](./references/banned-ai-patterns.md) for the comprehensive list covering layout, color, typography, decoration, interaction, and content patterns.

Top 6 AI slop patterns (highest detection priority):

1. **Purple/violet gradients** (`#6366f1`--`#8b5cf6`) -- the single most recognizable AI color signature. Pick a different palette entirely.
2. **3-column feature grid with icons in circles** -- the most common AI layout. Use asymmetric layouts, split screens, or bento grids instead.
3. **Icons in colored circles as decoration** -- primary-color background circle + white icon is default AI component styling. Use inline icons or subtle background tints.
4. **Center-heavy layouts** (>60% `text-align: center`) -- left-align body text; reserve centering for headings and CTAs only.
5. **Uniform bubbly border-radius** (>80% of elements sharing the same value >=16px) -- vary by purpose: sharp for data, rounded for interactive, pill for tags.
6. **Generic hero copy** ("Welcome to X", "Unlock the power of...", "Revolutionize your...") -- write specific, benefit-driven copy tied to the actual product.

See [banned-ai-patterns.md](./references/banned-ai-patterns.md) for the full catalog beyond these top 6.

## Verify

- Design philosophy written before code (for full pages)
- No forbidden AI patterns present in output
- Dependency check done before any new library import
- Code renders without errors in the browser
- No `outline: none` without replacement focus indicator
- All four interactive states present (loading, empty, error, tactile press) for any interactive component
- No animation of `top`/`left`/`width`/`height` (transform/opacity only)
- Grain/noise filters only on fixed `pointer-events-none` layers
- Interactive/animated components isolated as leaf `'use client'` components (Next.js App Router)

## References

- [Motion patterns](./references/motion-patterns.md) -- spring values, stagger recipes, hover animations, scroll entry, performance rules
- [Creative arsenal](./references/creative-arsenal.md) -- navigation, layout, card, typography, and micro-interaction patterns
- [Redesigning existing interfaces](./references/redesigning-existing.md) -- audit-first upgrade workflow for existing projects
- [Redesign audit checklist](./references/redesign-audit.md) -- 60+ checks across typography, color, layout, interactivity, content, and component patterns
- [RSC / Client Component boundaries](./references/rsc-client-boundaries.md) -- Next.js App Router rules for Server vs Client Components, continuous animations, and provider isolation
- For WCAG accessibility audits, use the `accessibility-tester` agent
