#!/bin/sh
# Launch Claude Code with the pack's model / advisor ladder (CLAUDE.md §8).
#
#   sh ~/.claude/pbi-sync/bin/pbi-claude.sh [--opus] [claude args...]
#
# Rungs:
#   default   sonnet[1m] writes the code, opus advises, effort high (a cheaper coder gets more effort)
#   --opus    opus[1m] writes the code, fable advises (effort from your settings)
#   refusal   if the advisor is refused AT LAUNCH, the next rung is tried:
#               sonnet + opus  ->  sonnet + fable  ->  sonnet, no advisor
#               opus + fable   ->  opus + opus     ->  opus, no advisor
#             "no advisor" is launched on purpose so the failure is visible in the banner; the
#             skills then fall back to AskUserQuestion checkpoints at each consult point.
#
# Why a launcher: Claude Code has no advisor fallback setting. `--advisor <m>` EXITS AT LAUNCH when
# <m> cannot act as advisor (usage-credits consent not given for fable, org allowlist, unsupported
# pairing), while a saved `advisorModel` is silently dropped. A refusal is detected by a TIMING
# HEURISTIC: non-zero exit within LAUNCH_FAIL_SECONDS. A session that ends non-zero later is a
# real session and is NOT retried.
#
# Mid-session declines are not the launcher's job: an advisor that answers "declined" is escalated
# by you, inside the session, with `/advisor fable` (CLAUDE.md §8). The flags below take precedence
# over any `advisorModel` that `/advisor` saved, so the next launch starts from the ladder again.
#
#   CLAUDE_BIN                  the claude executable (default: `claude` on PATH)
#   PBI_CLAUDE_MAIN             sonnet (default) | opus  - same as --opus
#   PBI_CLAUDE_SONNET_EFFORT    default high; empty string = leave to your settings
#   PBI_CLAUDE_LAUNCH_SECONDS   default 20

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
MAIN="${PBI_CLAUDE_MAIN:-sonnet}"
SONNET_EFFORT="${PBI_CLAUDE_SONNET_EFFORT-high}"
LAUNCH_FAIL_SECONDS="${PBI_CLAUDE_LAUNCH_SECONDS:-20}"

if [ "$1" = "--opus" ]; then MAIN=opus; shift; fi

command -v "$CLAUDE_BIN" >/dev/null 2>&1 || {
    printf 'pbi-claude: %s not found on PATH. Set CLAUDE_BIN to the claude executable.\n' "$CLAUDE_BIN" >&2
    exit 127
}

note() { printf 'pbi-claude: %s\n' "$*" >&2; }

# launch <model> <advisor> <effort-or-empty> [claude args...]
# Returns 1 on a launch refusal (retry the next rung); 0 when a session actually ran (exit with RC).
launch() {
    model=$1; advisor=$2; effort=$3; shift 3
    note "$model writes the code, $advisor advises${effort:+, effort $effort}"
    START=$(date +%s)
    if [ -n "$effort" ]; then
        "$CLAUDE_BIN" --model "$model" --advisor "$advisor" --effort "$effort" "$@"
    else
        "$CLAUDE_BIN" --model "$model" --advisor "$advisor" "$@"
    fi
    RC=$?
    ELAPSED=$(( $(date +%s) - START ))
    if [ "$RC" -ne 0 ] && [ "$ELAPSED" -le "$LAUNCH_FAIL_SECONDS" ]; then
        note "refused at launch (exit $RC after ${ELAPSED}s)"
        return 1
    fi
    return 0
}

case "$MAIN" in
    sonnet)
        launch "sonnet[1m]" opus "$SONNET_EFFORT" "$@" && exit "$RC"
        launch "sonnet[1m]" fable "$SONNET_EFFORT" "$@" && exit "$RC"
        note "no advisor could be attached - launching without one; consult points fall back to AskUserQuestion checkpoints (CLAUDE.md §8)"
        if [ -n "$SONNET_EFFORT" ]; then exec "$CLAUDE_BIN" --model "sonnet[1m]" --effort "$SONNET_EFFORT" "$@"; fi
        exec "$CLAUDE_BIN" --model "sonnet[1m]" "$@"
        ;;
    opus)
        launch "opus[1m]" fable "" "$@" && exit "$RC"
        note "fable refused - if this is the one-time usage-credits consent, run /model fable once inside a session"
        launch "opus[1m]" opus "" "$@" && exit "$RC"
        note "no advisor could be attached - launching without one; consult points fall back to AskUserQuestion checkpoints (CLAUDE.md §8)"
        exec "$CLAUDE_BIN" --model "opus[1m]" "$@"
        ;;
    *)
        note "PBI_CLAUDE_MAIN must be sonnet or opus (got '$MAIN')"; exit 2 ;;
esac
