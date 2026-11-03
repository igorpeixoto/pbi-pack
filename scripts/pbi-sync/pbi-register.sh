#!/bin/sh
# Add or update a project in the registry.
#
#   sh ~/.claude/pbi-sync/bin/pbi-register.sh <slug> <local-path> <onedrive-path> [extra ...]
#
# <extra> entries are additional deliverable paths relative to the project root (asset folders,
# themes, logos) that are not covered by the standard allowlist.

set -e
# shellcheck source=pbi-common.sh
. "$(dirname "$0")/pbi-common.sh"

SLUG="$1"; LOCAL="$2"; ONEDRIVE="$3"
shift 3 2>/dev/null || true
# shellcheck disable=SC2015  # die must run when either test fails, which is what && || does here
[ -n "$SLUG" ] && [ -n "$LOCAL" ] && [ -n "$ONEDRIVE" ] \
    || die "usage: pbi-register.sh <slug> <local-path> <onedrive-path> [extra ...]"

[ -d "$ONEDRIVE" ] || warn "onedrive path does not exist yet: $ONEDRIVE"
[ -d "$LOCAL" ] || warn "local path does not exist yet: $LOCAL"

# Refuse to register a local path that sits inside a OneDrive root. The whole point of this
# workflow is that the working copy lives where sync cannot reach it.
case "$(printf '%s' "$LOCAL" | tr '[:upper:]' '[:lower:]')" in
    *onedrive*) die "the local working path is inside a OneDrive folder: $LOCAL - that defeats the workflow. Clone it somewhere unsynced first." ;;
esac

mkdir -p "$(dirname "$REGISTRY")"
python - "$REGISTRY" "$SLUG" "$LOCAL" "$ONEDRIVE" "$@" <<'PY'
import json, os, sys

path, slug, local, onedrive = sys.argv[1:5]
extras = [e for e in sys.argv[5:] if e]

reg = {"projects": {}}
if os.path.exists(path):
    # utf-8-sig: editors on Windows may save the registry with a BOM, which plain utf-8 rejects.
    # A registry that does not parse aborts the run - falling back to an empty one and writing it
    # back is exactly how every other project's entry got erased.
    try:
        reg = json.load(open(path, encoding='utf-8-sig'))
    except Exception as e:
        sys.exit('pbi-register: cannot parse %s (%s) - nothing was written. Fix the file by hand.' % (path, e))
reg.setdefault("projects", {})

entry = reg["projects"].get(slug, {})
entry["local"] = local.replace('/', '\\')
entry["onedrive"] = onedrive.replace('/', '\\')
if extras:
    entry["extra_publish"] = extras
reg["projects"][slug] = entry

tmp = path + '.tmp'
json.dump(reg, open(tmp, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
os.replace(tmp, path)
print("registered: " + slug)
PY
