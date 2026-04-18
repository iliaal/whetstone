# Banned AI Design Patterns

Comprehensive list of visual patterns that signal AI-generated interfaces. Avoid all of these.

## Layout Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Centered hero + three equal-width cards + centered CTA | The most common AI layout | Asymmetric layouts, split screens, bento grids |
| >60% of content using `text-align: center` | Center-heavy layouts are the #1 structural AI tell | Left-align body text, reserve centering for headings and CTAs only |
| Perfectly symmetric grids everywhere | Real design uses intentional asymmetry | Vary column spans, use dominant/subordinate relationships |
| Full-width sections stacked vertically with identical padding | Monotonous rhythm | Vary section widths, padding, and visual weight |
| Everything inside cards (border + shadow + white bg) | Card overuse dilutes hierarchy | Use `border-t`, `divide-y`, or negative space for separation |
| Cookie-cutter section rhythm (every section follows identical structure) | Monotonous, signals templated generation | Vary section types: hero, split, bento, full-bleed, editorial |
| Colored left-border accent cards | Common AI component pattern | Use top borders, background tints, or typography weight for emphasis |
| Bento grids with empty/dead cells | Missing `grid-flow-dense` lets grids render with visible gaps that read as broken | Apply `grid-auto-flow: dense` (Tailwind: `grid-flow-dense`); verify `col-span`/`row-span` values interlock mathematically; zero empty cells |

## Color Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Purple/violet gradients (`#6366f1`--`#8b5cf6` range) | The single most recognizable AI color signature | Pick a different palette entirely -- earth tones, monochrome, warm accents |
| Purple-to-blue gradient hero | The default AI aesthetic | Pick a different palette entirely |
| Evenly distributed accent colors | No visual hierarchy | One dominant accent, neutrals everywhere else |
| Generic blue (#3B82F6) as primary | Default Tailwind blue | Choose a distinctive hue with personality |
| Oversaturated accent colors (saturation >80%) | Visually loud, cheap feel | Desaturate accents; muted tones read as more considered |
| Pure black (`#000000`) for text or backgrounds | Harsh, unnatural contrast | Use near-blacks (`#0a0a0a`, `#111`) or tinted darks |
| Rainbow gradient text | Screams "AI made this" | Single-color text, use weight/size for emphasis |
| Excessive `bg-clip-text bg-gradient-to-r` on headings | Gradient text overuse is an AI tell when applied to multiple headings | Reserve for one hero moment at most |
| Neon/outer glow effects (`shadow-[0_0_20px_...]`) | Dated, screams template | Subtle, tinted shadows that match the surface hue |
| Warm AND cool grays in the same interface | Inconsistent tinting | Pick one gray family and commit |

## Typography Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Inter/Roboto/System font everywhere | Zero personality | Distinctive choices: Geist, Outfit, Cabinet Grotesk, Satoshi |
| Uniform font-weight (400 regular everywhere) | Flat hierarchy | Weight contrast: 500/600 for headings, 400 for body |
| Title Case In Every Heading Word | Overly formal, AI tell | Sentence case |

## Decoration Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Accent line under every heading | Dead giveaway | Use typography weight and spacing for hierarchy |
| Decorative emoji in headers | Tacky | Quality icons (Phosphor, Radix) or no decoration |
| Uniform rounded corners everywhere (>80% of elements sharing the same `>=16px` radius) | Bubbly uniformity is an instant AI tell | Vary by purpose: sharp for data, rounded for interactive, pill for tags |
| Icons inside colored circles (primary-color background circle + white icon) | Default AI component decoration; #3 most common AI pattern | Use icons inline, or with subtle background tints matching the surface |
| `rounded-2xl` / `rounded-3xl` on containers, cards, and sections | Bubbly, toy-like feel | Reserve large radii for small interactive elements; use tighter radii for containers |
| Generic stock imagery | Placeholder feel | Contextual photos, SVG illustrations, or abstract graphics suited to the domain |
| Floating gradient blobs as background | Overused AI aesthetic | Noise textures, mesh gradients, geometric patterns |
| Custom mouse cursors (`cursor: url(...)`) | Novelty that signals template code | Use system cursors; reserve custom cursors for drawing tools or games |
| shadcn/ui components left in generic default state | Identifiably "template starter kit" | Customize colors, spacing, and radii to match the design system |

## Interaction Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Hover effect on every element | Noise, no hierarchy | Reserve hover for interactive elements only |
| Uniform transition-all on everything | Performance waste, lazy | Animate specific properties (transform, opacity) |
| Bounce animation on load | Juvenile | Staggered fade/translate reveals with spring physics |
| Skeleton loaders that look identical to content | Uncanny valley | Simpler placeholders or progressive loading |

## Content Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| "Welcome to X" / "Unlock the power of..." / "Revolutionize your..." hero copy | Generic AI copy; instant credibility killer | Write specific, benefit-driven copy tied to the actual product |
| "John Doe" / "Jane Smith" / "Sarah Chan" placeholder users | Lazy, unrealistic | Diverse, realistic names with messy data |
| "Acme Corp" / "Nexus" / "Synergy" startup slop names | Template feel, obviously generated | Industry-specific realistic names |
| Fake round numbers ("99.99%", "50%", "10x faster") | Suspiciously clean metrics signal fabrication | Use irregular numbers ("47.2%", "3.8x", "1,247") |
| Lorem ipsum visible in output | Unfinished | Realistic copy, even if placeholder |
| Broken Unsplash links (`source.unsplash.com` or expired URLs) | Renders as broken images, amateurish | Use `https://picsum.photos/seed/{name}/800/600` or local assets |
| Perfectly aligned testimonial cards with star ratings | Template pattern | Varied formats, pull quotes, inline mentions |
| Oversized H1s without proportional hierarchy below | Single-level typography signals "just make it big" | Scale the full type ramp: H1 through H4 with intentional ratio |
| Scroll-prompt filler UI ("Scroll to explore", "Swipe down", bouncing chevrons, scroll-arrow icons) | Signature AI landing-page tell; padding to avoid writing actual below-the-fold content | If content below is worth scrolling to, its first heading is the cue. Delete the prompt. |
