#!/bin/sh
# Bring changes made directly in the OneDrive deliverable back into the local working repo,
# onto a review branch. The rare reverse path - use it when pbi-publish reports drift.
#
#   sh ~/.claude/pbi-sync/bin/pbi-pull.sh [<slug>|.]
#
# It never merges for you: it lands the OneDrive content as one commit on a branch so you can
# diff it against your work and decide. Your current branch is left untouched.

set -e
# shellcheck source=pbi-common.sh
. "$(dirname "$0")/pbi-common.sh"

SLUG=$(resolve_slug "$1")
[ -n "$SLUG" ] || die "no project given and the current directory is not a registered project."

LOCAL=$(reg_field "$SLUG" local) || die "$SLUG is not in the registry"
ONEDRIVE=$(reg_field "$SLUG" onedrive) || die "$SLUG has no onedrive path"
[ -d "$LOCAL/.git" ] || die "local path is not a git repo: $LOCAL"
[ -d "$ONEDRIVE" ] || die "onedrive path does not exist: $ONEDRIVE"

printf 'pbi-sync pull: %s\n  from: %s\n  into: %s\n' "$SLUG" "$ONEDRIVE" "$LOCAL"

acquire_lock "$SLUG"
trap release_lock EXIT INT TERM

step 1 "Power BI Desktop closed?"
desktop_running && die "Power BI Desktop is running. Close it and re-run."
info "not running"

step 2 "local repo committed?"
DIRTY=$(git -C "$LOCAL" status --porcelain)
if [ -n "$DIRTY" ]; then
    printf '%s\n' "$DIRTY" | sed 's/^/    /' >&2
    die "commit or stash your local changes first - a pull creates a branch and needs a clean tree."
fi
ORIG_BRANCH=$(git -C "$LOCAL" rev-parse --abbrev-ref HEAD)
info "on $ORIG_BRANCH, clean"

# If the deliverable has uncommitted edits, capture them as a commit there first so the pull has
# something stable to read. This is the one case where pull writes to the OneDrive repo.
if [ -d "$ONEDRIVE/.git" ]; then
    if [ -n "$(git -C "$ONEDRIVE" status --porcelain)" ]; then
        step 3 "capturing uncommitted edits in the deliverable"
        git -C "$ONEDRIVE" add -A
        git -C "$ONEDRIVE" commit -q -m "external: edits made directly in the deliverable, captured by pbi-pull"
        info "$(git -C "$ONEDRIVE" log -1 --format='%h %s')"
    fi
fi

step 4 "creating the review branch"
TS=$(date +%Y%m%d-%H%M%S)
BRANCH="onedrive-pull/$TS"
# Branch from the commit that was last published, not from HEAD. The copy below writes the whole
# deliverable tree, so on top of HEAD the pull commit would also undo every local commit made since
# that publish - and merging it would silently revert them. From the published commit the branch
# holds only the edits made in OneDrive, and the merge is a real three-way merge.
BASE=$(state_get "$SLUG" published_src_sha)
if [ -n "$BASE" ] && git -C "$LOCAL" cat-file -e "$BASE^{commit}" 2>/dev/null; then
    git -C "$LOCAL" switch -q -c "$BRANCH" "$BASE"
    info "$BRANCH (from the last published commit $(echo "$BASE" | cut -c1-7))"
else
    git -C "$LOCAL" switch -q -c "$BRANCH"
    info "$BRANCH (from $ORIG_BRANCH - no published commit on record, so the diff also shows local work since then as removed)"
fi

step 5 "copying the deliverable back"
# Only the paths the deliverable owns. Each is mirrored so deletions on the OneDrive side show up
# in the diff; nothing outside these paths is touched, so local tooling files are safe.
for dir in "$ONEDRIVE"/*.Report "$ONEDRIVE"/*.SemanticModel; do
    [ -d "$dir" ] || continue
    name=$(basename "$dir")
    set +e
    robocopy "$(win_path "$ONEDRIVE/$name")" "$(win_path "$LOCAL/$name")" //MIR //NFL //NDL //NJH //NJS //NP //R:2 //W:2 >/dev/null 2>&1
    RC=$?
    set -e
    robocopy_ok "$RC" || die "robocopy failed ($RC) on $name - your branch $BRANCH is partially written; inspect it before switching away"
    info "$name"
done

for pbip in "$ONEDRIVE"/*.pbip; do
    [ -f "$pbip" ] || continue
    f=$(basename "$pbip")
    cp "$pbip" "$LOCAL/$f"; info "$f"
done
[ -f "$ONEDRIVE/CHANGELOG.md" ] && { cp "$ONEDRIVE/CHANGELOG.md" "$LOCAL/CHANGELOG.md"; info "CHANGELOG.md"; }
# The deliverable README maps back to the client-README source, never over the tooling README.
[ -f "$ONEDRIVE/README.md" ] && { cp "$ONEDRIVE/README.md" "$LOCAL/README.client.md"; info "README.md -> README.client.md"; }

step 6 "committing the review branch"
git -C "$LOCAL" add -A
if git -C "$LOCAL" diff --cached --quiet; then
    info "no differences - the deliverable matches your working copy"
    git -C "$LOCAL" switch -q "$ORIG_BRANCH"
    git -C "$LOCAL" branch -q -D "$BRANCH"
    printf '\nNothing to pull. Back on %s, review branch removed.\n' "$ORIG_BRANCH"
    exit 0
fi
git -C "$LOCAL" commit -q -m "pull: deliverable state from OneDrive ($TS)"
info "$(git -C "$LOCAL" log -1 --format='%h %s')"

# Recorded so pbi-publish can tell "drift that was pulled and merged" from "drift nobody has seen".
if [ -d "$ONEDRIVE/.git" ]; then
    state_set "$SLUG" \
        pulled_onedrive_sha "$(git -C "$ONEDRIVE" rev-parse HEAD)" \
        pulled_commit_sha "$(git -C "$LOCAL" rev-parse HEAD)"
fi

printf '\nPulled onto %s. Review and merge:\n' "$BRANCH"
printf '  git -C "%s" diff %s^..%s\n' "$LOCAL" "$BRANCH" "$BRANCH"
printf '  git -C "%s" switch %s && git merge %s\n' "$LOCAL" "$ORIG_BRANCH" "$BRANCH"
printf '\nYou are currently ON %s. Switch back when done.\n' "$BRANCH"
