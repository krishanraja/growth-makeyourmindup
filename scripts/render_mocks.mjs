#!/usr/bin/env node
// Render mock PNGs from the kit templates in render/, with headless Chromium through Playwright.
//
//   node scripts/render_mocks.mjs JOBS.json [--out-dir DIR] [--manifest FILE] [--verify]
//
// JOBS.json is a list of {template, fields, out}: template is an id in render/templates.json,
// fields fills its placeholders, out is the PNG path (relative paths resolve against --out-dir,
// or the folder JOBS.json is in). A job may instead be {video: [png, ...], seconds, out}, seconds one
// number or one per frame: a
// slideshow of already rendered PNGs, padded onto a 1080x1920 ink frame, encoded with ffmpeg
// bit-exactly (YouTube takes video, never a still). Video jobs run after every PNG job.
//
// This is the one script in the repository that is not standard library Python: it needs Node
// and Playwright's Chromium (never installed from here). The engine never imports it, and
// growth.py --self-test never runs it.
//
// Deterministic: every request the page makes is served from render/ or refused, so nothing
// reaches the network; fonts are vendored; text is fitted by fixed steps (render/fit.js); and
// any text or time chunk is stripped from each PNG, so the same input gives the same bytes.
// --verify renders every job twice and fails unless both sha256 values agree.
// A job whose words do not fit its box at the smallest size, whose fonts did not load, or
// whose fields carry an em dash, is refused; nothing is clipped silently. Each result names the colours
// and fonts the page really painted with, so a test can hold them to the kit.

import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RENDER = path.join(ROOT, 'render');
const ORIGIN = 'http://mocks.invalid';
const EM_DASH = /\u2014/;
const TYPES = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.ttf': 'font/ttf' };

function loadPlaywright() {
  try { return require('playwright'); } catch (e) { /* fall through */ }
  try {
    const root = execFileSync('npm', ['root', '-g'], { encoding: 'utf8' }).trim();
    return require(path.join(root, 'playwright'));
  } catch (e) {
    throw new Error('Playwright is not available to Node; this script never installs it');
  }
}

