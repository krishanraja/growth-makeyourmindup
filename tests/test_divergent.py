"""divergent-thinker on call (engine/divergent.py): dormant until served, never while held, the walls and the copy lint
before any spark is proposed, a refusal is a quiet line, and the mix plan flags a repeated hook. Synthetic words only."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from engine import divergent, mix
from engine.control_center import Client, ProtocolError, validate_report

NOW = '2026-11-18T12:00:00Z'
GAP = {'week_of': '2026-11-16', 'week_target': 271, 'current': 0, 'as_of': '2026-11-15', 'urgency': 5,
       'reason': 'under 40 of the target two weeks running'}
RUN = 'dt_run_synthetic'


def spark(rank, title, step='Pick one editor and write one note'):
    return {'rank': rank, 'title': title, 'mechanism': 'Synthetic mechanism for the fixture',
            'whyNonObvious': 'Synthetic reason it is not the obvious play', 'firstStep': step, 'lens': 'inversion',
            'kind': 'partnership', 'conventionalTwin': 'Post more', 'survivedAttack': True, 'score': 0.7,
            'remoteness': 0.6, 'judge': None, 'prompt': None}


SPARKS = [spark(1, 'Run a giveaway for anyone who subscribes this week'),
          spark(2, 'Trade one reader question with one editor you name'),
          spark(3, 'Open a reading room for one chapter each week')]


class FakeCC:
    def __init__(self, features=None, error=None, answer=None, cap_error=None):
        self.features, self.error, self.answer, self.cap_error = features, error, answer, cap_error
        self.calls = []

    def capabilities(self):
        self.calls.append('capabilities')
        if self.cap_error:
            raise self.cap_error
        return {'ok': True, 'features': self.features or {}}

    def divergent(self, body):
        self.calls.append(body)
        if self.error:
            raise self.error
        return self.answer or {'ok': True}


def served(**answer):
    return FakeCC({'divergent': True}, answer={'ok': True, **answer})


class Gate(unittest.TestCase):
    def test_flag_off_or_absent_means_no_call_and_a_quiet_line(self):
        for features in (None, {'divergent': False}, {'humour': True}, {'divergent': 'yes'}):
            cc = FakeCC(features)
            play, lines, holds = divergent.recovery(cc, {}, GAP, {}, NOW)
            self.assertIsNone(play)
            self.assertEqual(lines, [divergent.NOT_SERVED])
            self.assertEqual(holds, [])
            self.assertEqual(cc.calls, ['capabilities'])  # read the flag, called nothing
        unreadable = FakeCC(cap_error=ProtocolError('unreachable'))
        self.assertEqual(divergent.recovery(unreadable, {}, GAP, {}, NOW)[1], [divergent.NOT_SERVED])
        self.assertFalse(divergent.served(None))

    def test_held_or_calm_or_unread_ledger_or_a_waiting_play_asks_nothing(self):
        cc = served(sparks=SPARKS, runId=RUN)
        self.assertEqual(divergent.recovery(cc, {}, GAP, {}, NOW, held=True), (None, [], []))
        self.assertEqual(divergent.recovery(cc, {}, dict(GAP, urgency=3), {}, NOW), (None, [], []))
        self.assertEqual(divergent.recovery(cc, {}, dict(GAP, urgency=None), {}, NOW), (None, [], []))
        self.assertEqual(divergent.recovery(cc, {}, GAP, None, NOW), (None, [], []))
        waiting = {divergent.PROPOSAL_PREFIX + '2026-11-17': 'pending'}
        self.assertEqual(divergent.recovery(cc, {}, GAP, waiting, NOW), (None, [], []))
        self.assertEqual(cc.calls, [])

    def test_a_refusal_is_a_quiet_line_never_a_raise(self):
        for status, code in ((429, 'daily_diverge_cap_reached'), (503, 'embedder_uncalibrated'),
                             (503, 'daily_spend_unreadable'), (409, 'engine_held'), (403, 'forbidden')):
            cc = FakeCC({'divergent': True}, error=ProtocolError('http_error', status, code))
            play, lines, holds = divergent.recovery(cc, {}, GAP, {}, NOW)
            self.assertIsNone(play)
            self.assertEqual(holds, [])
            self.assertIn(code, lines[0])
            self.assertEqual(len([c for c in cc.calls if isinstance(c, dict)]), 1)  # never retried
        cc = FakeCC({'divergent': True}, error=ProtocolError('too_many_requests', 429, 'daily_score_cap_reached'))
        mixed = {'concepts': [{'concept_id': 'meme-a', 'claim': 'A synthetic hook'}]}
        guard = divergent.guard_hooks(cc, mixed, live=['A synthetic live post'])
        self.assertEqual(guard['status'], 'unavailable')
        self.assertIn('daily_score_cap_reached', guard['note'])


class Recovery(unittest.TestCase):
    def test_the_request_is_the_u5_strategy_ask(self):
        cc = served(sparks=SPARKS, runId=RUN)
        divergent.recovery(cc, {}, GAP, {}, NOW)
        body = cc.calls[-1]
        self.assertEqual((body['op'], body['target'], body['count']), ('diverge', 'strategy', 3))
        self.assertEqual(body['problem'], divergent.PROBLEM)
        self.assertTrue(body['namespace'].startswith('growth-makeyourmindup'))
        self.assertIn('Post more often', body['cliches'])
        self.assertIn('Post more', body['cliches'])
        self.assertTrue(any('Substack Live' in c for c in body['cliches']))
        for word in ('delve', 'leverage'):
            self.assertIn(word, body['bannedWords'])
        self.assertNotIn('Krish', body['bannedWords'])
        self.assertNotIn('\u2014', json.dumps(body, ensure_ascii=False))

    def test_sparks_are_checked_and_the_top_survivor_is_the_one_ask_with_its_provenance(self):
        play, lines, holds = divergent.recovery(served(sparks=SPARKS, runId=RUN), {}, GAP, {}, NOW)
        # Spark 1 offers a prize: the walls hold it, with its reason, and it is never proposed.
        self.assertEqual(len(holds), 1)
        self.assertIn('spark 1', holds[0]['detail'])
        self.assertIn('wall paid', holds[0]['detail'])
        self.assertEqual(play['proposal_id'], 'makeyourmindup:divergent:2026-11-18')
        self.assertEqual((play['wall'], play['kind'], play['stage']), ('strategy', 'advice', 'plan'))
        self.assertTrue(play['title'].endswith('Trade one reader question with one editor you name'))
        self.assertIn('First step: Pick one editor', play['exact_payload'])
        self.assertEqual(play['evidence'], [{'label': 'divergent-thinker spark 2, run ' + RUN, 'url': None}])
        # The third is a note in the report, not a second ask.
        self.assertTrue(any('spark 3' in line and 'not asked' in line for line in lines))
        self.assertTrue(all(len(line) <= 500 for line in lines))

    def test_the_walls_hold_consent_bulk_and_community_breaks_and_lint_hits(self):
        for words, wall in (('DM every follower a link', 'bulk'), ('Join an engagement pod', 'community'),
                            ('Add readers to the list without asking', 'consent'),
                            ('Boost the best Note', 'paid')):
            self.assertTrue(any(e.startswith('wall ' + wall) for e in divergent.wall_errors(words)), words)
        self.assertTrue(divergent.wall_errors('A play \u2014 with an em dash'))
        self.assertTrue(divergent.wall_errors("Krish's take on the week"))
        self.assertTrue(divergent.wall_errors('Leverage the landscape'))
        self.assertEqual(divergent.wall_errors('Swap one guest essay with one editor you name, no paid ads'), [])
        bad = [spark(1, 'Join an engagement pod'), spark(2, 'Use a fake account to seed replies'),
               spark(3, 'Scrape commenters and DM each one')]
        play, lines, holds = divergent.recovery(served(sparks=bad, runId=RUN), {}, GAP, {}, NOW)
        self.assertIsNone(play)
        self.assertEqual(len(holds), 3)
        self.assertTrue(any('No divergent-thinker spark cleared' in line for line in lines))

    def test_the_runner_report_carries_the_play_only_when_nothing_else_is_proposed(self):
        from engine.cc_loop import runner_report
        play = divergent.recovery(served(sparks=SPARKS, runId=RUN), {}, GAP, {}, NOW)
        root = Path(__file__).resolve().parents[1]
        checks = [{'name': 'self_test', 'ok': True, 'stdout': '', 'stderr': ''}]
        with patch('engine.cc_loop.experiment_proposals', lambda r, n=None: []), \
                patch('engine.cc_loop.standing_plan', lambda r: None), \
                patch('engine.ai_answers.proposal_or_hold', lambda r: (None, None)):
            report, _ = runner_report(root, 'makeyourmindup:2026-11-18:runner', NOW, checks, 'synthetic', sent={},
                                      gap=GAP, recovery=play, rev='abc1234')
        validate_report(report)
        self.assertEqual([p['proposal_id'] for p in report['proposals']], ['makeyourmindup:divergent:2026-11-18'])
        self.assertTrue(any('spark 3' in a['line'] for a in report['activity']))
        self.assertTrue(any(h['reason'].startswith('A divergent-thinker spark') for h in report['holds']))
        other = divergent.proposal('makeyourmindup:experiment:x', 'Decide x', 'Synthetic', 'advice', 'strategy',
                                   'experiment_started', reference='x')
        with patch('engine.cc_loop.experiment_proposals', lambda r, n=None: [other]), \
                patch('engine.cc_loop.standing_plan', lambda r: None), \
                patch('engine.ai_answers.proposal_or_hold', lambda r: (None, None)):
            report, _ = runner_report(root, 'makeyourmindup:2026-11-18:runner', NOW, checks, 'synthetic', sent={},
                                      gap=GAP, recovery=play, rev='abc1234')
        self.assertEqual([p['proposal_id'] for p in report['proposals']], ['makeyourmindup:experiment:x'])


class Hooks(unittest.TestCase):
    MIX = {'concepts': [{'concept_id': 'meme-a', 'claim': 'Your AI budget is a vibe'},
                        {'concept_id': 'meme-b', 'claim': 'The memo nobody read'},
                        {'concept_id': 'carousel-x', 'claim': None}]}
    IDEAS = [{'idea_id': 'a', 'lane': 'meme', 'idea': 'x', 'note': 'One question for your next board meeting'}]

    def test_hooks_are_the_captions_and_the_planned_notes(self):
        hooks = divergent.plan_hooks(self.MIX, self.IDEAS)
        self.assertEqual([h for _, h in hooks], ['Your AI budget is a vibe', 'The memo nobody read',
                                                'One question for your next board meeting'])

    def test_a_repeated_hook_is_flagged_never_dropped_with_zero_model_calls(self):
        results = [{'title': 'Your AI budget is a vibe', 'status': 'rejected_archive'},
                   {'title': 'The memo nobody read', 'status': 'accepted'},
                   {'title': 'One question', 'status': 'rejected_gravity'}]
        cc = served(results=results, divergenceIndex=0.4)
        guard = divergent.guard_hooks(cc, self.MIX, self.IDEAS, ['A live post', 'Another live post'])
        body = cc.calls[-1]
        self.assertEqual(body['op'], 'score')
        self.assertEqual(body['namespace'], 'growth-makeyourmindup:hooks')
        self.assertEqual(body['obvious'], ['A live post', 'Another live post'])  # obvious given, no judge: no model call
        self.assertNotIn('judge', body)
        self.assertEqual([f['status'] for f in guard['flags']], ['rejected_archive', 'rejected_gravity'])
        self.assertEqual(guard['flags'][0]['where'], 'concept meme-a caption')
        self.assertEqual(len(self.MIX['concepts']), 3)

    def test_no_live_posts_or_not_served_scores_nothing(self):
        cc = served(results=[])
        self.assertEqual(divergent.guard_hooks(cc, self.MIX, live=[])['status'], 'skipped')
        self.assertEqual([c for c in cc.calls if isinstance(c, dict)], [])
        off = FakeCC({})
        self.assertEqual(divergent.guard_hooks(off, self.MIX, live=['x'])['status'], 'not_served')
        self.assertEqual(off.calls, ['capabilities'])

    def test_the_mix_plan_writes_the_flags_into_the_plan(self):
        results = [{'status': 'rejected_archive'}]
        cc = served(results=results)
        with tempfile.TemporaryDirectory() as folder:
            live = Path(folder) / 'live.json'
            live.write_text(json.dumps(['Your AI budget is a vibe']), encoding='utf-8')
            plan = {'concepts': [{'concept_id': 'meme-a', 'claim': 'Your AI budget is a vibe'}]}
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                mix.hook_guard(plan, [], lambda: cc, live)
        self.assertEqual(plan['hook_guard']['flags'][0]['status'], 'rejected_archive')
        self.assertIn('flagged rejected_archive: concept meme-a caption', err.getvalue())
        # No token here: the factory refuses, and the plan says not served, with no call.
        plan = {'concepts': [{'concept_id': 'meme-a', 'claim': 'x'}]}
        with contextlib.redirect_stderr(io.StringIO()):
            mix.hook_guard(plan, [], lambda: (_ for _ in ()).throw(ValueError('no key')), '/nonexistent')
        self.assertEqual(plan['hook_guard']['status'], 'not_served')


class Record(unittest.TestCase):
    POSTS = [{'post_id': 'a', 'sent_at': '2026-11-18T09:00:00Z', 'words': 'Live words https://example.com/x?utm=1'},
             {'post_id': 'b', 'sent_at': '2026-11-17T09:00:00Z', 'words': 'Live words https://example.com/y'},
             {'post_id': 'c', 'sent_at': '2026-11-01T09:00:00Z', 'words': 'Too old to record'},
             {'post_id': 'd', 'sent_at': '2026-11-16T09:00:00Z', 'words': 'Older live words'}]

    def test_records_published_words_only_links_removed_each_once(self):
        cc = served()
        line = divergent.record_live(cc, self.POSTS, NOW)
        body = cc.calls[-1]
        self.assertEqual(body['op'], 'record')
        self.assertEqual(body['namespace'], 'growth-makeyourmindup:hooks')
        self.assertEqual(body['items'], ['Live words', 'Older live words'])
        self.assertNotIn('Live words', line)  # counts only in the log
        self.assertIn('recorded 2', line)

    def test_not_served_or_refused_records_nothing_quietly(self):
        self.assertEqual(divergent.record_live(FakeCC({}), self.POSTS, NOW), divergent.NOT_SERVED)
        refused = FakeCC({'divergent': True}, error=ProtocolError('http_error', 409, 'engine_held'))
        self.assertIn('engine_held', divergent.record_live(refused, self.POSTS, NOW))
        self.assertIsNone(divergent.record_live(served(), [], NOW))


class ClientRoute(unittest.TestCase):
    def test_diverge_waits_its_own_timeout_and_score_the_usual_one(self):
        seen = []

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n):
                return b'{"ok": true}'

        class Opener:
            def open(self, request, timeout):
                seen.append((request.full_url, timeout))
                return Response()

        client = Client('gen1_' + 'x' * 20, 'http://127.0.0.1:9', loopback_for_tests=True, timeout=7)
        client._opener = Opener()
        client.divergent({'op': 'diverge', 'problem': 'p'})
        client.divergent({'op': 'score', 'problem': 'p', 'ideas': ['a']})
        self.assertTrue(seen[0][0].endswith('/api/growth/engines/makeyourmindup/divergent'))
        self.assertEqual([t for _, t in seen], [300, 7])


if __name__ == '__main__':
    unittest.main()


class BannedWordsForTheGate(unittest.TestCase):
    def test_his_name_is_not_sent_but_the_slop_is(self):
        from engine import divergent as d
        words = [w.lower() for w in d.BANNED_WORDS]
        self.assertNotIn('krish', words)
        self.assertIn('leverage', words)


class AtWill(unittest.TestCase):
    """growth.py divergent <op>: any session, by hand. One call at most, never retried, never on his list."""

    class CC(FakeCC):
        def __init__(self, held=False, directive_error=None, **kw):
            super().__init__(**kw)
            self.held, self.directive_error = held, directive_error

        def directive(self):
            self.calls.append('directive')
            if self.directive_error:
                raise self.directive_error
            words = 'Krish has held this engine until he releases it' if self.held else 'Prepare the week'
            return {'ok': True, 'directive': {'next_action': {'instruction': words}}}

    def cc(self, **kw):
        kw.setdefault('features', {'divergent': True})
        return self.CC(**kw)

    def run_cli(self, argv, cc):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = divergent.command(argv, lambda: cc)
        return code, out.getvalue(), err.getvalue()

    def test_each_op_sends_its_own_body_and_namespace(self):
        d = divergent
        self.assertEqual(d.at_will_body('map', 'A problem', 'Some context'),
                         {'op': 'map', 'problem': 'A problem', 'context': 'Some context'})
        self.assertEqual(d.at_will_body('challenge', 'A problem', idea='One idea'),
                         {'op': 'challenge', 'problem': 'A problem', 'idea': 'One idea'})
        provoke = d.at_will_body('provoke', 'A problem', cliches=['Post more'], count=4, target='strategy',
                                 temperament='wild', lane='hooks')
        self.assertEqual(provoke['namespace'], 'growth-makeyourmindup:hooks')
        self.assertEqual((provoke['cliches'], provoke['count'], provoke['target'], provoke['temperament']),
                         (['Post more'], 4, 'strategy', 'wild'))
        self.assertEqual(provoke['bannedWords'], list(d.BANNED_WORDS))
        self.assertNotIn('krish', [w.lower() for w in provoke['bannedWords']])
        diverge = d.at_will_body('diverge', 'A problem')
        self.assertEqual((diverge['op'], diverge['namespace']), ('diverge', 'growth-makeyourmindup'))
        score = d.at_will_body('score', 'A problem', ideas=['a', 'b'], obvious=['c'], judge=True)
        self.assertEqual(score, {'op': 'score', 'problem': 'A problem', 'ideas': ['a', 'b'],
                                 'bannedWords': list(d.BANNED_WORDS), 'namespace': 'growth-makeyourmindup',
                                 'obvious': ['c'], 'judge': True})
        self.assertEqual(d.at_will_body('record', items=['x'], lane='live', label='batch'),
                         {'op': 'record', 'items': ['x'], 'namespace': 'growth-makeyourmindup:live', 'label': 'batch'})
        for bad in (lambda: d.at_will_body('map'), lambda: d.at_will_body('challenge', 'p'),
                    lambda: d.at_will_body('score', 'p'), lambda: d.at_will_body('record'),
                    lambda: d.at_will_body('map', 'p', lane='Not A Lane')):
            self.assertRaises(ValueError, bad)

    def test_the_cli_reads_files_and_prints_the_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            ideas, obvious = Path(tmp, 'ideas.json'), Path(tmp, 'obvious.txt')
            ideas.write_text(json.dumps(['Hook one', 'Hook two']), encoding='utf-8')
            obvious.write_text('Live one\n\nLive two\n', encoding='utf-8')
            cc = self.cc(answer={'ok': True, 'results': [{'status': 'accepted'}, {'status': 'accepted'}]})
            code, out, err = self.run_cli(['score', '--problem', 'p', '--ideas-file', str(ideas),
                                           '--obvious-file', str(obvious), '--lane', 'hooks'], cc)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['results'][0]['status'], 'accepted')
        body = cc.calls[-1]
        self.assertEqual((body['ideas'], body['obvious'], body['namespace']),
                         (['Hook one', 'Hook two'], ['Live one', 'Live two'], 'growth-makeyourmindup:hooks'))
        self.assertEqual(cc.calls[0], 'capabilities')
        self.assertNotIn('directive', cc.calls)  # score spends nothing, so the held read is not needed

    def test_a_score_that_flags_anything_exits_one(self):
        cc = self.cc(answer={'ok': True, 'results': [{'status': 'accepted'}, {'status': 'rejected_gravity'}]})
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, 'ideas.txt'); f.write_text('a\nb\n', encoding='utf-8')
            code, out, _ = self.run_cli(['score', '--problem', 'p', '--ideas-file', str(f)], cc)
        self.assertEqual(code, 1)
        self.assertIn('rejected_gravity', out)

    def test_generating_ops_read_the_held_state_and_run_once(self):
        cc = self.cc(answer={'ok': True, 'runId': RUN, 'sparks': []})
        code, out, _ = self.run_cli(['provoke', '--problem', 'p', '--count', '3'], cc)
        self.assertEqual(code, 0)
        self.assertEqual(cc.calls[:2], ['capabilities', 'directive'])
        self.assertEqual([c['op'] for c in cc.calls if isinstance(c, dict)], ['provoke'])
        self.assertEqual(json.loads(out)['runId'], RUN)

    def test_held_refuses_generating_ops_and_never_calls(self):
        for op, extra in (('map', []), ('provoke', []), ('challenge', ['--idea', 'i']), ('diverge', [])):
            cc = self.cc(held=True)
            code, out, err = self.run_cli([op, '--problem', 'p'] + extra, cc)
            self.assertEqual((code, out), (2, ''))
            self.assertIn('held', err)
            self.assertEqual(cc.calls, ['capabilities', 'directive'])
        unreadable = self.cc(directive_error=ProtocolError('unreachable'))
        self.assertEqual(self.run_cli(['map', '--problem', 'p'], unreadable)[0], 2)
        self.assertEqual(unreadable.calls, ['capabilities', 'directive'])
        # Held does not stop the free ops: they spend nothing.
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp, 'items.txt'); f.write_text('one\n', encoding='utf-8')
            cc = self.cc(held=True)
            self.assertEqual(self.run_cli(['record', '--items-file', str(f)], cc)[0], 0)
            self.assertEqual(cc.calls[-1]['op'], 'record')

    def test_not_served_exits_two_with_no_call(self):
        for cc in (self.cc(features={'divergent': False}), self.cc(features={}),
                   self.cc(cap_error=ProtocolError('unreachable'))):
            code, out, err = self.run_cli(['map', '--problem', 'p'], cc)
            self.assertEqual((code, out), (2, ''))
            self.assertIn('not served', err)
            self.assertEqual(cc.calls, ['capabilities'])

    def test_a_refusal_or_no_token_exits_two_and_is_never_retried(self):
        for status, server in ((429, 'daily_diverge_cap_reached'), (503, 'embedder_uncalibrated'),
                               (409, 'engine_held'), (400, 'bad_request')):
            cc = self.cc(error=ProtocolError('http_error', status, server))
            code, out, err = self.run_cli(['diverge', '--problem', 'p'], cc)
            self.assertEqual((code, out), (2, ''))
            self.assertIn(server, err)
            self.assertEqual(len([c for c in cc.calls if isinstance(c, dict)]), 1)

        def no_token():
            raise ValueError('No Control Center engine key')
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(divergent.command(['map', '--problem', 'p'], no_token), 2)
        self.assertIn('not consulted', err.getvalue())

    def test_growth_py_dispatches_the_command(self):
        import growth
        err = io.StringIO()
        with patch.dict('os.environ', {'CONTROL_CENTER_ENGINE_TOKEN': ''}), \
                patch.object(growth, 'ENGINE_TOKEN_FILE', Path('/nonexistent/engine-token')), \
                contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(growth.main(['divergent', 'map', '--problem', 'p']), 2)
        self.assertIn('not consulted', err.getvalue())
