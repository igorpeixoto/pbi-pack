#!/bin/sh
# Install the pbi-sync publish tooling into ~/.claude/pbi-sync/, the runtime location the
# scripts and the session hooks are executed from.
#
#   sh scripts/install-pbi-sync.sh
#
# Run this once per machine, after cloning the pack. Safe to re-run at any time.
#
# Same shape as scripts/sync-skills.sh: one-way, repo -> home, and it overwrites. The pack is
# canonical; anything edited directly in ~/.claude/pbi-sync/bin/ is replaced on the next run.
#
# What it does NOT touch:
#   projects.json   the local <-> OneDrive registry. Machine-specific: the OneDrive half embeds
#                   this machine's Windows profile name, so it is created empty if missing and
#                   never overwritten. Register projects with pbi-register.sh.
#   state/          per-machine record of what was last published from here.
#   snapshots/      pre-publish rollback copies.

set -e

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || ROOT="."
cd "$ROOT"

SRC="scripts/pbi-sync"
DEST="${HOME}/.claude/pbi-sync"
LABEL="${1:-Install}"

[ -d "$SRC" ] || { echo "[$LABEL] no $SRC/ in this repo - nothing to install." >&2; exit 1; }

echo "[$LABEL] Installing $SRC/ -> $DEST/bin/..."
mkdir -p "$DEST/bin" "$DEST/state" "$DEST/locks" "$DEST/snapshots" "$DEST/staging"

for f in "$SRC"/*.sh; do
    name=$(basename "$f")
    cp "$f" "$DEST/bin/$name"
    chmod +x "$DEST/bin/$name"
    echo "[$LABEL]   -> $name"
done

# The registry is machine-specific and must survive re-runs.
if [ ! -f "$DEST/projects.json" ]; then
    cat > "$DEST/projects.json" <<'JSON'
{
  "$comment": "Registry mapping each local working repo to its OneDrive publish target. Lives under ~/.claude/ on purpose: a config file inside the working tree could ride along into OneDrive; this one physically cannot. Add entries with: sh ~/.claude/pbi-sync/bin/pbi-register.sh <slug> <local> <onedrive>",
  "projects": {}
}
JSON
    echo "[$LABEL]   created an empty projects.json (register projects with pbi-register.sh)"
else
    echo "[$LABEL]   kept the existing projects.json ($(python -c "
import json,io,sys
try: print(len(json.load(io.open(sys.argv[1],encoding='utf-8')).get('projects',{})))
except Exception: print('?')
" "$DEST/projects.json") project(s) registered)"
fi

# --- Wire the session hooks into the user settings ---------------------------------------------
# Idempotent, and it merges rather than replacing: everything already in settings.json survives.
echo "[$LABEL] Wiring SessionStart/SessionEnd hooks into ~/.claude/settings.json..."
python - "${HOME}/.claude/settings.json" <<'PY'
import json, io, os, sys

path = sys.argv[1]
s = {}
if os.path.exists(path):
    try:
        s = json.load(io.open(path, encoding='utf-8'))
    except Exception:
        print("      settings.json is not valid JSON - refusing to touch it.", file=sys.stderr)
        raise SystemExit(1)
    # Keep a one-off backup the first time this runs on a machine.
    bak = path + '.bak-pbi-sync'
    if not os.path.exists(bak):
        io.open(bak, 'w', encoding='utf-8').write(json.dumps(s, indent=2, ensure_ascii=False))

# All four sources: the hook itself prints only the project-state block on clear/compact.
START_MATCHER = "startup|resume|clear|compact"
start = {"matcher": START_MATCHER, "hooks": [{
    "type": "command", "shell": "bash",
    "command": "sh ~/.claude/pbi-sync/bin/hook-session-start.sh", "timeout": 15}]}
end = {"hooks": [{
    "type": "command", "shell": "bash",
    "command": "sh ~/.claude/pbi-sync/bin/hook-session-end.sh", "timeout": 10}]}

hooks = s.setdefault("hooks", {})

def ensure(event, entry, marker):
    existing = hooks.setdefault(event, [])
    for e in existing:
        for h in e.get("hooks", []):
            if marker in str(h.get("command", "")):
                # Migrate the matcher this installer wrote before clear/compact were handled. Any
                # other matcher is someone's own choice and is left alone.
                if event == "SessionStart" and e.get("matcher") == "startup|resume":
                    e["matcher"] = START_MATCHER
                    return "matcher widened to " + START_MATCHER
                return "already present"
    existing.append(entry)
    return "added"

r1 = ensure("SessionStart", start, "hook-session-start.sh")
r2 = ensure("SessionEnd", end, "hook-session-end.sh")

# Read-only status is safe to pre-approve. publish and pull stay prompted on purpose: they
# write outside the repo, into a shared client folder.
allow = s.setdefault("permissions", {}).setdefault("allow", [])
for rule in ["Bash(sh ~/.claude/pbi-sync/bin/pbi-status.sh *)",
             "Bash(sh ~/.claude/pbi-sync/bin/pbi-status.sh)"]:
    if rule not in allow:
        allow.append(rule)

# Model ladder defaults (CLAUDE.md §8: Sonnet codes, Opus advises), seeded ONLY when absent - a
# user's own choice is never overwritten. advisorModel is the second-opinion model; fallbackModel is unrelated to it and
# only covers a server-side outage of the main model mid-session (tried in order, that turn only).
seeded = []
if "model" not in s:
    s["model"] = "sonnet[1m]"; seeded.append("model=sonnet[1m]")
if "advisorModel" not in s:
    s["advisorModel"] = "opus"; seeded.append("advisorModel=opus")
if "fallbackModel" not in s:
    s["fallbackModel"] = ["opus[1m]"]; seeded.append("fallbackModel=[opus[1m]]")

json.dump(s, io.open(path, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print("      SessionStart: %s | SessionEnd: %s" % (r1, r2))
print("      advisor defaults: %s" % (", ".join(seeded) if seeded else "already set, left untouched"))
PY

echo "[$LABEL] Done."
echo
echo "  Next, per project on this machine:"
echo "    git clone <remote> C:/dev/pbi/<slug>"
echo "    sh ~/.claude/pbi-sync/bin/pbi-register.sh <slug> C:/dev/pbi/<slug> \"<onedrive path>\""
echo "    sh ~/.claude/pbi-sync/bin/pbi-status.sh"
echo
echo "  To start a session on the advisor ladder (Sonnet codes + Opus advises; --opus: Opus codes + Fable advises):"
echo "    sh ~/.claude/pbi-sync/bin/pbi-claude.sh"
