#!/bin/sh
# Fails when any forbidden term appears in a tracked or staged file.
#   -I  skip binary files      -i  ignore case
#   -E  each line of the list is an extended regex
#   -f  read the patterns from the denylist file
# The list itself lives in a gitignored file (or a CI secret) so it never leaks the names it guards.
set -eu
DENY="${DENYLIST_FILE:-.denylist}"
if [ ! -s "$DENY" ]; then
  echo "check-denylist: no denylist at $DENY, skipping" >&2
  exit 0
fi
# git grep exits 0 on a match, 1 on no match, and higher on an error such as an invalid regex.
# Only a real "no match" may count as clean.
rc=0
git grep -nIiE -f "$DENY" -- . ':!.denylist' ':!docs/public-release/' || rc=$?
case "$rc" in
  0) echo "check-denylist: forbidden term found (see lines above)" >&2; exit 1 ;;
  1) echo "check-denylist: clean" ;;
  *) echo "check-denylist: git grep failed (exit $rc), check the patterns in $DENY" >&2; exit 2 ;;
esac
