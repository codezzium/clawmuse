#!/usr/bin/env bash
# UserPromptSubmit: see user_prompt.py. Silent when no Python is available.
root="${CLAUDE_PLUGIN_ROOT:-$(cd "${0%/*}/.." && pwd)}"
. "$root/lib/find-python.sh"
[ -n "$PY" ] || exit 0
exec $PY "$root/hooks/user_prompt.py"
