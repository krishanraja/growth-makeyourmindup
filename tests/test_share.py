"""Built to be sent (Ruling, Krish, 2026-10-28): the share block, the share-CTA lint and the blind send test.

Synthetic fixtures only. No model, network or platform call happens here: the
blind reader's answers below are written by hand to exercise the comparison.
"""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from engine import share as share_module
from engine.buffer_channels import BUFFER_CHANNEL_ID
from engine.packs import problems
from engine.run.invariants import house_errors
from engine.run.measure import SNACKABLE_PRIMARY, share_fields, share_rates
from engine.run.spec import lint
from engine.share import (JOBS, RULES, StaleSendTest, compare_send_test, cta_applies, cta_errors, dm_line_errors,
                          load_rules, receiver_key, receiver_relation, request_digest, send_test_request, share_errors,
                          share_line, stage_send_test)
from engine.social import ROOT, command, inventory, preflight, validate

SNACKABLE = {'meme', 'carousel', 'single-image', 'short-video', 'story', 'note'}
SHARE = {'sender': 'a head of marketing at a mid-size retailer',
         'receiver': 'her CEO, who keeps asking when the AI pilot pays back',
         'job': 'settles_it',
         'dm_line': 'This is the six-week rule I meant: agree one number on day one, then decide.',
         'moment': 'the Monday leadership meeting where the pilot budget comes up again',
         'standalone': True}


def package(path, fmt='single-image', share=SHARE, caption='One number, agreed on day one, decides the pilot.'):
    path.write_bytes(b'synthetic accepted asset, not a real post')
    return {'schema_version': 1, 'kind': 'package', 'id': 'synthetic-share-package',
            'channel': 'instagram', 'account_url': 'https://www.instagram.com/makeyourmind.up',
            'account_context': 'publication', 'format': fmt, 'tool': 'buffer',
            'buffer_channel_id': BUFFER_CHANNEL_ID['instagram'],
            'source_url': 'https://example.com/verified-test', 'caption': caption,
            'share': copy.deepcopy(share),
            'assets': [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'alt_text': 'Synthetic regression asset.'}],
            'production': {'owner': 'content-engine', 'approved': True, 'evidence_ref': 'synthetic-only'},
            'voice_review_passed': True, 'proposed_due_at': '2026-11-03T14:00:00+00:00',
            'platform_metadata': {'ai_generated': None, 'share_to_feed': None,
                                  'post_type': None, 'link_preview_url': None},
            'publication_approval': {'approved': False, 'payload_sha256': None, 'evidence_ref': None}}


# The request the answers below were given for: a package with this file's default caption and asset.
with tempfile.TemporaryDirectory() as _tmp:
    REQUEST = send_test_request(package(Path(_tmp) / 'asset.bin'))


def answer(receiver='my CEO', job='settles_it', would_send=True,
           dm_line='Here is the rule I was on about: one number on day one.', request=None):
    return {'would_send': would_send, 'receiver': receiver if would_send else None,
            'job': job if would_send else None, 'dm_line': dm_line if would_send else None,
            'why': 'Synthetic reader answer for tests.',
            'request_sha256': (request or REQUEST)['request_sha256']}


def compare(declared, reply, request=None):
    return compare_send_test(declared, reply, request or REQUEST)


def scoped_root(folder, scope):
    """A copy of social/ (and the docs routing reads) with share.json's share_cta_scope set."""
    root = Path(folder) / 'root'
    shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
    (root / 'docs').mkdir()
    for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
        shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
    rules = json.loads((root / 'social' / 'share.json').read_text(encoding='utf-8'))
    rules['share_cta_scope'] = scope
    (root / 'social' / 'share.json').write_text(json.dumps(rules, indent=2), encoding='utf-8')
    return root


