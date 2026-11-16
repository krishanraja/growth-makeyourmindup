#!/usr/bin/env node
// codex_thread.mjs: the one way Claude starts and talks to Codex (Ruling, Krish, 2026-11-15: "Claude starts Codex only
// through scripts/codex_thread.mjs"). Each command connects to Codex Desktop's own app-server daemon for one turn, so
// the thread is made in the server Desktop runs, shows in his Codex Desktop sidebar with Desktop's tools (the in-app
// browser included), and is never held open: Claude and Krish take turns on the same thread. It never uses the Codex
// plugin's long-running broker.
//
//   node scripts/codex_thread.mjs open [options] "<message>"   a permanent thread titled by the message's first line;
//                                                              runs that first message, prints the thread id
//   node scripts/codex_thread.mjs send [options] <thread> "<message>"   one turn on the thread, then it is released
//   node scripts/codex_thread.mjs read <thread>                 the thread's turns from its session file, Desktop's too
//
// Options: --cwd DIR (default: here), --prompt-file FILE (the message from a file), --sandbox read-only|workspace-write
// (default read-only), --model M, --effort E, --home DIR (default: VE_CODEX_DESKTOP_HOME, else ~/.codex), --json,
// --detach (open or send runs on in the background; its output, the thread id first, goes to --log FILE).
// Canonical copy: krishanraja/ai-harness scripts/codex_thread.mjs (Ruling, Krish, 2026-11-15). Change it there first,
// then copy it unchanged to the same path in every repository that starts Codex; ai-harness checks the copies match.
import { spawn } from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const USAGE = 'usage: codex_thread.mjs open [opts] "<message>" | send [opts] <thread> "<message>" | read <thread> [--json]';

export function parseArgs(argv) {
  const opts = { positional: [] };
  const valued = new Set(['--cwd', '--prompt-file', '--sandbox', '--model', '--effort', '--home', '--log']);
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (valued.has(arg)) {
      if (i + 1 >= argv.length) throw new Error(`${arg} needs a value`);
      opts[arg.slice(2).replace('-f', 'F')] = argv[++i];
    } else if (arg === '--json') {
      opts.json = true;
    } else if (arg === '--detach') {
      opts.detach = true;
    } else {
      opts.positional.push(arg);
    }
  }
  return opts;
}

export function codexHome(opts = {}) {
  return path.resolve(opts.home || process.env.VE_CODEX_DESKTOP_HOME || path.join(os.homedir(), '.codex'));
}

export function firstLine(text) {
  return String(text).split(/\r?\n/).map((l) => l.trim()).find(Boolean)?.slice(0, 120) || 'Codex thread';
}

// ---- reading a thread from its session file ---------------------------------------------------------------------

export function findSessionFile(home, threadId) {
  for (const root of [path.join(home, 'sessions'), path.join(home, 'archived_sessions')]) {
    const stack = [root];
    while (stack.length) {
      const dir = stack.pop();
      let entries;
      try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { continue; }
      for (const e of entries) {
        const full = path.join(dir, e.name);
        if (e.isDirectory()) stack.push(full);
        else if (e.name.endsWith('.jsonl') && e.name.includes(threadId)) return full;
      }
    }
  }
  return null;
}

function itemText(item) {
  return (item.content || []).map((c) => c.text || '').filter(Boolean).join('\n');
}

// The turns as the session file records them: each completed UserMessage (Claude's or Krish's in Desktop) and
// AgentMessage, in order. Injected context (AGENTS.md, environment) is not a UserMessage item and is left out.
export function readTurns(file) {
  const turns = [];
  let meta = {};
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    if (!line.trim()) continue;
    let o;
    try { o = JSON.parse(line); } catch { continue; }
    const p = o.payload || {};
    if (o.type === 'session_meta') meta = { id: p.id, cwd: p.cwd, originator: p.originator, source: p.source };
    if (o.type === 'event_msg' && p.type === 'item_completed' && p.item) {
      const role = p.item.type === 'UserMessage' ? 'user' : p.item.type === 'AgentMessage' ? 'codex' : null;
      if (role) turns.push({ at: o.timestamp, turn: p.turn_id, role, text: itemText(p.item) });
    }
  }
  return { meta, turns };
}

