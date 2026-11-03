#!/bin/sh
# Publish a local Power BI working repo to its OneDrive deliverable folder.
#
#   sh ~/.claude/pbi-sync/bin/pbi-publish.sh [<slug>|.] [options]
#
#   --init                    first publish into this target: re-initialise the deliverable
#                             repo (snapshotted first). Required once per project.
#   --dry-run                 build and verify staging, print what would change, touch nothing.
#   --force-overwrite         publish even though the OneDrive side drifted. Discards their work.
#   --allow-claude-mentions   let a published .md mention Claude (default: hard abort).
#   --min-ratio <n>           file-count floor vs. the last publish, in percent (default 60).
#
# Design contract: the OneDrive folder is a publish TARGET, never a working copy. This script is
# its only writer. Nothing touches OneDrive until every gate below has passed.

set -e
# shellcheck source=pbi-common.sh
. "$(dirname "$0")/pbi-common.sh"

SLUG=""; DO_INIT=0; DRY=0; FORCE=0; ALLOW_CLAUDE=0
while [ $# -gt 0 ]; do
    case "$1" in
        --init) DO_INIT=1 ;;
        --dry-run) DRY=1 ;;
        --force-overwrite) FORCE=1 ;;
        --allow-claude-mentions) ALLOW_CLAUDE=1 ;;
        --min-ratio) shift; MIN_FILE_RATIO="$1" ;;
        -*) die "unknown option: $1" ;;
        *) SLUG="$1" ;;
    esac
    shift
done

SLUG=$(resolve_slug "$SLUG")
[ -n "$SLUG" ] || die "no project given and the current directory is not a registered project. Register it with pbi-register.sh, or pass a slug."

LOCAL=$(reg_field "$SLUG" local) || die "$SLUG is not in the registry ($REGISTRY)"
ONEDRIVE=$(reg_field "$SLUG" onedrive) || die "$SLUG has no onedrive path in the registry"
EXTRAS=$(reg_field "$SLUG" extra_publish 2>/dev/null || true)

[ -d "$LOCAL" ] || die "local path does not exist: $LOCAL"
[ -d "$LOCAL/.git" ] || die "local path is not a git repo: $LOCAL"
[ -d "$ONEDRIVE" ] || die "onedrive path does not exist: $ONEDRIVE"

printf 'pbi-sync publish: %s\n  local:    %s\n  onedrive: %s\n' "$SLUG" "$LOCAL" "$ONEDRIVE"

acquire_lock "$SLUG"
trap release_lock EXIT INT TERM

# --- Gate 1: Power BI Desktop must be closed -------------------------------------------------
# Desktop holds file locks and rewrites .pbi/ caches while open. Publishing under it races both
# the source read and the target write.
step 1 "Power BI Desktop closed?"
if desktop_running; then
    die "Power BI Desktop is running. Close it and re-run - it locks files and rewrites .pbi/ caches mid-copy."
fi
info "not running"

# --- Gate 2: the local repo must be clean and committed --------------------------------------
# A publish has to correspond to a commit, otherwise there is nothing to roll back to and no
# SHA to stamp the deliverable commit with.
step 2 "local repo committed?"
DIRTY=$(git -C "$LOCAL" status --porcelain)
if [ -n "$DIRTY" ]; then
    printf '%s\n' "$DIRTY" | sed 's/^/    /' >&2
    die "the local repo has uncommitted changes (above). Commit or stash them first - a publish must map to a commit."
fi
SRC_SHA=$(git -C "$LOCAL" rev-parse --short HEAD)
SRC_MSG=$(git -C "$LOCAL" log -1 --format=%s)
info "HEAD $SRC_SHA - $SRC_MSG"

# --- Build staging (allowlist) ---------------------------------------------------------------
# Allowlist, not denylist: a tooling file added to the project later must not be able to leak
# into OneDrive just because nobody remembered to exclude it.
step 3 "building the deliverable in staging"
STAGE="$STAGE_DIR/$SLUG"
rm -rf "$STAGE"; mkdir -p "$STAGE"

PBIP=$(find "$LOCAL" -maxdepth 1 -name '*.pbip' | head -1)
[ -n "$PBIP" ] || die "no .pbip file at the root of $LOCAL"
cp "$PBIP" "$STAGE/"

