---
name: frontend-design
description: >-
  Visual design and aesthetic direction for frontend interfaces. Use when
  building web pages, landing pages, dashboards, or applications where visual
  identity matters. For React patterns and testing, use react-frontend.
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
- **Typography**: Choose fonts with character. Avoid Inter, Roboto, Arial, system fonts. Use distinctive choices like `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`, or context-appropriate serifs. Pair a display font with a refined body font. Headlines: tighten letter-spacing, reduce line-height, use weight contrast (Medium 500, SemiBold 600) beyond just Regular/Bold. Body text: limit to ~65 characters wide, increase line-height. Use `font-variant-numeric: tabular-nums` or monospace for data-heavy numbers. Fix orphaned words with `text-wrap: balance`.
- **Color & Theme**: Commit to a cohesive palette. Max one accent color, saturation below 80%. Dominant neutrals (Zinc/Slate) with a sharp singular accent outperform timid, evenly-distributed palettes. Use CSS variables for consistency. Tint all grays consistently (warm OR cool, never both). Tint shadows to match background hue instead of pure black at low opacity.
- **Motion**: Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (`animation-delay: calc(var(--index) * 80ms)` using a CSS index variable) creates more delight than scattered micro-interactions. Use spring physics (`type: "spring", stiffness: 100, damping: 20`) over linear easing. Animate exclusively via `transform` and `opacity` -- never `top`, `left`, `width`, `height`. Scroll entry: combine Y translation + blur + opacity (`translate-y-16 blur-md opacity-0` resolving to `translate-y-0 blur-0 opacity-100`) for premium depth. Use `IntersectionObserver` for scroll reveals -- never `window.addEventListener('scroll')` (causes continuous reflows). Never use `useState` for continuous/magnetic hover animations -- use `useMotionValue` + `useTransform` exclusively for frame-rate-sensitive motion. Memoize perpetual motion components (`React.memo`) and isolate them as leaf `'use client'` components. Apply grain/noise filters only to fixed, `pointer-events-none` pseudo-elements, never to scrolling containers.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density. Use CSS Grid over complex flexbox percentage math (`w-[calc(33%-1rem)]`). Contain layouts with `max-w-7xl mx-auto` or similar. Use `min-h-[100dvh]` instead of `h-screen` (prevents iOS Safari viewport jumping). Bottom padding often needs to be slightly larger than top for optical balance. **Anti-card overuse:** at high density (dashboards, data-heavy UIs), don't wrap everything in card containers (border + shadow + white). Use `border-t`, `divide-y`, or negative space to separate content instead. Cards should exist only when elevation communicates hierarchy. **Bento grid archetypes:** when building dashboard grids, use named patterns: Intelligent List (filterable, sortable data), Command Input (search/action bar), Live Status (real-time metrics), Wide Data Stream (timeline/activity feed), Contextual UI (details panel that responds to selection).
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, and grain overlays. Use radial gradients, noise overlays, or mesh gradients over standard linear 45-degree fades. For premium depth, use the double-bezel pattern: outer wrapper with `ring-1` hairline + padding + large radius, inner content with its own background + `shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]` + derived inner radius (`rounded-[calc(2rem-0.375rem)]`). Add glassmorphism inner borders with `border-white/10` for refraction effects. Use reliable placeholders like `https://picsum.photos/seed/{name}/800/600` when real assets are unavailable.

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

Core offenders:
- **Purple-to-blue gradient hero** -- the default AI aesthetic. Pick a different palette entirely.
- **Centered hero + three equal-width cards + centered CTA** -- the most common AI layout. Use asymmetric layouts, split screens, or bento grids instead.
- **Uniform rounded corners everywhere** -- vary border-radius by component purpose (sharp for data, rounded for interactive, pill for tags)
- **Generic placeholder copy** -- no "John Doe", "Acme Corp", "Lorem ipsum". Use realistic, messy data ("47.2%", "+1 (312) 847-1928")

## Verify

- Design philosophy written before code (for full pages)
- No forbidden AI patterns present in output
- Dependency check done before any new library import
- Code renders without errors in the browser
- No `outline: none` without replacement focus indicator

## References

- [Creative arsenal](./references/creative-arsenal.md) -- navigation, layout, card, typography, and micro-interaction patterns
- [Redesigning existing interfaces](./references/redesigning-existing.md) -- audit-first upgrade workflow for existing projects