// ---- driving Codex Desktop's own app-server ----------------------------------------------------------------------
// Every command talks to the app-server daemon Codex Desktop itself runs, through `codex app-server proxy`, which
// bridges stdio to its control socket. The thread therefore lives in the same server as Desktop: it appears in Krish's
// sidebar as it is made, he can open and type in it, and its turns run with Desktop's tools, the in-app browser
// included. Spawning a private `codex app-server` (what this did before 16 Nov 2026) saved the thread to disk but kept
// it out of Desktop's list and ran its turns with no browser (Krish, 2026-11-16: "we need to fix your ability to open a
// codex desktop session I can see and use alongside you"). If the daemon is not reachable the command fails and says
// so. It never falls back to a private server, because that thread would be invisible.
// The control socket speaks WebSocket: one HTTP upgrade, then one JSON-RPC message per text frame.

const HANDSHAKE_MS = 15000;

class AppServer {
  constructor(home, cwd) {
    const env = { ...process.env, CODEX_HOME: home };
    delete env.CODEX_COMPANION_APP_SERVER_ENDPOINT;
    this.proc = spawn('codex', ['app-server', 'proxy'], { cwd, env, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
    this.next = 1;
    this.pending = new Map();
    this.listeners = [];
    this.stderr = '';
    this.buf = Buffer.alloc(0);
    this.fragments = [];
    this.upgraded = false;
    this.ready = new Promise((resolve, reject) => { this.onReady = resolve; this.onReadyFail = reject; });
    this.ready.catch(() => {});
    this.proc.stderr.on('data', (d) => { this.stderr = (this.stderr + d).slice(-4000); });
    this.exited = new Promise((resolve) => this.proc.on('exit', resolve));
    this.proc.on('error', (error) => this.failAll(error));
    this.proc.on('exit', (code) => this.failAll(new Error((this.upgraded
      ? `Codex Desktop's app-server connection closed (${code})`
      : `Codex Desktop's app-server is not reachable from ${home}: open Codex Desktop (\`codex app-server daemon version\` says whether its daemon runs), then retry (${code})`)
      + ` ${this.stderr.trim().split('\n').pop() || ''}`.trimEnd())));
    this.proc.stdout.on('data', (d) => this.onData(d));
    this.proc.stdin.write('GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
      + `Sec-WebSocket-Key: ${crypto.randomBytes(16).toString('base64')}\r\nSec-WebSocket-Version: 13\r\n\r\n`);
    this.handshakeTimer = setTimeout(() => this.failAll(new Error("Codex Desktop's app-server did not answer: open Codex "
      + 'Desktop (`codex app-server daemon version` says whether its daemon runs), then retry')), HANDSHAKE_MS);
  }

  failAll(error) {
    clearTimeout(this.handshakeTimer);
    this.onReadyFail(error);
    for (const { reject } of this.pending.values()) reject(error);
    this.pending.clear();
    for (const l of this.listeners) l.reject?.(error);
  }

  onData(chunk) {
    this.buf = Buffer.concat([this.buf, chunk]);
    if (!this.upgraded) {
      const end = this.buf.indexOf('\r\n\r\n');
      if (end < 0) return;
      const head = this.buf.subarray(0, end).toString('latin1');
      this.buf = this.buf.subarray(end + 4);
      if (!/^HTTP\/1\.1 101/.test(head)) {
        this.failAll(new Error(`Codex Desktop's app-server refused the connection: ${head.split('\r\n')[0]}`));
        return;
      }
      this.upgraded = true;
      clearTimeout(this.handshakeTimer);
      this.onReady();
    }
    this.readFrames();
  }

  readFrames() {
    for (;;) {
      if (this.buf.length < 2) return;
      const fin = this.buf[0] & 0x80;
      const op = this.buf[0] & 0x0f;
      let len = this.buf[1] & 0x7f;
      let off = 2;
      if (len === 126) { if (this.buf.length < 4) return; len = this.buf.readUInt16BE(2); off = 4; }
      else if (len === 127) { if (this.buf.length < 10) return; len = Number(this.buf.readBigUInt64BE(2)); off = 10; }
      if (this.buf.length < off + len) return;
      const payload = this.buf.subarray(off, off + len);
      this.buf = this.buf.subarray(off + len);
      if (op === 0x9) { this.frame(0xa, payload); continue; } // ping: answer with a pong
      if (op === 0xa) continue;
      if (op === 0x8) { this.failAll(new Error("Codex Desktop's app-server closed the connection")); return; }
      this.fragments.push(payload);
      if (!fin) continue;
      const text = Buffer.concat(this.fragments).toString('utf8');
      this.fragments = [];
      this.onLine(text);
    }
  }

  // One client frame (RFC 6455); every frame a client sends is masked.
  frame(op, data) {
    const mask = crypto.randomBytes(4);
    let head;
    if (data.length < 126) head = Buffer.from([0x80 | op, 0x80 | data.length]);
    else if (data.length < 65536) { head = Buffer.alloc(4); head[0] = 0x80 | op; head[1] = 0x80 | 126; head.writeUInt16BE(data.length, 2); }
    else { head = Buffer.alloc(10); head[0] = 0x80 | op; head[1] = 0x80 | 127; head.writeBigUInt64BE(BigInt(data.length), 2); }
    const masked = Buffer.alloc(data.length);
    for (let i = 0; i < data.length; i += 1) masked[i] = data[i] ^ mask[i % 4];
    this.proc.stdin.write(Buffer.concat([head, mask, masked]));
  }

  onLine(line) {
    let msg;
    try { msg = JSON.parse(line); } catch { return; }
    if (msg.id !== undefined && (msg.result !== undefined || msg.error !== undefined) && this.pending.has(msg.id)) {
      const { resolve, reject } = this.pending.get(msg.id);
      this.pending.delete(msg.id);
      if (msg.error) reject(new Error(`${msg.error.message || JSON.stringify(msg.error)}`));
      else resolve(msg.result);
      return;
    }
    if (msg.id !== undefined && msg.method) {
      // A request from the server (an approval). Runs use approval "never", so decline anything that still asks.
      this.write({ id: msg.id, error: { code: -32601, message: 'codex_thread.mjs answers no server requests' } });
      return;
    }
    if (msg.method) for (const l of [...this.listeners]) l.onNotification(msg);
  }

  write(obj) { this.frame(0x1, Buffer.from(JSON.stringify(obj), 'utf8')); }

  request(method, params) {
    const id = this.next++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.write({ id, method, params });
    });
  }

