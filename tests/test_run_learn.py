"""The weekly learn (`growth.py run learn`, then `growth.py mix learn --verdicts`) on synthetic fixtures.

Ruling (Krish, 2026-11-12): the engine reads subscribers every week and judges posts by subscribers, not
engagement. Every post, id, link and figure here is invented; nothing reaches Buffer or Control Center.
"""
import contextlib
import datetime as dt
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from engine import mix
from engine.core import instant, read_json, write_json
from engine.run import learn

from test_mix import ideas, inventory_of, mocks_for
from test_run_measure_auto import CHANNEL_IDS, LINK, SERVICES, FakeBuffer, covered_block
from engine.run.release import BUFFER_NAME

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / 'tests' / 'fixtures' / 'ga4'
SUNDAY = '2026-11-22T10:30:00Z'  # 05:30 New York, before next week's plan is made that day
JUDGED, PLAN = '2026-11-09', '2026-11-23'


def config_root(tmp):
    """A copy of this repository (what the planner reads) with a verified ga4.json of synthetic names."""
    root = Path(tmp) / 'repo'
    shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns('.git', '.scratch', '__pycache__', 'lists'))
    (root / 'lists').mkdir()
    write_json(root / 'invariants' / 'ga4.json', read_json(FIX / 'config-verified.json'))
    return root


def posted(n, channel, day, content):
    """One sent post as buffer_reads.sent_posts gives it."""
    return {'post_id': 'post%02d' % n, 'channel': channel, 'sent_at': instant(day + 'T15:00:00Z'),
            'words': 'TEST FIXTURE ONLY. ' + LINK.format(src=channel, content=content), 'metrics': None}


def raw(n, channel, day, content):
    """The same post as Buffer lists it, for the fake client."""
    return {'id': 'post%02d' % n, 'status': 'sent', 'via': 'api', 'sentAt': day + 'T15:00:00.000Z',
            'text': 'TEST FIXTURE ONLY. ' + LINK.format(src=channel, content=content), 'metrics': [],
            'channelId': CHANNEL_IDS[channel], 'channelService': SERVICES[channel],
            'channel': {'id': CHANNEL_IDS[channel], 'name': BUFFER_NAME[channel], 'service': SERVICES[channel],
                        'isDisconnected': False, 'isLocked': False}}


# Three memes that each brought a sign-up, two carousels that brought visits but none, one level-up post that
# brought too few visits to call, one post not made from the mix, and one from the week after (not judged).
WEEK_POSTS = [('x', '2026-11-10', 'meme-a'), ('instagram', '2026-11-11', 'meme-b'), ('x', '2026-11-12', 'meme-c'),
              ('x', '2026-11-10', 'carousel-d'), ('instagram', '2026-11-12', 'carousel-e'),
              ('x', '2026-11-13', 'level-up-f'), ('x', '2026-11-14', None), ('x', '2026-11-17', 'meme-g')]


def block():
    rows = []
    for n, (channel, day, concept) in enumerate(WEEK_POSTS):
        content = 'placement_%02d' % n
        next_day = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
        if concept and concept.startswith('meme'):
            rows += [(next_day, content, 'page_view', 2), (next_day, content, 'synthetic_sign_up', 1)]
        elif concept and concept.startswith('carousel'):
            rows.append((next_day, content, 'page_view', 40))
        else:
            rows.append((next_day, content, 'page_view', 2))
    return covered_block(rows, through='2026-11-21', first='2026-10-25')


def entries():
    return [{'buffer_draft_id': 'post%02d' % n, 'concept_id': concept, 'channel': channel, 'due_at': day + 'T15:00:00Z',
             'payload_sha256': '%064x' % n} for n, (channel, day, concept) in enumerate(WEEK_POSTS) if concept]


def posts():
    return {'posts': [posted(n, c, d, 'placement_%02d' % n) for n, (c, d, _) in enumerate(WEEK_POSTS)]}


