"""AI answers through AEO-Engine, the one specialist (protocol 1.22.0; Ruling, Krish, 2026-11-12)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from engine import ai_answers, cc_loop
from engine.control_center import amended_digest

ROOT = Path(__file__).resolve().parent.parent


class FakeClient:
    def __init__(self, fail=False):
        self.posted, self.fail = [], fail

    def answers_request(self, body):
        if self.fail:
            raise RuntimeError('down')
        self.posted.append(body)
        return {'ok': True, 'request_id': 'r', 'questions': len(body['questions'])}


def directive(standing='absent', features=True):
    body = {'features': {'engine_state': True, 'krish_instruction': True, **({'ai_answers': True} if features else {})}}
    if standing != 'absent':
        body['ai_answers'] = {'standing': standing, 'rule': 'r'}
    return {'ok': True, 'directive': body}


class AiAnswersTest(unittest.TestCase):
    def test_the_committed_file_holds_no_invented_question_and_names_the_hosts(self):
        questions, hosts = ai_answers.configured(ROOT)
        self.assertEqual(hosts, ['home.makeyourmindup.ai', 'makeyourmindup.ai'])
        self.assertTrue(all('@' not in q for q in questions))

    def test_with_no_reader_question_on_file_it_asks_nothing_and_says_so(self):
        client = FakeClient()
        lines = ai_answers.sync(client, directive(None), ROOT)
        self.assertEqual(client.posted, [])
        self.assertEqual(lines[0], 'AI answers: not tracked yet.')
        self.assertIn('No real reader question is on file', lines[1])

    def test_with_reader_questions_and_no_request_it_asks_aeo_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'config').mkdir()
            (Path(tmp) / ai_answers.QUESTIONS).write_text(json.dumps({'domains': ['home.makeyourmindup.ai'], 'questions': [{'question': 'Who actually gets paid when AI licenses the news?'}, 'short']}))
            client = FakeClient()
            lines = ai_answers.sync(client, directive({'tracked': False, 'latest': None, 'request': None}), tmp)
            self.assertEqual(client.posted, [{'questions': ['Who actually gets paid when AI licenses the news?'], 'domains': ['home.makeyourmindup.ai']}])
            self.assertIn('Asked AEO-Engine to track 1 reader question', lines[-1])
            self.assertEqual(ai_answers.sync(FakeClient(fail=True), directive(None), tmp)[-1][:30], 'Could not ask AEO-Engine to tr')

    def test_a_request_on_file_or_an_unserved_directive_asks_nothing(self):
        client = FakeClient()
        standing = {'tracked': True, 'latest': {'as_of': '2026-11-22', 'asked': 12, 'cited_first': 0}, 'request': {'state': 'served'},
                    'misses': [{'question': 'Q one?', 'first': 'x.example'}], 'moves': [{'title': 'M', 'target_query': 'Q one?'}]}
        self.assertEqual(ai_answers.sync(client, directive(standing), ROOT), ['AI answers: cited first on 0 of 12 questions, 22 Nov.'])
        self.assertEqual(ai_answers.misses_and_moves(standing), ['Q one?'])
        self.assertEqual(ai_answers.sync(client, directive(features=False), ROOT), [])
        self.assertEqual(client.posted, [])


PID = 'makeyourmindup:ai-answer-questions:2026-11-13'
NOW = '2026-11-14T05:10:00Z'


def folder():
    """A temporary root holding the committed proposed set and the committed questions file."""
    tmp = tempfile.mkdtemp()
    (Path(tmp) / 'config').mkdir()
    for name in (ai_answers.PROPOSED, ai_answers.QUESTIONS):
        shutil.copy(ROOT / name, Path(tmp) / name)
    return tmp


def decision(item, verdict='approved', words=None, digest=None, at='2026-11-14T04:00:00Z'):
    d = {'proposal_id': item['proposal_id'], 'decision': verdict, 'decided_at': at,
         'payload_sha256': digest or item['payload_sha256'], 'stage': None, 'amended': words is not None}
    if words is not None:
        d.update(exact_payload=words, amount_usd=None, amended_sha256=amended_digest(None, words))
    return d


class ProposedQuestionsTest(unittest.TestCase):
    """Ruling (Krish, 2026-11-13): Make Your Mind Up's growth engine proposes its AI-answer questions for his approval."""

    def setUp(self):
        self.tmp = folder()
        self.item = ai_answers.questions_proposal(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def file(self):
        return json.loads((Path(self.tmp) / ai_answers.QUESTIONS).read_text(encoding='utf-8'))

    def test_the_set_is_one_strategy_ask_whose_exact_words_are_the_questions(self):
        item = self.item
        self.assertEqual((item['proposal_id'], item['wall'], item['kind']), (PID, 'strategy', 'prepared'))
        self.assertEqual(item['close_condition'], {'event': 'questions_written', 'reference': ai_answers.QUESTIONS})
        questions, refused = ai_answers.parse_payload(item['exact_payload'])
        self.assertEqual((len(questions), refused), (20, 0))
        proposed = json.loads((ROOT / ai_answers.PROPOSED).read_text(encoding='utf-8'))['questions']
        self.assertEqual(questions, [q['question'] for q in proposed])
        text = json.dumps(item, ensure_ascii=False)
        for banned in ('Mindmake', 'mind/make', 'CTRL', 'Krish', '\u2014'):
            self.assertNotIn(banned, item['exact_payload'] + item['title'], banned)
        self.assertNotIn('\u2014', text)
        self.assertTrue(all(e['url'].startswith('https://') for e in item['evidence']))
        self.assertTrue(all(q.endswith('?') for q in questions))
        self.assertEqual({q['series'] for q in proposed}, {'follow.the.money', 'under.the.hood', 'mind.the.gap', 'good news'})

    def test_his_words_back_numbered_or_ending_in_a_question_mark_and_never_a_contact(self):
        words = ('How to change it.\n\n1. Is the AI bubble going to burst?\n2)  Will AI   take my job?\n'
                 '- Who pays when an agent shops?\nA note, not a question.\n3. Call 020 7946 0958 now?\n'
                 '4. Mail hello@example.com?\n5. Short?\n6. is the ai bubble going to burst?')
        self.assertEqual(ai_answers.parse_payload(words),
                         (['Is the AI bubble going to burst?', 'Will AI take my job?', 'Who pays when an agent shops?'], 3))

    def test_no_decision_or_his_no_writes_nothing(self):
        before = self.file()
        self.assertEqual(ai_answers.approved_write(self.tmp, [], NOW), ([], None))
        lines, event = ai_answers.approved_write(self.tmp, [decision(self.item, 'declined')], NOW)
        self.assertIsNone(event)
        self.assertIn('said no', lines[0])
        lines, event = ai_answers.approved_write(self.tmp, None, NOW)
        self.assertIsNone(event)
        self.assertIn("Could not read Krish's decisions", lines[0])
        self.assertEqual(self.file(), before)

    def test_his_yes_writes_exactly_the_proposed_questions_once_and_closes_the_ask(self):
        lines, event = ai_answers.approved_write(self.tmp, [decision(self.item)], NOW)
        data = self.file()
        proposed = ai_answers.parse_payload(self.item['exact_payload'])[0]
        self.assertEqual([q['question'] for q in data['questions']], proposed)
        self.assertEqual({q['from'] for q in data['questions']}, {'krish_approved'})
        self.assertEqual(data['ask'], 'pending')
        self.assertEqual(data['approved'], {'proposal_id': PID, 'sha256': self.item['payload_sha256'], 'amended': False,
                                            'decided_at': '2026-11-14T04:00:00Z', 'questions': 20})
        self.assertEqual(data['domains'], ['home.makeyourmindup.ai', 'makeyourmindup.ai'])
        self.assertEqual(event, {'event': 'questions_written', 'proposal_id': PID, 'at': NOW, 'evidence_url': ai_answers.FILE_URL})
        self.assertIn('Krish approved 20 AI-answer questions', lines[0])
        # The same yes again writes nothing new; the close is sent again until Control Centre marks it done.
        self.assertEqual(ai_answers.approved_write(self.tmp, [decision(self.item)], NOW), ([], event))
        self.assertEqual(ai_answers.approved_write(self.tmp, [decision(self.item, 'done')], NOW), ([], None))
        self.assertEqual(self.file(), data)

    def test_his_amended_version_is_what_is_written_never_the_engines(self):
        words = self.item['exact_payload'].replace('1. Is the AI bubble going to burst?\n', '')
        words = words.replace('Will AI cure cancer?', 'Can AI help find a cure for cancer?')
        words += '\nWho owns a song an AI wrote?'
        lines, event = ai_answers.approved_write(self.tmp, [decision(self.item, words=words)], NOW)
        written = [q['question'] for q in self.file()['questions']]
        self.assertEqual(len(written), 20)
        self.assertNotIn('Is the AI bubble going to burst?', written)
        self.assertNotIn('Will AI cure cancer?', written)
        self.assertIn('Can AI help find a cure for cancer?', written)
        self.assertEqual(written[-1], 'Who owns a song an AI wrote?')
        self.assertTrue(self.file()['approved']['amended'])
        self.assertIn('in his own version', lines[0])
        self.assertEqual(event['proposal_id'], PID)

    def test_a_yes_on_other_words_or_a_broken_amendment_writes_nothing(self):
        before = self.file()
        lines, event = ai_answers.approved_write(self.tmp, [decision(self.item, digest='0' * 64)], NOW)
        self.assertIsNone(event)
        self.assertIn('another version', lines[0])
        bad = decision(self.item, words='1. Will AI take my job?')
        bad['amended_sha256'] = '0' * 64
        lines, event = ai_answers.approved_write(self.tmp, [bad], NOW)
        self.assertIsNone(event)
        self.assertIn('did not match its digest', lines[0])
        self.assertEqual(self.file(), before)

    def test_a_reader_question_already_on_file_stays_after_his(self):
        data = self.file()
        data['questions'] = [{'question': 'Who gets paid when AI licenses the news?'}, 'Will AI take my job?']
        (Path(self.tmp) / ai_answers.QUESTIONS).write_text(json.dumps(data), encoding='utf-8')
        ai_answers.approved_write(self.tmp, [decision(self.item)], NOW)
        written = [q['question'] if isinstance(q, dict) else q for q in self.file()['questions']]
        self.assertEqual(len(written), 21)
        self.assertEqual(written[-1], 'Who gets paid when AI licenses the news?')
        self.assertEqual(written.count('Will AI take my job?'), 1)

    def test_after_his_yes_aeo_is_asked_even_with_an_older_request_on_file_and_only_once(self):
        ai_answers.approved_write(self.tmp, [decision(self.item)], NOW)
        standing = {'tracked': True, 'latest': None, 'request': {'id': 'old', 'state': 'served'}}
        client = FakeClient()
        lines = ai_answers.sync(client, directive(standing), self.tmp, NOW)
        self.assertEqual(len(client.posted), 1)
        self.assertEqual(len(client.posted[0]['questions']), 20)
        self.assertEqual(client.posted[0]['domains'], ['home.makeyourmindup.ai', 'makeyourmindup.ai'])
        self.assertEqual(self.file()['ask'], {'request_id': 'r', 'asked_at': NOW, 'questions': 20})
        self.assertIn('the 20 questions Krish approved', lines[-1])
        self.assertEqual(len(ai_answers.sync(client, directive(standing), self.tmp, NOW)), 1)
        self.assertEqual(len(client.posted), 1)

    def test_a_failed_ask_stays_pending_for_the_next_run(self):
        ai_answers.approved_write(self.tmp, [decision(self.item)], NOW)
        lines = ai_answers.sync(FakeClient(fail=True), directive({'tracked': False, 'latest': None, 'request': None}), self.tmp, NOW)
        self.assertIn('Could not ask AEO-Engine', lines[-1])
        self.assertEqual(self.file()['ask'], 'pending')

    def test_the_runner_sends_the_set_once_and_carries_the_close(self):
        checks = [{'name': 'self_test', 'ok': True, 'stdout': '', 'stderr': 'Ran 1 test'}]
        report = cc_loop.runner_report(ROOT, 'r1', NOW, checks, 'synthetic', True, 'fixture', sent={})[0]
        sent = [p for p in report['proposals'] if p['proposal_id'] == PID]
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]['payload_sha256'], ai_answers.questions_proposal(ROOT)['payload_sha256'])
        waiting = cc_loop.runner_report(ROOT, 'r1', NOW, checks, 'synthetic', True, 'fixture', sent={PID: 'pending'})[0]
        self.assertNotIn(PID, {p['proposal_id'] for p in waiting['proposals']})
        self.assertTrue(any(h['reason'] == cc_loop.WAITING and PID in h['detail'] for h in waiting['holds']))
        event = {'event': 'questions_written', 'proposal_id': PID, 'at': NOW, 'evidence_url': ai_answers.FILE_URL}
        closed = cc_loop.runner_report(ROOT, 'r1', NOW, checks, 'synthetic', True, 'fixture', sent={PID: 'approved'},
                                       events=[event])[0]
        self.assertEqual(closed['events'], [event])
        self.assertNotIn(PID, {p['proposal_id'] for p in closed['proposals']})

    def test_an_unreadable_set_is_a_hold_never_a_partial_ask(self):
        (Path(self.tmp) / ai_answers.PROPOSED).write_text('{"proposal_id": "x", "questions": ["Call 020 7946 0958?"]}')
        item, hold = ai_answers.proposal_or_hold(self.tmp)
        self.assertIsNone(item)
        self.assertEqual(hold['reason'], 'The proposed AI-answer questions could not be read')


if __name__ == '__main__':
    unittest.main()
