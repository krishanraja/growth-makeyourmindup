"""GitHub Actions runs: the backup gate, key health, doctor's session mode, the
workflows' secrets and the cost meter. Synthetic data only; no network."""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import types
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

import growth
from engine import meter
from engine.control_center import ProtocolError
from engine.run import backup, buffer_reads, keys

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-27T05:40:00Z'
FOREIGN = 'not-the-engine-key-' + 'x' * 12


def runs(*items):
    return {'total_count': len(items), 'workflow_runs': list(items)}


def run_item(event='repository_dispatch', conclusion='success', created='2026-10-27T05:10:12Z', status='completed'):
    return {'id': 1, 'event': event, 'status': status, 'conclusion': conclusion, 'created_at': created}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class BackupGateTests(unittest.TestCase):
    def test_a_successful_dispatch_today_skips_the_backup(self):
        self.assertTrue(backup.dispatch_succeeded_today(runs(run_item()), NOW))

    def test_anything_else_runs_the_backup(self):
        for item in (run_item(conclusion='failure'), run_item(created='2026-10-26T05:10:12Z'),
                     run_item(event='schedule'), run_item(event='workflow_dispatch'),
                     run_item(status='in_progress', conclusion=None), run_item(created=None)):
            self.assertFalse(backup.dispatch_succeeded_today(runs(item), NOW), item)
        self.assertFalse(backup.dispatch_succeeded_today(runs(), NOW))
        with self.assertRaises(ValueError):
            backup.dispatch_succeeded_today({'message': 'synthetic'}, NOW)

    def test_the_request_asks_only_for_todays_successful_dispatches(self):
        seen = []

        def open_fn(request, timeout):
            seen.append(request)
            return Response(json.dumps(runs(run_item())).encode('utf-8'))

        env = {'GITHUB_REPOSITORY': 'synthetic-owner/synthetic-repo', 'GITHUB_TOKEN': 'ghs_synthetic'}
        out = []
        with tempfile.TemporaryDirectory() as folder:
            env['GITHUB_OUTPUT'] = str(Path(folder) / 'output')
            self.assertEqual(backup.main([], env, NOW, open_fn, out.append), 0)
            self.assertEqual(Path(env['GITHUB_OUTPUT']).read_text(encoding='utf-8'), 'skip=true\n')
        self.assertEqual(out, ['dispatch already ran today'])
        url = seen[0].full_url
        self.assertTrue(url.startswith('https://api.github.com/repos/synthetic-owner/synthetic-repo/actions/workflows/'
                                       'control-center.yml/runs?'))
        self.assertIn('event=repository_dispatch', url)
        self.assertIn('created=%3E%3D2026-10-27', url)
        self.assertEqual(seen[0].get_method(), 'GET')

    def test_an_unreadable_answer_runs_the_backup_and_prints_no_token(self):
        def refused(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 403, 'Forbidden', {}, io.BytesIO(b'ghs_synthetic'))

        env = {'GITHUB_REPOSITORY': 'synthetic-owner/synthetic-repo', 'GITHUB_TOKEN': 'ghs_synthetic'}
        skip, line = backup.decide(env, NOW, refused)
        self.assertFalse(skip)
        self.assertEqual(line, 'could not read the workflow runs (github_http_403); running the backup')
        self.assertFalse(backup.decide({'GITHUB_REPOSITORY': 'not a repo'}, NOW, refused)[0])


class FakeCC:
    def __init__(self, error=None):
        self.error = error

    def capabilities(self):
        if self.error:
            raise self.error
        return {'schema_versions': ['1.0.0']}


