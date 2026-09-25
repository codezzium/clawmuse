# Sourced by bin/muse-ask and the hooks. Sets PY to a command that runs Python 3.8+,
# or to an empty string. Every candidate is actually run: on Windows, `python3` and
# `python` are often Microsoft Store stubs that only print an install hint.
PY=
for _c in python3 python "py -3"; do
  if $_c -c 'import sys; sys.exit(sys.version_info < (3, 8))' >/dev/null 2>&1; then
    PY=$_c
    break
  fi
done
unset _c
