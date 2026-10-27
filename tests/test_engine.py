"""Regression checks exercise failure boundaries, not external accounts."""
import contextlib
import copy
import datetime as dt
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qsl, urlsplit
import urllib.error

import growth
from engine.catalog import discover, parse_feed, strip_html
from engine.core import (acquisition, calendar_date, canonical, identity, instant,
                         locked, ny_time, read_json, today, tracked, write_json)
from engine.dry_run import run
from engine.operations import (aggregate, daily_queue, experiment_decision,
                               relationship, validate_observation, yield_per_thousand)
from engine.packs import answer_piece_errors, check_pack, problems, seal, validate_envelope, wire_pack, x_weight

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-17T18:00:00Z'
URL = 'https://home.makeyourmindup.ai/p/test-fixture'


def draft():
    text = 'TEST FIXTURE ONLY. I asked one useful question.'
    eid = identity('evidence', URL, text)
    return ({'pack_date': '2026-10-17', 'kind': 'daily', 'headline': 'Test fixture',
             'items': [{'platform': 'x', 'text': text}]},
            [{'evidence_id': eid, 'kind': 'published_piece', 'url': URL, 'excerpt': text,
              'snapshot': text, 'observed_at': NOW}],
            [{'asset_id': identity('piece', URL), 'placement': 'thread', 'variant': 'a', 'evidence_ids': [eid],
              'priority': 1, 'minutes': 3, 'why_now': 'Fixture only.', 'success_check': 'Source comparison completed.'}])


def observation(**updates):
    value = {'platform': 'x', 'metric': 'reach', 'unit': 'accounts', 'window_kind': 'interval',
             'source': 'https://x.com/i/account_analytics', 'scope': 'post:fixture', 'asset_id': 'fixture',
             'start': '2026-10-15T04:00:00Z', 'end': '2026-10-16T04:00:00Z',
             'captured_at': NOW, 'timezone': 'America/New_York', 'availability': 'available', 'value': 100}
    return {**value, **updates}


class ClockTests(unittest.TestCase):
    def test_new_york_date_is_not_utc_date(self):
        self.assertEqual(today('2026-10-17T02:00:00Z'), '2026-10-16')

    def test_spring_change(self):
        self.assertEqual(ny_time('2026-03-08T06:59:59Z').hour, 1)
        self.assertEqual(ny_time('2026-03-08T07:00:00Z').hour, 3)

    def test_autumn_repeated_hour(self):
        first, second = ny_time('2026-11-01T05:30:00Z'), ny_time('2026-11-01T06:30:00Z')
        self.assertEqual(first.hour, second.hour)
        self.assertNotEqual(first.utcoffset(), second.utcoffset())

    def test_windows_without_iana_database(self):
        from zoneinfo import ZoneInfoNotFoundError
        with patch('zoneinfo.ZoneInfo', side_effect=ZoneInfoNotFoundError()):
            for stamp, hour, offset in [('2026-03-08T06:59:59Z', 1, -5), ('2026-03-08T07:00:00Z', 3, -4),
                                        ('2026-11-01T05:59:59Z', 1, -4), ('2026-11-01T06:00:00Z', 1, -5)]:
                with self.subTest(stamp=stamp):
                    result = ny_time(stamp)
                    self.assertEqual((result.hour, result.utcoffset().total_seconds() / 3600), (hour, offset))

    def test_reject_naive_timestamp(self):
        with self.assertRaises(ValueError):
            instant('2026-10-17T18:00:00')

    def test_real_calendar_dates(self):
        for value in ('2026-02-30', '2026-1-01', None):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                calendar_date(value)


