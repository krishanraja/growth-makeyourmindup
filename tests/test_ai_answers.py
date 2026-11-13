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


# AEO's win kits, the digest re-ask and shipped answer pieces (proposed 1.23.0; Ruling, Krish, 2026-11-13) ---------

HOSTS = ['home.makeyourmindup.ai', 'makeyourmindup.ai']
KIT_A = {
    'kit_id': 'kit-a', 'v': 1, 'query_id': 'q-a', 'question': 'Synthetic kit question about who gets paid?',
    'gap_class': 'no_page', 'priority': 2, 'title': 'Synthetic kit title alpha',
    'target': {'kind': 'new_page', 'url': None, 'host': 'home.makeyourmindup.ai', 'suggested_path': '/p/synthetic-alpha'},
    'capsule': {'rules': ['Synthetic capsule rule'], 'must_cover': ['synthetic point']},
    'h2s': ['Synthetic heading alpha'],
    'beat': [{'url': 'https://rival.example/page', 'host': 'rival.example', 'engine': 'perplexity', 'position': 1,
              'features': ['faq']}],
    'site_fixes': [
        {'gate': 'sitemap', 'host': 'makeyourmindup.ai', 'url': 'https://makeyourmindup.ai/sitemap.xml',
         'fix': 'List every answer page in the sitemap', 'owner_repo': 'krishanraja/makeyourmindup'},
        {'gate': 'faq', 'host': 'makeyourmindup.ai', 'url': None, 'fix': 'Add personal examples to the FAQ',
         'owner_repo': 'krishanraja/makeyourmindup'},
        {'gate': 'schema', 'host': 'makeyourmindup.ai', 'url': None, 'fix': 'Add Person schema to every article',
         'owner_repo': 'krishanraja/makeyourmindup'},
        {'gate': 'eeat', 'host': 'makeyourmindup.ai', 'url': None, 'fix': 'Add a bio with a byline to each piece',
         'owner_repo': 'krishanraja/makeyourmindup'},
        {'gate': 'about', 'host': 'makeyourmindup.ai', 'url': 'https://makeyourmindup.ai/about',
         'fix': 'Link Krish Raja profiles from the about page', 'owner_repo': 'krishanraja/makeyourmindup'},
        'not a fix',
    ],
    'off_site': [{'host': 'reddit.example', 'url': None, 'source_type': 'forum', 'engines': ['perplexity'],
                  'why': 'Cited first on two engines'},
                 {'host': 'linkedin.com', 'url': None, 'source_type': 'social', 'engines': ['chatgpt'],
                  'why': 'Post as Krish on LinkedIn'}],
    'verify': {'engines': ['perplexity', 'chatgpt'], 'samples': 3, 'success': 'cited first on two engines',
               'recheck': '2026-11-29', 'baseline': 0},
    'evidence': ['https://aeo.example/run'],
}
KIT_B = {'kit_id': 'kit-b', 'question': 'Synthetic second kit question?', 'priority': 1, 'title': None}
KIT_C = {'kit_id': 'kit-c', 'title': 'Synthetic kit title gamma', 'priority': None, 'site_fixes': 'broken', 'h2s': [3, 'Ok heading']}
UNREADABLE = ['x', {'kit_id': 'empty'}, {'title': 5}, None]
KIT_WORDS = ('Synthetic kit', 'Synthetic second kit', 'Synthetic capsule', 'Synthetic heading', 'rival.example',
             'sitemap', 'Person schema', 'reddit.example')


def detailed(standing, detail=True):
    out = directive(standing)
    if detail:
        out['directive']['features']['ai_answers_detail'] = True
    return out


def questions_file(tmp, rows, extra=None):
    (Path(tmp) / 'config').mkdir(exist_ok=True)
    data = {'domains': HOSTS, 'questions': rows, **(extra or {})}
    (Path(tmp) / ai_answers.QUESTIONS).write_text(json.dumps(data), encoding='utf-8')


def read_file(tmp):
    return json.loads((Path(tmp) / ai_answers.QUESTIONS).read_text(encoding='utf-8'))


