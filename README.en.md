# Jiheng (玑衡) — the exact math execution layer for AI

[![test](https://github.com/CQQOOQ123/jiheng/actions/workflows/test.yml/badge.svg)](https://github.com/CQQOOQ123/jiheng/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/jiheng-mcp)](https://pypi.org/project/jiheng-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[中文](https://github.com/CQQOOQ123/jiheng/blob/main/README.md) | English

**Not a calculator that thinks for your AI — a calculator so your AI doesn't have to do mental math.**

> LLMs are great at reasoning and bad at arithmetic. One silently rounded number can
> propagate into a price, a report, or a trade. Jiheng does one job: **return the exact
> value, or tell you clearly why it cannot.**

## What it is

An exact math execution layer for AI agents and MCP clients: fractions, radicals,
symbolic math, statistics, finance, units and dates. Runs as an **MCP server** or a
**DSH plugin**.

## Who it is for

- Developers building AI agents / MCP clients
- Finance, quant, engineering and data agents
- Workflows where exact numbers, units, dates and statistical conventions matter

## Why it

- `1/3` stays a fraction, `sqrt(2)` stays a radical, `2^200` is exact
- No silent rounding, no guessed units, no plausible-but-wrong numbers
- Errors are explicit and actionable, so the model can repair itself
- Local, no API key, millisecond latency

## Quick start (MCP)

```json
{
  "mcpServers": {
    "jiheng": { "command": "uvx", "args": ["jiheng-mcp"] }
  }
}
```

DSH plugin: `@local/jiheng`.

> If `uv pip install jiheng-mcp==x.y.z` says unsatisfiable while the PyPI page has that
> version, run `uv cache clean jiheng-mcp` and retry; if it still fails, run a full `uv cache clean`. It is usually a stale local uv index.


## Evidence

- 19,000 expression-level acceptance cases
- 1,000 mixed acceptance cases
- 19 capability packs
- Fail-loud error contract: no silent failures
- External benchmark notes: [BENCHMARKS.md](https://github.com/CQQOOQ123/jiheng/blob/main/BENCHMARKS.md)

## Boundaries

- Does not read, model or reason about problems — that is the LLM's job
- Not Wolfram-level symbolic integration / PDE
- Does not fetch live market data or process large CSVs — fetch first, then compute

## Documentation

- [AI usage](https://github.com/CQQOOQ123/jiheng/blob/main/AI-USAGE.md)
- [Capability packs](https://github.com/CQQOOQ123/jiheng/blob/main/PACKS.md)
- [Quality audit](https://github.com/CQQOOQ123/jiheng/blob/main/QUALITY.md)
- [Benchmarks & limits](https://github.com/CQQOOQ123/jiheng/blob/main/BENCHMARKS.md)
- [Changelog](https://github.com/CQQOOQ123/jiheng/blob/main/CHANGELOG.md)
- [llms.txt (for AI)](https://github.com/CQQOOQ123/jiheng/blob/main/llms.txt)

## Why Jiheng?

Different tools optimize for different jobs. Jiheng is built for one specific use case:
**an AI agent that needs a fast, exact, local calculator with a clean tool interface.**

| | Jiheng | Wolfram (Alpha / Cloud) | SymPy MCP | Code Interpreter |
|---|---|---|---|---|
| **Exact fractions / radicals** | ✅ always (`1/3`, `sqrt(2)`) | ✅ | ✅ but a low-level API | ⚠️ float unless you write code |
| **AI-first tool surface** | ✅ `steps`, `functions()`, `help()`, teaching-style errors | ⚠️ docs-oriented | ❌ raw API | ✅ general-purpose |
| **Local, no API key** | ✅ `uvx jiheng-mcp` | ❌ cloud / paid | ✅ local | ❌ hosted |
| **Warm latency** | ~3 ms / call | network round-trip | Python startup per call | seconds |
| **Domain coverage** | 19 packs: stats, finance, engineering, units, dates, distributions, ODE, linalg… | ✅ very broad | base math only | ⚠️ via libraries |
| **Multi-step in one call** | ✅ named `steps` | ⚠️ | ❌ | ✅ code |
| **Parallel shards** | ✅ `calc_shard` + worker pool | ❌ | ❌ | ⚠️ manual |
| **Symbolic depth** | ⚠️ good, not Wolfram-level | ✅ best-in-class | ✅ strong | ⚠️ via SymPy |
| **Hard numerical integration** | ⚠️ improved, not Wolfram-level | ✅ | ⚠️ | ✅ SciPy |
| **Chinese domain conventions** | ✅ discount/tax/date/unit templates | ⚠️ | ❌ | ⚠️ |
| **License / cost** | MIT, free | paid / cloud | BSD, free | free but hosted |
| **Measured benchmark** | ✅ 97.6% on 1,000 mixed tasks | — | — | — |

**Use Jiheng when:**

- You are building an AI agent / MCP client and want a dependable calculator tool
- You need exact values (money, fractions, roots) with no silent rounding
- You want one command, local, no API key, with millisecond latency
- You need domain functions (finance, units, dates, engineering) without writing Python
- You want stable, parseable output and errors the model can self-correct

**Do not use Jiheng for:**

- Risch-level symbolic integration, Meijer-G, PDEs → use Wolfram / Mathematica
- Large CSV/dataframe workflows → use code execution / DuckDB
- Live market data, news, web lookups → fetch data separately, then pass it to Jiheng
- Arbitrary programming → use a code interpreter

## Interoperability

Jiheng is a **computation layer**, not a data layer. It does not open database
connections, fetch web pages, or read files. It computes on numbers you already have.
Data access belongs to dedicated MCP tools; compose them:

| Need | Use |
|---|---|
| Fetch rows from a database / CSV | database MCP, filesystem MCP, code interpreter |
| Statistics, finance, units, dates | **Jiheng** |
| Large joins / ETL | DuckDB / code execution |
| Charts | chart MCP |

Typical flow:

```text
DB MCP: SELECT month, revenue FROM finance
        ↓
[120000, 135000, 149000, 162000]
        ↓
Jiheng: cagr(162000, 120000, 3)   → 0.105...
        Jiheng: mean([...])        → 141500
        Jiheng: npv(0.08, [...], 1) → discounted value
```

Why Jiheng does not embed a database client:

- no database credentials
- no SQL execution surface
- no network requests
- small, auditable, offline-friendly calculator

If you need read-only SQLite / DuckDB / CSV access, use a dedicated data tool or MCP
server, then pass the numbers to Jiheng.

## Quick start

### 30-second setup (MCP)

**1. Install uv** (skip if already installed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

**2. Let your client launch Jiheng**

Add this to your MCP client config (Claude Desktop, Cursor, Codex, ...):

```json
{
  "mcpServers": {
    "jiheng": {
      "command": "uvx",
      "args": ["jiheng-mcp"]
    }
  }
}
```

`uvx` downloads `jiheng-mcp` on first launch, then uses the local cache.

**3. Restart the client and ask**

```text
Use calc to compute 1/3 + 1/6
Use calc to compute mean([12,15,9,22])
Use calc to compute npv(0.08, [623,644,431,286], 1)
Use calc to compute sqrt(2)*sqrt(2)
```

### Other install options

| Method | Command |
|---|---|
| PyPI (pip) | `pip install jiheng-mcp` |
| Local checkout | `uvx --from ./dsh-calc jiheng-mcp` |
| From git | `uvx --from git+https://github.com/CQQOOQ123/jiheng jiheng-mcp` |

### DSH plugin

```powershell
plugin_manager install_bundle target="D:\path\to\dsh-calc"
plugin_manager set_bundle target="@local/jiheng" enabled=true
```

### Run the MCP server directly (debugging)

```bash
cd dsh-calc
python -u mcp_server.py    # JSON-RPC over stdio
```

### Tool arguments

```json
{
  "expr": "final expression (optional when steps are given)",
  "steps": [{"name": "d1", "expr": "..."}, {"name": "C", "expr": "..."}],
  "defs": {"const": {"k": 1.05}, "fn": {"f": {"p": ["x"], "e": "x^2"}}}
}
```

Returns `content[0].text` (decimal-first, with exact form). On errors, `isError: true`
with a correctable hint.

## Usage examples

```text
calc(expr="1/3 + 1/6")                          → 1/2
calc(expr="sqrt(2)*sqrt(2)")                    → 2
calc(expr="mean([12,15,9,22])")                 → 14.5
calc(expr="loan_pmt(1000000, 0.049, 20)")       → monthly payment
calc(expr="black_scholes_call(115,113,1,0.05,0.30)")
calc(expr="npv(0.08, [623,644,431,286], 1)")    → start=1: first cash flow at year-end
calc(expr="functions()")                        → all function names
calc(expr="help(\"norm_cdf\")")                 → norm_cdf(x, mu, sigma) — normal CDF
```

Multi-step in one call:

```json
{
  "steps": [
    {"name": "d1", "expr": "(ln(115/113)+(0.05+0.3^2/2)*1)/(0.3*sqrt(1))"},
    {"name": "d2", "expr": "d1-0.3*sqrt(1)"},
    {"name": "C", "expr": "115*norm_cdf(d1)-113*exp(-0.05)*norm_cdf(d2)"}
  ]
}
```

> `N(expr, digits)` is numeric evaluation, **not** the normal CDF; use `norm_cdf(x)`.

## Functions

- Operators/constants: `+ - * / % ** ^`, `pi`, `e`
- Statistics: `sum mean std std_pop std_sample var_pop var_sample median quantile min max count corr cov regression`
- Finance: `loan_pmt npv(rate, flows[, start]) annuity_pv discount_factor irr bond_price bond_duration black_scholes_call black_scholes_put irr_all`
- Units: `unit_convert unit_add unit_mul unit_div unit_pow unit_eval convert`
- Dates: `days_between date_add weekday`
- Symbolic: `solve diff integrate simplify expand factor subs limit series taylor`
- Engineering: `stress strain bending_stress beam_cantilever_point heat_flux thermal_resistance`
- Distributions: `norm_pdf norm_cdf norm_quantile t_pdf chi2_pdf`
- Discovery: `functions()`, `help("name")`

See [`AI-USAGE.md`](https://github.com/CQQOOQ123/jiheng/blob/main/AI-USAGE.md) for the full contract (60+ functions).

## Configuration

### Policy

| policy | Behavior |
|---|---|
| `always` | call the tool for any arithmetic |
| `complex` | lists/stats, money, units, symbolic, 3+ steps, big numbers (default) |
| `auto` | let the model decide |
| `never` | do not register the tool |
| `custom` | natural-language rules in `customRules` |

### Limits

Settings → Calculator → Limits (stored in `<calcHome>/settings.json`):

| Limit | Default | Behavior |
|---|---|---|
| `max_series` | 10000 | error |
| `max_output_items` | 200 | summarize list |
| `max_expr_chars` | 2000 | error |
| `max_steps` | 50 | error |
| `max_symbol_len` / `max_decimal_len` | 120 / 4000 | degrade to numeric + `exact=false` |
| `exact_only` | 1 | keep exact long symbolic forms (also return `d`) |
| `strict_numeric` | 0 | 1 = error when not exactly representable |

### Worker pool

```yaml
workers: 1        # 1..maxWorkers, or auto
maxWorkers: 8     # hard cap 16; ~52 MB each
```

- `auto`: start with 1 and grow when busy
- Settings page shows running/ready counts; changes apply immediately
- Routes: `GET/POST /calc/workers`, `POST /calc/batch` (1..200 expressions in parallel)
- Workers send `{"ready":true}` on startup; resize waits for all to be ready

### Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `DSH_CALC_PYTHON` | auto-detect | worker interpreter |
| `DSH_CALC_HOME` | `./.calc` or `~/.calc` | settings/packs directory |
| `DSH_CALC_TIMEOUT_MS` | 8000 | per-evaluation timeout |
| `DSH_CALC_DEBUG` | empty | forward worker stderr |
| `DSH_CALC_POLICY` | empty | override policy |
| `DSH_CALC_BUILTIN_PACKS` | bundled `packs/` | built-in packs directory |

## Architecture

```text
DSH Host (Node, resident)
  └─ index.js ── registers calc / calc_shard tools
        │  spawn 1..N workers
        ▼
  worker.py (resident, JSON-lines protocol, ~3ms/eval)
        └─ calc_core.py  AST whitelist + Fraction + SymPy
              └─ packs/*.py  hot-reloadable capability packs

MCP client ──stdio JSON-RPC──▶ mcp_server.py ──▶ calc_core.py + packs/
```

- Resident worker avoids 250–800ms Python startup per call
- No `eval`: AST whitelist only
- Exact first: Fraction fast path; SymPy only for radicals/π/transcendentals

## Precision contract

- Arithmetic / integer powers / percentages / statistics → exact rationals
- Fractions, radicals, constants stay symbolic, plus a decimal `d`
- Simplifiable transcendentals are simplified (`sin(pi/6)=1/2`, `log(1000,10)=3`)
- Oversized exact fractions degrade to decimals with `exact=false`
- **Never silently round**; every approximation is flagged

## Error protocol

```json
{"e":"ValueError","msg":"unknown function 'norm_cdf'... did you mean ..."}
{"e":"ValueError","msg":"invalid date '2026-02-30': 2026-02 has 28 days ... Do not roll over."}
{"e":"ValueError","msg":"dimension mismatch: GB (data) vs kg (mass)"}
{"e":"ValueError","msg":"not an expression (hint: multiple statements are not supported ...)"}
```

## HTTP routes (DSH plugin)

- `/calc/status` — version, policy, registration, worker/ready counts
- `POST /calc/policy` — `{policy, customRules}`
- `GET/POST /calc/limits` — limits; `{"reset":true}` restores defaults
- `GET/POST /calc/workers` — worker pool
- `POST /calc/batch` — `{exprs:[...]}` evaluated in parallel
- `GET/POST /calc/packs` — formula/capability packs

## Capability packs

`packs/*.py` (or `.calc/plugins/*.py`):

```python
NAME = "stats"

def register(reg):
    reg.func("corr", ["x", "y"], corr_impl, doc="Pearson correlation")
```

- Pure functions, no IO/state, exact values in/out
| Pack | Provides |
|---|---|
| `stats` | correlation, covariance, dot product, linear regression |
| `finance` | NPV, annuities, IRR, bonds, Black-Scholes |
| `calculus` | integrate / limit / taylor |
| `calculus2` | nintegrate / summation |
| `distributions` | normal / t / chi-square pdf, cdf, quantiles |
| `linalg` | determinant, inverse, eigenvalues, linear solve, matmul |
| `ode` | first-order ODE `dsolve` |
| `special` | gamma, erf, Bessel, factorial, binomial, beta, zeta |
| `strategy` | integral checks, integration by parts, partial fractions, trig simplification |
| `units` | unit conversion/mul/div/pow, temperature |
| `dates` | date differences, date arithmetic, weekday |
| `currency` | currency conversion |
| `percent` | share, YoY, tax-inclusive/exclusive, discount, growth multiple |
| `engineering` | stress, strain, beam deflection, bending stress, heat flux, thermal resistance |
| `templates` | quotes, tax, discounts, margin, markup, remaining principal, wastage |
| `templates_hr` | overtime pay, N+1 compensation, income tax, social insurance base |
| `templates_logistics` | volumetric weight, chargeable weight, shipping cost |
| `templates_manufacturing` | yield, OEE, material cost, labor cost |
| `templates_retail` | double discount, rebate, average ticket, sell-through rate |

**19 capability packs**, bundled and hot-reloaded.

- Hot-reloaded on change; see [`PACKS.md`](https://github.com/CQQOOQ123/jiheng/blob/main/PACKS.md)

## Parallel shards (`calc_shard`)

```text
calc_shard(expr="x*exp(x)", var="x", from=0, to=1, shards=4, mode="integrate", op="sum")
→ sum(nintegrate) = 1
```

- `mode`: `integrate` / `sum`; `op`: `sum / mean / max / min`
- Only for decomposable problems (interval integrals, range sums, parameter scans)

## Tests & benchmark

```bash
python test_cases.py        # 63: precision/stats/semantics/errors/security
python test_packs.py        # 169: capability packs
python test_worker.py       # 12: worker protocol/hot reload/ready
python test_mcp.py          # 6: MCP smoke
node test_client_contract.mjs   # 8: client contract
node test_routes.mjs http://127.0.0.1:3379  # 26: HTTP routes
```

Benchmark (1000 mixed tasks, deepseek-v4-flash, natural usage): **97.6%** (976/1000).

### Black-box acceptance (0.3.8 candidate)

| Item | Result |
|---|---|
| Mixed task bank | **1,000/1,000** |
| Per capability pack | **19 packs × 1,000 = 19,000/19,000** |
| Truth source | `Fraction` / `mpmath dps=50` / calendar facts; never the plugin itself |
| Call path | MCP stdio, black-box input/output only |
| Difficulty (mixed bank) | easy 639 / medium 131 / hard 130 / adversarial 100 |
| Built-artifact performance | cold ~4.2 ms, p50 ~1.8 ms, p95 ~42 ms, p99 ~45 ms, ~119 calls/s |

> This is a generated acceptance suite for behavioral consistency, exact contracts and fail-loud boundaries. It is engineering/quantitative coverage, not competition-level mathematics.



## FAQ

**Q: Is `std` sample or population?**
A: `std`/`std_pop`/`var`/`var_pop` are population; `std_sample`/`var_sample` are sample.
`sharpe`, `zscore` and `cov` use the sample convention internally (ddof=1). `max_drawdown` requires strictly positive prices by default; `allow_leading_zeros=1` permits leading zeros.

**Q: Why is `N(...)` not the normal CDF?**
A: `N(expr, digits)` is numeric evaluation; use `norm_cdf(x)`.

**Q: Why is the first `npv` cash flow not discounted?**
A: Default `start=0` (`flows[0]` at t=0); use `npv(rate, flows, 1)` for year-end flows.

**Q: What happens with an invalid date?**
A: A clear error (e.g. `2026-02-30`), never normalized to March 2.

**Q: What is `api retries exhausted`?**
A: The model API failed after 6 retries (rate limit/network); not a calculator error.

Quality audit: [`QUALITY.md`](https://github.com/CQQOOQ123/jiheng/blob/main/QUALITY.md)

## Known limitations

- Not a Python expression language: no comprehensions/loops/assignments (intentional)
- Unit tables cover common categories, not every unit
- Repeating decimals/transcendentals are approximations, flagged with `exact=false`
- `calc_shard` cannot split single-point symbolic work
- `index.js` changes need a host restart; `calc_core.py` applies after worker restart

## Packaging

```bash
uv build --directory dsh-calc
# dist/jiheng_mcp-0.3.8-py3-none-any.whl
# dist/jiheng_mcp-0.3.8.tar.gz
```

Docker:

```bash
docker build -t jiheng-mcp dsh-calc
docker run -i --rm jiheng-mcp
```

## Version & license

- Version: `0.3.8`
- MCP package: `jiheng-mcp` on PyPI
- DSH plugin id: `@local/jiheng`
- License: **MIT** (see [LICENSE](https://github.com/CQQOOQ123/jiheng/blob/main/LICENSE))
