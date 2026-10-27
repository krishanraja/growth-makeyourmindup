"""Lane L0 handoff against local stand-ins for Control Center and Buffer only.

A routine's dispatch becomes a go-live (or a week ask) Krish approves with one
press, and the go-live it proposes is exactly the one autorelease releases.
No test reaches controlcenter.krishraja.com, api.buffer.com or any media host.
Every word, id, digest and byte here is synthetic.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

try:
    from test_autonomy import CapableStandIn
    from test_run_autorelease import BufferStandIn, fetch, sha, staged_report
except ImportError:  # run as tests.test_run_handoff
    from tests.test_autonomy import CapableStandIn
    from tests.test_run_autorelease import BufferStandIn, fetch, sha, staged_report

from engine.control_center import proposal
from engine.run import autorelease, handoff
from engine.run.autorelease import line_digest, parse_manifest, staged_report_run_id
from engine.run.handoff import GO_LIVE, MAKE_PIECE, PAYLOAD_CAP, WEEK_PACKET

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-03T15:00:00Z'
DUE = '2026-11-04T14:00:00Z'
RUN = 'makeyourmindup:2026-11-03:piece'
GOLIVE = 'makeyourmindup:golive:2026-11-03:piece'
PLAN = 'makeyourmindup:plan:w45-w52'
P_THREADS, P_X, P_LINKEDIN, P_CAROUSEL = ('dddddddddddddddddddddd01', 'dddddddddddddddddddddd02',
                                          'dddddddddddddddddddddd03', 'dddddddddddddddddddddd04')
CH = 'eeeeeeeeeeeeeeeeeeeeee01'
WORDS = {P_THREADS: 'Synthetic handoff words for the threads slot.', P_X: 'Synthetic handoff words for the x slot.',
         P_LINKEDIN: 'Synthetic handoff words for the linkedin slot.',
         P_CAROUSEL: 'Synthetic handoff words for the carousel slot.'}
IMAGE = b'synthetic handoff image bytes\n'
SERVICE = {'threads': 'threads', 'x': 'twitter', 'linkedin': 'linkedin', 'instagram': 'instagram'}
METADATA = {'threads': {'__typename': 'ThreadsPostMetadata', 'type': 'post', 'threadCount': 0, 'linkAttachment': None},
            'x': {'__typename': 'TwitterPostMetadata', 'type': 'post', 'isAiGenerated': False, 'threadCount': 0,
                  'retweet': None},
            'linkedin': None,
            'instagram': {'__typename': 'InstagramPostMetadata', 'type': 'carousel', 'shouldShareToFeed': True,
                          'isAiGenerated': None, 'firstComment': None, 'link': None, 'stickerFields': None,
                          'geolocation': None}}


def routine_slot(slot_id, channel, draft, words, assets=(), mode='engine', due=DUE, fmt='post', review=False):
    """One slot as a routine dispatches it: ids, codes, a time and the spec's digest."""
    digest = line_digest({'channel': channel, 'format': fmt, 'words': words, 'link_placement': None,
                          'due_at': due, 'publish_mode': mode, 'assets': list(assets)})
    return {'slot': slot_id, 'channel': channel, 'buffer_draft_id': draft, 'payload_sha256': digest,
            'per_item_review': review, 'format': fmt, 'due_at': due, 'link_placement': None, 'publish_mode': mode}


