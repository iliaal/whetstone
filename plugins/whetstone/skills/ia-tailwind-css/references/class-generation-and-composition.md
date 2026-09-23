# Class generation and composition

## ESLint Integration

Use `eslint-plugin-better-tailwindcss` for automated class validation:
- `no-conflicting-classes`: catches `text-red-500 text-blue-500`
- `no-unknown-classes`: flags typos
- `enforce-canonical-classes`: normalizes shorthand
- `no-duplicate-classes`: removes redundant entries
- `no-deprecated-classes`: catches v3 classes removed in v4
- `useSortedClasses`: enforces canonical class order; configure `attributes: ["classList"]` and `functions: ["clsx", "cva", "cn", "tv", "tw"]` to cover JSX utility functions


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

**Keep class names whole in the source.** The example above works because both branches are complete literals. Tailwind's scanner does literal string matching over source text and never evaluates JavaScript, so a class assembled by interpolation is invisible to it and the utility is simply never generated. The failure is silent: no error, no warning, just missing styles.

```typescript
// Broken: `bg-red-500` never appears in the source, so it is never generated
<div className={`bg-${color}-500`} />

// Works: every candidate class is a complete literal the scanner can see
const BG = { red: "bg-red-500", blue: "bg-blue-500" } as const;

function Swatch({ color }: { color: keyof typeof BG }) {
  return <div className={BG[color]} />;
}
```

The same applies to classes built in a non-scanned location (a string in a database, a CMS field, or a file outside the configured `@source` paths). Confirm the source actually gets scanned before assuming a literal is enough.

`@source` directives resolve relative to the file they appear in, so a shared token package pulling in a sibling (`@source '../../ui/src/**/*.{ts,tsx}'`) is what makes a `libs/ui`-only utility generate in every consuming app. The real generation risk is a utility with **no** prior usage anywhere, and it fails invisibly rather than loudly: an SVG whose root carries `fill="none"` and whose paths swap `fill="#355BF5"` for `className="fill-primary-500"` renders *invisible*, not mis-colored. Grep the compiled CSS of every consuming app, not one.

Verify by building, not by reading: when class names or scanned sources changed, run the real Tailwind build and grep the output CSS for the expected utilities. Reviewing the `className` attribute proves the string is right, not that the rule exists.


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

See [tailwind-variants patterns](./component-patterns.md) for slots, composition, and responsive variants.
