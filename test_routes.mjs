#!/usr/bin/env node
/**
 * 集成测试：对运行中的 DSH Host 打 HTTP 路由。
 * 用法：node test_routes.mjs [baseUrl]   默认 http://127.0.0.1:3379
 */
const base = process.argv[2] || process.env.DSH_WEB_URL || 'http://127.0.0.1:3379';

try {
  await fetch(base + '/calc/status', { cache: 'no-store' });
} catch (err) {
  if (process.env.CALC_REQUIRE_HOST === '1') {
    console.error('DSH host unreachable at', base, '-', String(err && err.message || err));
    process.exit(1);
  }
  console.log('SKIP: DSH host not reachable at', base, '(set CALC_REQUIRE_HOST=1 to fail)');
  process.exit(0);
}

let pass = 0;
let fail = 0;

function ok(name, condition, detail = '') {
  if (condition) {
    pass += 1;
    console.log(`ok   ${name.padEnd(40)} ${detail}`);
  } else {
    fail += 1;
    console.log(`FAIL ${name.padEnd(40)} ${detail}`);
  }
}

async function json(pathname, init) {
  const res = await fetch(base + pathname, init);
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(`${pathname}: non-JSON response (${res.status}): ${text.slice(0, 80)}`);
  }
  return { status: res.status, data };
}

function post(pathname, body) {
  return json(pathname, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const original = (await json('/calc/status')).data;

let r = await json('/calc/status');
ok('GET /calc/status', r.data.ok === true && typeof r.data.version === 'string', `v${r.data.version}`);
ok('status has limits', r.data.limits && Number(r.data.limits.max_series) > 0);
ok('status has defaults', r.data.defaults && r.data.defaults.limits);

r = await post('/calc/policy', { policy: 'auto' });
ok('POST /calc/policy auto', r.data.policy === 'auto', r.data.policy);

r = await json('/calc/status');
ok('policy persisted', r.data.policy === 'auto');

r = await post('/calc/policy', { policy: 'never' });
ok('policy never unregisters', r.data.registered === false);

r = await post('/calc/policy', { policy: 'complex' });
ok('policy restore', r.data.registered === true);

r = await post('/calc/limits', { limits: { max_output_items: 5 } });
ok('POST /calc/limits custom', r.data.limits.max_output_items === 5);

r = await post('/calc/limits', { reset: true });
ok('POST /calc/limits reset', r.data.limits.max_output_items === original.defaults.limits.max_output_items);

r = await json('/calc/packs');
ok('GET /calc/packs', r.data.ok === true && Array.isArray(r.data.packs), 'packs=' + (r.data.packs || []).length);

r = await post('/calc/packs', {
  op: 'add', pack: 'route-test', name: '双倍', params: ['x'], body: 'x*2',
  tests: [{ args: ['2'], expect: '4' }],
});
ok('add + self-test', (r.data.packs || []).some((p) => p.file === 'route-test.json') && r.data.tested === 1);

let added = (r.data.packs || []).find((p) => p.file === 'route-test.json');
ok('added formula listed', !!added && added.fn.some((f) => f.name === '双倍' && f.params[0] === 'x'));
ok('pack version bumped', (added.version || 0) >= 2, 'v' + added.version);
const stored = added.fn.find((f) => f.name === '双倍');
ok('function version set', !!stored && (stored.version || 0) >= 1, 'v' + (stored && stored.version));

r = await post('/calc/packs', {
  op: 'add', pack: 'route-test', name: '坏自测', params: ['x'], body: 'x*2',
  tests: [{ args: ['2'], expect: '5' }],
});
ok('reject failing self-test', r.status === 400, String(r.data.error || ''));

r = await json('/calc/packs');
ok('failed formula not saved', !(r.data.packs || []).some((p) => p.fn.some((f) => f.name === '坏自测')));

r = await post('/calc/packs', { op: 'add', pack: 'route-test', name: '双倍', params: ['x'], body: 'x*3' });
ok('conflict without overwrite', r.status === 400, String(r.data.error || ''));

r = await post('/calc/packs', {
  op: 'add', pack: 'route-test', name: '双倍', params: ['x'], body: 'x*3', overwrite: true,
  tests: [{ args: ['2'], expect: '6' }],
});
ok('overwrite with self-test', r.status === 200 && r.data.ok === true);

r = await post('/calc/packs', { op: 'delete', pack: 'route-test' });
ok('delete pack', !(r.data.packs || []).some((p) => p.file === 'route-test.json'));

r = await post('/calc/packs', { op: 'add', pack: '../evil', name: 'x', params: [], body: '1+1' });
ok('reject bad pack name', r.status === 400);

r = await post('/calc/packs', { op: 'add', pack: 'route-test', name: '坏公式', params: [], body: 'x=' });
ok('reject bad body', r.status === 400);

r = await json('/calc/workers');
ok('GET /calc/workers', r.data.ok === true && Array.isArray(r.data.options), 'workers=' + r.data.workers);

r = await post('/calc/workers', { workers: 2 });
ok('POST /calc/workers 2', r.data.configuredWorkers === 2, 'running=' + r.data.workers);

r = await post('/calc/workers', { workers: 'auto' });
ok('POST /calc/workers auto', r.data.configuredWorkers === 'auto');

r = await post('/calc/workers', { workers: 1 });
ok('POST /calc/workers restore', r.data.configuredWorkers === 1);

r = await post('/calc/policy', { policy: original.policy });
ok('restore original policy', r.data.policy === original.policy);

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
