"""Standing authority, stale-page protection and interrupted browser writes."""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from engine.channel_audit import ACCOUNTS, begin, checkpoint, command, in_scope, reconcile, repair_plan

NOW = '2026-10-21T12:00:00+00:00'
TARGET = 'https://www.youtube.com/watch?v=synthetic'


def fixture():
    return {'channel': 'youtube', 'account_url': ACCOUNTS['youtube'], 'target_url': TARGET,
            'surface': 'post', 'field': 'title', 'before': 'Synthetic typo', 'after': 'Synthetic title',
            'evidence': {'method': 'browser', 'url': TARGET, 'excerpt': 'Synthetic typo', 'observed_at': NOW},
            'reason': 'Correct a synthetic typo', 'success_check': 'Reloaded title equals proposed title',
            'owner_verified': True, 'meaning_preserved': True, 'voice_checked': True,
            'claims_checked': True, 'field_editable': True}


def current(change):
    return {**change['evidence'], 'field': change['field'], 'value': change['before'],
            'account_url': change['account_url'], 'owner_verified': True}


class ChannelAuditTests(unittest.TestCase):
    def test_metadata_and_protected_fields_are_separate(self):
        c = fixture()
        self.assertEqual(repair_plan(c, NOW)['disposition'], 'autonomous')
        for field in ('video', 'overlay', 'bio', 'pin', 'reupload', 'delete', 'unknown', 'thumbnail'):
            c['field'] = field
            c['approved'] = True
            self.assertEqual(repair_plan(c, NOW)['disposition'], 'approval_required')

    def test_identity_target_and_literal_evidence_fail_closed(self):
        for key, value in [('account_url', 'https://www.youtube.com/@someone-else'),
                           ('target_url', 'https://example.com/watch'), ('before', 'not observed')]:
            c = fixture()
            c[key] = value
            with self.assertRaises(ValueError):
                repair_plan(c, NOW)

    def test_missing_owner_and_editability_hold(self):
        for flag in ('owner_verified', 'meaning_preserved', 'voice_checked', 'claims_checked', 'field_editable'):
            c = fixture()
            c.pop(flag)
            self.assertEqual(repair_plan(c, NOW)['disposition'], 'held')

    def test_old_and_future_evidence_refused(self):
        for at in ('2026-10-20T12:00:00Z', '2026-10-21T13:00:00Z'):
            c = fixture()
            c['evidence']['observed_at'] = at
            with self.assertRaises(ValueError):
                repair_plan(c, NOW)

    def test_missing_timestamp_is_not_treated_as_now(self):
        c = fixture()
        c['evidence'].pop('observed_at')
        with self.assertRaises(ValueError):
            repair_plan(c, NOW)

    def test_cli_journals_before_edit_and_reconciles_on_resume(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            root = Path(folder)
            private = root / '.scratch'
            private.mkdir()
            source, state, out = (private / name for name in ('input.json', 'state.json', 'output.json'))
            c = fixture()
            source.write_text(json.dumps({'change': c, 'current': current(c)}))
            command('begin', source, state, out, root, NOW)
            recorded = json.loads(state.read_text())['repairs']
            repair_id = next(iter(recorded))
            self.assertEqual(recorded[repair_id]['status'], 'pending_readback')
            source.write_text(json.dumps({'repair_id': repair_id, 'readback': {
                **current(c), 'value': c['after'], 'excerpt': c['after'], 'reopened': True}}))
            command('reconcile', source, state, out, root, NOW)
            self.assertEqual(json.loads(state.read_text())['repairs'][repair_id]['status'], 'verified')
            with self.assertRaises(ValueError):
                command('plan', source, state, root / 'public.json', root, NOW)

    def test_stale_value_cannot_overwrite_user_edit(self):
        c = fixture()
        live = {**current(c), 'value': 'Edited by owner'}
        with self.assertRaises(ValueError):
            begin({}, c, live, NOW)

    def test_timeout_never_retries_pending_write(self):
        c = fixture()
        pending = begin({}, c, current(c), NOW)
        with self.assertRaises(ValueError):
            begin({pending['repair_id']: pending}, c, current(c), NOW)

    def test_reload_verifies_and_rerun_skips(self):
        c = fixture()
        pending = begin({}, c, current(c), NOW)
        readback = {**current(c), 'value': c['after'], 'excerpt': c['after'], 'reopened': True}
        done = reconcile(pending, readback, NOW)
        self.assertEqual(done['status'], 'verified')
        replay = begin({done['repair_id']: done}, c, readback, NOW)
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['status'], 'verified')

    def test_saved_button_does_not_prove_persistence(self):
        c = fixture()
        pending = begin({}, c, current(c), NOW)
        with self.assertRaises(ValueError):
            reconcile(pending, current(c), NOW)
        failed = reconcile(pending, {**current(c), 'reopened': True}, NOW)
        self.assertEqual(failed['status'], 'held')

    def test_readback_cannot_claim_a_value_absent_from_page(self):
        c = fixture()
        pending = begin({}, c, current(c), NOW)
        with self.assertRaises(ValueError):
            reconcile(pending, {**current(c), 'value': c['after'], 'reopened': True}, NOW)

    def test_profile_subscription_destination_is_verified(self):
        c = fixture()
        c.update(surface='profile', field='link', before='https://old.example',
                 after='https://home.makeyourmindup.ai/subscribe', link_purpose='align_subscription')
        c['evidence']['excerpt'] = c['before']
        c['destination'] = {'method': 'browser', 'url': c['after'], 'requested_url': c['after'],
                            'observed_at': NOW, 'excerpt': 'Subscribe', 'usable': True, 'purpose_match': True}
        self.assertEqual(repair_plan(c, NOW)['disposition'], 'autonomous')
        for url in ('https://home.makeyourmindup.ai.evil.example/subscribe',
                    'https://home.makeyourmindup.ai/', 'https://example.com/subscribe'):
            bad = copy.deepcopy(c)
            bad['after'] = url
            bad['destination'].update(url=url, requested_url=url)
            with self.assertRaises(ValueError):
                repair_plan(bad, NOW)

    def test_baseline_new_posts_pins_attention_and_unknown_dates(self):
        self.assertTrue(in_scope({'surface': 'profile'}, now=NOW))
        self.assertTrue(in_scope({'published_at': '2026-10-01T00:00:00Z'}, now=NOW))
        old = {'published_at': '2026-01-01T00:00:00Z'}
        self.assertFalse(in_scope(old, now=NOW))
        for flag in ('pinned', 'attention_evidence', 'open_repair'):
            self.assertTrue(in_scope({**old, flag: True}, now=NOW))
        self.assertTrue(in_scope({}, now=NOW))
        self.assertFalse(in_scope({'published_at': '2026-10-14T00:00:00Z'},
                                 last_complete='2026-10-15T00:00:00Z', now=NOW))

    def test_partial_channel_does_not_lose_unaudited_posts(self):
        coverage = {'channel': 'youtube', 'account_url': ACCOUNTS['youtube'], 'complete': True,
                    'pagination_complete': True, 'blockers': [], 'profiles_checked': True,
                    'pins_checked': True, 'window_start': '2026-09-21T12:00:00+00:00', 'window_end': NOW}
        self.assertEqual(checkpoint(None, coverage, NOW), NOW)
        for field in ('pagination_complete', 'profiles_checked', 'pins_checked', 'complete'):
            with self.assertRaises(ValueError):
                checkpoint(None, {**coverage, field: False}, NOW)
        with self.assertRaises(ValueError):
            checkpoint(None, {**coverage, 'blockers': ['signed_out']}, NOW)


if __name__ == '__main__':
    unittest.main()