for d in "$LOCAL"/*.Report "$LOCAL"/*.SemanticModel; do
    [ -d "$d" ] || continue
    cp -r "$d" "$STAGE/"
done

[ -f "$LOCAL/CHANGELOG.md" ] && cp "$LOCAL/CHANGELOG.md" "$STAGE/"

# The client-facing README is a separate source file. The repo's own README.md is tooling
# documentation and never publishes.
if [ -f "$LOCAL/README.client.md" ]; then
    cp "$LOCAL/README.client.md" "$STAGE/README.md"
else
    warn "no README.client.md in $LOCAL - the deliverable will ship without a README."
fi

# Anything else the project declares as a deliverable asset (icons, themes, logos).
if [ -n "$EXTRAS" ]; then
    printf '%s\n' "$EXTRAS" | while IFS= read -r x; do
        [ -n "$x" ] || continue
        if [ -e "$LOCAL/$x" ]; then
            cp -r "$LOCAL/$x" "$STAGE/"
            info "extra: $x"
        else
            warn "extra_publish entry not found, skipped: $x"
        fi
    done
fi

# Hard Rule 19: without .gitattributes the deliverable repo takes the full CRLF churn every time
# Desktop resaves TMDL/PBIR. Generate the canonical one if the project lacks it.
if [ -f "$LOCAL/.gitattributes" ]; then
    cp "$LOCAL/.gitattributes" "$STAGE/"
else
    warn "$LOCAL has no .gitattributes - generating the canonical one into the deliverable."
    {
        printf '* text=auto eol=lf\n'
        printf '*.pbip     text eol=lf\n'
        printf '*.pbir     text eol=lf\n'
        printf '*.pbism    text eol=lf\n'
        printf '*.platform text eol=lf\n'
        printf '*.tmdl     text eol=lf\n'
        printf '*.json     text eol=lf\n'
        printf '*.pq       text eol=lf\n'
        printf '*.dax      text eol=lf\n'
        printf '*.m        text eol=lf\n'
    } > "$STAGE/.gitattributes"
fi

# The deliverable repo's own ignore rules. Short by construction: publish already strips tooling
# at the staging step, so this only needs to cover what Desktop and OneDrive generate in place.
{
    printf '# Power BI Desktop machine-local session files\n'
    printf '**/.pbi/localSettings.json\n'
    printf '**/.pbi/cache.abf\n'
    printf '*.pbi.json\n\n'
    printf '# Local backup copies\n'
    printf 'backups/\n\n'
    printf '# OneDrive sync conflict copies\n'
    if [ -n "$CONFLICT_SUFFIX" ]; then printf '*-%s.*\n' "$CONFLICT_SUFFIX"; fi
    printf '*conflicted copy*\n'
} > "$STAGE/.gitignore"

# Prune what Desktop leaves behind inside the copied definition folders.
find "$STAGE" -path '*/.pbi/*' -name 'localSettings.json' -delete
find "$STAGE" -path '*/.pbi/*' -name 'cache.abf' -delete
if [ -n "$CONFLICT_SUFFIX" ]; then find "$STAGE" -iname "*-$CONFLICT_SUFFIX.*" -delete; fi
find "$STAGE" -iname '*conflicted copy*' -delete
find "$STAGE" -type d -name '.pbi' -empty -delete

STAGE_FILES=$(find "$STAGE" -type f | wc -l | tr -d ' ')
info "$STAGE_FILES files staged"

# --- Gate 3: leak check ----------------------------------------------------------------------
# The one constraint that must never fail: no Claude tooling may reach a synced path.
step 4 "leak check (no Claude tooling in the deliverable)"
LEAK=$(find "$STAGE" \( -name '.claude' -o -name 'CLAUDE.md' -o -name 'RELEASING.md' \
        -o -name '.git' -o -name 'docs' -o -name 'backups' -o -name 'settings.local.json' \
        -o -name 'README.client.md' \) -print)
if [ -n "$LEAK" ]; then
    printf '%s\n' "$LEAK" | sed 's/^/    /' >&2
    die "tooling paths reached staging (above). This is a bug in the allowlist - publish aborted."
fi
# Scan EVERY text file, not just .md. This originally checked --include='*.md' and missed twenty
# CLAUDE.md citations sitting in M and DAX comments inside .tmdl - one of them inside a refresh
# error message the client would actually see on screen. -I skips binaries (PNGs, .pbiviz).
MENTIONS=$(grep -rilI -e claude -e gemini "$STAGE" 2>/dev/null || true)
if [ -n "$MENTIONS" ] && [ "$ALLOW_CLAUDE" -eq 0 ]; then
    printf '%s\n' "$MENTIONS" | sed 's/^/    /' >&2
    printf '  matching lines:\n' >&2
    printf '%s\n' "$MENTIONS" | while IFS= read -r f; do
        grep -inI -e claude -e gemini "$f" 2>/dev/null | head -3 | sed "s|^|    $(basename "$f"):|" >&2
    done
    die "the files above still mention the development tooling. Fix them at the source, or pass --allow-claude-mentions."
fi
info "clean"

