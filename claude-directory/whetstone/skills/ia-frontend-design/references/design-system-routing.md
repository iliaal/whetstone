# Design system routing

Read for greenfield work in the product register (the design serves a task). Before drafting a bespoke token system, check whether an established, accessible component system already fits the brief. Matching one gives a vetted component vocabulary, keyboard and screen-reader behavior, and density conventions for free; the Design Philosophy then constrains how the system is themed rather than reinventing its parts.

## Brief to system

| Brief | Start from |
|-------|------------|
| SaaS app, admin panel, dashboard | Radix primitives + shadcn/ui, themed away from defaults |
| Enterprise, data-dense internal tooling | Carbon or Material 3 |
| Microsoft ecosystem (Office, Teams, Windows) | Fluent |
| Commerce or merchant back office | Polaris |
| Developer tool, code-adjacent UI | Primer |
| Government or public-sector service | USWDS or GOV.UK Design System |
| iOS native or iOS-first web | Apple Human Interface Guidelines |
| Android native | Material 3 |

Routing picks a starting vocabulary, not a look: still run Context Detection and the swap test, and still theme colors, radii, and spacing so the result does not read as the system's default demo.

## When not to route

- Brand register: the design is the product (marketing sites, launches, campaign pages). A component system flattens the signature the brief needs.
- Landing and marketing pages inside an otherwise product-register app; route the app, design the landing page.
- An existing system already detected (4+ signals). Match it instead.

## Read mode (docs, articles, changelogs)

- Structure for comprehension: headings that summarize, a scannable outline, code and tables where prose would slow the reader.
- No hero or CTA theater on a docs index; the first viewport is the table of contents or the first useful section.
- Generous measure (about 60-75 characters) and line-height; body type sized for sustained reading.
- Persistent navigation with the current location visible; search where the corpus exceeds one page of links.
- Restrained motion; nothing moves while the reader is reading.

## Experience mode (portfolios, galleries, showcases)

- The work fills the first viewport; the artifact itself is the hero.
- Never crop, mask, or letterbox the artifact to fit a card or grid template; size the frame to the work.
- Chrome recedes: navigation, captions, and controls stay small, quiet, and out of the artifact's way.
- One artifact per viewport or a clear dominant/subordinate arrangement; no equal-weight thumbnail walls as the primary view.
- Motion serves transitions between works, not decoration on them.
