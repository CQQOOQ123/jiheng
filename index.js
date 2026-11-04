/**
 * Host half of dsh-calc.
 *
 * - Registers the `calc` tool backed by a persistent Python worker.
 * - Adds two same-origin HTTP routes consumed by the settings UI:
 *     GET  /calc/status  → version, policy, worker state, home, capabilities
 *     POST /calc/policy  → change usage policy at runtime (persisted to settings.json)
 *
 * Policy decides how the tool description steers the model:
 *   always | complex | auto | never | custom
 */
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

export const name = 'jiheng';
export const inject = ['tools'];

const require = createRequire(import.meta.url);
const VERSION = require('./package.json').version;
const POLICIES = ['always', 'complex', 'auto', 'never', 'custom'];
const DEFAULT_POLICY = 'complex';

const DEFAULT_LIMITS = {
  display_digits: 30,
  max_symbol_len: 120,
  max_decimal_len: 4000,
  max_series: 10000,
  max_array_items: 100000,
  max_expr_chars: 2000,
  max_output_items: 200,
  max_steps: 50,
  exact_only: 1,
  strict_numeric: 0,
};

const PYTHON_CANDIDATES = [
  'C:/Users/HUAWEI/AppData/Local/Programs/Python/Python313/python.exe',
  'C:/Users/HUAWEI/AppData/Local/Programs/Python/Python312/python.exe',
  'C:/Python313/python.exe',
  'C:/Python312/python.exe',
];

function pickPython(config, calcHome) {
  const bundled = path.join(calcHome, 'runtime', process.platform === 'win32' ? 'python.exe' : 'bin/python3');
  const candidates = [];
  if (config && config.pythonPath) candidates.push({ python: config.pythonPath, source: 'config' });
  if (process.env.DSH_CALC_PYTHON) candidates.push({ python: process.env.DSH_CALC_PYTHON, source: 'env' });
  candidates.push({ python: bundled, source: 'bundled' });
  for (const candidate of PYTHON_CANDIDATES) candidates.push({ python: candidate, source: 'known' });
  candidates.push({ python: 'python', source: 'PATH' });
  candidates.push({ python: 'python3', source: 'PATH' });
  for (const candidate of candidates) {
    if (candidate.python === 'python' || candidate.python === 'python3') return candidate;
    if (existsSync(candidate.python)) return candidate;
  }
  return candidates[candidates.length - 1];
}

function resolveHome(configured) {
  if (configured) return configured;
  if (process.env.DSH_CALC_HOME) return process.env.DSH_CALC_HOME;
  const local = path.join(process.cwd(), '.calc');
  if (existsSync(local)) return local;
  return path.join(homedir(), '.calc');
}

function normalizePolicy(value) {
  const p = String(value || '').trim().toLowerCase();
  return POLICIES.includes(p) ? p : DEFAULT_POLICY;
}

const BASE_DESCRIPTION =
  'Evaluate a math expression exactly: fractions stay fractions (1/3), radicals stay radicals '
  + '(sqrt(2)). Symbolic: solve/diff/simplify/expand/factor/subs with single-letter variables '
  + '(e.g. solve(x^2-5*x+6, x)). Built-ins: sum/mean/std/median/quantile, loan_pmt, cagr, '
  + 'discount, markup, convert, series(expr, x, from, to[, step]) for repeated evaluation. '
  + 'Use steps to name intermediate results and reuse them. '
  + 'Results include a full-precision decimal; copy it verbatim and never round. '
  + 'std/std_pop are population standard deviation; std_sample is sample; var_sample/var_pop are variances. Base your final answer on the returned decimal; do not recompute or round it yourself. '
  + 'Common composite functions: norm_cdf(x), black_scholes_call(spot, strike, years, rate, vol), '
  + 'npv(rate, flows), loan_pmt(principal, annualRate, years), unit_convert(value, from, to). '
  + 'Call functions() to list every name and help("name") for a signature. '
  + 'N(expr, digits) is numeric evaluation, NOT the normal CDF; use norm_cdf(x) for a CDF. '
  + 'For multi-step work use ONE call with steps: '
  + '[{name:"d1",expr:"..."},{name:"d2",expr:"d1-..."},{name:"C",expr:"..."}]; '
  + 'later steps may reference earlier names. '
  + 'If a call errors, read the hint and fix it once; do not retry the same expression.';

