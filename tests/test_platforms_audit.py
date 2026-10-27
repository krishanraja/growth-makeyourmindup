"""Known platforms and audit authority per account. Synthetic fixtures only."""
from pathlib import Path
import unittest
from urllib.parse import parse_qsl, urlsplit

from engine.channel_audit import ACCOUNTS, begin, checkpoint, repair_plan
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

    def test_linkedin_audit_edit_is_held(self):
        # Krish, 26 Oct 2026: no edits to live LinkedIn posts or profile fields,
        # including the older existing-field audit permission.
        post = 'https://www.linkedin.com/posts/synthetic'
        for field in ('title', 'caption', 'description', 'link'):
            c = change('linkedin', post, field=field)
            c['destination'] = {'method': 'browser', 'url': c['after'], 'requested_url': c['after'],
                                'observed_at': NOW, 'excerpt': 'Synthetic', 'usable': True, 'purpose_match': True}
            self.assert_held(c)
        self.assert_held(profile_link('linkedin', ACCOUNTS['linkedin']))

    def test_facebook_is_a_known_platform(self):
        record = read_json(ROOT / 'social/channels/facebook.json')
        self.assertIn('facebook', PLATFORMS)
        self.assertEqual(ACCOUNTS['facebook'], record['account_url'])
        self.assertEqual(channel_rows()['facebook']['url'], record['account_url'])
        query = dict(parse_qsl(urlsplit(tracked(URL, 'facebook', 'daily', '2026-10-27')).query))
        self.assertEqual(query['utm_source'], 'facebook')
        target = ACCOUNTS['facebook'] + '/posts/synthetic'
        # The branded Page sits under the standing 21 Oct existing-field authority.
        self.assertEqual(repair_plan(change('facebook', target), NOW)['disposition'], 'autonomous')
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