# --- Gate 4: structural verification ---------------------------------------------------------
# A .pbip is ~200 bytes of JSON pointing at its siblings; its presence proves nothing. Check the
# things whose absence actually breaks the deliverable.
step 5 "structural verification"
N_PBIP=$(find "$STAGE" -maxdepth 1 -name '*.pbip' | wc -l | tr -d ' ')
[ "$N_PBIP" -eq 1 ] || die "expected exactly one .pbip in the deliverable, found $N_PBIP"
find "$STAGE" -path '*.SemanticModel/definition/model.tmdl' | grep -q . \
    || die "no *.SemanticModel/definition/model.tmdl in the deliverable"
N_PAGES=$(find "$STAGE" -path '*.Report/definition/pages/*' -name 'page.json' | wc -l | tr -d ' ')
[ "$N_PAGES" -ge 1 ] || die "no report pages found in the deliverable"
info ".pbip ok - model.tmdl ok - $N_PAGES pages"

# --- Gate 5: no collapse vs. the last publish ------------------------------------------------
step 6 "size sanity vs. last publish"
PREV_FILES=$(state_get "$SLUG" published_files)
if [ -n "$PREV_FILES" ] && [ "$PREV_FILES" -gt 0 ] 2>/dev/null; then
    FLOOR=$(( PREV_FILES * MIN_FILE_RATIO / 100 ))
    if [ "$STAGE_FILES" -lt "$FLOOR" ]; then
        die "the deliverable collapsed from $PREV_FILES files to $STAGE_FILES (floor $FLOOR at ${MIN_FILE_RATIO}%). This looks like a broken build, not an intentional deletion. Re-run with --min-ratio if it really is intentional."
    fi
    info "$STAGE_FILES vs $PREV_FILES previously (floor $FLOOR)"
else
    info "no previous publish recorded - skipped"
fi

# --- Gate 6: OneDrive drift ------------------------------------------------------------------
# The deliverable repo's own git status is the drift detector: it says not just that something
# changed, but what and who.
step 7 "OneDrive side unchanged since last publish?"
OD_IS_REPO=0
[ -d "$ONEDRIVE/.git" ] && OD_IS_REPO=1
if [ "$OD_IS_REPO" -eq 1 ] && [ "$DO_INIT" -eq 0 ]; then
    OD_DIRTY=$(git -C "$ONEDRIVE" status --porcelain)
    OD_HEAD=$(git -C "$ONEDRIVE" rev-parse HEAD 2>/dev/null || echo "")
    PREV_HEAD=$(state_get "$SLUG" published_onedrive_sha)
    if [ -n "$OD_DIRTY" ] && [ "$FORCE" -eq 0 ]; then
        printf '%s\n' "$OD_DIRTY" | sed 's/^/    /' >&2
        die "the OneDrive copy has uncommitted changes (above). Someone edited the deliverable directly. Run pbi-pull.sh to bring them into a branch here, or --force-overwrite to discard them."
    fi
    if [ -n "$PREV_HEAD" ] && [ "$OD_HEAD" != "$PREV_HEAD" ] && [ "$FORCE" -eq 0 ]; then
        # Drift that pbi-pull captured and that is now merged into what we publish is not lost by
        # overwriting it - let it through instead of forcing --force-overwrite on a clean merge.
        PULLED_OD=$(state_get "$SLUG" pulled_onedrive_sha)
        PULLED_COMMIT=$(state_get "$SLUG" pulled_commit_sha)
        if [ "$PULLED_OD" = "$OD_HEAD" ] && [ -n "$PULLED_COMMIT" ] \
            && git -C "$LOCAL" merge-base --is-ancestor "$PULLED_COMMIT" HEAD 2>/dev/null; then
            info "OneDrive edits were pulled ($(echo "$PULLED_COMMIT" | cut -c1-7)) and are merged into HEAD"
        else
            git -C "$ONEDRIVE" log --oneline "$PREV_HEAD..$OD_HEAD" 2>/dev/null | sed 's/^/    /' >&2 || true
            if [ "$PULLED_OD" = "$OD_HEAD" ]; then
                die "the OneDrive edits (above) were pulled but the review branch is not merged into HEAD yet. Merge it, or --force-overwrite to discard them."
            fi
            die "the OneDrive repo has commits you did not publish (above). Run pbi-pull.sh and merge its review branch, or --force-overwrite to discard them."
        fi
    else
        info "in sync"
    fi
elif [ "$DO_INIT" -eq 1 ]; then
    info "--init: skipping drift check"
else
    info "target is not a git repo yet - run once with --init"
    [ "$DRY" -eq 1 ] || die "first publish into this target must be run with --init"
fi

