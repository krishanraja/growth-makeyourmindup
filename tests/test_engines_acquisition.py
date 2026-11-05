"""The Acquisition engine (engine/engines/acquisition.py) and its replay of the 5 November incidents.

The acceptance replay runs through the normal entry point, `growth.py engine start acquisition`, on a copy of
the committed seeds. Other cases use synthetic records only.
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import growth
from engine.engines import acquisition as acq
from engine.engines import core

ROOT = Path(__file__).resolve().parents[1]
DECLINED = 'acq-creator-collaboration-declined'
BATCH = 'acq-outreach-batch-pending-approval'
SOURCE = {'kind': 'review', 'ref': 'docs/reviews/x.md', 'observed_at': '2026-11-05'}
MYMU = 'https://home.makeyourmindup.ai'


def opportunity(rid, **detail):
    base = {'route': 'newsletter_placement', 'opportunity_key': acq.opportunity_key('newsletter', rid)}
    base.update(detail)
    return {'id': rid, 'engine': 'acquisition', 'kind': 'opportunity', 'title': 'A synthetic route',
            'state': 'qualified', 'source': SOURCE, 'next_owner': 'acquisition', 'next_action': 'prepare the offer',
            'revisit_when': 'after the intake replies', 'opportunity_id': rid, 'links': [],
            'updated_at': '2026-11-05', 'detail': base}


def outreach(rid, opp, recipient='editor@example.org', **detail):
    base = {'recipient_key': acq.recipient_key(recipient), 'channel': 'email', 'structure': list(acq.PARTS),
            'approval': None, 'outcomes': {}}
    base.update(detail)
    return {'id': rid, 'engine': 'acquisition', 'kind': 'outreach', 'title': 'One pitch', 'state': 'awaiting_approval',
            'source': SOURCE, 'next_owner': 'krish', 'next_action': 'Krish decides', 'revisit_when': 'on his decision',
            'opportunity_id': opp, 'links': [], 'updated_at': '2026-11-05', 'detail': base}


PATH = {'find': True, 'follow': True, 'subscribe': True}
STORY = [{'basis': 'story_interest', 'ref': 'thread on shopping agents'}]
TITLE = [{'basis': 'title', 'ref': 'head of engineering'}]
FIELDS = dict(sender='hello@krishraja.com', recipient='editor@example.org', channel='email', subject='A test',
              body='Hello', links=[MYMU])


def cli(argv):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = growth.main(argv)
    return code, json.loads(buffer.getvalue())


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}


class AcceptanceReplay(unittest.TestCase):
    """Closes the declined creator opportunity, suppresses follow-up, preserves the unsent batch and identifies
    the strongest next route without duplicating an existing pitch or brief."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines')

    def start(self):
        code, result = cli(['engine', 'start', 'acquisition', '--now', '2026-11-05', '--root', str(self.root)])
        self.assertEqual(code, 0)
        return result

    def test_committed_seeds_recover_the_incident_state(self):
        before = files(self.root)
        result = self.start()
        self.assertEqual(files(self.root), before)
        recovered = result['recover']
        self.assertEqual([r['id'] for r in recovered['closed_routes']], [DECLINED])
        self.assertEqual(recovered['closed_routes'][0]['state'], 'closed_declined')
        self.assertIn(DECLINED, recovered['suppressed']['opportunity_ids'])
        committed = core.load('acquisition', ROOT, private=False)[BATCH]
        self.assertEqual(recovered['outstanding_approvals'],
                         [{**{k: committed.get(k) for k in ('id', 'title', 'state', 'next_owner', 'next_action',
                                                            'revisit_when', 'opportunity_id')},
                           'detail': committed['detail']}])
        self.assertEqual(committed['state'], 'awaiting_approval')
        self.assertIsNone(recovered['best_opportunity'])
        self.assertIsNone(recovered['next_action']['id'])
        self.assertIn('strongest route into an audience', recovered['next_action']['next_action'])
        self.assertEqual(result['next_action'], recovered['next_action'])
        self.assertTrue(any('fresh decision' in rule for rule in recovered['rules']))
        self.assertEqual(recovered['conflicts'], [])

    def test_replayed_decline_closes_suppresses_and_next_route_is_strongest_without_duplicates(self):
        root = self.root
        acq.add(opportunity('opp-creator', route='creator_collaboration', reader_path=PATH, fit=3,
                            fit_evidence=STORY), root)
        acq.add(outreach('pitch-creator', 'opp-creator', approval=None), root)
        for line in acq.decline(core.load('acquisition', root), 'opp-creator', '2026-11-05', 'receipts/decline'):
            core.append('acquisition', line, root)
        records = core.load('acquisition', root)
        self.assertEqual(records['opp-creator']['state'], 'closed_declined')
        self.assertEqual(records['pitch-creator']['state'], 'closed_declined')
        self.assertNotIn('sent', records['pitch-creator']['detail']['outcomes'])
        with self.assertRaisesRegex(ValueError, 'suppressed'):
            acq.add(outreach('pitch-creator-again', 'opp-creator'), root)
        with self.assertRaisesRegex(ValueError, 'suppressed'):
            acq.add(outreach('pitch-same-person', 'opp-other'), root)
        with self.assertRaisesRegex(ValueError, 'duplicates opportunity opp-creator'):
            acq.add(opportunity('opp-creator-again', route='creator_collaboration',
                                opportunity_key=records['opp-creator']['detail']['opportunity_key']), root)

        acq.add(opportunity('opp-feature', route='editorial_feature', reader_path=PATH, fit=3, fit_evidence=STORY,
                            access=2, access_evidence=['contributor guidelines page']), root)
        acq.add(opportunity('opp-newsletter', reader_path=PATH, fit=2, fit_evidence=STORY), root)
        acq.add(outreach('pitch-feature', 'opp-feature', recipient='desk@example.org'), root)
        with self.assertRaisesRegex(ValueError, 'duplicates pitch pitch-feature'):
            acq.add(outreach('pitch-feature-twice', 'opp-feature', recipient='desk@example.org'), root)

        recovered = self.start()['recover']
        self.assertEqual(recovered['best_opportunity']['id'], 'opp-feature')
        self.assertEqual(recovered['next_action']['id'], 'opp-feature')
        self.assertEqual(recovered['evidence_of_access']['opp-feature'], ['contributor guidelines page'])
        self.assertIn(BATCH, [r['id'] for r in recovered['outstanding_approvals']])
        self.assertEqual({r['id'] for r in recovered['closed_routes']}, {DECLINED, 'opp-creator'})
        self.assertEqual(recovered['conflicts'], [])
        self.assertEqual(core.check(root), [])


