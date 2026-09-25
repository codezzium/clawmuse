"""Tests for bin/muse-ask and the hooks, run through bash the way Claude Code runs them,
with tests/fake_muse.py standing in for the muse CLI. Linux, macOS and Windows (Git Bash).

Run: python3 -m unittest discover -s tests -v
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAKE = Path(__file__).resolve().parent / 'fake_muse.py'
OWN_ENV = ('CLAWMUSE_DEPTH', 'CLAWMUSE_MUSE', 'CLAUDE_PLUGIN_ROOT')
SESSION = '01a0d8ae-ca9a-7590-903f-bf601b5119e7'
WINDOWS = os.name == 'nt'


def find_bash():
    if WINDOWS:
        # Claude Code on Windows runs commands in Git Bash; System32\bash.exe would be WSL.
        for base in (os.environ.get('ProgramFiles'), r'C:\Program Files'):
            cand = Path(base or '') / 'Git' / 'bin' / 'bash.exe'
            if cand.exists():
                return str(cand)
    return shutil.which('bash')


BASH = find_bash()


def script(rel):
    """A path bash can open on every platform (forward slashes, also on Windows)."""
    return (ROOT / rel).as_posix()


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in OWN_ENV}
    env.update(extra)
    return env


def run(cmd, stdin=None, env=None, cwd=None, timeout=60):
    return subprocess.run(cmd, input=stdin, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', env=env, cwd=cwd, timeout=timeout)


class MuseAskTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.record = self.dir / 'record.json'
        self.work = self.dir / 'work'
        self.work.mkdir()
        # Something Popen can start directly: the script itself, or a .cmd shim on Windows.
        self.muse = str(FAKE)
        if WINDOWS:
            shim = self.dir / 'fake_muse.cmd'
            shim.write_text(f'@"{sys.executable}" "{FAKE}" %*\r\n')
            self.muse = str(shim)

    def tearDown(self):
        # Windows releases a killed process tree's handles a moment after taskkill returns.
        # Retry for a while; a process that really survived still fails the test.
        for _ in range(20 if WINDOWS else 1):
            try:
                self.tmp.cleanup()
                return
            except PermissionError:
                time.sleep(0.5)
        self.tmp.cleanup()

    def ask(self, *args, scenario='ok', stdin=None, extra_env=None, timeout=60):
        env = clean_env(CLAWMUSE_MUSE=self.muse, FAKE_MUSE_RECORD=str(self.record),
                        FAKE_MUSE_SCENARIO=scenario, XDG_CACHE_HOME=str(self.dir / 'cache'))
        env.update(extra_env or {})
        return run([BASH, script('bin/muse-ask'), *args], stdin=stdin, env=env, cwd=self.work,
                   timeout=timeout)

    def recorded(self):
        return json.loads(self.record.read_text(encoding='utf-8'))

    def log_text(self):
        logs = list((self.dir / 'cache' / 'clawmuse' / 'runs').glob('*.md'))
        self.assertEqual(len(logs), 1)
        return logs[0].read_text(encoding='utf-8')

    def test_report_and_footer_only(self):
        r = self.ask('where is A?')
        self.assertEqual(r.returncode, 0, r.stderr)
        report, footer = r.stdout.strip().split('\n\n')
        self.assertEqual(report, 'A = 1 (a.js:1). Tests: 3 pass.')
        self.assertIn('muse · research ·', footer)
        self.assertIn('2 tools', footer)
        self.assertIn(f'session {SESSION}', footer)
        self.assertNotIn('Let me look', r.stdout)
        self.assertNotIn('const A', r.stdout)

    def test_research_runs_yolo_read_only_on_fixed_model(self):
        self.ask('where is A?')
        rec = self.recorded()
        argv = rec['argv']
        self.assertEqual(argv[0], 'exec')
        for flag in ('--json', '--yolo', '--disable-write'):
            self.assertIn(flag, argv)
        self.assertNotIn('--approval-mode', argv)
        self.assertEqual(argv[argv.index('--model') + 1], 'muse-spark-1.3')
        self.assertEqual(argv[argv.index('--reasoning-effort') + 1], 'max')
        self.assertTrue(os.path.samefile(rec['cwd'], self.work))
        self.assertEqual(rec['depth'], '1')
        self.assertIn('MODE: RESEARCH', rec['prompt'])
        self.assertIn('At most ~300 words', rec['prompt'])
        self.assertTrue(rec['prompt'].rstrip().endswith('TASK:\nwhere is A?'))

    def test_test_mode_can_write_and_passes_options(self):
        other = self.dir / 'other'
        other.mkdir()
        img = self.dir / 'shot.png'
        img.write_bytes(b'png')
        r = self.ask('-m', 'test', '-C', str(other), '-w', '120', '-s', '7', '-i', str(img),
                     'run the tests')
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = self.recorded()
        argv = rec['argv']
        self.assertIn('--yolo', argv)
        self.assertNotIn('--disable-write', argv)
        self.assertEqual(argv[argv.index('--reasoning-effort') + 1], 'max')
        self.assertEqual(argv[argv.index('--max-model-steps') + 1], '7')
        self.assertTrue(os.path.samefile(argv[argv.index('--image') + 1], img))
        self.assertTrue(os.path.samefile(rec['cwd'], other))
        self.assertIn('MODE: TEST', rec['prompt'])
        self.assertIn('At most ~120 words', rec['prompt'])

    def test_model_and_effort_cannot_be_chosen(self):
        for flag in ('-e', '--effort', '--model', '--reasoning-effort'):
            r = self.ask(flag, 'low', 'x')
            self.assertEqual(r.returncode, 2, flag)
            self.assertFalse(self.record.exists(), flag)

    def test_follow_up_reuses_session(self):
        self.ask('-c', 'abc-123', 'and B?')
        rec = self.recorded()
        self.assertEqual(rec['argv'][rec['argv'].index('--session-id') + 1], 'abc-123')
        self.assertIn('FOLLOW-UP', rec['prompt'])

    def test_brief_from_stdin_keeps_unicode(self):
        r = self.ask('-', stdin='testleri çalıştır\nğüşiöç İ ı\n')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('TASK:\ntestleri çalıştır\nğüşiöç İ ı', self.recorded()['prompt'])

    def test_unicode_report_is_printed_as_utf8(self):
        r = self.ask('x', scenario='unicode')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('Testler geçti: ş ğ ı İ ✓', r.stdout)

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
        self.assertIn(f'muse-ask -c {SESSION}', r.stdout)

    def test_no_terminal_falls_back_to_last_deltas(self):
        r = self.ask('x', scenario='no-terminal')
        self.assertEqual(r.returncode, 1)
        self.assertIn('Partial output:\nhalf an answer', r.stdout)

    def test_timeout_stops_muse(self):
        t0 = time.monotonic()
        r = self.ask('-t', '2', 'x', scenario='hang')
        self.assertLess(time.monotonic() - t0, 30)
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


def stub_bin(tmp):
    """A bin dir whose python3 and python behave like the Windows Store stubs."""
    d = Path(tmp) / 'stubs'
    d.mkdir()
    for name in ('python3', 'python'):
        f = d / name
        f.write_text('#!/bin/sh\necho "Python was not found; run without arguments to install '
                     'from the Microsoft Store" >&2\nexit 49\n', newline='\n')
        f.chmod(0o755)
    return d


class PythonDiscoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_store_stubs_only_gives_clear_error(self):
        env = clean_env(PATH=str(stub_bin(self.tmp.name)))
        r = run([BASH, script('bin/muse-ask'), 'x'], env=env)
        self.assertEqual(r.returncode, 127, r.stderr)
        self.assertIn('Python 3.8+ not found', r.stderr)

    @unittest.skipIf(WINDOWS, 'symlinks need extra privileges on Windows')
    def test_falls_back_past_a_stub_python3(self):
        stubs = stub_bin(self.tmp.name)
        (stubs / 'python').unlink()
        (stubs / 'python').symlink_to(sys.executable)
        work = Path(self.tmp.name) / 'work'
        work.mkdir()
        # The fake's own `env python3` shebang would hit the stub too.
        muse = Path(self.tmp.name) / 'muse'
        muse.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE}" "$@"\n')
        muse.chmod(0o755)
        env = clean_env(PATH=f'{stubs}{os.pathsep}{os.environ["PATH"]}', CLAWMUSE_MUSE=str(muse),
                        FAKE_MUSE_SCENARIO='ok', XDG_CACHE_HOME=str(Path(self.tmp.name) / 'cache'))
        r = run([BASH, script('bin/muse-ask'), 'x'], env=env, cwd=work)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('A = 1 (a.js:1)', r.stdout)

    def test_hooks_stay_silent_without_python(self):
        env = clean_env(PATH=str(stub_bin(self.tmp.name)), CLAUDE_PLUGIN_ROOT=str(ROOT),
                        CLAWMUSE_MUSE=BASH)
        for hook in ('hooks/session-start.sh', 'hooks/user-prompt.sh'):
            r = run([BASH, script(hook)], stdin=json.dumps({'prompt': 'ask muse'}), env=env)
            self.assertEqual((r.returncode, r.stdout), (0, ''), hook)


class HooksTest(unittest.TestCase):
    def run_hook(self, hook, stdin='', **env):
        base = clean_env(CLAUDE_PLUGIN_ROOT=str(ROOT), CLAWMUSE_MUSE='bash')
        base.update(env)
        return run([BASH, script(hook)], stdin=stdin, env=base, timeout=30)

    def context(self, prompt, **env):
        r = self.run_hook('hooks/user-prompt.sh', json.dumps({'prompt': prompt, 'cwd': '/x/muse-work'}),
                          **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        if not r.stdout.strip():
            return None
        out = json.loads(r.stdout)['hookSpecificOutput']
        self.assertEqual(out['hookEventName'], 'UserPromptSubmit')
        return out['additionalContext']

    def test_hooks_json_points_at_existing_scripts(self):
        hooks = json.loads((ROOT / 'hooks' / 'hooks.json').read_text(encoding='utf-8'))['hooks']
        for event in ('SessionStart', 'UserPromptSubmit'):
            cmd = hooks[event][0]['hooks'][0]['command']
            self.assertTrue(cmd.startswith('bash "${CLAUDE_PLUGIN_ROOT}/'), cmd)
            self.assertTrue((ROOT / cmd.split('}/')[1].rstrip('"')).exists(), cmd)

    def test_session_start_injects_context(self):
        r = self.run_hook('hooks/session-start.sh')
        out = json.loads(r.stdout)['hookSpecificOutput']
        self.assertEqual(out['hookEventName'], 'SessionStart')
        self.assertIn('muse-ask', out['additionalContext'])

    def test_session_start_silent_without_muse_or_inside_muse(self):
        self.assertEqual(self.run_hook('hooks/session-start.sh', CLAWMUSE_MUSE='no-such-muse-binary').stdout, '')
        self.assertEqual(self.run_hook('hooks/session-start.sh', CLAWMUSE_DEPTH='1').stdout, '')

    def test_mention_forces_delegation(self):
        for prompt in ("bunu muse'a araştırt, kodu sen yaz", 'Muse ile testleri çalıştır',
                       'MUSE: check the logs', 'run muse-ask on this'):
            self.assertIn('muse-ask', self.context(prompt) or '', prompt)

    def test_no_mention_stays_silent(self):
        for prompt in ('look at /opt/clawmuse', 'that was amusing', 'fix the museum page', ''):
            self.assertIsNone(self.context(prompt), prompt)

    def test_prompt_hook_silent_without_muse_inside_muse_or_on_bad_input(self):
        self.assertIsNone(self.context('ask muse', CLAWMUSE_MUSE='no-such-muse-binary'))
        self.assertIsNone(self.context('ask muse', CLAWMUSE_DEPTH='1'))
        r = self.run_hook('hooks/user-prompt.sh', 'not json')
        self.assertEqual((r.returncode, r.stdout), (0, ''))


if __name__ == '__main__':
    unittest.main()
