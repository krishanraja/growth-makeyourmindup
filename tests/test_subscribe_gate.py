"""The subscribe gate on every Buffer post (Ruling, Krish, 2026-11-12). Synthetic data only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from engine import owners, post_channels, subscribe_gate
from engine.buffer_channels import BUFFER_CHANNEL_ID, DENIED_CHANNELS, HANDED_OFF_CHANNELS

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://home.makeyourmindup.ai/subscribe'
LINKEDIN = next(cid for cid, channel in HANDED_OFF_CHANNELS.items() if channel == 'linkedin')
POST = 'a' * 24
# Buffer's edit_post as its schema has it (loaded, never called): postId, and never a channelId.
EDITS = ({'postId': POST, 'mode': 'shareNow'}, {'postId': POST, 'text': 'TEST FIXTURE ONLY. New words.'},
         {'postId': POST, 'mode': 'customScheduled', 'dueAt': '2026-11-20T09:00:00-05:00'},
         {'postId': POST, 'saveToDraft': False, 'mode': 'shareNow', 'schedulingType': 'automatic'},
         {'postId': POST, 'text': 'Read it: ' + PAGE + '?utm_source=linkedin&utm_medium=organic&utm_content=s'})


def hook(name, call, project=ROOT):
    """Run one of this tree's Claude Code hooks as Claude Code does, on the project named explicitly, so the test
    proves the tree it lives in whatever CLAUDE_PROJECT_DIR the shell around it holds."""
    return subprocess.run([sys.executable, str(Path(project) / '.claude' / 'hooks' / name)], input=json.dumps(call),
                          capture_output=True, text=True, cwd=str(project), check=True,
                          env=dict(os.environ, CLAUDE_PROJECT_DIR=str(project))).stdout


def tagged(source):
    return PAGE + '?utm_source=' + source + '&utm_medium=social&utm_campaign=growth&utm_content=test-slot'


def post(channel, text, **meta):
    call = {'channelId': BUFFER_CHANNEL_ID[channel], 'schedulingType': 'automatic', 'text': text}
    if meta:
        call['metadata'] = meta
    return call


class Gate(unittest.TestCase):
    def test_a_draft_without_the_tagged_link_is_refused(self):
        problems = subscribe_gate.errors('mcp__Buffer__create_post', post('threads', 'TEST FIXTURE ONLY. A plain post.'), 5)
        self.assertTrue(problems and problems[0].startswith('subscribe_route_missing:'), problems)

    def test_the_tagged_link_in_the_words_passes(self):
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', post('threads', 'Read it: ' + tagged('threads')), 5), [])

    def test_an_untagged_or_other_channel_link_is_refused(self):
        self.assertTrue(subscribe_gate.errors('mcp__Buffer__create_post', post('x', 'Read it: ' + PAGE), 5))
        self.assertTrue(subscribe_gate.errors('mcp__Buffer__create_post', post('x', 'Read it: ' + tagged('threads')), 5))

    def test_instagram_takes_the_first_comment(self):
        call = post('instagram', 'TEST FIXTURE ONLY.', instagram={'type': 'reel', 'shouldShareToFeed': True,
                                                                  'firstComment': 'Subscribe free: ' + tagged('instagram')})
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', call, 5), [])

    def test_instagram_may_point_to_the_profile_link(self):
        call = post('instagram', 'TEST FIXTURE ONLY. Subscribe free: link in bio.')
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', call, 5), [])

    def test_nothing_is_required_below_the_conversion_urgency(self):
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', post('threads', 'A plain post.'), 1), [])

    def test_other_ventures_channels_pass_untouched(self):
        call = {'channelId': next(iter(DENIED_CHANNELS)), 'schedulingType': 'automatic', 'text': 'Another venture.'}
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', call, 5), [])

    def test_krish_personal_linkedin_is_refused_at_every_urgency(self):
        # Ruling (Krish, 2026-11-13): growth-mindmake owns his personal LinkedIn. A create_post on its Buffer
        # channel id is refused outright, a tagged link or not.
        for urgency in (1, 3, 5, None):
            for text in ('TEST FIXTURE ONLY.', 'Read it: ' + tagged('linkedin')):
                call = {'channelId': LINKEDIN, 'schedulingType': 'automatic', 'text': text}
                [problem] = subscribe_gate.errors('mcp__Buffer__create_post', call, urgency)
                self.assertTrue(problem.startswith(owners.HOLD + ': Buffer channel ' + LINKEDIN + ': '), problem)
                self.assertIn(owners.refusal('linkedin'), problem)
        # An edit names only its post: one read on LinkedIn's channel is refused, whatever it changes, at every
        # urgency (publishing it now, new words, a new time, taking it out of drafts).
        for urgency in (1, 3, 5, None):
            for edit in EDITS:
                [problem] = subscribe_gate.errors('mcp__Buffer__edit_post', edit, urgency, posts={POST: LINKEDIN})
                self.assertEqual(problem, owners.HOLD + ': Buffer channel ' + LINKEDIN + ': ' + owners.refusal('linkedin'))
        # An edit carrying LinkedIn's own metadata is refused even before its post is known.
        edit = {'postId': POST, 'text': 'TEST FIXTURE ONLY.', 'metadata': {'linkedin': {'firstComment': 'More soon.'}}}
        [problem] = subscribe_gate.errors('mcp__Buffer__edit_post', edit, 1, posts={})
        self.assertIn(owners.refusal('linkedin'), problem)
        # His X and the publication's own channels keep the subscribe check alone.
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', post('x', 'Read it: ' + tagged('x')), 5), [])

    def test_an_edit_of_a_post_never_read_is_refused(self):
        # The gate cannot tell an unread post's channel, so it may be his LinkedIn: read it first.
        for urgency in (1, 5):
            for edit in EDITS:
                [problem] = subscribe_gate.errors('mcp__Buffer__edit_post', edit, urgency, posts={})
                self.assertTrue(problem.startswith(subscribe_gate.UNKNOWN + ': ' + subscribe_gate.UNREAD_POST), problem)
                self.assertIn("growth-mindmake's", problem)
        self.assertEqual(subscribe_gate.UNREAD_POST, 'read the post with get_post first, so its channel is known')
        # Reading it with get_post (the hook records its channel) lets the same edit through on his X.
        read = post_channels.from_call('mcp__Buffer__get_post', {'postId': POST},
                                       {'id': POST, 'channelId': BUFFER_CHANNEL_ID['x'], 'status': 'draft'})
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', EDITS[0], 5, posts=dict(read)), [])

    def test_the_hook_denies_a_linkedin_post_through_claude_code(self):
        call = {'tool_name': 'mcp__Buffer__create_post',
                'tool_input': {'channelId': LINKEDIN, 'schedulingType': 'automatic',
                               'text': 'TEST FIXTURE ONLY. Read it: ' + tagged('linkedin')}}
        decision = json.loads(hook('buffer-subscribe-gate.py', call))['hookSpecificOutput']  # whatever the urgency
        self.assertEqual(decision['permissionDecision'], 'deny')
        self.assertIn("growth-mindmake's", decision['permissionDecisionReason'])

    def test_the_hooks_read_a_post_then_refuse_its_edit_through_claude_code(self):
        # The two hooks together, in a copy of this tree: a get_post answer on LinkedIn's channel is recorded
        # after the call, and an edit of that post is then denied before it runs. Ids only reach the map.
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            ignore = shutil.ignore_patterns('__pycache__', '*.pyc')
            shutil.copytree(str(ROOT / 'engine'), str(project / 'engine'), ignore=ignore)
            shutil.copytree(str(ROOT / '.claude' / 'hooks'), str(project / '.claude' / 'hooks'), ignore=ignore)
            edit = {'tool_name': 'mcp__Buffer__edit_post', 'tool_input': {'postId': POST, 'mode': 'shareNow'}}
            before = json.loads(hook('buffer-subscribe-gate.py', edit, project))['hookSpecificOutput']
            self.assertIn(subscribe_gate.UNREAD_POST, before['permissionDecisionReason'])
            answer = [{'type': 'text', 'text': json.dumps({'post': {'id': POST, 'channelId': LINKEDIN, 'status': 'draft',
                                                                    'text': 'TEST FIXTURE ONLY. Private words.'}})}]
            out = hook('buffer-post-channels.py', {'tool_name': 'mcp__Buffer__get_post', 'tool_input': {'postId': POST},
                                                   'tool_response': answer}, project)
            self.assertEqual(out, '')
            stored = (project / post_channels.MAP).read_text(encoding='utf-8')
            self.assertEqual(json.loads(stored)['posts'], {POST: LINKEDIN})
            self.assertNotIn('Private words', stored)
            after = json.loads(hook('buffer-subscribe-gate.py', edit, project))['hookSpecificOutput']
            self.assertEqual(after['permissionDecision'], 'deny')
            self.assertIn(owners.refusal('linkedin'), after['permissionDecisionReason'])

    def test_an_edit_that_changes_no_words_passes(self):
        read = {POST: BUFFER_CHANNEL_ID['threads']}
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': POST, 'mode': 'shareNext'}, 5,
                                               posts=read), [])

    def test_every_allowed_edit_on_its_own_channels_still_passes_once_read(self):
        # Once the post was read, the edits this engine always made on its seven channels pass as before: a
        # reschedule, an asset swap, a move to drafts and words that do not speak for the publication.
        for channel, cid in BUFFER_CHANNEL_ID.items():
            for edit in EDITS[:4]:
                self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', edit, 5, posts={POST: cid}), [],
                                 (channel, edit))
        # New words that speak for the publication still need the tagged link, now checked on the post's own channel.
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': POST, 'text': 'makeyourmindup: '
                                               + tagged('x')}, 5, posts={POST: BUFFER_CHANNEL_ID['x']}), [])
        self.assertTrue(subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': POST, 'text': 'makeyourmindup, no link'},
                                              5, posts={POST: BUFFER_CHANNEL_ID['threads']}))
        # Another venture's post passes untouched, as before.
        other = next(iter(DENIED_CHANNELS))
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', EDITS[1], 5, posts={POST: other}), [])

    def test_other_tools_pass(self):
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__list_posts', {}, 5), [])

    def test_an_x_thread_is_read_under_buffers_twitter_key(self):
        # Buffer keeps X metadata under twitter (create_post schema: metadata.twitter.thread), never under x.
        first = 'TEST FIXTURE ONLY. Part one.'
        routed = post('x', first, twitter={'thread': [{'text': first}, {'text': 'Part two: ' + tagged('x')}]})
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', routed, 5), [])
        bare = post('x', first, twitter={'thread': [{'text': first}, {'text': 'Part two, no link.'}]})
        self.assertTrue(subscribe_gate.errors('mcp__Buffer__create_post', bare, 5))

    def test_a_threads_link_card_on_a_thread_item_counts_in_buffers_shape(self):
        card = {'text': 'Part two.', 'metadata': {'threads': {'linkAttachment': {'url': tagged('threads')}}}}
        call = post('threads', 'TEST FIXTURE ONLY.', threads={'thread': [{'text': 'TEST FIXTURE ONLY.'}, card]})
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__create_post', call, 5), [])


class Edits(unittest.TestCase):
    """Buffer's edit_post names a postId and never a channelId: the gate stays offline, never blocks another
    venture's post, and judges this engine's post by the channel the call names, never a default."""

    def edit(self, text, **meta):
        call = {'postId': 'a' * 24, 'text': text}
        if meta:
            call['metadata'] = meta
        return subscribe_gate.errors('mcp__Buffer__edit_post', call, 5)

    def test_a_routed_edit_passes_on_the_channel_its_route_names(self):
        self.assertEqual(self.edit('TEST FIXTURE ONLY. New words ' + tagged('x')), [])
        self.assertEqual(self.edit('TEST FIXTURE ONLY. New words ' + tagged('facebook')), [])

    def test_an_x_thread_edit_is_judged_as_x(self):
        self.assertEqual(self.edit('TEST FIXTURE ONLY. makeyourmindup', twitter={'thread': [
            {'text': 'TEST FIXTURE ONLY. makeyourmindup'}, {'text': 'More ' + tagged('x')}]}), [])
        problems = self.edit('TEST FIXTURE ONLY. makeyourmindup, no link', twitter={})
        self.assertTrue(problems and 'this x post' in problems[0], problems)

    def test_this_engines_routeless_edit_naming_no_channel_holds(self):
        problems = self.edit('TEST FIXTURE ONLY. makeyourmindup, new words and no link.')
        self.assertTrue(problems and problems[0].startswith('subscribe_route_missing:'), problems)
        self.assertNotIn('threads post', problems[0])
        below = subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': 'a' * 24,
                                                                 'text': 'makeyourmindup, no link.'}, 3)
        self.assertEqual(below, [], 'below the conversion urgency nothing is required')

    def test_an_edit_whose_channel_id_is_null_is_resolved_as_one_with_none(self):
        # A channelId present but null names no channel, as one left out does (reverifier, 13 Nov 2026: it passed).
        def edit(text):
            return subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': 'a' * 24, 'channelId': None,
                                                                    'text': text}, 5)
        problems = edit('TEST FIXTURE ONLY. makeyourmindup, new words and no link.')
        self.assertTrue(problems and problems[0].startswith('subscribe_route_missing:'), problems)
        self.assertEqual(edit('TEST FIXTURE ONLY. New words ' + tagged('x')), [])
        self.assertEqual(edit('TEST FIXTURE ONLY. Another venture, new words.'), [])

    def test_another_ventures_edit_is_never_blocked(self):
        self.assertEqual(self.edit('TEST FIXTURE ONLY. Another venture, new words.'), [])
        self.assertEqual(self.edit('TEST FIXTURE ONLY. New caption.', instagram={'type': 'post', 'firstComment': ''}), [])
        self.assertEqual(self.edit('TEST FIXTURE ONLY. makeyourmindup', pinterest={'title': 'Synthetic'}), [])
        call = {'postId': 'a' * 24, 'channelId': next(iter(DENIED_CHANNELS)), 'text': 'makeyourmindup, no link.'}
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', call, 5), [])

    def test_the_hook_denies_through_claude_code(self):
        call = {'tool_name': 'mcp__Buffer__create_post', 'tool_input': post('threads', 'TEST FIXTURE ONLY.')}
        out = hook('buffer-subscribe-gate.py', call)
        if out:  # the live urgency may sit below U4, when nothing is required
            self.assertEqual(json.loads(out)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_the_hook_is_registered(self):
        s = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        commands = [h['command'] for m in s['hooks'].get('PreToolUse', []) for h in m['hooks']]
        self.assertTrue(any('buffer-subscribe-gate.py' in c for c in commands))
        after = [(m['matcher'], h['command']) for m in s['hooks'].get('PostToolUse', []) for h in m['hooks']]
        self.assertTrue(any('buffer-post-channels.py' in c and all(t in m for t in post_channels.TOOLS)
                            for m, c in after), after)

    def hook(self, stdin):
        return subprocess.run([sys.executable, str(ROOT / '.claude' / 'hooks' / 'buffer-subscribe-gate.py')],
                              input=stdin, capture_output=True, text=True, cwd=ROOT)

    def test_the_hook_fails_closed_on_input_it_cannot_read(self):
        for stdin in ('', 'not json', '[1, 2]', '"text"'):
            done = self.hook(stdin)
            self.assertEqual(done.returncode, 2, stdin)
            self.assertIn('refused', done.stderr)

    def test_the_hook_refuses_a_call_whose_tool_or_input_it_cannot_read(self):
        # 'A call it cannot check is refused': a tool name that is not text, or a create or edit whose input is
        # not an object, used to pass with exit 0.
        for call in ({'tool_name': 5}, {'tool_name': None, 'tool_input': {}},
                     {'tool_name': 'mcp__Buffer__create_post', 'tool_input': 'TEST FIXTURE ONLY.'},
                     {'tool_name': 'mcp__Buffer__edit_post', 'tool_input': ['TEST FIXTURE ONLY.']}):
            done = self.hook(json.dumps(call))
            self.assertEqual(done.returncode, 2, call)
            self.assertIn('refused', done.stderr)
        done = self.hook(json.dumps({'tool_name': 'mcp__Buffer__list_posts', 'tool_input': 'anything'}))
        self.assertEqual((done.returncode, done.stdout), (0, ''))

    def test_the_hook_fails_closed_when_the_gate_breaks(self):
        # metadata that is not an object breaks the gate's own reading of an engine post: refused, never passed.
        call = post('threads', 'TEST FIXTURE ONLY.')
        call['metadata'] = 'not an object'
        from engine import intensity
        done = self.hook(json.dumps({'tool_name': 'mcp__Buffer__create_post', 'tool_input': call}))
        if intensity.subscribe_required(intensity.state()['urgency']):
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
            self.assertIn('AttributeError', done.stderr)
        else:  # below U4 nothing is read, so nothing can break
            self.assertEqual((done.returncode, done.stdout), (0, ''))

    def test_the_registered_command_fails_closed_with_no_python(self):
        s = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        command = next(h['command'] for m in s['hooks'].get('PreToolUse', []) for h in m['hooks']
                       if 'buffer-subscribe-gate.py' in h['command'])
        self.assertTrue(command.rstrip().endswith('|| exit 2'), command)
        bash = next((p for p in ('/bin/bash', '/usr/bin/bash') if Path(p).exists()), None)
        if bash is None:
            self.skipTest('no bash here')
        done = subprocess.run([bash, '--noprofile', '--norc', '-c', command], input='{}', capture_output=True,
                              text=True, env={'PATH': '/nonexistent', 'CLAUDE_PROJECT_DIR': str(ROOT)})
        self.assertEqual(done.returncode, 2)


if __name__ == '__main__':
    unittest.main()
