"""Tests for bin/muse-ask and the SessionStart hook, using tests/fake_muse.py.

Run: python3 -m unittest discover -s tests -v
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSE_ASK = ROOT / 'bin' / 'muse-ask'
FAKE = Path(__file__).resolve().parent / 'fake_muse.py'
HOOK = ROOT / 'hooks' / 'session-start.sh'
PROMPT_HOOK = ROOT / 'hooks' / 'user-prompt.py'
OWN_ENV = ('CLAWMUSE_DEPTH', 'CLAWMUSE_YOLO')


class MuseAskTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.record = self.dir / 'record.json'
        self.work = self.dir / 'work'
        self.work.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, *args, scenario='ok', stdin=None, extra_env=None, timeout=30):
        env = {k: v for k, v in os.environ.items() if k not in OWN_ENV}
        env.update(CLAWMUSE_MUSE=str(FAKE), FAKE_MUSE_RECORD=str(self.record),
                   FAKE_MUSE_SCENARIO=scenario, XDG_CACHE_HOME=str(self.dir / 'cache'))
        env.update(extra_env or {})
        return subprocess.run([str(MUSE_ASK), *args], input=stdin, capture_output=True, text=True,
                              env=env, cwd=self.work, timeout=timeout)

    def recorded(self):
        return json.loads(self.record.read_text())

    def log_text(self):
        logs = list((self.dir / 'cache' / 'clawmuse' / 'runs').glob('*.md'))
        self.assertEqual(len(logs), 1)
        return logs[0].read_text()

    def test_report_and_footer_only(self):
        r = self.ask('where is A?')
        self.assertEqual(r.returncode, 0, r.stderr)
        report, footer = r.stdout.strip().split('\n\n')
        self.assertEqual(report, 'A = 1 (a.js:1). Tests: 3 pass.')
        self.assertIn('muse · research ·', footer)
        self.assertIn('2 tools', footer)
        self.assertIn('session 01a0d8ae-ca9a-7590-903f-bf601b5119e7', footer)
        self.assertNotIn('Let me look', r.stdout)
        self.assertNotIn('const A', r.stdout)

    def test_research_is_read_only_and_headless(self):
        self.ask('where is A?')
        rec = self.recorded()
        self.assertEqual(rec['argv'][0], 'exec')
        for flag in ('--json', '--disable-write', '--trust-workspace'):
            self.assertIn(flag, rec['argv'])
        self.assertEqual(rec['argv'][rec['argv'].index('--approval-mode') + 1], 'never')
        self.assertNotIn('--yolo', rec['argv'])
        self.assertNotIn('--reasoning-effort', rec['argv'])
        self.assertEqual(Path(rec['cwd']).resolve(), self.work.resolve())
        self.assertEqual(rec['depth'], '1')
        self.assertIn('MODE: RESEARCH', rec['prompt'])
        self.assertIn('At most ~300 words', rec['prompt'])
        self.assertTrue(rec['prompt'].rstrip().endswith('TASK:\nwhere is A?'))

    def test_test_mode_can_write_and_passes_options(self):
        other = self.dir / 'other'
        other.mkdir()
        img = self.dir / 'shot.png'
        img.write_bytes(b'png')
        r = self.ask('-m', 'test', '-C', str(other), '-e', 'low', '-w', '120', '-s', '7',
                     '-i', str(img), 'run the tests')
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = self.recorded()
        argv = rec['argv']
        self.assertNotIn('--disable-write', argv)
        self.assertEqual(argv[argv.index('--reasoning-effort') + 1], 'low')
        self.assertEqual(argv[argv.index('--max-model-steps') + 1], '7')
        self.assertEqual(argv[argv.index('--image') + 1], str(img.resolve()))
        self.assertEqual(Path(rec['cwd']).resolve(), other.resolve())
        self.assertIn('MODE: TEST', rec['prompt'])
        self.assertIn('At most ~120 words', rec['prompt'])

    def test_yolo_is_opt_in(self):
        self.ask('x', extra_env={'CLAWMUSE_YOLO': '1'})
        argv = self.recorded()['argv']
        self.assertIn('--yolo', argv)
        self.assertNotIn('--approval-mode', argv)
        self.assertIn('--disable-write', argv)

    def test_sandbox_failure_suggests_opt_in(self):
        r = self.ask('x', scenario='bwrap')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('CLAWMUSE_YOLO=1', r.stdout)
        self.assertIn('do not set it yourself', r.stdout)
        r = self.ask('x', scenario='bwrap', extra_env={'CLAWMUSE_YOLO': '1'})
        self.assertNotIn('CLAWMUSE_YOLO', r.stdout)

    def test_follow_up_reuses_session(self):
        self.ask('-c', 'abc-123', 'and B?')
        rec = self.recorded()
        self.assertEqual(rec['argv'][rec['argv'].index('--session-id') + 1], 'abc-123')
        self.assertIn('FOLLOW-UP', rec['prompt'])

    def test_brief_from_stdin(self):
        r = self.ask('-', stdin='multi\nline brief\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('TASK:\nmulti\nline brief', self.recorded()['prompt'])

    def test_empty_brief_is_usage_error(self):
        r = self.ask(stdin='')
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.record.exists())

    def test_nested_delegation_refused(self):
        r = self.ask('x', extra_env={'CLAWMUSE_DEPTH': '1'})
        self.assertEqual(r.returncode, 2)
        self.assertIn('nested', r.stderr)
        self.assertFalse(self.record.exists())

    def test_missing_muse(self):
        r = self.ask('x', extra_env={'CLAWMUSE_MUSE': 'no-such-muse-binary'})
        self.assertEqual(r.returncode, 127)

    def test_failure_reports_reason_and_resume_hint(self):
        r = self.ask('x', scenario='failed')
        self.assertEqual(r.returncode, 1)
        self.assertIn('MUSE FAILED (PROVIDER ERROR)', r.stdout)
        self.assertIn('provider exploded', r.stdout)
        self.assertNotIn('workspace root', r.stdout)
        self.assertIn('muse-ask -c 01a0d8ae-ca9a-7590-903f-bf601b5119e7', r.stdout)

    def test_no_terminal_falls_back_to_last_deltas(self):
        r = self.ask('x', scenario='no-terminal')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Partial output:\nhalf an answer', r.stdout)

    def test_timeout_stops_muse(self):
        t0 = time.monotonic()
        r = self.ask('-t', '2', 'x', scenario='hang')
        self.assertLess(time.monotonic() - t0, 15)
        self.assertEqual(r.returncode, 124)
        self.assertIn('MUSE TIMEOUT AFTER 2S', r.stdout)
        self.assertIn('Partial output:\nstill working', r.stdout)
        self.assertIn('muse-ask -c ', r.stdout)

    def test_log_keeps_tool_outputs(self):
        self.ask('where is A?')
        log = self.log_text()
        self.assertIn('## Brief\nwhere is A?', log)
        self.assertIn('### 1. read_file - success', log)
        self.assertIn('1|const A = 1;', log)
        self.assertIn('$ npm test\nexit: 0\npass 3', log)
        self.assertIn('## Final report\nA = 1 (a.js:1). Tests: 3 pass.', log)


class HookTest(unittest.TestCase):
    def run_hook(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in OWN_ENV}
        base.update(env)
        return subprocess.run([str(HOOK)], capture_output=True, text=True, env=base, timeout=10)

    def test_injects_context_when_muse_present(self):
        r = self.run_hook(CLAWMUSE_MUSE=str(FAKE))
        out = json.loads(r.stdout)['hookSpecificOutput']
        self.assertEqual(out['hookEventName'], 'SessionStart')
        self.assertIn('muse-ask', out['additionalContext'])

    def test_silent_without_muse_or_inside_muse(self):
        self.assertEqual(self.run_hook(CLAWMUSE_MUSE='no-such-muse-binary').stdout, '')
        self.assertEqual(self.run_hook(CLAWMUSE_MUSE=str(FAKE), CLAWMUSE_DEPTH='1').stdout, '')



class PromptHookTest(unittest.TestCase):
    def run_hook(self, stdin, **env):
        base = {k: v for k, v in os.environ.items() if k not in OWN_ENV}
        base.update(CLAWMUSE_MUSE=str(FAKE))
        base.update(env)
        return subprocess.run([str(PROMPT_HOOK)], input=stdin, capture_output=True, text=True,
                              env=base, timeout=10)

    def context(self, prompt, **env):
        r = self.run_hook(json.dumps({'prompt': prompt, 'cwd': '/home/x/muse-work'}), **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return None
        out = json.loads(r.stdout)['hookSpecificOutput']
        self.assertEqual(out['hookEventName'], 'UserPromptSubmit')
        return out['additionalContext']

    def test_mention_forces_delegation(self):
        for prompt in ("bunu muse'a araştırt, kodu sen yaz", 'Muse ile testleri çalıştır',
                       'MUSE: check the logs', 'run muse-ask on this'):
            self.assertIn('muse-ask', self.context(prompt) or '', prompt)

    def test_no_mention_stays_silent(self):
        for prompt in ('look at /opt/clawmuse', 'that was amusing', 'fix the museum page', ''):
            self.assertIsNone(self.context(prompt), prompt)

    def test_silent_without_muse_inside_muse_or_on_bad_input(self):
        self.assertIsNone(self.context('ask muse', CLAWMUSE_MUSE='no-such-muse-binary'))
        self.assertIsNone(self.context('ask muse', CLAWMUSE_DEPTH='1'))
        r = self.run_hook('not json')
        self.assertEqual((r.returncode, r.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
