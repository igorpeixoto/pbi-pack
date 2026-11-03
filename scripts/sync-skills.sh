#!/bin/sh
# Sync this repo's skills/ into ~/.claude/skills/, the runtime location Claude Code loads from.
#
# skills/ here and ~/.claude/skills/ are two independent copies with no link. Without a sync,
# edits made here silently never take effect in a live session.
#
# Shared implementation called by the pre-commit, post-merge, and post-checkout hooks in
# scripts/git-hooks/. Safe to run by hand at any time:
#   sh scripts/sync-skills.sh
#
# One-way, repo -> home, and it overwrites: anything edited directly in ~/.claude/skills/
# under a power-bi-* name will be replaced by this repo's version.

set -e

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT"

SKILLS_DIR="skills"
INSTALLED_SKILLS_DIR="${HOME}/.claude/skills"
LABEL="${1:-Sync}"

[ -d "$SKILLS_DIR" ] || exit 0

echo "[$LABEL] Syncing $SKILLS_DIR/ -> $INSTALLED_SKILLS_DIR/..."
mkdir -p "$INSTALLED_SKILLS_DIR"

for dir in "$SKILLS_DIR"/*/; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    mkdir -p "$INSTALLED_SKILLS_DIR/$name"
    cp -r "${dir}." "$INSTALLED_SKILLS_DIR/$name/"
    echo "[$LABEL]   -> $name"
done

# Prune pack-owned skills that no longer exist in this repo. Scoped to the power-bi-* namespace on
# purpose: ~/.claude/skills/ is personal scope and may hold skills this pack does not own, which must
# never be touched.
for installed in "$INSTALLED_SKILLS_DIR"/power-bi-*/; do
    [ -d "$installed" ] || continue
    name=$(basename "$installed")
    if [ ! -d "$SKILLS_DIR/$name" ]; then
        rm -rf "$installed"
        echo "[$LABEL]   -- removed $name (no longer in the pack)"
    fi
done

echo "[$LABEL] Installed skills refreshed (runtime-only copy, not tracked by git)."
