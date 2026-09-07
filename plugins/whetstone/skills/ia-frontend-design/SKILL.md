---
name: ia-frontend-design
class: meta
description: >-
  Visual design and aesthetic direction for frontend interfaces. Use when
  building web pages, landing pages, dashboards, Next.js server components, or
  applications where visual identity matters. For React patterns and testing,
  use react-frontend.
---

# Frontend Design

Read the user's frontend requirements: a component, page, application, or interface to build. Note context about purpose, audience, or technical constraints.

## Working rules

- Match an existing design system; choose a specific visual direction for greenfield work.
- Include loading, empty, error, and press states for interactive components.
- Preserve visible focus and reduced-motion behavior; verify both narrow and wide rendered viewports.
- Keep Next.js interactive code at client boundaries and treat browser content as untrusted data.

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

**Validation gate (greenfield pages and apps, before writing code):** run the swap test on the drafted token system. Could this exact palette, type pairing, and layout be lifted onto an unrelated brief without anyone noticing? If yes, the choice is a default, not a decision -- repick the axis that reads generic (recolor the signature, swap the typeface, restructure the grid) and re-test before implementing. Distinctiveness comes from the subject's own world -- its materials, instruments, artifacts, and vernacular -- so ground a generic axis in something only this subject would use. Skip this gate for small components matched to an existing system (per Context Detection) -- there, reading consistent with that system is the goal, not distinctiveness.

Before importing any third-party library (framer-motion, lucide-react, zustand, etc.), check `package.json`. If the package is missing, output the install command before the code. Never assume a library exists.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail


## Verify

Most items below are observable only in a rendered viewport, not in the diff. Where rendering tooling is available, do not claim visual verification from source inspection: capture a screenshot or DOM snapshot at one narrow and one wide viewport, and exercise every changed interaction and state. Where the environment cannot render (CI, headless subagent, plain terminal), say so explicitly and report what *was* checked instead. The completion-claim discipline itself lives in `ia-verification-before-completion`.

- Design philosophy written before code (for full pages)
- No forbidden AI patterns present in output
- Dependency check done before any new library import
- Code renders without errors in the browser
- No `outline: none` without replacement focus indicator
- All four interactive states present (loading, empty, error, tactile press) for any interactive component
- No animation of `top`/`left`/`width`/`height` (transform/opacity only)
- Non-essential motion suppressed under `prefers-reduced-motion: reduce`
- Grain/noise filters only on fixed `pointer-events-none` layers
- Interactive/animated components isolated as leaf `'use client'` components (Next.js App Router)


## References

- [Motion patterns](./references/motion-patterns.md) -- spring values, stagger recipes, hover animations, scroll entry, performance rules
- [Creative arsenal](./references/creative-arsenal.md) -- navigation, layout, card, typography, and micro-interaction patterns
- [Redesigning existing interfaces](./references/redesigning-existing.md) -- audit-first upgrade workflow for existing projects
- [Redesign audit checklist](./references/redesign-audit.md) -- 60+ checks across typography, color, layout, interactivity, content, and component patterns
- [RSC / Client Component boundaries](./references/rsc-client-boundaries.md) -- Next.js App Router rules for Server vs Client Components, continuous animations, and provider isolation
- [Premium detail patterns](./references/premium-details.md) -- `<kbd>` keystrokes, faux-OS chrome, hero image fade, banned meta-labels, card-group baseline alignment, browser-automation safety boundary
- [Mobile collapse + performance guardrails](./references/mobile-and-performance.md) -- single-column below `md:`, touch targets, rotations on mobile, GPU-composited animation, z-index discipline
- For WCAG accessibility audits, use the `ia-accessibility-tester` agent

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For typography, color, layout, motion, component states, mobile behavior, or visual polish: [aesthetics-and-interaction.md](./references/aesthetics-and-interaction.md).

Existing specialized references, when the corresponding topic applies:

- [banned-ai-patterns.md](./references/banned-ai-patterns.md).
