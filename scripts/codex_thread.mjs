#!/usr/bin/env node
// codex_thread.mjs: the one way Claude starts and talks to Codex (Ruling, Krish, 2026-11-15: "Claude starts Codex only
// through scripts/codex_thread.mjs"). It drives `codex app-server` directly, one short-lived server per command, so the
// thread lives in Krish's everyday Codex home, shows in his Codex Desktop app, and is never held open: Claude and Krish
// take turns on the same thread. When Desktop holds the thread (he has it open), `send` queues the message with
// `codex queue` and Desktop runs it as the next turn, with its browser (Ruling, Krish, 2026-11-17).
//
//   node scripts/codex_thread.mjs open [options] "<message>"   a permanent thread titled by the message's first line;
//                                                              runs that first message, prints the thread id
//   node scripts/codex_thread.mjs send [options] <thread> "<message>"   one turn on the thread, then it is released;
//                                                              queued for Desktop when Desktop is the thread's writer
//   node scripts/codex_thread.mjs read <thread>                 the thread's turns from its session file, Desktop's too
//
// Options: --cwd DIR (default: here), --prompt-file FILE (the message from a file), --sandbox read-only|workspace-write
// (default read-only), --model M, --effort E, --home DIR (default: VE_CODEX_DESKTOP_HOME, else ~/.codex), --json,
// --detach (open or send runs on in the background; its output, the thread id first, goes to --log FILE),
// --wait (a send queued for Desktop waits for that turn and prints Codex's last message), --timeout SECONDS (for
// --wait, default 1800). The codex binary: CODEX_THREAD_BIN if set, else found on PATH (on Windows, the native
// codex.exe behind npm's codex.cmd, else Desktop's own). Every failure exits non-zero with a one-line reason.
// Canonical copy: krishanraja/ai-harness scripts/codex_thread.mjs (Ruling, Krish, 2026-11-15). Change it there first,
// then copy it unchanged to the same path in every repository that starts Codex; ai-harness checks the copies match.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline';

const USAGE = 'usage: codex_thread.mjs open [opts] "<message>" | send [opts] <thread> "<message>" | read <thread> [--json]';