  async start() {
    await this.ready;
    await this.request('initialize', { clientInfo: { name: 'codex_thread', title: 'Claude (codex_thread.mjs)', version: '1.1.0' }, capabilities: {} });
    this.write({ method: 'initialized', params: {} });
  }

  // One turn: resolves with the turn's status and Codex's last message once turn/completed arrives for this thread.
  runTurn(threadId, text, opts) {
    return new Promise((resolve, reject) => {
      let last = '';
      const listener = {
        reject,
        onNotification: (msg) => {
          const p = msg.params || {};
          if (msg.method === 'item/completed' && p.threadId === threadId && p.item?.type === 'agentMessage') last = p.item.text || last;
          if (msg.method === 'turn/completed' && p.threadId === threadId) {
            this.listeners = this.listeners.filter((l) => l !== listener);
            resolve({ status: p.turn?.status || 'unknown', message: last, error: p.turn?.error?.message || null });
          }
        },
      };
      this.listeners.push(listener);
      this.request('turn/start', {
        threadId,
        input: [{ type: 'text', text, text_elements: [] }],
        model: opts.model ?? null,
        effort: opts.effort ?? null,
      }).catch(reject);
    });
  }

  async close() {
    clearTimeout(this.handshakeTimer);
    try { if (this.upgraded) this.frame(0x8, Buffer.from([0x03, 0xe8])); } catch { /* already closed */ }
    try { this.proc.stdin.end(); } catch { /* already closed */ }
    const timer = setTimeout(() => { try { this.proc.kill(); } catch { /* gone */ } }, 5000);
    await this.exited;
    clearTimeout(timer);
  }
}