export function escapeHtml(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function textHtml(value) {
  return escapeHtml(value).replace(/\r\n?/g, '\n').split('\n').join('<br>');
}

// A value may hold an arrow ("$2 → $4"); it is drawn in CSS (.arrow), so no font has to carry the glyph.
function valueHtml(value) {
  return String(value).split(/\s*(?:\u2192|->)\s*/).map(textHtml).join('<span class="arrow" role="img" aria-label="to"></span>');
}

function rowsHtml(rows) {
  if (!Array.isArray(rows) || !rows.length || !rows.every((r) => Array.isArray(r) && (r.length === 2 || r.length === 3))) {
    throw new Error('rows must be a list of [name, value] pairs or [name, note, value] triples');
  }
  return rows.map((r) => {
    const name = r.length === 3
      ? '<span class="name"><span class="main">' + textHtml(r[0]) + '</span><span class="note">' + textHtml(r[1]) + '</span></span>'
      : '<span class="name">' + textHtml(r[0]) + '</span>';
    return '<div class="row">' + name + '<span class="value">' + valueHtml(r[r.length - 1]) + '</span></div>';
  }).join('');
}

function optionsHtml(options) {
  if (!Array.isArray(options) || !options.length || options.length > 4) throw new Error('options must be a list of one to four answers');
  return options.map((o, i) => '<div class="option"><span class="key">' + 'ABCD'[i] + '</span><span class="text">'
    + textHtml(o) + '</span></div>').join('');
}

function strings(value) {
  return Array.isArray(value) ? value.flat(Infinity).map(String) : [String(value)];
}

export function fill(manifest, job) {
  const spec = manifest.templates[job.template];
  if (!spec) throw new Error('unknown template ' + JSON.stringify(job.template));
  const fields = job.fields || {};
  const unknown = Object.keys(fields).filter((k) => !(k in spec.fields));
  if (unknown.length) throw new Error(job.template + ': unknown field(s) ' + unknown.join(', '));
  const missing = spec.required.filter((k) => fields[k] === undefined || fields[k] === null || fields[k] === '');
  if (missing.length) throw new Error(job.template + ': missing field(s) ' + missing.join(', '));
  for (const [k, v] of Object.entries(fields)) {
    if (strings(v).some((s) => EM_DASH.test(s))) throw new Error(job.template + ': field ' + k + ' has an em dash');
  }
  for (const [k, allowed] of Object.entries(spec.choices || {})) {
    if (fields[k] !== undefined && fields[k] !== '' && !allowed.includes(fields[k])) {
      throw new Error(job.template + ': ' + k + ' is one of ' + allowed.join(', ') + ', not ' + JSON.stringify(fields[k]));
    }
  }
  let html = fs.readFileSync(path.join(RENDER, spec.file), 'utf8');
  html = html.replace(/\{\{(?:(rows|options):)?([a-z0-9_]+)\}\}/g, (_, kind, name) => {
    const declared = spec.fields[name];
    if (!declared) throw new Error(spec.file + ' names a field the manifest does not: ' + name);
    const value = fields[name];
    if (value === undefined || value === null) return '';
    if ((kind || 'text') !== declared) throw new Error(spec.file + ': ' + name + ' is ' + declared + ', not ' + (kind || 'text'));
    if (declared === 'rows') return rowsHtml(value);
    if (declared === 'options') return optionsHtml(value);
    return textHtml(value);
  });
  return { spec, html };
}

// Keep only the chunks that carry the picture; a text or time chunk would make bytes differ.
export function stripPng(buf) {
  const sig = buf.subarray(0, 8);
  const keep = [sig];
  let i = 8;
  while (i < buf.length) {
    const len = buf.readUInt32BE(i);
    const type = buf.toString('latin1', i + 4, i + 8);
    const end = i + 12 + len;
    if (!['tEXt', 'zTXt', 'iTXt', 'tIME'].includes(type)) keep.push(buf.subarray(i, end));
    i = end;
  }
  return Buffer.concat(keep);
}

function sha256(buf) { return createHash('sha256').update(buf).digest('hex'); }

async function renderOne(browser, manifest, job) {
  const { spec, html } = fill(manifest, job);
  const page = await browser.newPage({ viewport: { width: spec.width, height: spec.height }, deviceScaleFactor: 1 });
  try {
    await page.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      if (url.origin !== ORIGIN) return route.abort();
      if (url.pathname === '/' + spec.file) return route.fulfill({ status: 200, contentType: TYPES['.html'], body: html });
      const file = path.normalize(path.join(RENDER, decodeURIComponent(url.pathname)));
      if (!file.startsWith(RENDER + path.sep) || !fs.existsSync(file)) return route.abort();
      return route.fulfill({ status: 200, contentType: TYPES[path.extname(file)] || 'application/octet-stream',
        body: fs.readFileSync(file) });
    });
    await page.goto(ORIGIN + '/' + spec.file, { waitUntil: 'load' });
    const report = await page.evaluate(async () => {
      const faces = Array.from(document.fonts);
      await Promise.all(faces.map((f) => f.load().catch(() => null)));
      await document.fonts.ready;
      const unloaded = faces.filter((f) => f.status !== 'loaded').map((f) => f.family + ' ' + f.weight);
      const errors = window.__fit ? window.__fit() : ['render/fit.js did not load'];
      const frame = document.querySelector('.frame');
      if (frame && (frame.scrollHeight > frame.clientHeight + 1 || frame.scrollWidth > frame.clientWidth + 1)) {
        errors.push('the page overflows its frame');
      }
      // What the page really painted with: every colour and the first font of every element that shows text.
      const hex = (c) => {
        const m = /^rgba?\((\d+), (\d+), (\d+)(?:, ([\d.]+))?\)$/.exec(c);
        if (!m || m[4] === '0') return null;
        return '#' + [m[1], m[2], m[3]].map((n) => Number(n).toString(16).padStart(2, '0')).join('').toUpperCase();
      };
      const colours = new Set();
      const fonts = new Set();
      for (const el of [document.documentElement, ...document.querySelectorAll('*')]) {
        for (const pseudo of [null, '::before', '::after']) {
          const st = getComputedStyle(el, pseudo);
          if (st.display === 'none' || (pseudo && st.content === 'none')) continue;
          [st.color, st.backgroundColor, st.webkitTextStrokeColor].forEach((c) => { const h = hex(c); if (h) colours.add(h); });
          for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
            if (parseFloat(st['border' + side + 'Width']) > 0 && st['border' + side + 'Style'] !== 'none') {
              const h = hex(st['border' + side + 'Color']); if (h) colours.add(h);
            }
          }
          for (const m of st.backgroundImage.matchAll(/rgba?\([^)]*\)/g)) { const h = hex(m[0]); if (h) colours.add(h); }
          if (!pseudo && Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim())) {
            fonts.add(st.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, ''));
          }
        }
      }
      return { unloaded, errors, faces: faces.length, colours: [...colours].sort(), fonts: [...fonts].sort() };
    });
    if (!report.faces || report.unloaded.length) throw new Error(job.out + ': fonts did not load: ' + report.unloaded.join(', '));
    if (report.errors.length) throw new Error(job.out + ': ' + report.errors.join('; '));
    const png = await page.screenshot({ type: 'png', animations: 'disabled', caret: 'hide', scale: 'css',
      clip: { x: 0, y: 0, width: spec.width, height: spec.height } });
    return { png: stripPng(Buffer.from(png)), colours: report.colours, fonts: report.fonts };
  } finally {
    await page.close();
  }
}

