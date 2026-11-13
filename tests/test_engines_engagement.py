"""The Engagement engine (engine/engines/engagement.py) and its acceptance replay from the 5 Nov review.

"Counts nine outgoing drafts plus one incoming response as nine outgoing items. A cleared editor reduces the
ready count. A replacement qualifies only after the post, contribution, identity and retained text are
checked." Synthetic fixtures only, written through core.append into a temp root and read back by core.start.
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from engine.engines import core, engagement as eng

ROOT = Path(__file__).resolve().parents[1]
# Every step an X reply needs: no account here is prefilled in a native editor since LinkedIn, the only one
# that was, went to growth-mindmake on 13 Nov 2026 (Ruling, Krish, 2026-11-13).
ALL_STEPS = {s: True for s in eng.required_steps('x')}
DRAFT = core.digest('Would the three models still pick different winners with the brand names hidden?')


def item(n, direction='outgoing', state='ready', account='x', links=('batch-one',), **detail):
    d = {'direction': direction, 'parent_post_key': core.digest('https://example.org/post/' + str(n)),
         'account': account, 'identity_checked': True, 'contribution': 'real_question',
         'draft_digest': DRAFT, 'verified_digest': DRAFT, 'editor_verification': dict(ALL_STEPS)}
    if direction == 'incoming':
        d.update(contribution=None, editor_verification={})
    d.update(detail)
    return {'id': 'item-' + str(n), 'engine': 'engagement', 'kind': 'interaction', 'title': 'Synthetic item ' + str(n),
            'state': state, 'source': {'kind': 'review', 'ref': 'docs/reviews/2026-11-05-growth-engine-review.md',
                                       'observed_at': '2026-11-05'},
            'next_owner': 'krish', 'next_action': 'final click', 'revisit_when': 'after Krish reviews',
            'links': list(links), 'updated_at': '2026-11-05', 'detail': d}


def batch(requested=10, **changes):
    value = {'id': 'batch-one', 'engine': 'engagement', 'kind': 'batch', 'title': 'Ten requested comments',
             'state': 'requested', 'source': {'kind': 'user_ruling', 'ref': 'synthetic', 'observed_at': '2026-11-05'},
             'next_owner': 'engagement', 'next_action': 'prepare the batch', 'revisit_when': 'when ten are ready',
             'links': [], 'updated_at': '2026-11-05', 'detail': {'requested': requested, 'requested_by': 'krish'}}
    value.update(changes)
    return value


class AcceptanceReplay(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines', ignore=shutil.ignore_patterns('records'))
        core.append('engagement', batch(), self.root)
        for n in range(1, 10):
            core.append('engagement', item(n), self.root)
        # The incoming reply on Krish's own post that once counted toward ten outgoing comments.
        core.append('engagement', item(10, direction='incoming', state='candidate'), self.root)

    def start(self):
        return core.start('engagement', self.root, now='2026-11-05')['recover']

    def test_nine_outgoing_plus_one_incoming_counts_nine_outgoing(self):
        recovered = self.start()
        b = recovered['batches'][0]
        self.assertEqual((b['outgoing'], b['incoming'], b['ready'], b['short']), (9, 1, 9, 1))
        self.assertEqual(recovered['unanswered_incoming'], ['item-10'])
        self.assertEqual(recovered['ready_for_review']['ready'], 9)
        self.assertEqual(core.check(self.root), [])

    def test_a_cleared_editor_reduces_the_ready_count(self):
        core.append('engagement', item(3, editor_verification=dict(ALL_STEPS, full_text_verified=False),
                                       updated_at='2026-11-06'), self.root)
        core.append('engagement', item(4, verified_digest=core.digest('')), self.root)
        recovered = self.start()
        self.assertEqual(recovered['batches'][0]['ready'], 7)
        self.assertEqual(recovered['batches'][0]['outgoing'], 9)
        self.assertEqual(recovered['stale_ready'], ['item-3', 'item-4'])

    def test_a_replacement_qualifies_only_after_every_check(self):
        records = core.load('engagement', self.root)
        good = item(11)
        self.assertTrue(eng.qualifies_as_replacement(good, records))
        cases = {'the actual post was not opened': item(11, editor_verification=dict(ALL_STEPS,
                                                                                      opened_actual_post=False)),
                 'no contribution from Krish is identified': item(11, state='candidate', contribution=None),
                 'the account identity was not checked': item(11, identity_checked=False),
                 'the retained text was not verified in the editor': item(11, verified_digest=None)}
        for reason, candidate in cases.items():
            self.assertFalse(eng.qualifies_as_replacement(candidate, records), reason)
            self.assertIn(reason, eng.replacement_errors(candidate, records))
        self.assertEqual(eng.replacement_errors(item(10, direction='incoming', state='candidate'), records),
                         ['an incoming item never fills an outgoing batch'])

    def test_exclusions_and_handled_items_cannot_re_enter(self):
        core.append('engagement', item(10, direction='incoming', state='handled', revisit_when=None), self.root)
        excluded = item(12)
        core.append('engagement', {'id': 'batch-one', 'detail': {
            'excluded_keys': [excluded['detail']['parent_post_key']]}}, self.root, private=True)
        records = core.load('engagement', self.root)
        same_post = item(13, parent_post_key=item(10)['detail']['parent_post_key'])
        self.assertEqual(eng.replacement_errors(same_post, records), ['already handled'])
        self.assertEqual(eng.replacement_errors(excluded, records), ['privately excluded'])
        recovered = self.start()
        self.assertEqual(recovered['unanswered_incoming'], [])
        self.assertEqual(recovered['exclusions'], {'excluded': 1, 'handled': 1})
        self.assertEqual(core.load('engagement', self.root, private=False)['batch-one']['detail'],
                         batch()['detail'])

    def test_a_weak_tenth_goes_back_to_the_researcher(self):
        weak = item(14, state='candidate', contribution=None, identity_checked=False)
        self.assertFalse(eng.qualifies_as_replacement(weak, core.load('engagement', self.root)))
        core.append('engagement', eng.return_to_researcher(weak, '2026-11-05'), self.root)
        recovered = self.start()
        self.assertEqual(recovered['returned_to_researcher'], ['item-14'])
        self.assertEqual(recovered['batches'][0]['ready'], 9)
        self.assertEqual(core.check(self.root), [])

    def test_unchecked_identity_or_missing_contribution_is_not_ready(self):
        # Reviewer case: both lines validate, and once both counted as ready beside identities.unchecked.
        core.append('engagement', item(5, state='drafted', identity_checked=False, updated_at='2026-11-06'),
                    self.root)
        core.append('engagement', item(6, state='candidate', contribution=None, updated_at='2026-11-06'),
                    self.root)
        recovered = self.start()
        self.assertEqual(recovered['batches'][0]['ready'], 7)
        self.assertNotIn('item-5', recovered['ready_for_review']['ready_ids'])
        self.assertNotIn('item-6', recovered['ready_for_review']['ready_ids'])
        self.assertEqual(recovered['identities']['unchecked'], ['item-5'])
        self.assertIn('an outgoing ready item needs the account identity checked',
                      core.validate(item(5, identity_checked=False)))
        self.assertTrue(core.validate(item(6, state='awaiting_krish', contribution=None)))

    def test_open_drafts_on_excluded_or_handled_posts_are_blocked_not_ready(self):
        core.append('engagement', {'id': 'batch-one', 'detail': {
            'excluded_keys': [item(7)['detail']['parent_post_key']]}}, self.root, private=True)
        core.append('engagement', item(20, direction='incoming', state='handled', links=(), revisit_when=None),
                    self.root)
        core.append('engagement', item(8, parent_post_key=item(20)['detail']['parent_post_key'],
                                       updated_at='2026-11-06'), self.root)
        recovered = self.start()
        self.assertEqual(recovered['blocked'], ['item-7', 'item-8'])
        self.assertEqual(recovered['batches'][0]['ready'], 7)
        self.assertEqual(recovered['ready_for_review']['ready'], 7)
        self.assertNotIn('item-7', recovered['ready_for_review']['ready_ids'])


class Rules(unittest.TestCase):
    def test_ready_count_reports_incoming_and_outgoing_apart(self):
        items = [item(n) for n in range(1, 9)] + [item(9, verified_digest=None), item(10, editor_verification={})]
        self.assertEqual({k: v for k, v in eng.ready_count(items).items() if k != 'ready_ids'},
                         {'incoming': 0, 'outgoing': 10, 'ready': 8})
        self.assertEqual(eng.ready_count([item(1, direction='incoming', state='candidate')])['ready'], 0)

    def test_no_account_is_prefilled_in_a_native_editor(self):
        steps = {s: True for s in eng.required_steps('x')}
        self.assertNotIn('filled_native_editor', steps)
        self.assertEqual(eng.NATIVE_PREFILL, ())
        self.assertTrue(eng.is_ready(item(1, account='x', editor_verification=steps)))
        prefilled = dict(steps, filled_native_editor=True, switched_away=True, returned=True)
        self.assertTrue(any(e.startswith('no comment is prepared in a native editor here')
                            for e in core.validate(item(1, account='instagram', editor_verification=prefilled))))

    def test_linkedin_is_not_an_account_this_engine_engages_from(self):
        # Ruling (Krish, 2026-11-13): growth-mindmake owns his personal LinkedIn and the replies to everyone who
        # engages with his posts. No interaction, outgoing or incoming, is recorded here on it.
        self.assertNotIn('linkedin', eng.ACCOUNTS)
        for direction, state in (('outgoing', 'ready'), ('incoming', 'candidate')):
            errors = core.validate(item(1, direction=direction, state=state, account='linkedin'))
            self.assertTrue(any("growth-mindmake's since 2026-11-13" in e for e in errors), errors)

    def test_detail_refusals(self):
        self.assertIn('personal encouragement alone is not a reason to comment',
                      core.validate(item(1, contribution='personal_encouragement')))
        self.assertTrue(core.validate(item(1, state='drafted', contribution=None)))
        self.assertTrue(core.validate(item(1, account='myspace')))
        self.assertTrue(core.validate(item(1, direction='sideways')))
        self.assertTrue(core.validate(item(1, parent_post_key='https://example.org/post/1')))
        self.assertTrue(core.validate(item(1, direction='incoming', state='returned_to_researcher',
                                           revisit_when=None)))
        self.assertTrue(core.validate(batch(requested=0)))
        self.assertTrue(core.validate(batch(detail={'requested': 1, 'requested_by': 'acquisition'})))
        self.assertEqual(core.validate(batch(detail={'requested': 1, 'requested_by': 'acquisition'},
                                             opportunity_id='opp-creator')), [])
        # Exact words stay private: a committed line carrying them is refused.
        self.assertTrue(core.privacy_errors(item(1, text='the exact comment')))

    def test_post_urls_and_exact_words_are_refused_in_committed_records(self):
        words = 'https://x.com/synthetic_one/status/1 Great point, would the models...'
        for key in ('post_url', 'recovery_copy', 'comment'):
            self.assertTrue(core.validate(item(30, **{key: words})), key)
            self.assertEqual(core.validate(item(30, **{key: words}), private=True), [], key)
        self.assertIn('detail.url: a URL; commit parent_post_key and keep the URL in .scratch/engines/',
                      core.validate(item(30, url=words)))

    def test_contract_and_job_say_linkedin_is_growth_mindmakes(self):
        contract = core.load_contract('engagement', ROOT)
        job = ' '.join((ROOT / 'jobs' / 'engagement.md').read_text(encoding='utf-8').split())
        self.assertFalse(any('one prefilled LinkedIn box' in a for a in contract['permitted_actions']))
        self.assertTrue(any("Krish's personal LinkedIn" in a and "growth-mindmake's" in a
                            for a in contract['forbidden_actions']))
        self.assertNotIn('open_for_krish', contract, 'the LinkedIn tab conflict closed with the handover')
        self.assertIn("growth-mindmake's since 13 November 2026", job)

    def test_questions_go_to_acquisition_and_content_engine(self):
        q = dict(batch(), id='question-one', kind='question', state='handed_off', next_owner='acquisition',
                 detail={'times_seen': 3, 'hand_to': ['content-engine', 'acquisition']})
        self.assertEqual(core.validate(q), [])
        self.assertTrue(core.validate(dict(q, next_owner='engagement')))
        self.assertTrue(core.validate(dict(q, detail={'times_seen': 1, 'hand_to': ['acquisition', 'content-engine']})))
        self.assertTrue(core.validate(dict(q, detail={'times_seen': 2, 'hand_to': ['acquisition']})))

    def test_a_commissioned_comment_is_one_draft_and_one_decision(self):
        one = dict(item(1, links=()), opportunity_id='opp-creator')
        two = dict(item(2, links=()), opportunity_id='opp-creator')
        records = {r['id']: r for r in (one, two, item(3, links=()))}
        self.assertEqual(eng.decision_conflicts(records), {'opp-creator': ['item-1', 'item-2']})
        records['item-2'] = eng.return_to_researcher(two, '2026-11-05')
        self.assertEqual(eng.decision_conflicts(records), {})


if __name__ == '__main__':
    unittest.main()
