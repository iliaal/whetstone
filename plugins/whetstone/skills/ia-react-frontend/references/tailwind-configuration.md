# Configuration and migration

## CSS-First Configuration

v4 prefers CSS configuration. Legacy JavaScript configuration remains supported through an explicit `@config` directive; v4 does not detect it automatically. Preserve an existing config until its settings and plugins have equivalent verified coverage in CSS or compatibility loading. Check loader support before referencing a TypeScript config. See the [official migration guide](https://tailwindcss.com/docs/upgrade-guide#using-a-javascript-config-file).

For example, load a supported legacy config using its actual path relative to the stylesheet:

```css
@config "../../tailwind.config.js";
```

Migrate unsupported legacy options separately: `corePlugins`, `safelist`, and `separator` are not supported through v4 compatibility loading. Use `@source inline()` for a safelist where needed. Verify generated utilities and affected interfaces before removing the old file.

| Directive | Purpose |
|-----------|---------|
| `@import "tailwindcss"` | Entry point (replaces `@tailwind base/components/utilities`) |
| `@theme { }` | Define/extend design tokens; auto-generates utility classes |
| `@theme inline { }` | Map CSS variables to Tailwind utilities without generating new vars |
| `@theme static { }` | Emit all theme variables, including unused ones; utility generation still applies |
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

Tokens defined with `@theme` become utilities automatically: `--color-brand` produces `bg-brand`, `text-brand`, `border-brand`. Define z-index as tokens (`--z-modal: 50`) and reference via `z-(--z-modal)` instead of arbitrary `z-50`. The `oklch()` form above matches how v4 defines its own default palette; lightness is perceptually uniform there, so a scale stepped by L reads evenly, and the `/N` opacity modifier mixes in the same space (`bg-brand/50` compiles to `color-mix(in oklab, var(--color-brand) 50%, transparent)`).

- **Derive alpha variants from one token instead of hand-picking shades**: `--color-brand-soft: color-mix(in oklab, var(--color-brand) 10%, transparent);` inside `@theme` yields a named `bg-brand-soft` that tracks the base token; use it only when a named token must exist (design-system contract, shared across apps), since the `/N` modifier already covers one-off use.
- **Clear a namespace for a strict design system**: `--color-*: initial;` as the first line of `@theme` removes the entire default palette (no `bg-red-500`, no emitted `--color-red-*` variables), so only the tokens declared after it exist; `--color-lime-*: initial;` drops a single default color, and `--*: initial;` resets every namespace (spacing, fonts, breakpoints) for a fully custom theme.

For custom properties that should not define Tailwind utilities, declare them in ordinary CSS such as `:root`, outside `@theme`.

**`@theme` tokens are tree-shaken.** v4 emits only the variables it can see used, so a token existing in a shared file says nothing about whether it reaches a given app's bundle. Measured on one shared token file feeding two apps: 20 of 59 `--color-*` emitted into one, 19 of 59 into the other. `@theme static` is the opt-out. A `var(--color-x)` reference inside your own hand-written CSS **counts as a use**, so pointing a custom property at a token (`--app-checkbox-border: var(--color-border-400)`) is self-sustaining, not fragile: Tailwind sees your CSS, not just your class names. Never rate a "this indirection depends on some unrelated utility still existing" concern on tree-shaking alone: delete the last utility usage in that app's scan set, rebuild, and read the compiled CSS. Assert the utility actually vanished as the applied control, or a build that silently no-opped (wrong package filter, stale `dist`) reads identically, producing the same false conclusion from nothing.

**CSS Modules**: reference the actual stylesheet that defines the theme, utilities, and variants, for example `@reference "../../app.css";` with the path adjusted relative to the module. Use `@reference "tailwindcss";` when only the default theme is needed. A package alias such as `#tailwind` works only when that alias is explicitly configured and resolves to the correct stylesheet.

**Animations (tw-animate-css)**: use `animate-in`/`animate-out` base classes combined with effect classes (`fade-in`, `slide-in-from-top`). Decimal spacing gotcha: use bracket notation `[0.625rem]` instead of fractional values like `2.5`.


## v3 to v4 Migration

For projects upgrading from v3 to v4, see [tailwind-v3-to-v4.md](./tailwind-v3-to-v4.md) for the full breaking-change table and codemod guidance. For greenfield v4 work, current patterns are above.


## Common Errors

| Symptom | Fix |
|---------|-----|
| `bg-primary` doesn't work | Add `@theme inline { --color-primary: var(--primary); }` |
| Colors all black/white | Double `hsl()` wrapping; use `var(--color)` not `hsl(var(--color))` |
| `@apply` fails on custom class | Use `@utility` instead of `@layer components` |
| Build fails after migration | Inspect the build error and config loading; preserve the legacy config until settings/plugins are covered by CSS or supported `@config` loading |
| Animations broken | Replace `tailwindcss-animate` with `tw-animate-css` |
| `.dark { @theme { } }` fails | v4 does not support nested `@theme`; use `:root`/`.dark` CSS vars mapped via `@theme inline` |


## Dark Mode (v4 Pattern)

```css
:root { --background: hsl(0 0% 100%); --foreground: hsl(222 84% 4.9%); }
.dark { --background: hsl(222 84% 4.9%); --foreground: hsl(210 40% 98%); }
@theme inline { --color-background: var(--background); --color-foreground: var(--foreground); }
```

Semantic classes (`bg-background`, `text-foreground`) auto-switch; no `dark:` variants needed for themed colors.
