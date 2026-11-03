#!/bin/sh
# SessionEnd hook: records a reminder if this project has commits that were never published.
#
# It copies NOTHING. SessionEnd is documented as "may not fire" under some terminations, and it
# cannot block termination, so it is not a safe place for the only copy-back path. If it fails to
# fire, nothing is lost: the next SessionStart recomputes the same fact from git.
#
# Always exits 0.

PBI_SYNC_HOME="${PBI_SYNC_HOME:-$HOME/.claude/pbi-sync}"
BIN="$PBI_SYNC_HOME/bin"

[ -f "$BIN/pbi-common.sh" ] || exit 0
# shellcheck source=pbi-common.sh
. "$BIN/pbi-common.sh" 2>/dev/null || exit 0

SLUG=$(resolve_slug "" 2>/dev/null)
[ -n "$SLUG" ] || exit 0

LOCAL=$(reg_field "$SLUG" local 2>/dev/null) || exit 0
[ -d "$LOCAL/.git" ] || exit 0

PUB_SHA=$(state_get "$SLUG" published_src_sha)
DIRTY=$(git -C "$LOCAL" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

if [ -z "$PUB_SHA" ]; then
    printf '%s  %s: never published (%s uncommitted)\n' "$(date -Iseconds)" "$SLUG" "$DIRTY" >> "$PENDING_LOG"
    exit 0
fi

AHEAD=$(git -C "$LOCAL" rev-list --count "${PUB_SHA}..HEAD" 2>/dev/null || echo 0)
if [ "$AHEAD" != "0" ] || [ "$DIRTY" != "0" ]; then
    printf '%s  %s: %s commits unpublished, %s uncommitted\n' \
        "$(date -Iseconds)" "$SLUG" "$AHEAD" "$DIRTY" >> "$PENDING_LOG"
fi

exit 0