export function parseArgs(argv) {
  const opts = { positional: [] };
  const valued = new Set(['--cwd', '--prompt-file', '--sandbox', '--model', '--effort', '--home', '--log', '--timeout']);
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (valued.has(arg)) {
      if (i + 1 >= argv.length) throw new Error(`${arg} needs a value`);
      opts[arg.slice(2).replace('-f', 'F')] = argv[++i];
    } else if (arg === '--json') {
      opts.json = true;
    } else if (arg === '--detach') {
      opts.detach = true;
    } else if (arg === '--wait') {
      opts.wait = true;
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

// ---- finding a runnable codex -----------------------------------------------------------------------------------

const WIN_TRIPLES = { x64: 'x86_64-pc-windows-msvc', arm64: 'aarch64-pc-windows-msvc' };

// The codex to run, as { command, prefix }: prefix is argv placed before codex's own (a .js/.mjs file runs on this
// node). On Windows the npm install puts only codex.cmd and codex.ps1 on PATH, which spawn cannot run without a shell
// (it fails with ENOENT), so this finds the native codex.exe: the one npm installed behind codex.cmd, a codex.exe on
// PATH, then Codex Desktop's own app-server. Pure given its inputs; throws a one-line reason when there is none.
export function resolveCodex({ env = process.env, platform = process.platform, arch = process.arch, homedir = os.homedir(), exists = fs.existsSync } = {}) {
  const forced = env.CODEX_THREAD_BIN;
  if (forced) {
    if (!exists(forced)) throw new Error(`CODEX_THREAD_BIN is ${forced}, which does not exist`);
    return /\.(c|m)?js$/i.test(forced) ? { command: process.execPath, prefix: [forced] } : { command: forced, prefix: [] };
  }
  const dirs = String(env.PATH ?? env.Path ?? '').split(platform === 'win32' ? ';' : ':').filter(Boolean);
  if (platform !== 'win32') {
    for (const dir of dirs) if (exists(path.posix.join(dir, 'codex'))) return { command: path.posix.join(dir, 'codex'), prefix: [] };
    throw new Error('codex is not on PATH; install the Codex CLI (npm i -g @openai/codex)');
  }
  const win = path.win32;
  const tried = [];
  const triple = WIN_TRIPLES[arch] || WIN_TRIPLES.x64;
  for (const dir of dirs) {
    if (!exists(win.join(dir, 'codex.cmd'))) continue;
    const exe = win.join(dir, 'node_modules', '@openai', 'codex', 'node_modules', '@openai', `codex-win32-${arch}`, 'vendor', triple, 'bin', 'codex.exe');
    tried.push(exe);
    if (exists(exe)) return { command: exe, prefix: [] };
  }
  for (const dir of dirs) {
    const exe = win.join(dir, 'codex.exe');
    if (exists(exe)) return { command: exe, prefix: [] };
  }
  const desktop = win.join(homedir, '.codex', 'packages', 'app-server-daemon', 'current', 'bin', 'codex.exe');
  tried.push(desktop);
  if (exists(desktop)) return { command: desktop, prefix: [] };
  throw new Error(`no runnable codex.exe found (looked on PATH and at ${tried.join(', ')})`);
}

function codexEnv(home) {
  const env = { ...process.env, CODEX_HOME: home };
  delete env.CODEX_COMPANION_APP_SERVER_ENDPOINT;
  return env;
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

function parseLines(text) {
  const out = [];
  for (const line of String(text).split(/\r?\n/)) {
    if (!line.trim()) continue;
    try { out.push(JSON.parse(line)); } catch { /* a line still being written */ }
  }
  return out;
}

// The turns as the session file records them: each completed UserMessage (Claude's or Krish's in Desktop) and
// AgentMessage, in order. Injected context (AGENTS.md, environment) is not a UserMessage item and is left out.
export function readTurns(file) {
  const turns = [];
  let meta = {};
  for (const o of parseLines(fs.readFileSync(file, 'utf8'))) {
    const p = o.payload || {};
    if (o.type === 'session_meta') meta = { id: p.id, cwd: p.cwd, originator: p.originator, source: p.source };
    if (o.type === 'event_msg' && p.type === 'item_completed' && p.item) {
      const role = p.item.type === 'UserMessage' ? 'user' : p.item.type === 'AgentMessage' ? 'codex' : null;
      if (role) turns.push({ at: o.timestamp, turn: p.turn_id, role, text: itemText(p.item) });
    }
  }
  return { meta, turns };
}

// Where a queued message stands, from the session file lines written after it was queued. Pure. The turn is the one
// whose UserMessage is the queued text, never a turn someone else queued. Returns null until that turn ends, then
// { status, message, error, turn }.
export function queuedTurnResult(lines, text) {
  const want = String(text).trim();
  let turn = null;
  const last = new Map(), ended = new Map();
  for (const o of lines) {
    const p = o.payload || {};
    if (o.type !== 'event_msg') continue;
    if (p.type === 'item_completed' && p.item?.type === 'UserMessage' && !turn && itemText(p.item).trim() === want) turn = p.turn_id;
    if (p.type === 'item_completed' && p.item?.type === 'AgentMessage') last.set(p.turn_id, itemText(p.item) || last.get(p.turn_id));
    if (p.type === 'task_complete') ended.set(p.turn_id, { status: 'completed', message: p.last_agent_message ?? last.get(p.turn_id) ?? '', error: null });
    if (p.type === 'turn_aborted') ended.set(p.turn_id, { status: 'interrupted', message: last.get(p.turn_id) ?? '', error: `turn aborted${p.reason ? ` (${p.reason})` : ''}` });
  }
  return turn && ended.has(turn) ? { ...ended.get(turn), turn } : null;
}

// ---- driving one short-lived app-server -------------------------------------------------------------------------

export class AppServer {
  constructor(home, cwd, codex = resolveCodex()) {
    this.next = 1;
    this.pending = new Map();
    this.listeners = [];
    this.stderr = '';
    this.dead = null;
    this.proc = spawn(codex.command, [...codex.prefix, 'app-server'], { cwd, env: codexEnv(home), stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true });
    // 'close' follows both a normal exit and a failed spawn, so close() never waits on an event that cannot come.
    this.exited = new Promise((resolve) => this.proc.on('close', resolve));
    this.proc.stderr.on('data', (d) => { this.stderr = (this.stderr + d).slice(-4000); });
    this.proc.stdin.on('error', () => { /* the server went away; 'exit' or 'error' says why */ });
    this.proc.on('error', (error) => this.failAll(new Error(`could not run ${codex.command} app-server: ${error.code || error.message}`)));
    this.proc.on('exit', (code, signal) => this.failAll(new Error(`codex app-server exited (${code ?? signal}) ${this.stderr.trim().split('\n').pop() || ''}`.trim())));
    readline.createInterface({ input: this.proc.stdout }).on('line', (line) => this.onLine(line));
  }

  failAll(error) {
    this.dead = this.dead || error;
    for (const { reject } of this.pending.values()) reject(this.dead);
    this.pending.clear();
    for (const l of this.listeners) l.reject?.(this.dead);
    this.listeners = [];
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

  write(obj) {
    if (this.dead) return;
    try { this.proc.stdin.write(JSON.stringify(obj) + '\n'); } catch { /* reported by 'exit' or 'error' */ }
  }

  request(method, params) {
    if (this.dead) return Promise.reject(this.dead);
    const id = this.next++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.write({ id, method, params });
    });
  }

  async start() {
    await this.request('initialize', { clientInfo: { name: 'codex_thread', title: 'Claude (codex_thread.mjs)', version: '1.1.0' }, capabilities: {} });
    this.write({ method: 'initialized', params: {} });
  }

  // One turn: resolves with the turn's status and Codex's last message once turn/completed arrives for this thread.
  runTurn(threadId, text, opts) {
    if (this.dead) return Promise.reject(this.dead);
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

// Another process (Codex Desktop, when Krish has the thread open) is the thread's one writer.
export const isActiveWriterError = (error) => /already has an active writer/i.test(String(error?.message ?? error));

// Windows caps a whole command line at 32767 characters. A message longer than this goes in a file the turn reads.
export const QUEUE_INLINE_MAX = 24000;

// `codex queue` writes the message to the home's queue; the process holding the thread runs it as its next turn. The
// message is one argv element on the native binary, never through a shell, so no quoting can change it.
function queueMessage(home, threadId, text) {
  let inline = text, file = null;
  if (text.length > QUEUE_INLINE_MAX) {
    const dir = path.join(home, 'codex_thread-messages');
    fs.mkdirSync(dir, { recursive: true });
    file = path.join(dir, `${threadId}-${Date.now()}.md`);
    fs.writeFileSync(file, text, 'utf8');
    inline = `${firstLine(text)}\n\nThis message from Claude is too long to queue inline. Read it in full from ${file} and act on it as this turn's message.`;
  }
  const codex = resolveCodex();
  return new Promise((resolve, reject) => {
    let out = '';
    const proc = spawn(codex.command, [...codex.prefix, 'queue', '--thread', threadId, '--message', inline], { env: codexEnv(home), stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
    proc.stdout.on('data', (d) => { out += d; });
    proc.stderr.on('data', (d) => { out += d; });
    proc.on('error', (error) => reject(new Error(`could not run ${codex.command} queue: ${error.code || error.message}`)));
    proc.on('close', (code) => (code === 0 ? resolve({ text: inline, file })
      : reject(new Error(`codex queue exited (${code}): ${out.trim().split('\n').pop() || 'no output'}`))));
  });
}

async function waitForQueuedTurn(home, threadId, text, since, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const file = findSessionFile(home, threadId);
    if (file) {
      const body = fs.readFileSync(file);
      const result = queuedTurnResult(parseLines(body.subarray(Math.min(since.get(file) ?? 0, body.length)).toString('utf8')), text);
      if (result) return result;
    }
    if (Date.now() > deadline) throw new Error(`the queued turn on ${threadId} did not finish within ${Math.round(timeoutMs / 1000)}s; it may still run in Desktop (read it later)`);
    await new Promise((r) => setTimeout(r, 2000));
  }
}

export async function send(opts) {
  const home = codexHome(opts);
  const threadId = opts.positional[1];
  if (!threadId) throw new Error(USAGE);
  const file = findSessionFile(home, threadId);
  const cwd = path.resolve(opts.cwd || (file && readTurns(file).meta.cwd) || process.cwd());
  const text = message(opts, 2);
  let held = false;
  const direct = await withServer(home, cwd, async (server) => {
    try {
      await server.request('thread/resume', { threadId, ...threadParams(cwd, opts) });
    } catch (error) {
      if (!isActiveWriterError(error)) throw error;
      held = true;
      return null;
    }
    const turn = await server.runTurn(threadId, text, opts);
    return { thread: threadId, home, ...turn };
  });
  if (!held) return direct;

  // Desktop is the thread's writer: queue the message for it instead of failing.
  const since = new Map();
  const before = findSessionFile(home, threadId);
  if (before) since.set(before, fs.statSync(before).size);
  const queued = await queueMessage(home, threadId, text);
  console.error(`thread ${threadId} is held by another writer (Codex Desktop): the message is queued and runs as its next turn there${queued.file ? `; full text in ${queued.file}` : ''}`);
  if (!opts.wait) return { thread: threadId, home, status: 'queued', message: '', error: null, via: 'codex queue', file: queued.file };
  const timeoutMs = Math.max(1, Number(opts.timeout || 1800)) * 1000;
  const turn = await waitForQueuedTurn(home, threadId, queued.text, since, timeoutMs);
  return { thread: threadId, home, ...turn, via: 'codex queue' };
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
  else if (out.status === 'queued') {
    console.log(`thread ${out.thread} (${out.home}): queued for the Codex Desktop writer; it runs as the thread's next turn. Read it with: codex_thread.mjs read ${out.thread}`);
  } else {
    console.log(`thread ${out.thread} (${out.home}): turn ${out.status}; ${out.via ? 'ran in Codex Desktop' : 'released'}`);
    if (out.message) console.log(out.message);
    if (out.error) console.error(out.error);
  }
  return out.status === 'completed' || out.status === 'queued' ? 0 : 1;
}

const invoked = process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
if (invoked) {
  let settled = false;
  // Never exit silently: if the event loop drains while a command is still unsettled, that is a failure.
  process.on('beforeExit', () => {
    if (!settled) { console.error('codex_thread: stopped with no result (the codex process went away without answering)'); process.exit(1); }
  });
  main().then((code) => { settled = true; process.exit(code); }, (error) => { settled = true; console.error(`codex_thread: ${error.message}`); process.exit(1); });
}
