#!/usr/bin/env bash
# SessionStart: tell Claude that Muse is available for research and test runs.
# Silent when muse or Python is missing, or when this session was started from inside Muse.
[ -n "${CLAWMUSE_DEPTH:-}" ] && exit 0
command -v "${CLAWMUSE_MUSE:-muse}" >/dev/null 2>&1 || exit 0
root="${CLAUDE_PLUGIN_ROOT:-$(cd "${0%/*}/.." && pwd)}"
. "$root/lib/find-python.sh"
[ -n "$PY" ] || exit 0
cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"clawmuse is active: Muse (Meta's Muse Spark coding agent) runs as a delegate through the `muse-ask` command, and its work costs none of your context or the user's Claude quota. Default to delegating research (exploring several files, where/how does X work, web or docs lookups, long logs) and test/build runs to it instead of doing them yourself or spawning Explore/general-purpose subagents; load the clawmuse:muse skill for usage before the first call. Keep small targeted reads, edits and final verification yourself."}}
EOF
