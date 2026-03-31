# Banned AI Design Patterns

Comprehensive list of visual patterns that signal AI-generated interfaces. Avoid all of these.

## Layout Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Centered hero + three equal-width cards + centered CTA | The most common AI layout | Asymmetric layouts, split screens, bento grids |
| Perfectly symmetric grids everywhere | Real design uses intentional asymmetry | Vary column spans, use dominant/subordinate relationships |
| Full-width sections stacked vertically with identical padding | Monotonous rhythm | Vary section widths, padding, and visual weight |
| Everything inside cards (border + shadow + white bg) | Card overuse dilutes hierarchy | Use `border-t`, `divide-y`, or negative space for separation |

## Color Patterns

| Pattern | Problem | Alternative |
|---------|---------|-------------|
| Purple-to-blue gradient hero | The default AI aesthetic | Pick a different palette entirely |
| Evenly distributed accent colors | No visual hierarchy | One dominant accent, neutrals everywhere else |
| Generic blue (#3B82F6) as primary | Default Tailwind blue | Choose a distinctive hue with personality |
| Rainbow gradient text | Screams "AI made this" | Single-color text, use weight/size for emphasis |
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
| Uniform rounded corners everywhere | Monotonous | Vary by purpose: sharp for data, rounded for interactive, pill for tags |
| Generic stock imagery | Placeholder feel | Realistic, messy data ("47.2%", "+1 (312) 847-1928") |
| Floating gradient blobs as background | Overused AI aesthetic | Noise textures, mesh gradients, geometric patterns |

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
| "John Doe" / "Jane Smith" placeholder users | Lazy, unrealistic | Diverse, realistic names with messy data |
| "Acme Corp" / "Example Inc" | Template feel | Industry-specific realistic names |
| Lorem ipsum visible in output | Unfinished | Realistic copy, even if placeholder |
| Perfectly aligned testimonial cards with star ratings | Template pattern | Varied formats, pull quotes, inline mentions |
