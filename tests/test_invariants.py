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
from engine.run.invariants import test_names as defined_tests  # not collected as a test

GA4_TESTS = ('test_ga4_credentials_accept_raw_or_base64_json', 'test_rs256_signature_verifies_with_public_key',
             'test_ga4_transport_only_allows_google_origins_and_never_logs_secrets',
             'test_ga4_unverified_event_name_is_refused', 'test_ga4_report_joins_slots_by_utm_content',
             'test_ga4_reconcile_prefers_the_conservative_reading', 'test_ga4_never_calls_network_without_live')


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
                       'LinkedIn stays unscheduled drafts', 'It proposes no pitch, swap or partner note',
                       'incidental step', 'Purge on a go-live', 'Never force a fact', 'his no stops the plan'):
            self.assertIn(anchor, agents)
        self.assertTrue(any('personal identity must sound sincere' in r['quote'] for r in rules))
        quotes = ' '.join(r['quote'] for r in rules)
        for anchor in ('X and TikTok remain personal identities', 'meaning-changing replacements require approval',
                       'automatic cross-sharing', 'before cleanup', 'production originals',
                       'Do not overwrite the approved revision', 'never duplicate them',
                       'brand kit in Canva with computer use', 'In a signed-in browser you may open pages',
                       'signed out from another browser'):
            self.assertIn(anchor, quotes)

    def test_rule_guards_and_tests_exist(self):
        self.assertEqual(check_rule_links(load_rules()), [])

    def test_superseded_lines_point_to_the_27_october_rulings(self):
        rules = {r['id']: r for r in load_rules()}
        self.assertIn('R63', rules['R18']['statement'])
        self.assertIn('R59', rules['R40']['statement'])
        self.assertEqual(rules['R59']['source_file'], 'CHANGES.md')
        self.assertIn('R78', rules['R27']['statement'])
        self.assertEqual(rules['R78']['source_file'], 'CHANGES.md')

    def test_ga4_rule_quotes_the_27_october_ruling(self):
        rule = {r['id']: r for r in load_rules()}['R83']
        self.assertEqual(rule['source_file'], 'CHANGES.md')
        for anchor in ('Make sure this is a part of your Measurement Specialist.', 'G-VC5V9LDE17',
                       'joined on `utm_content`; Substack Growth sources remain the North Star source',
                       'read-only service account (Viewer on that one property)', 'kept as the fallback'):
            self.assertIn(anchor, collapse(rule['quote']))
        names = defined_tests()
        waiting = [t for t in GA4_TESTS if t not in names]
        self.assertEqual(set(rule['tests']) | set(rule.get('pending_tests', [])), set(GA4_TESTS))
        if waiting:
            self.assertEqual(rule['pending_item'], 'measure')

    def test_27_october_evening_rulings_are_quoted_and_guarded(self):
        rules = {r['id']: r for r in load_rules()}
        anchors = {'R92': ('Derivatives of approved pieces.', 'show me before you post',
                           "It wasn't plain English and human and humble enough."),
                   'R93': ('less fragile way of doing this than a session engine token',
                           'Same for the cost baseline.'),
                   'R94': ('set yourself daily autonomous tasks', 'like my personal LinkedIn posts')}
        for rule_id, phrases in anchors.items():
            self.assertEqual(rules[rule_id]['source_file'], 'CHANGES.md')
            for phrase in phrases:
                self.assertIn(phrase, collapse(rules[rule_id]['quote']), rule_id)
            self.assertTrue(rules[rule_id]['tests'], rule_id)
        self.assertIn('engine/run/invariants.py:check_lanes', rules['R93']['enforced_by'])
        failures = {f['id']: f for f in load_failures()}
        self.assertEqual(FAILURE_IDS[65:71], ('F66', 'F67', 'F68', 'F69', 'F70', 'F71'))
        for fid, guard in (('F66', 'may_post_alone'), ('F67', 'check_lanes'), ('F68', 'check_lanes'),
                           ('F69', 'calendar.py:lint'), ('F70', 'plain.py:lint_carousel'),
                           ('F71', 'canva.py:lint_design')):
            self.assertEqual(failures[fid]['status'], 'tested', fid)
            self.assertIn(guard, failures[fid]['guard'], fid)
        for path in (ROOT / 'invariants' / 'authority.json', ROOT / 'lanes.json', ROOT / 'calendar' / 'v1.json'):
            self.assertEqual(house_errors(path.read_text(encoding='utf-8')), [], path.name)

    def test_notes_identity_and_asset_storage_rules_are_quoted(self):
        rules = {r['id']: r for r in load_rules()}
        notes = rules['R81']
        self.assertEqual(notes['source_file'], 'docs/PUBLISHING-AUTHORITY.md')
        for anchor in ("Substack Notes post from a person's profile, not the publication.",
                       'whose handle is mindmakerlive', 'at up to two a day as signed', 'is superseded by this paragraph'):
            self.assertIn(anchor, collapse(notes['quote']))
        self.assertIn('test_substack_notes_is_personal_cadence', notes['tests'])
        self.assertIn('profile change held for him', rules['R82']['quote'])
        self.assertIn('R81', rules['R59']['statement'])
        storage = ' '.join(collapse(r['quote']) for r in rules.values() if r['source_file'] == 'docs/ASSET-STORAGE.md')
        for anchor in ('Preserve session learning and assets in structured places every session.',
                       'Store a manifest with SHA-256', 'without an explicit historical/rejected label',
                       'independently read back names, parents and sizes', 'a folder named Private as an access boundary'):
            self.assertIn(anchor, storage)


