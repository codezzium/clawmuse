#!/usr/bin/env python3
"""Stand-in for the muse CLI in tests.

Records its argv, cwd, the prompt file and CLAWMUSE_DEPTH to $FAKE_MUSE_RECORD,
then plays the scenario named by $FAKE_MUSE_SCENARIO with the same event shapes
real `muse exec --json` emits.
"""

import json
import os
import sys
import time

SESSION = '01a0d8ae-ca9a-7590-903f-bf601b5119e7'
seq = 0


def emit(payload_type, payload):
    global seq
    seq += 1
    print(json.dumps({
        'schema_version': 1, 'sequence': seq, 'record_type': 'event',
        'stream': {'kind': 'session', 'id': SESSION},
        'payload_type': payload_type, 'payload': payload,
    }), flush=True)


def tool(name, text, outcome='success'):
    emit('tool.result', {'kind': 'tool_result', 'text': text,
                         'correlation_facts': {'tool_name': name, 'outcome': outcome}})


def delta(text):
    emit('run.output.delta', {'kind': 'run_output_delta', 'text': text})


def terminal(state, text=None, reason=None):
    emit(f'run.terminal.{state}', {'kind': 'run_terminal', 'terminal': state, 'text': text, 'reason': reason})


def main():
    argv = sys.argv[1:]
    prompt = ''
    if '--prompt-file' in argv:
        with open(argv[argv.index('--prompt-file') + 1], encoding='utf-8') as f:
            prompt = f.read()
    record = os.environ.get('FAKE_MUSE_RECORD')
    if record:
        with open(record, 'w', encoding='utf-8') as f:
            json.dump({'argv': argv, 'cwd': os.getcwd(), 'prompt': prompt,
                       'depth': os.environ.get('CLAWMUSE_DEPTH')}, f)

    print('muse: workspace root: /x (cwd default)', file=sys.stderr, flush=True)
    scenario = os.environ.get('FAKE_MUSE_SCENARIO', 'ok')
    emit('run.model.configured', {'kind': 'run_model_configured', 'model_id': 'muse-spark-test'})
    print('[not json]', flush=True)
    print('[1, 2]', flush=True)

    if scenario == 'ok':
        delta('Let me look.')
        tool('read_file', 'Read text file `a.js`.\n1|const A = 1;\n')
        tool('bash', json.dumps({'command': 'npm test', 'exit_code': 0, 'output': 'pass 3\nfail 0'}))
        delta('A = 1 (a.js:1). ')
        delta('Tests: 3 pass.')
        terminal('completed', 'A = 1 (a.js:1). Tests: 3 pass.')
    elif scenario == 'bwrap':
        tool('bash', json.dumps({'command': 'ls', 'exit_code': 1,
                                 'output': 'bwrap: setting up uid map: Permission denied'}), 'failure')
        terminal('completed', 'ls failed (sandbox).')
    elif scenario == 'failed':
        tool('search', 'nothing')
        terminal('failed', None, 'provider error')
        print('muse: provider exploded', file=sys.stderr, flush=True)
        sys.exit(1)
    elif scenario == 'no-terminal':
        tool('search', 'x')
        delta('half an ')
        delta('answer')
        sys.exit(3)
    elif scenario == 'hang':
        tool('bash', json.dumps({'command': 'sleep 600', 'exit_code': None, 'output': ''}))
        delta('still working')
        time.sleep(600)


if __name__ == '__main__':
    main()