class LearnTests(unittest.TestCase):
    def test_the_judged_week_is_the_last_whose_posts_had_their_seven_days(self):
        self.assertEqual(learn.weeks(SUNDAY), (dt.date(2026, 11, 9), dt.date(2026, 11, 23)))
        self.assertEqual(learn.weeks('2026-11-25T15:00:00Z'), (dt.date(2026, 11, 9), dt.date(2026, 11, 30)))

    def test_posts_are_judged_by_subscribers_and_joined_to_their_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = config_root(tmp)
            doc = learn.build(posts(), {'ok': True, 'directive': {'web_analytics': block()}}, entries(), SUNDAY, root)
            self.assertEqual((doc['judged_week_of'], doc['for_week_of'], doc['basis']), (JUDGED, PLAN, 'subscribers'))
            self.assertEqual(doc['counts'], {'posts_in_week': 7, 'from_the_mix': 6, 'not_from_the_mix': 1})
            verdicts = {r['concept_id']: r['verdict'] for r in doc['rows']}
            self.assertEqual(verdicts, {'meme-a': 'works', 'meme-b': 'works', 'meme-c': 'works',
                                        'carousel-d': 'fails', 'carousel-e': 'fails', 'level-up-f': 'insufficient'})
            learned = mix.learn_from_verdicts(doc, root)
            self.assertEqual(learned['lanes']['meme'], {'works': 3, 'neutral': 0, 'fails': 0, 'insufficient': 0})
            self.assertEqual(learned['lanes']['repurposed_carousel']['fails'], 2)
            self.assertEqual(learned['counts']['insufficient_because'], {'too_few_visits': 1})
            # The committed file carries tallies and counts only: no post id, concept id, link or figure.
            text = json.dumps(learned)
            for private in ('post0', 'meme-a', 'placement_', 'carousel-d', 'sessions'):
                self.assertNotIn(private, text)

    def test_a_verdict_changes_next_weeks_plan(self):
        """The wire end to end: subscriber verdicts, mix learn, the committed file, and mix plan reading it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = config_root(tmp)
            doc = learn.build(posts(), {'ok': True, 'directive': {'web_analytics': block()}}, entries(), SUNDAY, root)
            verdicts_path = root / '.scratch' / 'learn' / 'v.json'
            write_json(verdicts_path, doc)
            learned_path = root / mix.LEARN_DIR / ('for-' + PLAN + '.json')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mix.command(['learn', '--verdicts', str(verdicts_path), '--out', str(learned_path)],
                                             root), 0)
            first = mix.plan(inventory_of(), PLAN, ideas(), urgency=4, root=root)
            before = mix.plan(inventory_of(), PLAN, ideas(), mocks_for(first), urgency=4, root=root)
            loaded, _ = mix.learned_for(PLAN, root)
            after = mix.plan(inventory_of(), PLAN, ideas(), mocks_for(first), loaded, urgency=4, root=root)
            self.assertEqual(before['weights']['meme'], 25)
            self.assertEqual(after['weights']['meme'], 30, 'three memes that each brought a subscriber move memes up')
            # Two carousels failed, but two judged posts are fewer than mix.json's three, so the lane keeps its weight.
            self.assertEqual(after['weights']['repurposed_carousel'], 50)
            self.assertEqual(set(after['moved']), {'meme'})
            self.assertGreater(sum(c.get('meme', 0) for c in after['per_channel'].values()),
                               sum(c.get('meme', 0) for c in before['per_channel'].values()))
            # The command line picks the committed file up by itself for that week, and says so.
            write_json(root / 'inv.json', inventory_of())
            write_json(root / 'ideas.json', ideas())
            err, out = io.StringIO(), root / 'plan.json'
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(mix.command(['plan', '--week-of', PLAN, '--inventory', str(root / 'inv.json'),
                                              '--ideas', str(root / 'ideas.json'), '--urgency', '4', '--out', str(out)],
                                             root), 0)
            self.assertIn('learned from lists/mix-learn/for-' + PLAN + '.json', err.getvalue())
            self.assertEqual(read_json(out)['weights']['meme'], 30)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                mix.command(['plan', '--week-of', PLAN, '--inventory', str(root / 'inv.json'), '--ideas',
                             str(root / 'ideas.json'), '--urgency', '4', '--no-learn', '--out', str(root / 'p2.json')],
                            root)
            self.assertEqual(read_json(root / 'p2.json')['weights']['meme'], 25)
            # Another week's plan never reads this week's file.
            self.assertEqual(mix.learned_for('2026-11-30', root), (None, None))

    def test_learning_refuses_anything_but_subscriber_verdicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = config_root(tmp)
            doc = learn.build(posts(), {'ok': True, 'directive': {'web_analytics': block()}}, entries(), SUNDAY, root)
            for change, message in ((lambda d: d.update(basis='engagement'), 'subscriber verdicts only'),
                                    (lambda d: d.update(schema='x'), 'growth-learn-verdicts'),
                                    (lambda d: d.update(for_week_of='2026-11-24'), 'Monday'),
                                    (lambda d: d['rows'][0].update(verdict='great'), 'verdict')):
                bad = json.loads(json.dumps(doc))
                change(bad)
                with self.assertRaisesRegex(ValueError, message):
                    mix.learn_from_verdicts(bad, root)
            self.assertEqual(mix.lane_of('carousel-x', mix.load(root)), 'repurposed_carousel')
            self.assertEqual(mix.lane_of('positive-news-x', mix.load(root)), 'positive_news')
            self.assertIsNone(mix.lane_of('series-cut', mix.load(root)))

    def test_the_command_reads_fakes_and_logs_counts_only(self):
        class FakeCC:
            def directive(self):
                return {'ok': True, 'directive': {'web_analytics': block()}}

        with tempfile.TemporaryDirectory() as tmp:
            root = config_root(tmp)
            buffer = FakeBuffer([raw(n, c, d, 'placement_%02d' % n) for n, (c, d, _) in enumerate(WEEK_POSTS)])
            text = io.StringIO()
            with patch.object(learn, 'read_entries', return_value=(entries(), {})), contextlib.redirect_stdout(text):
                code = learn.main(['learn', '--now', SUNDAY], buffer=(buffer, None), make_client=FakeCC, root=root)
            self.assertEqual(code, 0, text.getvalue())
            self.assertIn('learn: week of 2026-11-09 for the plan of 2026-11-23; 7 posts, 6 from the mix; by subscribers '
                          'works=3 neutral=0 fails=2 insufficient=1', text.getvalue())
            for private in ('post0', 'meme-', 'placement_'):
                self.assertNotIn(private, text.getvalue())
            self.assertTrue((root / '.scratch/learn/verdicts-for-2026-11-23.json').is_file())
            # No Buffer key: nothing is written and the log names the code only.
            text = io.StringIO()
            with patch.object(learn, 'read_entries', return_value=(entries(), {})), contextlib.redirect_stdout(text):
                code = learn.main(['learn', '--now', SUNDAY], buffer=(None, 'Buffer not configured'),
                                  make_client=FakeCC, root=root)
            self.assertEqual((code, text.getvalue().strip()), (1, 'learn: not written; buffer_not_configured'))


if __name__ == '__main__':
    unittest.main()
