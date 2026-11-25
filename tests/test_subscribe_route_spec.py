"""The one subscribe route (audit 2026-11-14, I-09): specs/subscribe-route.json is the shape every repository
builds a subscribe link from, so the code that builds and checks links here must equal it. Offline only."""
import json
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit

from engine import intensity, route, subscribe_gate
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.run import ga4

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'specs' / 'subscribe-route.json').read_text(encoding='utf-8'))


class SubscribeRouteSpecTests(unittest.TestCase):
    def test_the_spec_names_its_schema(self):
        self.assertEqual(SPEC['schema'], 'mymu-subscribe-route/1')

    def test_the_page_tags_and_pattern_equal_the_code(self):
        conversion = intensity.bounds()['conversion']
        self.assertEqual(SPEC['page'], conversion['subscribe_url'])
        self.assertEqual(urlsplit(SPEC['page']).hostname, ga4.OWN_HOST)
        self.assertEqual((SPEC['medium'], SPEC['campaign']), (route.MEDIUM, route.CAMPAIGN))
        self.assertEqual(tuple(SPEC['post_tags']), intensity.SOURCE_TAGS)
        self.assertEqual(tuple(SPEC['post_tags']), route.UTMS)
        self.assertEqual(tuple(SPEC['post_tags']), ga4.UTMS)
        self.assertEqual(tuple(SPEC['profile_tags']), intensity.PROFILE_TAGS)
        self.assertEqual(SPEC['profile_link_channels'], conversion['profile_link_channels'])
        self.assertEqual(SPEC['utm_content_pattern'], route.CONTENT.pattern)

    def test_the_sources_equal_the_gate_and_the_pinned_channels(self):
        self.assertEqual(set(SPEC['sources']), set(BUFFER_CHANNEL_ID))
        for channel, names in SPEC['sources'].items():
            self.assertEqual(set(names), {channel, subscribe_gate.SERVICE.get(channel, channel)}, channel)

    def test_a_link_built_from_the_spec_is_the_link_the_code_builds_and_passes_the_gate(self):
        for channel in SPEC['sources']:
            content = 'slot-2026-11-14-' + channel
            built = SPEC['page'] + '?' + '&'.join(t + '=' + v for t, v in zip(
                SPEC['post_tags'], (channel, SPEC['medium'], SPEC['campaign'], content)))
            self.assertEqual(built, route.subscribe_url(channel, content))
            self.assertRegex(content, SPEC['utm_content_pattern'])
            found, why = subscribe_gate._tagged(built, channel, intensity.ROOT)
            self.assertEqual((found, why), (built, []), channel)

    def test_the_approved_profile_links_follow_the_spec(self):
        table = (ROOT / 'jobs' / 'channel-audit.md').read_text(encoding='utf-8')
        links = re.findall(r'`(' + re.escape(SPEC['page']) + r'\?[^`]+)`', table)
        self.assertTrue(links)
        for link in links:
            query = {k: v[0] for k, v in parse_qs(urlsplit(link).query).items()}
            self.assertTrue(all(query.get(t) for t in SPEC['profile_tags']), link)
            for key, value in SPEC['profile_link'].items():
                self.assertEqual(query.get(key), value, link)

    def test_a_board_items_utm_content_is_the_rule_the_spec_states(self):
        self.assertIn('engine-2026-11-09-gitbroke-threads', SPEC['utm_content_rule'])
        content = route.item_content('engine:2026-11-09:gitbroke', 'threads')
        self.assertEqual(content, 'engine-2026-11-09-gitbroke-threads')
        self.assertRegex(content, SPEC['utm_content_pattern'])


# The weekly edition's own links (Krish, 2026-11-25: one email a week, Saturday 08:00 New York). The block is the one
# content-engine and growth agreed, byte for byte; content-engine vendors this file with its sha256.
EDITION = {
    'utm_source': 'newsletter',
    'utm_medium': 'email',
    'utm_campaign': 'weekly',
    'utm_content_pattern': '^edition-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{1,40}$',
    'places': ['forward', 'subscribe', 'piece-mon', 'piece-wed', 'piece-fri', 'video-mon', 'video-wed', 'video-fri',
               'note'],
    'rule': "Every link in the weekly edition carries all four tags; utm_content is edition-<the Saturday, "
            "YYYY-MM-DD>-<place>. A subscribe link goes to the one page; a piece link goes to the piece's own "
            "address with the same four tags.",
}
SATURDAY = '2026-11-14'
PIECE = 'https://home.makeyourmindup.ai/p/synthetic-piece'