SHIPPED = {'question': 'Who gets paid when AI licenses the news?',
           'shipped': {'url': 'https://home.makeyourmindup.ai/p/who-gets-paid', 'shipped_at': '2026-11-14'}}
PLAIN = {'question': 'Will AI take my job before the decade is out?'}


class KitsTest(unittest.TestCase):
    """AEO's win kits reach Krish through this engine (Ruling, Krish, 2026-11-13), read loosely and never committed."""

    def test_request_digest_matches_control_centers_definition_on_a_fixed_vector(self):
        # Computed with JavaScript: q.trim().replace(/\s+/g, ' '), sorted by code point, JSON.stringify, SHA-256.
        vector = ['  Will AI\ttake my   job? ', 'Is the AI bubble going to burst?', 'État de l’IA en 2026?',
                  'Ａ fullwidth question about AI?', '\U00020000 ideograph question about AI?',
                  'Who pays when an agent shops?\n']
        self.assertEqual(ai_answers.request_digest(vector),
                         'f7a7165ab181193439f9e6fc29fc3d8fb1b38d73cbd7f2f5abbfb96fbd7e0885')
        # The order never matters, and code point order is not UTF-16 order (JavaScript's default sort gives 9d2844f9...).
        self.assertEqual(ai_answers.request_digest(list(reversed(vector))), ai_answers.request_digest(vector))
        # JavaScript's whitespace, not Python's: U+FEFF trims, U+0085 and U+001C stay (escaped as \u001c).
        self.assertEqual(ai_answers.request_digest(['﻿Will AI take my job?\x85', 'Who\x1cpays when an agent shops?']),
                         'b81c1f8286c79c1b5f11f4727f51fb8b37a4e18e2fd984542b00c239fbce610f')
        # A lone surrogate is escaped as JSON.stringify writes it, and the empty list is "[]".
        self.assertEqual(ai_answers.request_digest(['Lone \ud800 surrogate question?', 'Who pays when an agent shops?']),
                         '5b1b7da10609e803f99093e33e720862887391cdd17a07ec3a7f8c5b2e33b046')
        self.assertEqual(ai_answers.request_digest([]), '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945')

    def test_kits_are_read_loosely_highest_priority_first_and_at_most_five(self):
        # AEO ranks a higher priority first (AEO-Engine src/pipeline/62-kits.ts: b.priority - a.priority).
        s = {'kits': [KIT_C, KIT_A, *UNREADABLE, KIT_B, dict(KIT_A, title='A repeat of kit a')]}
        found, counts = ai_answers.read_kits(s)
        self.assertEqual([k['kit_id'] for k in found], ['kit-a', 'kit-b', 'kit-c'])
        self.assertEqual(counts, {'served': 3, 'unreadable': 4, 'dropped': 4})
        self.assertEqual(found[2]['site_fixes'], [])
        self.assertEqual(found[2]['h2s'], ['Ok heading'])
        two = {'kits': [{'kit_id': 'lo', 'question': 'Synthetic low question?', 'priority': 1.0},
                        {'kit_id': 'hi', 'question': 'Synthetic high question?', 'priority': 8.0}]}
        self.assertEqual([k['kit_id'] for k in ai_answers.kits(two)], ['hi', 'lo'])
        # More than five served: the cut keeps the five highest, a kit with no priority last, served order on a tie.
        many = {'kits': [{'kit_id': 'none', 'question': 'Synthetic unranked question?'}]
                + [{'kit_id': f'k{i}', 'question': f'Synthetic question number {i}?', 'priority': 10 - i} for i in range(8)]
                + [{'kit_id': 'tie', 'question': 'Synthetic tied question?', 'priority': 8}]}
        self.assertEqual([k['kit_id'] for k in ai_answers.kits(many)], ['k0', 'k1', 'k2', 'tie', 'k3'])
        self.assertEqual([k['kit_id'] for k in ai_answers.kits({'kits': many['kits'][:1] + many['kits'][-1:]})],
                         ['tie', 'none'])
        for broken in (None, {}, {'kits': None}, {'kits': 'x'}, {'kits': {'a': 1}}, 'standing', []):
            self.assertEqual(ai_answers.read_kits(broken), ([], {'served': 0, 'unreadable': 0, 'dropped': 0}))

    def test_a_number_too_large_or_not_finite_is_malformed_never_an_error(self):
        huge = int('9' * 400)
        kit = {'kit_id': 'big', 'question': 'Synthetic big question?', 'priority': huge, 'v': huge,
               'beat': [{'host': 'rival.example', 'position': huge}], 'verify': {'samples': huge, 'baseline': huge}}
        found, counts = ai_answers.read_kits({'kits': [kit, dict(KIT_B, priority=float('inf')), dict(KIT_C, priority=float('nan'))]})
        self.assertEqual(counts['served'], 3)
        self.assertEqual([(k['kit_id'], k['priority']) for k in found], [('big', None), ('kit-b', None), ('kit-c', None)])
        self.assertEqual((found[0]['v'], found[0]['beat'][0]['position'], found[0]['verify']['samples'],
                          found[0]['verify']['baseline']), (None, None, None, None))
        self.assertEqual(ai_answers.kits({'kits': [dict(KIT_B, priority=10 ** 15)]})[0]['priority'], 10 ** 15)
        standing = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 1}, 'kits': [kit]}
        self.assertIn('Kit 1: Synthetic big question?', ai_answers.block(detailed(standing)))
        self.assertTrue(ai_answers.sync(FakeClient(), detailed(standing), ROOT))

    def test_a_malformed_features_or_directive_body_is_read_as_none_never_an_error(self):
        for body in ({'features': ['x']}, {'features': 'x', 'ai_answers': {'standing': None}}, {'features': 5}):
            d = {'ok': True, 'directive': body}
            self.assertFalse(ai_answers.detail_served(d))
            self.assertEqual(ai_answers.served(d), 'ai_answers' in body)
            self.assertTrue(ai_answers.block(d))
            self.assertIsInstance(ai_answers.sync(FakeClient(), d, ROOT), list)
        for d in ({'ok': True, 'directive': ['x']}, {'ok': True, 'directive': 'x'}, ['x'], None, 'x'):
            self.assertEqual((ai_answers.served(d), ai_answers.readable(d), ai_answers.standing(d)), (False, False, None))
            self.assertEqual(ai_answers.sync(FakeClient(), d, ROOT), [])
            self.assertEqual(ai_answers.block(d)[1], "Not served by today's directive.")

    def test_a_kit_fix_for_author_or_person_work_under_his_name_is_dropped_and_counted(self):
        # R100: no content refers to Krish and no article is authored by him, so no kit adds that work.
        kit = ai_answers.kits({'kits': [KIT_A]})[0]
        self.assertEqual([f['gate'] for f in kit['site_fixes']], ['sitemap', 'faq'])
        self.assertEqual([m['host'] for m in kit['off_site']], ['reddit.example'])
        text = json.dumps(kit)
        for gone in ('Person schema', 'byline', 'Krish', '/about'):
            self.assertNotIn(gone, text)
        for words in ('Add author markup', 'rel=author on each piece', 'Strengthen E-E-A-T signals', 'Add a ProfilePage',
                      'Use the krishraja handle', 'Add schema.org/Person', 'Show who authored each piece',
                      'Add a writer bio with credentials to each article', 'Add an Organization founder with sameAs links',
                      'Add an about-the-author box', 'Co-authoring notes on every piece', 'Show the expertise behind it',
                      'Add a headshot to each article', 'Build E-A-T on the about page'):
            self.assertEqual(ai_answers.read_kits({'kits': [dict(KIT_B, site_fixes=[{'fix': words}])]})[1]['dropped'], 1, words)
        # An off-site move that asks for the same work is dropped too; its host and address only say where.
        for move in ({'host': 'medium.example', 'why': 'Publish a guest post with an author bio'},
                     {'host': 'forum.example', 'source_type': 'byline', 'why': 'Cited by two engines'}):
            self.assertEqual(ai_answers.read_kits({'kits': [dict(KIT_B, off_site=[move])]})[1]['dropped'], 1, move)
        kept = ai_answers.read_kits({'kits': [dict(KIT_B, off_site=[{'host': 'authors.example', 'url': 'https://authors.example/p'}])]})
        self.assertEqual((kept[1]['dropped'], len(kept[0][0]['off_site'])), (0, 1))
        # Whole words only: AEO's own host and page fixes and plain words like these are kept.
        for words in ('Add personal examples to the FAQ', 'Cite authoritative sources', 'Build topical authority',
                      'Publish a sitemap at /sitemap.xml and name it in robots.txt.',
                      'Date the page: datePublished and dateModified in JSON-LD, and a visible date.',
                      'Open with the answer capsule right under the H1: 40 to 60 words that answer the question as asked.',
                      "Point the page's canonical at the page itself."):
            self.assertEqual(ai_answers.read_kits({'kits': [dict(KIT_B, site_fixes=[{'fix': words}])]})[1]['dropped'], 0, words)

    def test_a_malformed_standing_never_raises_and_never_replaces_a_request_on_a_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [SHIPPED, PLAIN])
            client = FakeClient()
            for broken in ('x', 5, [], {'misses': 5, 'moves': 'x', 'kits': 3, 'request': 'r', 'latest': 'l'},
                           {'request': {'id': 'r0', 'digest': 5}, 'kits': [None, 3, 'x']}):
                lines = ai_answers.sync(client, detailed(broken), tmp, NOW)
                self.assertTrue(lines and all(isinstance(l, str) for l in lines), broken)
                self.assertTrue(ai_answers.block(detailed(broken)))
            # A request on file, however malformed, is never replaced: only the shipped list is told, once.
            self.assertEqual([body['mode'] for body in client.posted], ['append'])

    def test_misses_and_moves_puts_the_kits_first(self):
        s = {'kits': [KIT_A, KIT_B], 'misses': [{'question': 'Synthetic second kit question?'}, {'question': 'Miss?'}],
             'moves': [{'title': 'M', 'target_query': 'Move query?'}]}
        self.assertEqual(ai_answers.misses_and_moves(s),
                         ['Synthetic kit title alpha', 'Synthetic second kit question?', 'Miss?', 'Move query?'])
        self.assertEqual(ai_answers.misses_and_moves({'kits': 'broken', 'misses': [{'question': 'Miss?'}]}), ['Miss?'])

    def test_the_report_lines_carry_counts_only_and_the_local_block_carries_the_kit(self):
        standing = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 1},
                    'kits': [KIT_A, KIT_B, KIT_C, 'x'], 'misses': [{'question': 'Synthetic miss question?'}]}
        lines = ai_answers.sync(FakeClient(), detailed(standing), ROOT)
        self.assertIn('AEO-Engine serves 3 win kits for the publication; the answer job reads them first.', lines)
        self.assertTrue(any(l.startswith('Left out 4 kit fixes that would put author or Person work') for l in lines))
        self.assertIn('1 kit could not be read and was left out.', lines)
        joined = '\n'.join(lines)
        for words in KIT_WORDS + ('Synthetic miss',):
            self.assertNotIn(words, joined)
        block = '\n'.join(ai_answers.block(detailed(standing)))
        for words in ("Win kits, highest priority first (AEO's priority: a higher number matters more):",
                      'Kit 1, priority 2: Synthetic kit title alpha', 'Kit 2, priority 1: Synthetic second kit question?',
                      'Kit 3: Synthetic kit title gamma',
                      'Capsule rule: Synthetic capsule rule', 'H2: Synthetic heading alpha', 'Pages to beat (hosts): rival.example',
                      'List every answer page in the sitemap', 'Off site: reddit.example (forum)', 'Synthetic miss question?',
                      'Target: new_page, home.makeyourmindup.ai /p/synthetic-alpha'):
            self.assertIn(words, block)
        for gone in ('https://rival.example/page', 'Person schema', 'byline', 'Krish Raja', 'Post as Krish'):
            self.assertNotIn(gone, block)
        self.assertIn("not served by today's directive yet", '\n'.join(ai_answers.block(detailed(standing, detail=False))))
        self.assertNotIn('Synthetic kit', '\n'.join(ai_answers.block(detailed(standing, detail=False))))
        self.assertEqual(ai_answers.sync(FakeClient(), detailed(standing, detail=False), ROOT),
                         ['AI answers: tracked, not asked yet.'])

    def test_the_digest_on_file_re_asks_only_when_it_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [PLAIN, {'question': 'Is the AI bubble going to burst?'}])
            mine = ai_answers.configured(tmp)[0]
            same = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 2,
                                                                 'digest': ai_answers.request_digest(mine)}}
            other = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 2,
                                                                  'digest': ai_answers.request_digest(mine[:1])}}
            client = FakeClient()
            ai_answers.sync(client, detailed(same), tmp)
            ai_answers.sync(client, detailed(same, detail=False), tmp)
            for broken in ('A' * 64, 'abc', None, 7):
                ai_answers.sync(client, detailed({**other, 'request': {**other['request'], 'digest': broken}}), tmp)
            self.assertEqual(client.posted, [])
            lines = ai_answers.sync(client, detailed(other), tmp, NOW)
            self.assertEqual(client.posted, [{'questions': mine, 'domains': HOSTS, 'mode': 'replace'}])
            self.assertIn('Asked AEO-Engine again to track 2 reader questions, replacing the request on file', lines[-1])
            self.assertEqual(read_file(tmp)['ask'], {'request_id': 'r', 'asked_at': NOW, 'questions': 2,
                                                     'digest': ai_answers.request_digest(mine)})
            # The request on file still reads otherwise (Control Center kept fewer, say): never asked every day.
            lines = ai_answers.sync(client, detailed(other), tmp, NOW)
            self.assertEqual(lines[-1], ai_answers.SETTLED)
            self.assertEqual(len(client.posted), 1)
            # A question added to the file is a new list: asked again, once.
            data = read_file(tmp)
            data['questions'].append({'question': 'Who pays when an agent shops for me?'})
            (Path(tmp) / ai_answers.QUESTIONS).write_text(json.dumps(data), encoding='utf-8')
            ai_answers.sync(client, detailed(other), tmp, NOW)
            self.assertEqual(len(client.posted), 2)
            self.assertEqual(len(client.posted[-1]['questions']), 3)
            self.assertEqual(ai_answers.problems(read_file(tmp)), [])
            # The engine never marks a question shipped.
            self.assertFalse(any(isinstance(q, dict) and 'shipped' in q for q in read_file(tmp)['questions']))

    def test_without_the_detail_flag_a_digest_still_decides_and_the_post_carries_nothing_new(self):
        # As Heartside's on_record and Mindmake's askFor read it: a present digest decides; mode and shipped wait.
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [SHIPPED, PLAIN])
            mine = ai_answers.configured(tmp)[0]
            other = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 1,
                                                                  'digest': ai_answers.request_digest(mine[:1])}}
            client = FakeClient()
            lines = ai_answers.sync(client, directive(other), tmp, NOW)
            self.assertEqual(client.posted, [{'questions': mine, 'domains': HOSTS}])
            self.assertIn('Asked AEO-Engine again to track 2 reader questions, replacing the request on file', lines[-1])
            self.assertFalse(any('win kit' in l for l in lines))
            data = read_file(tmp)
            self.assertEqual(data['ask'], {'request_id': 'r', 'asked_at': NOW, 'questions': 2,
                                           'digest': ai_answers.request_digest(mine)})
            self.assertNotIn('shipped_sent', data)
            self.assertEqual(ai_answers.sync(client, directive(other), tmp, NOW)[-1], ai_answers.SETTLED)
            # No digest and no flag: the 1.22.0 rule, a request on file is not asked for again.
            plain = {**other, 'request': {k: v for k, v in other['request'].items() if k != 'digest'}}
            self.assertEqual(ai_answers.sync(client, directive(plain), tmp, NOW), ['AI answers: tracked, not asked yet.'])
            self.assertEqual(len(client.posted), 1)

    def test_a_standing_that_could_not_be_read_asks_nothing_and_records_nothing(self):
        # The protocol leaves the ai_answers block out when Control Center could not read the standing (1.22.0).
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [SHIPPED, PLAIN], {'ask': 'pending'})
            before = (Path(tmp) / ai_answers.QUESTIONS).read_bytes()
            client = FakeClient()
            unread = [detailed('absent'), directive('absent'),
                      {'ok': True, 'directive': {'features': {'ai_answers': True, 'ai_answers_detail': True},
                                                 'ai_answers': {'rule': 'r'}}},
                      detailed('x'), detailed([]), detailed(5)]
            for _ in range(3):
                for d in unread:
                    lines = ai_answers.sync(client, d, tmp, NOW)
                    self.assertEqual(lines, ["AI answers: the publication's standing could not be read today, so nothing was asked."])
                    self.assertIn('could not read', ai_answers.block(d)[1])
            self.assertEqual(client.posted, [])
            self.assertEqual((Path(tmp) / ai_answers.QUESTIONS).read_bytes(), before)
            # Once it reads (null: no request on file), the pending ask goes, once.
            ai_answers.sync(client, detailed(None), tmp, NOW)
            self.assertEqual(len(client.posted), 1)

    def test_shipped_pieces_are_read_only_from_a_sound_mark_on_the_publications_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = [{'question': 'Is the AI bubble going to burst?', 'shipped': {'url': 'https://elsewhere.example/p', 'shipped_at': '2026-11-14'}},
                   {'question': 'Who pays when an agent shops?', 'shipped': {'url': 'http://makeyourmindup.ai/a', 'shipped_at': '2026-11-14'}},
                   {'question': 'What does an AI agent really cost?', 'shipped': {'url': 'https://makeyourmindup.ai/a', 'shipped_at': 'soon'}},
                   {'question': 'Can an AI agent sign a contract?', 'shipped': {'url': 'https://makeyourmindup.ai.evil.example/a', 'shipped_at': '2026-11-14'}},
                   {'question': 'Does AI make the news worse?', 'shipped': 'yes'}]
            questions_file(tmp, [SHIPPED, PLAIN, *bad, dict(SHIPPED, question='who gets paid when AI licenses the news')])
            self.assertEqual(ai_answers.shipped(tmp), [{'question': SHIPPED['question'], **SHIPPED['shipped']}])
            found = ai_answers.problems(read_file(tmp))
            self.assertEqual(len([p for p in found if 'shipped must be' in p]), 5, found)
            self.assertTrue(any('repeats an earlier one' in p for p in found))

    def test_the_committed_file_is_sound_and_every_shipped_mark_reads(self):
        # A session marks a question shipped and commits it (jobs/answer.md), so the file may hold marks; each must
        # read as one (problems), and the engine never writes one (the sync tests).
        data = json.loads((ROOT / ai_answers.QUESTIONS).read_text(encoding='utf-8'))
        self.assertEqual(ai_answers.problems(data), [])
        marked = [q for q in data.get('questions') or [] if isinstance(q, dict) and 'shipped' in q]
        self.assertEqual(len(ai_answers.shipped(ROOT)), min(len(marked), ai_answers.MAX_QUESTIONS))
        for bad in ([], {'domains': ['https://x.example'], 'questions': []}, {'domains': HOSTS, 'questions': ['short']},
                    {'domains': HOSTS, 'questions': [], 'ask': 3}, {'domains': HOSTS, 'questions': [], 'shipped_sent': {'sha256': 'x'}}):
            self.assertTrue(ai_answers.problems(bad), bad)

    def test_shipped_pieces_go_with_a_request_only_once_the_detail_is_served(self):
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [SHIPPED, PLAIN])
            client = FakeClient()
            ai_answers.sync(client, directive({'tracked': False, 'latest': None, 'request': None}), tmp)
            self.assertEqual(client.posted[-1], {'questions': [SHIPPED['question'], PLAIN['question']], 'domains': HOSTS})
            self.assertNotIn('shipped_sent', read_file(tmp))
            lines = ai_answers.sync(client, detailed({'tracked': False, 'latest': None, 'request': None}), tmp, NOW)
            entry = {'question': SHIPPED['question'], **SHIPPED['shipped']}
            self.assertEqual(client.posted[-1], {'questions': [SHIPPED['question'], PLAIN['question']], 'domains': HOSTS,
                                                 'mode': 'replace', 'shipped': [entry]})
            self.assertIn('with 1 shipped answer piece', lines[-1])
            self.assertEqual(read_file(tmp)['shipped_sent'], {'sha256': ai_answers.shipped_digest([entry]), 'at': NOW,
                                                              'request_id': 'r', 'answers': 1})
            # The same list is not told again once the request is on file.
            filed = {'tracked': True, 'latest': None, 'request': {'id': 'r', 'state': 'open', 'questions': 2,
                                                                  'digest': ai_answers.request_digest(ai_answers.configured(tmp)[0])}}
            self.assertEqual(len(ai_answers.sync(client, detailed(filed), tmp, NOW)), 2)
            self.assertEqual(len(client.posted), 2)

    def test_a_changed_shipped_list_is_told_once_on_its_own_and_a_failure_tells_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            questions_file(tmp, [SHIPPED, PLAIN])
            filed = {'tracked': True, 'latest': None, 'request': {'id': 'r0', 'state': 'served', 'questions': 2,
                                                                  'digest': ai_answers.request_digest(ai_answers.configured(tmp)[0])}}
            lines = ai_answers.sync(FakeClient(fail=True), detailed(filed), tmp, NOW)
            self.assertIn('Could not tell AEO-Engine of 1 shipped answer piece', lines[-1])
            self.assertNotIn('shipped_sent', read_file(tmp))
            client = FakeClient()
            lines = ai_answers.sync(client, detailed(filed), tmp, NOW)
            entry = {'question': SHIPPED['question'], **SHIPPED['shipped']}
            self.assertEqual(client.posted, [{'questions': [SHIPPED['question']], 'domains': HOSTS, 'mode': 'append',
                                              'shipped': [entry]}])
            self.assertIn('Told AEO-Engine of 1 shipped answer piece', lines[-1])
            self.assertNotIn(SHIPPED['question'], '\n'.join(lines))
            ai_answers.sync(client, detailed(filed), tmp, NOW)
            self.assertEqual(len(client.posted), 1)
            data = read_file(tmp)
            data['questions'][1]['shipped'] = {'url': 'https://makeyourmindup.ai/answers/job', 'shipped_at': '2026-11-21T09:00:00Z'}
            (Path(tmp) / ai_answers.QUESTIONS).write_text(json.dumps(data), encoding='utf-8')
            ai_answers.sync(client, detailed(filed), tmp, NOW)
            self.assertEqual(len(client.posted), 2)
            self.assertEqual(len(client.posted[-1]['shipped']), 2)
            self.assertEqual(client.posted[-1]['mode'], 'append')
            self.assertEqual(ai_answers.problems(read_file(tmp)), [])

    def test_his_yes_keeps_a_shipped_mark_on_the_same_question(self):
        tmp = folder()
        try:
            item = ai_answers.questions_proposal(tmp)
            first = ai_answers.parse_payload(item['exact_payload'])[0][0]
            mark = {'url': 'https://home.makeyourmindup.ai/p/bubble', 'shipped_at': '2026-11-14'}
            data = read_file(tmp)
            data['questions'] = [{'question': first, 'shipped': mark}]
            (Path(tmp) / ai_answers.QUESTIONS).write_text(json.dumps(data), encoding='utf-8')
            ai_answers.approved_write(tmp, [decision(item)], NOW)
            written = read_file(tmp)['questions']
            self.assertEqual(written[0], {'question': first, 'from': 'krish_approved', 'shipped': mark})
            self.assertEqual(sum(1 for q in written if 'shipped' in q), 1)
            self.assertEqual(ai_answers.problems(read_file(tmp)), [])
        finally:
            shutil.rmtree(tmp)