# --- Dry run stops here ----------------------------------------------------------------------
if [ "$DRY" -eq 1 ]; then
    step 8 "dry run - what would change"
    set +e
    robocopy "$(win_path "$STAGE")" "$(win_path "$ONEDRIVE")" //MIR //XD ".git" //L //NJH //NJS //NP //NDL 2>&1 | sed 's/^/    /' | head -40
    set -e
    printf '\nDry run complete. Nothing was written. Staging kept at:\n  %s\n' "$STAGE"
    exit 0
fi

# --- Snapshot --------------------------------------------------------------------------------
# Local, not inside OneDrive: a snapshot written into the synced folder would double the sync
# churn and is exactly the kind of mass write that trips retention heuristics.
step 8 "snapshotting the current OneDrive state (locally)"
TS=$(date +%Y%m%d-%H%M%S)
SNAP="$SNAP_DIR/$SLUG-$TS"
mkdir -p "$SNAP"
set +e
robocopy "$(win_path "$ONEDRIVE")" "$(win_path "$SNAP")" //E //NFL //NDL //NJH //NJS //NP //R:2 //W:2 >/dev/null 2>&1
RC=$?
set -e
robocopy_ok "$RC" || die "snapshot failed (robocopy $RC) - nothing was written to OneDrive"
info "$SNAP"
# Keep the three most recent snapshots per project.
# shellcheck disable=SC2012  # ls is safe here: these names are "<slug>-<timestamp>", written by this script
ls -1d "$SNAP_DIR/$SLUG-"* 2>/dev/null | sort -r | tail -n +4 | while IFS= read -r old; do rm -rf "$old"; done

# --- Re-initialise the deliverable repo on --init --------------------------------------------
if [ "$DO_INIT" -eq 1 ]; then
    step 9 "initialising the deliverable repo"
    if [ -d "$ONEDRIVE/.git" ]; then
        warn "removing the existing .git in the target - its history contains dev/tooling commits and is preserved in $LOCAL and on the GitHub remote."
        rm -rf "$ONEDRIVE/.git"
    fi
    git -C "$ONEDRIVE" init -q -b main
    # The deliverable is written by robocopy from a CRLF working tree while .gitattributes stores
    # LF. That is correct and intended, but git's default safecrlf=warn emits one warning per file
    # on every publish. Silence it here rather than at each call site.
    git -C "$ONEDRIVE" config core.safecrlf false
    info "fresh repo at $ONEDRIVE"
fi

# --- Mirror ----------------------------------------------------------------------------------
step 10 "mirroring staging into OneDrive"
set +e
robocopy "$(win_path "$STAGE")" "$(win_path "$ONEDRIVE")" //MIR //XD ".git" //NFL //NDL //NJH //NJS //NP //R:2 //W:2 >/dev/null 2>&1
RC=$?
set -e
if ! robocopy_ok "$RC"; then
    warn "robocopy failed ($RC) - restoring the snapshot"
    robocopy "$(win_path "$SNAP")" "$(win_path "$ONEDRIVE")" //MIR //NFL //NDL //NJH //NJS //NP >/dev/null 2>&1 || true
    die "mirror failed and the previous state was restored from $SNAP"
fi
info "mirrored"

# --- Post-copy verification ------------------------------------------------------------------
step 11 "verifying the target matches staging"
OD_FILES=$(find "$ONEDRIVE" -type f -not -path '*/.git/*' | wc -l | tr -d ' ')
if [ "$OD_FILES" -ne "$STAGE_FILES" ]; then
    warn "target has $OD_FILES files, staging had $STAGE_FILES - restoring the snapshot"
    robocopy "$(win_path "$SNAP")" "$(win_path "$ONEDRIVE")" //MIR //NFL //NDL //NJH //NJS //NP >/dev/null 2>&1 || true
    die "post-copy verification failed; previous state restored from $SNAP"
fi
info "$OD_FILES files match"

# --- Commit the deliverable ------------------------------------------------------------------
step 12 "committing the deliverable"
git -C "$ONEDRIVE" add -A
if git -C "$ONEDRIVE" diff --cached --quiet; then
    info "no content change - nothing to commit"
else
    git -C "$ONEDRIVE" commit -q -m "publish: ${SRC_MSG}  [src ${SRC_SHA}]"
    info "$(git -C "$ONEDRIVE" log -1 --format='%h %s')"
fi
OD_HEAD=$(git -C "$ONEDRIVE" rev-parse HEAD)

state_set "$SLUG" \
    published_src_sha "$SRC_SHA" \
    published_onedrive_sha "$OD_HEAD" \
    published_files "$STAGE_FILES" \
    published_at "$(date -Iseconds)"

printf '\nPublished %s - %s files, src %s -> deliverable %s\n' "$SLUG" "$STAGE_FILES" "$SRC_SHA" "$(echo "$OD_HEAD" | cut -c1-7)"
