# Changelog — <VISUAL_NAME>

One version heading per release, one line per change. Rules in RELEASING.md.
Claude Code / Developer: when committing completed work, add a line under [Unreleased].

Severity is measured by what breaks in a **consuming report** — see the table below.
Every version heading must match `pbiviz.json`'s `visual.version` and a `vX.Y.Z` git tag
(CLAUDE.md Hard Rule #2).

## [Unreleased]

- Initial visual setup

<!-- Release protocol: the human or Claude Code bumps pbiviz.json visual.version, renames
     [Unreleased] to ## [X.Y.Z] - YYYY-MM-DD (after the Visual Validation Gate passes) and
     opens a fresh [Unreleased] above it. Claude Code creates the vX.Y.Z tag (CLAUDE.md §5). -->

## Version Numbering (Visual-Adapted Semver)

| Bump  | Criteria                                                            |
| ----- | ------------------------------------------------------------------- |
| MAJOR | Breaks an existing report: data role or property removed/renamed,   |
|       | dataViewMappings shape changed, apiVersion bump, or a rendering     |
|       | change that alters the meaning of published numbers                 |
| MINOR | New optional data role, new formatting card/group/property, new     |
|       | rendering capability — existing bindings and settings keep working  |
| PATCH | Rendering fixes, default corrections, label fixes, perf, dependency |
|       | bumps with no contract change                                       |
