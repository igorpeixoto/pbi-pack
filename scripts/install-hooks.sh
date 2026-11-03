#!/bin/sh
# Install every tracked git hook into .git/hooks/.
#
# Git hooks are never tracked by git, so .git/hooks/ starts empty on a fresh clone and on every
# other machine. Run this once per clone:
#   sh scripts/install-hooks.sh
# After that the hooks keep themselves current: pre-commit, post-merge and post-checkout call this
# script whenever scripts/git-hooks/ changes.
#
# Each hook is written to a temp file and renamed into place, never overwritten in place: this
# script is often run BY one of these hooks, and a shell reads its script as it executes, so
# rewriting the running file in place makes the shell resume at a stale offset in the new text.

set -e

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

for hook in pre-commit post-merge post-checkout; do
    cp "scripts/git-hooks/$hook" ".git/hooks/$hook.tmp-install"
    chmod +x ".git/hooks/$hook.tmp-install"
    mv -f ".git/hooks/$hook.tmp-install" ".git/hooks/$hook"
    echo "installed .git/hooks/$hook"
done

echo "Done. Hooks active for this clone."
