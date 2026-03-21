# Creative Arsenal

Avoid defaulting to generic patterns. Pull from these when the design calls for it:

**Navigation**: Floating glass-pill navbar detached from top. Hamburger that morphs into X. Mega-menu with staggered fade-in. Magnetic button that pulls toward cursor (use `useMotionValue` + `useTransform`, never `useState`).

**Layouts**: Asymmetric bento grid (`grid-template-columns: 2fr 1fr`). Masonry (staggered heights). Z-axis card cascade (slight rotation, overlapping depth). Editorial split (massive type left, interactive content right). Horizontal scroll hijack. Sticky scroll stack (cards physically stack on top of each other).

**Cards**: Parallax tilt tracking mouse coordinates. Spotlight border illuminating under cursor. Glassmorphism with inner refraction border (`border-white/10` + `shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`). Morphing modal (button expands into full-screen dialog).

**Typography**: Kinetic marquee (reverses on scroll). Text scramble/Matrix decode on hover. Text mask revealing video behind letters. Gradient stroke animation running along outlined text.

**Micro-interactions**: Particle explosion on CTA success. Skeleton shimmer (shifting light across placeholders). Directional hover fill (enters from the mouse's entry side). Ripple from click coordinates. Animated SVG line drawing. Mesh gradient blob background (`pointer-events-none`, `position: fixed`).
