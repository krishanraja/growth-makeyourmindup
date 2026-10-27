"""Quote-anchored rules, the failure register, sources and the production boundary.

Synthetic fixtures only. A drifted quote or a vanished test fails here.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from engine.run.invariants import (FAILURE_IDS, RULE_SOURCES, ROOT, check_failures, check_quotes,
                                   check_rule_links, collapse, house_errors, load_boundary,
                                   load_failures, load_rules, load_sources)


def fixture_root(folder, source_text, rule_quote, failures=None, test_source=''):
    root = Path(folder)
    (root / 'invariants').mkdir()
    (root / 'tests').mkdir()
    (root / 'AGENTS.md').write_text(source_text, encoding='utf-8')
    (root / 'tests' / 'test_fixture.py').write_text(test_source, encoding='utf-8')
    rule = {'id': 'R01', 'statement': 'Synthetic rule.', 'source_file': 'AGENTS.md', 'quote': rule_quote,
            'enforced_by': ['doc-only'], 'tests': []}
    (root / 'invariants' / 'rules.json').write_text(json.dumps({'rules': [rule]}), encoding='utf-8')
    if failures is not None:
        (root / 'invariants' / 'failures.json').write_text(json.dumps({'failures': failures}), encoding='utf-8')
    return root


def register(status='tested', tests=('test_present_in_fixture',), **extra):
    entries = [{'id': i, 'title': 'Synthetic entry', 'source': 'fixture', 'guard': 'doc',
                'tests': [], 'status': 'doc-only'} for i in FAILURE_IDS]
    entries[0].update(status=status, tests=list(tests), **extra)
    return entries


class RuleTests(unittest.TestCase):
    def test_rule_quotes_match_sources(self):
        self.assertEqual(check_quotes(load_rules()), [])

    def test_rule_quote_drift_is_detected(self):
        text = 'The engine never acts on a platform\nwithout an approved go-live, read in its own run.\n'
        quote = 'The engine never acts on a platform without an approved go-live'
        with tempfile.TemporaryDirectory() as folder:
            root = fixture_root(folder, text, quote)
            self.assertEqual(check_quotes(load_rules(root), root), [], 'a rewrapped line is not drift')
            (root / 'AGENTS.md').write_text(text.replace('approved', 'signed'), encoding='utf-8')
            self.assertEqual(check_quotes(load_rules(root), root), ['R01: quote drifted from AGENTS.md'])
            (root / 'AGENTS.md').unlink()
            self.assertIn('source file missing', check_quotes(load_rules(root), root)[0])

    def test_short_or_unsourced_quote_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = fixture_root(folder, 'Short text here.', 'Short text here.')
            with self.assertRaisesRegex(ValueError, '40 characters'):
                load_rules(root)

    def test_rules_cover_every_named_source(self):
        rules = load_rules()
        self.assertEqual({r['source_file'] for r in rules}, set(RULE_SOURCES))
        self.assertTrue(all(len(collapse(r['quote'])) >= 40 for r in rules))
        # AGENTS.md: rules 1 to 7, Autonomy, Growth ownership and Outreach.
        agents = ' '.join(r['quote'] for r in rules if r['source_file'] == 'AGENTS.md')
        for anchor in ('Never post, send, comment', 'Never invent a number', 'Content-engine owns production',
                       'No links in LinkedIn comments', 'No mass outreach', 'one you read on a page today',
                       'Never change Control Center', 'never authorises any other go-live',
                       'LinkedIn stays unscheduled drafts', 'It proposes no pitch, swap or partner note'):
            self.assertIn(anchor, agents)
        self.assertTrue(any('personal identity must sound sincere' in r['quote'] for r in rules))

    def test_rule_guards_and_tests_exist(self):
        self.assertEqual(check_rule_links(load_rules()), [])

    def test_superseded_lines_point_to_the_27_october_rulings(self):
        rules = {r['id']: r for r in load_rules()}
        self.assertIn('R63', rules['R18']['statement'])
        self.assertIn('R59', rules['R40']['statement'])
        self.assertEqual(rules['R59']['source_file'], 'CHANGES.md')


class FailureRegisterTests(unittest.TestCase):
    def test_failure_register_tests_exist(self):
        self.assertEqual(check_failures(load_failures()), [])

    def test_failure_register_is_complete(self):
        failures = load_failures()
        self.assertEqual(tuple(f['id'] for f in failures), FAILURE_IDS)
        pending = [f for f in failures if f['status'] == 'pending-build']
        self.assertTrue(pending and all(f['pending_item'] for f in pending))
        self.assertTrue(all(f['tests'] for f in failures if f['status'] == 'tested'))

    def test_missing_test_fails_the_register(self):
        with tempfile.TemporaryDirectory() as folder:
            source = 'def test_present_in_fixture(self):\n    pass\n'
            root = fixture_root(folder, 'x' * 50, 'x' * 50, register(), source)
            self.assertEqual(check_failures(load_failures(root), root), [])
            root = fixture_root(tempfile.mkdtemp(dir=folder), 'x' * 50, 'x' * 50,
                                register(tests=['test_that_was_deleted']), source)
            self.assertEqual(check_failures(load_failures(root), root), ['F01: test not found: test_that_was_deleted'])

    def test_pending_build_is_exempt_only_while_pending_is_allowed(self):
        with tempfile.TemporaryDirectory() as folder:
            entries = register(status='pending-build', tests=['test_still_being_built'], pending_item='Z')
            root = fixture_root(folder, 'x' * 50, 'x' * 50, entries)
            failures = load_failures(root)
            self.assertEqual(check_failures(failures, root), [])
            self.assertEqual(check_failures(failures, root, allow_pending=False),
                             ['F01: test not found: test_still_being_built'])
            del entries[0]['pending_item']
            root = fixture_root(tempfile.mkdtemp(dir=folder), 'x' * 50, 'x' * 50, entries)
            with self.assertRaisesRegex(ValueError, 'pending_item'):
                load_failures(root)

    def test_register_must_be_whole_and_in_order(self):
        with tempfile.TemporaryDirectory() as folder:
            entries = register()
            for broken in (entries[1:], list(reversed(entries)), entries + [copy.deepcopy(entries[0])]):
                root = fixture_root(tempfile.mkdtemp(dir=folder), 'x' * 50, 'x' * 50, broken)
                with self.assertRaisesRegex(ValueError, 'F01 to F54'):
                    load_failures(root)
            entries[0]['status'] = 'fixed'
            root = fixture_root(tempfile.mkdtemp(dir=folder), 'x' * 50, 'x' * 50, entries)
            with self.assertRaisesRegex(ValueError, 'unknown status'):
                load_failures(root)


class SourceAndBoundaryTests(unittest.TestCase):
    def test_sources_are_proposed_not_approved(self):
        data = load_sources()
        self.assertIs(data['approved'], False)
        self.assertIsNone(data['approved_by'])
        self.assertIsNone(data['approved_at'])
        self.assertEqual(data['note'], 'Krish approves at G-A; until then only all-source counts are used')
        cats = data['categories']
        self.assertEqual(cats['direct'], 'unattributed')
        for label in ('substack notes', 'substack recommendations', 'other substacks', 'trackbacks', 'substack app',
                      'reader referral', 'partner', 'external placement', 'linkedin', 'x', 'threads', 'instagram',
                      'facebook', 'tiktok', 'youtube', 'google'):
            self.assertEqual(cats[label], 'organic', label)
        self.assertEqual(cats['email'], 'unattributed')
        self.assertEqual(cats['import'], 'unattributed')
        self.assertEqual(cats['paid ads'], 'paid')

    def test_boundary_follows_the_canva_ruling(self):
        data = load_boundary()
        self.assertEqual(data['source_file'], 'CHANGES.md')
        self.assertIn(collapse(data['quote']), collapse((ROOT / 'CHANGES.md').read_text(encoding='utf-8')))
        owners = data['owners']
        for name in ('article', 'long-video', 'short-video', 'carousel', 'story-artwork', 'cover', 'thumbnail'):
            self.assertEqual(owners[name], 'content-engine', name)
        for name in ('note-image', 'meme', 'receipt-card', 'quote-card', 'scorecard', 'poll-result',
                     'profile-art', 'highlight-art', 'platform-resize'):
            self.assertEqual(owners[name], 'growth-canva', name)
        self.assertEqual(owners['note-text'], 'growth-copy')
        self.assertEqual(owners['caption'], 'growth-copy')

    def test_invariant_text_has_no_em_dash_or_percent(self):
        for name in ('rules.json', 'failures.json', 'sources.json', 'boundary.json'):
            text = (ROOT / 'invariants' / name).read_text(encoding='utf-8')
            self.assertEqual(house_errors(text), [], name)
        self.assertTrue(house_errors('ten per cent'))
        self.assertTrue(house_errors('A \u2014 B'))


if __name__ == '__main__':
    unittest.main()
