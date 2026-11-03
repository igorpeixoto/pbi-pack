#!/bin/sh
# SessionStart hook: advisory, plus one background job — the pack auto-update below, which pulls
# the pack and lets its post-merge hook refresh ~/.claude/. Everything else reads state only.
#
# Deliberately NOT matched on the "clear" source: /clear is routine (CLAUDE.md Hard Rule 20 makes
# it so), and re-announcing publish state on every context clear is noise.
#
# Always exits 0. A hook that can fail a session start is a hook that will, at the worst moment.

PBI_SYNC_HOME="${PBI_SYNC_HOME:-$HOME/.claude/pbi-sync}"
BIN="$PBI_SYNC_HOME/bin"

# --- Governance freshness (power-bi-dev §5 / power-bi-visual-dev §7, done deterministically) ---
# Compares this project's governance hash against the pack on disk and prints one line when it
# is behind. Runs in EVERY project (before the pbi-sync registry check below, which exits early
# for unregistered folders). Silent when there is nothing to say; never blocks.
PACK="${PBI_PACK_HOME:-C:/dev/pbi-pack}"
PACK=$(printf '%s' "$PACK" | sed 's#\\#/#g')
if [ -f CLAUDE.md ] && [ -d "$PACK" ] && [ "$(cd "$PACK" 2>/dev/null && pwd -P)" != "$(pwd -P)" ]; then
    for slug in power-bi-skills power-bi-visual-skills; do
        grep -qF "<!-- BEGIN $slug -->" CLAUDE.md 2>/dev/null || continue
        case "$slug" in
            power-bi-skills) canon="$PACK/CLAUDE.md" ;;
            *)               canon="$PACK/pbiviz-starter/CLAUDE.md" ;;
        esac
        [ -f "$canon" ] || break
        here=$(sed -n "s/^<!-- $slug-hash: \([0-9a-f]*\).*/\1/p" CLAUDE.md | head -1)
        pack=$(sed -n "s/^<!-- $slug-hash: \([0-9a-f]*\).*/\1/p" "$canon" | head -1)
        if [ -z "$here" ]; then
            printf 'governance: CLAUDE.md has no %s hash line (predates the freshness scheme) - treat as stale; see %s/CHANGELOG.md\n' "$slug" "$PACK"
        elif [ -n "$pack" ] && [ "$here" != "$pack" ]; then
            printf 'governance: CLAUDE.md block %s is %s, the pack has %s - behind the pack; see %s/CHANGELOG.md and let power-bi-dev §5 (or power-bi-visual-dev §7) update the span\n' "$slug" "$here" "$pack" "$PACK"
        elif [ -n "$pack" ]; then
            # Printed on purpose: silence would be indistinguishable from "hook not installed",
            # and power-bi-dev §5 falls back to the manual comparison when no line appears.
            printf 'governance: CLAUDE.md block %s matches the pack (%s)\n' "$slug" "$here"
        fi
        break
    done
fi

# --- Pack auto-update ----------------------------------------------------------------------------
# Keeps every machine on the pack's main without anyone running `git pull`: at most once every
# PBI_PACK_UPDATE_HOURS (default 6), pull the pack in the background; the pack's post-merge hook
# then refreshes ~/.claude/skills/, the ~/.claude/CLAUDE.md span, these scripts and the git hooks.
# Fast-forward only, and only on a clean main — a diverged, dirty or feature-branch pack is left
# for a human. Detached and time-boxed, so a slow or blocked network never delays the session;
# what it pulled takes effect from the next session. Off with PBI_PACK_AUTOUPDATE=0.
AU_STATE="$PBI_SYNC_HOME/state"
AU_LOG="$AU_STATE/pack-autoupdate.log"
if [ "${PBI_PACK_AUTOUPDATE:-1}" != "0" ] && [ -d "$PACK/.git" ]; then
    mkdir -p "$AU_STATE" 2>/dev/null
    # Notices queued by the background sync (e.g. a setting kept local), shown once.
    if [ -s "$AU_STATE/notices.log" ]; then
        cat "$AU_STATE/notices.log"
        : > "$AU_STATE/notices.log"
    fi
    # Say so once when the last attempt failed; the log keeps the reason.
    if grep -q '^FAIL' "$AU_LOG" 2>/dev/null; then
        printf 'pack auto-update: %s\n' "$(sed 's/^FAIL //' "$AU_LOG" | head -1)"
        sed -i 's/^FAIL /FAIL-SEEN /' "$AU_LOG" 2>/dev/null
    fi
    AU_STAMP="$AU_STATE/pack-autoupdate.stamp"
    AU_MIN=$(( ${PBI_PACK_UPDATE_HOURS:-6} * 60 ))
    if [ ! -f "$AU_STAMP" ] || [ -z "$(find "$AU_STAMP" -mmin -"$AU_MIN" 2>/dev/null)" ]; then
        touch "$AU_STAMP"
        (
            cd "$PACK" || exit 0
            now=$(date -Iseconds)
            br=$(git symbolic-ref --quiet --short HEAD 2>/dev/null)
            if [ "$br" != "main" ]; then
                echo "SKIP $now: pack is on '$br', not main" > "$AU_LOG"; exit 0
            fi
            if [ -n "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
                echo "SKIP $now: pack has uncommitted changes" > "$AU_LOG"; exit 0
            fi
            before=$(git rev-parse --short HEAD)
            if GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=20" \
               timeout 180 git pull --ff-only --quiet origin main; then
                echo "OK $now: $before -> $(git rev-parse --short HEAD)" > "$AU_LOG"
            else
                echo "FAIL $now: could not fast-forward $PACK from origin/main (offline, diverged or auth) - run 'git -C $PACK pull' by hand" > "$AU_LOG"
            fi
        ) </dev/null >/dev/null 2>&1 &
    fi
fi

[ -f "$BIN/pbi-common.sh" ] || exit 0
# shellcheck source=pbi-common.sh
. "$BIN/pbi-common.sh" 2>/dev/null || exit 0

SLUG=$(resolve_slug "" 2>/dev/null)
[ -n "$SLUG" ] || exit 0

OUT=$(sh "$BIN/pbi-status.sh" "$SLUG" 2>/dev/null)
[ -n "$OUT" ] || exit 0

printf 'pbi-sync state for this project:\n%s\n' "$OUT"

# Surface anything the last session flagged on its way out, then clear it.
if [ -s "$PENDING_LOG" ]; then
    printf '\nUnfinished from a previous session:\n'
    cat "$PENDING_LOG"
    : > "$PENDING_LOG"
fi

printf '\nReminder: the OneDrive folder is a publish target. Edit only the local repo, then run:\n'
printf '  sh ~/.claude/pbi-sync/bin/pbi-publish.sh %s\n' "$SLUG"

exit 0