class Ranking(unittest.TestCase):
    def test_fit_needs_evidence_and_seniority_alone_ranks_low(self):
        self.assertIn('a fit score needs fit_evidence of demonstrated interest in the story',
                      core.validate(opportunity('o', fit=3)))
        senior = opportunity('senior', reader_path=PATH, fit=3, fit_evidence=TITLE, access=3,
                             access_evidence=['intake'])
        story = opportunity('story', reader_path=PATH, fit=2, fit_evidence=STORY)
        self.assertEqual(core.validate(senior), [])
        self.assertEqual(acq.fit(senior), 1)
        self.assertEqual([r['id'] for r in acq.rank_routes([senior, story])], ['story', 'senior'])

    def test_a_route_with_no_reader_path_never_outranks_one_with_a_path(self):
        strong = opportunity('strong', fit=3, fit_evidence=STORY, access=3, access_evidence=['intake'], speed=3,
                             credit=3, effort=0, reader_path={'find': True, 'follow': True, 'subscribe': False})
        modest = opportunity('modest', reader_path=PATH)
        self.assertEqual([r['id'] for r in acq.rank_routes([strong, modest])], ['modest', 'strong'])

    def test_publisher_size_is_not_delivered_reach(self):
        big = opportunity('big', reader_path=PATH, publisher_audience=1000000, delivered_reach='unknown')
        small = opportunity('small', reader_path=PATH, publisher_audience=5000, delivered_reach=800)
        self.assertEqual([r['id'] for r in acq.rank_routes([big, small])], ['small', 'big'])
        self.assertIn('delivered_reach cannot exceed publisher_audience',
                      core.validate(opportunity('o', publisher_audience=10, delivered_reach=11)))

    def test_closed_routes_do_not_rank_and_a_live_placement_needs_reference_and_path(self):
        closed = opportunity('gone', reader_path=PATH, suppressed=True)
        closed.update(state='closed_declined', revisit_when=None)
        self.assertEqual(core.validate(closed), [])
        self.assertEqual(acq.rank_routes([closed]), [])
        live = opportunity('live', reader_path=PATH)
        live['state'] = 'live'
        self.assertTrue(core.validate(live))
        live['detail']['live_ref'] = 'https://example.org/feature'
        self.assertEqual(core.validate(live), [])


