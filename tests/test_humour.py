"""The humour engine on call (engine/humour.py): the house rules it holds, that unavailable is never a pass, and the
real package run end to end through this engine's own client."""
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import humour
from engine.control_center import ProtocolError


def analysis(reading='supported', target='behaviour', mech=('incongruity',), deps=0, attempt='supported_inference',
             missing=()):
    return {
        'comic_reading': reading,
        'humour_attempt': {'status': attempt} if attempt else None,
        'interpretations': [{'id': 'i1', 'is_main': True, 'supported_reading': 'comic' if reading == 'supported' else None,
                             'labels_by_axis': {'mechanism': list(mech)}, 'target_and_subject': {'target': target}}],
        'context_dependencies': [{'source_kind': 'topical', 'required': True}] * deps,
        'missing_context': list(missing),
    }


class FakeCC:
    def __init__(self, features=None, error=None, payload=None):
        self.features, self.error, self.payload, self.calls = features or {}, error, payload, []

    def capabilities(self):
        self.calls.append(('GET', 'capabilities'))
        if self.error:
            raise self.error
        return {'ok': True, 'features': self.features}

    def humour(self, body):
        self.calls.append(('POST', 'humour'))
        if self.error:
            raise self.error
        return {'ok': True, 'payload': self.payload, 'model': 'claude-sonnet-5', 'prompt': 'comprehension-v1:engine',
                'usage': {'input_tokens': 900, 'output_tokens': 300}, 'cost_usd': 0.005}


class HumourRules(unittest.TestCase):
    def test_a_comment_joke_at_the_poster_is_held_and_one_at_the_topic_passes(self):
        rules, _, _ = humour.findings(analysis(target='other_person'), 'comment')
        self.assertTrue(rules and rules[0].startswith('at_person'))
        self.assertEqual(humour.findings(analysis(target='situation'), 'comment')[0], [])
        # On the publication's own caption the target rule does not apply (the register decides that).
        self.assertEqual(humour.findings(analysis(target='other_person'), 'caption')[0], [])

    def test_any_joke_on_a_mindmake_piece_is_held(self):
        rules, _, _ = humour.findings(analysis(), 'caption', mindmake=True)
        self.assertTrue(any(r.startswith('mindmake_humour') for r in rules))
        self.assertEqual(humour.findings(analysis(reading='not_supported', attempt=None), 'caption', True)[0], [])

    def test_a_joke_that_needs_explaining_is_held(self):
        self.assertTrue(humour.findings(analysis(deps=2))[0])
        self.assertTrue(humour.findings(analysis(missing=['who the CEO is']))[0])
        self.assertEqual(humour.findings(analysis(deps=1))[0], [])
        self.assertTrue(humour.findings(analysis(reading='insufficient_context'))[0])

    def test_a_forced_joke_is_a_note_and_plain_copy_passes(self):
        rules, notes, _ = humour.findings(analysis(reading='not_supported'))
        self.assertEqual(rules, [])
        self.assertTrue(notes and notes[0].startswith('forced'))
        self.assertEqual(humour.findings(analysis(reading='not_supported', attempt=None)), ([], [], {}))


