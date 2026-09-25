#!/usr/bin/env python3
"""UserPromptSubmit: when the user names Muse in a message, make delegation explicit
for that turn instead of leaving it to Claude's judgement. Silent otherwise, when
muse is not installed, and inside Muse itself."""

import json
import os
import re
import shutil
import sys

CONTEXT = (
    'The user mentioned Muse in this message. Unless they said not to use it, do the research, '
    'test-running, web-lookup or log-reading part of this request through `muse-ask` (load the '
    'clawmuse:muse skill first if it is not loaded yet) instead of your own tools or subagents; '
    'do the rest, such as code edits, yourself.'
)
# "muse", "Muse'a", "museyi", "muse-ask"; not "clawmuse", "amuse" or "museum".
MENTION = re.compile(r'(?<![\w-])muse(?!um)', re.IGNORECASE)


def main():
    if os.environ.get('CLAWMUSE_DEPTH') or not shutil.which(os.environ.get('CLAWMUSE_MUSE', 'muse')):
        return
    try:
        prompt = json.load(sys.stdin).get('prompt') or ''
    except (ValueError, AttributeError):
        return
    if MENTION.search(prompt):
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit', 'additionalContext': CONTEXT}}))


if __name__ == '__main__':
    main()
