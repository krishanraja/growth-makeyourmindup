"""Every video goes out with its designed cover, never an auto-picked frame (Ruling, Krish, 2026-11-15).

His words, on the Counting rat tails reel Buffer posted to Instagram on 14 Nov (Buffer post 6af7980e81e1228421cd5b7b,
F133): "the thumbnail is ridiculously poor, and that must never be the case." That post carried the raw cut with
thumbnailOffset null, so Instagram showed frame 0, an AI scene with no headline and no wordmark.

Buffer takes a video as {url, metadata {title, thumbnailOffset}} (engine/run/buffer_api.py): there is no field for a
cover image, so Buffer can only ever show a frame of the cut. This module gives it one to point at:

1. Which cover. The piece manifest's per-channel `cover` when content-engine names one (engine/run/piece_manifest.py,
   `cover_for`), else the library's designed tall cover for the cut (the post's `3 Posts` folder,
   content-engine's docs/COVER-STANDARD.md). No cover means the post holds as `video_without_designed_cover`.
2. `append_cover`: the cover is appended to the cut as its last second (ffmpeg, re-encoded at the cut's own size,
   frame rate and audio, with silence under the cover), and `thumbnailOffset` is the middle of that second.
3. `cover_frame_errors`: the frame at that offset is pulled back out of the new file and compared with the cover
   (root mean square error over 0 to 1, under RMSE_LIMIT). A file whose frame is not the cover holds as
   `cover_frame_not_designed`.

Release refuses any video call on a cover channel with no thumbnailOffset (engine/run/release.py), the L0 carry
refuses a stored draft with none (buffer_api.carried), and the maker never saves a video draft without one
(buffer_drafts.create_draft). Never a null offset. Nothing here posts, uploads or schedules: the new file is local,
and the session files it (content-engine's send.py) before its Drive link goes on a draft.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

# The channels whose grid tile or player shows a video's cover: Instagram, TikTok, YouTube, Facebook, Threads and X
# (the five vertical channels, AGENTS.md "Vertical content goes to all five", and YouTube Shorts).
COVER_CHANNELS = ('instagram', 'tiktok', 'youtube', 'facebook', 'threads', 'x')
# The same channels by Buffer service name (a readback carries channelService).
COVER_SERVICES = ('instagram', 'tiktok', 'youtube', 'facebook', 'threads', 'twitter')
HOLD_SECONDS = 1.0
# Re-encoding moves pixels a little: 0.005 and 0.011 were measured on 15 Nov between Instagram's served poster and
# the designed cover, so 0.03 passes the cover and refuses a different picture (an AI scene, a title card).
RMSE_LIMIT = 0.03
INK = '0x0A1411'  # the kit's ink (render/kit.css --ink), the pad colour when a cover is not the cut's shape
TIMEOUT = 600
COMPARE = (270, 480)  # frames are compared at a quarter of 1080x1920


class CoverHold(Exception):
    """A video that cannot go out with its designed cover: a lower_snake code only."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def needs_cover(channel, kinds):
    """True when a post on this channel (engine id or Buffer service) carries a video."""
    return (channel in COVER_CHANNELS or channel in COVER_SERVICES) and 'video' in set(kinds or ())