class Outreach(unittest.TestCase):
    def draft(self, **changes):
        value = {'intro': 'I am Krish Raja and I write Make Your Mind Up (' + MYMU + '), about weird AI stories.',
                 'reason': 'Your readers argued about shopping agents last week.',
                 'contribution': 'A test of three shopping models on the same 20 products.',
                 'ask': 'Would a short guest piece on it suit your next issue?', 'links': [MYMU]}
        value.update(changes)
        return value

    def test_a_draft_needs_intro_reason_contribution_one_ask_and_the_link(self):
        self.assertEqual(acq.outreach_errors(self.draft()), [])
        self.assertIn('missing intro', acq.outreach_errors(self.draft(intro='')))
        self.assertIn('the introduction says who Krish is and what MYMU is',
                      acq.outreach_errors(self.draft(intro='Hi there, see ' + MYMU)))
        self.assertIn('the introduction carries a clickable publication link',
                      acq.outreach_errors(self.draft(intro='I am Krish and I write MYMU.')))
        self.assertIn('links must include the MYMU publication link', acq.outreach_errors(self.draft(links=[])))
        self.assertIn('one proportionate ask, not several',
                      acq.outreach_errors(self.draft(ask='Could you feature it? And share it? And link it?')))

    def test_approval_digest_changes_when_any_bound_field_changes(self):
        base = acq.approval_digest(**FIELDS)
        self.assertEqual(base, acq.approval_digest(**FIELDS))
        for name, value in (('sender', 'other'), ('recipient', 'desk@example.org'), ('channel', 'linkedin'),
                            ('subject', 'Another'), ('body', 'Hello!'), ('links', [MYMU, 'https://x.org'])):
            self.assertNotEqual(base, acq.approval_digest(**{**FIELDS, name: value}), name)

    def test_a_redirect_needs_a_fresh_decision(self):
        approved = acq.approve(outreach('p', 'opp'), acq.approval_digest(**FIELDS), '2026-11-05', 'decisions/1')
        self.assertEqual(core.validate(approved), [])
        self.assertTrue(acq.approval_valid(approved, **FIELDS))
        moved = acq.redirect(approved, 'desk@example.org', '2026-11-06')
        self.assertEqual(core.validate(moved), [])
        self.assertEqual((moved['state'], moved['next_owner']), ('needs_fresh_decision', 'krish'))
        self.assertEqual(moved['detail']['redirected_from'], approved['detail']['recipient_key'])
        self.assertFalse(acq.approval_valid(moved, **{**FIELDS, 'recipient': 'desk@example.org'}))
        self.assertFalse(acq.approval_valid(moved, **FIELDS))
        with self.assertRaisesRegex(ValueError, 'needs an approval'):
            acq.record_outcome(moved, 'sent', '2026-11-06', 'receipts/1')

    def test_each_rung_stands_on_its_own_record(self):
        p = acq.approve(outreach('p', 'opp'), acq.approval_digest(**FIELDS), '2026-11-05', 'decisions/1')
        p = acq.record_outcome(p, 'sent', '2026-11-05', 'receipts/sent')
        self.assertEqual(p['state'], 'sent')
        p = acq.record_outcome(p, 'replied', '2026-11-07', 'receipts/reply')
        self.assertEqual(p['state'], 'replied')
        self.assertEqual(core.validate(p), [])
        self.assertNotIn('delivered', p['detail']['outcomes'])
        p = acq.record_outcome(p, 'delivered', '2026-11-07', 'receipts/delivery')
        self.assertEqual(p['state'], 'replied')
        for rung in ('booked', 'live', 'subscriber_attributed'):
            self.assertNotIn(rung, p['detail']['outcomes'])
        claimed = dict(p, state='subscriber_attributed')
        self.assertIn('state subscriber_attributed needs its own recorded outcome; a later rung implies nothing '
                      'earlier', core.validate(claimed))
        unapproved = outreach('q', 'opp', outcomes={'sent': {'at': '2026-11-05', 'evidence_ref': 'r'}})
        unapproved['state'] = 'sent'
        self.assertIn('approved and later rungs need an approval digest', core.validate(unapproved))

    def test_a_comment_as_first_step_goes_to_engagement_on_the_same_opportunity(self):
        line, batch = acq.commission_comment(opportunity('opp-x', reader_path=PATH), '2026-11-06')
        self.assertEqual((line['opportunity_id'], line['next_owner']), ('opp-x', 'engagement'))
        self.assertEqual((batch['engine'], batch['opportunity_id'], batch['detail']['requested_by']),
                         ('engagement', 'opp-x', 'acquisition'))
        self.assertEqual(core.validate(line), [])
        self.assertEqual(core.validate(batch), [])
        self.assertEqual(acq.recover({'opp-x': line}, {}, '2026-11-06')['handed_off'][0]['id'], 'opp-x')

    def test_committed_records_never_hold_the_address(self):
        record = outreach('p', 'opp')
        self.assertNotIn('editor@example.org', json.dumps(record))
        record['detail']['recipient_address'] = 'editor@example.org'
        self.assertTrue(core.privacy_errors(record))


