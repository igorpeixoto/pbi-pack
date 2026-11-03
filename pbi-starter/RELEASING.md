# Releasing — Power BI Dashboard

Release system: **git tags + changelog**. No release branches, no CI — right-sized for a solo- or small-team-maintained dashboard.

## The Invariant

**Tag exactly what you publish.** The tagged commit in git IS what runs in the Power BI Service. Publish untagged changes and the system is broken.

## Workflow (Every Release)

Division of labor: **both the human developer and Claude Code can declare and tag releases.**

```bash
# 1. Validate in Desktop: refresh green, guards silent, visuals render,
#    CF colors show. Then close Power BI Desktop.
git add -A && git commit -m "Describe the change"

# 2. Declare the release: in CHANGELOG.md, rename [Unreleased] to
#    ## [X.Y.Z] - YYYY-MM-DD and open a fresh [Unreleased] above it.
#    (Can be performed by human or Claude Code)
git add CHANGELOG.md && git commit -m "Release vX.Y.Z"

# 3. Create annotated Git tag:
git tag -a vX.Y.Z -m "Short release summary"
git push origin main --tags        # if a remote exists

# 4. Open Desktop → Publish to Service. NO edits between tag and publish.
```

## Version Numbering (BI-Adapted Semver)

| Bump | When |
|------|------|
| MAJOR | Model schema changes; breaking source-file changes; semantics changes that shift numbers stakeholders already saw |
| MINOR | New pages, visuals, or measures |
| PATCH | Fixes: measures, CF, filters, interactions |

## Rollback

```bash
# Close Desktop FIRST.
git checkout vX.Y.Z        # last known-good
# Open .pbip, verify, publish. Investigate the broken version on a branch later.
```

## Notes

- Pro workspaces have no tag awareness or deployment pipelines — the tag is YOUR record of what was published, nothing more.
- After Desktop normalizes files on save ($schema stamps etc.), commit that normalization BEFORE tagging — the tag must capture a loadable state.
- Close Desktop before any checkout/switch/merge, always.
