"""Sessions and handoffs across the four engines (engine/engines/core.py).

Krish, 5 Nov 2026: every session reports what it would do better next time, one session works on one engine,
and work that belongs to another engine is recommended as a handoff he can paste into that engine's session.
Each test writes into a temp root carrying the committed contracts and records.
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import growth
from engine.engines import core

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-05'
REVIEW = {'kind': 'review', 'ref': 'docs/reviews/2026-11-05-growth-engine-review.md', 'observed_at': NOW}
GOOD = ['Read the Buffer queue before drafting so the slot list matches what is actually scheduled']
OTHER = ['Open the public Short in a logged-out window before recording the continuation check']


def learnings(**changes):
    value = {'session_ref': 'https://chatgpt.com/codex/tasks/task-1', 'did': ['Scheduled the Monday edition'],
             'better_next_time': list(GOOD), 'worked': ['The route lookup named the hold at once']}
    value.update(changes)
    return value


def edition(rid='ed-monday-x'):
    return {'id': rid, 'engine': 'publishing', 'kind': 'edition', 'title': 'Monday edition on X',
            'state': 'scheduled', 'source': REVIEW, 'next_owner': 'publishing',
            'next_action': 'read back the reader view once it goes live', 'revisit_when': 'after the slot',
            'links': [], 'updated_at': NOW, 'opportunity_id': 'opp-monday',
            'detail': {'channel': 'x', 'format': 'short-video', 'route': 'buffer',
                       'payload_sha256': core.digest('synthetic approved edition'), 'post_id': 'post-1',
                       'due_on': NOW}}


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        shutil.copytree(ROOT / 'engines', self.root / 'engines')
        (self.root / 'jobs').mkdir()
        for name in core.ENGINES:
            (self.root / 'jobs' / (name + '.md')).write_text('# Job\n', encoding='utf-8')

    def write(self, value, name='learnings.json'):
        path = self.root / '.scratch' / 'engines' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')
        return str(path)

    def cli(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = growth.main(['engine'] + list(argv) + ['--root', str(self.root), '--now', NOW])
        text = buffer.getvalue()
        value, end = json.JSONDecoder().raw_decode(text)
        return code, value, text[end:]

    def handoff(self, frm='publishing', to='measurement', **extra):
        return core.handoff(frm, to, extra.get('what', 'Read the measured results at the judge window'),
                            'Measurement judges results; Publishing only checks the reader view',
                            extra.get('links', ()), None, extra.get('to_session'), self.root, NOW)

    # close --------------------------------------------------------------------------------------------------

    def test_close_refuses_missing_and_weak_learnings(self):
        for weak in (None, [], ['none'], ['Nothing'], ['too short to say'], ['Nothing, it all went fine today'],
                     ['Next time I would be more careful overall.'], ['  Be more efficient, going forward!  '],
                     GOOD + [GOOD[0].upper()],
                     # Filler that only matched when it was the whole line (verifier, 5 Nov 2026).
                     ['Everything went well, nothing to change at all'],
                     ['No issues this session, all tasks were completed'],
                     ['Next time I would be more careful with everything overall'],
                     ['Be more careful and thorough when doing the work'],
                     ['Double check everything before scheduling posts'],
                     ['Communicate better with Krish about the plan and timing'],
                     ['I think the session went quite well on the whole'],
                     ['Nope, the session was fine as it went'],
                     ['Keep doing what I did this session, it worked']):
            value = learnings(better_next_time=weak)
            if weak is None:
                del value['better_next_time']
            with self.assertRaises(ValueError, msg=repr(weak)):
                core.close('publishing', value, self.root, NOW)
        self.assertEqual(core.load('publishing', self.root, private=False).get('session-publishing-2026-11-05-1'),
                         None)
        with self.assertRaises(ValueError):
            self.cli('close', 'publishing', '--learnings', self.write(learnings(better_next_time=['none'])))

    def test_close_writes_a_session_record_that_start_shows(self):
        code, report, text = self.cli('close', 'publishing', '--learnings', self.write(learnings()))
        self.assertEqual(code, 0)
        session = report['session']
        self.assertEqual((session['id'], session['kind'], session['state']),
                         ('session-publishing-2026-11-05-1', 'session', 'closed'))
        self.assertEqual(session['source'], {'kind': 'session', 'ref': session['id'], 'observed_at': NOW})
        self.assertIn('What I would do better next time:\n- ' + GOOD[0], text)
        self.assertIn('Handoffs: none.', text)
        self.assertEqual(core.check(self.root), [])
        start = core.start('publishing', self.root, NOW)
        self.assertEqual(start['last_learnings'],
                         [{'id': session['id'], 'date': NOW, 'better_next_time': GOOD}])
        self.assertEqual(start['this_session']['engine'], 'publishing')
        self.assertIn('One engine per session', start['this_session']['rule'])
        self.assertIn('python growth.py engine close publishing --learnings FILE', start['this_session']['rule'])
        core.close('publishing', learnings(better_next_time=OTHER), self.root, NOW)
        self.assertEqual([x['id'][-1] for x in core.start('publishing', self.root, NOW)['last_learnings']],
                         ['1', '2'])

    def test_a_repeated_learning_is_refused_until_promoted(self):
        core.close('publishing', learnings(), self.root, NOW)
        again = learnings(better_next_time=['  ' + GOOD[0].lower().replace(' ', '   ') + ' '])
        with self.assertRaises(ValueError) as caught:
            core.close('publishing', again, self.root, NOW)
        self.assertIn('Promote it into engines/publishing.json or jobs/publishing.md', str(caught.exception))
        with self.assertRaises(ValueError):  # a trailing full stop is still the same learning
            core.close('publishing', learnings(better_next_time=[GOOD[0] + '.']), self.root, NOW)
        with self.assertRaises(ValueError) as caught:  # the job exists but the learning is not written in it
            core.close('publishing', dict(again, promoted=[{'learning': GOOD[0], 'to': 'jobs/publishing.md'}]),
                       self.root, NOW)
        self.assertIn('not written there yet', str(caught.exception))
        (self.root / 'jobs' / 'publishing.md').write_text('# Job\n\n- ' + GOOD[0].replace(' so ', '\n  so ')
                                                          + '.\n', encoding='utf-8')
        for bad in ('jobs/missing.md', 'docs/README.md', '../outside.md'):
            with self.assertRaises(ValueError, msg=bad):
                core.close('publishing', dict(again, promoted=[{'learning': GOOD[0], 'to': bad}]), self.root, NOW)
        (self.root / 'docs').mkdir()
        (self.root / 'docs' / 'README.md').write_text('x', encoding='utf-8')
        with self.assertRaises(ValueError):  # exists, but is not where a repeated learning is promoted
            core.close('publishing', dict(again, promoted=[{'learning': GOOD[0], 'to': 'docs/README.md'}]),
                       self.root, NOW)
        report = core.close('publishing', dict(again, promoted=[{'learning': GOOD[0], 'to': 'jobs/publishing.md'}]),
                            self.root, NOW)
        self.assertEqual(report['session']['detail']['promoted'][0]['to'], 'jobs/publishing.md')
        lessons = self.root / 'social' / 'lessons'
        lessons.mkdir(parents=True)
        (lessons / 'queue-first.json').write_text(json.dumps({'lesson': GOOD[0]}), encoding='utf-8')
        core.close('publishing', dict(again, promoted=[{'learning': GOOD[0], 'to': 'social/lessons/queue-first.json'}]),
                   self.root, NOW)
        self.assertEqual(core.check(self.root), [])

    # handoff ------------------------------------------------------------------------------------------------

    def test_handoff_appends_to_the_target_queue_and_prints_the_paste_message(self):
        with self.assertRaises(ValueError):
            self.handoff('publishing', 'publishing')
        with self.assertRaises(ValueError):
            self.handoff(links=['no-such-record'])
        code, record, text = self.cli('handoff', 'publishing', 'measurement', '--what', 'Read the measured results',
                                      '--why', 'Measurement judges results')
        self.assertEqual(code, 0)
        self.assertEqual(record['id'], 'handoff-publishing-to-measurement-2026-11-05-1')
        self.assertEqual((record['engine'], record['state'], record['next_owner']), ('measurement', 'open',
                                                                                    'measurement'))
        self.assertEqual(record['detail']['first_command'], 'python growth.py engine start measurement')
        self.assertEqual(record['detail']['from_session'], 'session-publishing-2026-11-05-1')
        self.assertIn(record['id'], core.load('measurement', self.root, private=False))
        self.assertNotIn(record['id'], core.load('publishing', self.root, private=False))
        message = ('Run Measurement. Pick up handoff ' + record['id'] + ' from Publishing: Read the measured results.'
                   ' First: git pull, then python growth.py engine start measurement.')
        self.assertIn(message, text)
        self.assertIn('Ask Krish first, exactly:\n\n    Do you have a session running for the Measurement & Allocation'
                      ' engine? If so, paste its link. If not, spin one up and tell me which it is, or I\'ll create'
                      ' one myself.', text)
        self.assertIn(message + ' When it is done, report back here.', text)
        link = 'https://chatgpt.com/codex/tasks/task-measure'
        code, record, text = self.cli('handoff', 'publishing', 'measurement', '--what', 'Read the measured results',
                                      '--why', 'Measurement judges results', '--to-session', link)
        self.assertEqual(record['id'][-1], '2')
        self.assertEqual(record['detail']['to_session_ref'], link)
        self.assertIn('Send this to your Measurement & Allocation session at ' + link + ':', text)
        self.assertEqual(core.check(self.root), [])

    def test_the_handoff_says_to_push_its_record_before_the_message_is_sent(self):
        push = ('Before sending it, commit engines/records/measurement.jsonl to main and push: the Measurement &'
                ' Allocation session finds this handoff only after git pull.')
        for extra in ((), ('--to-session', 'https://chatgpt.com/codex/tasks/task-measure')):
            code, record, text = self.cli('handoff', 'publishing', 'measurement', '--what', 'Judge Tuesday',
                                          '--why', 'Measurement judges results', *extra)
            self.assertEqual(code, 0)
            self.assertIn(push, text)
            self.assertLess(text.index(push), text.index('Pick up handoff ' + record['id']))
            self.assertEqual(core.handoff_message(record, self.root)['push'], push)
        for job in ('publishing', 'measurement', 'acquisition', 'engagement'):
            words = ' '.join((Path(core.ROOT) / 'jobs' / (job + '.md')).read_text(encoding='utf-8').split()).lower()
            self.assertIn('commit and push the new handoff line before sending the message', words, job)
        agents = ' '.join((Path(core.ROOT) / 'AGENTS.md').read_text(encoding='utf-8').split())
        self.assertIn('commits and pushes the handoff line before it sends the message', agents)

    def test_the_target_starts_with_its_oldest_inbound_handoff(self):
        first = self.handoff(what='Read the X results at 48 hours')
        self.handoff(what='Read the Substack results at 7 days')
        start = core.start('measurement', self.root, NOW)
        self.assertEqual([h['id'] for h in start['inbound_handoffs']], [first['id'], first['id'][:-1] + '2'])
        self.assertEqual(start['next_action']['id'], first['id'])
        self.assertIn('Read the X results at 48 hours', start['next_action']['next_action'])
        self.assertEqual(core.start('publishing', self.root, NOW)['inbound_handoffs'], [])

    def test_close_refuses_an_unlisted_handoff_and_a_foreign_one(self):
        made = self.handoff()
        with self.assertRaises(ValueError) as caught:
            core.close('publishing', learnings(), self.root, NOW)
        self.assertIn('not listed: ' + made['id'], str(caught.exception))
        for bad in (['handoff-nope'], [self.handoff('engagement', 'acquisition')['id']]):
            with self.assertRaises(ValueError):
                core.close('publishing', learnings(handoffs=[made['id']] + bad), self.root, NOW)
        report = core.close('publishing', learnings(handoffs=[made['id']]), self.root, NOW)
        self.assertEqual(report['session']['id'], made['detail']['from_session'])
        self.assertEqual(report['session']['links'], [made['id']])
        self.assertIn('Run Measurement. Pick up handoff ' + made['id'], report['handoffs'][0]['message'])
        text = core.report_text(report, self.root)
        self.assertIn('    Run Measurement. Pick up handoff ' + made['id'], text)
        # A later session the same day need not list what an earlier session already reported.
        core.close('publishing', learnings(better_next_time=OTHER), self.root, NOW)

    # done ---------------------------------------------------------------------------------------------------

    def test_done_closes_the_handoff_in_the_target_only(self):
        made = self.handoff()
        with self.assertRaises(ValueError) as caught:
            core.done('publishing', made['id'], 'not mine', self.root, NOW)
        self.assertIn('measurement\'s record', str(caught.exception))
        with self.assertRaises(ValueError):
            core.done('measurement', made['id'], '', self.root, NOW)
        code, closed, _ = self.cli('done', 'measurement', made['id'], '--note', 'Read at 48 hours; recorded')
        self.assertEqual((code, closed['state'], closed['detail']['done_note']), (0, 'closed',
                                                                                 'Read at 48 hours; recorded'))
        self.assertEqual([r['state'] for r in core.history('measurement', made['id'], self.root)], ['open', 'closed'])
        self.assertEqual(core.start('measurement', self.root, NOW)['inbound_handoffs'], [])
        with self.assertRaises(ValueError):
            core.done('measurement', made['id'], 'again', self.root, NOW)
        core.append('publishing', edition(), self.root)
        with self.assertRaises(ValueError):  # an edition closes only through close_edition
            core.done('publishing', 'ed-monday-x', 'scheduled', self.root, NOW)
        self.assertEqual(core.check(self.root), [])

    def test_done_never_closes_a_batch_at_krishs_approval_gate(self):
        gated = 'acq-outreach-batch-pending-approval'
        before = core.load('acquisition', self.root, private=False)[gated]
        with self.assertRaises(ValueError) as caught:
            self.cli('done', 'acquisition', gated, '--note', 'closing it')
        self.assertIn('waits on Krish', str(caught.exception))
        # Even with another owner, Acquisition's own admission refuses a plain close at the gate.
        core.append('acquisition', dict(before, id='acq-outreach-gated-two', next_owner='acquisition'), self.root)
        with self.assertRaises(ValueError) as caught:
            core.done('acquisition', 'acq-outreach-gated-two', 'closing it', self.root, NOW)
        self.assertIn("approval gate", str(caught.exception))
        self.assertEqual(core.load('acquisition', self.root, private=False)[gated], before)
        pending = core.start('acquisition', self.root, NOW)['recover']['outstanding_approvals']
        self.assertIn(gated, [r['id'] for r in pending])

    # privacy -------------------------------------------------------------------------------------------------

    def test_no_url_in_a_committed_handoff_or_session(self):
        post = 'https://www.linkedin.com/posts/someone-activity-123'
        with self.assertRaises(ValueError) as caught:
            self.handoff('acquisition', 'engagement', what='Comment on ' + post + ' with the approved angle')
        self.assertIn('no URL in a committed handoff', str(caught.exception))
        with self.assertRaises(ValueError):
            self.handoff('acquisition', 'engagement', what='Comment on www.linkedin.com/posts/x with the angle')
        self.assertNotIn('linkedin.com', (self.root / 'engines' / 'records' / 'engagement.jsonl')
                         .read_text(encoding='utf-8'))
        for key in ('did', 'worked'):
            with self.assertRaises(ValueError, msg=key):
                core.close('publishing', learnings(**{key: ['Scheduled the edition at ' + post]}), self.root, NOW)
        with self.assertRaises(ValueError):
            core.close('publishing', learnings(better_next_time=[GOOD[0] + ' at ' + post]), self.root, NOW)
        # The session links themselves are allowed.
        made = self.handoff(to_session='https://chatgpt.com/codex/tasks/task-measure')
        core.close('publishing', learnings(handoffs=[made['id']]), self.root, NOW)
        self.assertEqual(core.check(self.root), [])

    # session links, private --------------------------------------------------------------------------------

    def test_the_registry_lives_under_scratch_and_the_cli_sets_shows_and_clears_it(self):
        link = 'https://chatgpt.com/codex/tasks/task-measure'
        code, entry, _ = self.cli('session', 'set', 'measurement', link)
        self.assertEqual((code, entry), (0, {'ref': link, 'set_at': NOW, 'set_by_session': None}))
        path = self.root / '.scratch' / 'engines' / 'sessions.json'
        self.assertEqual(path, self.root / core.SESSIONS_FILE)
        self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['measurement']['ref'], link)
        self.assertFalse(any(link in f.read_text(encoding='utf-8')
                             for f in (self.root / 'engines' / 'records').glob('*')))
        self.assertEqual(self.cli('session', 'show')[1], {'measurement': entry})
        self.assertEqual(self.cli('session', 'show', 'measurement')[1], entry)
        self.assertEqual(self.cli('session', 'clear', 'measurement')[1], {'cleared': 'measurement', 'was': entry})
        self.assertEqual(core.load_sessions(self.root), {})
        with self.assertRaises(ValueError):
            core.set_session('measurement', 'two\nlines', self.root, NOW)
        self.assertEqual(core.check(self.root), [])

    def test_start_with_session_records_my_session_ref(self):
        before = core.start('publishing', self.root, NOW)
        self.assertEqual((before['my_session_ref'], before['known_sessions']), (None, {}))
        self.assertFalse((self.root / core.SESSIONS_FILE).exists())  # start without --session writes nothing
        link = 'https://chatgpt.com/codex/tasks/task-publish'
        code, value, _ = self.cli('start', 'publishing', '--session', link)
        self.assertEqual(value['my_session_ref'], link)
        self.assertEqual(value['known_sessions']['publishing'],
                         {'ref': link, 'set_at': NOW, 'set_by_session': 'session-publishing-2026-11-05-1'})
        other = core.start('measurement', self.root, NOW)
        self.assertEqual((other['my_session_ref'], other['known_sessions']['publishing']['ref']), (None, link))

    def test_handoff_asks_to_confirm_a_known_session(self):
        link = 'https://chatgpt.com/codex/tasks/task-measure'
        core.set_session('measurement', link, self.root, NOW)
        made = self.handoff()
        self.assertIsNone(made['detail']['to_session_ref'])
        m = core.handoff_message(made, self.root)
        self.assertEqual(m['question'], 'Is ' + link + ' still your Measurement & Allocation session? Say yes, paste'
                                        ' another link, or I\'ll create a new one.')
        self.assertIn('Ask Krish first, exactly:\n\n    ' + m['question'], core.handoff_text(made, self.root))

    def test_to_session_records_the_registry_and_addresses_the_message(self):
        mine, theirs = 'https://chatgpt.com/codex/tasks/task-publish', 'https://chatgpt.com/codex/tasks/task-measure'
        code, made, text = self.cli('handoff', 'publishing', 'measurement', '--what', 'Read the measured results',
                                    '--why', 'Measurement judges results', '--to-session', theirs,
                                    '--from-session', mine)
        self.assertEqual((made['detail']['to_session_ref'], made['detail']['from_session_ref']), (theirs, mine))
        registry = core.load_sessions(self.root)
        self.assertEqual((registry['measurement']['ref'], registry['publishing']['ref']), (theirs, mine))
        self.assertEqual(registry['measurement']['set_by_session'], made['detail']['from_session'])
        self.assertNotIn('Ask Krish', text)
        self.assertIn('Send this to your Measurement & Allocation session at ' + theirs + ':', text)
        self.assertIn('First: git pull, then python growth.py engine start measurement. When it is done, report back'
                      ' to the Publishing session at ' + mine + '.', text)
        # A later handoff from the same engine finds its own link in the registry.
        later = self.handoff(what='Read the Substack results at 7 days')
        self.assertEqual(later['detail']['from_session_ref'], mine)
        self.assertEqual(core.check(self.root), [])

    def test_done_on_a_handoff_reports_back_to_the_from_session(self):
        mine = 'https://chatgpt.com/codex/tasks/task-publish'
        core.set_session('publishing', mine, self.root, NOW)
        made = self.handoff()
        code, closed, text = self.cli('done', 'measurement', made['id'], '--note', 'Read at 48 hours; recorded',
                                      '--next', 'hold the Wednesday slot until the read is in')
        self.assertEqual((code, closed['state']), (0, 'closed'))
        self.assertIn('Commit engines/records/measurement.jsonl to main and push first, so the Publishing session'
                      ' sees the closed handoff after git pull. Then send this report back to the Publishing session'
                      ' at ' + mine + ' with the Codex tools available, or give it to Krish to paste there:', text)
        self.assertIn('Measurement & Allocation finished handoff ' + made['id'] + ': Read at 48 hours; recorded.'
                      ' Next for Publishing: hold the Wednesday slot until the read is in.', text)
        self.assertEqual(core.check(self.root), [])

    def test_committed_records_allow_session_links_only_in_their_fields(self):
        link = 'https://chatgpt.com/codex/tasks/task-measure'
        made = self.handoff(to_session=link)
        bad = dict(made, id=made['id'][:-1] + '9', detail=dict(made['detail'], why_not_here='See ' + link))
        self.assertTrue(any('no URL in a committed handoff' in e for e in core.validate(bad)))
        bad = dict(made, id=made['id'][:-1] + '9', detail=dict(made['detail'], session_link=link))
        self.assertTrue(core.validate(bad))
        good = dict(made, detail=dict(made['detail'], from_session_ref=link))
        self.assertEqual(core.validate(good), [])

    # Krish's example, end to end ---------------------------------------------------------------------------

    def test_publishing_schedules_then_hands_the_results_to_measurement(self):
        core.append('publishing', edition(), self.root)
        code, made, text = self.cli('handoff', 'publishing', 'measurement', '--what',
                                    'Judge the Monday X edition at its 48 hour window', '--why',
                                    'Publishing checks the reader view; measured results are Measurement\'s',
                                    '--link', 'ed-monday-x')
        self.assertEqual((made['links'], made['opportunity_id']), (['ed-monday-x'], 'opp-monday'))
        self.assertIn('Pick up handoff ' + made['id'] + ' from Publishing', text)
        code, report, text = self.cli('close', 'publishing', '--learnings',
                                      self.write(learnings(handoffs=[made['id']])))
        self.assertEqual(code, 0)
        self.assertIn('Still open in publishing:\n- ed-monday-x (scheduled)', text)
        self.assertIn('Run Measurement. Pick up handoff ' + made['id'], text)
        start = core.start('measurement', self.root, NOW)
        self.assertEqual(start['inbound_handoffs'][0]['id'], made['id'])
        self.assertEqual(start['next_action']['id'], made['id'])
        self.assertEqual(core.check(self.root), [])


    def test_two_checkouts_taking_the_same_session_id_is_reported_not_overwritten(self):
        with contextlib.redirect_stdout(io.StringIO()):
            core.close('publishing', learnings(), root=self.root, now=NOW)
        records = self.root / 'engines' / 'records' / 'publishing.jsonl'
        lines = records.read_text(encoding='utf-8').splitlines()
        session = [line for line in lines if '"kind": "session"' in line or '"kind":"session"' in line][-1]
        records.write_text('\n'.join(lines + [session]) + '\n', encoding='utf-8')
        self.assertTrue(any('opened twice' in e for e in core.check(self.root)))


class CommittedSessionRulesTests(unittest.TestCase):
    def test_every_contract_names_the_session_rule(self):
        for name in core.ENGINES:
            contract = core.load_contract(name, ROOT)
            permitted = ' '.join(contract['permitted_actions'])
            self.assertIn('python growth.py engine handoff', permitted)
            self.assertIn('python growth.py engine close ' + name, permitted)
            self.assertIn("doing another engine's work in this session", contract['forbidden_actions'])
            self.assertIn('a session record with what to do better next time, and every cross-engine item handed off',
                          contract['done'])
            job = ' '.join((ROOT / 'jobs' / (name + '.md')).read_text(encoding='utf-8').split())
            for needle in ('## This session', '## Close', 'python growth.py engine close ' + name,
                           'Never do the other engine\'s work in this session'):
                self.assertIn(needle, job, name + ': ' + needle)
            for needle in ('python growth.py engine start ' + name + ' --session', 'Do you have a session running',
                           'python growth.py engine session set', 'without waiting', 'report-back'):
                self.assertIn(needle, job, name + ': ' + needle)
            for needle in ('python growth.py engine session set', 'Codex session for another engine'):
                self.assertIn(needle, permitted, name + ': ' + needle)
            self.assertLess(len((ROOT / 'jobs' / (name + '.md')).read_text(encoding='utf-8').splitlines()), 125)

    def test_outreach_belongs_to_acquisition_not_control_center(self):
        contract = json.dumps(core.load_contract('acquisition', ROOT))
        job = ' '.join((ROOT / 'jobs' / 'acquisition.md').read_text(encoding='utf-8').split())
        for text in (contract, job):
            self.assertIn('approval_digest', text)
            self.assertIn('Mindmake', text)
        self.assertIn('nothing goes to Control Center', job)
        engagement = ' '.join((ROOT / 'jobs' / 'engagement.md').read_text(encoding='utf-8').split())
        self.assertIn('explicit approval of the exact text', engagement)


if __name__ == '__main__':
    unittest.main()
