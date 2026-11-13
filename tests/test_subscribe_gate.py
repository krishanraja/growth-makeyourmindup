"""The subscribe gate on every Buffer post (Ruling, Krish, 2026-11-12). Synthetic data only."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

from engine import subscribe_gate
from engine.buffer_channels import BUFFER_CHANNEL_ID, DENIED_CHANNELS

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://home.makeyourmindup.ai/subscribe'


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

    def test_an_edit_that_changes_no_words_passes(self):
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__edit_post', {'postId': 'a' * 24, 'mode': 'shareNext'}, 5), [])

    def test_other_tools_pass(self):
        self.assertEqual(subscribe_gate.errors('mcp__Buffer__list_posts', {}, 5), [])

    def test_the_hook_denies_through_claude_code(self):
        call = {'tool_name': 'mcp__Buffer__create_post', 'tool_input': post('threads', 'TEST FIXTURE ONLY.')}
        out = subprocess.run([sys.executable, str(ROOT / '.claude' / 'hooks' / 'buffer-subscribe-gate.py')],
                             input=json.dumps(call), capture_output=True, text=True, cwd=ROOT, check=True).stdout
        if out:  # the live urgency may sit below U4, when nothing is required
            self.assertEqual(json.loads(out)['hookSpecificOutput']['permissionDecision'], 'deny')

    def test_the_hook_is_registered(self):
        s = json.loads((ROOT / '.claude' / 'settings.json').read_text(encoding='utf-8'))
        commands = [h['command'] for m in s['hooks'].get('PreToolUse', []) for h in m['hooks']]
        self.assertTrue(any('buffer-subscribe-gate.py' in c for c in commands))

    def hook(self, stdin):
        return subprocess.run([sys.executable, str(ROOT / '.claude' / 'hooks' / 'buffer-subscribe-gate.py')],
                              input=stdin, capture_output=True, text=True, cwd=ROOT)

    def test_the_hook_fails_closed_on_input_it_cannot_read(self):
        for stdin in ('', 'not json', '[1, 2]', '"text"'):
            done = self.hook(stdin)
            self.assertEqual(done.returncode, 2, stdin)
            self.assertIn('refused', done.stderr)

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
