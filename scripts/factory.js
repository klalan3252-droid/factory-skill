#!/usr/bin/env node
'use strict';
// Checkpoint, pause/resume and metrics helper for the factory workflow.
// Zero dependencies. State lives in FACTORY_STATE_DIR (default .factory/state).
const fs = require('node:fs');
const path = require('node:path');

const STEPS = ['context', 'plan', 'implement', 'test', 'pr', 'post', 'update'];

const stateDir = () => process.env.FACTORY_STATE_DIR || path.join(process.cwd(), '.factory', 'state');
const fileFor = (task) => {
  if (!/^[\w.-]+$/.test(task || '')) throw new Error(`invalid task id: ${task}`);
  return path.join(stateDir(), `${task}.json`);
};

// Atomic write: temp file then rename, so a crash never leaves a torn checkpoint.
function writeAtomic(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2) + '\n');
  fs.renameSync(tmp, file);
}

function load(task) {
  try {
    return JSON.parse(fs.readFileSync(fileFor(task), 'utf8'));
  } catch (e) {
    if (e.code === 'ENOENT') return null;
    throw e;
  }
}

// Mark a step ended with the given outcome, keeping its start time.
function endStep(s, step, now, outcome) {
  const prev = s.steps[step] || { startedAt: now };
  s.steps[step] = { ...prev, ...outcome, endedAt: now, durationMs: now - prev.startedAt };
}

// Start a step: records start time, marks task running, clears any pause.
function begin(task, step, now = Date.now()) {
  if (!STEPS.includes(step)) throw new Error(`unknown step: ${step}`);
  const s = load(task) || { task, createdAt: now, steps: {}, status: 'running' };
  s.status = 'running';
  delete s.pause;
  s.current = step;
  s.steps[step] = { ...s.steps[step], startedAt: now, status: 'running' };
  writeAtomic(fileFor(task), s);
  return s;
}

// Finish a step with optional data (branch, commit, pr url, thread ts ...).
function complete(task, step, data = {}, now = Date.now()) {
  const s = load(task);
  if (!s) throw new Error(`no checkpoint for ${task}`);
  endStep(s, step, now, { status: 'done', data });
  s.current = STEPS[STEPS.indexOf(step) + 1] || null;
  if (!s.current) s.status = 'done';
  writeAtomic(fileFor(task), s);
  return s;
}

function fail(task, step, reason, now = Date.now()) {
  const s = load(task) || { task, createdAt: now, steps: {} };
  endStep(s, step, now, { status: 'failed', reason });
  s.status = 'failed';
  writeAtomic(fileFor(task), s);
  return s;
}

// Usage limit hit: pause until the reset time. The in-flight step stays "running"
// so resume restarts it; completed steps are never repeated.
function pause(task, resetAt, reason = 'usage limit', now = Date.now()) {
  const at = typeof resetAt === 'number' ? resetAt : Date.parse(resetAt);
  if (Number.isNaN(at)) throw new Error(`invalid reset time: ${resetAt}`);
  const s = load(task);
  if (!s) throw new Error(`no checkpoint for ${task}`);
  s.status = 'paused';
  s.pause = { reason, resetAt: at, pausedAt: now };
  writeAtomic(fileFor(task), s);
  return s;
}

// What to do next: wait (with seconds), resume from a step, or nothing.
function next(task, now = Date.now()) {
  const s = load(task);
  if (!s) return { action: 'start', step: STEPS[0] };
  if (s.status === 'done') return { action: 'none' };
  if (s.status === 'failed') return { action: 'none', reason: 'failed' };
  if (s.status === 'paused' && s.pause.resetAt > now) {
    return { action: 'wait', waitSeconds: Math.ceil((s.pause.resetAt - now) / 1000), resetAt: new Date(s.pause.resetAt).toISOString() };
  }
  const step = STEPS.find((x) => !s.steps[x] || s.steps[x].status !== 'done');
  return { action: 'resume', step, completed: STEPS.filter((x) => s.steps[x] && s.steps[x].status === 'done') };
}

function list() {
  if (!fs.existsSync(stateDir())) return [];
  return fs.readdirSync(stateDir()).filter((f) => f.endsWith('.json')).map((f) => load(f.slice(0, -5)));
}

const pct = (sorted, q) => (sorted.length ? sorted[Math.min(sorted.length - 1, Math.ceil(q * sorted.length) - 1)] : null);

// Quantified performance numbers from all checkpoints.
function metrics(states = list()) {
  const count = (st) => states.filter((s) => s.status === st).length;
  const done = count('done');
  const failed = count('failed');
  const perStep = {};
  for (const s of states) {
    for (const [name, st] of Object.entries(s.steps)) {
      if (st.status === 'done') (perStep[name] = perStep[name] || []).push(st.durationMs);
    }
  }
  const steps = {};
  for (const [name, ds] of Object.entries(perStep)) {
    ds.sort((a, b) => a - b);
    steps[name] = { n: ds.length, p50Ms: pct(ds, 0.5), p95Ms: pct(ds, 0.95), totalMs: ds.reduce((a, b) => a + b, 0) };
  }
  const cycle = states
    .filter((s) => s.status === 'done')
    .map((s) => Object.values(s.steps).reduce((a, x) => a + (x.durationMs || 0), 0))
    .sort((a, b) => a - b);
  const pausedMs = states
    .filter((s) => s.pause && s.status === 'paused')
    .reduce((a, s) => a + Math.max(0, s.pause.resetAt - s.pause.pausedAt), 0);
  return {
    tasks: states.length,
    done,
    failed,
    paused: count('paused'),
    running: count('running'),
    successRate: done + failed ? Number((done / (done + failed)).toFixed(3)) : null,
    cycleTimeMs: { p50: pct(cycle, 0.5), p95: pct(cycle, 0.95) },
    pausedMs,
    steps,
  };
}

function main(argv) {
  const [cmd, task, ...rest] = argv;
  const arg = (i) => rest[i];
  const out = (v) => console.log(JSON.stringify(v, null, 2));
  switch (cmd) {
    case 'begin': return out(begin(task, arg(0)));
    case 'complete': return out(complete(task, arg(0), arg(1) ? JSON.parse(arg(1)) : {}));
    case 'fail': return out(fail(task, arg(0), arg(1) || 'unknown'));
    case 'pause': return out(pause(task, arg(0), arg(1)));
    case 'next': return out(next(task));
    case 'show': return out(load(task));
    case 'metrics': return out(metrics());
    default:
      console.error('usage: factory.js begin|complete|fail|pause|next|show <task> ... | metrics');
      process.exitCode = 2;
  }
}

if (require.main === module) {
  try {
    main(process.argv.slice(2));
  } catch (e) {
    console.error(`error: ${e.message}`);
    process.exitCode = 1;
  }
}

module.exports = { STEPS, begin, complete, fail, pause, next, load, list, metrics };