class Fixture:
    """One approved standing plan, Buffer drafts for three slots and the routine's manifest."""

    def __init__(self, cc, buf):
        self.cc, self.buf = cc, buf
        buf.media['img.png'] = IMAGE
        self.image = {'type': 'image', 'source': buf.base + '/media/img.png', 'mimeType': 'image/png',
                      'image': {'altText': 'Synthetic alt text', 'userTags': None}}
        self.draft(P_THREADS, 'threads', [self.image])
        self.draft(P_X, 'x')
        self.draft(P_LINKEDIN, 'linkedin')
        self.slots = [routine_slot('threads-1', 'threads', P_THREADS, WORDS[P_THREADS], [sha(IMAGE)]),
                      routine_slot('x-1', 'x', P_X, WORDS[P_X]),
                      routine_slot('linkedin-1', 'linkedin', P_LINKEDIN, WORDS[P_LINKEDIN], mode='krish_click', due=None)]
        self.plan = proposal(PLAN, 'Synthetic standing plan', 'Synthetic why', 'advice', 'strategy', 'reviewed',
                             exact_payload='Synthetic standing plan words.', stage='plan')
        report = staged_report(self.plan)
        cc.reports[report['run_id']] = report
        cc.decisions = [self.decision(self.plan, '2026-11-01T12:00:00Z')]

    def draft(self, post_id, channel, assets=(), words=None, status='draft'):
        self.buf.posts[post_id] = {'id': post_id, 'status': status, 'dueAt': None, 'schedulingType': 'automatic',
                                   'via': 'api', 'text': words or WORDS[post_id], 'channelId': CH,
                                   'channelService': SERVICE[channel], 'assets': list(assets),
                                   'metadata': METADATA[channel]}

    def payload(self, **extra):
        return dict({'run_id': RUN, 'slots': self.slots}, **extra)

    @staticmethod
    def decision(item, at, **extra):
        return dict({'proposal_id': item['proposal_id'], 'decision': 'approved', 'decided_at': at,
                     'payload_sha256': item['payload_sha256'], 'stage': item['stage'], 'amended': False}, **extra)


class HandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = CapableStandIn().__enter__()
        cls.buf = BufferStandIn().__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.cc.__exit__()
        cls.buf.__exit__()

    def setUp(self):
        self.cc.reports, self.cc.calls, self.cc.decisions = {}, [], []
        self.buf.reset()
        self.fix = Fixture(self.cc, self.buf)
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / 'handoff.json'

    def tearDown(self):
        self.tmp.cleanup()

    def run_handoff(self, payload=None, event=GO_LIVE, deliver=True, root=None):
        payload = self.fix.payload() if payload is None else payload
        return handoff.handoff(event, payload, self.cc.client(), self.buf.client(), NOW, deliver, fetch,
                               root or ROOT, self.out)

    def proposals(self):
        return [p for r in self.cc.reports.values() for p in r['proposals'] if p.get('stage') == 'go_live']

    def report_posts(self):
        return self.cc.posts('reports')

    def test_a_matching_manifest_is_proposed_and_autorelease_releases_it(self):
        summary, code = self.run_handoff()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'proposed': 3})
        self.assertEqual(summary['proposals'], {'go_live': 1})
        self.assertEqual(summary['reports']['posted'], 1)
        self.assertEqual(summary['reports']['readback_matches'], 1)
        [item] = self.proposals()
        # Its own report, at the run_id convention, under the open plan, a post wall with target null.
        self.assertIn(staged_report_run_id(GOLIVE, item['payload_sha256']), self.cc.reports)
        self.assertEqual(item['proposal_id'], GOLIVE)
        self.assertEqual((item['stage'], item['parent_proposal_id'], item['wall']), ('go_live', PLAN, 'post'))
        self.assertLessEqual(len(item['exact_payload']), PAYLOAD_CAP)
        lines = parse_manifest(item['exact_payload'], engine=True)
        self.assertEqual(sorted(lines), ['linkedin-1', 'threads-1', 'x-1'])
        for slot in self.fix.slots:
            self.assertEqual(lines[slot['slot']]['payload_sha256'], slot['payload_sha256'])
        self.assertEqual(lines['threads-1']['assets'], [sha(IMAGE)])
        self.assertEqual(json.loads(item['exact_payload'])['run_id'], RUN)
        self.assertIn('Yes schedules these 2 exact posts in Buffer', item['why'])
        self.assertIn('Until 29 November 2026 you see every batch', item['why'])
        self.assertIn('LinkedIn', item['why'])
        # Nothing was scheduled by the handoff.
        self.assertEqual(self.buf.mutations(), [])
        # Krish approves; autorelease finds that exact go-live and schedules it once.
        self.cc.decisions.append(self.fix.decision(item, '2026-11-03T14:30:00Z'))
        released, code = autorelease.autorelease(self.cc.client(), self.buf.client(), NOW, True, fetch)
        self.assertEqual(code, 0, released)
        self.assertEqual(released['slots'], {'krish_click': 1, 'scheduled': 2})
        self.assertEqual(self.buf.posts[P_X]['status'], 'scheduled')
        self.assertEqual(self.buf.posts[P_LINKEDIN]['status'], 'draft')

    def test_a_second_handoff_of_the_same_manifest_reports_nothing_new(self):
        self.run_handoff()
        before = dict(self.cc.reports)
        summary, code = handoff.handoff(GO_LIVE, self.fix.payload(), self.cc.client(), self.buf.client(),
                                        '2026-11-03T15:05:00Z', True, fetch, ROOT, self.out)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['reports']['already_reported'], 1)
        self.assertEqual(self.cc.reports, before)

    def test_a_mismatched_digest_holds_that_slot(self):
        self.buf.posts[P_X]['text'] = WORDS[P_X] + ' Edited after lint.'
        summary, code = self.run_handoff()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['holds'], {'handoff_digest_mismatch': 1})
        self.assertEqual(summary['slots'], {'held': 1, 'proposed': 2})
        [item] = self.proposals()
        self.assertNotIn('x-1', parse_manifest(item['exact_payload']))
        report = self.cc.reports[staged_report_run_id(item['proposal_id'], item['payload_sha256'])]
        self.assertEqual([h['reason'] for h in report['holds']], ['handoff_digest_mismatch'])

    def test_a_draft_that_is_no_longer_a_draft_holds(self):
        self.buf.posts[P_X]['status'] = 'scheduled'
        summary, _ = self.run_handoff()
        self.assertEqual(summary['holds'], {'not_a_draft': 1})
        self.assertNotIn('x-1', parse_manifest(self.proposals()[0]['exact_payload']))

    def test_linkedin_always_goes_in_as_krish_click(self):
        self.fix.slots[2] = routine_slot('linkedin-1', 'linkedin', P_LINKEDIN, WORDS[P_LINKEDIN], mode='engine')
        summary, code = self.run_handoff()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'linkedin_to_krish_click': 1, 'proposed': 3})
        line = parse_manifest(self.proposals()[0]['exact_payload'], engine=True)['linkedin-1']
        self.assertEqual(line['publish_mode'], 'krish_click')
        self.assertEqual(line['payload_sha256'], line_digest(line))

    def test_an_oversize_manifest_splits_into_go_lives_in_order(self):
        long_words = 'Synthetic long handoff words. ' * 25
        slots = []
        for index in range(30):
            post_id = 'ffffffffffffffffffffff' + '%02d' % index
            self.fix.draft(post_id, 'x', words=long_words)
            slots.append(routine_slot('x-%02d' % index, 'x', post_id, long_words))
        summary, code = self.run_handoff({'run_id': RUN, 'slots': slots})
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['slots'], {'proposed': 30})
        items = sorted(self.proposals(), key=lambda p: int(p['proposal_id'].rsplit(':p', 1)[1]))
        self.assertGreater(len(items), 1)
        self.assertEqual(summary['proposals'], {'go_live': len(items)})
        self.assertEqual(summary['reports']['posted'], len(items))
        seen = []
        for number, item in enumerate(items, 1):
            self.assertEqual(item['proposal_id'], GOLIVE + ':p' + str(number))
            self.assertLessEqual(len(item['exact_payload']), PAYLOAD_CAP)
            self.assertIn('(part ' + str(number) + ' of ' + str(len(items)) + ')', item['title'])
            seen += sorted(parse_manifest(item['exact_payload']))
        self.assertEqual(sorted(seen), ['x-%02d' % i for i in range(30)])

    def test_a_new_kind_of_post_is_its_own_go_live(self):
        self.fix.draft(P_CAROUSEL, 'instagram', [self.fix.image])
        self.fix.slots.append(routine_slot('ig-1', 'instagram', P_CAROUSEL, WORDS[P_CAROUSEL], [sha(IMAGE)],
                                           fmt='carousel', review=False))
        summary, code = self.run_handoff()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['proposals'], {'go_live': 2})
        self.assertEqual(summary['slots'], {'own_review': 1, 'proposed': 4})
        by_id = {p['proposal_id']: p for p in self.proposals()}
        self.assertEqual(sorted(parse_manifest(by_id[GOLIVE + ':item-1']['exact_payload'])), ['ig-1'])
        self.assertIn('New kind of post', by_id[GOLIVE + ':item-1']['title'])
        self.assertNotIn('ig-1', parse_manifest(by_id[GOLIVE]['exact_payload']))

    def test_authority_file_names_the_new_formats(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'invariants').mkdir()
            (root / 'invariants' / 'authority.json').write_text(json.dumps(
                {'show_before_post_until': '2026-11-01', 'per_item_review_formats': ['post']}), encoding='utf-8')
            summary, _ = self.run_handoff(root=root)
        self.assertEqual(summary['proposals'], {'go_live': 3})
        self.assertTrue(all('Until' not in p['why'] for p in self.proposals()))

    def test_routine_per_item_review_is_honoured(self):
        self.fix.slots[1]['per_item_review'] = True
        summary, _ = self.run_handoff()
        self.assertEqual(summary['proposals'], {'go_live': 2})

    def test_no_open_plan_proposes_nothing(self):
        self.cc.decisions = []
        summary, code = self.run_handoff()
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['holds'], {'no_open_plan': 3})
        self.assertEqual(self.proposals(), [])
        self.assertEqual([r['status'] for r in self.cc.reports.values() if not r['proposals']], ['held'])

    def test_an_unknown_key_is_rejected_before_any_call(self):
        bad_payloads = [self.fix.payload(words='x'), dict(self.fix.payload(), slots=[dict(self.fix.slots[0], words='x')]),
                        dict(self.fix.payload(), slots=[dict(self.fix.slots[0], buffer_draft_id='nope')]),
                        dict(self.fix.payload(), slots=self.fix.slots * 1 + [self.fix.slots[0]]),
                        dict(self.fix.payload(), slots=self.fix.slots * 21), {'slots': self.fix.slots},
                        dict(self.fix.payload(), run_id='someone-else:2026-W45:week'), []]
        for payload in bad_payloads:
            summary, code = self.run_handoff(payload)
            self.assertEqual(code, 1)
            self.assertTrue(summary['error'].startswith('payload_rejected_'), summary)
        self.assertEqual(self.cc.calls, [])
        self.assertEqual(self.buf.calls, [])

    def test_the_dry_run_sends_nothing(self):
        summary, code = self.run_handoff(deliver=False)
        self.assertEqual(code, 0, summary)
        self.assertEqual(self.report_posts(), [])
        self.assertEqual(self.buf.mutations(), [])
        written = json.loads(self.out.read_text(encoding='utf-8'))
        self.assertEqual(len(written['reports']), 1)
        self.assertEqual(written['reports'][0]['proposals'][0]['proposal_id'], GOLIVE)

    def test_a_week_packet_is_one_check_in_on_the_open_plan_or_a_plan(self):
        packet = {'run_id': 'makeyourmindup:2026-W46:week', 'week': 'W46', 'spec_sha256': 'ab' * 32,
                  'slots': [{'slot': s['slot'], 'channel': s['channel'], 'payload_sha256': s['payload_sha256']}
                            for s in self.fix.slots]}
        summary, code = self.run_handoff(packet, WEEK_PACKET)
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary['proposals'], {'check_in': 1})
        [item] = [p for r in self.cc.reports.values() for p in r['proposals'] if p.get('stage') == 'check_in']
        self.assertEqual((item['parent_proposal_id'], item['wall']), (PLAN, 'strategy'))
        self.assertIn(staged_report_run_id(item['proposal_id'], item['payload_sha256']), self.cc.reports)
        self.assertIn('No stops the plan for good', item['exact_payload'])
        self.cc.reports, self.cc.decisions = {}, []
        summary, code = self.run_handoff(packet, WEEK_PACKET)
        self.assertEqual(summary['proposals'], {'plan': 1})
        for bad in (dict(packet, week='46'), dict(packet, extra=1), dict(packet, slots=[dict(packet['slots'][0], x=1)])):
            self.assertEqual(self.run_handoff(bad, WEEK_PACKET)[1], 1)

    def test_make_piece_is_recorded_and_proposes_nothing(self):
        summary, code = handoff.handoff(MAKE_PIECE, {'piece_id': 'synthetic-piece-1'}, None, None, NOW, True,
                                        out_path=self.out)
        self.assertEqual((code, summary['recorded']), (0, 1))
        self.assertEqual(self.cc.calls, [])
        self.assertEqual(handoff.handoff(MAKE_PIECE, {'piece_id': 'x', 'more': 1}, None, None, NOW, True,
                                         out_path=self.out)[1], 1)

    def test_the_log_carries_counts_and_codes_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'payload.json'
            self.buf.posts[P_X]['text'] = WORDS[P_X] + ' Edited.'
            path.write_text(json.dumps(self.fix.payload()), encoding='utf-8')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = handoff.main(['handoff', '--event', GO_LIVE, '--payload', str(path), '--deliver', '--now', NOW,
                                     '--out', str(self.out)], make_cc=self.cc.client, make_buffer=self.buf.client,
                                    fetch=fetch)
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        summary = json.loads(text)
        self.assertEqual(summary['holds'], {'handoff_digest_mismatch': 1})
        banned = list(WORDS.values()) + [P_THREADS, P_X, P_LINKEDIN, RUN, GOLIVE, PLAN, 'threads-1', 'x-1',
                                         self.buf.base, 'http', 'Synthetic', sha(IMAGE)]
        banned += [s['payload_sha256'] for s in self.fix.slots]
        for needle in banned:
            self.assertNotIn(needle, text)
        self.assertEqual(len(text.strip().splitlines()), 1)

    def test_the_cli_routes_and_refuses_without_a_key(self):
        import growth
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'payload.json'
            path.write_text(json.dumps(self.fix.payload()), encoding='utf-8')
            out = io.StringIO()
            with unittest.mock.patch.dict('os.environ', {'BUFFER_API_KEY': ''}), contextlib.redirect_stdout(out):
                self.assertEqual(growth.main(['run', 'handoff', '--event', GO_LIVE, '--payload', str(path)]), 1)
        self.assertEqual(json.loads(out.getvalue())['error'], 'buffer_key_missing')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / '.github' / 'workflows' / 'handoff.yml').read_text(encoding='utf-8')

    def run_blocks(self):
        blocks, current, indent = [], None, None
        for line in self.text.splitlines():
            stripped = line.lstrip()
            here = len(line) - len(stripped)
            if current is not None:
                if stripped and here <= indent:
                    blocks.append(current)
                    current = None
                else:
                    current.append(line)
                    continue
            if re.match(r'^\s*run:', line):
                indent, current = here, [line]
        if current is not None:
            blocks.append(current)
        return blocks

    def test_the_payload_never_reaches_a_run_line(self):
        blocks = self.run_blocks()
        self.assertGreaterEqual(len(blocks), 2)
        for block in blocks:
            body = '\n'.join(block)
            self.assertNotIn('${{', body)
            self.assertNotIn('client_payload', body)
        payload_lines = [ln.strip() for ln in self.text.splitlines() if 'github.event.client_payload' in ln or 'inputs.payload' in ln]
        self.assertTrue(payload_lines)
        self.assertTrue(all(ln.startswith('HANDOFF_PAYLOAD:') for ln in payload_lines), payload_lines)

    def test_triggers_secrets_and_limits(self):
        self.assertEqual(set(re.findall(r'secrets\.([A-Za-z0-9_]+)', self.text)),
                         {'CONTROL_CENTER_ENGINE_TOKEN', 'BUFFER_API_KEY'})
        self.assertEqual(set(re.findall(r'vars\.([A-Za-z0-9_]+)', self.text)), {'CONTROL_CENTER_URL'})
        for needle in ('repository_dispatch', 'types: [growth-go-live-manifest, growth-week-packet, growth-make-piece]',
                       'workflow_dispatch', 'contents: read', 'group: handoff', 'cancel-in-progress: false',
                       'timeout-minutes: 10', "python-version: '3.12'", 'actions/checkout@v7.0.1',
                       'actions/setup-python@v7.0.0', 'persist-credentials: false',
                       'python growth.py run handoff --event "$HANDOFF_EVENT" --payload "$HANDOFF_FILE" --deliver'):
            self.assertIn(needle, self.text)
        self.assertEqual(re.findall(r'^\s+(\w+): (?:read|write)$', self.text, re.M), ['contents'])
        for banned in ('upload-artifact', 'GITHUB_TOKEN', 'contents: write', 'set -x', 'cat "$HANDOFF_FILE"'):
            self.assertNotIn(banned, self.text)


if __name__ == '__main__':
    unittest.main()