const POLICY_TEXT = {
  always:
    ' Always call this tool for any arithmetic, including single-step two-number calculations.',
  complex:
    ' Call it when: (1) a list of numbers (mean/std/median/quantile/corr/regression), '
    + '(2) money with more than one step (discount+tax, loan/interest/NPV/IRR), '
    + '(3) unit/date/currency conversion, (4) big or exact numbers (fractions, radicals, >6 digits), '
    + '(5) symbolic math or matrices, (6) your own reasoning would need 3+ arithmetic steps. '
    + 'Do NOT call it for a single two-number operation (e.g. 37*89) or a one-step percentage '
    + 'you can answer directly. If unsure whether a number must be exact, call it - a wrong digit '
    + 'costs more than the call.',
  auto:
    ' Call it when: a list of numbers, money with more than one step, unit/date/currency conversion, '
    + 'big or exact numbers, symbolic math, matrices, or 3+ arithmetic steps. Otherwise answer directly.',
};

function buildDescription(policy, customRules) {
  if (policy === 'custom') {
    return BASE_DESCRIPTION + ' ' + (customRules || POLICY_TEXT.auto);
  }
  return BASE_DESCRIPTION + (POLICY_TEXT[policy] || POLICY_TEXT.auto);
}

function listFiles(dir) {
  try {
    return readdirSync(dir).filter((name) => /\.(py|json)$/.test(name));
  } catch {
    return [];
  }
}

function sanitizePackFile(name) {
  const clean = String(name || '').trim();
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(clean)) throw new Error('invalid pack name (use letters, digits, _ or -)');
  return clean;
}

function readFormulaPacks(dir) {
  const packs = [];
  try {
    for (const file of readdirSync(dir)) {
      if (!file.endsWith('.json')) continue;
      let data;
      try {
        data = JSON.parse(readFileSync(path.join(dir, file), 'utf8'));
      } catch {
        continue;
      }
      packs.push({
        file,
        name: data.name || file.replace(/\.json$/, ''),
        version: data.version || 1,
        const: data.const || {},
        fn: Object.entries(data.fn || {}).map(([name, spec]) => ({
          name,
          params: spec.p || [],
          body: spec.e || '',
          version: spec.v || 1,
        })),
      });
    }
  } catch {
    /* no packs yet */
  }
  return packs;
}

function validateFormula(pythonPath, body) {
  const check = spawnSync(pythonPath, ['-c', 'import ast,sys; ast.parse(sys.stdin.read(), mode="eval")'], {
    input: body,
    encoding: 'utf8',
    timeout: 5000,
  });
  if (check.status !== 0) {
    const message = String(check.stderr || check.error || 'parse error').trim().split('\n').pop();
    throw new Error('invalid expression: ' + message);
  }
}

async function runSelfTest(evaluateFn, name, params, expr, tests) {
  const defs = JSON.stringify({ fn: { [name]: { p: params, e: expr } } });
  const cases = tests.length ? tests : [{ args: params.map(() => '1') }];
  for (let index = 0; index < cases.length; index += 1) {
    const item = cases[index] || {};
    const callArgs = Array.isArray(item.args) ? item.args.map(String) : [];
    const call = `${name}(${callArgs.join(', ')})`;
    const msg = await evaluateFn({ expr: call, defs });
    if (msg.e) {
      throw new Error(`self-test ${index + 1} failed: ${msg.e}: ${msg.msg}`);
    }
    if (item.expect !== undefined && String(item.expect) !== '') {
      const got = Array.isArray(msg.v) ? msg.v.join(', ') : String(msg.v);
      const want = String(item.expect);
      if (got !== want) {
        const gotNum = Number(got);
        const wantNum = Number(want);
        const close = Number.isFinite(gotNum) && Number.isFinite(wantNum)
          && Math.abs(gotNum - wantNum) <= 1e-9 * Math.max(1, Math.abs(wantNum));
        if (!close) throw new Error(`self-test ${index + 1} mismatch: got ${got}, want ${want}`);
      }
    }
  }
  return cases.length;
}

function sendJson(res, code, value) {
  res.statusCode = code;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'no-store');
  res.end(JSON.stringify(value));
}

async function readJsonBody(req, limit = 32 * 1024) {
  let size = 0;
  const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > limit) throw new Error('body too large');
    chunks.push(chunk);
  }
  const text = Buffer.concat(chunks).toString('utf8');
  return text ? JSON.parse(text) : {};
}

