# Changelog

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
