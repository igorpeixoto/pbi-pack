# Task: <one-line goal>

## Branch
<main for trivial | `git switch -c <type>/<name>` if it can break loading>
Close Power BI Desktop before switching.

## Context
<What's true right now. Verified facts only — file paths, column names,
error messages. If a claim came from a human's memory, say so and tell
Claude Code to verify before acting.>

## Steps
1. **Inspect first.** <Which files to read; what to confirm before editing.>
2. <The change, with exact names/code. Mark anything Claude Code must NOT
   guess (labels, schemas) as verify-don't-assume.>

## Out of scope
<What NOT to touch. PBIR CF/tooltips/field wells default to GUI-only.>

## Constraints
Per CLAUDE.md §3. <Repeat any rule this task is likely to bump into.>

## Validate
- Open .pbip in Desktop, refresh: no errors, guards silent.
- <Task-specific checks — a hand-verifiable number, a rendering check.>
- <Regression check on untouched pages.>
Report anything unverifiable (canvas rendering, Service refresh) as such.

## Commit
git add -A && git commit -m "<message>"
<+ CHANGELOG line under [Unreleased] if user-visible.>