class HumourConsult(unittest.TestCase):
    def test_statuses_and_unavailable_is_never_a_pass(self):
        lines = ['The model is so confident it cited a paper from next year.']
        self.assertEqual(humour.consult(lines, read=lambda r: analysis())['status'], 'pass')
        self.assertEqual(humour.consult(lines, 'comment', read=lambda r: analysis(target='other_person'))['status'], 'flagged')
        self.assertEqual(humour.consult(lines, read=None)['status'], 'unavailable')
        self.assertEqual(humour.consult(lines, read=lambda r: (_ for _ in ()).throw(TimeoutError()))['status'], 'unavailable')
        abstain = humour.consult(lines, read=lambda r: {'comic_reading': None, 'errors': [{'code': 'budget_exhausted'}]})
        self.assertEqual(abstain['status'], 'unavailable')
        self.assertIn('budget_exhausted', abstain['reason'])

    def test_the_request_carries_the_surface_and_context_in_one_call(self):
        req = humour.request(['a', 'b'], 'comment', ['posted under a launch video'])
        self.assertEqual([s['segment_id'] for s in req['segments']], ['l1', 'l2'])
        self.assertIn('comment', req['context']['provided_facts'][0])
        self.assertIn('launch video', req['context']['provided_facts'][1])
        self.assertEqual(req['budget']['max_model_calls'], 1)
        self.assertEqual(req['provider_policy']['allowed_provider_ids'], ['controlcenter'])

    def test_compare_names_differences_and_never_picks(self):
        a = humour.consult(['x'], read=lambda r: analysis(mech=('irony',)))
        b = humour.consult(['y'], read=lambda r: analysis(mech=('understatement',)))
        self.assertTrue(any('mechanism' in d for d in humour.differences(a, b)))
        self.assertEqual(humour.differences(a, a), [])

    def test_transport_uses_the_engine_client_and_maps_its_errors(self):
        cc = FakeCC(payload={'x': 1})
        status, body = humour.transport_for(cc)('ignored', {'system': 's'})
        self.assertEqual((status, body['ok']), (200, True))
        cc = FakeCC(error=ProtocolError('rate_limited', 429, 'daily_humour_cap_reached'))
        self.assertEqual(humour.transport_for(cc)('ignored', {}), (429, {'ok': False, 'error': 'daily_humour_cap_reached'}))

    def test_doctor_reads_capabilities_only(self):
        ok, rows = humour.doctor(FakeCC({'humour': True}), package=True)
        self.assertTrue(ok, rows)
        ok, rows = humour.doctor(FakeCC({}), package=True)
        self.assertFalse(ok)
        self.assertTrue(any('NOT SERVED' in r for r in rows))
        ok, rows = humour.doctor(None, package=False)
        self.assertFalse(ok)
        cc = FakeCC({'humour': True})
        humour.doctor(cc, package=True)
        self.assertEqual(cc.calls, [('GET', 'capabilities')])

    def test_cli_without_a_token_exits_2(self):
        def no_client():
            raise ValueError('no key')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(humour.command(['check', 'one line'], no_client), 2)
            self.assertEqual(humour.command(['doctor'], no_client), 2)
        self.assertIn('UNAVAILABLE', out.getvalue())

    def test_growth_py_routes_the_humour_command(self):
        text = (Path(__file__).resolve().parents[1] / 'growth.py').read_text(encoding='utf-8')
        self.assertIn("social_args[0] == 'humour'", text)

    def test_live_path_runs_the_real_package_through_this_engines_client(self):
        try:
            import humour_engine  # noqa: F401
        except ImportError:
            self.skipTest('humour-engine not installed (requirements-humour.txt)')
        line = 'The model is so confident it cited a paper from next year.'
        payload = {
            'comic_reading': 'supported',
            'humour_attempt': {'status': 'supported_inference', 'evidence': [{'segment_id': 'l1', 'quote': 'a paper from next year'}]},
            'interpretations': [{
                'id': 'i1', 'is_main': True, 'literal_reading': 'the model cites a paper that does not exist yet',
                'supported_reading': 'confidence outruns truth',
                'expectations': ['citations point to the past'], 'connecting_logic': 'a future citation is impossible',
                'labels_by_axis': {'mechanism': ['incongruity', 'exaggeration'], 'rhetorical_mode': ['observational']},
                'target': {'target': 'behaviour'},
                'evidence': [{'segment_id': 'l1', 'quote': 'a paper from next year'}],
            }],
            'missing_context': [],
        }
        cc = FakeCC(payload=payload)
        o = humour.consult([line], 'caption', read=humour.reader(cc))
        self.assertEqual(cc.calls, [('POST', 'humour')])
        self.assertEqual(o['status'], 'pass', o)
        self.assertIn('incongruity', o['labels']['mechanism'])
        json.dumps(o)


if __name__ == '__main__':
    unittest.main()
