# Task: <one-line goal>

## Branch
<main for additive rendering work | `git switch -c <type>/<name>` if it can break an
existing report: data role or capabilities change, formatting-property change, apiVersion
bump — CLAUDE.md Hard Rule #17.>

## Context
<What's true right now. Verified facts only — file paths, data-role names, property
names, the error or the screenshot. If a claim came from a human's memory, say so and
tell Claude Code to verify before acting.>

## Contract impact
<Does this touch capabilities.json, a data role, or a released formatting property name?
If yes: which consuming reports exist, and what breaks in them. A rename is MAJOR and
silently discards report authors' saved settings — Hard Rule #5.>

## Steps
1. **Inspect first.** <Which files to read; what to confirm before editing. capabilities.json
   and the formatting model are the contract — read both before touching src/.>
2. <The change, with exact names/code. Mark anything Claude Code must NOT guess (role
   names, format strings, theme slots) as verify-don't-assume.>

## Out of scope
<What NOT to touch. `visual.guid` is never changed. `.api/`, `dist/`, `node_modules/`,
`package-lock.json` are generated. Cert install and Developer Mode are user actions.>

## Constraints
Per CLAUDE.md §4. <Repeat any Hard Rule this task is likely to bump into — commonly #6
(degenerate dataView), #8 (theme colors), #9 (no host-model assumptions).>

## Validate — Visual Validation Gate (Hard Rule #15)
- `pbiviz start`, dev visual loaded in Desktop: renders with real data.
- Zero rows: renders a deliberate empty state, not a blank rectangle.
- Null / missing measure: no exception, no silent blank.
- Resize both directions; Format pane shows grouped cards with working defaults.
- Switch the report theme: colors follow it.
- <Task-specific check — a hand-verifiable number, a specific interaction.>
- Fresh session: `/code-review medium src/` before packaging (Hard Rule #16).
Report anything unverifiable (Service-only behavior, other reports' bindings) as such.

## Commit
git add -A && git commit -m "<message>"
<+ CHANGELOG line under [Unreleased] if consumer-visible.>
