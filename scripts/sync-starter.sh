#!/bin/sh
# Refresh the pbi-starter/ copies from their canonical sources at the pack root.
#
#   sh scripts/sync-starter.sh
#
# Two files, two rules:
#   CLAUDE.md               -> pbi-starter/CLAUDE.md      ONLY the <!-- BEGIN power-bi-skills --> ..
#                                                          <!-- END power-bi-skills --> span. The root
#                                                          file carries pack-only notes after END that
#                                                          must never reach a client project.
#   .claude/settings.json   -> pbi-starter/.claude/settings.json   verbatim. The starter drifted two
#                                                          releases behind the root before this existed.
#
# Called by scripts/git-hooks/pre-commit and .github/workflows/sync-claude.yml. Idempotent.

set -e

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT"

SLUG="power-bi-skills"
BEGIN_MARKER="<!-- BEGIN ${SLUG} -->"
END_MARKER="<!-- END ${SLUG} -->"

grep -qF "$BEGIN_MARKER" CLAUDE.md || { echo "sync-starter: CLAUDE.md has no '$BEGIN_MARKER'" >&2; exit 1; }
grep -qF "$END_MARKER"   CLAUDE.md || { echo "sync-starter: CLAUDE.md has no '$END_MARKER'" >&2; exit 1; }

mkdir -p pbi-starter/.claude
awk -v b="$BEGIN_MARKER" -v e="$END_MARKER" '
    $0 == b { inside = 1 }
    inside  { print }
    $0 == e { inside = 0 }
' CLAUDE.md > pbi-starter/CLAUDE.md
echo "sync-starter: CLAUDE.md governance span -> pbi-starter/CLAUDE.md"

if [ -f .claude/settings.json ]; then
    cp .claude/settings.json pbi-starter/.claude/settings.json
    echo "sync-starter: .claude/settings.json -> pbi-starter/.claude/settings.json"
fi
