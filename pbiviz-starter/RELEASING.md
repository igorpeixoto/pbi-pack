# Releasing — Power BI Custom Visual

Release system: **git tags + changelog + one `.pbiviz` binary per tag**. No release branches, no CI — right-sized for a visual maintained by one person and consumed by a handful of reports.

## The Invariant

**One version, three places, one binary.** `pbiviz.json`'s `visual.version`, the `CHANGELOG.md` heading, and the git tag are the same number, and the `.pbiviz` attached to that tag is the only build anyone may import. Break that and "which build is in that report?" has no answer — and unlike a report repo, you cannot open the artifact and look.

## Workflow (Every Release)

Division of labor: **both the human developer and Claude Code can declare and tag releases.**

```bash
# 1. Pass the Visual Validation Gate (CLAUDE.md Hard Rule #15): pbiviz start, load the
#    dev visual in Desktop, check real data / zero rows / null measure / resize /
#    grouped Format pane / theme switch.
#    Then, in a FRESH session: /code-review medium src/   (Hard Rule #16)
git add -A && git commit -m "Describe the change"

# 2. Bump the version in ONE commit with the heading:
#    - pbiviz.json  → "visual": { "version": "X.Y.Z.0" }
#    - CHANGELOG.md → rename [Unreleased] to ## [X.Y.Z] - YYYY-MM-DD, open a fresh one above
git add pbiviz.json CHANGELOG.md && git commit -m "Release vX.Y.Z"

# 3. Build the binary FROM the tagged state and tag it:
pbiviz package                     # emits dist/<VisualName>.pbiviz
git tag -a vX.Y.Z -m "Short release summary"
git push origin main --tags        # if a remote exists

# 4. Publish the binary against the tag — pick one and stay consistent:
gh release create vX.Y.Z dist/<VisualName>.pbiviz -t "vX.Y.Z" -F -   # with a remote
# ...or, no remote: mkdir -p releases/vX.Y.Z && cp dist/*.pbiviz releases/vX.Y.Z/
#    (releases/ is the one exception to the dist/ ignore — commit it in this case)

# 5. Import into each consuming report:
pbi visual import-custom ./dist/<VisualName>.pbiviz --replace   # back up the .pbip first
```

## Version Numbering (Visual-Adapted Semver)

Severity is what breaks in a **consuming report**, not how much code changed.

| Bump | When |
|------|------|
| MAJOR | Data role or formatting property removed/renamed; `dataViewMappings` shape changed; `apiVersion` bump; a rendering change that alters the meaning of published numbers. Every existing report needs attention — say exactly what in the changelog entry. |
| MINOR | New optional data role, new formatting card/group/property, new rendering capability. Existing bindings and saved settings keep working. |
| PATCH | Rendering fixes, default corrections, `displayName`/label fixes, performance, dependency bumps with no contract change. |

## Rollback

```bash
git checkout vX.Y.Z        # last known-good
npm install && pbiviz package
pbi visual import-custom ./dist/<VisualName>.pbiviz --replace
```

Re-importing the previous binary restores the previous behavior **as long as the GUID never changed** (CLAUDE.md Hard Rule #1) — bindings and saved formatting survive because they are keyed by GUID and property name. If a MAJOR release renamed a property, rolling back does *not* bring back the settings that release discarded; they were already gone.

## Notes

- The Power BI org store refuses to replace an imported visual with a **lower** `visual.version`. A rollback that must go through the store needs a new higher version carrying the old code, not a downgrade.
- `pbiviz package` reads the version from `pbiviz.json` and stamps it into the binary — bump before packaging, never after.
- A MAJOR bump is a message to other people. The changelog line for it is the only place they will read what to re-do.
