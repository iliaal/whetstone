# Redesigning Existing Interfaces

## Reference-fidelity mode

When the task is to implement a supplied mockup, screenshot, or design frame, treat the reference as an existing design system regardless of repository signal count. Skip the design philosophy and swap test. Let the reference's appearance override generic taste rules and banned-pattern tables. Retain functional, accessibility, and content-authenticity requirements.

1. Transcribe readable visible copy exactly. Flag illegible text or missing assets instead of inventing a replacement silently.
2. Extract type sizes and weight relationships, heading-to-body and text-to-action gaps, section gutters, component shapes and fills, and semantic color roles.
3. Resolve unclear details from the visible design language first, then spacing and layout relationships, then the component family. Use generic defaults only where those sources provide no answer.
4. Compare rendered narrow and wide layouts with the reference. Check for lost hierarchy, compressed spacing, or distinctive compositions flattened into generic rows. Report intentional responsive adaptations and unresolved details.

## Screenshot Iteration Mode (repair from evidence)

When the entry point is a screenshot plus a complaint ("here's the page, this looks wrong, fix it") rather than a greenfield brief, route by evidence, not by vibe:

1. **State the problem in ONE sentence**: name what specifically looks wrong. Preserve the user's negative label when it is diagnostic ("cramped", "muddy", "off"); do not launder it into "make it more modern" or "make it more premium". "More premium" is not a diagnosis; "the caption baseline drifts above the adjacent line" is. A diagnosis points at a measurable element; a mood does not.
2. **Resolve material uncertainty.** If evidence supports a reversible repair already within the user's request, state the diagnosis and proceed. Ask for clarification only when competing diagnoses imply materially different outcomes or require new authority. Honor approval already given; do not require a repeated confirmation solely because the entry point is a screenshot.
3. **Fix the diagnosed cause first** with the smallest focused change. Repair spacing or layout directly when the evidence identifies that cause. Prioritize typography when font metrics explain the defect. Reserve the suggested sequence below for broadly authorized redesigns.

**Stop tuning, start tokenizing (3-tune rule).** If a single magic spacing or sizing value has been hand-adjusted three times and the layout still looks off, stop tuning the number. Replace the N independent padding/gap/margin values with one shared named token (a CSS variable or scale step) and align every site to it. Asymmetry that survives three rounds of tuning is structural, not numeric; another nudge will not find a value that does not exist.

For a broadly authorized redesign, audit first. Prioritize findings by impact and risk; use this sequence as a guide when it fits the evidence:

1. **Font swap**: when font choice or metrics contribute to the diagnosed problems
2. **Color palette cleanup**: remove clashing or oversaturated colors, enforce one accent
3. **Hover and active states**: makes the interface feel alive
4. **Layout and spacing**: proper grid, max-width container, consistent padding
5. **Replace generic components**: swap cliche patterns for modern alternatives
6. **Add reachable loading, empty, and error states**: cover the actual data/action lifecycle without inventing async behavior for synchronous controls
7. **Polish typography scale and spacing**: the premium final touch

Use the [redesign-audit.md](./redesign-audit.md) checklist (typography, color, layout, interactivity, content, component pattern checks) to systematically identify violations before starting fixes.

Work with the existing tech stack. Do not migrate frameworks or styling libraries. Keep changes reviewable and focused: small, targeted improvements over big rewrites. Before importing any new library or writing any styles, check `package.json` for the Tailwind version (v3 vs v4); v4 syntax in a v3 project will break the build.

For a visual-only redesign, inspect the affected interface's behavioral dependencies before changing markup. Preserve route paths, anchor IDs, form field names, analytics event names, and selectors consumed by scripts or tests. Preserve primary navigation labels, the logo/wordmark, and legal and consent wording unless the requested change authorizes their revision. Retain page titles, descriptions, canonical URLs, JSON-LD structured data, and Open Graph/Twitter card metadata. Add redirects when an authorized migration changes routes. An authorized identifier migration requires updating its consumers. Preserve existing focus visibility, alt text, keyboard paths, and contrast. Exercise affected deep links, form submissions, tracked actions, and consent controls after the redesign; a screenshot does not establish that these behaviors still work. Recheck affected metadata and accessibility behavior after layout or template changes.