function threadParams(cwd, opts) {
  return { cwd, model: opts.model ?? null, approvalPolicy: 'never', sandbox: opts.sandbox || 'read-only' };
}

function message(opts, index) {
  if (opts.promptFile) return fs.readFileSync(opts.promptFile, 'utf8');
  const text = opts.positional[index];
  if (!text) throw new Error(USAGE);
  return text;
}

async function withServer(home, cwd, fn) {
  const server = new AppServer(home, cwd);
  try {
    await server.start();
    return await fn(server);
  } finally {
    await server.close();
  }
}

export async function open(opts) {
  const home = codexHome(opts);
  const cwd = path.resolve(opts.cwd || process.cwd());
  const text = message(opts, 1);
  return withServer(home, cwd, async (server) => {
    const started = await server.request('thread/start', { ...threadParams(cwd, opts), ephemeral: false });
    const threadId = started.thread.id;
    console.error(`thread ${threadId} opened in ${home}`);
    try { await server.request('thread/name/set', { threadId, name: firstLine(text) }); } catch { /* older servers name it from the message */ }
    const turn = await server.runTurn(threadId, text, opts);
    return { thread: threadId, home, ...turn };
  });
}

export async function send(opts) {
  const home = codexHome(opts);
  const threadId = opts.positional[1];
  if (!threadId) throw new Error(USAGE);
  const file = findSessionFile(home, threadId);
  const cwd = path.resolve(opts.cwd || (file && readTurns(file).meta.cwd) || process.cwd());
  const text = message(opts, 2);
  return withServer(home, cwd, async (server) => {
    await server.request('thread/resume', { threadId, ...threadParams(cwd, opts) });
    const turn = await server.runTurn(threadId, text, opts);
    return { thread: threadId, home, ...turn };
  });
}

export function read(opts) {
  const home = codexHome(opts);
  const threadId = opts.positional[1];
  if (!threadId) throw new Error(USAGE);
  const file = findSessionFile(home, threadId);
  if (!file) throw new Error(`no session file for ${threadId} under ${home}`);
  return { thread: threadId, file, ...readTurns(file) };
}

// --detach: the same command runs on in a detached child, so the caller (ve dispatch) returns at once; the child still
// releases the thread when its turn ends.
function detach(opts) {
  const args = process.argv.slice(2).filter((a) => a !== '--detach');
  const log = path.resolve(opts.log || path.join(os.tmpdir(), `codex_thread-${Date.now()}.log`));
  fs.mkdirSync(path.dirname(log), { recursive: true });
  const fd = fs.openSync(log, 'a');
  const child = spawn(process.execPath, [process.argv[1], ...args], { detached: true, stdio: ['ignore', fd, fd], windowsHide: true });
  child.unref();
  console.log(`codex_thread: ${opts.positional[0]} runs on in the background (pid ${child.pid}); its log, thread id first: ${log}`);
  return 0;
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const command = opts.positional[0];
  if (opts.detach && (command === 'open' || command === 'send')) return detach(opts);
  if (command === 'read') {
    const out = read(opts);
    if (opts.json) console.log(JSON.stringify(out, null, 2));
    else for (const t of out.turns) console.log(`[${t.at}] ${t.role}:\n${t.text}\n`);
    return 0;
  }
  if (command !== 'open' && command !== 'send') { console.error(USAGE); return 2; }
  const out = command === 'open' ? await open(opts) : await send(opts);
  if (opts.json) console.log(JSON.stringify(out, null, 2));
  else {
    console.log(`thread ${out.thread} (${out.home}): turn ${out.status}; released`);
    if (out.message) console.log(out.message);
    if (out.error) console.error(out.error);
  }
  return out.status === 'completed' ? 0 : 1;
}

const invoked = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
if (invoked) {
  main().then((code) => process.exit(code), (error) => { console.error(`codex_thread: ${error.message}`); process.exit(1); });
}
