# Changelog

## [0.3.9] - 2026-11-05
- README 增加 MCP Registry 所有权标记 `mcp-name: io.github.CQQOOQ123/jiheng`
- server.json 更新到 0.3.9
- 用于通过 MCP Registry PyPI ownership validation
- 无计算内核行为变更

## [0.3.8] - 2026-11-05
- AI-USAGE 增加“何时用/不用 calc”的执行层路由规则
- 工具描述明确“执行层，不是推理器”
- README 增加 uv 安装 unsatisfiable 的 cache 清理说明
- 文档与发现性元数据继续沿用 0.3.7 产品页
- 无计算内核行为变更

## [0.3.7] - 2026-11-05
- 文档版：README 改为产品首页，详细内容通过文档链接分流
- 新增 BENCHMARKS.md（内部验收、外部 benchmark、审计与边界）
- 新增 llms.txt（AI 入口）
- GitHub Topics / PyPI 关键词改为产品与 AI 可发现性导向
- 无代码行为变更

## [0.3.6] - 2026-11-05
- 新增 `irr_all`：NPV=0 化为精确多项式，返回全部实数 IRR（去重、升序、无实根返回 []）
- `series` 奇点/空区间 fail-loud；`ln(0)`/`log(0)` 不再返回 `zoo`
- `dsolve` 支持常量右端（`dsolve(1, x)` → `C1 + x`）
- 新增 1000 题黑盒验收任务银行（独立真值）+ 性能基准
- 能力包测试 165 → 168 项

## [0.3.5] - 2026-11-05
- `max_drawdown(prices[, allow_leading_zeros])` 显式参数：默认严格 >0，allow=1 允许前导 0
- AI-USAGE 增加统计口径声明（总体/样本 ddof、max_drawdown 契约）
- test_docs 增加 ddof / allow_leading_zeros 契约检查，防止文档回退
- 能力包测试 135 → 141 项

## [0.3.4] - 2026-11-05
- 链式符号类型纪律：stats 返回值统一 wrap，内核接受裸 SymPy（B12/C4/G1/G2）
- `max_drawdown` 严格正价格：全零/0 起步/负价格明确报错
- 文档声明 ddof：sharpe/zscore/cov 使用样本口径（ddof=1）
- 能力包测试 124 → 135 项

## [0.3.3] - 2026-11-05
- 修复静默失败：整数截断、零方差、多重 IRR、深度虚值期权下溢
- 新增严格整数校验（bond/date/discount/annuity/factorial/binomial/unit_pow/diff/templates）
- 新增 `var` 总体方差别名；`std`/`var` 与样本函数口径分离
- 修复 min/max 空列表、quantile 越界、gamma/zeta 极点、绝对零度、零利率贷款等边界
- 能力包测试 93 → 124 项

## [0.3.2] - 2026-11-05
- 修正 PyPI 页面语言切换链接（改为 GitHub 绝对地址）
- 中文 / 英文 README 互链可直接跳转
- 仅文档修复，无功能变更

## [0.3.1] - 2026-11-05

- 新增英文 README（PyPI 页面使用英文版）
- GitHub Actions：测试 + Trusted Publishing 自动发布
- 测试脚本适配仓库布局（packs/、AI-USAGE）
- 补充项目 CHANGELOG

## [0.3.0] - 2026-11-05

首个公开版本：玑衡（Jiheng）——给 AI 的精确计算层。

### 核心

- 精确有理数、根号、符号计算，不静默舍入
- 19 个能力包：统计、金融、工程、单位、日期、分布、线代、ODE、特殊函数等
- `steps` 多步一次提交、`functions()` / `help()` 函数发现
- worker 池（1–16）+ `calc_shard` 并行拆题
- MCP 服务器（`jiheng-mcp`）与 DSH 插件两种形态
- MIT License

### 修复与改进

- 基准脚本加载能力包，答案提取支持分数/根号/LaTeX
- `npv(rate, flows[, start])` 增加 `start` 参数（0=首笔 t=0，1=第 1 年末）
- 非法日期明确报错，不自动顺延
- worker 启动发送 `{"ready":true}` 握手
- 1000 题自然使用基准：97.6%
