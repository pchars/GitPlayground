---
name: design-system
description: "GitPlayground design specification — tokens, typography, components. Read docs/DESIGN.md (not a workflow agent)."
tools: Read, Grep, Glob
model: inherit
---

This entry is a **pointer to the project design system**, not a generic UI-design
workflow. For design process (research, critique, handoff), use
[ui-designer.md](ui-designer.md).

## Primary source

**[`docs/DESIGN.md`](../../docs/DESIGN.md)** — the single source of truth
for colors, typography, spacing, components, and responsive breakpoints in
GitPlayground.

Also see [docs/FRONTEND.md](../../docs/FRONTEND.md) for the static-file map and
`static_v` cache-busting.

## When to read docs/DESIGN.md

- Adding or changing page CSS (`static/css/*.css`)
- New templates or layout components
- Spacing, colors, typography, hover states
- SVG/icon assets and monochrome palette rules

## Project rules (summary)

- Tokens live in `static/css/common.css` (`:root`); page CSS uses `var(--…)`
- One page → one CSS file; all `@media` in `responsive.css`
- User-facing copy in Russian; `class` names and paths in English
- Terminal ANSI colors are documented exceptions to the token palette

**AGENTS.md** overrides this summary when they conflict (e.g. `static_v` tag,
migration policy). Always read the full `docs/DESIGN.md` before visual changes.
