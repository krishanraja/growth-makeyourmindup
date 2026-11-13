"""AI answers through AEO-Engine, the one specialist (protocol 1.22.0; Ruling, Krish, 2026-11-12)."""
import json
import tempfile
import unittest
from pathlib import Path

from engine import ai_answers

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


if __name__ == '__main__':
    unittest.main()
