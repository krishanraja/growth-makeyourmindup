"""Krish's personal LinkedIn is growth-mindmake's (Ruling, Krish, 2026-11-13). Synthetic fixtures only.

Asked "Which engine should own your personal LinkedIn posts (you still click every post)?", he answered
"growth-mindmake owns it". This engine drafts, queues, taps, schedules and pins nothing there; reading LinkedIn
stays. The other routes are proved beside their own tests (social, engagement, the two engines, the calendar,
the handoff, release and the backlog); this file proves the owner table, the pack check, the week spec and the
Control Center report, and that what stays is only reading.
"""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from engine import owners
from engine.buffer_channels import BUFFER_CHANNEL_ID, HANDED_OFF_CHANNELS, channel_id_errors
from engine.cc_loop import workspace_report
from engine.packs import check_pack, problems
from engine.run.spec import lint as spec_lint
from engine.social import inventory

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-13T15:00:00Z'
GAP = {'week_of': '2026-11-09', 'week_target': 162, 'current': 1, 'as_of': '2026-11-08', 'urgency': 5,
       'reason': 'under two fifths'}
WORDS = 'TEST FIXTURE ONLY. A useful line about who gets paid when the model is free.'


class OwnerTable(unittest.TestCase):
    def test_the_owner_table_and_the_channel_record_agree(self):
        self.assertEqual(owners.HANDED_OFF, {'linkedin': 'growth-mindmake'})
        self.assertEqual(owners.SINCE, {'linkedin': '2026-11-13'})
        record = inventory()['channel']['linkedin']
        self.assertEqual((record['owned_by']['engine'], record['owned_by']['since']), ('growth-mindmake', '2026-11-13'))
        self.assertIn('growth-mindmake owns it', record['owned_by']['ruling'])
        # He still clicks every post: the wall stays human_publish_only with no quota.
        self.assertEqual((record['publication_mode'], record['daily_posts_target']), ('human_publish_only', None))
        for label in ('linkedin', 'LinkedIn', ' linkedin-comment'):
            self.assertEqual(owners.owner(label), 'growth-mindmake', label)
        for label in ('x', 'threads', 'instagram', None, 3):
            self.assertIsNone(owners.owner(label), label)
        refusal = owners.refusal('linkedin')
        self.assertIn("Krish's personal LinkedIn is growth-mindmake's since 2026-11-13", refusal)
        self.assertNotIn('\u2014', refusal)
        self.assertEqual(owners.refusal('x'), '')

    def test_a_record_and_a_table_that_disagree_fail_the_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
            (root / 'docs').mkdir()
            for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
                shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
            inventory(root)
            path = root / 'social' / 'channels' / 'linkedin.json'
            record = json.loads(path.read_text(encoding='utf-8'))
            for change in ({'engine': 'growth-legibility'}, {'since': '2026-11-14'}):
                path.write_text(json.dumps(dict(record, owned_by=dict(record['owned_by'], **change))), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'owned by another engine'):
                    inventory(root)
            path.write_text(json.dumps({k: v for k, v in record.items() if k != 'owned_by'}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'owned by another engine'):
                inventory(root)
            # Another channel cannot claim an owner the table does not name.
            x_path = root / 'social' / 'channels' / 'x.json'
            path.write_text(json.dumps(record), encoding='utf-8')
            x = json.loads(x_path.read_text(encoding='utf-8'))
            x_path.write_text(json.dumps(dict(x, owned_by=record['owned_by'])), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'owned by another engine'):
                inventory(root)

    def test_its_buffer_channel_is_unpinned_and_refused_by_id(self):
        linkedin = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
        self.assertEqual(linkedin, '6adccba0778b240e2fafc06d')
        self.assertNotIn('linkedin', BUFFER_CHANNEL_ID)
        self.assertEqual(len(BUFFER_CHANNEL_ID), 7)
        for channel in ('linkedin', 'x', 'instagram'):
            [error] = channel_id_errors(channel, linkedin)
            self.assertIn("growth-mindmake's", error)
        self.assertIn("growth-mindmake's", channel_id_errors('linkedin', BUFFER_CHANNEL_ID['x'])[0])


class Drafts(unittest.TestCase):
    def test_the_pack_check_refuses_a_linkedin_draft_in_every_public_kind(self):
        for kind in ('daily', 'radar', 'conversion', 'pitches', 'swaps', 'partners'):
            errors = problems({'platform': 'linkedin', 'text': WORDS}, kind)
            self.assertIn(owners.refusal('linkedin'), errors, kind)
        self.assertIn(owners.refusal('linkedin'), problems({'platform': 'linkedin', 'text': WORDS}))
        pack = {'pack_date': '2026-11-13', 'kind': 'daily', 'headline': 'TEST FIXTURE ONLY',
                'items': [{'platform': 'x', 'text': WORDS}, {'platform': 'linkedin', 'text': WORDS}]}
        self.assertEqual([e for e in check_pack(pack) if "growth-mindmake's" in e],
                         ['draft 2: ' + owners.refusal('linkedin')])

    def test_reading_linkedin_stays(self):
        # A report or a numbers row about LinkedIn is a reading, never a draft: it is not refused.
        for kind in ('report', 'numbers'):
            self.assertNotIn(owners.refusal('linkedin'), problems({'platform': 'linkedin', 'text': WORDS}, kind))
        sources = json.loads((ROOT / 'invariants' / 'sources.json').read_text(encoding='utf-8'))
        self.assertEqual(sources['categories']['linkedin'], 'organic', 'subscribers it brings are still counted')

    def test_the_week_spec_refuses_a_linkedin_slot(self):
        spec = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        clean = spec_lint(copy.deepcopy(spec))
        self.assertNotIn('channel_owned_by_another_engine', {e['code'] for e in clean['errors']})
        slot = dict(next(s for s in spec['slots'] if s['channel'] == 'threads'), slot_id='w45-linkedin-1',
                    channel='linkedin', format='text', assets=[], publish_mode='krish_click', due_at=None)
        spec['slots'].append(slot)
        found = [e for e in spec_lint(spec)['errors'] if e['code'] == 'channel_owned_by_another_engine']
        self.assertEqual(len(found), 1)
        self.assertIn("growth-mindmake's", found[0]['message'])


class Reports(unittest.TestCase):
    def envelope(self, kind, platforms):
        items, meta = [], []
        for n, platform in enumerate(platforms):
            items.append({'platform': platform, 'text': WORDS + ' ' + str(n),
                          'target_url': 'https://x.com/synthetic_one/status/18500000000000' + str(n)})
            meta.append({'item_id': kind + '-' + str(n), 'placement': 'post', 'minutes': 1, 'priority': 1,
                         'evidence_ids': [], 'why_now': 'Fixture only.', 'success_check': 'Fixture.'})
        envelope = {'pack': {'kind': kind, 'items': items}, 'metadata': meta, 'evidence': []}
        return envelope, {'items': [{'item_id': m['item_id']} for m in meta], 'deferred': [], 'budget_minutes': 20}

    def test_a_linkedin_draft_never_reaches_his_list(self):
        envelope, queue = self.envelope('daily', ['x', 'linkedin'])
        report = workspace_report('daily', 'makeyourmindup:2026-11-13:daily', NOW, [envelope], queue,
                                  rev='fixture', root=ROOT, gap=GAP)[0]
        self.assertEqual([p['channel'] for p in report['proposals']], ['x'])
        held = [h for h in report['holds'] if h['reason'] == "Not this engine's channel"]
        self.assertEqual(len(held), 1)
        self.assertTrue(held[0]['detail'].startswith('daily-1: ' + owners.refusal('linkedin')))
        self.assertNotIn('LinkedIn', json.dumps(report['proposals']))

    def test_a_report_recommendation_about_linkedin_is_still_a_reading(self):
        envelope, queue = self.envelope('report', ['linkedin'])
        report = workspace_report('report', 'makeyourmindup:2026-11-13:report', NOW, [envelope], queue,
                                  rev='fixture', root=ROOT, gap=GAP)[0]
        self.assertFalse([h for h in report['holds'] if h['reason'] == "Not this engine's channel"])


class Reading(unittest.TestCase):
    """Reading stays and writing goes: the read-only readers still read and judge this engine's LinkedIn posts
    from before the handover, with no 'Buffer channel not pinned' hold, while every write route refuses it."""

    LINKEDIN = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
    NOW = '2026-11-15T12:00:00Z'

    def post(self, n, channel_id, name, service, sent_at, status='sent'):
        return {'id': '{:024x}'.format(0xe00000 + n), 'status': status, 'via': 'api', 'text': WORDS,
                'sentAt': sent_at if status == 'sent' else None, 'dueAt': sent_at, 'channelId': channel_id,
                'channelService': service, 'externalLink': None, 'metrics': [],
                'channel': {'id': channel_id, 'name': name, 'service': service, 'isDisconnected': False,
                            'isLocked': False}}

    def listed(self):
        return [self.post(1, BUFFER_CHANNEL_ID['x'], 'TheRealKrisho', 'twitter', '2026-11-10T14:00:00.000Z'),
                self.post(2, self.LINKEDIN, 'krish-raja', 'linkedin', '2026-11-10T15:00:00.000Z'),  # before
                self.post(3, self.LINKEDIN, 'krish-raja', 'linkedin', '2026-11-14T15:00:00.000Z')]  # after

    def test_a_linkedin_post_from_before_the_handover_is_still_read_and_judged(self):
        from engine.run import buffer_reads, measure_auto
        from engine.run.ga4 import load_config
        from engine.core import instant

        class Fake:
            def __init__(self, posts):
                self.posts = posts

            def list_posts(self, status=None, since=None):
                return {'edges': [{'node': p} for p in self.posts]}

        read = buffer_reads.sent_posts(Fake(self.listed()), '2026-11-01T00:00:00Z', self.NOW)
        self.assertEqual([(p['post_id'][-1], p['channel']) for p in read['posts']], [('1', 'x'), ('2', 'linkedin')],
                         "the post from after the handover is growth-mindmake's, never judged here")
        self.assertEqual(read['held'], [])
        self.assertEqual(read['history'], 1)
        report, _, _ = measure_auto.build(read, None, instant(self.NOW), ROOT, 'synthetic', load_config(ROOT), True)
        self.assertFalse([h for h in report['holds'] if h['reason'] == 'Buffer channel not pinned'])
        lines = ' | '.join(a['line'] for a in report['activity'])
        self.assertIn('Read 2 sent posts from Buffer on 1 of 7 pinned channels', lines)
        self.assertIn('1 of them from before a channel was handed to another engine, judged as history', lines)
        self.assertIn('linkedin: 1 post; by subscribers', lines)

    def test_the_ledger_keeps_linkedin_history_and_leaves_out_the_new_owners_posts(self):
        from engine import ledger
        scheduled = self.post(4, self.LINKEDIN, 'krish-raja', 'linkedin', '2026-11-16T15:00:00.000Z', 'scheduled')
        rows = ledger.normalise_posts(self.listed() + [scheduled])
        self.assertEqual([(r['post_id'][-1], r['channel']) for r in rows], [('1', 'x'), ('2', 'linkedin')])

    def test_writing_to_it_stays_refused(self):
        from engine.buffer_channels import READ_CHANNEL_ID, read_channel
        self.assertEqual(READ_CHANNEL_ID['linkedin'], self.LINKEDIN)
        self.assertEqual(read_channel(self.LINKEDIN, '2026-11-12T23:59:59Z'), 'linkedin')
        self.assertIsNone(read_channel(self.LINKEDIN, '2026-11-13T00:00:00Z'))
        self.assertIsNone(read_channel(self.LINKEDIN, None))
        self.assertEqual(read_channel(BUFFER_CHANNEL_ID['x'], None), 'x')
        self.assertNotIn('linkedin', BUFFER_CHANNEL_ID)
        self.assertIn("growth-mindmake's", channel_id_errors('linkedin', self.LINKEDIN)[0])


class Docs(unittest.TestCase):
    def test_the_ruling_is_recorded_where_the_rules_live(self):
        agents = ' '.join((ROOT / 'AGENTS.md').read_text(encoding='utf-8').split())
        changes = ' '.join((ROOT / 'CHANGES.md').read_text(encoding='utf-8').split())
        authority = ' '.join((ROOT / 'docs' / 'PUBLISHING-AUTHORITY.md').read_text(encoding='utf-8').split())
        question = '"Which engine should own your personal LinkedIn posts (you still click every post)?"'
        for text in (agents, changes, authority):
            self.assertIn(question, text)
            self.assertIn('"growth-mindmake owns it"', text)
        self.assertIn("## Krish's personal LinkedIn is growth-mindmake's (Ruling, Krish, 2026-11-13)", agents)
        self.assertIn("## 13 November 2026: Krish's personal LinkedIn is growth-mindmake's", authority)
        rules = {r['id']: r for r in json.loads((ROOT / 'invariants' / 'rules.json').read_text(encoding='utf-8'))['rules']}
        self.assertEqual(rules['R125']['source_file'], 'CHANGES.md')
        for text in (agents, changes, authority):
            self.assertNotIn('\u2014', text)


if __name__ == '__main__':
    unittest.main()