function renderVideo(job, base) {
  const frames = job.video.map((f) => path.resolve(base, f));
  const seconds = Array.isArray(job.seconds) ? job.seconds.map(Number) : frames.map(() => Number(job.seconds || 3));
  if (!frames.length || seconds.length !== frames.length || !seconds.every((s) => s > 0)) {
    throw new Error(job.out + ': a video job needs frames and a positive seconds for each (one number or a list)');
  }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mocks-'));
  try {
    const list = frames.map((f, i) => "file '" + f.replace(/'/g, "'\\''") + "'\nduration " + seconds[i]).join('\n')
      + "\nfile '" + frames[frames.length - 1].replace(/'/g, "'\\''") + "'\n";
    fs.writeFileSync(path.join(dir, 'list.txt'), list);
    const tmp = path.join(dir, 'out.mp4');
    execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(dir, 'list.txt'),
      '-vf', 'scale=1080:-2:flags=bicubic,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x0C1512,fps=30,format=yuv420p',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-threads', '1', '-x264-params', 'threads=1:sliced-threads=0',
      '-an', '-map_metadata', '-1', '-fflags', '+bitexact', '-flags:v', '+bitexact', '-movflags', '+faststart', tmp]);
    return fs.readFileSync(tmp);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

async function main(argv) {
  const args = { verify: false };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--verify') args.verify = true;
    else if (argv[i] === '--out-dir') args.outDir = argv[++i];
    else if (argv[i] === '--manifest') args.manifest = argv[++i];
    else rest.push(argv[i]);
  }
  if (rest.length !== 1) {
    console.error('usage: node scripts/render_mocks.mjs JOBS.json [--out-dir DIR] [--manifest FILE] [--verify]');
    return 2;
  }
  const jobs = JSON.parse(fs.readFileSync(rest[0], 'utf8'));
  if (!Array.isArray(jobs)) throw new Error('the jobs file is a JSON list of {template, fields, out}');
  const base = path.resolve(args.outDir || path.dirname(rest[0]));
  const manifest = JSON.parse(fs.readFileSync(path.join(RENDER, 'templates.json'), 'utf8'));
  const seen = new Set();
  for (const job of jobs) {
    if (!job || typeof job.out !== 'string' || !job.out) throw new Error('every job needs an out path');
    if (seen.has(job.out)) throw new Error('two jobs write ' + job.out);
    seen.add(job.out);
  }
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true,
    args: ['--font-render-hinting=none', '--disable-gpu', '--disable-lcd-text', '--force-color-profile=srgb', '--disable-font-subpixel-positioning'] });
  const results = [];
  try {
    for (const job of jobs.filter((j) => !j.video)) {
      const { png, colours, fonts } = await renderOne(browser, manifest, job);
      const digest = sha256(png);
      if (args.verify) {
        const again = sha256((await renderOne(browser, manifest, job)).png);
        if (again !== digest) throw new Error(job.out + ': two renders differ (' + digest + ' and ' + again + ')');
      }
      const out = path.resolve(base, job.out);
      fs.mkdirSync(path.dirname(out), { recursive: true });
      fs.writeFileSync(out, png);
      results.push({ out: job.out, template: job.template, width: manifest.templates[job.template].width,
        height: manifest.templates[job.template].height, bytes: png.length, sha256: digest, colours, fonts });
    }
  } finally {
    await browser.close();
  }
  for (const job of jobs.filter((j) => j.video)) {
    const mp4 = renderVideo(job, base);
    const digest = sha256(mp4);
    if (args.verify && sha256(renderVideo(job, base)) !== digest) throw new Error(job.out + ': two encodes differ');
    const out = path.resolve(base, job.out);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, mp4);
    results.push({ out: job.out, template: 'video', width: 1080, height: 1920, bytes: mp4.length, sha256: digest,
      frames: job.video, seconds: job.seconds });
  }
  const text = JSON.stringify(results, null, 2) + '\n';
  if (args.manifest) fs.writeFileSync(args.manifest, text);
  process.stdout.write(text);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).then((code) => process.exit(code), (err) => {
    console.error('render_mocks: ' + err.message);
    process.exit(1);
  });
}