def offset_ok(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def resolve_cover(manifest_cover=None, library_cover=None):
    """The cover a video posts with: the manifest's for its channel first, else the library's designed tall cover.

    Each is {"path" or "asset", "sha256"} as its source names it. Raises CoverHold when there is none."""
    for source, cover in (('manifest', manifest_cover), ('library', library_cover)):
        if isinstance(cover, dict) and (cover.get('path') or cover.get('asset')):
            return dict(cover, source=source)
    raise CoverHold('video_without_designed_cover')


def _tools():
    for name in ('ffmpeg', 'ffprobe'):
        if not shutil.which(name):
            raise CoverHold('ffmpeg_missing')


def _run(args):
    try:
        return subprocess.run(args, check=True, capture_output=True, timeout=TIMEOUT).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        raise CoverHold('ffmpeg_failed') from None


def probe(path):
    """{width, height, fps, duration_ms, audio} of a video file."""
    _tools()
    raw = _run(['ffprobe', '-v', 'error', '-show_entries',
                'stream=codec_type,width,height,r_frame_rate:format=duration', '-of', 'json', str(path)])
    data = json.loads(raw.decode('utf-8'))
    video = next((s for s in data.get('streams') or [] if s.get('codec_type') == 'video'), None)
    if not video:
        raise CoverHold('not_a_video')
    num, _, den = (video.get('r_frame_rate') or '30/1').partition('/')
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {'width': int(video['width']), 'height': int(video['height']), 'fps': round(fps, 3) or 30.0,
            'duration_ms': int(round(float((data.get('format') or {}).get('duration') or 0) * 1000)),
            'audio': any(s.get('codec_type') == 'audio' for s in data.get('streams') or [])}


def _fit(width, height):
    return ('scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=%s,setsar=1'
            % (width, height, width, height, INK))


def append_cover(cut, cover, out, seconds=HOLD_SECONDS):
    """Write cut + its cover held for `seconds` to out. Returns {offset_ms, duration_ms, sha256}.

    The offset is the middle of the cover's hold, so a platform that rounds to a keyframe or a frame still lands
    on the cover. Never overwrites the cut."""
    cut, cover, out = Path(cut), Path(cover), Path(out)
    if not cut.is_file() or not cover.is_file():
        raise CoverHold('cover_or_cut_missing')
    if out.resolve() == cut.resolve():
        raise CoverHold('would_overwrite_cut')
    info = probe(cut)
    w, h, fps = info['width'], info['height'], info['fps']
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(cut),
            '-loop', '1', '-framerate', str(fps), '-t', str(seconds), '-i', str(cover)]
    chain = '[0:v]' + _fit(w, h) + ',fps=%s,format=yuv420p[v0];[1:v]' % fps + _fit(w, h) + \
            ',fps=%s,format=yuv420p,trim=duration=%s[v1];' % (fps, seconds)
    if info['audio']:
        args += ['-f', 'lavfi', '-t', str(seconds), '-i', 'anullsrc=r=48000:cl=stereo']
        chain += ('[0:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a0];'
                  '[2:a]aformat=sample_fmts=fltp:channel_layouts=stereo[a1];'
                  '[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]')
        maps = ['-map', '[v]', '-map', '[a]', '-c:a', 'aac', '-b:a', '192k']
    else:
        chain += '[v0][v1]concat=n=2:v=1:a=0[v]'
        maps = ['-map', '[v]']
    _run(args + ['-filter_complex', chain] + maps +
         ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
          str(out)])
    total = probe(out)['duration_ms']
    # The cover starts where the cut ends; an audio encoder may pad the file's end, so count from the cut.
    offset = min(info['duration_ms'] + int(round(seconds * 1000 / 2)), max(0, total - 1))
    return {'offset_ms': offset, 'duration_ms': total, 'cut_duration_ms': info['duration_ms'],
            'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}


def _raw(args):
    """One frame as raw RGB bytes at the compare size (ffmpeg only, so the check needs no imaging library)."""
    data = _run(['ffmpeg', '-hide_banner', '-loglevel', 'error'] + args +
                ['-frames:v', '1', '-vf', 'scale=%d:%d' % COMPARE, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
    if len(data) != COMPARE[0] * COMPARE[1] * 3:
        raise CoverHold('offset_past_end')
    return data


def frame_rmse(video, offset_ms, cover):
    """Root mean square error (0 to 1) between the frame at offset_ms and the cover fitted to the video's frame."""
    info = probe(video)
    with tempfile.TemporaryDirectory() as tmp:
        fitted = Path(tmp) / 'cover.png'
        _run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(cover),
              '-vf', _fit(info['width'], info['height']), '-frames:v', '1', str(fitted)])
        a = _raw(['-ss', '%.3f' % (offset_ms / 1000.0), '-i', str(video)])
        b = _raw(['-i', str(fitted)])
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a)) / 255.0


def cover_frame_errors(video, offset_ms, cover):
    """[] when the frame at offset_ms is the designed cover, else the hold codes."""
    if not offset_ok(offset_ms):
        return ['video_without_cover_offset']
    try:
        rmse = frame_rmse(video, offset_ms, cover)
    except CoverHold as hold:
        return [hold.code]
    return [] if rmse < RMSE_LIMIT else ['cover_frame_not_designed']


def prepare(cut, cover, out, seconds=HOLD_SECONDS):
    """Append the cover, then prove the frame at the offset is it. Returns the append result with its rmse."""
    result = append_cover(cut, cover, out, seconds)
    rmse = frame_rmse(out, result['offset_ms'], cover)
    if rmse >= RMSE_LIMIT:
        Path(out).unlink(missing_ok=True)
        raise CoverHold('cover_frame_not_designed')
    return dict(result, rmse=round(rmse, 4))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run cover',
                                     description='Append a video\'s designed cover as its last second and give '
                                                 'the thumbnailOffset Buffer needs, or check one.')
    parser.add_argument('command', choices=['cover'])
    sub = parser.add_subparsers(dest='action', required=True)
    add = sub.add_parser('append', help='cut + cover -> a new file and its thumbnailOffset')
    add.add_argument('--cut', required=True)
    add.add_argument('--cover', help='the designed tall cover (the manifest\'s for the channel, else the library\'s)')
    add.add_argument('--out', required=True)
    add.add_argument('--seconds', type=float, default=HOLD_SECONDS)
    check = sub.add_parser('check', help='is the frame at --offset-ms the cover')
    check.add_argument('video')
    check.add_argument('--offset-ms', type=int, required=True)
    check.add_argument('--cover', required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'append':
            resolve_cover(library_cover={'path': args.cover} if args.cover else None)
            print(json.dumps(dict(prepare(args.cut, args.cover, args.out, args.seconds), ok=True), indent=1))
            return 0
        errors = cover_frame_errors(args.video, args.offset_ms, args.cover)
        print(json.dumps({'ok': not errors, 'holds': errors}, indent=1))
        return 0 if not errors else 1
    except CoverHold as hold:
        print(json.dumps({'ok': False, 'holds': [hold.code]}, indent=1))
        return 1
