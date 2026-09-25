"""Print each unittest FAIL/ERROR block of a log as a GitHub Actions error annotation."""

import re
import sys

log = open(sys.argv[1], encoding='utf-8', errors='replace').read()
for block in re.split(r'\n={20,}\n', log)[1:]:
    block = re.split(r'\n-{20,}\nRan ', block)[0].strip()
    if block.startswith(('FAIL:', 'ERROR:')):
        msg = block.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
        print(f'::error::{msg[:4000]}')
