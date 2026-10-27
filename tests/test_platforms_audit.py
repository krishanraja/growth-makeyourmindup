"""Known platforms and audit authority per account. Synthetic fixtures only."""
from pathlib import Path
import unittest
from urllib.parse import parse_qsl, urlsplit

from engine.channel_audit import ACCOUNTS, begin, checkpoint, reconcile, repair_plan
from engine.core import PLATFORMS, read_json, tracked

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-10-27T12:00:00+00:00'
URL = 'https://makeyourmindup.ai/p/synthetic'
SUBSCRIBE = 'https://home.makeyourmindup.ai/subscribe'


def change(channel, target, surface='post', field='caption', before='Synthetic typo', after='Synthetic caption'):
    return {'channel': channel, 'account_url': ACCOUNTS[channel], 'target_url': target,
            'surface': surface, 'field': field, 'before': before, 'after': after,
            'evidence': {'method': 'browser', 'url': target, 'excerpt': before, 'observed_at': NOW},
            'reason': 'Correct a synthetic value', 'success_check': 'Reloaded value equals proposed value',
            'owner_verified': True, 'meaning_preserved': True, 'voice_checked': True,
            'claims_checked': True, 'field_editable': True}


def profile_link(channel, target, after=SUBSCRIBE):
    c = change(channel, target, surface='profile', field='link', before='https://old.example', after=after)
    c['link_purpose'] = 'align_subscription'
    c['destination'] = {'method': 'browser', 'url': after, 'requested_url': after, 'observed_at': NOW,
                        'excerpt': 'Subscribe', 'usable': True, 'purpose_match': True}
    return c


def current(c):
    return {**c['evidence'], 'field': c['field'], 'value': c['before'],
            'account_url': c['account_url'], 'owner_verified': True}


def channel_rows():
    return {r['channel']: r for r in read_json(ROOT / 'channels.json')['channels']}


