---
name: frontend-design
description: >-
  Create distinctive, production-grade frontend interfaces with real working
  code. Use when building web pages, UI components, landing pages, dashboards,
  or applications with HTML/CSS/JS/React. Avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

Create distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

Read the user's frontend requirements: a component, page, application, or interface to build. Note context about purpose, audience, or technical constraints.

## Design Philosophy (Write First, Code Second)

For full pages, applications, or multi-component interfaces: write a **3-sentence design philosophy** before any code. This forces a coherent aesthetic direction and prevents generic output.

1. **Sentence 1 — Intent**: What emotional response should this interface provoke? (Not "clean and modern" — that's every AI default. Be specific: "controlled tension between density and breathing room" or "the quiet confidence of a well-bound book.")
2. **Sentence 2 — Signature**: What single visual choice makes this unmistakable? (A typeface, a color relationship, a spatial pattern, a motion behavior.)
3. **Sentence 3 — Constraint**: What will this design deliberately NOT do? (The constraint shapes the identity as much as the choices.)

Write the philosophy as a comment or in conversation before implementation begins. The philosophy constrains implementation without being prescriptive — it's a compass, not a blueprint.

For small components or quick additions to existing interfaces, skip the philosophy and match the surrounding design system.

## Design Thinking

With the philosophy written, commit to the specifics:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts with character. Avoid Inter, Roboto, Arial, system fonts. Use distinctive choices like `Geist`, `Outfit`, `Cabinet Grotesk`, `Satoshi`, or context-appropriate serifs. Pair a display font with a refined body font. Headlines: tighten letter-spacing, reduce line-height, use weight contrast (Medium 500, SemiBold 600) beyond just Regular/Bold. Body text: limit to ~65 characters wide, increase line-height. Use `font-variant-numeric: tabular-nums` or monospace for data-heavy numbers. Fix orphaned words with `text-wrap: balance`.
- **Color & Theme**: Commit to a cohesive palette. Max one accent color, saturation below 80%. Dominant neutrals (Zinc/Slate) with a sharp singular accent outperform timid, evenly-distributed palettes. Use CSS variables for consistency. Tint all grays consistently (warm OR cool, never both). Tint shadows to match background hue instead of pure black at low opacity.
- **Motion**: Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (`animation-delay`) creates more delight than scattered micro-interactions. Use spring physics (`type: "spring", stiffness: 100, damping: 20`) over linear easing. Animate exclusively via `transform` and `opacity` — never `top`, `left`, `width`, `height`. Apply grain/noise filters only to fixed, `pointer-events-none` pseudo-elements, never to scrolling containers.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density. Use CSS Grid over complex flexbox percentage math (`w-[calc(33%-1rem)]`). Contain layouts with `max-w-7xl mx-auto` or similar. Use `min-h-[100dvh]` instead of `h-screen` (prevents iOS Safari viewport jumping). Bottom padding often needs to be slightly larger than top for optical balance.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, and grain overlays. Use radial gradients, noise overlays, or mesh gradients over standard linear 45-degree fades. Use reliable placeholders like `https://picsum.photos/seed/{name}/800/600` when real assets are unavailable.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

## Forbidden AI Patterns

These are the telltale signs of AI-generated design. Avoid them:

**Visual**: No pure `#000000` (use off-black, Zinc-950, charcoal). No neon outer glows or default `box-shadow` glows. No oversaturated accents. No purple/blue "AI gradient" aesthetic. No excessive gradient text on large headers. No custom mouse cursors. No arbitrary `z-50` or `z-9999` — use z-index only for systemic layers (navbars, modals, overlays).

**Typography**: No Inter font. No oversized H1s that scream — control hierarchy with weight and color, not just scale. No serif fonts on dashboards or software UIs. No all-caps subheaders everywhere — try sentence case, lowercase italics, or small-caps.

**Layout**: No centered hero sections when the design calls for asymmetry — use split-screen, left-aligned content, or offset compositions. No "three equal cards in a row" feature sections — use zig-zag, asymmetric grid, horizontal scroll, or masonry instead. No random dark sections breaking a light-mode page (or vice versa) — commit to a tone or use subtle shade shifts.

**Content (the "Jane Doe" effect)**: No generic names ("John Doe", "Sarah Chen"). No fake round numbers (`99.99%`, `50%`) — use organic data (`47.2%`, `$87.50`, `+1 (312) 847-1928`). No startup slop names ("Acme", "Nexus", "SmartFlow") — invent contextual, believable brands. No AI copywriting cliches ("Elevate", "Seamless", "Unleash", "Next-Gen", "Delve", "Game-changer"). No Lorem Ipsum. No exclamation marks in success messages. No "Oops!" error messages — be direct. Use sentence case for headers, not Title Case On Every Header.

**Components**: No generic card look everywhere (border + shadow + white) — cards should exist only when elevation communicates hierarchy. No Lucide/Feather icons exclusively (try Phosphor, Heroicons, or custom). No rocketship for "Launch", shield for "Security" — replace cliche metaphors. No accordion FAQ — use side-by-side lists or inline progressive disclosure. No 3-card carousel testimonials with dots. No avatar circles exclusively — try squircles or rounded squares. No broken Unsplash links — use picsum.photos or SVG avatars. Standardize icon stroke widths. Always include a favicon.

**Interactivity**: Implement full interaction cycles, not just the success state. Provide skeleton loaders (not circular spinners), composed empty states, inline error messages (not `window.alert()`), and tactile press feedback (`scale-[0.98]` or `translateY(1px)` on `:active`). Add visible focus rings for keyboard navigation. Add `scroll-behavior: smooth` for anchor navigation.

## Redesigning Existing Interfaces

When upgrading an existing project, audit first, then fix in this priority order (maximum visual impact, minimum risk):

1. **Font swap** — biggest instant improvement, lowest risk
2. **Color palette cleanup** — remove clashing or oversaturated colors, enforce one accent
3. **Hover and active states** — makes the interface feel alive
4. **Layout and spacing** — proper grid, max-width container, consistent padding
5. **Replace generic components** — swap cliche patterns for modern alternatives
6. **Add loading, empty, and error states** — makes it feel finished
7. **Polish typography scale and spacing** — the premium final touch

Work with the existing tech stack. Do not migrate frameworks or styling libraries. Keep changes reviewable and focused — small, targeted improvements over big rewrites. Before importing any new library, check `package.json` first. If the project uses Tailwind, check the version (v3 vs v4) before modifying config.
