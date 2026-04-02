# Redesign Audit Framework

Use when the user explicitly asks to redesign, audit, or improve an existing interface. This audit does NOT apply when building new features within an existing design system -- in that case, match the existing system per the Context Detection rules in the parent skill.

Walk through each section, note violations, then prioritize fixes by ROI.

## Fix Priority Order

Font swap (highest ROI, lowest risk) -> Color cleanup -> Hover/active states -> Layout/spacing -> Replace generics -> Add loading/empty/error states -> Polish typography

## Typography (10 checks)

1. Using a generic/default font (Inter, Roboto, system-ui with no customization)?
2. Headlines lack presence (same weight/size as body, no letter-spacing adjustment)?
3. Body text exceeds ~65ch line width?
4. Only Regular (400) and Bold (700) weights used (no Medium, SemiBold, Light variation)?
5. Numbers in data displays not using `tabular-nums` or monospace?
6. No `letter-spacing` adjustment on headlines (especially uppercase)?
7. All-caps text without increased tracking (0.05-0.1em)?
8. Orphaned single words on line ends (missing `text-wrap: balance`)?
9. No typographic scale (sizes jump inconsistently)?
10. Serif and sans-serif mixed without clear hierarchy purpose?

## Color and Surfaces (8 checks)

1. Pure black (`#000000`) on pure white background?
2. Oversaturated accent colors (saturation > 80%)?
3. More than one accent color competing for attention?
4. Mixing warm and cool grays in the same palette?
5. AI purple gradient (the telltale sign)?
6. Generic shadows (`box-shadow: 0 2px 4px rgba(0,0,0,0.1)` copy-pasted everywhere)?
7. Completely flat design with no depth hierarchy?
8. Linear 45-degree gradients (prefer radial, mesh, or noise)?

## Layout (15 checks)

1. Everything centered with no asymmetry or visual tension?
2. Three equal-width cards in a row (the AI default)?
3. Using `h-screen` instead of `min-h-[100dvh]`?
4. Complex flexbox percentage math (`w-[calc(33%-1rem)]`) instead of CSS Grid?
5. No `max-width` container (content stretches to viewport edge)?
6. All cards exactly the same height with no variation?
7. Inconsistent border-radius (mixing 4px, 8px, 12px, 16px)?
8. No element overlap or z-axis layering?
9. Top and bottom padding identical (bottom usually needs more for optical balance)?
10. Sidebar defaults with no creative alternative considered?
11. Insufficient whitespace between major sections (< `py-16`)?
12. Buttons scattered without alignment to a visual axis?
13. Every element wrapped in a card container (border + shadow + padding)?
14. Grid items all same size (no spanning or featured items)?
15. Mobile layout is just desktop squeezed (no responsive redesign)?

## Interactivity and States (11 checks)

1. No hover state on interactive elements?
2. No active/pressed state on buttons (`scale(0.98)` on press)?
3. No focus-visible styles for keyboard navigation?
4. Transitions missing or using default `ease` (should use `cubic-bezier`)?
5. No loading state (spinner, skeleton, or progress)?
6. No empty state ("No items yet" with illustration or guidance)?
7. No error state (what happens when the API fails)?
8. Dead links or placeholder `href="#"` left in?
9. No active indicator on current nav item?
10. Scroll behavior not smooth or not using `IntersectionObserver`?
11. Form inputs without label, placeholder, and validation feedback?

## Content (9 checks)

1. Generic placeholder names ("John Doe", "Acme Corp", "Lorem ipsum")?
2. Fake round numbers ($99, 100%, 1,000 users)?
3. Placeholder company name or brand still present?
4. Cliched marketing language ("revolutionary", "game-changing")?
5. Exclamation marks in UI text?
6. Passive voice in CTAs ("Your order will be processed" vs "We'll process your order")?
7. Identical dates/timestamps across all sample data?
8. Same avatar/profile image repeated?
9. Latin placeholder text visible in production?

## Component Patterns (8 checks)

1. Card overuse (everything is a card, no alternative layouts)?
2. Only two button styles: primary filled + ghost outline?
3. Badges all same color/style regardless of semantic meaning?
4. Accordions with full borders/boxes instead of minimal `border-bottom` dividers?
5. Carousels with dot indicators and auto-play?
6. Pricing tables with the "popular" badge on the middle tier?
7. Modals that overlay the entire viewport with no alternative interaction?
8. Toast notifications with no dismiss action or progress?
