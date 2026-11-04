# Changelog

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
