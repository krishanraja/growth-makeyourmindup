"""A tiny Buffer GraphQL client for the release lane (L0). Standard library only.

It reads posts and turns one signed draft into a post scheduled at an exact
time. It has no immediate-publish path and no removal path: the only mutation
it can send is editPost with mode customScheduled and an exact dueAt, on a
post that is still a draft, carrying the draft's whole payload forward (an
edit is revalidated as a whole post, lesson F01).

It never logs or raises with post text, URLs or the key: errors carry a
lower_snake code only.

Schema facts relied on, read with the read-only introspect_schema on
27 October 2026 (recheck after a provider change):
- POST a JSON body {query, variables, operationName} to the endpoint with
  `Authorization: Bearer <key>` (developers.buffer.com, getting started).
- Query.account { id organizations { id } }; Query.post(input: PostInput!)
  where PostInput is {id}; Query.posts(after, first, input: PostsInput!) with
  {organizationId, filter: {channelIds, status, dueAt: {start, end}}}.
- Mutation.editPost(input: EditPostInput!) returns PostActionPayload, the union
  PostActionSuccess {post} | NotFoundError | UnauthorizedError |
  UnexpectedError | RestProxyError | LimitReachedError | InvalidInputError.
  EditPostInput has no channelId: the post id pins its channel.
- Post: id status text dueAt channelId channelService schedulingType via
  assets metadata (a union per service). PostStatus: draft, needs_approval,
  scheduled, sending, sent, error.
- AssetInput is exactly one of image {url, metadata {altText, userTags}},
  video {url, metadata {title, thumbnailOffset}} or document.
"""
import hashlib
import json
import re
import socket
import urllib.error
import urllib.request

ENDPOINT = 'https://api.buffer.com'  # developers.buffer.com getting-started; verify against live schema
TIMEOUT = 20
ASSET_TIMEOUT = 60
MAX_RESPONSE = 5000000
ASSET_CAP = 50 * 1024 * 1024
PAGE = 50
MAX_PAGES = 20
BUFFER_ID = re.compile(r'^[a-f0-9]{24}$')
LOOPBACK = re.compile(r'^http://127\.0\.0\.1:[0-9]{1,5}(/|$)')
# GraphQL error extension codes that mean the key was refused; verify against live schema.
AUTH_CODES = ('UNAUTHENTICATED', 'UNAUTHORIZED', 'FORBIDDEN')
CODE = re.compile(r'^[a-z][a-z0-9_]{0,63}$')
SCHEDULE_MODE = 'customScheduled'

# The selection every read and the mutation use: everything carried forward.
METADATA_FIELDS = '''__typename
      ... on InstagramPostMetadata { type shouldShareToFeed isAiGenerated firstComment link
        stickerFields { music other products text topics } geolocation { id text } }
      ... on FacebookPostMetadata { type firstComment title linkAttachment { url } }
      ... on LinkedInPostMetadata { type firstComment linkAttachment { url } }
      ... on TwitterPostMetadata { type isAiGenerated threadCount retweet { id } }
      ... on ThreadsPostMetadata { type topic locationId locationName threadCount linkAttachment { url } }
      ... on TiktokPostMetadata { type isAiGenerated title }
      ... on YoutubePostMetadata { type title category { categoryId } privacy madeForKids notifySubscribers
        embeddable license isAiGenerated }
      ... on SubstackPostMetadata { type linkAttachment { url } }'''
POST_FIELDS = '''id status text dueAt channelId channelService schedulingType via
    assets { type source mimeType
      ... on ImageAsset { image { altText userTags { handle x y } } }
      ... on VideoAsset { video { title thumbnailOffset } } }
    metadata { ''' + METADATA_FIELDS + ''' }'''

ACCOUNT_QUERY = 'query AccountCheck { account { id organizations { id } } }'
POST_QUERY = 'query GetPost($input: PostInput!) { post(input: $input) { ' + POST_FIELDS + ' } }'
POSTS_QUERY = ('query ListPosts($first: Int, $after: String, $input: PostsInput!) { posts(first: $first, after: $after, '
               'input: $input) { edges { node { ' + POST_FIELDS + ' } } pageInfo { hasNextPage endCursor } } }')
SCHEDULE_MUTATION = ('mutation ScheduleDraft($input: EditPostInput!) { editPost(input: $input) { __typename '
                     '... on PostActionSuccess { post { ' + POST_FIELDS + ' } } ... on MutationError { message } } }')