class EditionRouteTests(unittest.TestCase):
    def test_the_edition_block_is_the_agreed_one_and_every_older_key_stands(self):
        self.assertEqual(SPEC['edition'], EDITION)
        self.assertEqual(list(SPEC['edition']), list(EDITION))
        self.assertEqual(list(SPEC), ['schema', 'note', 'page', 'medium', 'campaign', 'post_tags', 'profile_tags',
                                      'profile_link', 'profile_link_channels', 'utm_content_pattern',
                                      'utm_content_rule', 'sources', 'sources_rule', 'content_of', 'edition'])
        self.assertEqual(SPEC['schema'], 'mymu-subscribe-route/1')
        # newsletter is the edition's source, never a social one: the social sources stay the pinned channels.
        self.assertNotIn('newsletter', SPEC['sources'])
        self.assertFalse(any('newsletter' in names for names in SPEC['sources'].values()))
        self.assertEqual(set(SPEC['sources']), set(BUFFER_CHANNEL_ID))

    def test_the_edition_tags_equal_the_code(self):
        edition = SPEC['edition']
        self.assertEqual((edition['utm_source'], edition['utm_medium'], edition['utm_campaign']),
                         (route.EDITION_SOURCE, route.EDITION_MEDIUM, route.EDITION_CAMPAIGN))
        self.assertEqual(edition['utm_content_pattern'], route.EDITION_CONTENT.pattern)
        self.assertEqual(tuple(edition['places']), route.EDITION_PLACES)
        self.assertEqual(set(route.EDITION_PAGE_PLACES) | set(route.EDITION_TARGET_PLACES) | {'note'},
                         set(route.EDITION_PLACES))
        self.assertEqual(tuple((k, edition[k]) for k in ('utm_source', 'utm_medium', 'utm_campaign')),
                         ga4.EDITION_TAGS)
        self.assertEqual(edition['utm_content_pattern'], ga4.EDITION_CONTENT.pattern)
        self.assertEqual(edition['utm_source'], ga4.EDITION_SOURCE)

    def test_an_edition_link_built_from_the_spec_is_the_link_the_code_builds(self):
        edition = SPEC['edition']
        for place in edition['places']:
            content = 'edition-' + SATURDAY + '-' + place
            self.assertRegex(content, edition['utm_content_pattern'])
            self.assertEqual(route.edition_content(SATURDAY, place), content)
            tags = '&'.join(t + '=' + v for t, v in zip(SPEC['post_tags'], (
                edition['utm_source'], edition['utm_medium'], edition['utm_campaign'], content)))
            target = PIECE if place in route.EDITION_TARGET_PLACES else None
            built = (target or SPEC['page']) + '?' + tags
            self.assertEqual(route.edition_url(SATURDAY, place, target), built)
            self.assertEqual(route.edition_tags(built), {'source': 'newsletter', 'content': content,
                                                         'edition_date': SATURDAY, 'place': place})

    def test_an_edition_link_is_credited_to_newsletter_by_the_gate_and_ga4(self):
        link = route.edition_url(SATURDAY, 'forward')
        self.assertEqual(subscribe_gate.credited_source(link), 'newsletter')
        found = ga4.own_links('Pass it on: ' + link)
        self.assertEqual([(x['tracked'], x['edition'], x['credited_source'], x['utm_content']) for x in found],
                         [(True, True, 'newsletter', 'edition-' + SATURDAY + '-forward')])
        piece = ga4.own_links(route.edition_url(SATURDAY, 'piece-wed', PIECE))[0]
        self.assertEqual((piece['edition'], piece['credited_source']), (True, 'newsletter'))
        # A social link keeps its own channel, through the gate and through GA4, exactly as before.
        for channel in SPEC['sources']:
            social = route.subscribe_url(channel, 'slot-2026-11-14-' + channel)
            self.assertEqual(subscribe_gate.credited_source(social), channel)
            self.assertIsNone(route.edition_tags(social))
            got = ga4.own_links(social)[0]
            self.assertEqual((got['edition'], got['credited_source']), (False, channel))

    def test_an_edition_link_never_stands_in_for_a_channels_own_link(self):
        link = route.edition_url(SATURDAY, 'note')
        found, why = subscribe_gate._tagged('Read the week: ' + link, 'substack-notes', intensity.ROOT)
        self.assertIsNone(found)
        self.assertTrue(why and 'credited to newsletter' in why[0], why)
        both = 'Read the week: ' + link + ' Subscribe: ' + route.subscribe_url('substack-notes', 'slot-1')
        self.assertEqual(subscribe_gate._tagged(both, 'substack-notes', intensity.ROOT)[1], [])

    def test_a_link_the_spec_does_not_describe_is_never_built_or_credited(self):
        bad = (
            (('2026-11-13', 'forward', None), 'Saturday'),
            (('2026-11-31', 'forward', None), 'real date'),
            (('14/11/2026', 'forward', None), 'YYYY-MM-DD'),
            ((SATURDAY, 'footer', None), 'edition places'),
            ((SATURDAY, 'piece-mon', None), 'own address'),
            ((SATURDAY, 'forward', PIECE), 'one subscribe page'),
            ((SATURDAY, 'piece-mon', 'http://home.makeyourmindup.ai/p/x'), 'own https address'),
            ((SATURDAY, 'piece-mon', 'https://example.com/p/x'), 'own https address'),
            ((SATURDAY, 'piece-mon', 'https://home.makeyourmindup.ai/'), 'own https address'),
            ((SATURDAY, 'piece-mon', PIECE + '?utm_source=x'), 'utm_ tag'),
        )
        for args, message in bad:
            with self.assertRaisesRegex(ValueError, message, msg=str(args)):
                route.edition_url(*args)
        self.assertEqual(route.edition_url(SATURDAY, 'piece-mon', PIECE + '?r=1#top'),
                         PIECE + '?r=1&utm_source=newsletter&utm_medium=email&utm_campaign=weekly'
                         '&utm_content=edition-' + SATURDAY + '-piece-mon#top')
        good = route.edition_url(SATURDAY, 'subscribe')
        for wrong in (good.replace('utm_medium=email', 'utm_medium=social'),
                      good.replace('utm_campaign=weekly', 'utm_campaign=growth'),
                      good.replace('edition-' + SATURDAY, 'issue-' + SATURDAY),
                      good.replace('home.makeyourmindup.ai', 'example.com')):
            self.assertIsNone(route.edition_tags(wrong), wrong)
            self.assertFalse(any(x['edition'] for x in ga4.own_links(wrong)), wrong)