class FailureRegisterTests(unittest.TestCase):
    def test_failure_register_tests_exist(self):
        self.assertEqual(check_failures(load_failures()), [])

    def test_failure_register_is_complete(self):
        failures = load_failures()
        self.assertEqual(tuple(f['id'] for f in failures), FAILURE_IDS)
        pending = [f for f in failures if f['status'] == 'pending-build']
        # 27 Oct: entries flip to tested once their tests exist, so none need stay pending.
        self.assertTrue(all(f.get('pending_item') for f in pending))
        self.assertTrue(all(f['tests'] for f in failures if f['status'] == 'tested'))

    def test_pending_build_stays_only_while_a_test_is_missing(self):
        # Once every named test exists, the entry is flipped to tested and its pending_item dropped.
        names = defined_tests()
        offenders = []
        for kind, entries in (('failure', load_failures()), ('rule', load_rules())):
            for entry in entries:
                pending = entry.get('pending_tests', [])
                if kind == 'failure' and entry['status'] == 'pending-build':
                    pending = pending + entry['tests']
                if pending and all(t in names for t in pending):
                    offenders.append(entry['id'] + ': every pending test exists; flip it and drop pending_item')
                elif not pending and 'pending_item' in entry:
                    offenders.append(entry['id'] + ': nothing is pending; drop pending_item')
        self.assertEqual(offenders, [])

    def test_register_records_the_27_october_learnings(self):
        failures = {f['id']: f for f in load_failures()}
        self.assertEqual(FAILURE_IDS[53:56], ('F54', 'F55', 'F56'))
        buffer, notes = failures['F55'], failures['F56']
        self.assertEqual((buffer['status'], buffer['tests']),
                         ('tested', ['test_release_is_pinned_to_this_engines_buffer_channels']))
        self.assertIn('engine/run/release.py:resolve_channel', buffer['guard'])
        self.assertIn('other ventures', buffer['title'])
        self.assertEqual((notes['status'], notes['tests']), ('tested', ['test_substack_notes_is_personal_cadence']))
        self.assertIn('substack-notes-identity', notes['source'])
        self.assertIn('mindmakerlive', notes['title'])
        owner = {t: f for f in failures.values() for t in f['tests']}
        names = defined_tests()
        expected = [(t, 'measure') for t in GA4_TESTS] + [
            ('test_linkedin_audit_is_krish_only_even_after_approval', 'audit'),
            ('test_facebook_and_threads_follow_the_audit_authority', 'audit'),
            ('test_www_hosts_match_their_account', 'audit'),
            ('test_threads_text_limit_is_500', 'social')]
        for name, item in expected:
            self.assertIn(name, owner)
            if name not in names:  # Still being built by its work item.
                self.assertEqual((owner[name]['status'], owner[name]['pending_item']), ('pending-build', item), name)

    def test_register_records_the_v1_build(self):
        failures = {f['id']: f for f in load_failures()}
        new = FAILURE_IDS[71:92]
        self.assertEqual((new[0], new[-1], FAILURE_IDS[92]), ('F72', 'F92', 'F93'))
        self.assertTrue(all(failures[fid]['status'] == 'tested' for fid in new))
        for fid, guard, test in (
                ('F72', '_rebuilt_digest', 'test_one_changed_asset_byte_holds'),
                ('F75', 'BufferAuthError', 'test_a_refused_key_fails_loudly'),
                ('F78', '_cc_client', 'test_the_cli_routes_and_refuses_without_a_key'),
                ('F85', 'handoff.py:rebuild', 'test_a_mismatched_digest_holds_that_slot'),
                ('F91', 'spec.py:lint', 'test_story_frames_do_not_count_against_the_feed_cap'),
                # Retargeted on 29 Oct 2026: there are no Claude routines; the walls live in docs/TASTE.md.
                ('F92', 'docs/TASTE.md', 'test_taste_file_reads_both_tools_and_never_blocks')):
            self.assertIn(guard, failures[fid]['guard'], fid)
            self.assertIn(test, failures[fid]['tests'], fid)
        rules = {r['id']: r for r in load_rules()}
        for rule_id, phrase in (('R95', 'queue and post autonomously'), ('R96', 'LinkedIn stays his own final click'),
                                ('R97', 'show me before you post')):
            self.assertIn(phrase, rules[rule_id]['quote'], rule_id)

    def test_register_records_the_posting_path_review(self):
        # The adversarial review of PR #19: nothing is posted unless Krish approved exactly
        # that content, on this engine's own account.
        failures = {f['id']: f for f in load_failures()}
        new = FAILURE_IDS[92:99]
        self.assertEqual((new[0], new[-1], FAILURE_IDS[99]), ('F93', 'F99', 'G1'))
        self.assertTrue(all(failures[fid]['status'] == 'tested' for fid in new))
        for fid, guard, test in (
                ('F93', 'buffer_api.py:signed_meta', 'test_a_metadata_change_after_approval_holds'),
                ('F94', 'release.py:account_hold', 'test_a_draft_on_another_account_holds'),
                ('F95', 'SCHEDULE_WINDOW', 'test_a_slot_more_than_ninety_minutes_out_is_never_read_or_edited'),
                ('F96', 'autorelease.py:check_revoked', 'test_a_no_after_scheduling_is_loud_and_never_unscheduled'),
                ('F97', 'GITHUB_EVENT_PATH', 'test_no_step_env_carries_the_payload'),
                ('F98', 'autorelease.py:signed_golives', 'test_old_go_lives_never_starve_a_new_one'),
                ('F99', 'autorelease.py:due_instant', 'test_an_impossible_due_date_holds_that_slot_only')):
            self.assertIn(guard, failures[fid]['guard'], fid)
            self.assertIn(test, failures[fid]['tests'], fid)

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

    def test_tested_entry_guard_must_exist_nested_paths_too(self):
        source = 'def test_present_in_fixture(self):\n    pass\n'
        with tempfile.TemporaryDirectory() as folder:
            entries = register(guard='engine/run/release.py:release_gate (fixture)')
            root = fixture_root(folder, 'x' * 50, 'x' * 50, entries, source)
            self.assertEqual(check_failures(load_failures(root), root),
                             ['F01: guard not found: engine/run/release.py:release_gate'])
            (root / 'engine' / 'run').mkdir(parents=True)
            (root / 'engine' / 'run' / 'release.py').write_text('def release_gate(pack):\n    return pack\n',
                                                                 encoding='utf-8')
            self.assertEqual(check_failures(load_failures(root), root), [])

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

    def test_bad_source_labels_and_owners_are_refused(self):
        sources = {'approved': False, 'approved_by': None, 'approved_at': None, 'note': 'Synthetic.',
                   'categories': {'direct': 'unattributed'}}
        boundary = {'source_file': 'CHANGES.md', 'quote': 'Synthetic quote.', 'owners': {'meme': 'growth-canva'}}
        broken = [('sources', dict(sources, categories={'Direct': 'unattributed'}), 'lower-case'),
                  ('sources', dict(sources, categories={'direct': 'owned'}), 'lower-case'),
                  ('sources', dict(sources, approved_by='Someone'), 'names no approver'),
                  ('sources', dict(sources, approved_at='2026-10-27'), 'names no approver'),
                  ('boundary', dict(boundary, owners={'meme': 'growth-studio'}), 'growth-canva')]
        with tempfile.TemporaryDirectory() as folder:
            for name, data, message in broken:
                root = Path(tempfile.mkdtemp(dir=folder))
                (root / 'invariants').mkdir()
                for kind, good in (('sources', sources), ('boundary', boundary)):
                    (root / 'invariants' / (kind + '.json')).write_text(json.dumps(good), encoding='utf-8')
                self.assertEqual(load_sources(root)['categories'], {'direct': 'unattributed'})
                self.assertEqual(load_boundary(root)['owners'], {'meme': 'growth-canva'})
                (root / 'invariants' / (name + '.json')).write_text(json.dumps(data), encoding='utf-8')
                with self.assertRaisesRegex(ValueError, message):
                    (load_sources if name == 'sources' else load_boundary)(root)

    def test_invariant_text_has_no_em_dash_or_percent(self):
        for name in ('rules.json', 'failures.json', 'sources.json', 'boundary.json'):
            text = (ROOT / 'invariants' / name).read_text(encoding='utf-8')
            self.assertEqual(house_errors(text), [], name)
        self.assertTrue(house_errors('ten per cent'))
        self.assertTrue(house_errors('A \u2014 B'))


if __name__ == '__main__':
    unittest.main()