class BufferError(Exception):
    """A Buffer failure named by a lower_snake code. Never carries a body, URL or key."""

    def __init__(self, code, status=None):
        self.code = code if isinstance(code, str) and CODE.match(code) else 'buffer_error'
        self.status = status
        super().__init__('Buffer: ' + self.code + (' (HTTP ' + str(status) + ')' if status else ''))


class BufferAuthError(BufferError):
    """The key was refused (401/403, or an auth error in the GraphQL body)."""

    def __init__(self, status=None):
        super().__init__('buffer_key_refused', status)


class CarryHold(ValueError):
    """The draft carries something a whole-post edit cannot carry forward safely."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect could carry the bearer elsewhere, so the API client follows none."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BufferError('redirect_refused', code)


class _HttpsRedirectOnly(urllib.request.HTTPRedirectHandler):
    """Media hosts may redirect to a CDN; only to https, and never with a key."""

    def __init__(self, loopback=False):
        self.loopback = loopback

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not (newurl.startswith('https://') or (self.loopback and LOOPBACK.match(newurl))):
            raise BufferError('asset_redirect_refused', code)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _transient(error):
    if isinstance(error, urllib.error.HTTPError):
        return error.code >= 500
    return isinstance(error, (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError))


class Buffer:
    """Reads, plus one scheduling edit of a draft. Nothing else."""

    def __init__(self, key, endpoint=ENDPOINT, timeout=TIMEOUT, loopback_for_tests=False):
        if loopback_for_tests:
            if not LOOPBACK.match(endpoint or ''):
                raise BufferError('endpoint_refused')
        elif endpoint != ENDPOINT:
            raise BufferError('endpoint_refused')
        if not isinstance(key, str) or not key or any(c.isspace() for c in key):
            raise BufferError('buffer_key_missing')
        self._endpoint = endpoint
        self._key = key
        self._timeout = timeout
        self._loopback = loopback_for_tests
        handlers = [_NoRedirect()]
        if loopback_for_tests:
            handlers.append(urllib.request.ProxyHandler({}))
        self._opener = urllib.request.build_opener(*handlers)
        self.mutations = 0
        self.requests = 0

    def __repr__(self):
        return '<Buffer client>'

    # Transport -------------------------------------------------------------

    def _send(self, body):
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self._endpoint, data=data, method='POST', headers={
            'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json', 'Accept': 'application/json'})
        self.requests += 1
        with self._opener.open(request, timeout=self._timeout) as response:
            raw = response.read(MAX_RESPONSE + 1)
        if len(raw) > MAX_RESPONSE:
            raise BufferError('response_too_large')
        return raw

    def _graphql(self, operation, query, variables=None):
        body = {'operationName': operation, 'query': query, 'variables': variables or {}}
        raw = None
        for attempt in (1, 2):
            try:
                raw = self._send(body)
                break
            except BufferError:
                raise
            except urllib.error.HTTPError as error:
                status = error.code
                error.close()
                if status in (401, 403):
                    raise BufferAuthError(status) from None
                if attempt == 1 and _transient(error):
                    continue
                if status == 429:
                    raise BufferError('buffer_rate_limited', status) from None
                raise BufferError('buffer_server_error' if status >= 500 else 'buffer_rejected', status) from None
            except (urllib.error.URLError, OSError) as error:
                if attempt == 1 and _transient(error):
                    continue
                reason = getattr(error, 'reason', error)
                raise BufferError('buffer_timeout' if isinstance(reason, socket.timeout) else 'buffer_unreachable') from None
        try:
            result = json.loads(raw.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            raise BufferError('buffer_bad_response') from None
        if not isinstance(result, dict):
            raise BufferError('buffer_bad_response')
        errors = result.get('errors')
        if errors:
            codes = {((e or {}).get('extensions') or {}).get('code') for e in errors if isinstance(e, dict)}
            if codes & set(AUTH_CODES):
                raise BufferAuthError()
            raise BufferError('buffer_graphql_error')
        if not isinstance(result.get('data'), dict):
            raise BufferError('buffer_bad_response')
        return result['data']

    # Reads -----------------------------------------------------------------

    def account_check(self):
        """Proves the key works. Returns ids only: {'account': True, 'organization_ids': [...]}."""
        account = self._graphql('AccountCheck', ACCOUNT_QUERY).get('account')
        if not isinstance(account, dict) or not account.get('id'):
            raise BufferError('buffer_bad_response')
        orgs = [o.get('id') for o in account.get('organizations') or [] if isinstance(o, dict) and o.get('id')]
        return {'account': True, 'organization_ids': orgs}

    def get_post(self, post_id):
        if not isinstance(post_id, str) or not BUFFER_ID.match(post_id):
            raise BufferError('bad_post_id')
        post = self._graphql('GetPost', POST_QUERY, {'input': {'id': post_id}}).get('post')
        if not isinstance(post, dict) or post.get('id') != post_id:
            raise BufferError('post_not_read_back')
        return post

    def list_posts(self, organization_id, status=None, channel_ids=None, since=None):
        """Posts in one organisation, filtered by status, channels and dueAt from since."""
        flt = {}
        if status:
            flt['status'] = [status] if isinstance(status, str) else list(status)
        if channel_ids:
            flt['channelIds'] = list(channel_ids)
        if since:
            flt['dueAt'] = {'start': since}
        variables = {'first': PAGE, 'after': None, 'input': {'organizationId': organization_id, 'filter': flt}}
        out = []
        for _ in range(MAX_PAGES):
            posts = self._graphql('ListPosts', POSTS_QUERY, variables).get('posts') or {}
            out += [e['node'] for e in posts.get('edges') or [] if isinstance(e, dict) and isinstance(e.get('node'), dict)]
            page = posts.get('pageInfo') or {}
            if not page.get('hasNextPage') or not page.get('endCursor'):
                return out
            variables['after'] = page['endCursor']
        raise BufferError('too_many_posts')

    # The one mutation --------------------------------------------------------

    def schedule_draft(self, post, due_at, text=None):
        """Schedule one draft at exactly due_at, carrying its whole payload.

        post is a fresh get_post of the draft. text, when given, is the signed
        (or Krish's amended) words; otherwise the draft's own words are kept.
        Returns the post the mutation returned; the caller still reads back."""
        if not isinstance(post, dict) or post.get('status') != 'draft':
            raise BufferError('not_a_draft')
        if not isinstance(due_at, str) or not due_at:
            raise BufferError('no_due_at')
        payload = edit_input(post, due_at, text)
        self.mutations += 1
        result = self._graphql('ScheduleDraft', SCHEDULE_MUTATION, {'input': payload}).get('editPost')
        if not isinstance(result, dict):
            raise BufferError('buffer_bad_response')
        if result.get('__typename') != 'PostActionSuccess' or not isinstance(result.get('post'), dict):
            name = result.get('__typename') if isinstance(result.get('__typename'), str) else ''
            raise BufferError('edit_refused_' + re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower() if name else 'edit_refused')
        return result['post']


# Carrying a draft forward ---------------------------------------------------

def _asset_input(asset):
    kind = asset.get('type') if isinstance(asset, dict) else None
    url = asset.get('source') if isinstance(asset, dict) else None
    if not isinstance(url, str) or not url:
        raise CarryHold('asset_without_source')
    if kind == 'image':
        body = {'url': url}
        image = asset.get('image') or {}
        meta = {}
        if image.get('altText'):
            meta['altText'] = image['altText']
        if image.get('userTags'):
            if 'altText' not in meta:
                raise CarryHold('user_tags_without_alt_text')
            meta['userTags'] = [{'handle': t['handle'], 'x': t['x'], 'y': t['y']} for t in image['userTags']]
        if meta:
            body['metadata'] = meta
        return {'image': body}
    if kind == 'video':
        body = {'url': url}
        video = asset.get('video') or {}
        meta = {k: video[k] for k in ('title', 'thumbnailOffset') if video.get(k) is not None}
        if meta:
            body['metadata'] = meta
        return {'video': body}
    if kind == 'document':
        # F52: Buffer lost a saved PDF preview; documents are held, never re-sent.
        raise CarryHold('document_asset_held')
    raise CarryHold('unknown_asset_type')


def _has_link(meta):
    return bool((meta.get('linkAttachment') or {}).get('url')) if isinstance(meta.get('linkAttachment'), dict) else False


def _metadata_input(post):
    """The draft's stored metadata as PostInputMetaData, or a CarryHold."""
    meta = post.get('metadata')
    if meta is None:
        return None
    if not isinstance(meta, dict):
        raise CarryHold('unknown_metadata')
    kind = meta.get('__typename')
    has_video = any(isinstance(a, dict) and a.get('type') == 'video' for a in post.get('assets') or [])
    if kind == 'InstagramPostMetadata':
        stickers = meta.get('stickerFields') or {}
        if meta.get('link') or (isinstance(stickers, dict) and any(stickers.values())):
            raise CarryHold('instagram_link_sticker')  # F09
        out = {'type': meta['type'], 'shouldShareToFeed': bool(meta.get('shouldShareToFeed'))}
        for key in ('isAiGenerated', 'firstComment'):
            if meta.get(key) is not None:
                out[key] = meta[key]
        geo = meta.get('geolocation') or {}
        if isinstance(geo, dict) and (geo.get('id') or geo.get('text')):
            out['geolocation'] = {k: geo[k] for k in ('id', 'text') if geo.get(k) is not None}
        return {'instagram': out}
    if kind == 'FacebookPostMetadata':
        if _has_link(meta):
            raise CarryHold('link_preview_held')  # F03
        if meta.get('type') not in ('post', 'reel', 'story'):
            raise CarryHold('unknown_metadata')
        out = {'type': meta['type']}
        if meta.get('firstComment'):
            out['firstComment'] = meta['firstComment']
        return {'facebook': out}
    if kind == 'LinkedInPostMetadata':
        raise CarryHold('linkedin_is_krish_click')
    if kind == 'TwitterPostMetadata':
        if (meta.get('threadCount') or 0) > 0 or meta.get('retweet'):
            raise CarryHold('thread_not_carried')
        return {'twitter': {'isAiGenerated': True}} if meta.get('isAiGenerated') else None
    if kind == 'ThreadsPostMetadata':
        if (meta.get('threadCount') or 0) > 0:
            raise CarryHold('thread_not_carried')
        if _has_link(meta):
            raise CarryHold('link_preview_held')
        out = {k: meta[k] for k in ('type', 'topic', 'locationId', 'locationName') if meta.get(k) is not None}
        return {'threads': out} if out else None
    if kind == 'TiktokPostMetadata':
        if meta.get('isAiGenerated') and not has_video:
            raise CarryHold('tiktok_photo_ai_flag')  # F02
        out = {k: meta[k] for k in ('title',) if meta.get(k)}
        if meta.get('isAiGenerated'):
            out['isAiGenerated'] = True
        return {'tiktok': out} if out else None
    if kind == 'YoutubePostMetadata':
        category = (meta.get('category') or {}).get('categoryId')
        if not meta.get('title') or not category:
            raise CarryHold('youtube_needs_title_and_category')
        out = {'title': meta['title'], 'categoryId': category}
        for key in ('privacy', 'madeForKids', 'notifySubscribers', 'embeddable', 'license', 'isAiGenerated'):
            if meta.get(key) is not None:
                out[key] = meta[key]
        return {'youtube': out}
    if kind == 'SubstackPostMetadata':
        if _has_link(meta):
            raise CarryHold('link_preview_held')
        return None
    raise CarryHold('unknown_metadata')


def edit_input(post, due_at, text=None):
    """EditPostInput for one draft: id, words, every asset, metadata, exact time."""
    if not isinstance(post.get('id'), str) or not BUFFER_ID.match(post['id']):
        raise CarryHold('bad_post_id')
    words = post.get('text') if text is None else text
    if not isinstance(words, str) or not words.strip():
        raise CarryHold('no_words')
    payload = {'id': post['id'], 'text': words, 'assets': [_asset_input(a) for a in post.get('assets') or []],
               'mode': SCHEDULE_MODE, 'dueAt': due_at, 'schedulingType': 'automatic', 'saveToDraft': False}
    meta = _metadata_input(post)
    if meta:
        payload['metadata'] = meta
    return payload


# Media bytes -----------------------------------------------------------------

def download_sha256(url, cap=ASSET_CAP, timeout=ASSET_TIMEOUT, loopback_for_tests=False):
    """sha256 and size of the bytes at url, read fresh, capped. Never sends a key.
    Any failure raises BufferError with a code; the caller holds."""
    if not isinstance(url, str) or not (url.startswith('https://') or (loopback_for_tests and LOOPBACK.match(url))):
        raise BufferError('asset_url_refused')
    handlers = [_HttpsRedirectOnly(loopback_for_tests)]
    if loopback_for_tests:
        handlers.append(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, method='GET', headers={'Accept': '*/*'})
    digest, size = hashlib.sha256(), 0
    try:
        with urllib.request.build_opener(*handlers).open(request, timeout=timeout) as response:
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                size += len(chunk)
                if size > cap:
                    raise BufferError('asset_too_large')
                digest.update(chunk)
    except BufferError:
        raise
    except (urllib.error.URLError, OSError, ValueError):
        raise BufferError('asset_download_failed') from None
    if size == 0:
        raise BufferError('asset_download_failed')
    return digest.hexdigest(), size