class KitsCliTest(unittest.TestCase):
    """The wiring: cc start keeps the kits in the ignored local file; the public runner carries counts only."""

    def setUp(self):
        try:  # discovered from tests/ (growth.py --self-test, unittest discover -s tests)
            import test_control_center as stand_in
        except ImportError:  # run as tests.test_ai_answers from the repository root
            from tests import test_control_center as stand_in
        self.CliTests, self.StandIn, self.now = stand_in.CliTests, stand_in.StandIn, stand_in.NOW

    def standing(self, digest=None):
        return {'tracked': True, 'latest': None, 'misses': [], 'moves': [], 'kits': [KIT_A, KIT_B],
                'request': {'id': 'r0', 'state': 'served', 'questions': 1, 'digest': digest or '0' * 64}}

    def extra(self, standing):
        return {'features': {'ai_answers': True, 'ai_answers_detail': True}, 'ai_answers': {'standing': standing, 'rule': 'r'}}

    def test_cc_start_writes_the_kits_to_the_ignored_local_file_and_prints_a_count(self):
        CC_NOW = self.now
        cli = self.CliTests()
        with self.StandIn() as stand, tempfile.TemporaryDirectory() as tmp:
            cli.workspace(tmp)
            stand.directive_extra = self.extra(self.standing())
            code, text = cli.capture(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', CC_NOW],
                                     stand, tmp)
            self.assertEqual(code, 0, text)
            self.assertIn('AI-answer kits: 2 from AEO-Engine in ' + str(Path('.scratch/cc/ai-answers.txt')), text)
            saved = (Path(tmp) / '.scratch/cc/ai-answers.txt').read_text(encoding='utf-8')
            self.assertIn('Synthetic kit title alpha', saved)
            for words in KIT_WORDS:
                self.assertNotIn(words, text)

    def test_cc_start_survives_a_malformed_features_and_says_nothing_is_served(self):
        CC_NOW = self.now
        cli = self.CliTests()
        with self.StandIn() as stand, tempfile.TemporaryDirectory() as tmp:
            cli.workspace(tmp)
            stand.directive_extra = {'features': ['x']}
            code, text = cli.capture(['cc', 'start', '--job', 'daily', '--deliver', '--mode', 'synthetic', '--now', CC_NOW],
                                     stand, tmp)
            self.assertEqual(code, 0, text)
            self.assertIn('attempt started', text)
            saved = (Path(tmp) / '.scratch/cc/ai-answers.txt').read_text(encoding='utf-8')
            self.assertIn("Not served by today's directive.", saved)

    def test_the_runner_re_asks_on_a_new_digest_with_the_shipped_pieces_and_reports_counts_only(self):
        CC_NOW = self.now
        from engine.control_center import canonical_json
        cli = self.CliTests()
        with self.StandIn() as stand, tempfile.TemporaryDirectory() as tmp:
            cli.workspace(tmp)
            questions_file(tmp, [SHIPPED, PLAIN])
            stand.directive_extra = self.extra(self.standing())
            code, text = cli.capture(['cc', 'runner', '--deliver', '--mode', 'synthetic', '--now', CC_NOW], stand, tmp)
            self.assertEqual(code, 0, text)
            asked = stand.posts('answers')
            self.assertEqual(len(asked), 1)
            self.assertEqual(asked[0]['body']['mode'], 'replace')
            self.assertEqual(asked[0]['body']['shipped'], [{'question': SHIPPED['question'], **SHIPPED['shipped']}])
            report = canonical_json(stand.posts('reports')[0]['body'])
            self.assertIn('AEO-Engine serves 2 win kits for the publication', report)
            self.assertIn('Left out 4 kit fixes', report)
            for words in KIT_WORDS + (SHIPPED['question'], PLAIN['question']):
                self.assertNotIn(words, text)
                self.assertNotIn(words, report)


if __name__ == '__main__':
    unittest.main()
