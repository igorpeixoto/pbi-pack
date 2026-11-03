#!/bin/sh
# Read-only status for one or all registered projects. Touches nothing.
#
#   sh ~/.claude/pbi-sync/bin/pbi-status.sh [<slug>|.]
#
# Reports, per project: unpublished local commits, OneDrive-side drift, whether Desktop is open,
# and whether a publish lock is held. This is what the SessionStart hook surfaces.

set -e
# shellcheck source=pbi-common.sh
. "$(dirname "$0")/pbi-common.sh"

report_one() {
    slug="$1"
    local_path=$(reg_field "$slug" local 2>/dev/null || echo "")
    od_path=$(reg_field "$slug" onedrive 2>/dev/null || echo "")
    [ -n "$local_path" ] || { printf '%s: not in the registry\n' "$slug"; return 0; }

    printf '%s\n' "$slug"

    if [ ! -d "$local_path/.git" ]; then
        printf '  local:     MISSING or not a git repo (%s)\n' "$local_path"
        return 0
    fi

    dirty=$(git -C "$local_path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    head=$(git -C "$local_path" rev-parse --short HEAD 2>/dev/null || echo '?')
    pub_sha=$(state_get "$slug" published_src_sha)
    pub_at=$(state_get "$slug" published_at)

    if [ -z "$pub_sha" ]; then
        printf '  local:     %s, %s uncommitted - NEVER PUBLISHED\n' "$head" "$dirty"
    else
        ahead=$(git -C "$local_path" rev-list --count "${pub_sha}..HEAD" 2>/dev/null || echo '?')
        if [ "$ahead" = "0" ]; then
            printf '  local:     %s, %s uncommitted - published %s\n' "$head" "$dirty" "$pub_at"
        else
            printf '  local:     %s, %s uncommitted - %s COMMITS NOT PUBLISHED (last publish %s)\n' \
                "$head" "$dirty" "$ahead" "$pub_at"
            git -C "$local_path" log --oneline "${pub_sha}..HEAD" 2>/dev/null | head -5 | sed 's/^/               /'
        fi
    fi

    if [ ! -d "$od_path" ]; then
        printf '  onedrive:  MISSING (%s)\n' "$od_path"
    elif [ ! -d "$od_path/.git" ]; then
        printf '  onedrive:  present, not yet a deliverable repo - needs a first publish --init\n'
    else
        od_dirty=$(git -C "$od_path" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
        od_head=$(git -C "$od_path" rev-parse HEAD 2>/dev/null || echo '')
        prev_head=$(state_get "$slug" published_onedrive_sha)
        if [ "$od_dirty" != "0" ]; then
            printf '  onedrive:  DRIFTED - %s files changed there since the last publish\n' "$od_dirty"
        elif [ -n "$prev_head" ] && [ "$od_head" != "$prev_head" ]; then
            pulled_od=$(state_get "$slug" pulled_onedrive_sha)
            pulled_commit=$(state_get "$slug" pulled_commit_sha)
            if [ "$pulled_od" = "$od_head" ] && [ -n "$pulled_commit" ] \
                && git -C "$local_path" merge-base --is-ancestor "$pulled_commit" HEAD 2>/dev/null; then
                printf '  onedrive:  pulled and merged - the next publish brings it back in sync\n'
            elif [ "$pulled_od" = "$od_head" ]; then
                printf '  onedrive:  DRIFTED - pulled, but the review branch is not merged yet\n'
            else
                printf '  onedrive:  DRIFTED - commits made there that you did not publish\n'
            fi
        else
            printf '  onedrive:  in sync\n'
        fi
    fi

    [ -d "$LOCK_DIR/$slug.lock" ] && printf '  lock:      HELD by PID %s\n' "$(cat "$LOCK_DIR/$slug.lock/pid" 2>/dev/null || echo '?')"
    return 0
}

TARGET=$(resolve_slug "$1")
if [ -n "$TARGET" ]; then
    report_one "$TARGET"
else
    slugs=$(reg_slugs)
    [ -n "$slugs" ] || { printf 'No projects registered in %s\n' "$REGISTRY"; exit 0; }
    printf '%s\n' "$slugs" | while IFS= read -r s; do [ -n "$s" ] && report_one "$s"; done
fi

if desktop_running; then
    printf '\nPower BI Desktop is OPEN - publishing is blocked until it is closed.\n'
fi
