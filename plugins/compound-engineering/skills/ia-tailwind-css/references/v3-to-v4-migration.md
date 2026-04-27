# v3 to v4 Breaking Changes

Reference for migrating an existing Tailwind v3 project to v4. For greenfield v4 work, the SKILL body covers current patterns directly.

| v3 | v4 | Notes |
|----|-----|-------|
| `tailwind.config.ts` | `@theme` in CSS | Delete config file |
| `@tailwind base/components/utilities` | `@import "tailwindcss"` | Single import |
| `darkMode: "class"` | `@custom-variant dark (...)` | CSS-only |
| `bg-gradient-to-r` | `bg-linear-to-r` | Also: `bg-radial`, `bg-conic` |
| `bg-opacity-60` | `bg-red-500/60` | All `*-opacity-*` removed |
| `rounded-sm` | `rounded-xs` | Radius scale shifted down one step |
| `rounded` | `rounded-sm` | (run `@tailwindcss/upgrade` codemod) |
| `rounded-md` (6px) | `rounded` (6px) | |
| `rounded-lg` | `rounded-md` | |
| `rounded-xl` | `rounded-lg` | |
| `min-h-screen` | `min-h-dvh` | `dvh` handles mobile browser chrome |
| `w-6 h-6` | `size-6` | Size shorthand for equal w/h |
| `space-x-4` | `gap-4` | Gap handles flex/grid wrapping correctly |
| `text-base leading-7` | `text-base/7` | Inline line-height modifier |
| `require("tailwindcss-animate")` | `tw-animate-css` | CSS-only animations |

Run `@tailwindcss/upgrade` codemod before hand-editing -- it handles the mechanical class renames. Hand-fix `@theme` migration, custom variants, and any project-specific config patterns the codemod cannot infer.