class KeysTests(unittest.TestCase):
    def run_keys(self, make_client, environ, module=None):
        out = []
        with patch.object(buffer_reads, 'buffer_module', lambda: module):
            code = keys.main(['keys'], make_client, environ, out.append)
        return code, '\n'.join(out)

    def test_healthy_control_center_and_no_buffer_module_passes(self):
        code, text = self.run_keys(lambda: FakeCC(), {'BUFFER_API_KEY': 'synthetic'})
        self.assertEqual(code, 0, text)
        self.assertIn('keys: Control Center capabilities: ok', text)
        self.assertIn('buffer_api not installed', text)
        self.assertIn('Cost in all:', text)

    def test_refused_engine_token_exits_non_zero_with_its_code(self):
        code, text = self.run_keys(lambda: FakeCC(ProtocolError('unauthorized', 401)), {})
        self.assertEqual(code, 1)
        self.assertIn('FAILED cc_token_refused', text)

    def test_missing_or_foreign_engine_token(self):
        with patch.object(growth, 'engine_token', return_value=''):
            code, text = self.run_keys(growth.engine_client, {})
        self.assertEqual((code, 'FAILED cc_token_missing' in text), (1, True))
        with patch.object(growth, 'engine_token', return_value=FOREIGN):
            code, text = self.run_keys(growth.engine_client, {'GITHUB_ACTIONS': 'true'})
        self.assertEqual(code, 1)
        self.assertIn('FAILED cc_token_refused', text)
        self.assertIn('::error::key check failed: cc_token_refused', text)
        self.assertNotIn(FOREIGN, text)

    def test_refused_buffer_key_exits_non_zero_with_its_code(self):
        class Client:
            def __init__(self, key):
                self.key = key

            def account_check(self):
                error = ValueError('synthetic refusal body')
                error.status = 401
                raise error

        module = types.SimpleNamespace(Client=Client)
        code, text = self.run_keys(lambda: FakeCC(), {'BUFFER_API_KEY': 'synthetic-buffer-key'}, module)
        self.assertEqual(code, 1)
        self.assertIn('keys: Buffer: FAILED buffer_key_refused', text)
        self.assertNotIn('synthetic', text)

    def test_buffer_not_configured_and_a_healthy_buffer(self):
        module = types.SimpleNamespace(Client=lambda key: types.SimpleNamespace(account_check=lambda: {'ok': True}))
        code, text = self.run_keys(lambda: FakeCC(), {}, module)
        self.assertEqual((code, 'keys: Buffer: Buffer not configured' in text), (0, True))
        code, text = self.run_keys(lambda: FakeCC(), {'BUFFER_API_KEY': 'k'}, module)
        self.assertEqual((code, 'Buffer account check: ok' in text), (0, True))

    def test_keys_is_routed(self):
        from engine.run import cli
        self.assertEqual((cli.ROUTES['keys'], cli.ROUTES['dispatch-check']), ('keys', 'backup'))


class DoctorModeTests(unittest.TestCase):
    def doctor(self, value, offline):
        out = io.StringIO()
        with patch.object(growth, 'engine_token', return_value=value), \
                patch.object(growth, 'call', return_value={'ok': True, 'packs': [1]}), \
                patch.object(growth, 'pieces', return_value=[{'title': 'synthetic'}]), \
                patch.object(growth, 'engine_client', side_effect=AssertionError('engine token used')), \
                contextlib.redirect_stdout(out):
            code = growth.doctor(offline)
        return code, out.getvalue()

    def test_no_engine_token_is_session_mode_and_ready(self):
        for offline in (True, False):
            code, text = self.doctor('', offline)
            self.assertEqual(code, 0, text)
            self.assertIn('OK session mode: Control Center is reached by the GitHub runner (repository secret); '
                          'no token is needed here', text)
            self.assertNotIn('NOT READY', text)

    def test_a_foreign_token_is_a_warning_never_printed_or_used(self):
        for offline in (True, False):
            code, text = self.doctor(FOREIGN, offline)
            self.assertEqual(code, 0, text)
            self.assertIn("WARNING a token is set in this environment but is not the engine's gen1_ token; "
                          'it is not used; remove it', text)
            self.assertNotIn(FOREIGN, text)

    def test_the_engine_token_is_still_checked_read_only(self):
        out = io.StringIO()
        with patch.object(growth, 'engine_token', return_value='gen1_' + 'Synthetic' * 4), \
                patch.object(growth, 'call', return_value={'ok': True}), \
                patch.object(growth, 'pieces', return_value=[{}]), \
                patch.object(growth, 'engine_client', return_value=FakeCC(ProtocolError('unauthorized', 401))), \
                contextlib.redirect_stdout(out):
            self.assertEqual(growth.doctor(False), 1)
        self.assertIn('NOT READY Control Center engine protocol read access', out.getvalue())

    def test_engine_client_refuses_a_foreign_token(self):
        with patch.object(growth, 'engine_token', return_value=FOREIGN):
            with self.assertRaisesRegex(ValueError, 'not the engine gen1_ token') as caught:
                growth.engine_client()
        self.assertNotIn(FOREIGN, str(caught.exception))


class WorkflowTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / '.github' / 'workflows' / name).read_text(encoding='utf-8')

    def secrets(self, name):
        return set(re.findall(r'secrets\.([A-Za-z0-9_]+)', self.read(name)))

    def test_workflows_name_only_the_expected_secrets(self):
        self.assertEqual(self.secrets('control-center.yml'), {'CONTROL_CENTER_ENGINE_TOKEN'})
        self.assertEqual(self.secrets('measure.yml'), {'CONTROL_CENTER_ENGINE_TOKEN', 'BUFFER_API_KEY'})
        self.assertEqual(self.secrets('check.yml'), set())
        for name in ('control-center.yml', 'measure.yml', 'check.yml'):
            self.assertNotIn('upload-artifact', self.read(name))

    def test_control_center_has_the_backup_schedule_and_gate(self):
        text = self.read('control-center.yml')
        for needle in ("cron: '40 5 * * *'", 'actions: read', 'contents: read', 'python growth.py run dispatch-check',
                       "if: github.event_name == 'schedule'", "if: steps.backup.outputs.skip != 'true'",
                       'GITHUB_TOKEN: ${{ github.token }}', 'python growth.py cc runner --deliver --backup',
                       'cc-growth-directive', 'workflow_dispatch'):
            self.assertIn(needle, text)
        self.assertNotIn('actions: write', text)

    def test_measure_runs_three_times_a_day_after_a_key_check(self):
        text = self.read('measure.yml')
        for needle in ("cron: '0 7,13,19 * * *'", 'workflow_dispatch', 'contents: read', 'group: measure',
                       'timeout-minutes: 15', '${{ vars.CONTROL_CENTER_URL }}', 'Buffer not configured',
                       'python growth.py run measure auto --deliver'):
            self.assertIn(needle, text)
        self.assertLess(text.index('python growth.py run keys'), text.index('python growth.py run measure auto'))
        self.assertEqual(re.findall(r'^\s+(\w+): (?:read|write)$', text, re.M), ['contents'])


class MeterTests(unittest.TestCase):
    def test_one_counter_sees_every_urllib_call(self):
        class Fake(urllib.request.BaseHandler):
            def fake_open(self, request):
                return io.BytesIO(b'{}')

        meter.install()
        meter.install()  # idempotent: never counts twice
        before = meter.calls()
        opener = urllib.request.build_opener(Fake())
        opener.open('fake://one')
        opener.open('fake://two')
        self.assertEqual(meter.calls() - before, 2)

    def test_cost_line_is_seconds_and_calls_only(self):
        meter.reset()
        line = meter.cost_line('in all', now=1000.4, environ={meter.START_ENV: '900'})
        self.assertEqual(line, 'Cost in all: 100 seconds of Actions run time and 0 HTTP calls')
        self.assertEqual(meter.seconds(now=5, environ={meter.START_ENV: '9'}), 0)


if __name__ == '__main__':
    unittest.main()
