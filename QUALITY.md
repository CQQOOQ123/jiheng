# 质量审计：静默失败（silent failure）

一次用 WorkBuddy 做的量化场景测试暴露了 5 类问题。它们都不是“算错”，而是
**工程契约问题**：正常输入算得对，异常输入却给出“看起来正常”的值。

工程上统一叫法：**违反“要么给对、要么明说”的底线**。

## 问题、验证、修复

| # | 问题 | 修复前 | 修复后 |
|---|---|---|---|
| 1 | 债券年份截断 | `bond_price(..., years=2.5, freq=1)` 静默按 2 年算 | 报错：`years must be a multiple of 1/freq ... refusing to truncate`；`freq=2` 时支持 2.5 年 |
| 2 | 零方差返回 `zoo` / 0 | `sharpe([1,1,1])` 返回 `zoo`；`zscore` 同类 | 抛出 `sharpe: returns have zero variance`；`zscore` 同理 |
| 3 | 深度虚值期权返回 0.0 | `black_scholes_call(100,1000,0.1,0.05,0.2)` → `0.0` | 高精度 `erfc` 计算 → `1.602e-289`（不再下溢） |
| 4 | 多重 IRR 只返回一个根 | `irr([-100,230,-132])` 报“no sign change”，误导 | 明确报错：`cashflows change sign 2 times; multiple IRRs may exist...` |
| 5 | 方差口径不一致 | `std` 是总体，但缺少 `var` 对称入口 | 新增 `var`（总体），与 `std` 一致；样本用 `std_sample` / `var_sample` |

另：样本方差/标准差在 `n < 2` 时现在抛
`variance: need at least 2 values (got 1)`，而不是除零。

## 复现验证

```bash
python dsh-calc/test_packs.py
```

相关断言：

```text
raises("bond_price(100, 0.05, 2.5, 0.05, 1)", "refusing to truncate")
check("bond_price(100, 0.05, 2.5, 0.05, 2)", "100")
raises("irr([-100, 230, -132])", "multiple IRRs")
raises("sharpe([1, 1, 1])", "zero variance")
raises("zscore([1, 1, 1])", "zero variance")
raises("std_sample([5])", "at least 2")
check("var([1,2,3])", "2/3")
check_prefix("black_scholes_call(100, 1000, 0.1, 0.05, 0.2)", "1.602049234")
```

## 工程原则

1. **输入契约**：函数声明收什么就收什么；不支持就报错，绝不静默截断/归一化
2. **fail loud**：零方差、退化输入、多重根 → 抛异常，不返回值
3. **算法完备性**：求解器只覆盖单根时，检测多根并明确拒绝，而不是任选一个
4. **口径统一**：`std`/`var`/`std_pop`/`var_pop` 为总体；`std_sample`/`var_sample` 为样本
5. **诚实标注**：只有走精确路径才标 `exact=true`；浮点/近似结果标 `exact=false` 并附警告

## 仍然存在的边界（明确不支持，而不是假装支持）

- `irr` 只支持单次符号变化；多重 IRR 明确报错，需自行扫描 `npv(rate, flows)`
- `black_scholes_*` 是数值结果（`exact=false`），但使用 40 位高精度，避免下溢
- 债券 `years` 必须是 `1/freq` 的整数倍；例如 `freq=1` 时 2.5 年直接拒绝
- 单位/日期等非法输入继续明确报错，不自动顺延或猜测


## 第二轮扩展审计（2026-11-05）

对全部函数做边界探测，又发现并修复：

| 问题 | 修复 |
|---|---|
| `min([])` / `max([])` 报 `_sort_key is not defined` | 补 `_sort_key`，空列表明确报错 |
| `quantile([1,2], 1.5)` 静默返回 2 | q 必须在 [0,1]，否则报错 |
| `bond_duration(face=0)` 抛 `Fraction(1,0)` | 明确报 `face must be > 0` |
| `date_add(..., 1.5)` 静默截断成 1 天 | 严格整数，报错 |
| `discount_factor(..., 1.5)` / `annuity_pv(..., 2.5)` 截断 | 严格整数，报错 |
| `factorial(1.5)` / `binomial(5,2.5)` 截断 | 严格整数，报错 |
| `gamma(-1)` / `zeta(1)` 返回 `zoo` | 极点明确报错 |
| `unit_pow(2,'m',1.5)` 截断指数 | 严格整数，报错 |
| `diff(x^3, x, 1.5)` 截断阶数 | 严格整数，报错 |
| `max_drawdown([])` 返回 0 | 空序列明确报错 |
| `loan_pmt(..., rate=0)` 抛 `Fraction(1,0)` | 零利率正确返回本金/期数 |
| `cagr(..., years=0)` / `start=0` 除零 | 明确报错 |
| `temp_convert(-300,'C','K')` 返回负开尔文 | 低于绝对零度报错 |
| `去税(100,-1)` 抛 `Fraction(1,0)` | 明确报错 |

验证：

```text
能力包测试 101 → 124 项，全部通过
```

- `solve` / `limit` 返回主值解（例如 `solve(sin(x), x)` 给 0、π），不表示一般解 nπ；
  需要一般解时请自行加周期或明确域名
- `integrate(1/x, x)` 返回 `log(x)`，默认复数域/正区间；跨负区间的定积分需自行处理
- `currency_*` 的汇率来自 `.calc/currency.json`（数据，不是实时行情）；对给定汇率的算术是精确的
- `black_scholes_*` 是数值结果（`exact=false`），只是用高精度避免下溢

## 结论

这五类问题的共同点是：**happy path 很强，unhappy path 假装正常**。
修复不需要更高深的数学，只需要更严格的工程纪律。

修复后：

```text
核心 63 + 能力包 101 + worker 12 + 客户端 8 + MCP 6 项测试通过
```