export function apply(ctx, config) {
  const calcHome = resolveHome(config && config.calcHome);
  const pythonInfo = pickPython(config, calcHome);
  const python = pythonInfo.python;
  const workerPath = fileURLToPath(new URL('./worker.py', import.meta.url));
  const builtinPacks = fileURLToPath(new URL('./packs', import.meta.url));
  const timeoutMs = Number(process.env.DSH_CALC_TIMEOUT_MS || 8000);
  const settingsPath = path.join(calcHome, 'settings.json');

  function loadSettings() {
    try {
      return JSON.parse(readFileSync(settingsPath, 'utf8')) || {};
    } catch {
      return {};
    }
  }

  function saveSettings(patch) {
    try {
      const current = loadSettings();
      const next = { ...current, ...patch };
      mkdirSync(calcHome, { recursive: true });
      writeFileSync(settingsPath, JSON.stringify(next, null, 2), 'utf8');
    } catch {
      /* ignore persistence failure; runtime state still applies */
    }
  }

  const saved = loadSettings();
  let limits = { ...DEFAULT_LIMITS, ...(saved.limits || {}) };
  let policy = normalizePolicy(saved.policy || (config && config.policy) || process.env.DSH_CALC_POLICY);
  let customRules = typeof saved.customRules === 'string'
    ? saved.customRules
    : String((config && config.customRules) || '');
  const startedAt = Date.now();

  const maxWorkers = Math.min(16, Math.max(1, Number((config && config.maxWorkers)
    || process.env.DSH_CALC_MAX_WORKERS || 8)));
  function normalizeWorkers(raw) {
    if (String(raw).toLowerCase() === 'auto') return 'auto';
    const value = Number(raw);
    return Number.isFinite(value) ? Math.min(maxWorkers, Math.max(1, Math.floor(value))) : 1;
  }
  let configuredWorkers = normalizeWorkers(
    saved.workers ?? (config && config.workers) ?? process.env.DSH_CALC_WORKERS ?? 1,
  );
  let seq = 0;
  const workers = [];

  function spawnWorker() {
    const p = spawn(python, ['-u', workerPath], {
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, CALC_HOME: calcHome, DSH_CALC_BUILTIN_PACKS: builtinPacks },
    });
    const worker = { proc: p, buf: '', pending: new Map(), ready: false };
    p.stdout.setEncoding('utf8');
    p.stdout.on('data', (chunk) => {
      worker.buf += chunk;
      let idx;
      while ((idx = worker.buf.indexOf('\n')) >= 0) {
        const line = worker.buf.slice(0, idx).trim();
        worker.buf = worker.buf.slice(idx + 1);
        if (!line) continue;
        let msg;
        try {
          msg = JSON.parse(line);
        } catch {
          continue;
        }
        if (msg.ready === true) {
          worker.ready = true;
          continue;
        }
        const waiter = worker.pending.get(msg.id);
        if (waiter) {
          worker.pending.delete(msg.id);
          waiter.resolve(msg);
        }
      }
    });
    p.stderr.setEncoding('utf8');
    p.stderr.on('data', (text) => {
      if (process.env.DSH_CALC_DEBUG) process.stderr.write(String(text));
    });
    const drop = () => {
      for (const [, waiter] of worker.pending) waiter.reject(new Error('calc worker exited'));
      worker.pending.clear();
      const index = workers.indexOf(worker);
      if (index >= 0) workers.splice(index, 1);
    };
    p.on('exit', drop);
    p.on('error', drop);
    workers.push(worker);
    return worker;
  }

  function poolTarget() {
    if (configuredWorkers !== 'auto') return configuredWorkers;
    const busy = workers.filter((worker) => worker.pending.size > 0).length;
    const target = workers.length === 0 ? 1 : workers.length;
    if (busy === workers.length && workers.length < maxWorkers) return workers.length + 1;
    return target;
  }

  function ensurePool() {
    const target = poolTarget();
    while (workers.length < target) spawnWorker();
    return workers;
  }

  function resizeWorkers(next) {
    configuredWorkers = normalizeWorkers(next);
    if (configuredWorkers === 'auto') return;
    while (workers.length > configuredWorkers) {
      const worker = workers.pop();
      try {
        worker.proc.kill();
      } catch {
        /* ignore */
      }
    }
    while (workers.length < configuredWorkers) spawnWorker();
  }

  function waitForReady(count, timeoutMs) {
    const deadline = Date.now() + (timeoutMs || 8000);
    return new Promise((resolve) => {
      const check = () => {
        const ready = workers.filter((worker) => worker.ready && worker.proc.exitCode === null).length;
        if (ready >= count) return resolve(true);
        if (Date.now() > deadline) return resolve(false);
        setTimeout(check, 50);
      };
      check();
    });
  }

  function pickWorker() {
    ensurePool();
    const ready = workers.filter((worker) => worker.ready);
    const pool = ready.length ? ready : workers;
    let best = pool[0];
    for (const worker of pool) {
      if (worker.pending.size < best.pending.size) best = worker;
    }
    return best;
  }

  function evaluate(payload) {
    return new Promise((resolve, reject) => {
      let worker;
      try {
        worker = pickWorker();
      } catch (err) {
        reject(err);
        return;
      }
      const id = ++seq;
      const timer = setTimeout(() => {
        if (worker.pending.has(id)) {
          worker.pending.delete(id);
          reject(new Error('calc timed out after ' + timeoutMs + 'ms'));
        }
      }, timeoutMs);
      worker.pending.set(id, {
        resolve: (msg) => {
          clearTimeout(timer);
          resolve(msg);
        },
        reject: (err) => {
          clearTimeout(timer);
          reject(err);
        },
      });
      worker.proc.stdin.write(JSON.stringify({ id, ...payload }) + '\n');
    });
  }

  let toolDisposer = null;
  let shardDisposer = null;
  let historyDisposer = null;

  function registerTool() {
    if (toolDisposer) {
      try {
        toolDisposer();
      } catch {
        /* ignore */
      }
      toolDisposer = null;
    }
    if (policy === 'never') return;
    toolDisposer = ctx.tools.register({
      name: 'calc',
      description: buildDescription(policy, customRules),
      parameters: {
        type: 'object',
        additionalProperties: false,
        required: [],
        properties: {
          expr: {
            type: 'string',
            description: 'Final expression, e.g. 1000*(1+0.13) or mean([12,15,9,22]); optional when steps are given',
          },
          steps: {
            type: 'array',
            description: 'Named intermediate steps evaluated in order; later steps and expr may reference earlier names',
            items: {
              type: 'object',
              additionalProperties: false,
              required: ['name', 'expr'],
              properties: {
                name: { type: 'string' },
                expr: { type: 'string' },
              },
            },
          },
          defs: {
            type: 'string',
            description: 'Optional JSON definitions: {"const":{...},"fn":{"name":{"p":["x"],"e":"expr"}}}',
          },
        },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: false,
          required: ['v'],
          properties: {
            v: { type: 'string', description: 'exact form, e.g. 1/3, sqrt(2), 912.5' },
            steps: {
              type: 'array',
              description: 'per-step results, in the order given',
              items: {
                type: 'object',
                additionalProperties: false,
                required: ['name', 'v'],
                properties: { name: { type: 'string' }, v: { type: 'string' } },
              },
            },
            d: { type: 'string', description: 'decimal approximation when v is not a plain decimal' },
            exact: { type: 'boolean', description: 'false when the result had to be approximated' },
            w: { type: 'string', description: 'warning when the result is not exact' },
          },
        },
        render: (_args, value) => {
          const asList = (x) => (Array.isArray(x) ? x : [x]);
          const values = asList(value.v);
          const decimals = value.d ? asList(value.d) : null;
          const text = values
            .map((item, index) => {
              const dec = decimals && decimals[index];
              return dec && dec !== item ? `${dec}  (exact: ${item})` : String(item);
            })
            .join(', ');
          const warn = value.w ? `  [${value.w}]` : '';
          const steps = Array.isArray(value.steps) && value.steps.length
            ? `  [steps: ${value.steps.map((s) => `${s.name}=${s.v}`).join(', ')}]`
            : '';
          return [{ type: 'text', text: `${text}${warn}${steps}` }];
        },
      },
      async execute(args) {
        const steps = Array.isArray(args.steps) ? args.steps : [];
        if (!args.expr && steps.length === 0) {
          throw new Error('provide expr and/or steps');
        }
        const msg = await evaluate({ expr: args.expr || '', defs: args.defs || '', steps });
        if (msg.e) throw new Error(`${msg.e}: ${msg.msg || 'calculation failed'}`);
        return {
          v: String(msg.v),
          exact: msg.exact !== false,
          ...(msg.d ? { d: String(msg.d) } : {}),
          ...(msg.w ? { w: String(msg.w) } : {}),
          ...(Array.isArray(msg.steps) ? { steps: msg.steps } : {}),
        };
      },
    });
  }

  function usageStats() {
    const file = path.join(calcHome, 'history.jsonl');
    let calls = 0;
    let errors = 0;
    let last = 0;
    try {
      for (const line of readFileSync(file, 'utf8').split('\n')) {
        if (!line.trim()) continue;
        calls += 1;
        try {
          const row = JSON.parse(line);
          if (row.e) errors += 1;
          if (row.time) last = Math.max(last, Number(row.time));
        } catch {
          /* ignore a torn line */
        }
      }
    } catch {
      /* no history yet */
    }
    return { calls, errors, lastCallAt: last };
  }

  function status() {
    return {
      ok: true,
      version: VERSION,
      policy,
      customRules,
      policies: POLICIES,
      limits,
      usage: usageStats(),
      defaults: { policy: DEFAULT_POLICY, limits: DEFAULT_LIMITS },
      registered: Boolean(toolDisposer),
      worker: workers.some((worker) => worker.proc.exitCode === null) ? 'running' : 'idle',
      workers: workers.length,
      ready: workers.filter((worker) => worker.ready).length,
      configuredWorkers,
      maxWorkers,
      home: calcHome,
      python,
      pythonSource: pythonInfo.source,
      timeoutMs,
      uptimeSec: Math.round((Date.now() - startedAt) / 1000),
      packs: {
        plugins: listFiles(path.join(calcHome, 'plugins')),
        formulas: listFiles(path.join(calcHome, 'packs')),
      },
      clientModule: (() => {
        try {
          const cm = ctx.get('clientModules');
          const graph = cm && typeof cm.graph === 'function' ? cm.graph() : undefined;
          const entries = (graph && (graph.entries || graph.modules || graph.rows)) || [];
          const ids = entries.map((entry) => entry && (entry.id || entry.package || entry.name)).filter(Boolean);
          return ids.includes('@local/jiheng') ? 'in-graph' : 'missing(' + ids.length + ' entries)';
        } catch (err) {
          return 'error: ' + String((err && err.message) || err);
        }
      })(),
      capabilities: [
        'exact rational', 'big integers', 'radicals', 'symbolic solve/diff',
        'statistics', 'finance', 'unit conversion', 'custom formulas',
      ],
    };
  }

  registerTool();

  historyDisposer = ctx.tools.register({
    name: 'calc_history',
    description:
      'Recent calculations from this calculator (expression -> result). Use it to reuse a previous result, '
      + 'or to recover one after context compaction; filter with a query.',
    parameters: {
      type: 'object',
      additionalProperties: false,
      required: [],
      properties: {
        limit: { type: 'number', description: 'max entries (default 10, max 100)' },
        query: { type: 'string', description: 'optional substring filter' },
      },
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          ok: { type: 'boolean' },
          items: {
            type: 'array',
            items: {
              type: 'object',
              additionalProperties: false,
              properties: {
                time: { type: 'number' },
                expr: { type: 'string' },
                v: { type: 'string' },
                error: { type: 'string' },
              },
            },
          },
        },
      },
      render: (_args, value) => {
        const items = value.items || [];
        if (!items.length) return [{ type: 'text', text: '(no calculation history yet)' }];
        const lines = items.map((item) => {
          const clock = new Date(item.time).toISOString().slice(11, 19);
          return `- ${clock} ${item.expr} \u2192 ${item.error ? 'ERROR: ' + item.error : item.v}`;
        });
        return [{ type: 'text', text: lines.join('\n') }];
      },
    },
    execute(args) {
      const file = path.join(calcHome, 'history.jsonl');
      let lines = [];
      try {
        lines = readFileSync(file, 'utf8').split('\n').filter(Boolean);
      } catch {
        lines = [];
      }
      const limit = Math.min(Math.max(Number(args.limit) || 10, 1), 100);
      const query = String(args.query || '').toLowerCase();
      const items = [];
      for (let i = lines.length - 1; i >= 0 && items.length < limit; i -= 1) {
        let row;
        try {
          row = JSON.parse(lines[i]);
        } catch {
          continue;
        }
        if (query
          && !String(row.expr || '').toLowerCase().includes(query)
          && !String(row.v || '').toLowerCase().includes(query)) continue;
        items.push({
          time: Number(row.time) || 0,
          expr: String(row.expr || ''),
          v: row.v == null ? '' : String(row.v),
          ...(row.e ? { error: String(row.e) + (row.msg ? ': ' + row.msg : '') } : {}),
        });
      }
      return { ok: true, items };
    },
  });

  if (shardDisposer) {
    try {
      shardDisposer();
    } catch {
      /* ignore */
    }
    shardDisposer = null;
  }
  if (policy !== 'never') {
    shardDisposer = ctx.tools.register({
      name: 'calc_shard',
      description:
        'Split one hard computation into parallel shards and merge them. Shards run concurrently on the worker pool. '
        + 'Use for interval integration, range sums, or parameter scans; not for single-point symbolic work.',
      parameters: {
        type: 'object',
        additionalProperties: false,
        required: ['expr', 'var', 'from', 'to', 'shards'],
        properties: {
          expr: { type: 'string', description: 'expression in the variable, e.g. x*exp(x)' },
          var: { type: 'string', description: 'single-letter variable, e.g. x' },
          from: { type: 'number' },
          to: { type: 'number' },
          shards: { type: 'number', description: '1..8' },
          mode: { type: 'string', enum: ['integrate', 'sum'] },
          op: { type: 'string', enum: ['sum', 'mean', 'max', 'min'] },
        },
      },
      output: {
        schema: {
          type: 'object',
          additionalProperties: false,
          required: ['v', 'mode', 'op'],
          properties: {
            v: { type: 'number' },
            mode: { type: 'string' },
            op: { type: 'string' },
            shards: {
              type: 'array',
              items: {
                type: 'object',
                additionalProperties: false,
                properties: {
                  from: { type: 'number' },
                  to: { type: 'number' },
                  v: { type: 'number' },
                },
              },
            },
          },
        },
        render: (_args, value) => {
          const parts = (value.shards || []).map((s) => `[${s.from},${s.to}]=${s.v}`);
          return [{ type: 'text', text: `${value.op}(${value.mode}) = ${value.v}  (${parts.join(', ')})` }];
        },
      },
      async execute(args) {
        const varName = String(args.var || 'x').trim();
        if (!/^[A-Za-z]$/.test(varName)) throw new Error('var must be a single letter');
        const count = Math.min(8, Math.max(1, Math.floor(Number(args.shards) || 1)));
        const start = Number(args.from);
        const end = Number(args.to);
        if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
          throw new Error('need from < to');
        }
        const mode = args.mode === 'sum' ? 'summation' : 'nintegrate';
        const op = ['mean', 'max', 'min'].includes(args.op) ? args.op : 'sum';
        const bounds = [];
        for (let index = 0; index < count; index += 1) {
          const a = start + ((end - start) * index) / count;
          const b = start + ((end - start) * (index + 1)) / count;
          bounds.push([Number(a.toFixed(12)), Number(b.toFixed(12))]);
        }
        const shards = await Promise.all(bounds.map(async ([a, b]) => {
          const expr = `${mode}(${args.expr}, ${varName}, ${a}, ${b})`;
          const msg = await evaluate({ expr, defs: '' });
          if (msg.e) throw new Error(`shard [${a},${b}] failed: ${msg.e}: ${msg.msg}`);
          const value = Number(msg.v);
          if (!Number.isFinite(value)) throw new Error(`shard [${a},${b}] not numeric: ${msg.v}`);
          return { from: a, to: b, v: value };
        }));
        const values = shards.map((shard) => shard.v);
        const merged = op === 'mean'
          ? values.reduce((sum, value) => sum + value, 0) / values.length
          : op === 'max'
            ? Math.max(...values)
            : op === 'min'
              ? Math.min(...values)
              : values.reduce((sum, value) => sum + value, 0);
        return { v: merged, shards, mode, op };
      },
    });
  }

  ctx.inject(['webServer'], (webCtx) => {
    const web = webCtx.webServer;
    if (!web || typeof web.register !== 'function') return;
    ctx.effect(() => {
    const disposers = [];
    const register = (route) => {
      try {
        disposers.push(web.register(route));
      } catch (err) {
        // A previous activation may still hold the exact path; keep the tool usable
        // instead of failing the whole plugin activation.
        console.error('jiheng: route skipped:', String((err && err.message) || err));
      }
    };
    register({
      kind: 'exact',
      path: '/calc/status',
      handler: (req, res) => {
        if (req.method !== 'GET') return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        return sendJson(res, 200, status());
      },
    });
    register({
      kind: 'exact',
      path: '/calc/limits',
      handler: async (req, res) => {
        if (req.method === 'GET') {
          return sendJson(res, 200, { ok: true, limits, defaults: DEFAULT_LIMITS });
        }
        if (req.method !== 'POST') {
          return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        }
        try {
          const body = await readJsonBody(req);
          if (body.reset === true) {
            limits = { ...DEFAULT_LIMITS };
          } else {
            const patch = body.limits && typeof body.limits === 'object' ? body.limits : {};
            const next = { ...limits };
            for (const [key, value] of Object.entries(patch)) {
              if (!(key in DEFAULT_LIMITS)) continue;
              const num = Number(value);
              if (key === 'exact_only' || key === 'strict_numeric') {
                next[key] = num ? 1 : 0;
                continue;
              }
              if (!Number.isFinite(num) || num <= 0 || num > 1e7) {
                return sendJson(res, 400, { ok: false, error: 'invalid limit: ' + key });
              }
              next[key] = Math.floor(num);
            }
            limits = next;
          }
          saveSettings({ limits });
          return sendJson(res, 200, { ok: true, limits, defaults: DEFAULT_LIMITS });
        } catch (err) {
          return sendJson(res, 400, { ok: false, error: String((err && err.message) || err) });
        }
      },
    });
    register({
      kind: 'exact',
      path: '/calc/workers',
      handler: async (req, res) => {
        if (req.method === 'GET') {
          return sendJson(res, 200, {
            ok: true,
            workers: workers.length,
            ready: workers.filter((worker) => worker.ready).length,
            configuredWorkers,
            maxWorkers,
            options: Array.from({ length: maxWorkers }, (_, i) => i + 1).concat(['auto']),
          });
        }
        if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        try {
          const body = await readJsonBody(req);
          const next = body.workers;
          if (next === undefined) return sendJson(res, 400, { ok: false, error: 'workers is required' });
          resizeWorkers(next);
          saveSettings({ workers: configuredWorkers });
          await waitForReady(workers.length, 1500 + workers.length * 900);
          return sendJson(res, 200, {
            ok: true,
            workers: workers.length,
            ready: workers.filter((worker) => worker.ready).length,
            configuredWorkers,
            maxWorkers,
            options: Array.from({ length: maxWorkers }, (_, i) => i + 1).concat(['auto']),
          });
        } catch (err) {
          return sendJson(res, 400, { ok: false, error: String((err && err.message) || err) });
        }
      },
    });
    register({
      kind: 'exact',
      path: '/calc/batch',
      handler: async (req, res) => {
        if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        try {
          const body = await readJsonBody(req);
          const exprs = Array.isArray(body.exprs) ? body.exprs : [];
          if (!exprs.length || exprs.length > 200) {
            return sendJson(res, 400, { ok: false, error: 'exprs must contain 1..200 items' });
          }
          const defs = typeof body.defs === 'string' ? body.defs : '';
          const results = await Promise.all(exprs.map(async (expr) => {
            const msg = await evaluate({ expr: String(expr), defs });
            return {
              v: msg.v,
              ...(msg.d ? { d: msg.d } : {}),
              exact: msg.exact,
              ...(msg.w ? { w: msg.w } : {}),
              ...(msg.e ? { e: msg.e, msg: msg.msg } : {}),
            };
          }));
          return sendJson(res, 200, { ok: true, workers: workers.length, results });
        } catch (err) {
          return sendJson(res, 400, { ok: false, error: String((err && err.message) || err) });
        }
      },
    });
    register({
      kind: 'exact',
      path: '/calc/packs',
      handler: async (req, res) => {
        if (req.method === 'GET') {
          return sendJson(res, 200, {
            ok: true,
            packs: readFormulaPacks(path.join(calcHome, 'packs')),
            plugins: listFiles(path.join(calcHome, 'plugins')).filter((name) => name.endsWith('.py')),
          });
        }
        if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        try {
          const body = await readJsonBody(req);
          const op = body.op || 'add';
          if (op === 'add') {
            const file = sanitizePackFile(body.pack || 'ai-formulas');
            const name = String(body.name || '').trim();
            if (!name || name.length > 64) throw new Error('invalid function name');
            const params = Array.isArray(body.params) ? body.params.map(String) : [];
            const expr = String(body.body || '').trim();
            if (!expr || expr.length > 2000) throw new Error('invalid formula body');
            validateFormula(python, expr);
            mkdirSync(path.join(calcHome, 'packs'), { recursive: true });
            const fp = path.join(calcHome, 'packs', file + '.json');
            const data = existsSync(fp)
              ? JSON.parse(readFileSync(fp, 'utf8'))
              : { name: file, version: 1, const: {}, fn: {} };
            data.fn = data.fn || {};
            const existing = data.fn[name];
            if (existing && existing.e !== expr && body.overwrite !== true) {
              throw new Error(`conflict: "${name}" already exists with a different body; resend with overwrite:true`);
            }
            const tests = Array.isArray(body.tests) ? body.tests : [];
            const tested = await runSelfTest(evaluate, name, params, expr, tests);
            const changed = !existing
              || existing.e !== expr
              || JSON.stringify(existing.p || []) !== JSON.stringify(params);
            data.fn[name] = {
              p: params,
              e: expr,
              v: (existing && existing.v ? existing.v : 0) + (changed ? 1 : 0),
              updated: Date.now(),
            };
            if (changed) data.version = (data.version || 1) + 1;
            writeFileSync(fp, JSON.stringify(data, null, 2), 'utf8');
            return sendJson(res, 200, {
              ok: true,
              tested,
              changed,
              packs: readFormulaPacks(path.join(calcHome, 'packs')),
            });
          }
          if (op === 'delete') {
            const file = sanitizePackFile(body.pack);
            const fp = path.join(calcHome, 'packs', file + '.json');
            if (!existsSync(fp)) throw new Error('pack not found: ' + file);
            if (body.name) {
              const data = JSON.parse(readFileSync(fp, 'utf8'));
              if (data.fn) delete data.fn[String(body.name)];
              writeFileSync(fp, JSON.stringify(data, null, 2), 'utf8');
            } else {
              unlinkSync(fp);
            }
            return sendJson(res, 200, { ok: true, packs: readFormulaPacks(path.join(calcHome, 'packs')) });
          }
          throw new Error('unknown op: ' + op);
        } catch (err) {
          return sendJson(res, 400, { ok: false, error: String((err && err.message) || err) });
        }
      },
    });
    register({
      kind: 'exact',
      path: '/calc/policy',
      handler: async (req, res) => {
        if (req.method !== 'POST') return sendJson(res, 405, { ok: false, error: 'method not allowed' });
        try {
          const body = await readJsonBody(req);
          const next = normalizePolicy(body.policy);
          if (body.policy !== undefined && !POLICIES.includes(String(body.policy).trim().toLowerCase())) {
            return sendJson(res, 400, { ok: false, error: 'unknown policy: ' + String(body.policy) });
          }
          policy = next;
          if (typeof body.customRules === 'string') customRules = body.customRules.slice(0, 2000);
          saveSettings({ policy, customRules });
          registerTool();
          return sendJson(res, 200, status());
        } catch (err) {
          return sendJson(res, 400, { ok: false, error: String((err && err.message) || err) });
        }
      },
    });
    return () => {
      for (const dispose of disposers) {
        try {
          dispose();
        } catch {
          /* ignore */
        }
      }
    };
    });
  });

  if (process.env.DSH_CALC_PREWARM !== '0') {
    const prewarmTimer = setTimeout(() => {
      try {
        ensurePool();
      } catch {
        /* spawned on first call instead */
      }
    }, 300);
    if (typeof prewarmTimer.unref === 'function') prewarmTimer.unref();
    ctx.effect(() => () => clearTimeout(prewarmTimer));
  }

  ctx.effect(() => {
    return () => {
      if (shardDisposer) {
        try {
          shardDisposer();
        } catch {
          /* ignore */
        }
        shardDisposer = null;
      }
      if (historyDisposer) {
        try {
          historyDisposer();
        } catch {
          /* ignore */
        }
        historyDisposer = null;
      }
      if (toolDisposer) {
        try {
          toolDisposer();
        } catch {
          /* ignore */
        }
        toolDisposer = null;
      }
      for (const worker of workers) {
        try {
          worker.proc.kill();
        } catch {
          /* ignore */
        }
      }
      workers.length = 0;
    };
  });
}
