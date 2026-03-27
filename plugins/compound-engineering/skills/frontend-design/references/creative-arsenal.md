# Creative Arsenal

Avoid defaulting to generic patterns. Pull from these when the design calls for it:

**Navigation**: Floating glass-pill navbar detached from top. Hamburger that morphs into X. Mega-menu with staggered fade-in. Magnetic button that pulls toward cursor (use `useMotionValue` + `useTransform`, never `useState`).

**Layouts**: Asymmetric bento grid (`grid-template-columns: 2fr 1fr`). Masonry (staggered heights). Z-axis card cascade (slight rotation, overlapping depth). Editorial split (massive type left, interactive content right). Horizontal scroll hijack. Sticky scroll stack (cards physically stack on top of each other).

**Cards**: Parallax tilt tracking mouse coordinates. Spotlight border illuminating under cursor. Glassmorphism with inner refraction border (`border-white/10` + `shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`). Morphing modal (button expands into full-screen dialog).

**Typography**: Kinetic marquee (reverses on scroll). Text scramble/Matrix decode on hover. Text mask revealing video behind letters. Gradient stroke animation running along outlined text.

**Micro-interactions**: Particle explosion on CTA success. Skeleton shimmer (shifting light across placeholders). Directional hover fill (enters from the mouse's entry side). Ripple from click coordinates. Animated SVG line drawing. Mesh gradient blob background (`pointer-events-none`, `position: fixed`).

## Forbidden AI Patterns

These are the telltale signs of AI-generated design. Avoid them:

**Visual**: No pure `#000000` (use off-black, Zinc-950, charcoal). No neon outer glows or default `box-shadow` glows. No oversaturated accents. No purple/blue "AI gradient" aesthetic. No excessive gradient text on large headers. No custom mouse cursors. No arbitrary `z-50` or `z-9999` -- use z-index only for systemic layers (navbars, modals, overlays).

**Typography**: No Inter font. No oversized H1s that scream -- control hierarchy with weight and color, not just scale. No serif fonts on dashboards or software UIs. No all-caps subheaders everywhere -- try eyebrow tags instead (`rounded-full px-3 py-1 text-[10px] uppercase tracking-[0.2em] font-medium`), sentence case, lowercase italics, or small-caps.

**Layout**: No centered hero sections when the design calls for asymmetry -- use split-screen, left-aligned content, or offset compositions. No "three equal cards in a row" feature sections -- use zig-zag, asymmetric grid, horizontal scroll, or masonry instead. No random dark sections breaking a light-mode page (or vice versa) -- commit to a tone or use subtle shade shifts.

**Content (the "Jane Doe" effect)**: No generic names ("John Doe", "Sarah Chen"). No fake round numbers (`99.99%`, `50%`) -- use organic data (`47.2%`, `$87.50`, `+1 (312) 847-1928`). No startup slop names ("Acme", "Nexus", "SmartFlow") -- invent contextual, believable brands. No AI copywriting cliches ("Elevate", "Seamless", "Unleash", "Next-Gen", "Delve", "Game-changer"). No Lorem Ipsum. No exclamation marks in success messages. No "Oops!" error messages -- be direct. Use sentence case for headers, not Title Case On Every Header. No emojis in code, markup, or text content -- replace with icons or SVG primitives.

**Forms**: Label above the input. Helper text optional but present in markup. Error message below input. Use `gap-2` for input stacking.

**Components**: No generic card look everywhere (border + shadow + white) -- cards should exist only when elevation communicates hierarchy. No Lucide/Feather icons exclusively (try Phosphor, Heroicons, or custom). No rocketship for "Launch", shield for "Security" -- replace cliche metaphors. No accordion FAQ -- use side-by-side lists or inline progressive disclosure. No 3-card carousel testimonials with dots. No avatar circles exclusively -- try squircles or rounded squares. No broken Unsplash links -- use picsum.photos or SVG avatars. Standardize icon stroke widths. Always include a favicon.

**Interactivity**: Implement full interaction cycles, not just the success state. Provide skeleton loaders (not circular spinners), composed empty states, inline error messages (not `window.alert()`), and tactile press feedback (`scale-[0.98]` or `translateY(1px)` on `:active`). For CTA buttons with icons, wrap the icon in its own circular container (`w-8 h-8 rounded-full bg-black/5`) with independent hover kinetics (`group-hover:translate-x-1 scale-105`). Add visible focus rings for keyboard navigation. Add `scroll-behavior: smooth` for anchor navigation.

**Content Register**: Match copy to context. Dashboards and operational tools need utility copy -- section headings say what the area is, not what the brand aspires to be. If a sentence could appear in a homepage hero, rewrite it until it sounds like product UI. Hero sections on landing pages use marketing copy.

**Hero Construction**: Full-bleed heroes run edge-to-edge; constrain only the inner text/action column. Use `calc(100svh - var(--header-height))` to account for persistent UI chrome. Test: if the first viewport still works after removing the image, the image is too weak.

## Animation Library Guidance

Default to Framer Motion for UI interactions (buttons, modals, lists, bento cards). Use GSAP or Three.js only for isolated full-page scroll storytelling or canvas/WebGL backgrounds -- never mix them with Framer Motion in the same component tree. Wrap GSAP/Three.js in strict `useEffect` cleanup blocks.
