---
name: tailwind-css
description: >-
  Tailwind CSS v4 patterns: CSS-first config, utility classes, component
  variants, v3 migration. Use when styling with Tailwind, configuring
  @theme tokens, using tailwind-variants/CVA, migrating v3 to v4, or
  fixing Tailwind styles and dark mode.
---

# Tailwind CSS v4

## CSS-First Configuration

v4 eliminates `tailwind.config.ts`. All configuration lives in CSS.

| Directive | Purpose |
|-----------|---------|
| `@import "tailwindcss"` | Entry point (replaces `@tailwind base/components/utilities`) |
| `@theme { }` | Define/extend design tokens -- auto-generates utility classes |
| `@theme inline { }` | Map CSS variables to Tailwind utilities without generating new vars |
| `@theme static { }` | Define tokens that don't generate utilities |
| `@utility name { }` | Create custom utilities (replaces `@layer components` + `@apply`) |
| `@custom-variant name (selector)` | Define custom variants |

```css
@import "tailwindcss";

@theme {
  --color-brand: oklch(0.72 0.11 178);
  --font-display: "Inter", sans-serif;
  --animate-fade-in: fade-in 0.2s ease-out;
  @keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
}

@custom-variant dark (&:where(.dark, .dark *));
```

Tokens defined with `@theme` become utilities automatically: `--color-brand` produces `bg-brand`, `text-brand`, `border-brand`. Define z-index as tokens (`--z-modal: 50`) and reference via `z-(--z-modal)` instead of arbitrary `z-50`.

**CSS Modules**: when using `.module.css` with Tailwind v4, add `@reference "#tailwind";` at the top of the module file to enable theme token access inside the module.

**Animations (tw-animate-css)**: use `animate-in`/`animate-out` base classes combined with effect classes (`fade-in`, `slide-in-from-top`). Decimal spacing gotcha: use bracket notation `[0.625rem]` instead of fractional values like `2.5`.

## v3 to v4 Breaking Changes

| v3 | v4 | Notes |
|----|-----|-------|
| `tailwind.config.ts` | `@theme` in CSS | Delete config file |
| `@tailwind base/components/utilities` | `@import "tailwindcss"` | Single import |
| `darkMode: "class"` | `@custom-variant dark (...)` | CSS-only |
| `bg-gradient-to-r` | `bg-linear-to-r` | Also: `bg-radial`, `bg-conic` |
| `bg-opacity-60` | `bg-red-500/60` | All `*-opacity-*` removed |
| `rounded-sm` | `rounded-xs` | Radius scale shifted down one step |
| `rounded` | `rounded-sm` | (run `@tailwindcss/upgrade` codemod) |
| `rounded-md` (6px) | `rounded` (6px) | |
| `rounded-lg` | `rounded-md` | |
| `rounded-xl` | `rounded-lg` | |
| `min-h-screen` | `min-h-dvh` | `dvh` handles mobile browser chrome |
| `w-6 h-6` | `size-6` | Size shorthand for equal w/h |
| `space-x-4` | `gap-4` | Gap handles flex/grid wrapping correctly |
| `text-base leading-7` | `text-base/7` | Inline line-height modifier |
| `require("tailwindcss-animate")` | `tw-animate-css` | CSS-only animations |
| `forwardRef` | `ref` as prop | React 19 change (not Tailwind, but co-occurs) |

## Coding Rules

- **`gap` over `space-x`/`space-y`** -- gap handles wrapping; space-* breaks on wrap
- **`size-*` over `w-* h-*`** -- for equal dimensions
- **`min-h-dvh` over `min-h-screen`** -- dvh accounts for mobile browser chrome
- **Opacity modifier** (`bg-black/50`) -- `*-opacity-*` utilities are removed in v4
- **Design tokens over arbitrary values** -- check `@theme` before using `[#hex]`
- **Never construct classes dynamically** -- `text-${color}-500` won't be detected; use complete class names
- **`@utility` over `@apply` with `@layer`** -- `@apply` on `@layer` classes fails in v4
- **Parent padding over last-child margin** -- use padding on containers instead of bottom margins on the last child

## ESLint Integration

Use `eslint-plugin-better-tailwindcss` for automated class validation:
- `no-conflicting-classes` -- catches `text-red-500 text-blue-500`
- `no-unknown-classes` -- flags typos
- `enforce-canonical-classes` -- normalizes shorthand
- `no-duplicate-classes` -- removes redundant entries
- `no-deprecated-classes` -- catches v3 classes removed in v4

## Class Merging

Use `cn()` combining `clsx` + `tailwind-merge` for conditional/dynamic classes. Use plain strings for static `className` attributes.

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

```typescript
// Static: plain string
<button className="rounded-lg px-4 py-2 font-medium bg-blue-600">

// Conditional: use cn()
<button className={cn("rounded-lg px-4 py-2", isActive ? "bg-blue-600" : "bg-gray-700")} />
```

## Component Variants

Use `tailwind-variants` (`tv()`) for type-safe variant components. Alternative: `class-variance-authority` (`cva()`).

```typescript
import { tv } from "tailwind-variants";
const button = tv({
  base: "rounded-lg px-4 py-2 font-medium transition-colors",
  variants: {
    color: { primary: "bg-blue-600 text-white", secondary: "bg-gray-200 text-gray-800" },
    size: { sm: "text-sm px-3 py-1", md: "text-base", lg: "text-lg px-6 py-3" },
  },
  defaultVariants: { color: "primary", size: "md" },
});
```

See [tailwind-variants patterns](references/component-patterns.md) for slots, composition, and responsive variants.

## Common Errors

| Symptom | Fix |
|---------|-----|
| `bg-primary` doesn't work | Add `@theme inline { --color-primary: var(--primary); }` |
| Colors all black/white | Double `hsl()` wrapping -- use `var(--color)` not `hsl(var(--color))` |
| `@apply` fails on custom class | Use `@utility` instead of `@layer components` |
| Build fails after migration | Delete `tailwind.config.ts` |
| Animations broken | Replace `tailwindcss-animate` with `tw-animate-css` |
| `.dark { @theme { } }` fails | v4 does not support nested `@theme` -- use `:root`/`.dark` CSS vars mapped via `@theme inline` |

## Dark Mode (v4 Pattern)

```css
:root { --background: hsl(0 0% 100%); --foreground: hsl(222 84% 4.9%); }
.dark { --background: hsl(222 84% 4.9%); --foreground: hsl(210 40% 98%); }
@theme inline { --color-background: var(--background); --color-foreground: var(--foreground); }
```

Semantic classes (`bg-background`, `text-foreground`) auto-switch -- no `dark:` variants needed for themed colors.

## References

- [Component patterns](references/component-patterns.md) -- tailwind-variants slots, CVA, compound components
- [Layout patterns](references/layout-patterns.md) -- grid areas, container queries, z-index management, fluid typography
