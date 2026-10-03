# Redesigning Existing Interfaces

## Screenshot Iteration Mode (repair from evidence)

When the entry point is a screenshot plus a complaint ("here's the page, this looks wrong, fix it") rather than a greenfield brief, route by evidence, not by vibe:

1. **State the problem in ONE sentence**: name what specifically looks wrong. Preserve the user's negative label when it is diagnostic ("cramped", "muddy", "off"); do not launder it into "make it more modern" or "make it more premium". "More premium" is not a diagnosis; "the caption baseline drifts above the adjacent line" is. A diagnosis points at a measurable element; a mood does not.
2. **Resolve material uncertainty.** If evidence supports a reversible repair already within the user's request, state the diagnosis and proceed. Ask for clarification only when competing diagnoses imply materially different outcomes or require new authority. Honor approval already given; do not require a repeated confirmation solely because the entry point is a screenshot.
3. **Apply changes in the blast-radius-minimizing order below** (font swap -> color cleanup -> hover/active -> layout & whitespace -> replace generic components -> add loading/empty/error states -> typographic polish). Earliest passes deliver the most visual lift for the smallest diff; later passes touch more surface area. Do not reorder to "fix the layout first" because the layout looks worst; a font swap often resolves what reads as a layout problem.

**Stop tuning, start tokenizing (3-tune rule).** If a single magic spacing or sizing value has been hand-adjusted three times and the layout still looks off, stop tuning the number. Replace the N independent padding/gap/margin values with one shared named token (a CSS variable or scale step) and align every site to it. Asymmetry that survives three rounds of tuning is structural, not numeric; another nudge will not find a value that does not exist.

When upgrading an existing project, audit first, then fix in this priority order (maximum visual impact, minimum risk):

1. **Font swap**: biggest instant improvement, lowest risk
2. **Color palette cleanup**: remove clashing or oversaturated colors, enforce one accent
3. **Hover and active states**: makes the interface feel alive
4. **Layout and spacing**: proper grid, max-width container, consistent padding
5. **Replace generic components**: swap cliche patterns for modern alternatives
6. **Add reachable loading, empty, and error states**: cover the actual data/action lifecycle without inventing async behavior for synchronous controls
7. **Polish typography scale and spacing**: the premium final touch

Use the [redesign-audit.md](./redesign-audit.md) checklist (typography, color, layout, interactivity, content, component pattern checks) to systematically identify violations before starting fixes.

Work with the existing tech stack. Do not migrate frameworks or styling libraries. Keep changes reviewable and focused: small, targeted improvements over big rewrites. Before importing any new library or writing any styles, check `package.json` for the Tailwind version (v3 vs v4); v4 syntax in a v3 project will break the build.

For a visual-only redesign, inspect the affected interface's behavioral dependencies before changing markup. Preserve route paths, anchor IDs, form field names, analytics event names, and selectors consumed by scripts or tests. Preserve legal and consent wording unless the requested change authorizes its revision. An authorized identifier migration requires updating its consumers. Exercise affected deep links, form submissions, tracked actions, and consent controls after the redesign; a screenshot does not establish that these behaviors still work.
