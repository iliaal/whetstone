# Motion Patterns

Detailed motion rules for frontend interfaces. The parent skill covers the high-level philosophy; this file has the implementation specifics.

## CSS-First Preference

Prioritize CSS-only solutions for HTML pages. Use the Motion library (framer-motion) for React when available. CSS animations cover most needs without adding a JS dependency.

## Stagger on Mount

No instant mounts. One well-orchestrated page load with staggered reveals creates more delight than scattered micro-interactions.

**CSS approach:** `animation-delay: calc(var(--index) * 80ms)` using a CSS custom property set per element.

**React (Motion) approach:** `staggerChildren: 0.08` in a parent variant so elements enter sequentially rather than appearing all at once.

## Spring Physics

Use spring physics over linear easing. Starting point: `type: "spring", stiffness: 100, damping: 20`. Tune stiffness up for snappy interactions (buttons, toggles) and down for fluid transitions (page enters, modals).

## Animate Only Transform and Opacity

Animate exclusively via `transform` and `opacity`. Never animate `top`, `left`, `width`, `height` -- these trigger layout recalculation instead of GPU compositing, causing jank on lower-end devices.

## Scroll Entry Recipe

Combine Y translation + blur + opacity for premium depth on scroll entry:

```
translate-y-16 blur-md opacity-0
  resolving to
translate-y-0 blur-0 opacity-100
```

## IntersectionObserver Mandate

Use `IntersectionObserver` for scroll reveals. Never use `window.addEventListener('scroll')` -- scroll listeners fire continuously and cause reflows. IntersectionObserver is declarative and only fires when elements cross thresholds.

## Hover Animations (React)

Never use `useState` for continuous or magnetic hover animations. `useState` triggers re-renders on every frame, destroying performance. Use `useMotionValue` + `useTransform` exclusively for frame-rate-sensitive motion -- these update outside the React render cycle.

## Perpetual Motion Components

Memoize perpetual motion components with `React.memo` and isolate them as leaf `'use client'` components. This prevents parent re-renders from resetting animations and keeps the motion calculation isolated from the component tree.

## Grain and Noise Filters

Apply grain/noise filters only to fixed, `pointer-events-none` pseudo-elements. Never apply them to scrolling containers -- the filter recalculates on every scroll frame, causing severe performance degradation.
