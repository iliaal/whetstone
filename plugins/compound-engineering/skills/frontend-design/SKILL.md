---
name: frontend-design
description: >-
  Visual design and aesthetic direction for new frontend interfaces. Use when
  building web pages, landing pages, dashboards, or applications where visual
  identity matters. Produces working code with distinctive aesthetics. For React
  architecture patterns, hooks, and testing, use react-frontend instead.
---

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

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

## Forbidden AI Patterns

These are the telltale signs of AI-generated design. Avoid them:

**Visual**: No pure `#000000` (use off-black, Zinc-950, charcoal). No neon outer glows or default `box-shadow` glows. No oversaturated accents. No purple/blue "AI gradient" aesthetic. No excessive gradient text on large headers. No custom mouse cursors. No arbitrary `z-50` or `z-9999` -- use z-index only for systemic layers (navbars, modals, overlays).

**Typography**: No Inter font. No oversized H1s that scream -- control hierarchy with weight and color, not just scale. No serif fonts on dashboards or software UIs. No all-caps subheaders everywhere -- try eyebrow tags instead (`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium`), sentence case, lowercase italics, or small-caps.

**Layout**: No centered hero sections when the design calls for asymmetry -- use split-screen, left-aligned content, or offset compositions. No "three equal cards in a row" feature sections -- use zig-zag, asymmetric grid, horizontal scroll, or masonry instead. No random dark sections breaking a light-mode page (or vice versa) -- commit to a tone or use subtle shade shifts.

**Content (the "Jane Doe" effect)**: No generic names ("John Doe", "Sarah Chen"). No fake round numbers (`99.99%`, `50%`) -- use organic data (`47.2%`, `$87.50`, `+1 (312) 847-1928`). No startup slop names ("Acme", "Nexus", "SmartFlow") -- invent contextual, believable brands. No AI copywriting cliches ("Elevate", "Seamless", "Unleash", "Next-Gen", "Delve", "Game-changer"). No Lorem Ipsum. No exclamation marks in success messages. No "Oops!" error messages -- be direct. Use sentence case for headers, not Title Case On Every Header. No emojis in code, markup, or text content -- replace with icons or SVG primitives.

**Forms**: Label above the input. Helper text optional but present in markup. Error message below input. Use `gap-2` for input stacking.

**Components**: No generic card look everywhere (border + shadow + white) -- cards should exist only when elevation communicates hierarchy. No Lucide/Feather icons exclusively (try Phosphor, Heroicons, or custom). No rocketship for "Launch", shield for "Security" -- replace cliche metaphors. No accordion FAQ -- use side-by-side lists or inline progressive disclosure. No 3-card carousel testimonials with dots. No avatar circles exclusively -- try squircles or rounded squares. No broken Unsplash links -- use picsum.photos or SVG avatars. Standardize icon stroke widths. Always include a favicon.

**Interactivity**: Implement full interaction cycles, not just the success state. Provide skeleton loaders (not circular spinners), composed empty states, inline error messages (not `window.alert()`), and tactile press feedback (`scale-[0.98]` or `translateY(1px)` on `:active`). For CTA buttons with icons, wrap the icon in its own circular container (`w-8 h-8 rounded-full bg-black/5`) with independent hover kinetics (`group-hover:translate-x-1 scale-105`). Add visible focus rings for keyboard navigation. Add `scroll-behavior: smooth` for anchor navigation.

**Content Register**: Match copy to context. Dashboards and operational tools need utility copy -- section headings say what the area is, not what the brand aspires to be. If a sentence could appear in a homepage hero, rewrite it until it sounds like product UI. Hero sections on landing pages use marketing copy.

**Hero Construction**: Full-bleed heroes run edge-to-edge; constrain only the inner text/action column. Use `calc(100svh - var(--header-height))` to account for persistent UI chrome. Test: if the first viewport still works after removing the image, the image is too weak.

## Animation Library Guidance

Default to Framer Motion for UI interactions (buttons, modals, lists, bento cards). Use GSAP or Three.js only for isolated full-page scroll storytelling or canvas/WebGL backgrounds -- never mix them with Framer Motion in the same component tree. Wrap GSAP/Three.js in strict `useEffect` cleanup blocks.

## Verify

- Design philosophy written before code (for full pages)
- No forbidden AI patterns present in output
- Dependency check done before any new library import
- Code renders without errors in the browser
- No `outline: none` without replacement focus indicator

## References

- [Creative arsenal](./references/creative-arsenal.md) -- navigation, layout, card, typography, and micro-interaction patterns
- [Redesigning existing interfaces](./references/redesigning-existing.md) -- audit-first upgrade workflow for existing projects
