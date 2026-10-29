"""The maker's one Buffer write: save a new draft. Never a scheduled, queued or published post.

engine/run/buffer_api.py is release's client and can only schedule an existing
draft. This module adds the one call the maker (engine/run/maker.py) needs: a
createPost with saveToDraft true and no dueAt, on this engine's pinned
channels only and never LinkedIn (F13, social/guides/buffer.md step 4).

Schema facts relied on (engine/run/release.py, read with introspect_schema on
27 October 2026; recheck after a provider change): Mutation.createPost(input:
CreatePostInput!) returns PostActionPayload. CreatePostInput needs channelId,
schedulingType and mode (ShareMode!, required). The draft tools in this
repository have always relied on saveToDraft true overriding the queue mode
the input requires, so the mode sent is the draft tools' own default and the
maker reads every draft back: anything but status draft with no dueAt is
loud, and nothing schedules it but release.yml, after Krish's approval.

Errors carry a lower_snake code only, never words, URLs or the key.
"""
import re

from engine.buffer_channels import channel_id_errors
from engine.run.buffer_api import LOOPBACK, POST_FIELDS, Buffer, BufferError

CREATE_MUTATION = ('mutation CreateDraft($input: CreatePostInput!) { createPost(input: $input) { __typename '
                   '... on PostActionSuccess { post { ' + POST_FIELDS + ' } } ... on MutationError { message } } }')
# The services a draft may be made on: the four concept channels (engine/concepts.py), never LinkedIn.
DRAFT_CHANNELS = {'instagram': 'instagram', 'youtube': 'youtube', 'tiktok': 'tiktok', 'x': 'twitter'}
# CreatePostInput requires a mode; saveToDraft true keeps the post a draft, and the readback proves it.
DRAFT_MODE = 'addToQueue'


class DraftBuffer(Buffer):
    """Buffer's reads and release's scheduling edit, plus the maker's one draft save."""

    def create_draft(self, channel, channel_id, text, assets, metadata=None):
        """Save one new draft on this engine's pinned channel: saveToDraft true, no dueAt.

        channel is the engine's channel id (x, instagram, youtube, tiktok); assets a list of
        AssetInput ({image: {url}} or {video: {url}}, https only); metadata at most the one key of
        its service. Sent once, never retried (a failure may have landed, so the caller reads
        Buffer before it tries again). Returns the post the mutation returned; the caller reads
        it back."""
        if channel not in DRAFT_CHANNELS or channel_id_errors(channel, channel_id):
            raise BufferError('draft_channel_refused')
        if not isinstance(text, str) or not text.strip():
            raise BufferError('no_words')
        for asset in assets or []:
            pair = list(asset.items()) if isinstance(asset, dict) and len(asset) == 1 else [(None, None)]
            kind, body = pair[0]
            url = body.get('url') if isinstance(body, dict) else None
            if kind not in ('image', 'video') or set(body or {}) != {'url'} or not isinstance(url, str) or not (
                    url.startswith('https://') or (self._loopback and LOOPBACK.match(url))):
                raise BufferError('draft_asset_refused')
        service = DRAFT_CHANNELS[channel]
        if metadata is not None and (not isinstance(metadata, dict) or set(metadata) != {service}):
            raise BufferError('draft_metadata_refused')
        payload = {'channelId': channel_id, 'text': text, 'schedulingType': 'automatic', 'mode': DRAFT_MODE,
                   'saveToDraft': True, 'assets': list(assets or [])}
        if metadata:
            payload['metadata'] = metadata
        self.mutations += 1
        result = self._graphql('CreateDraft', CREATE_MUTATION, {'input': payload}, retry=False).get('createPost')
        if not isinstance(result, dict):
            raise BufferError('buffer_bad_response')
        if result.get('__typename') != 'PostActionSuccess' or not isinstance(result.get('post'), dict):
            name = result.get('__typename') if isinstance(result.get('__typename'), str) else ''
            raise BufferError('create_refused_' + re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower() if name
                              else 'create_refused')
        return result['post']