class PlatformsAuditTests(unittest.TestCase):
    def assert_held(self, c):
        plan = repair_plan(c, NOW)
        self.assertEqual(plan['disposition'], 'approval_required')
        self.assertIn('held for Krish', plan['reason'])
        with self.assertRaises(ValueError):
            begin({}, c, current(c), NOW)

    def assert_krish_only(self, c):
        plan = repair_plan(c, NOW)
        self.assertEqual(plan['disposition'], 'krish_only')
        self.assertIn('never saves', plan['reason'])
        with self.assertRaisesRegex(ValueError, 'alone'):
            begin({}, c, current(c), NOW)

    def test_linkedin_audit_edit_is_held(self):
        # Krish, 26 Oct 2026: no edits to live LinkedIn posts or profile fields,
        # including the older existing-field audit permission. Krish, 27 Oct
        # 2026: LinkedIn stays his own final click, so the hold is now the
        # stricter krish_only disposition rather than approval_required.
        post = 'https://www.linkedin.com/posts/synthetic'
        for field in ('title', 'caption', 'description', 'link'):
            c = change('linkedin', post, field=field)
            c['destination'] = {'method': 'browser', 'url': c['after'], 'requested_url': c['after'],
                                'observed_at': NOW, 'excerpt': 'Synthetic', 'usable': True, 'purpose_match': True}
            self.assert_krish_only(c)
        self.assert_krish_only(profile_link('linkedin', ACCOUNTS['linkedin']))

    def test_linkedin_audit_is_krish_only_even_after_approval(self):
        # Krish, 26 Oct 2026 (docs/PUBLISHING-AUTHORITY.md): the engine never
        # edits live LinkedIn, not even after approval.
        post = 'https://www.linkedin.com/posts/synthetic'
        for field in ('caption', 'bio', 'pin', 'link'):
            c = change('linkedin', post, field=field)
            c.update({'approved': True, 'approval': {'by': 'Krish', 'at': NOW}, 'krish_approved': True})
            self.assert_krish_only(c)
        # A forged pending record cannot be reconciled into a verified save.
        c = change('linkedin', post)
        record = {**repair_plan(c, NOW), 'status': 'pending_readback', 'started_at': NOW, 'attempts': 1}
        readback = {**c['evidence'], 'field': 'caption', 'value': c['after'], 'excerpt': c['after'], 'reopened': True}
        with self.assertRaisesRegex(ValueError, 'alone'):
            reconcile(record, readback, NOW)
        # LinkedIn stays in the inventory: coverage is observation, not an edit.
        coverage = {'channel': 'linkedin', 'account_url': ACCOUNTS['linkedin'], 'complete': True,
                    'pagination_complete': True, 'blockers': [], 'profiles_checked': True,
                    'pins_checked': True, 'window_start': '2026-09-27T12:00:00+00:00', 'window_end': NOW}
        self.assertEqual(checkpoint(None, coverage, NOW), NOW)

    def test_facebook_and_threads_audit_edits_are_held(self):
        # Krish, 27 Oct 2026: Facebook and Threads are inventoried and observed,
        # but he has not extended the 21 Oct audit authority to them.
        targets = {'facebook': ('https://www.facebook.com/1364858250042525/posts/synthetic',
                                'https://facebook.com/1364858250042525/posts/synthetic'),
                   'threads': ('https://www.threads.com/@krishraja1/post/synthetic',
                               'https://www.threads.net/@krishraja1/post/synthetic')}
        for channel, urls in targets.items():
            for target in urls:
                for surface, field in (('post', 'title'), ('post', 'caption'), ('post', 'description'),
                                       ('post', 'link'), ('post', 'bio'), ('profile', 'pin')):
                    c = change(channel, target, surface=surface, field=field)
                    plan = repair_plan(c, NOW)
                    self.assertNotEqual(plan['disposition'], 'autonomous')
                    self.assert_held(c)
            self.assert_held(profile_link(channel, ACCOUNTS[channel]))
            # A held record is never reconciled into a verified save.
            c = change(channel, urls[0])
            record = {**repair_plan(c, NOW), 'status': 'pending_readback', 'started_at': NOW, 'attempts': 1}
            readback = {**c['evidence'], 'field': 'caption', 'value': c['after'], 'excerpt': c['after'], 'reopened': True}
            with self.assertRaisesRegex(ValueError, 'held for Krish'):
                reconcile(record, readback, NOW)

    def test_www_hosts_match_their_account(self):
        fb = repair_plan(change('facebook', 'https://www.facebook.com/1364858250042525/posts/synthetic'), NOW)
        self.assertEqual(fb['disposition'], 'approval_required')
        self.assertIn('held for Krish', fb['reason'])
        for channel, target in (('threads', 'https://threads.com/@krishraja1/post/synthetic'),
                                ('threads', 'https://threads.net/@krishraja1/post/synthetic'),
                                ('linkedin', 'https://linkedin.com/posts/synthetic')):
            self.assertIn(repair_plan(change(channel, target), NOW)['disposition'], ('approval_required', 'krish_only'))
        # Removing www. never makes a lookalike or another platform match.
        for channel, target in (('facebook', 'https://www.instagram.com/p/synthetic'),
                                ('facebook', 'https://m.facebook.com/1364858250042525/posts/synthetic'),
                                ('facebook', 'https://www.facebook.com.example.com/posts/synthetic'),
                                ('facebook', 'https://www.www.facebook.com/posts/synthetic'),
                                ('facebook', 'https://notfacebook.com/posts/synthetic'),
                                ('threads', 'https://www.threads.org/@krishraja1/post/synthetic'),
                                ('instagram', 'https://www.facebook.com/1364858250042525/posts/synthetic'),
                                ('youtube', 'https://youtube.com.example.com/watch?v=synthetic')):
            with self.assertRaisesRegex(ValueError, 'another platform'):
                repair_plan(change(channel, target), NOW)
        # The account check stays exact: a www. variant of the owner URL is refused.
        c = change('facebook', 'https://www.facebook.com/1364858250042525/posts/synthetic')
        c['account_url'] = 'https://www.facebook.com/1364858250042525'
        with self.assertRaisesRegex(ValueError, 'configured owner'):
            repair_plan(c, NOW)
        # Bare instagram.com still matches the www. account; the 21 Oct authority is unchanged there.
        self.assertEqual(repair_plan(change('instagram', 'https://instagram.com/p/synthetic'), NOW)['disposition'],
                         'autonomous')
        # Notes have no audit targets yet.
        with self.assertRaisesRegex(ValueError, 'unconfigured account'):
            repair_plan({**change('substack', 'https://home.makeyourmindup.ai/p/synthetic'), 'channel': 'notes'}, NOW)

    def test_facebook_is_a_known_platform(self):
        record = read_json(ROOT / 'social/channels/facebook.json')
        self.assertIn('facebook', PLATFORMS)
        self.assertEqual(ACCOUNTS['facebook'], record['account_url'])
        self.assertEqual(channel_rows()['facebook']['url'], record['account_url'])
        query = dict(parse_qsl(urlsplit(tracked(URL, 'facebook', 'daily', '2026-10-27')).query))
        self.assertEqual(query['utm_source'], 'facebook')
        target = ACCOUNTS['facebook'] + '/posts/synthetic'
        # Krish, 27 Oct 2026: the Page is inventoried, but the 21 Oct audit
        # authority is not extended to it, so caption edits are held for him.
        self.assertEqual(repair_plan(change('facebook', target), NOW)['disposition'], 'approval_required')
        self.assertEqual(repair_plan(change('facebook', target, field='bio'), NOW)['disposition'], 'approval_required')
        with self.assertRaises(ValueError):
            repair_plan(change('facebook', 'https://www.instagram.com/p/synthetic'), NOW)
        coverage = {'channel': 'facebook', 'account_url': ACCOUNTS['facebook'], 'complete': True,
                    'pagination_complete': True, 'blockers': [], 'profiles_checked': True,
                    'pins_checked': True, 'window_start': '2026-09-27T12:00:00+00:00', 'window_end': NOW}
        self.assertEqual(checkpoint(None, coverage, NOW), NOW)

    def test_threads_is_known_and_audit_edits_are_held(self):
        # Krish, 27 Oct 2026: Threads joins; audit edits are held like LinkedIn
        # until he rules otherwise.
        self.assertIn('threads', PLATFORMS)
        self.assertEqual(ACCOUNTS['threads'], 'https://www.threads.com/@krishraja1')
        self.assertEqual(channel_rows()['threads']['url'], ACCOUNTS['threads'])
        query = dict(parse_qsl(urlsplit(tracked(URL, 'threads', 'daily', '2026-10-27')).query))
        self.assertEqual(query['utm_source'], 'threads')
        self.assert_held(change('threads', 'https://www.threads.com/@krishraja1/post/synthetic'))
        self.assert_held(profile_link('threads', ACCOUNTS['threads']))

    def test_notes_links_are_tracked(self):
        # Krish, 27 Oct 2026, superseding the 14 Oct "no Notes" ruling.
        self.assertIn('notes', PLATFORMS)
        result = tracked(URL + '?utm_source=substack', 'notes', 'daily', '2026-10-27')
        query = dict(parse_qsl(urlsplit(result).query))
        self.assertEqual(query, {'utm_source': 'notes', 'utm_medium': 'organic', 'utm_campaign': 'growth',
                                 'utm_content': 'daily-20261027'})
        placed = tracked(URL, 'notes', 'daily', '2026-10-27', 'story1', 'note')
        self.assertNotEqual(placed, tracked(URL, 'substack', 'daily', '2026-10-27', 'story1', 'note'))
        self.assertIn('notes', channel_rows()['substack']['surfaces'])

    def test_x_profile_link_limit_is_checked(self):
        # The X profile link field holds at most 100 characters (F30).
        at_limit = SUBSCRIBE + '?ref=' + 'a' * (100 - len(SUBSCRIBE) - 5)
        self.assertEqual(len(at_limit), 100)
        self.assertEqual(repair_plan(profile_link('x', ACCOUNTS['x'], at_limit), NOW)['disposition'], 'autonomous')
        over = at_limit + 'a'
        with self.assertRaisesRegex(ValueError, 'field limit'):
            repair_plan(profile_link('x', ACCOUNTS['x'], over), NOW)

    def test_audit_accounts_match_committed_channel_records(self):
        rows = channel_rows()
        for channel, url in ACCOUNTS.items():
            self.assertIn(channel, PLATFORMS)
            if channel in rows:
                self.assertEqual(rows[channel]['url'].rstrip('/'), url.rstrip('/'))


if __name__ == '__main__':
    unittest.main()
