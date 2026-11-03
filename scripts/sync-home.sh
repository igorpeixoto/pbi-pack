#!/bin/sh
# Bring this machine's runtime copies under ~/.claude/ up to date with this repo.
#
#   sh scripts/sync-home.sh                    # everything (also the one-time setup on a machine)
#   sh scripts/sync-home.sh <label> "<paths>"  # only what <paths> touched (how the git hooks call it)
#
# Five independent targets, each one-way repo -> home:
#   skills/            -> ~/.claude/skills/          (scripts/sync-skills.sh)
#   user/CLAUDE.md     -> ~/.claude/CLAUDE.md span    (scripts/sync-user-claude.sh)
#   user/settings.json -> ~/.claude/settings.json keys (scripts/sync-user-settings.sh)
#   scripts/pbi-sync/  -> ~/.claude/pbi-sync/bin/    (scripts/install-pbi-sync.sh, also wires the
#                                                     SessionStart hook that auto-pulls this repo)
#   scripts/git-hooks/ -> .git/hooks/                (scripts/install-hooks.sh)
#
# The hooks reinstall themselves when their sources change, so a pull that changes the sync logic
# takes effect on the next pull without anyone running an installer.

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT" || exit 1

LABEL="${1:-Sync}"
CHANGED="${2-ALL}"

touched() {
    [ "$CHANGED" = "ALL" ] && return 0
    printf '%s\n' "$CHANGED" | grep -q "^$1"
}

touched "skills/"            && sh scripts/sync-skills.sh "$LABEL"
touched "user/"              && sh scripts/sync-user-claude.sh "$LABEL"
touched "user/"              && sh scripts/sync-user-settings.sh "$LABEL"
touched "scripts/pbi-sync/"  && sh scripts/install-pbi-sync.sh "$LABEL" >/dev/null && echo "[$LABEL] pbi-sync tooling reinstalled."
# Last, as one line ending in exit: when a hook calls this, install-hooks.sh replaces that hook.
touched "scripts/git-hooks/" && sh scripts/install-hooks.sh >/dev/null && echo "[$LABEL] git hooks reinstalled."; exit 0
