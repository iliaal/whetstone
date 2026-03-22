# Layout Patterns

## Grid Template Areas

Define reusable grid areas with `@utility`:

```css
@utility grid-areas-dashboard {
  grid-template-areas: "header header header" "nav main aside" "nav footer footer";
}
@utility area-header { grid-area: header; }
@utility area-nav { grid-area: nav; }
@utility area-main { grid-area: main; }
```

```html
<div class="grid grid-areas-dashboard grid-cols-[200px_1fr_250px] grid-rows-[60px_1fr_40px]">
  <header class="area-header">Header</header>
  <nav class="area-nav">Nav</nav>
  <main class="area-main">Content</main>
</div>
```

## Auto-Responsive Grids

```html
<!-- Auto-fit: cards stretch to fill -->
<div class="grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-6">

<!-- Auto-fill: maintains track size, leaves empty space -->
<div class="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4">

<!-- Safe minimum (handles container < minmax min) -->
<div class="grid grid-cols-[repeat(auto-fill,minmax(min(100%,300px),1fr))] gap-4">
```

## Z-Index Management

Define a z-index scale in `@theme` tokens instead of arbitrary numbers:

```css
@theme {
  --z-dropdown: 100;
  --z-sticky: 200;
  --z-fixed: 300;
  --z-modal-backdrop: 400;
  --z-modal: 500;
  --z-popover: 600;
  --z-tooltip: 700;
  --z-toast: 800;
}
```

Reference with `z-(--z-modal)` syntax -- never use `z-[9999]`.

## Container Queries

Component-level responsiveness independent of viewport.

```css
@plugin "@tailwindcss/container-queries";
```

```html
<article class="@container">
  <div class="flex flex-col @sm:flex-row gap-4">
    <img class="w-full @sm:w-32 @lg:w-48 aspect-video @sm:aspect-square object-cover" />
    <div class="flex-1 min-w-0">
      <h3 class="text-base @md:text-lg @lg:text-xl font-semibold truncate">Title</h3>
      <p class="text-sm @md:text-base line-clamp-2 @lg:line-clamp-3">Description</p>
    </div>
  </div>
</article>
```

| Use Container Queries | Use Viewport Queries |
|----------------------|---------------------|
| Reusable components | Page-level layouts |
| Sidebar widgets | Navigation bars |
| Card grids | Hero sections |
| Embedded/CMS content | Full-width sections |

Named containers scope queries: `@container/sidebar` with `@lg/sidebar:flex-row`.

## Fluid Typography

Eliminate breakpoint jumps with `clamp()`:

```css
@theme {
  --text-fluid-base: clamp(1rem, 0.9rem + 0.5vw, 1.125rem);
  --text-fluid-xl: clamp(1.25rem, 1rem + 1.25vw, 1.5rem);
  --text-fluid-3xl: clamp(1.875rem, 1.2rem + 3.375vw, 2.5rem);
}
```

Always combine `vw` with `rem` -- pure `vw` breaks when users zoom (WCAG violation).

## Custom Utilities

```css
@utility scrollbar-none {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

@utility text-gradient {
  @apply bg-linear-to-r from-primary to-accent bg-clip-text text-transparent;
}
```

## Native CSS Animations (v4)

Define keyframes inside `@theme` and reference with `--animate-*` tokens:

```css
@theme {
  --animate-slide-up: slide-up 0.3s ease-out;
  @keyframes slide-up {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }
}
```

Use `@starting-style` for entry animations on native popovers/dialogs:

```css
[popover]:popover-open { opacity: 1; transform: scale(1); }
@starting-style { [popover]:popover-open { opacity: 0; transform: scale(0.95); } }
```

Respect motion preferences: `motion-safe:animate-bounce motion-reduce:animate-none`.

## Safe Area Handling (Notched Devices)

```css
@utility safe-area-pt { padding-top: env(safe-area-inset-top); }
@utility safe-area-pb { padding-bottom: env(safe-area-inset-bottom); }
```

Apply to fixed headers/footers on mobile.
