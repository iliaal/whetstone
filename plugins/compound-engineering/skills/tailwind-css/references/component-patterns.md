# Component Patterns

## tailwind-variants (tv)

Type-safe component variants with slots, composition, and responsive support.

### Slots API

```typescript
import { tv } from "tailwind-variants";

const card = tv({
  slots: {
    base: "rounded-lg border shadow-sm",
    header: "flex flex-col space-y-1.5 p-6",
    title: "text-2xl font-semibold leading-none tracking-tight",
    content: "p-6 pt-0",
    footer: "flex items-center p-6 pt-0",
  },
  variants: {
    elevated: { true: { base: "shadow-lg border-0" } },
  },
});

const { base, header, title, content, footer } = card({ elevated: true });
```

### Composition

```typescript
const baseButton = tv({ base: "rounded-lg font-medium transition-colors" });

const iconButton = tv({
  extend: baseButton,
  base: "inline-flex items-center justify-center",
  variants: {
    size: { sm: "size-8", md: "size-10", lg: "size-12" },
  },
});
```

### Responsive Variants

```typescript
const grid = tv({
  base: "grid gap-4",
  variants: {
    cols: { 1: "grid-cols-1", 2: "grid-cols-2", 3: "grid-cols-3", 4: "grid-cols-4" },
  },
  responsiveVariants: ["sm", "md", "lg"],
});

// Usage: <div className={grid({ cols: { initial: 1, sm: 2, lg: 4 } })} />
```

## CVA (class-variance-authority)

Alternative to tailwind-variants -- simpler API, no slots.

```typescript
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        outline: "border border-border bg-background hover:bg-accent",
        ghost: "hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        sm: "h-9 rounded-md px-3",
        default: "h-10 px-4 py-2",
        lg: "h-11 rounded-md px-8",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
```

## Compound Components (React 19)

React 19 passes ref as a regular prop -- no `forwardRef` needed.

```typescript
export function Card({ className, ref, ...props }: React.HTMLAttributes<HTMLDivElement> & { ref?: React.Ref<HTMLDivElement> }) {
  return <div ref={ref} className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props} />;
}

export function CardHeader({ className, ref, ...props }: React.HTMLAttributes<HTMLDivElement> & { ref?: React.Ref<HTMLDivElement> }) {
  return <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6", className)} {...props} />;
}
```

## ESLint Integration

Use `eslint-plugin-better-tailwindcss` for v4 class validation:

| Rule | Purpose |
|------|---------|
| `no-conflicting-classes` | Detect classes that override each other |
| `no-unknown-classes` | Flag classes not registered with Tailwind |
| `enforce-shorthand-classes` | `size-6` not `w-6 h-6`; `p-6` not `px-6 py-6` |
| `no-deprecated-classes` | Catch v3 class names used in v4 projects |
