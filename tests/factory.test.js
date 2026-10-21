'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

process.env.FACTORY_STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'factory-'));
const f = require('../scripts/factory.js');

test('checkpoints persist and resume skips completed steps', () => {
  f.begin('T1', 'context', 1000);
  f.complete('T1', 'context', { thread: '123.4' }, 1500);
  f.begin('T1', 'plan', 1500);
  const n = f.next('T1', 2000);
  assert.deepEqual(n, { action: 'resume', step: 'plan', completed: ['context'] });
  assert.equal(f.load('T1').steps.context.data.thread, '123.4');
  assert.equal(f.load('T1').steps.context.durationMs, 500);
});

test('pause waits until reset, then resumes the interrupted step', () => {
  f.pause('T1', 10000, 'usage limit', 2000);
  const w = f.next('T1', 4000);
  assert.equal(w.action, 'wait');
  assert.equal(w.waitSeconds, 6);
  const r = f.next('T1', 10001);
  assert.equal(r.action, 'resume');
  assert.equal(r.step, 'plan');
  assert.equal(f.begin('T1', 'plan', 11000).status, 'running');
  assert.equal(f.load('T1').pause, undefined);
});

test('unknown task starts fresh; bad ids and steps are rejected', () => {
  assert.equal(f.next('NEW').action, 'start');
  assert.throws(() => f.begin('../evil', 'plan'));
  assert.throws(() => f.begin('T2', 'bogus'));
  assert.throws(() => f.pause('T1', 'not a date'));
});

test('no torn temp files remain after writes', () => {
  assert.deepEqual(fs.readdirSync(process.env.FACTORY_STATE_DIR).filter((x) => x.endsWith('.tmp')), []);
});

test('metrics report success rate and percentiles', () => {
  for (const [id, d] of [['A', 100], ['B', 300], ['C', 200]]) {
    f.begin(id, 'context', 0);
    f.complete(id, 'context', {}, d);
  }
  for (const step of f.STEPS.slice(1)) { f.begin('A', step, 0); f.complete('A', step, {}, 10); }
  f.fail('B', 'test', 'tests failed', 50);
  const m = f.metrics();
  assert.equal(m.done, 1);
  assert.equal(m.failed, 1);
  assert.equal(m.successRate, 0.5);
  assert.equal(m.steps.context.n, 4);
  assert.equal(m.steps.context.p50Ms, 200);
  assert.equal(m.steps.context.p95Ms, 500);
  assert.ok(m.cycleTimeMs.p50 > 0);
});