class Regressions(unittest.TestCase):
    """Defects found in review, each replayed through acquisition.add on a copy of the committed seeds."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines')

    def records(self):
        return core.load('acquisition', self.root)

    def approved(self):
        acq.add(opportunity('o1', reader_path=PATH, fit=2, fit_evidence=STORY), self.root)
        acq.add(outreach('p1', 'o1'), self.root)
        return acq.add(acq.approve(self.records()['p1'], acq.approval_digest(**FIELDS), '2026-11-05', 'd/1'),
                       self.root)

    def test_seeds_cite_the_review(self):
        for record in self.records().values():
            self.assertEqual(record['source'], {'kind': 'review', 'observed_at': '2026-11-05',
                                                'ref': 'docs/reviews/2026-11-05-growth-engine-review.md'})

    def test_a_declined_pitch_must_close_its_opportunity_and_suppresses_it_regardless(self):
        sent = acq.add(acq.record_outcome(self.approved(), 'sent', '2026-11-05', 'r/sent'), self.root)
        declined = acq.record_outcome(sent, 'declined', '2026-11-06', 'r/decline')
        with self.assertRaisesRegex(ValueError, 'decline\\(\\)'):
            acq.add(declined, self.root)
        core.append('acquisition', declined, self.root)
        recovered = acq.recover(self.records(), {}, '2026-11-06')
        self.assertIsNone(recovered['best_opportunity'])
        self.assertIn('o1', recovered['suppressed']['opportunity_ids'])
        self.assertTrue(any(c.startswith('o1: ') for c in recovered['conflicts']))
        with self.assertRaisesRegex(ValueError, 'suppressed'):
            acq.add(outreach('p2', 'o1', recipient='desk@example.org'), self.root)

    def test_a_declined_opportunity_cannot_be_reopened(self):
        acq.add(opportunity('o1', reader_path=PATH), self.root)
        for line in acq.decline(self.records(), 'o1', '2026-11-06', 'r/decline'):
            acq.add(line, self.root)
        reopened = dict(self.records()['o1'], state='qualified', revisit_when='soon', updated_at='2026-11-07')
        reopened['detail'] = {k: v for k, v in reopened['detail'].items() if k != 'suppressed'}
        with self.assertRaisesRegex(ValueError, 'stays closed'):
            acq.add(reopened, self.root)
        with self.assertRaisesRegex(ValueError, 'stays closed'):
            acq.add(dict(self.records()[DECLINED], state='candidate', revisit_when='soon'), self.root)

    def test_an_approval_does_not_carry_to_a_changed_recipient(self):
        approved = self.approved()
        moved = dict(approved, detail=dict(approved['detail'], recipient_key=acq.recipient_key('new@example.org')))
        with self.assertRaisesRegex(ValueError, 'fresh decision'):
            acq.add(moved, self.root)
        redirected = acq.add(acq.redirect(approved, 'new@example.org', '2026-11-06'), self.root)
        with self.assertRaisesRegex(ValueError, 'earlier recipient'):
            acq.approve(redirected, acq.approval_digest(**FIELDS), '2026-11-06', 'd/2')
        reused = dict(redirected, state='approved', detail=dict(redirected['detail'], approval=approved['detail'][
            'approval'], outcomes=approved['detail']['outcomes']))
        with self.assertRaisesRegex(ValueError, 'earlier recipient'):
            acq.add(reused, self.root)
        fresh = acq.approve(redirected, acq.approval_digest(**{**FIELDS, 'recipient': 'new@example.org'}),
                            '2026-11-06', 'd/3')
        self.assertEqual(acq.add(fresh, self.root)['state'], 'approved')

    def test_a_redirect_keeps_the_rungs_the_earlier_recipient_reached(self):
        sent = acq.add(acq.record_outcome(self.approved(), 'sent', '2026-11-05', 'r/sent'), self.root)
        moved = acq.add(acq.redirect(sent, 'new@example.org', '2026-11-06'), self.root)
        self.assertEqual(list(moved['detail']['outcomes']), [])
        earlier = moved['detail']['redirects'][0]
        self.assertEqual(earlier['recipient_key'], acq.recipient_key('editor@example.org'))
        self.assertEqual(earlier['outcomes']['sent'], {'at': '2026-11-05', 'evidence_ref': 'r/sent'})
        self.assertEqual(acq.superseded(moved), [acq.approval_digest(**FIELDS)])

    def test_a_commissioned_comment_reaches_a_fresh_engagement_run(self):
        acq.add(opportunity('o1', reader_path=PATH), self.root)
        line, batch = acq.commission_comment(self.records()['o1'], '2026-11-06')
        acq.add(line, self.root)
        core.append('engagement', batch, self.root)
        started = core.start('engagement', self.root, '2026-11-06')
        self.assertIn('o1', [b['opportunity_id'] for b in started['recover']['batches']])
        self.assertEqual(core.check(self.root), [])

    def test_the_batch_at_the_approval_gate_is_not_touched(self):
        batch = self.records()[BATCH]
        for changes in ({'state': 'drafted'}, {'next_owner': 'acquisition'}, {'title': 'Edited batch'}):
            with self.assertRaisesRegex(ValueError, 'approval gate'):
                acq.add(dict(batch, **changes), self.root)
        self.assertEqual(self.records()[BATCH], batch)


if __name__ == '__main__':
    unittest.main()
