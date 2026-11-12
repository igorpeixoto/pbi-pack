#!/bin/sh
# Merge this repo's user/settings.json into ~/.claude/settings.json, the user-level Claude Code
# settings that apply in EVERY project on this machine.
#
#   sh scripts/sync-user-settings.sh             # merge the pack's managed keys into this machine
#   sh scripts/sync-user-settings.sh --capture   # the reverse: copy this machine's current values of
#                                                # the managed keys into user/settings.json, to commit
#                                                # (not the permission lists: edit those in the pack)
#
# Only the keys listed in user/settings.json are managed; every other key in ~/.claude/settings.json
# (hooks wired by install-pbi-sync.sh, machine-specific env, plugins, ...) is left as it is.
#
# It is a three-way merge against what this script last wrote here
# (~/.claude/pbi-sync/state/user-settings.json), so a setting changed locally — by hand, or by
# /model, /effort, /config, which write to the same file — is never silently overwritten:
#   - unchanged here since the last sync      -> takes the pack's value
#   - changed here, pack unchanged            -> local value kept (reported once; --capture to share it)
#   - changed here AND in the pack            -> local value kept, reported as a conflict
#   - env                                     -> managed variable by variable under the same three
#                                                rules; variables only this machine sets stay
#   - permissions.allow / deny / ask          -> merged entry by entry: entries added to the pack are
#                                                added, entries removed from the pack are removed,
#                                                entries that exist only on this machine stay
# On the first run on a machine there is nothing to compare against, so the pack's values win.
#
# Called by the pre-commit, post-merge and post-checkout hooks (via sync-home.sh).

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT" || exit 1

LABEL="Sync"
MODE="merge"
for a in "$@"; do
    case "$a" in
        --capture) MODE="capture" ;;
        *) LABEL="$a" ;;
    esac
done

SRC="user/settings.json"
[ -f "$SRC" ] || exit 0

python - "$SRC" "${HOME}/.claude/settings.json" "${HOME}/.claude/pbi-sync/state/user-settings.json" "$MODE" "$LABEL" <<'PY'
import copy, io, json, os, re, shutil, sys

src_path, dest_path, state_path, mode, label = sys.argv[1:6]
LISTS = ("allow", "deny", "ask")   # permission lists merged entry by entry
SECRET = re.compile(r"(api[_-]?key|token|secret|passw|pwd|credential|connection[_-]?string|sk-ant-)", re.I)
MISSING = object()

def say(msg, err=False):
    print("[%s] %s" % (label, msg), file=sys.stderr if err else sys.stdout)

def load(path, default=None):
    if not os.path.exists(path):
        return default
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp-pbi-pack"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)   # atomic: Claude Code may be reading the file right now

def managed(pack):
    """Flatten the pack file into (path, value) pairs; permissions and env are managed key by key,
    so a machine's own env variables and permission keys are never replaced wholesale."""
    out = {}
    for k, v in pack.items():
        if k.startswith("$"):
            continue
        if k in ("permissions", "env") and isinstance(v, dict):
            for pk, pv in v.items():
                out[(k, pk)] = pv
        else:
            out[(k,)] = v
    return out

def get(d, path):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return MISSING
        d = d[p]
    return d

def put(d, path, value):
    for p in path[:-1]:
        d = d.setdefault(p, {})
    d[path[-1]] = value

def name(path):
    return ".".join(path)

try:
    pack = load(src_path)
    local = load(dest_path, {})
except ValueError as e:
    say("cannot parse JSON (%s) - nothing changed." % e, True)
    sys.exit(1)

# Refuse to ever carry something that looks like a secret through git.
for path, v in managed(pack).items():
    blob = json.dumps({name(path): v})
    if SECRET.search(blob):
        say("user/settings.json: %s looks like it holds a secret - refusing to sync it. Keep secrets local." % name(path), True)
        sys.exit(1)

if mode == "capture":
    changed = []
    for path in managed(pack):
        if path[0] == "permissions" and path[1] in LISTS:
            continue   # never sweep a machine's one-off approvals into the pack: edit these lists in the pack
        cur = get(local, path)
        if cur is not MISSING and cur != get(pack, path):
            put(pack, path, cur)
            changed.append(name(path))
    if changed:
        write_json(src_path, pack)
        say("user/settings.json: captured this machine's %s - review and commit to share it." % ", ".join(changed))
    else:
        say("user/settings.json already matches this machine.")
    sys.exit(0)

base_all = load(state_path, None)
first_run = base_all is None
base = {tuple(k.split("\x1f")): v for k, v in (base_all or {}).items()}

new = copy.deepcopy(local)
notes, applied = [], []
for path, pv in managed(pack).items():
    lv = get(local, path)
    bv = base.get(path, MISSING)
    if path[0] == "permissions" and path[1] in LISTS and isinstance(pv, list):
        lset = list(lv) if isinstance(lv, list) else []
        bset = set(bv) if isinstance(bv, list) else set()
        added = [x for x in pv if x not in bset and x not in lset]
        removed = [x for x in bset if x not in pv and x in lset]
        if added or removed:
            put(new, path, [x for x in lset if x not in removed] + added)
            applied.append("%s (+%d/-%d)" % (name(path), len(added), len(removed)))
        continue
    if lv == pv:
        continue
    if first_run or lv == bv or (lv is MISSING and bv is MISSING):
        put(new, path, copy.deepcopy(pv))
        applied.append(name(path))
    elif pv == bv:
        notes.append("%s is changed on this machine (%s); the pack has %s. Kept the local value - to share it, "
                     "run 'sh scripts/sync-user-settings.sh --capture' in %s and commit."
                     % (name(path), json.dumps(lv), json.dumps(pv), os.getcwd()))
    else:
        notes.append("CONFLICT %s: this machine has %s, the pack changed it to %s. Kept the local value - "
                     "remove it from ~/.claude/settings.json to take the pack's, or --capture to keep yours."
                     % (name(path), json.dumps(lv), json.dumps(pv)))

if applied:
    if os.path.exists(dest_path):
        shutil.copyfile(dest_path, dest_path + ".bak-pbi-pack")
    write_json(dest_path, new)
    say("~/.claude/settings.json: applied %s (previous version in settings.json.bak-pbi-pack)." % ", ".join(applied))

# Remember what the pack said, for the next three-way merge. Report each local divergence once.
write_json(state_path, {"\x1f".join(p): v for p, v in managed(pack).items()})
seen_path = state_path + ".reported"
seen = set(load(seen_path, []))
fresh = [n for n in notes if n not in seen]
for n in fresh:
    say(n, True)
# The merge usually runs inside the background auto-pull, whose output nobody sees: queue the notices
# for the next SessionStart, which prints and clears this file.
if fresh:
    with io.open(os.path.join(os.path.dirname(state_path), "notices.log"), "a", encoding="utf-8") as f:
        for n in fresh:
            f.write("settings: " + n + "\n")
write_json(seen_path, sorted(seen | set(fresh)) if notes else [])
PY
