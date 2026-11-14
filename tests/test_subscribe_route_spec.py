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
