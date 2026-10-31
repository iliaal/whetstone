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

Animate exclusively via `transform` and `opacity`. Never animate `top`, `left`, `width`, `height`; these trigger layout recalculation instead of GPU compositing, causing jank on lower-end devices.

## Scroll Entry Recipe

Combine Y translation and opacity for scroll entry, within the transform/opacity policy:

The classes below are the start and end states the script applies after it adds `.motion-ready`; they are not markup to author:

```
translate-y-16 opacity-0
  resolving to
translate-y-0 opacity-100
```

Ship content visible by default: never author `opacity-0` in the markup. Scope the hidden start state to a class the script adds (for example `.motion-ready` on `<html>`, with `.motion-ready .reveal { opacity: 0; transform: translateY(4rem) }`) only after the IntersectionObserver is set up, so a script error, a crawler, or slow hydration still renders every heading and CTA. Start scale entries at 0.85 or higher, never `scale(0)`, and stagger scroll reveals within one section rather than across the page.

## IntersectionObserver Mandate

Use `IntersectionObserver` for scroll reveals. Never use `window.addEventListener('scroll')`; scroll listeners fire continuously and cause reflows. IntersectionObserver is declarative and only fires when elements cross thresholds.

## Hover Animations (React)

Never use `useState` for continuous or magnetic hover animations. `useState` triggers re-renders on every frame, destroying performance. Use `useMotionValue` + `useTransform` exclusively for frame-rate-sensitive motion; these update outside the React render cycle.

## Perpetual Motion Components

Keep CSS/compositor animation in CSS; continuous animation alone does not cause React renders or require a Client Component. Isolate input-driven motion or state-driven frame work as a small client leaf and use motion values instead of React state for continuous updates. Add `React.memo` only when profiling identifies avoidable renders with stable props. Verify animation continuity rather than assuming every parent render resets it.

## Grain and Noise Filters

Apply grain/noise filters only to fixed, `pointer-events-none` pseudo-elements. Never apply them to scrolling containers: the filter recalculates on every scroll frame, causing severe performance degradation.
