"""The tall meme with a clip, centred by construction (Ruling, Krish, 2026-11-15).

His words, on Friday 13 Nov's "POV: your AI agent using your computer" meme: "The POV computer meme, it's not
centralized on the screen." It was made by hand: its whole group sat 40 px left of centre and 177 px high, with a third
of the frame empty below. So a tall meme with a clip is made from one template and one composer, never by hand:

1. `render/templates/meme-tall.html` draws the frame: the headline centred above a fixed clip window (x 200 to 880,
   y 600 to 1240), the wordmark and the credit centred under it, all inside the clear box every channel leaves
   (content-engine config/channel-safe-zones.json: y 270 to 1320, nothing past x 880 from y 520). The renderer
   reports the window as a slot, and `growth.py run kit painted` refuses one that is off centre (engine/run/kits.py).
2. `compose` puts the clip into that window, scaled to fit inside it with its own shape and centred in it, over the
   still frame, for the clip's length and with its sound. `placement` says where it lands, and `placement_errors`
   holds a placement that is off centre or outside the clear box.

Nothing here posts. The finished file is filed by the session (content-engine's send.py), and posting it goes through
the cover step like every video (engine/run/video_cover.py).
"""
import argparse
import json
from pathlib import Path

from .kits import SLOT_TOLERANCE, TALL_CLEAR
from .video_cover import CoverHold, _run, probe

CANVAS = (1080, 1920)
WINDOW = (200, 600, 680, 640)  # x, y, width, height of render/templates/meme-tall.html's clip window


def placement(width, height, window=WINDOW):
    """Where a clip of width x height lands in the window: [x, y, w, h], fitted inside it and centred, even sizes."""
    wx, wy, ww, wh = window
    scale = min(ww / float(width), wh / float(height))
    w, h = int(width * scale) // 2 * 2, int(height * scale) // 2 * 2
    return [wx + (ww - w) // 2, wy + (wh - h) // 2, w, h]


def placement_errors(box):
    """Off centre or outside the clear box, as kits.layout_errors says it for a slot."""
    x, y, w, h = box
    dx, dy = x + w / 2.0 - CANVAS[0] / 2.0, y + h / 2.0 - CANVAS[1] / 2.0
    out = []
    if abs(dx) > SLOT_TOLERANCE[0] or abs(dy) > SLOT_TOLERANCE[1]:
        out.append('clip_off_centre')
    if x < TALL_CLEAR['left'] or x + w > TALL_CLEAR['rail_x'] or y < TALL_CLEAR['top'] or y + h > TALL_CLEAR['bottom']:
        out.append('clip_outside_clear_box')
    return out


def compose(frame, clip, out):
    """The frame PNG with the clip in its window, as an H.264 file at 1080x1920. Returns {box, duration_ms}."""
    frame, clip, out = Path(frame), Path(clip), Path(out)
    if not frame.is_file() or not clip.is_file():
        raise CoverHold('frame_or_clip_missing')
    if out.resolve() in (frame.resolve(), clip.resolve()):
        raise CoverHold('would_overwrite_input')
    info = probe(clip)
    box = placement(info['width'], info['height'])
    errors = placement_errors(box)
    if errors:
        raise CoverHold(errors[0])
    x, y, w, h = box
    chain = ('[0:v]scale=%d:%d,setsar=1[bg];[1:v]scale=%d:%d,setsar=1[c];[bg][c]overlay=%d:%d:shortest=1,'
             'format=yuv420p[v]' % (CANVAS[0], CANVAS[1], w, h, x, y))
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-loop', '1', '-framerate', str(info['fps']),
            '-i', str(frame), '-i', str(clip), '-filter_complex', chain, '-map', '[v]']
    if info['audio']:
        args += ['-map', '1:a', '-c:a', 'aac', '-b:a', '192k']
    _run(args + ['-t', '%.3f' % (info['duration_ms'] / 1000.0), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                 '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(out)])
    return {'box': box, 'duration_ms': probe(out)['duration_ms']}


def main(argv=None):
    parser = argparse.ArgumentParser(prog='growth.py run meme',
                                     description='Put a clip into the tall meme frame, fitted and centred.')
    parser.add_argument('command', choices=['meme'])
    parser.add_argument('action', choices=['compose'])
    parser.add_argument('--frame', required=True, help='the rendered meme-tall PNG')
    parser.add_argument('--clip', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(dict(compose(args.frame, args.clip, args.out), ok=True), indent=1))
        return 0
    except CoverHold as hold:
        print(json.dumps({'ok': False, 'holds': [hold.code]}, indent=1))
        return 1
