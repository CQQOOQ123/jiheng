# Benchmarks & Limits

> 外部 benchmark 只作为解释性材料，不作为营销指标。
> External benchmarks are explanatory only — not a marketing claim.

## 1. 内部验收（每次发布前）

| 项 | 结果 |
|---|---:|
| 核心测试 | 63/63 |
| 能力包测试 | 169/169 |
| 客户端契约 | 8/8 |
| MCP smoke | 6/6 |
| 综合验收 | 1,000/1,000 |
| 按能力包验收 | 19,000/19,000 |

这些验收使用独立真值（Fraction / mpmath / 日历事实），通过 MCP 黑盒调用。

## 2. 外部 benchmark（解释性）

模型：`deepseek-v4-flash`，WorkBuddy provider。baseline 无工具，calc 可选工具。

| 数据集 | baseline | calc |
|---|---:|---:|
| MATH（1,000 数值题） | 99.1% | 97.9% |
| OlympiadBench（1,000） | 68.7% | 60.7% |
| FinQA（1,000） | 72.2% | 73.1% |

工具调用率：

```text
MATH ~9% / Olympiad ~9% / FinQA ~76%
```

结论：

- **数值执行密集**（FinQA、金融、表格）→ 工具有正向信号，但提升有限。
- **推理密集**（MATH / Olympiad）→ 工具没有提升，甚至更差。
- 模型在推理题上大多主动不调用工具；这不是工具失效。
- 因果验证仍需“无工具 / 可选 / 强制”随机对照。

## 3. 100 道 Olympiad 审计

| 类别 | 数量 |
|---|---:|
| MODEL_WRONG | 62 |
| FORMAT_ONLY | 15 |
| EXTRACTION_FAIL | 12 |
| TOOL_GAIN | 8 |
| GOLD_SUSPECT | 3 |

`GOLD_SUSPECT`：1071 / 1300 / 1388（官方答案或题面有问题）。
1066 经复核为 gold 格式错误，已归入 FORMAT_ONLY。

## 4. 性能（构建产物）

| 指标 | 值 |
|---|---:|
| 冷启动 | ~4 ms |
| p50 | ~1.8 ms |
| p95 | ~42 ms |
| p99 | ~45 ms |
| 吞吐 | ~119 calls/s |

数字随机器与负载变化；比较时看同机同版本相对值。

## 5. 不要宣传什么

- 不要把 MATH / Olympiad 分数当作“推理能力提升”
- 不要声称计算器能替代 LLM 读题、建模、推理
- 不要把 FinQA 的 +0.9pp 说成“显著提升”

## 6. 可以宣传什么

- 19,000 表达式级验收
- fail-loud 契约：不静默失败
- 精确分数 / 根号 / 符号 / 单位 / 日期
- 在数值执行密集场景中的稳定性与小幅提升