class ShareRulesTests(unittest.TestCase):
    def test_rules_load_and_match_the_package_schema(self):
        rules = load_rules()
        schema = json.loads((ROOT / 'social' / 'schemas' / 'package.schema.json').read_text(encoding='utf-8'))
        share = schema['properties']['share']
        self.assertEqual(tuple(share['properties']['job']['enum']), JOBS)
        self.assertEqual(tuple(rules['jobs']), JOBS)
        self.assertEqual(set(share['required']), set(SHARE))
        self.assertIn('share', schema['required'])
        self.assertEqual(rules['dm_line_max_chars'], 120)
        ids = [c['id'] for c in rules['share_cta']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(house_errors(RULES.read_text(encoding='utf-8')), [])
        self.assertIn('request_sha256', rules['send_test']['answer_fields'])
        self.assertEqual(rules['share_cta_scope'], 'snackable', "Krish's ruling covers snackable posts")
        self.assertIsNone(rules['send_test']['reader']['persona'])
        self.assertIn("Krish's to make", rules['send_test']['reader']['decision'])
        # A relationship is never folded into a job title: "my boss" is not "a marketing manager".
        self.assertNotIn('manager', rules['receiver_aliases'])
        self.assertNotIn('co-founder', rules['receiver_aliases']['founder'])
        x = rules['measure']['buffer_fields']['channels']['x']
        self.assertEqual((x['sends'], x['public_reposts']), (None, 'reposts'), 'a repost is public, never a send')

    def test_snackable_formats_carry_one_share_mechanic(self):
        formats = inventory()['format']
        self.assertEqual({k for k, v in formats.items() if v['snackable']}, SNACKABLE)
        for name in SNACKABLE:
            checks = [c for c in formats[name]['delivery_checks'] if c.startswith('Share mechanic: ')]
            self.assertEqual(len(checks), 1, name)
            self.assertTrue({'built-to-be-sent', 'share-rate-measure'} <= set(formats[name]['lessons']), name)
            self.assertTrue(formats[name]['measurements'][0].startswith('Primary measure'), name)
        mechanics = {k: next(c for c in v['delivery_checks'] if c.startswith('Share mechanic'))
                     for k, v in formats.items() if v['snackable']}
        self.assertIn('recognition of one specific situation', mechanics['meme'])
        self.assertIn('for a news carousel, one quotable, sourced number or fact a person will repeat',
                      mechanics['carousel'])
        self.assertIn('for an advice carousel, one move someone forwards to a named colleague', mechanics['carousel'])
        self.assertIn('lands with no context in the first seconds', mechanics['short-video'])
        # Production standards are content-engine's (Ruling, Krish, 2026-10-26): for its formats the mechanic
        # is a proposed hook in Growth's brief, never a defect Growth returns against a standard it does not own.
        for name in SNACKABLE:
            owner = formats[name]['production_owner']
            proposal = 'stays a proposal in the brief until content-engine adopts it' in mechanics[name]
            self.assertEqual(proposal, owner == 'content-engine', name)
            shares = ' '.join(c for c in formats[name]['delivery_checks']
                              if c.startswith(('Share mechanic', 'Before Krish sees it')))
            self.assertNotIn('production defect', shares, name)
        text = ' '.join(json.dumps(v) for v in formats.values())
        text += (ROOT / 'social' / 'guides' / 'formats.md').read_text(encoding='utf-8')
        for name in ('Uplifting', 'uplifting', 'Level-up', 'level-up'):
            self.assertNotIn(name, text, 'canonical names: News carousel and Advice')
        lesson = inventory()['lesson']['built-to-be-sent']
        self.assertEqual((lesson['status'], lesson['evidence']['kind']), ('accepted', 'user_ruling'))
        self.assertEqual(inventory()['lesson']['share-rate-measure']['status'], 'hypothesis')

    def test_a_snackable_format_without_its_mechanic_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(str(ROOT / 'social'), str(root / 'social'))
            (root / 'docs').mkdir()
            for name in ('ACCOUNT-VOICE.md', 'PUBLISHING-AUTHORITY.md'):
                shutil.copyfile(str(ROOT / 'docs' / name), str(root / 'docs' / name))
            inventory(root)
            path = root / 'social' / 'formats' / 'meme.json'
            meme = json.loads(path.read_text(encoding='utf-8'))
            meme['delivery_checks'] = [c for c in meme['delivery_checks'] if not c.startswith('Share mechanic')]
            path.write_text(json.dumps(meme), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'one share mechanic'):
                inventory(root)

    def test_hooks_carry_a_share_formula_marked_as_a_house_hypothesis(self):
        hooks = json.loads((ROOT / 'hooks.json').read_text(encoding='utf-8'))
        self.assertIn('House hypothesis', hooks['share_formula'])
        self.assertIn('social/share.json', hooks['share_formula'])
        self.assertTrue(any('never asks for it' in line for line in hooks['everywhere']))
        self.assertEqual(house_errors(json.dumps(hooks)), [])


class ShareBlockTests(unittest.TestCase):
    def test_complete_share_block_passes_and_renders_one_line(self):
        self.assertEqual(share_errors(SHARE), [])
        line = share_line(SHARE)
        self.assertTrue(line.startswith('a head of marketing at a mid-size retailer sends it to her CEO'))
        self.assertIn('(settles it)', line)
        self.assertIn(SHARE['dm_line'], line)

    def test_snackable_package_without_share_block_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for fmt in ('single-image', 'carousel', 'story', 'short-video'):
                p = package(Path(tmp) / 'asset.bin', fmt=fmt, share=None)
                if fmt == 'carousel':
                    p['assets'].append(dict(p['assets'][0], alt_text='Second synthetic frame.'))
                with self.assertRaisesRegex(ValueError, 'needs a share block'):
                    preflight(p, '2026-10-26')
            p = package(Path(tmp) / 'asset.bin')
            del p['share']
            with self.assertRaisesRegex(ValueError, 'missing share'):
                preflight(p, '2026-10-26')
            p = package(Path(tmp) / 'asset.bin')
            p['share']['job'] = 'go_viral'
            with self.assertRaisesRegex(ValueError, 'unsupported value'):
                preflight(p, '2026-10-26')
            p = package(Path(tmp) / 'asset.bin')
            p['share']['standalone'] = False
            with self.assertRaisesRegex(ValueError, 'no context'):
                preflight(p, '2026-10-26')
        # A text post is not snackable: it may carry no block, and a block it carries is still checked.
        self.assertEqual(share_errors(None, snackable=False), [])
        self.assertTrue(share_errors(dict(SHARE, receiver='your network'), snackable=False))

    def test_vague_receivers_are_refused(self):
        # Judged by the gate itself (share_errors and preflight), on the role before any clause or place.
        for vague in ('your network', 'friends', 'a friend', 'someone', 'colleagues', 'a colleague', 'anyone in tech',
                      'everyone at work', 'her followers', 'the team', 'people who care about AI', ' ',
                      'someone in tech', 'a friend at work', "a colleague who'd get it", 'a colleague who\u2019d get it',
                      'someone you know', 'the right person', 'whoever runs AI', 'the whole team', 'her group chat',
                      'my LinkedIn', 'a coworker you like', 'your mate in sales', 'a new colleague',
                      'a friend who just took over pricing at a bank', 'a peer who is planning a pilot'):
            self.assertTrue(share_errors(dict(SHARE, receiver=vague)), vague)
        for vague in ('your network', 'someone you know', 'your mate in sales', 'whoever runs AI'):
            with self.assertRaisesRegex(ValueError, r'share block: receiver|share\.receiver'):
                with tempfile.TemporaryDirectory() as tmp:
                    preflight(package(Path(tmp) / 'a.bin', share=dict(SHARE, receiver=vague)), '2026-10-26')
        for specific in ('her CEO', 'the analyst on her team who builds the weekly report', 'his co-founder',
                         'the CFO signing off the budget', 'my sister', 'a VP at a bank', 'her tech lead',
                         'the head of growth at her company', 'his engineering lead, who is scoping the next pilot'):
            self.assertEqual(share_errors(dict(SHARE, receiver=specific)), [], specific)
        self.assertTrue(share_errors(dict(SHARE, sender='someone')))
        self.assertTrue(share_errors(dict(SHARE, sender='a friend at work')))
        self.assertTrue(share_errors(dict(SHARE, receiver=', who runs pricing at a bank')))
        # Context after the role is never judged as the person: a crowd word there is fine.
        self.assertEqual(share_errors(dict(SHARE, receiver='her CEO, who forwards everything to the board')), [])

    def test_generic_dm_lines_are_refused(self):
        for line in ("You'll like this", 'you will like this!', 'Check this out', 'Saw this and thought of you',
                     'Interesting read, worth a look', 'FYI', 'Share this with your team', 'Thought you\u2019d like this',
                     'Have a look at this, so true', 'Ok you seriously need to see this right now',
                     'Must see, seriously good stuff here', 'Have you seen this yet? Crazy stuff honestly'):
            self.assertTrue(dm_line_errors(line), line)
        self.assertIn('too generic; say the specific reason', dm_line_errors("You'll like this")[0])
        self.assertTrue(dm_line_errors('x ' * 70))
        self.assertTrue(dm_line_errors('This is our pilot \u2014 the six-week rule'))
        self.assertTrue(dm_line_errors('Our pilot hit 40\x25 of the target'))
        self.assertTrue(dm_line_errors('Two lines\nof message'))
        for line in ('This is literally our Tuesday demo, slide for slide.',
                     "Before Thursday's budget review: read the line about who pays for retraining.",
                     'You will like this one: the six-week rule I keep banging on about.'):
            self.assertEqual(dm_line_errors(line), [], line)

    def test_generic_share_ctas_are_refused_in_copy(self):
        asks = ['Share this with your team.', 'Share this!', 'share it with someone who needs it',
                'Tag a friend who still runs pilots forever', 'Tag your boss.', 'Send this to someone who runs a pilot.',
                'Send it to your CFO before Friday', 'Forward this to your board', 'Repost if you agree',
                'RT if this is your company', 'Pass it on.', 'Spread the word', 'Know someone who needs this?',
                'Someone you know needs to see this', 'Like and share', 'Save & share for later',
                'Share if you have been there', 'Drop this in the group chat', 'Please share', 'Restack this',
                'One number decides it. Tag a friend who needs it.', 'If you agree, repost this.',
                'If this helped, pass it on.', 'Read it.\n\U0001f449 Share this with your CFO', 'So share it with your team.',
                '\u267b\ufe0f Repost to help others', 'Hit share if this is your company.',
                'Tap the share button and send it to your CFO.', 'Save this and share it with your team.',
                'If this landed, like and share.', 'DM this to your boss.', 'Send to a friend who runs pilots.',
                'Every boss needs to see this.',
                # Odd spaces and line ends are read as content-engine's copy lint reads them.
                'Share\u00a0this with your team.', 'Tag a\u00a0friend who needs it.',
                'One number decides it.\u2028Tag a friend who needs it.', 'Read it.\u2029Share this with your CFO']
        for text in asks:
            self.assertTrue(cta_errors(text), text)
        self.assertEqual(cta_errors('One number decides it. Tag a friend who needs it.')[0], 'tag-a-friend: "Tag a"')
        # A truthful fact that uses the same verb mid-clause is never an ask (follow.the.money staples).
        clean = ['Nvidia lost market share in one quarter.', 'Investors share this view of the cost.',
                 'A $2bn price tag a year buys a lot of pilots.', 'The partners share it equally.',
                 'Apple will send it to TSMC for the new chip.', 'No hashtag a day keeps the feed calm.',
                 'Who gets paid when the model is free? Three numbers.', 'The board will forward the memo on Friday.',
                 'They pass it on to the buyer.', 'Microsoft and OpenAI share it with regulators first.',
                 'The labs share these with the government', 'Banks tag them as high risk',
                 'Annotators tag a million images a day', 'Insurers tag her as a risk',
                 'Subscribe and we send it to your inbox every Monday.',
                 'Firms that repost it to their own feeds lose reach.', 'The court will forward it on to the regulator.',
                 'Most people know someone who lost a job to a model.', 'If this helped, the full piece is free to read.',
                 # True reporting that uses an ask's words mid-sentence (the 29 Oct review's collisions).
                 'Samsung told engineers never to share it with anyone outside the company.',
                 'Google trained the model but refused to share it with others.',
                 'TikTok users like and share AI clips twice as often as edited ones.',
                 'Gemini can now draft an email and send to your contacts without asking.',
                 'People share if it makes them look ahead of the news.',
                 'X quietly removed the share button from AI replies.',
                 'Viewers hit share three times more on the cloned-voice clip.',
                 "Hollywood's unions spread the word through group chats.",
                 'Engineers post it in the group chat before legal sees it.',
                 'Readers share and save carousels more than they share videos.']
        for text in clean:
            self.assertEqual(cta_errors(text), [], text)
        with tempfile.TemporaryDirectory() as tmp:
            p = package(Path(tmp) / 'asset.bin', caption='One number decides the pilot. Tag a friend who needs it.')
            with self.assertRaisesRegex(ValueError, 'generic share call to action'):
                preflight(p, '2026-10-26')
            p = package(Path(tmp) / 'asset.bin', caption='Banks tag them as high risk. One number decides the pilot.')
            self.assertTrue(preflight(p, '2026-10-26')['structurally_valid'])

    def test_share_cta_scope_is_krishs_choice(self):
        # His ruling covers snackable posts; share_cta_scope all_post_copy would widen the refusal to text posts.
        rules = load_rules()
        self.assertTrue(cta_applies(True, rules))
        self.assertFalse(cta_applies(False, rules))
        self.assertTrue(cta_applies(False, dict(rules, share_cta_scope='all_post_copy')))
        with tempfile.TemporaryDirectory() as tmp:
            for scope, refused in (('snackable', False), ('all_post_copy', True)):
                root = scoped_root(Path(tmp) / scope, scope)
                p = package(root / 'asset.bin', fmt='single-image')
                p.update(channel='x', account_url='https://x.com/therealkrisho', account_context='personal', share=None,
                         buffer_channel_id=BUFFER_CHANNEL_ID['x'], format='text', assets=[],
                         caption='Repost if your pilot never had a number.')
                try:
                    preflight(p, '2026-10-26', root=root)
                    raised = ''
                except ValueError as exc:
                    raised = str(exc)
                self.assertEqual('generic share call to action' in raised, refused, scope)
            bad = scoped_root(Path(tmp) / 'bad', 'everywhere')
            with self.assertRaisesRegex(ValueError, 'share_cta_scope'):
                load_rules(bad / 'social' / 'share.json')

    def test_daily_and_radar_drafts_follow_the_share_cta_scope(self):
        draft = {'platform': 'x', 'text': 'Who gets paid when the model is free? Repost if your pilot never had a number.'}
        for kind in ('daily', 'radar'):
            self.assertFalse(any('asks for the share' in e for e in problems(draft, kind)), kind)
        with patch.object(share_module, '_DEFAULT', [dict(load_rules(), share_cta_scope='all_post_copy')]):
            for kind in ('daily', 'radar'):
                self.assertTrue(any('asks for the share' in e for e in problems(draft, kind)), kind)
            self.assertFalse(any('asks for the share' in e for e in problems(dict(draft, text='Who gets paid?'), 'daily')))
            # The newsletter's own forward and refer rungs (hooks.json cta_ladder) are not post copy.
            self.assertFalse(any('asks for the share' in e for e in problems(draft, 'conversion')))

    def test_spec_words_refuse_a_share_cta(self):
        spec = json.loads((ROOT / 'specs' / 'fixtures' / 'w45-week.json').read_text(encoding='utf-8'))
        records = json.loads((ROOT / 'specs' / 'fixtures' / 'social-records.json').read_text(encoding='utf-8'))
        self.assertNotIn('share_cta', {e['code'] for e in lint(spec, records)['errors']})
        spec['slots'][0]['words'] += ' Send this to someone who is planning a pilot.'
        found = [e for e in lint(spec, records)['errors'] if e['code'] == 'share_cta']
        self.assertTrue(found)
        self.assertTrue(all(e['slot_id'] == spec['slots'][0]['slot_id'] for e in found))
        self.assertIn('send-this-to', ' '.join(e['message'] for e in found))


class SendTestTests(unittest.TestCase):
    def test_send_test_request_never_shows_the_share_block_or_a_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = package(Path(tmp) / 'asset.bin')
            request = send_test_request(p)
            blind = copy.deepcopy(p)
            blind['share'] = None
            self.assertEqual(request, send_test_request(blind))
            self.assertEqual(request, REQUEST, 'the same post in another folder is the same request')
            self.assertEqual(set(request), {'local_only', 'blind', 'reader_card', 'prompt', 'post', 'request_sha256'})
            self.assertEqual(set(request['post']), {'format', 'copy', 'assets'})
            self.assertEqual(request['post']['assets'], [{'name': 'asset-1.bin', 'sha256': p['assets'][0]['sha256']}])
            self.assertEqual(request['request_sha256'], request_digest(request['prompt'], request['post']))
            text = json.dumps(request)
            for field in ('sender', 'receiver', 'dm_line', 'moment'):
                self.assertNotIn(SHARE[field], text)
            for leak in (p['source_url'], 'synthetic-only', p['account_url'], 'Synthetic regression asset.', tmp):
                self.assertNotIn(leak, text)
            self.assertIn('would not send it', request['prompt'])
            self.assertIn('request_sha256', request['prompt'])
            self.assertTrue((ROOT / request['reader_card']).is_file())
            path = Path(tmp) / 'package.json'
            path.write_text(json.dumps(p), encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(command(['send-test', str(path)]), 0)
            self.assertNotIn(SHARE['dm_line'], out.getvalue())
            # Staging hands the reader one folder: the media under blind names and request.json, nothing else.
            folder = Path(tmp) / 'reader'
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command(['send-test', str(path), '--stage', str(folder)]), 0)
            self.assertEqual(sorted(f.name for f in folder.iterdir()), ['asset-1.bin', 'request.json'])
            self.assertEqual((folder / 'asset-1.bin').read_bytes(), Path(p['assets'][0]['path']).read_bytes())
            self.assertEqual(json.loads((folder / 'request.json').read_text(encoding='utf-8')), request)
            with self.assertRaisesRegex(ValueError, 'new or empty'):
                stage_send_test(p, folder)
            Path(p['assets'][0]['path']).write_bytes(b'changed after approval')
            with self.assertRaisesRegex(ValueError, 'do not match'):
                stage_send_test(p, Path(tmp) / 'other')

    def test_send_test_passes_only_on_matching_receiver_and_job(self):
        self.assertEqual(compare(SHARE, answer())['verdict'], 'pass')
        self.assertEqual(compare(SHARE, answer('my chief executive'))['verdict'], 'pass')
        self.assertEqual(compare(SHARE, answer('a CEO I report to'))['verdict'], 'pass')
        self.assertEqual(compare(dict(SHARE, receiver='the analyst on her team who builds the weekly report'),
                                 answer('a junior analyst I manage'))['verdict'], 'pass')
        wrong_job = compare(SHARE, answer(job='laugh_or_awe'))
        self.assertEqual(wrong_job['verdict'], 'revise')
        self.assertIn('laugh or awe, not to settles it', wrong_job['reasons'][0])
        wrong_person = compare(SHARE, answer('my sister'))
        self.assertEqual(wrong_person['verdict'], 'revise')
        self.assertIn('"my sister"', wrong_person['reasons'][0])
        self.assertEqual(wrong_person['reader_answer']['receiver'], 'my sister')
        topic_only = compare(SHARE, answer('the engineer running our AI pilot, who pays back nothing'))
        self.assertEqual(topic_only['verdict'], 'revise', 'context after the role never matches on a shared topic')
        rank_only = compare(dict(SHARE, receiver='the head of marketing'), answer('the head of sales'))
        self.assertEqual(rank_only['verdict'], 'revise')
        # One shared noun is not the same person: her own CEO is not a competitor's, a boss is not a
        # marketing manager, a co-founder is not a founder the reader mentors.
        for declared, named in (('her CEO', 'a CEO at a competitor'), ('a marketing manager', 'my boss'),
                                ('his co-founder', 'a founder I mentor')):
            result = compare(dict(SHARE, receiver=declared), answer(named))
            self.assertEqual(result['verdict'], 'revise', (declared, named))
        self.assertEqual((receiver_relation('her CEO'), receiver_relation('a CEO at a competitor'),
                          receiver_relation('a founder I mentor')), ('own', 'other', None))
        silent = compare(SHARE, answer(would_send=False))
        self.assertEqual((silent['verdict'], silent['reasons']), ('revise', ['the blind reader would not send it to anyone']))
        for bad in ({'would_send': 'yes'}, dict(answer(), job='viral'), dict(answer(), receiver=' '),
                    dict(answer(), rewrite='Try a punchier hook')):
            with self.assertRaises(ValueError):
                compare(SHARE, bad)
        with self.assertRaisesRegex(ValueError, 'does not recompute'):
            compare(SHARE, answer(), dict(REQUEST, post=dict(REQUEST['post'], copy='Edited copy.')))
        self.assertEqual(receiver_key('her CFO'), receiver_key('the finance director'))

    def test_an_answer_counts_only_for_the_request_it_was_given(self):
        stale = dict(answer(), request_sha256='0' * 64)
        with self.assertRaisesRegex(StaleSendTest, 'an earlier answer never carries over'):
            compare(SHARE, stale)
        unbound = answer()
        del unbound['request_sha256']
        with self.assertRaisesRegex(StaleSendTest, 'names no request_sha256'):
            compare(SHARE, unbound)

    def test_preflight_holds_until_a_matching_blind_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = package(Path(tmp) / 'asset.bin')
            result = preflight(p, '2026-10-26')
            self.assertIn('blind_send_test_required_before_krish_sees_it', result['holds'])
            self.assertIsNone(result['send_test'])
            self.assertEqual(result['send_test_request_sha256'], REQUEST['request_sha256'])
            passed = preflight(p, '2026-10-26', send_test=answer())
            self.assertNotIn('blind_send_test_required_before_krish_sees_it', passed['holds'])
            self.assertNotIn('blind_send_test_revise', passed['holds'])
            self.assertEqual(passed['send_test']['verdict'], 'pass')
            self.assertFalse(passed['publication_authorized'])
            revise = preflight(p, '2026-10-26', send_test=answer('my sister'))
            self.assertIn('blind_send_test_revise', revise['holds'])
            self.assertEqual(revise['send_test']['reader_answer']['receiver'], 'my sister')

    def test_a_revised_post_never_reuses_an_earlier_answer(self):
        # Must fail: change the caption and the dm_line, keep the answer, and the hold stays.
        with tempfile.TemporaryDirectory() as tmp:
            p = package(Path(tmp) / 'asset.bin')
            earlier = answer()
            self.assertEqual(preflight(p, '2026-10-26', send_test=earlier)['send_test']['verdict'], 'pass')
            p['caption'] = 'One number, agreed on day one, decides the pilot. Here is the second number too.'
            p['share']['dm_line'] = 'The six-week rule, now with the second number we argued about.'
            result = preflight(p, '2026-10-26', send_test=earlier)
            self.assertNotEqual(result['send_test_request_sha256'], REQUEST['request_sha256'])
            self.assertEqual(result['send_test']['verdict'], 'stale')
            self.assertIn('blind_send_test_required_before_krish_sees_it', result['holds'])
            self.assertNotIn('blind_send_test_revise', result['holds'])
            # A new byte in the asset is a new request too.
            p = package(Path(tmp) / 'asset.bin')
            Path(p['assets'][0]['path']).write_bytes(b'a revised synthetic asset')
            p['assets'][0]['sha256'] = hashlib.sha256(b'a revised synthetic asset').hexdigest()
            self.assertIn('blind_send_test_required_before_krish_sees_it',
                          preflight(p, '2026-10-26', send_test=earlier)['holds'])
            # The answer to this revision's own request passes again.
            fresh = answer(request=send_test_request(p))
            self.assertEqual(preflight(p, '2026-10-26', send_test=fresh)['send_test']['verdict'], 'pass')


class ShareMeasureTests(unittest.TestCase):
    def test_sends_and_saves_per_reach_are_the_snackable_measure(self):
        self.assertEqual(SNACKABLE_PRIMARY, ('sends_per_reach', 'saves_per_reach'))
        rates = share_rates('instagram', {'shares': 3, 'saves': 6, 'reach': 1200})
        self.assertEqual((rates['sends_per_reach'], rates['saves_per_reach']), (3 / 1200, 6 / 1200))
        self.assertEqual((rates['sends_per_1000_reached'], rates['saves_per_1000_reached']), (2.5, 5.0))
        self.assertIn('house hypothesis', rates['status'])
        self.assertEqual(rates['not_shown'], [])

    def test_unexposed_fields_are_not_shown_never_zero(self):
        # A repost is public amplification, never a one-to-one send: X shows no sends.
        x = share_rates('x', {'reposts': 2, 'impressions': 500})
        self.assertEqual((x['sends'], x['reach'], x['saves'], x['sends_per_reach']), (None, None, None, None))
        self.assertEqual(x['public_reposts'], 2)
        self.assertEqual(x['not_shown'], ['reach', 'sends', 'saves'])
        self.assertIsNone(share_rates('instagram', {'shares': 1, 'reach': 9})['public_reposts'])
        youtube = share_rates('youtube', {'views': 900})
        self.assertEqual(youtube['not_shown'], ['reach', 'sends', 'saves'])
        missing = share_rates('instagram', {'reach': 400})
        self.assertEqual((missing['sends'], missing['sends_per_reach']), (None, None))
        zero_reach = share_rates('tiktok', {'shares': 0, 'reach': 0})
        self.assertIsNone(zero_reach['sends_per_reach'])
        self.assertEqual(share_fields('threads')['status'], 'not_observed')
        with self.assertRaises(ValueError):
            share_rates('instagram', {'shares': -1, 'reach': 10})
        with self.assertRaises(ValueError):
            share_rates('myspace', {})


if __name__ == '__main__':
    unittest.main()
