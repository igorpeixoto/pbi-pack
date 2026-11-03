#!/bin/sh
# Shared helpers for the pbi-sync publish workflow.
#
# Everything this file touches lives under ~/.claude/pbi-sync/, which is off every OneDrive
# sync root by design. Nothing here may ever be relocated into a synced path.

# The variables below read as unused here because the scripts that source this file use them.
# shellcheck disable=SC2034

PBI_SYNC_HOME="${PBI_SYNC_HOME:-$HOME/.claude/pbi-sync}"
REGISTRY="$PBI_SYNC_HOME/projects.json"
STATE_DIR="$PBI_SYNC_HOME/state"
LOCK_DIR="$PBI_SYNC_HOME/locks"
SNAP_DIR="$PBI_SYNC_HOME/snapshots"
STAGE_DIR="$PBI_SYNC_HOME/staging"
PENDING_LOG="$PBI_SYNC_HOME/pending.log"

# A publish whose file count collapses below this share of the previous publish is treated as a
# build failure, not an intentional deletion. Overridable per-run with --min-ratio.
MIN_FILE_RATIO="${MIN_FILE_RATIO:-60}"
# A lock older than this is assumed to be from a crashed run and can be reclaimed.
LOCK_STALE_SECONDS=7200
# OneDrive names a sync-conflict copy after the machine that lost the race: model-<machine>.tmdl,
# cache-<machine>.abf. Set PBI_CONFLICT_SUFFIX to that machine name and publish strips those from
# the deliverable and ignores them there (case-insensitive). Off by default: a short or common
# machine name (dev, pc) would match real files and delete them before any gate could notice, so
# unset relies on the generic "conflicted copy" pattern alone.
CONFLICT_SUFFIX="${PBI_CONFLICT_SUFFIX:-}"

die()  { printf 'pbi-sync: %s\n' "$*" >&2; exit 1; }
warn() { printf 'pbi-sync: %s\n' "$*" >&2; }
info() { printf '  %s\n' "$*"; }
step() { printf '\n[%s] %s\n' "$1" "$2"; }

# --- registry -------------------------------------------------------------------------------

# Every python helper below disables newline translation on stdout. Python on Windows rewrites
# '\n' as '\r\n', so a value read back into a shell variable carries a trailing CR that silently
# fails every later string comparison — it surfaced as `pbi-status` with no argument reporting
# registered projects as "not in the registry". Fixed inside python rather than by piping through
# `tr`, because a pipe would replace python's exit status with tr's and reg_field signals
# "no such project" with exit 3, which pbi-publish depends on.
reg_field() {
    python - "$REGISTRY" "$1" "$2" <<'PY'
import json, sys
sys.stdout.reconfigure(newline='')
try:
    reg = json.load(open(sys.argv[1], encoding='utf-8-sig'))
except Exception:
    sys.exit(4)
p = reg.get('projects', {}).get(sys.argv[2])
if p is None:
    sys.exit(3)
v = p.get(sys.argv[3])
if isinstance(v, list):
    sys.stdout.write('\n'.join(v))
else:
    sys.stdout.write('' if v is None else str(v))
PY
}

reg_slugs() {
    python - "$REGISTRY" <<'PY'
import json, sys
sys.stdout.reconfigure(newline='')
try:
    reg = json.load(open(sys.argv[1], encoding='utf-8-sig'))
except Exception:
    sys.exit(0)
sys.stdout.write('\n'.join(reg.get('projects', {})))
PY
}

# Resolve a slug from an explicit argument, or from the current directory by finding the
# registered project whose local path is a prefix of $PWD. Returns empty if unregistered.
resolve_slug() {
    if [ -n "$1" ] && [ "$1" != "." ]; then printf '%s' "$1"; return 0; fi
    python - "$REGISTRY" "$(pwd -W 2>/dev/null || pwd)" <<'PY'
import json, sys, os
sys.stdout.reconfigure(newline='')
try:
    reg = json.load(open(sys.argv[1], encoding='utf-8-sig'))
except Exception:
    sys.exit(0)
cwd = os.path.normcase(os.path.abspath(sys.argv[2].replace('/', os.sep)))
best, best_len = '', -1
for slug, p in reg.get('projects', {}).items():
    loc = p.get('local')
    if not loc:
        continue
    loc = os.path.normcase(os.path.abspath(loc.replace('/', os.sep)))
    if cwd == loc or cwd.startswith(loc + os.sep):
        if len(loc) > best_len:
            best, best_len = slug, len(loc)
sys.stdout.write(best)
PY
}

# --- per-project state ----------------------------------------------------------------------

state_file() { printf '%s/%s.json' "$STATE_DIR" "$1"; }

state_get() {
    f=$(state_file "$1")
    [ -f "$f" ] || { printf ''; return 0; }
    python - "$f" "$2" <<'PY'
import json, sys
sys.stdout.reconfigure(newline='')
try:
    d = json.load(open(sys.argv[1], encoding='utf-8-sig'))
except Exception:
    sys.exit(0)
v = d.get(sys.argv[2])
sys.stdout.write('' if v is None else str(v))
PY
}

state_set() {
    f=$(state_file "$1"); shift
    mkdir -p "$STATE_DIR"
    python - "$f" "$@" <<'PY'
import json, sys, os
path = sys.argv[1]
d = {}
if os.path.exists(path):
    try:
        d = json.load(open(path, encoding='utf-8-sig'))
    except Exception as e:
        # Never fall back to {} and write: that silently erases the existing state.
        sys.exit('pbi-sync: cannot parse %s (%s) - fix or remove it by hand' % (path, e))
args = sys.argv[2:]
for i in range(0, len(args) - 1, 2):
    d[args[i]] = args[i + 1]
tmp = path + '.tmp'
json.dump(d, open(tmp, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
os.replace(tmp, path)
PY
}

# --- locking --------------------------------------------------------------------------------
# mkdir is atomic on NTFS, so it is the lock primitive. A lock is a directory holding a stamp
# file; a stale one (crashed run) is reclaimable after LOCK_STALE_SECONDS.

acquire_lock() {
    mkdir -p "$LOCK_DIR"
    _lock="$LOCK_DIR/$1.lock"
    if ! mkdir "$_lock" 2>/dev/null; then
        _age=$(( $(date +%s) - $(cat "$_lock/stamp" 2>/dev/null || echo 0) ))
        if [ "$_age" -gt "$LOCK_STALE_SECONDS" ]; then
            warn "reclaiming a stale lock for '$1' (${_age}s old, held by PID $(cat "$_lock/pid" 2>/dev/null || echo '?'))"
            rm -rf "$_lock"; mkdir "$_lock" || die "could not reclaim the lock for '$1'"
        else
            die "another pbi-sync run holds the lock for '$1' (PID $(cat "$_lock/pid" 2>/dev/null || echo '?'), ${_age}s old). Wait for it, or remove $_lock if you are sure it is dead."
        fi
    fi
    date +%s > "$_lock/stamp"; echo "$$" > "$_lock/pid"
    PBI_LOCK_PATH="$_lock"
}

release_lock() { [ -n "$PBI_LOCK_PATH" ] && rm -rf "$PBI_LOCK_PATH"; PBI_LOCK_PATH=""; }

# --- environment guards ---------------------------------------------------------------------

desktop_running() {
    tasklist //FI "IMAGENAME eq PBIDesktop.exe" //NH 2>/dev/null | grep -qi PBIDesktop
}

win_path() { cygpath -w "$1"; }

# robocopy returns a bitmask: 0-7 are success variants, >=8 is a real failure.
robocopy_ok() { [ "$1" -lt 8 ]; }
