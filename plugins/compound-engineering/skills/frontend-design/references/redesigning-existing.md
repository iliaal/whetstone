# Redesigning Existing Interfaces

When upgrading an existing project, audit first, then fix in this priority order (maximum visual impact, minimum risk):

1. **Font swap** — biggest instant improvement, lowest risk
2. **Color palette cleanup** — remove clashing or oversaturated colors, enforce one accent
3. **Hover and active states** — makes the interface feel alive
4. **Layout and spacing** — proper grid, max-width container, consistent padding
5. **Replace generic components** — swap cliche patterns for modern alternatives
6. **Add loading, empty, and error states** — makes it feel finished
7. **Polish typography scale and spacing** — the premium final touch

Work with the existing tech stack. Do not migrate frameworks or styling libraries. Keep changes reviewable and focused — small, targeted improvements over big rewrites. Before importing any new library or writing any styles, check `package.json` for the Tailwind version (v3 vs v4) — v4 syntax in a v3 project will break the build.
