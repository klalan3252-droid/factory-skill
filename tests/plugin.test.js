'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const p = (...parts) => path.join(ROOT, ...parts);
const read = (...parts) => fs.readFileSync(p(...parts), 'utf8');
const readJson = (...parts) => JSON.parse(read(...parts));

function listMd(dir) {
  const full = p(dir);
  if (!fs.existsSync(full)) return [];
  return fs.readdirSync(full).filter((f) => f.endsWith('.md')).map((f) => path.join(dir, f));
}

function listSkills() {
  const full = p('skills');
  if (!fs.existsSync(full)) return [];
  return fs
    .readdirSync(full, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => path.join('skills', d.name, 'SKILL.md'))
    .filter((f) => fs.existsSync(p(f)));
}

// Minimal frontmatter parser (simple "key: value" lines only).
function frontmatter(rel) {
  const m = read(rel).match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  assert.ok(m, `${rel} must start with YAML frontmatter`);
  const data = {};
  for (const line of m[1].split(/\r?\n/)) {
    const kv = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (kv) data[kv[1]] = kv[2].replace(/^["']|["']$/g, '').trim();
  }
  return { data, body: m[2] };
}

const lower = (s) => s.toLowerCase();

test('AC-1: plugin.json is valid', () => {
  const j = readJson('.claude-plugin', 'plugin.json');
  assert.equal(j.name, 'factory-skill');
  assert.match(j.version, /^\d+\.\d+\.\d+/);
  assert.ok(j.description && j.description.length > 0);
});

test('AC-1: marketplace.json is valid and lists the plugin', () => {
  const j = readJson('.claude-plugin', 'marketplace.json');
  assert.ok(j.name);
  assert.ok(Array.isArray(j.plugins));
  assert.ok(j.plugins.some((x) => x.name === 'factory-skill' && x.source));
});

test('AC-2: .mcp.json declares clickup, slack, github over https without secrets', () => {
  const raw = read('.mcp.json');
  const j = JSON.parse(raw);
  const servers = j.mcpServers;
  assert.deepEqual(Object.keys(servers).sort(), ['clickup', 'github', 'slack']);
  for (const [name, s] of Object.entries(servers)) {
    assert.match(s.url, /^https:\/\//, `${name} url must be https`);
  }
  assert.match(servers.clickup.url, /clickup\.com/);
  assert.match(servers.slack.url, /slack\.com/);
  assert.match(servers.github.url, /github/);
  assert.doesNotMatch(raw, /Bearer\s+(?!\$\{)/);
  assert.doesNotMatch(raw, /ghp_|github_pat_|xox[abprs]-|pk_\d/);
  // any header value must be an env reference
  for (const s of Object.values(servers)) {
    for (const v of Object.values(s.headers || {})) {
      assert.match(String(v), /\$\{[A-Z_]+\}/, 'header values must use ${ENV} refs');
    }
  }
});

test('AC-3/7: every skill, command and agent has valid frontmatter', () => {
  const skills = listSkills();
  assert.ok(skills.length >= 3, 'expected at least 3 skills');
  for (const f of skills) {
    const { data } = frontmatter(f);
    assert.ok(data.name, `${f} needs name`);
    assert.equal(data.name, path.basename(path.dirname(f)), `${f} name must match dir`);
    assert.ok(data.description, `${f} needs description`);
  }
  const cmds = listMd('commands');
  assert.ok(cmds.length >= 1, 'expected commands');
  for (const f of cmds) assert.ok(frontmatter(f).data.description, `${f} needs description`);
  for (const f of listMd('agents')) {
    const { data } = frontmatter(f);
    assert.ok(data.name && data.description, `${f} needs name+description`);
  }
});

test('AC-3/4: sync skill reads ClickUp, posts to Slack, and is idempotent', () => {
  const { data, body } = frontmatter('skills/clickup-slack-sync/SKILL.md');
  assert.ok(data.description);
  const b = lower(body);
  for (const k of ['clickup', 'slack', 'assigned', 'channel']) assert.ok(b.includes(k), k);
  assert.ok(b.includes('factory-slack-thread:'), 'marker string');
  assert.match(b, /idempoten/);
  assert.match(b, /skip/);
  assert.match(b, /comment|custom field/);
  assert.match(b, /thread/);
});

test('AC-5: workflow skill covers steps in order', () => {
  const b = lower(frontmatter('skills/factory-workflow/SKILL.md').body);
  const order = ['thread', 'clickup', 'plan', 'branch', 'test', 'pull request', 'link', 'status'];
  let pos = -1;
  for (const k of order) {
    const i = b.indexOf(k, pos + 1);
    assert.ok(i > pos, `keyword "${k}" missing or out of order`);
    pos = i;
  }
  assert.match(b, /github/);
});

test('AC-6: workflow skill reports failures and gates PR on tests', () => {
  const b = lower(frontmatter('skills/factory-workflow/SKILL.md').body);
  assert.match(b, /fail/);
  assert.match(b, /report[\s\S]{0,80}thread|thread[\s\S]{0,80}report/);
  assert.match(b, /silent/);
  assert.match(b, /(do not|never|don't)[^.\n]{0,40}(open|raise|create)[^.\n]{0,40}(pr|pull request)[^.\n]{0,80}(fail|test)/);
  assert.match(b, /never merge|do not merge|not merge/);
});

test('AC-7: status skill and sync command exist', () => {
  const { data } = frontmatter('skills/factory-status/SKILL.md');
  assert.ok(data.description);
  const sync = lower(read('commands/sync.md'));
  assert.match(sync, /\/loop|schedule/);
  assert.match(sync, /clickup-slack-sync|sync skill/);
});

test('AC-8: README documents setup', () => {
  const r = lower(read('README.md'));
  for (const k of ['mcp', 'slack app', '.factory.json', 'scope', 'permission', '/plugin install', 'marketplace add',
    'factory_slack_channel', 'factory_clickup_list_id', 'factory_repo', 'factory_base_branch', 'factory_test_command']) {
    assert.ok(r.includes(k), `README missing "${k}"`);
  }
  assert.ok(fs.existsSync(p('.factory.example.json')));
  JSON.parse(read('.factory.example.json'));
});
