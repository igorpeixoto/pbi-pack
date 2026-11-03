# Releasing — pbi-pack

Release system: **git tags + changelog**, same shape as a client Power BI project (`pbi-starter/RELEASING.md`) but for the pack itself — there's no Power BI Desktop or Service publish step here.

## The Invariant

**Tag exactly what's on `main`.** A project's Governance Freshness Check (`power-bi-dev` §5) and any manual skill re-sync always compare against whatever this repo currently has — the tag is a human-readable checkpoint of the pack's history, not something those checks read directly.

## Workflow (Every Release)

```bash
# 1. Confirm all intended CLAUDE.md / skills/ / pbi-starter/ changes are
#    committed and pushed to main (the pre-commit hook already stamped
#    CLAUDE.md's hash and re-synced skills/ -> ~/.claude/skills/).

# 2. Declare the release: in CHANGELOG.md, rename [Unreleased] to
#    ## [X.Y.Z] - YYYY-MM-DD and open a fresh [Unreleased] above it.
git add CHANGELOG.md && git commit -m "Release vX.Y.Z"

# 3. Create annotated Git tag:
git tag -a vX.Y.Z -m "Short release summary"
git push origin main --tags
```

## Version Numbering (Pack Semver)

See the table in `CHANGELOG.md`.

## Rollback

```bash
# Restore just the governance/skills surface to a known-good tag:
git checkout vX.Y.Z -- CLAUDE.md skills/ pbi-starter/
# Re-run the skills sync manually if needed:
#   for d in skills/*/; do n=$(basename "$d"); cp -r "$d." "$HOME/.claude/skills/$n/"; done
# Investigate the broken version on a branch; re-tag or patch forward once fixed.
```

## Notes

- This repo's "validation gate" is: the pre-commit hook ran cleanly (hash stamped, `pbi-starter/CLAUDE.md` synced, `~/.claude/skills/` refreshed), not a Desktop refresh.
- Client projects instantiated from `pbi-starter/` version and release independently on their own cadence — see `pbi-starter/RELEASING.md`, which is untouched by this file and unaffected by this repo's own tags.
