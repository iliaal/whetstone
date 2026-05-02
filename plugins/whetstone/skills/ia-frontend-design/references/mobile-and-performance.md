# Mobile Collapse and Performance Guardrails

Load this reference for any layout using asymmetry, rotations, animation, or complex grid variants. Missing mobile collapse and missing performance guards are the top two reported AI UI defects after missing interactive states.

## Mobile Collapse Mandate

Any layout using asymmetry, rotations, negative-margin overlaps, or `md:` / `lg:` grid variations above 768px MUST declare an explicit mobile fallback. Mobile is not "just narrower" — it's a different layout mode.

- **Collapse to single-column below `md:`**: reset widths to `w-full`, reset `grid-cols-*` to 1, apply `px-4 py-8` for baseline spacing.
- **Remove rotations and negative overlaps on mobile**: `md:-translate-y-8` and `md:rotate-2` should not carry over; they collide with touch targets at small widths.
- **Minimum 44×44px touch targets**: hit areas below that fail WCAG 2.5.5 and cause fat-finger misses. Apply `min-h-[44px] min-w-[44px]` on every button, link, and interactive icon.
- **No horizontal overflow**: wrap the outermost layout container with `overflow-x-hidden w-full max-w-full` to prevent off-canvas animations or oversized grids from creating a horizontal scrollbar.

Test the narrowest breakpoint before considering an asymmetric layout done.

## Performance Guardrails

These are architecture-level errors, not style preferences. Violating any one of them causes continuous GPU repaints, mobile jank, or z-index collisions that are hard to undo later.

- **Grain and noise filters** apply exclusively to fixed, `pointer-events-none` pseudo-elements (e.g., `fixed inset-0 z-50 pointer-events-none`). Never on scrolling containers — the filter re-rasterizes every scroll frame and collapses mobile performance.
- **Animate only `transform` and `opacity`**. Never animate `top`, `left`, `width`, or `height` — these trigger layout on every frame and cannot be GPU-composited.
- **Z-index restraint**: reserve `z-*` values for systemic layer contexts (sticky navbars, modals, overlays). Never spam arbitrary `z-10` or `z-50` to push elements around — that's what stacking contexts and DOM order are for.
- **Perpetual animations must be memoized and isolated** in their own tiny Client Component (`React.memo`-wrapped). An infinite loop inside a large layout causes the parent to re-render every frame.
