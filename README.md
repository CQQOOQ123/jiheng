# 玑衡 Jiheng — 给 AI 的精确计算层

[English](README.en.md) | 中文

[![test](https://github.com/CQQOOQ123/jiheng/actions/workflows/test.yml/badge.svg)](https://github.com/CQQOOQ123/jiheng/actions/workflows/test.yml) [![PyPI](https://img.shields.io/pypi/v/jiheng-mcp)](https://pypi.org/project/jiheng-mcp/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**玑衡（Jiheng）**：以古代测天仪器“璇玑玉衡”为名，做 AI 的精确计算层。
精确有理数 + 符号计算 + 统计/金融/单位/日期能力包，既可作为 **DSH 插件**，也可作为
**独立 MCP 服务器** 接入任意 MCP 客户端。

一句话：**让模型不心算、不猜单位、不静默舍入**。

| 能力 | 说明 |
|---|---|
| 精确 | `1/3` 保留分数，`sqrt(2)` 保留根号，`2^200` 逐位精确 |
| 符号 | `solve` / `diff` / `integrate` / `simplify` / `expand` / `factor` / `subs` |
| 多域 | 统计、金融、工程、单位、日期、分布、线代、ODE、特殊函数等 19 个能力包 |
| 多步 | 一次调用用 `steps` 提交命名中间量，避免模型反复往返 |
| 并行 | `calc_shard` 拆区间并行；worker 池 1–16 个进程 |
| 可扩展 | `.calc/plugins/*.py` 热加载；设置页可加/删公式 |
| 可发现 | `functions()` 列全部函数，`help("name")` 查签名 |

## 为什么选 Jiheng

不同工具优化的目标不同。Jiheng 只专注一件事：
**给 AI 代理一个快、准、本地、接口干净的精确计算器。**

| | Jiheng | Wolfram（Alpha / Cloud） | SymPy MCP | Code Interpreter |
|---|---|---|---|---|
| **精确分数/根号** | ✅ 始终（`1/3`、`sqrt(2)`） | ✅ | ✅ 但接口偏底层 | ⚠️ 不写代码就是浮点 |
| **AI 原生接口** | ✅ `steps`、`functions()`、`help()`、教学式错误 | ⚠️ 偏文档 | ❌ 原始 API | ✅ 通用 |
| **本地、无需 API key** | ✅ `uvx jiheng-mcp` | ❌ 云端/付费 | ✅ 本地 | ❌ 托管 |
| **热延迟** | 约 3ms/次 | 网络往返 | 每次起 Python | 秒级 |
| **领域覆盖** | 19 个包：统计、金融、工程、单位、日期、分布、ODE、线代… | ✅ 很广 | 只有基础数学 | ⚠️ 靠库 |
| **一次调用多步** | ✅ 命名 `steps` | ⚠️ | ❌ | ✅ 写代码 |
| **并行拆题** | ✅ `calc_shard` + worker 池 | ❌ | ❌ | ⚠️ 手动 |
| **符号深度** | ⚠️ 够用，非 Wolfram 级 | ✅ 最强 | ✅ 强 | ⚠️ 靠 SymPy |
| **难数值积分** | ⚠️ 已改进，非 Wolfram 级 | ✅ | ⚠️ | ✅ SciPy |
| **中文口径** | ✅ 折扣/税/日期/单位模板 | ⚠️ | ❌ | ⚠️ |
| **许可/成本** | MIT，免费 | 付费/云端 | BSD，免费 | 免费但托管 |
| **可测量基准** | ✅ 1000 题混合基准 97.6% | — | — | — |

**适合用 Jiheng：**

- 你在做 AI Agent / MCP 客户端，需要一个可靠的计算器工具
- 需要精确值（金额、分数、根号），不能静默舍入
- 想要一条命令、本地运行、毫秒级延迟
- 需要金融、单位、日期、工程等现成函数，不想写 Python
- 需要稳定可解析的输出，以及模型能自己修正的错误提示

**不适合用 Jiheng：**

- Risch 级符号积分、Meijer-G、PDE → 用 Wolfram / Mathematica
- 大型 CSV / DataFrame 处理 → 用代码执行 / DuckDB
- 实时行情、新闻、网页查询 → 先取数据，再交给 Jiheng
- 任意编程任务 → 用代码解释器

## 快速开始

### 方式 A：MCP 服务器（推荐给非 DSH 客户端）

```bash
# 从 PyPI 安装（推荐）
uvx jiheng-mcp
# 或
pip install jiheng-mcp

# 开发时从本地目录
uvx --from ./dsh-calc jiheng-mcp

# 或直接从 git 仓库
uvx --from git+https://github.com/CQQOOQ123/jiheng jiheng-mcp
```

MCP 客户端配置（PyPI）：

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

从 git 安装的配置：

```json
{
  "mcpServers": {
    "jiheng": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/CQQOOQ123/jiheng", "jiheng-mcp"]
    }
  }
}
```

提供一个工具 `calc`，参数：

```json
{
  "expr": "最终表达式（可省略，若 steps 已给出结果）",
  "steps": [{"name": "中间变量名", "expr": "子表达式"}],
  "defs": {"const": {"k": 1.05}, "fn": {"f": {"p": ["x"], "e": "x^2"}}}
}
```

返回：`content[0].text` 为十进制优先的结果（附精确形式）；错误时 `isError: true`，文本中包含可修正的提示。

### 方式 B：DSH 插件

```powershell
plugin_manager install_bundle target="D:\AI\DeepSeek-workplace\创造模式\dsh-calc"
plugin_manager set_bundle target="@local/jiheng" enabled=true
```

装载后工具表出现 `calc`；设置 → 计算器 出现配置页。

### 方式 C：直接跑 Python

```bash
cd dsh-calc
python -u mcp_server.py    # 读取 stdin 的 JSON-RPC
```

## 工具用法示例

```text
calc(expr="1/3 + 1/6")                         → 1/2
calc(expr="sqrt(2)*sqrt(2)")                   → 2
calc(expr="mean([12,15,9,22])")                → 14.5
calc(expr="loan_pmt(1000000, 0.049, 20)")      → 月供
calc(expr="black_scholes_call(115,113,1,0.05,0.30)")
calc(expr="npv(0.08, [623,644,431,286], 1)")   → start=1 表示首笔第 1 年末
calc(expr="functions()")                       → 全部函数名
calc(expr="help(\"norm_cdf\")")                → norm_cdf(x, mu, sigma) — 正态累积分布
```

多步一次提交（推荐，减少往返）：

```json
{
  "steps": [
    {"name": "d1", "expr": "(ln(115/113)+(0.05+0.3^2/2)*1)/(0.3*sqrt(1))"},
    {"name": "d2", "expr": "d1-0.3*sqrt(1)"},
    {"name": "C", "expr": "115*norm_cdf(d1)-113*exp(-0.05)*norm_cdf(d2)"}
  ]
}
```

> ⚠️ `N(expr, digits)` 是数值求值，**不是**正态 CDF；CDF 用 `norm_cdf(x)`。

## 常用函数

- 运算/常量：`+ - * / % ** ^`、`pi`、`e`
- 统计：`sum mean std std_pop std_sample var_pop var_sample median quantile min max count corr cov regression`
- 金融：`loan_pmt npv(rate, flows[, start]) annuity_pv discount_factor irr bond_price bond_duration black_scholes_call black_scholes_put`
- 单位：`unit_convert unit_add unit_mul unit_div unit_pow unit_eval` + `convert`
- 日期：`days_between date_add weekday`
- 符号：`solve diff integrate simplify expand factor subs limit series taylor`
- 工程：`stress strain bending_stress beam_cantilever_point heat_flux thermal_resistance`
- 分布：`norm_pdf norm_cdf norm_quantile t_pdf chi2_pdf`
- 函数发现：`functions()`、`help("name")`

完整 61+ 函数见 [`AI-USAGE.md`](./AI-USAGE.md)。

## 配置

### 使用策略（policy）

设置页可选，或 `cordis.patch.yml` 的 `config.policy`：

| policy | 行为 |
|---|---|
| `always` | 任何计算都调工具 |
| `complex` | 只在数组统计、金额、单位、符号、3+ 步、大数时调（默认） |
| `auto` | 模型自判 |
| `never` | 不注册工具 |
| `custom` | 用 `customRules` 自然语言规则 |

### 限额

设置 → 计算器 → 限额（存 `<calcHome>/settings.json`，立即生效）：

| 限额 | 默认 | 超限 |
|---|---|---|
| `max_series` | 10000 | 报错 |
| `max_output_items` | 200 | 列表转摘要 |
| `max_expr_chars` | 2000 | 报错 |
| `max_steps` | 50 | 报错 |
| `max_symbol_len` / `max_decimal_len` | 120 / 4000 | 降级为数值 + `exact=false` |
| `exact_only` | 1 | 长符号表达式保留精确形式（同时给 `d`） |
| `strict_numeric` | 0 | 1=无法精确表示时报错 |

### Worker 池

默认 1 个常驻进程（单次约 3ms）；高并发/重符号任务可开池：

```yaml
# cordis.patch.yml
workers: 1        # 1..maxWorkers，或 auto
maxWorkers: 8     # 硬上限 16；每个约 52MB
```

- `auto`：起始 1 个，忙时自动扩到 `maxWorkers`
- 设置页可查看 **运行中/就绪**，切换 1..8 / 自动 / 自定义，保存即生效
- 接口：`GET/POST /calc/workers`、`POST /calc/batch`（1..200 条表达式并行）
- worker 启动完成发 `{"ready":true}` 握手；扩容后等全部就绪再返回

### 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DSH_CALC_PYTHON` | 自动探测 | worker 解释器 |
| `DSH_CALC_HOME` | `./.calc` 或 `~/.calc` | 公式/设置目录 |
| `DSH_CALC_TIMEOUT_MS` | 8000 | 单次求值超时 |
| `DSH_CALC_DEBUG` | 空 | 透传 worker stderr |
| `DSH_CALC_POLICY` | 空 | 临时覆盖策略 |
| `DSH_CALC_BUILTIN_PACKS` | 包内 `packs/` | 内置能力包目录 |

## 架构

```text
DSH Host (Node, 常驻)
  └─ index.js ──注册 calc / calc_shard 工具──▶ ctx.tools.register
        │  spawn（1..N 个）
        ▼
  worker.py（常驻，JSON 行协议，~3ms/次）
        └─ calc_core.py  AST 白名单 + Fraction + SymPy
              └─ packs/*.py  能力包（热加载）

MCP 客户端 ──stdio JSON-RPC──▶ mcp_server.py ──▶ calc_core.py + packs/
```

- 常驻 worker：避免每次 250–800ms 的 Python 启动
- 禁 `eval`：AST 白名单，只允许数字/字符串/列表/四则/幂/白名单函数
- 精确优先：能 Fraction 就 Fraction，涉及根号/π/超越函数才进 SymPy

## 精度契约

- 四则/整数幂/百分比/统计 → 精确有理数：`1/7*7 = 1`、`2^200` 精确
- 分数/根号/常量保留符号，同时给 `d` 字段（30 位小数）
- 超越函数能化简就化简（`sin(pi/6)=1/2`、`log(1000,10)=3`）
- 精确分数过大时降级为小数，标 `exact=false`
- **永不静默舍入**；所有近似都有说明

## 错误协议（方便模型一次改对）

```json
{"e":"ValueError","msg":"unknown function 'norm_cdf'... did you mean ..."}
{"e":"ValueError","msg":"invalid date '2026-02-30': 2026-02 has 28 days ... Do not roll over."}
{"e":"ValueError","msg":"dimension mismatch: GB (data) vs kg (mass)"}
{"e":"ValueError","msg":"not an expression (hint: multiple statements are not supported ...)"}
```

## 设置页与 HTTP 路由

- `/calc/status`：版本、策略、注册状态、worker/就绪数、目录
- `POST /calc/policy`：`{policy, customRules}`
- `GET/POST /calc/limits`：限额；`{"reset":true}` 恢复默认
- `GET/POST /calc/workers`：worker 池
- `POST /calc/batch`：`{exprs:[...]}` 并行求值
- `GET/POST /calc/packs`：公式包/能力包

## 能力包扩展

`.calc/plugins/*.py`（或包内 `packs/`）：

```python
NAME = "stats"

def register(reg):
    reg.func("corr", ["x", "y"], corr_impl, doc="Pearson 相关系数")
```

- 纯函数、无 IO、无状态；输入输出为精确值
- 修改/新增后自动热加载（worker 校验 mtime）
- 指导文档：[`PACKS.md`](./PACKS.md)

## 拆题并行（calc_shard）

```text
calc_shard(expr="x*exp(x)", var="x", from=0, to=1, shards=4, mode="integrate", op="sum")
→ sum(nintegrate) = 1
```

- `mode`: `integrate` / `sum`；`op`: `sum / mean / max / min`
- 只适合可分解题型（区间积分、区间求和、参数扫描）

## 测试与基准

```bash
python dsh-calc/test_cases.py       # 63 项：精度/统计/语义/错误/安全
python dsh-calc/test_packs.py       # 93 项：能力包
python dsh-calc/test_worker.py      # 12 项：worker 协议/热加载/ready
node dsh-calc/test_client_contract.mjs  # 8 项：客户端契约
node dsh-calc/test_routes.mjs http://127.0.0.1:3379  # 26 项：HTTP 路由
python research/bench/mcp_smoke.py  # 7 项：MCP 冒烟
```

基准（1000 题混合题集，deepseek-v4-flash，自然使用模式）：**97.6%**（976/1000）。

## 常见问题

**Q：`std` 是样本还是总体？**
A：`std`/`std_pop` 是总体，`std_sample` 是样本。

**Q：为什么 `N(...)` 不等于正态 CDF？**
A：`N(expr, digits)` 是数值求值；正态 CDF 用 `norm_cdf(x)`。

**Q：`npv` 第一笔为什么不折现？**
A：默认 `start=0`（`flows[0]` 在 t=0）；年末现金流用 `npv(rate, flows, 1)`。

**Q：非法日期会怎样？**
A：明确报错（如 `2026-02-30`），不会顺延到 3 月 2 日。

**Q：`api retries exhausted` 是什么？**
A：模型 API 连续重试 6 次仍失败（限流/网络），不是计算器错误；用 `--resume` 补跑。

## 开发与发布

- CI：`.github/workflows/test.yml` 在 push / PR 时跑核心、能力包、文档、客户端、MCP 冒烟测试
- 发布：`.github/workflows/publish.yml` 在 GitHub Release 发布时自动构建并上传 PyPI
  （Trusted Publishing：GitHub OIDC，无需长期 token）

发布流程：

```bash
# 1. 改版本号（同步 package.json / pyproject / mcp_server）
python scripts/bump_version.py 0.3.1

# 2. 更新 CHANGELOG.md
# 3. 提交并创建 GitHub Release（建议先 Draft，确认后再 Publish）
# 4. Release 触发 publish.yml → 自动发布到 PyPI
```

PyPI 项目需在 **Publishing** 里配置 GitHub publisher：

```text
Owner:        CQQOOQ123
Repository:   jiheng
Workflow:     publish.yml
Environment:  （留空）
```

手动发布（备用）：

```bash
$env:UV_PUBLISH_TOKEN = "pypi-..."
uv build --directory dsh-calc
uv publish dsh-calc/dist/*
```

## 已知限制

- 表达式不是 Python：不支持推导式/循环/赋值（有意为之）
- 单位表覆盖常用类别，不是全量单位库
- 循环小数/超越函数是近似（有 `exact=false` 标记）
- 单点符号运算无法用 `calc_shard` 切分
- 宿主重启前改 `index.js` 不热更新；`calc_core.py` 在 worker 重启后生效

## 安装 / 打包

```bash
uv build --directory dsh-calc
# dist/jiheng_mcp-0.3.0-py3-none-any.whl
# dist/jiheng_mcp-0.3.0.tar.gz
```

Docker：

```bash
docker build -t jiheng-mcp dsh-calc
docker run -i --rm jiheng-mcp
```

## 版本与品牌

当前 `0.3.0`。

- 品牌：**玑衡 Jiheng**
- GitHub 仓库：https://github.com/CQQOOQ123/jiheng
- MCP 包名：`jiheng-mcp`（PyPI/npm 均可用）
- DSH 插件 id：`@local/jiheng`

版本号唯一来源：`dsh-calc/package.json`；`scripts/bump_version.py` 同步
`pyproject.toml` 与 `mcp_server.py`。

## 许可证

**MIT**（见 [LICENSE](./LICENSE)）。

允许任何人自由使用、修改、分发、商用，保留版权声明即可，无担保。
`package.json` 与 `pyproject.toml` 已声明 MIT。

### 为什么选 MIT

- AI/Agent 生态主流是 MIT：MCP SDK、LangChain、Ollama、llama.cpp、React/Vue 等
- 计算器的价值在“被集成”，不在“禁止别人用”；宽松许可证提高采用率
- 依赖（SymPy）是 BSD，与 MIT 完全兼容
- 公司内部工具/闭源产品可以放心接入，不会被 GPL 传染

### MIT 项目怎么保护自己

MIT **不限制别人复制代码**，保护来自许可证之外：

| 手段 | 说明 |
|---|---|
| **商标** | MIT 只授权代码，不授权名称/图标；“dsh-calc”品牌仍归作者 |
| **版权声明** | 分发时必须保留 `LICENSE` 和版权行，可追溯来源 |
| **Open Core** | 核心 MIT，企业版/高级能力包/托管服务单独商业授权 |
| **贡献者协议（CLA）** | 接受外部贡献前签 CLA，保留未来双许可/换许可证的权利 |
| **专利** | MIT 无专利授权；担心专利可改 Apache-2.0，或在 CLA 中要求专利授权 |
| **SaaS 差异化** | 托管服务的运维、SLA、合规、数据是竞争力；若怕云厂商直接复制，用 AGPL |

典型案例：React（Meta）、VS Code、Ollama、LangChain 都是 MIT/宽松许可，
靠品牌、生态、企业服务/托管平台赚钱，而不是靠许可证封锁。