class TrackingTests(unittest.TestCase):
    def test_replace_all_tags_preserve_functional_parameters_and_fragment(self):
        result = tracked(URL + '?utm_source=old&utm_medium=old&utm_content=old&ref=a%26b&empty=#proof', 'x', 'daily', '2026-10-17')
        self.assertEqual(dict(parse_qsl(urlsplit(result).query, keep_blank_values=True)),
                         {'ref': 'a&b', 'empty': '', 'utm_source': 'x', 'utm_medium': 'organic', 'utm_campaign': 'growth', 'utm_content': 'daily-20261017'})
        self.assertNotIn('&&', result)
        self.assertEqual(urlsplit(result).fragment, 'proof')

    def test_url_encoding(self):
        result = tracked(URL + '?q=AI+tools', 'linkedin', 'daily', '2026-10-17')
        self.assertEqual(dict(parse_qsl(urlsplit(result).query))['q'], 'AI tools')

    def test_stable_and_distinct_placement_ids(self):
        args = (URL, 'x', 'daily', '2026-10-17', 'story1', 'pin')
        first = tracked(*args)
        self.assertEqual(first, tracked(*args))
        self.assertNotEqual(first, tracked(*args, variant='b'))
        self.assertNotEqual(first, tracked(URL, 'x', 'daily', '2026-10-17', 'story1', 'reply'))

    def test_placement_requires_asset(self):
        with self.assertRaises(ValueError):
            tracked(URL, 'x', 'daily', asset='a')

    def test_invalid_urls_and_dimensions(self):
        for url in ('javascript:alert(1)', 'https://user:secret@example.com', 'https://example.com/has space'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                tracked(url, 'x', 'daily')
        # Krish, 27 Oct 2026, superseding the 14 Oct "no Notes" ruling: Notes
        # links are tracked; an unknown platform is still refused.
        self.assertIn('utm_source=notes', tracked(URL, 'notes', 'daily', '2026-10-27'))
        with self.assertRaises(ValueError):
            tracked(URL, 'myspace', 'daily')

    def test_canonical_identity_ignores_tags_not_referral_code(self):
        self.assertEqual(canonical(URL + '?utm_source=x#x'), URL)
        self.assertNotEqual(canonical(URL + '?ref=reader'), URL)

    def test_internal_placement_preserves_external_acquisition(self):
        origin = acquisition(URL + '?utm_source=linkedin')['original']
        result = acquisition(URL + '?utm_source=internal', origin, internal=True)
        self.assertEqual(result['original']['utm_source'], 'linkedin')
        self.assertEqual(result['placement']['utm_source'], 'internal')

    def test_direct_stays_unknown(self):
        self.assertIsNone(acquisition(URL)['original'])


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.data = (ROOT / 'tests/fixtures/feed.xml').read_bytes()
        self.rows = parse_feed(self.data, 21, NOW)

    def test_parse_published_bodies_and_empty_video(self):
        self.assertEqual(len(self.rows), 2)
        self.assertEqual(self.rows[0]['evidence_status'], 'body_missing')
        self.assertIn('TEST FIXTURE ONLY', self.rows[1]['text'])

    def test_explicit_pair_only(self):
        result = discover(self.rows, now=NOW)
        self.assertEqual(len(result['verified_pairs']), 1)
        self.rows[1]['links'] = []
        self.assertEqual(discover(self.rows, now=NOW)['verified_pairs'], [])

    def test_ambiguous_pair_not_merged(self):
        extra = copy.deepcopy(self.rows[0])
        extra.update(piece_id='other-video', url=URL + '-other')
        self.rows[1]['links'].append(extra['url'])
        self.assertEqual(discover(self.rows + [extra], now=NOW)['verified_pairs'], [])

    def test_late_publication_recovers_and_replay_has_no_new_tasks(self):
        first = discover(self.rows, now=NOW)
        self.assertTrue(any(r['late'] for r in first['changes']))
        second = discover(self.rows, first, NOW)
        self.assertEqual(second['changes'], [])
        self.assertEqual(second['pieces'][self.rows[0]['piece_id']]['first_seen_at'], NOW.replace('Z', '+00:00'))
        self.assertEqual(len(second['pending']), 1)

    def test_new_body_revision_recovered(self):
        first = discover(self.rows, now=NOW)
        updated = parse_feed(self.data.replace(b'<content:encoded></content:encoded>', b'<content:encoded>Now readable.</content:encoded>'), 21, NOW)
        second = discover(updated, first, NOW)
        self.assertEqual(second['changes'][0]['reason'], 'revised')
        self.assertEqual(second['pending'], [])

    def test_unavailable_future_and_old_entries_not_used(self):
        self.assertEqual(parse_feed(self.data, 1, '2026-01-01T00:00:00Z'), [])
        self.assertEqual(parse_feed(self.data, 1, '2026-11-01T00:00:00Z'), [])

    def test_date_is_new_york(self):
        changed = self.data.replace(b'Fri, 16 Oct 2026 17:00:00 GMT', b'Sat, 17 Oct 2026 02:00:00 GMT')
        self.assertEqual(parse_feed(changed, 21, NOW)[1]['date'], '2026-10-16')

    def test_html_drops_script_and_keeps_paragraphs(self):
        self.assertEqual(strip_html('<p>One &amp; two</p><script>bad()</script><p>Three<br>four</p>'), 'One & two\n\nThree\nfour')

    def test_schema_migration_fails_closed(self):
        with self.assertRaises(ValueError):
            discover(self.rows, {'schema_version': 1}, NOW)


class PackTests(unittest.TestCase):
    def test_good_pack_and_envelope(self):
        pack, evidence, metadata = draft()
        self.assertEqual(check_pack(pack), [])
        env = seal(pack, evidence, metadata, NOW)
        self.assertEqual(validate_envelope(env, NOW), env)

    def test_bad_structure_not_traceback(self):
        for value in (None, [], {'items': 'text'}, {'headline': 3, 'items': [None]}):
            with self.subTest(value=value):
                self.assertTrue(check_pack(value))

    def test_house_rules(self):
        for text in ('A — B', '10%', 'ten per cent', 'Let that sink in.', "It's not X, it's Y."):
            with self.subTest(text=text):
                self.assertTrue(problems({'platform': 'x', 'text': text}))

    def test_stock_phrase_matching_does_not_hit_unrelated_word(self):
        self.assertEqual(problems({'platform': 'x', 'text': 'I used a spade to delve.'})[0], 'uses stock phrase "delve"')
        self.assertEqual(problems({'platform': 'x', 'text': 'The delivery arrived.'}), [])

    def test_percent_encoding_does_not_look_like_prose_percentage(self):
        link = tracked(URL + '?ref=a%20b', 'x', 'daily', '2026-10-17')
        self.assertEqual(problems({'platform': 'x', 'text': 'Read ' + link}), [])

    def test_complete_tracking_required(self):
        for suffix in ('', '?utm_source=x', '?utm_source=x&utm_source=x&utm_medium=organic&utm_campaign=growth&utm_content=pin'):
            with self.subTest(suffix=suffix):
                self.assertTrue(problems({'platform': 'x', 'text': 'Read ' + URL + suffix}))

    def test_settings_exemption_is_path_bound(self):
        self.assertEqual(problems({'platform': 'substack', 'text': 'Open https://home.makeyourmindup.ai/publish/settings'}), [])
        self.assertTrue(problems({'platform': 'x', 'text': 'Read ' + URL + '?settings=1'}))

    def test_radar_linkedin_rule_cannot_be_bypassed_by_missing_hint(self):
        pack, _, _ = draft()
        pack.update(kind='radar', items=[{'platform': 'linkedin', 'text': 'Read https://example.com'}])
        self.assertTrue(any('no links' in e for e in check_pack(pack)))

    def test_x_urls_and_non_latin_weight(self):
        self.assertEqual(x_weight('a' * 256 + ' ' + 'https://example.com/' + 'long' * 100), 280)
        self.assertEqual(x_weight('界' * 140), 280)
        self.assertEqual(x_weight('e\u0301'), x_weight('é'))
        self.assertTrue(problems({'platform': 'x', 'text': '界' * 141}))
        self.assertEqual(problems({'platform': 'x', 'text': 'a' * 200 + '\n\n' + 'b' * 200}), [])

    def test_real_date_and_acting_keys(self):
        pack, _, _ = draft()
        for change in ({'pack_date': '2026-02-30'}, {'send': False}, {'items': [{'platform': 'x', 'text': 'hello', 'publish_at': None}]}):
            with self.subTest(change=change):
                self.assertTrue(check_pack({**pack, **change}))

    def test_utf16_api_limits(self):
        pack, _, _ = draft()
        pack['items'] = [{'platform': 'other', 'text': '😀' * 2001}]
        self.assertTrue(check_pack(pack))

    def test_missing_evidence_and_fake_excerpt_rejected(self):
        pack, evidence, metadata = draft()
        with self.assertRaises(ValueError):
            seal(pack, [], metadata, NOW)
        evidence[0]['snapshot'] = 'Different text'
        with self.assertRaises(ValueError):
            seal(pack, evidence, metadata, NOW)

    def test_quotes_must_exist_in_cited_excerpt(self):
        pack, evidence, metadata = draft()
        metadata[0]['quotes'] = ['I tested every model.']
        with self.assertRaises(ValueError):
            seal(pack, evidence, metadata, NOW)

    def test_radar_expiry_and_thread_required(self):
        pack, evidence, metadata = draft()
        pack['kind'] = 'radar'
        with self.assertRaises(ValueError):
            seal(pack, evidence, metadata, NOW)
        evidence[0]['kind'] = 'source_thread'
        evidence[0]['created_at'] = '2026-10-17T17:00:00Z'
        metadata[0]['expires_at'] = '2026-10-17T20:00:00Z'
        self.assertTrue(seal(pack, evidence, metadata, NOW))

    def test_radar_cannot_extend_old_thread_lifetime(self):
        pack, evidence, metadata = draft()
        pack['kind'] = 'radar'
        evidence[0].update(kind='source_thread', created_at='2026-10-16T12:00:00Z')
        metadata[0]['expires_at'] = '2026-10-17T20:00:00Z'
        with self.assertRaisesRegex(ValueError, '12 hours'):
            seal(pack, evidence, metadata, NOW)

    def test_answer_piece_fixture_prepares_and_checks(self):
        source = read_json(ROOT / 'tests/fixtures/answer-input.json')
        env = seal(source['pack'], source['evidence'], source['metadata'], NOW)
        self.assertEqual(validate_envelope(env, NOW), env)
        self.assertEqual(answer_piece_errors(source['pack']['items'][0]['text']), [])

    def test_answer_piece_shape_is_enforced(self):
        source = read_json(ROOT / 'tests/fixtures/answer-input.json')
        text = source['pack']['items'][0]['text']
        question, answer, rest = text.split('\n\n', 2)
        link = rest.rsplit(' ', 1)[1]
        for bad, reason in ((answer + '\n\n' + question + '\n\n' + rest, 'question'),
                            (question + '\n\n' + ' '.join(['word'] * 61) + '\n\n' + rest, '60 words'),
                            (question + '\n\n' + 'Did I answer?' + '\n\n' + rest, 'not ask'),
                            (question + '\n\n' + answer + '\n\nNo link here.', 'links to the published piece')):
            with self.subTest(reason=reason):
                self.assertTrue(any(reason in e for e in answer_piece_errors(bad)))
                pack = copy.deepcopy(source['pack'])
                pack['items'][0]['text'] = bad
                with self.assertRaises(ValueError):
                    seal(pack, source['evidence'], source['metadata'], NOW)
        self.assertIn('?utm_source=substack', link)

    def test_answer_piece_needs_the_real_question_on_record(self):
        source = read_json(ROOT / 'tests/fixtures/answer-input.json')
        meta = copy.deepcopy(source['metadata'])
        meta[0]['evidence_ids'] = [e['evidence_id'] for e in source['evidence'] if e['kind'] == 'published_piece']
        with self.assertRaisesRegex(ValueError, 'real reader question'):
            seal(source['pack'], source['evidence'], meta, NOW)

    def test_answer_piece_is_a_substack_or_seo_draft(self):
        source = read_json(ROOT / 'tests/fixtures/answer-input.json')
        pack = copy.deepcopy(source['pack'])
        pack['items'][0]['platform'] = 'linkedin'
        with self.assertRaises(ValueError):
            seal(pack, source['evidence'], source['metadata'], NOW)

    def test_v2_link_placement_must_match_metadata(self):
        pack, evidence, metadata = draft()
        pack['items'][0]['text'] = 'Read ' + tracked(URL, 'x', 'daily', '2026-10-17')
        with self.assertRaisesRegex(ValueError, 'asset/placement'):
            seal(pack, evidence, metadata, NOW)

    def test_stable_id_survives_copy_edit_revision_changes(self):
        pack, evidence, metadata = draft()
        first = seal(pack, evidence, metadata, NOW)
        pack['items'][0]['text'] += ' Read it.'
        second = seal(pack, evidence, metadata, NOW)
        self.assertEqual(first['metadata'][0]['item_id'], second['metadata'][0]['item_id'])
        self.assertNotEqual(first['metadata'][0]['revision_id'], second['metadata'][0]['revision_id'])
        first['pack']['items'][0]['text'] += ' Edited again.'
        with self.assertRaises(ValueError):
            validate_envelope(first, NOW)

    def test_projection_is_explicit_and_does_not_assert_posted(self):
        pack, evidence, metadata = draft()
        pack['items'][0].update(status='posted', extra='not transmitted')
        result = wire_pack(seal(pack, evidence, metadata, NOW), NOW)
        self.assertEqual(set(result), {'pack_date', 'kind', 'headline', 'items', 'numbers', 'link', 'source'})
        self.assertEqual(set(result['items'][0]), {'platform', 'text'})

    def test_numbers_need_structured_evidence(self):
        pack = {'pack_date': '2026-10-17', 'kind': 'numbers', 'headline': 'Fixture', 'items': [],
                'numbers': [{'platform': 'x', 'followers': 12, 'note': 'Fixture source, snapshot today.'}]}
        with self.assertRaises(ValueError):
            seal(pack, [], [], NOW)
        obs = observation(metric='followers', unit='accounts', window_kind='snapshot', start=NOW, end=NOW, value=12)
        self.assertTrue(seal(pack, [], [], NOW, [obs]))
        pack['numbers'][0]['new_this_week'] = 4
        with self.assertRaises(ValueError):
            seal(pack, [], [], NOW, [obs])

    def test_invalid_number_types(self):
        pack = {'pack_date': '2026-10-17', 'kind': 'numbers', 'headline': 'Fixture', 'items': []}
        for value in (True, '42', float('nan'), float('inf'), -1):
            with self.subTest(value=value):
                self.assertTrue(check_pack({**pack, 'numbers': [{'platform': 'x', 'followers': value}]}))

    def test_source_label_is_text_not_a_numeric_measure(self):
        pack = {'pack_date': '2026-10-17', 'kind': 'numbers', 'headline': 'Fixture', 'items': [],
                'numbers': [{'platform': 'substack', 'followers': None, 'top_source': 'Recommendations', 'note': 'Not shown in fixture.'}]}
        self.assertEqual(check_pack(pack), [])


    def test_encoded_url_server_edge_case_is_refused_at_export(self):
        pack, evidence, metadata = draft()
        # urlencode normalises a space to +. A literal percent value still
        # produces a percent encoding that the legacy server can misread.
        pack['items'][0]['text'] = 'Read ' + tracked(URL + '?ref=2%2520cats', 'x', 'daily', '2026-10-17', metadata[0]['asset_id'], metadata[0]['placement'])
        self.assertEqual(check_pack(pack), [])
        with self.assertRaisesRegex(ValueError, 'legacy API'):
            wire_pack(seal(pack, evidence, metadata, NOW), NOW)

    def test_future_evidence_is_refused(self):
        pack, evidence, metadata = draft()
        evidence[0]['observed_at'] = '2026-10-18T00:00:00Z'
        with self.assertRaises(ValueError):
            seal(pack, evidence, metadata, NOW)

    def test_wrong_platform_source_is_refused(self):
        self.assertTrue(problems({'platform': 'linkedin', 'text': 'Read ' + tracked(URL, 'x', 'daily')}))

    def test_duplicate_item_identity_is_refused(self):
        pack, evidence, metadata = draft()
        pack['items'] *= 2
        with self.assertRaises(ValueError):
            seal(pack, evidence, metadata * 2, NOW)

    def test_nonempty_numbers_row_needs_context(self):
        pack = {'pack_date': '2026-10-17', 'kind': 'numbers', 'headline': 'Fixture',
                'items': [], 'numbers': [{'platform': 'x', 'followers': None}]}
        with self.assertRaisesRegex(ValueError, 'note'):
            seal(pack, [], [], NOW)


class MeasurementTests(unittest.TestCase):
    def test_immature_retention_cohort_refused(self):
        with self.assertRaisesRegex(ValueError, 'matured'):
            validate_observation(observation(metric='retained_30d', unit='people', window_kind='cohort'))
    def test_missing_is_null_with_reason(self):
        self.assertTrue(validate_observation(observation(value=None, availability='signed_out', reason='Signed out.')))
        with self.assertRaises(ValueError):
            validate_observation(observation(value=None, availability='signed_out'))

    def test_views_are_not_reach(self):
        with self.assertRaises(ValueError):
            validate_observation(observation(metric='views'))

    def test_invalid_window_and_source(self):
        for updates in ({'start': '2026-10-20T04:00:00Z'}, {'captured_at': '2026-10-14T00:00:00Z'}, {'source': 'not a URL'}, {'timezone': 'UTC'}):
            with self.subTest(updates=updates), self.assertRaises(ValueError):
                validate_observation(observation(**updates))

    def test_repeated_weekly_capture_not_added_twice(self):
        row = observation()
        self.assertEqual(aggregate([row, row])['value'], 100)
        changed = observation(value=103, captured_at='2026-10-17T19:00:00Z')
        self.assertEqual(aggregate([row, changed])['value'], 103)

    def test_overlap_and_gap(self):
        with self.assertRaises(ValueError):
            aggregate([observation(), observation(start='2026-10-15T12:00:00Z')])
        result = aggregate([observation(), observation(start='2026-10-17T04:00:00Z', end='2026-10-17T16:00:00Z')])
        self.assertIsNone(result['value'])

    def test_disjoint_daily_observations_add(self):
        result = aggregate([observation(), observation(start='2026-10-16T04:00:00Z', end='2026-10-17T04:00:00Z', value=20)])
        self.assertEqual(result['value'], 120)

    def test_snapshot_not_summed(self):
        with self.assertRaises(ValueError):
            aggregate([observation(metric='followers', window_kind='snapshot', start=NOW, end=NOW)])

    def test_missing_window_not_zero(self):
        self.assertIsNone(aggregate([observation(value=None, availability='not_shown', reason='Unavailable')])['value'])

    def test_yield_requires_attribution_and_matching_unique_reach(self):
        new = observation(metric='new_free', unit='people', value=4, attribution_basis='tagged source export')
        self.assertEqual(yield_per_thousand(new, observation())['value'], 40)
        self.assertIsNone(yield_per_thousand({**new, 'attribution_basis': 'temporal'}, observation())['value'])
        self.assertIsNone(yield_per_thousand(new, observation(scope='other'))['value'])
        self.assertIsNone(yield_per_thousand(new, observation(metric='views', unit='views'))['value'])


    def test_conflicting_identical_capture_fails(self):
        with self.assertRaises(ValueError):
            aggregate([observation(), observation(value=101)])

    def test_different_source_or_scope_not_combined(self):
        with self.assertRaises(ValueError):
            aggregate([observation(), observation(scope='different')])

    def test_zero_is_valid_only_as_an_observed_value(self):
        self.assertEqual(validate_observation(observation(value=0))['value'], 0)
        with self.assertRaises(ValueError):
            validate_observation(observation(value=0, availability='not_shown', reason='Unknown'))


class OperationTests(unittest.TestCase):
    def items(self):
        return [{'item_id': str(i), 'priority': 1, 'minutes': 7} for i in range(4)]

    def test_global_budget_across_jobs(self):
        result = daily_queue(self.items(), NOW)
        self.assertEqual(result['estimated_minutes'], 14)
        self.assertEqual(len(result['deferred']), 2)

    def test_sunday_budget(self):
        self.assertEqual(daily_queue(self.items(), '2026-10-18T18:00:00Z')['estimated_minutes'], 28)

    def test_expired_blocked_and_done_are_deferred(self):
        items = self.items()[:3]
        items[0]['expires_at'] = '2026-10-17T17:00:00Z'
        items[1]['blocked_by'] = ['video not live']
        items[2]['status'] = 'posted'
        self.assertEqual(daily_queue(items, NOW)['items'], [])

    def test_priority_beats_generation_order(self):
        items = self.items()
        items[0]['priority'] = 5
        self.assertNotEqual(daily_queue(items, NOW)['items'][0]['item_id'], '0')

    def test_duplicates_and_bad_effort_fail(self):
        for items in ([self.items()[0]] * 2, [{'item_id': 'x', 'priority': True, 'minutes': 1}], [{'item_id': 'x', 'priority': 1, 'minutes': 0}]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                daily_queue(items, NOW)

    def event(self, **updates):
        return {'event_id': 'fixture-event', 'person_id': 'fixture-only', 'type': 'drafted', 'at': '2026-10-15T12:00:00Z', **updates}

    def test_draft_never_advances_or_starts_cooldown(self):
        result = relationship([self.event()], 'fixture-only', NOW)
        self.assertEqual(result['state'], 'uncontacted')
        self.assertTrue(result['eligible'])

    def test_real_sent_event_requires_proof_and_human(self):
        with self.assertRaises(ValueError):
            relationship([self.event(type='sent')], 'fixture-only', NOW)
        result = relationship([self.event(type='sent', confirmed_by='Krish', evidence_url='https://example.com/message')], 'fixture-only', NOW)
        self.assertFalse(result['eligible'])

    def test_inbound_allows_relevant_next_step(self):
        result = relationship([self.event(type='replied', confirmed_by='Krish', evidence_url='https://example.com/message')], 'fixture-only', NOW)
        self.assertTrue(result['eligible'])

    def test_decline_suppresses_outreach(self):
        result = relationship([self.event(type='declined', confirmed_by='Krish', evidence_url='https://example.com/message')], 'fixture-only', NOW)
        self.assertFalse(result['eligible'])

    def test_experiment_cannot_kill_on_small_sample_or_unfinished_window(self):
        exp = {'experiment_id': 'fixture', 'hypothesis': 'Fixture.', 'primary_metric': 'reach', 'guardrail': 'Fixture.',
               'decision_rule': 'Fixture.', 'owner': 'Krish', 'status': 'completed', 'minimum_observations': 6,
               'start': '2026-10-01T00:00:00Z', 'end': '2026-10-16T04:00:00Z'}
        self.assertIn('too few', experiment_decision(exp, [], NOW))
        self.assertIn('not completed', experiment_decision({**exp, 'end': '2026-10-30T00:00:00Z'}, [], NOW))


    def test_cooldown_expires_from_real_send(self):
        sent = self.event(type='sent', at='2026-07-01T12:00:00Z', confirmed_by='Krish', evidence_url='https://example.com/message')
        self.assertTrue(relationship([sent], 'fixture-only', NOW, 90)['eligible'])

    def test_future_relationship_event_fails(self):
        with self.assertRaises(ValueError):
            relationship([self.event(at='2026-10-20T12:00:00Z')], 'fixture-only', NOW)


class RuntimeTests(unittest.TestCase):
    def test_atomic_utf8_write_and_lock(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            write_json(path, {'text': '£ café'})
            self.assertEqual(read_json(path)['text'], '£ café')
            with locked(path):
                with self.assertRaises(ValueError):
                    with locked(path):
                        pass
            self.assertFalse(Path(str(path) + '.lock').exists())

    def test_offline_doctor_needs_no_secrets_or_network(self):
        with patch.object(growth, 'token', side_effect=AssertionError('secret read')), patch('urllib.request.urlopen', side_effect=AssertionError('network')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(growth.doctor(offline=True), 0)

    def test_delivery_gate_before_token_or_network(self):
        with patch.object(growth, 'token', side_effect=AssertionError('secret read')):
            with self.assertRaisesRegex(ValueError, 'explicit'):
                growth.call('POST', '/api/growth/packs', {}, deliver=False)

    def test_origin_allowlist(self):
        with patch.object(growth, 'BASE', 'https://example.com'), patch.object(growth, 'token', side_effect=AssertionError('secret read')):
            with self.assertRaisesRegex(ValueError, 'origin'):
                growth.call('GET', '/api/growth/packs')

    def test_redirects_never_forward_secret(self):
        with self.assertRaises(ValueError):
            growth.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

    def test_failed_delivery_is_failure_and_hides_remote_body(self):
        error = urllib.error.HTTPError('https://controlcenter.krishraja.com', 500, 'failure', {}, io.BytesIO(b'secret body'))
        with patch.object(growth, 'token', return_value='fixture-token'), patch('urllib.request.OpenerDirector.open', side_effect=error):
            with self.assertRaises(ValueError) as result:
                growth.call('POST', '/api/growth/packs', {}, deliver=True)
            self.assertNotIn('secret body', str(result.exception))

    def test_offline_end_to_end_has_no_network_or_control_centre(self):
        with tempfile.TemporaryDirectory() as folder, patch('urllib.request.urlopen', side_effect=AssertionError('network')), patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')), patch.object(growth, 'call', side_effect=AssertionError('Control Centre')):
            first = run(ROOT, folder)
            second = run(ROOT, folder)
            self.assertEqual(first, second)
            self.assertEqual(first['external_writes'], 0)
            self.assertEqual(first['replay_new_tasks'], 0)
            self.assertTrue(first['draft_did_not_advance_outreach'])

    def test_cli_prepare_export_and_post_default_dry_run(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()), patch.object(growth, 'call', side_effect=AssertionError('Control Centre')):
            source, envelope, wire = (str(Path(folder) / name) for name in ('input.json', 'envelope.json', 'wire.json'))
            pack, evidence, metadata = draft()
            write_json(source, {'pack': pack, 'evidence': evidence, 'metadata': metadata})
            self.assertEqual(growth.main(['prepare', source, '--out', envelope, '--now', NOW]), 0)
            self.assertEqual(growth.main(['export', envelope, '--out', wire, '--now', NOW]), 0)
            with patch('engine.packs.instant', wraps=instant) as clock:
                # Current wall time can differ on CI; freeze the validation clock.
                clock.side_effect = lambda value=None: instant(value or NOW)
                self.assertEqual(growth.main(['post', envelope]), 0)

    def test_nine_automations_one_per_job_file(self):
        config = read_json(ROOT / 'automations.json')
        self.assertEqual(config['timezone'], 'America/New_York')
        self.assertEqual(len(config['automations']), 9)
        # Conversion runs the weekly audit. Daily browser work has its own
        # Codex heartbeat, not an extra entry in this nine-job configuration.
        self.assertEqual({r['job'] for r in config['automations']},
                         {'jobs/' + p.name for p in (ROOT / 'jobs').glob('*.md')
                          if p.name not in ('channel-audit.md', 'daily-growth.md')})
        self.assertIn('jobs/channel-audit.md', (ROOT / 'jobs/conversion.md').read_text())
        conversion = next(r for r in config['automations'] if r['job'] == 'jobs/conversion.md')
        self.assertEqual(conversion['timezone'], 'Europe/London')
        self.assertEqual(conversion['schedule'], 'RRULE:FREQ=WEEKLY;BYDAY=SA;BYHOUR=12;BYMINUTE=0')


    def test_corrupt_feed_does_not_replace_catalog(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            state = Path(folder) / 'state.json'
            feed = Path(folder) / 'feed.xml'
            write_json(state, {'schema_version': 2, 'pieces': {}, 'sentinel': 'unchanged'})
            feed.write_text('<not valid XML', encoding='utf-8')
            with self.assertRaises(ValueError):
                growth.main(['discover', '--feed-file', str(feed), '--state', str(state), '--now', NOW])
            self.assertEqual(read_json(state)['sentinel'], 'unchanged')
            self.assertFalse(Path(str(state) + '.lock').exists())

    def test_configuration_describes_conditional_surfaces_not_verified_access(self):
        channels = read_json(ROOT / 'channels.json')['channels']
        self.assertTrue(all(r['access'] == 'not_verified_in_runtime' for r in channels))
        self.assertEqual({r['channel'] for r in channels}, {'substack', 'website', 'linkedin', 'x', 'youtube', 'instagram', 'facebook', 'tiktok', 'threads', 'spotify', 'reddit', 'email', 'partner'})
        self.assertTrue(all(r['status'] == 'planned' and r['start'] is None for r in read_json(ROOT / 'experiments.json')['experiments']))


if __name__ == '__main__':
    unittest.main()
