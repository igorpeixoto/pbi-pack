#!/bin/sh
# Sync this repo's user/CLAUDE.md into ~/.claude/CLAUDE.md, the user-level instructions Claude Code
# loads in EVERY project on this machine.
#
# Only the <!-- BEGIN pbi-pack-user --> .. <!-- END pbi-pack-user --> span is replaced; anything
# else in ~/.claude/CLAUDE.md (your own notes, other tools' blocks) is left exactly as it is. If the
# home file has no span yet, the legacy <!-- BEGIN power-bi-skills --> block is replaced instead
# (that is what lived there before this script), and failing that the span is appended.
#
# Called by the pre-commit, post-merge and post-checkout hooks; safe to run by hand at any time:
#   sh scripts/sync-user-claude.sh            # refuses if the span was edited in ~/.claude
#   sh scripts/sync-user-claude.sh --force    # overwrite such an edit (a backup is kept)
#
# One-way, repo -> home. The span is canonical here: an edit made directly in ~/.claude/CLAUDE.md
# would be lost on the next sync, so instead of silently overwriting it the script stops and says
# so. It knows the difference because it records the hash of what it last wrote
# (~/.claude/pbi-sync/state/user-claude.sha).

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT" || exit 1

LABEL="Sync"
FORCE=0
for a in "$@"; do
    case "$a" in
        --force) FORCE=1 ;;
        *) LABEL="$a" ;;
    esac
done

SRC="user/CLAUDE.md"
[ -f "$SRC" ] || exit 0

python - "$SRC" "${HOME}/.claude/CLAUDE.md" "${HOME}/.claude/pbi-sync/state/user-claude.sha" "$FORCE" "$LABEL" <<'PY'
import hashlib, io, os, re, shutil, sys

src_path, dest_path, state_path, force, label = sys.argv[1:6]
force = force == "1"
BEGIN, END = "<!-- BEGIN pbi-pack-user -->", "<!-- END pbi-pack-user -->"
LEGACY = ("<!-- BEGIN power-bi-skills -->", "<!-- END power-bi-skills -->")

def say(msg, err=False):
    print("[%s] %s" % (label, msg), file=sys.stderr if err else sys.stdout)

def read(path):
    with io.open(path, "rb") as f:
        return f.read().decode("utf-8")

def span(text, b, e):
    i = text.find(b)
    j = text.find(e, i + 1) if i >= 0 else -1
    return (i, j + len(e)) if i >= 0 and j >= 0 else None

def sha(text):
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:16]

src = read(src_path).replace("\r\n", "\n")
s = span(src, BEGIN, END)
if not s:
    say("%s has no %s..%s span - nothing to sync." % (src_path, BEGIN, END), True)
    sys.exit(1)
block = src[s[0]:s[1]]
new_sha = sha(block)

dest = read(dest_path) if os.path.exists(dest_path) else ""
nl = "\r\n" if "\r\n" in dest else "\n"
out_block = block.replace("\n", nl)

cur = span(dest, BEGIN, END)
if cur:
    current = dest[cur[0]:cur[1]]
    if sha(current) == new_sha:
        sys.exit(0)  # already current: stay silent
    last = read(state_path).strip() if os.path.exists(state_path) else ""
    if last and sha(current) != last and not force:
        say("~/.claude/CLAUDE.md: the pbi-pack-user block was edited there directly since the last sync,", True)
        say("so it was NOT overwritten. Move the edit into the pack's user/CLAUDE.md and commit, or rerun", True)
        say("  sh scripts/sync-user-claude.sh --force   (keeps a backup) to discard it.", True)
        sys.exit(0)
    new = dest[:cur[0]] + out_block + dest[cur[1]:]
    how = "replaced the pbi-pack-user block"
else:
    legacy = span(dest, *LEGACY)
    if legacy:
        new = dest[:legacy[0]] + out_block + dest[legacy[1]:]
        how = "replaced the legacy power-bi-skills block"
    else:
        sep = "" if not dest or dest.endswith(nl + nl) else (nl if dest.endswith(nl) else nl + nl)
        new = dest + sep + out_block + nl
        how = "appended the pbi-pack-user block"

if dest:
    bak = dest_path + ".bak-pbi-pack"
    shutil.copyfile(dest_path, bak)
os.makedirs(os.path.dirname(dest_path), exist_ok=True)
with io.open(dest_path, "wb") as f:
    f.write(new.encode("utf-8"))
os.makedirs(os.path.dirname(state_path), exist_ok=True)
with io.open(state_path, "w", encoding="utf-8") as f:
    f.write(new_sha + "\n")
say("~/.claude/CLAUDE.md: %s (previous version in CLAUDE.md.bak-pbi-pack)." % how)
PY
