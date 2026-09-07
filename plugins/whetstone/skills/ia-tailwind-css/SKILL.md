---
name: ia-tailwind-css
class: language
description: >-
  Tailwind CSS v4 patterns: CSS-first config, utility classes, component
  variants, v3 migration. Use when styling with Tailwind, configuring
  @theme tokens, using tailwind-variants/CVA, migrating v3 to v4, or
  fixing Tailwind styles and dark mode.
paths: "**/*.css,**/tailwind.config.*,**/*.tsx,**/*.jsx,**/*.html,**/*.vue,**/*.blade.php"
---

# Tailwind CSS v4

**Verify before implementing**: For v4-specific syntax (`@theme`, `@variant`, CSS-first config), look up current docs via Context7 (`query-docs`) before writing code. Tailwind v4 changed significantly from v3 and training data may be stale.

## Working rules

- Keep utility names as complete source literals and confirm their files are scanned.
- Use shared design tokens and one consistent visibility mechanism.
- Inspect generated CSS after source/configuration changes; JSX strings alone do not prove utilities exist.
- Test scrolling, overlays, and focus behavior in a browser when layout containment changes.

## Coding Rules

- **`gap` over `space-x`/`space-y`** -- gap handles wrapping; space-* breaks on wrap
- **`size-*` over `w-* h-*`** -- for equal dimensions
- **`min-h-dvh` over `min-h-screen`** -- dvh accounts for mobile browser chrome
- **Opacity modifier** (`bg-black/50`) -- `*-opacity-*` utilities are removed in v4
- **Design tokens over arbitrary values** -- check `@theme` before using `[#hex]`
- **Never construct classes dynamically** -- `text-${color}-500` won't be detected; use complete class names
- **`@utility` over `@apply` with `@layer`** -- `@apply` on `@layer` classes fails in v4
- **Parent padding over last-child margin** -- use padding on containers instead of bottom margins on the last child
- **`overflow-x-auto` makes a scroll container on BOTH axes** -- the utility emits only `overflow-x: auto`, but CSS Overflow 3 computes a `visible` value on the other axis to `auto` once either axis is scrollable, so a wrapper added purely to allow horizontal panning silently clips or scrolls whatever overflows it vertically: a non-portalled dropdown, popover, tooltip, custom select, or focus ring. jsdom does no layout, so no unit test catches it -- enumerate every component rendered inside the new wrapper and confirm each overlay-ish one escapes it. Portaling is opt-in, not automatic: Radix exposes it as a separate `*.Portal` part wrapping `*.Content`, so read the component rather than assuming a library handles it. Same computed-value rule read backwards: before blaming a page-level scrollbar, walk every ancestor's `overflow` and name the element that actually scrolls
- **Never express visibility as the native `hidden` attribute plus a display utility** -- the two resolve in opposite directions across versions. v4's Preflight ships `[hidden]:where(:not([hidden="until-found"])) { display: none !important }`, so the attribute wins and an element expected to be visible stays hidden; on v3, or wherever Preflight is disabled or not loaded, the author-origin utility (`block`, `flex`, `grid`) beats the UA-origin `[hidden]` rule regardless of specificity and the element stays on screen with `hidden` set. Toggle one mechanism: `clsx(base, open ? 'block' : 'hidden')`. Neither direction is visible to jsdom's `toBeInTheDocument` -- only `toBeVisible` or a real browser engine catches it


## Verify

- Build passes with zero errors (`npm run build` or equivalent)
- No v3 class names remain in changed files (check with `@tailwindcss/upgrade --dry-run` if available)
- No conflicting classes on the same element


## References

- [Component patterns](./references/component-patterns.md) -- tailwind-variants slots, CVA, compound components
- [Layout patterns](./references/layout-patterns.md) -- grid areas, container queries, z-index management, fluid typography

## Task-specific references

Read the relevant reference before implementing or reviewing the matching behavior:

- For theme tokens, build configuration, version migration, dark mode, or missing styles: [configuration-and-migration.md](./references/configuration-and-migration.md).
- For class merging, scanning paths, variants, or lint integration: [class-generation-and-composition.md](./references/class-generation-and-composition.md).

Existing specialized references, when the corresponding topic applies:

- [v3-to-v4-migration.md](./references/v3-to-v4-migration.md).
