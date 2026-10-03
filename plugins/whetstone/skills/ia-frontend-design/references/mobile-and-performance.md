# Mobile Collapse and Performance Guardrails

Load this reference for any layout using asymmetry, rotations, animation, or complex grid variants. Missing mobile collapse and missing performance guards are the top two reported AI UI defects after missing interactive states.

## Mobile Collapse Mandate

Any layout using asymmetry, rotations, negative-margin overlaps, or `md:` / `lg:` grid variations above 768px MUST declare an explicit mobile fallback. Mobile is not "just narrower"; it's a different layout mode.

- **Collapse to single-column below `md:`**: reset widths to `w-full`, reset `grid-cols-*` to 1, apply `px-4 py-8` for baseline spacing.
- **Remove rotations and negative overlaps on mobile**: `md:-translate-y-8` and `md:rotate-2` should not carry over; they collide with touch targets at small widths.
- **Touch target sizing**: prefer 44×44px hit areas for standalone touch controls. WCAG 2.5.5 is a Level AAA criterion with exceptions; it does not make every smaller link a violation. For WCAG 2.2 AA, check 2.5.8: at least 24×24px or sufficient spacing, subject to its inline, equivalent-control, user-agent, and essential exceptions. Check the applicable [AA minimum](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) or [AAA enhanced](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html) criterion before reporting a compliance failure.
- **No unintended horizontal overflow**: identify and constrain the actual oversized grid or decorative layer. Do not hide overflow on the outermost layout by default; `overflow-x-hidden` can change vertical scrolling and clip focus indicators or overlays. Verify menus, focus visibility, and sticky behavior after applying containment. Preserve intentional scrolling regions such as wide data tables.

Test the narrowest breakpoint before considering an asymmetric layout done.

## Performance Guardrails

Check these guards against the actual rendering mechanism and measure performance in the affected viewport.

- **Grain and noise filters** apply exclusively to fixed, `pointer-events-none` pseudo-elements (e.g., `fixed inset-0 z-50 pointer-events-none`). Never on scrolling containers: the filter re-rasterizes every scroll frame and collapses mobile performance.
- **Animate only `transform` and `opacity`**. Never animate `top`, `left`, `width`, or `height`; these trigger layout on every frame and cannot be GPU-composited.
- **Z-index restraint**: reserve `z-*` values for systemic layer contexts (sticky navbars, modals, overlays). Never spam arbitrary `z-10` or `z-50` to push elements around; that's what stacking contexts and DOM order are for.
- **Distinguish animation from React updates**: CSS/compositor animations do not themselves re-render React. Keep those animations in CSS without introducing a Client Component solely for animation. Isolate state-driven frame work or input-driven motion in a small client leaf. Use motion values to avoid frame-by-frame React state updates. Apply `React.memo` only when profiling shows avoidable renders with stable props.
