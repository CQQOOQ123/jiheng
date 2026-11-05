# 玑衡 Jiheng — 给 AI 的精确计算器（AI-USAGE）

> 面向模型/Agent 的工具手册。人类向文档见 `README.md`。

## 0. 什么时候用它

**用**：
- 一串数字求 均值/标准差/中位数/分位数
- 3 步以上、大数、小数、金额、百分比
- 折扣/复利/贷款/单位换算
- 解方程、求导、化简（符号）
- 需要多步过程可核对（用 `steps`）

**不用**：
- 单个两数四则（如 `37*89`），直接算更快
- 需要读文件/循环/画图（那是代码模式）

### 判断顺序（执行层规则）

**先用 calc 的情况：**
- 已经知道要算什么，只是不想心算
- 数值执行是瓶颈：多步、精确分数/根号、大数、金额、百分比、单位/日期、金融/统计口径
- 需要可核对的 `steps`
- 需要 exact/approx 的诚实标注

**不要用 calc 的情况：**
- 还在读题、建模、选择方法：先让模型完成推理
- 几何证明、组合构造、纯符号推理：calc 不是推理器
- 单个两数四则：直接答更快
- 读文件/循环/画图：用代码模式

**关键区分：**

```text
推理瓶颈 → 模型自己做
执行瓶颈 → calc 做
```

如果一道题需要“先想清楚”，不要一上来就调 calc；  
如果一道题需要“算准”，不要自己心算。

## 1. 调用契约

```json
calc({
  "expr": "最终表达式（可省略，若 steps 已给出结果）",
  "steps": [{"name": "变量名", "expr": "子表达式"}, ...],
  "defs": "可选 JSON：{\"const\":{...},\"fn\":{\"名\":{\"p\":[...],\"e\":\"...\"}}}"
})
```

返回：

```json
{ "v": "精确值", "d": "小数近似（可选）", "exact": true,
  "w": "告警（可选）", "steps": [{"name":"...","v":"..."}] }
```

**读法**：
- `v` 是精确形式，优先用它
- `d` 只是给人看的小数，不要拿它当精确值
- `exact=false` 表示被迫近似（循环小数/超大分数/截断），**不要声称绝对精确**
- 工具文本显示为 `小数  (exact: 精确形式)`；**下一步计算请用括号里的精确形式**，不要用小数
- `N(expr, digits)` 显式数值化（如 `N(pi/3, 30)`）；`strict_numeric=1` 时，无法精确表示的结果会直接报错，而不是给近似
- `w` 出现时先读它

### 统计口径（重要）

```text
std / std_pop / var / var_pop        = 总体（ddof=0）
std_sample / var_sample              = 样本（ddof=1）
sharpe / zscore / cov 内部            = 样本（ddof=1）
max_drawdown(prices[, allow_leading_zeros])
  默认要求价格严格 > 0；allow_leading_zeros=1 允许前导 0（负价永远报错）
```

## 2. 语法速查

### 运算
`+ - * / % **`，`^` 等价于幂（含优先级），`× ÷`、全角括号/逗号自动容错。
科学记数法精确解析：`1e-9`。

### 常量与变量
- 常量：`pi`、`e`
- 符号变量：单个字母 `x/y/z/t/n…`（用于 solve/diff/series）

### 函数

| 类别 | 函数 |
|---|---|
| 基础 | `sqrt abs round floor ceil exp ln log(b?) N(expr, digits)` |
| 三角 | `sin cos tan atan` |
| 统计 | `sum mean std std_sample std_pop var var_pop var_sample median quantile min max count first last` |
| 金融 | `loan_pmt(P,年利率,年数) cagr(末,初,年) fv(P,r,n) discount(价,百分比) markup pct_of`、`npv irr irr_all` |
| 单位 | `convert(值,"from","to")`（速度/长度/质量/数据） |
| 符号 | `solve solve_real diff simplify expand factor subs`、`integrate(式,x) limit(式,x,点) taylor(式,x,点,阶)` |
| 区间/假设 | `interval(式, 位数)` 返回可证明的上下界；`assume(x, "positive")` / `forget(x)` 给符号加/清假设（**只在同一次调用内生效**，每个请求开始时自动清空，避免跨会话泄漏） |
| 查函数 | `functions()` 列出全部函数名；`help("norm_cdf")` 查看签名与说明 |
| 并行拆题 | `calc_shard(expr, var, from, to, shards, mode, op)`：切片并行积分/求和后合并 |
| 序列 | `series(式, x, 起, 止[, 步长])` → 数组 |
| 统计包 | `corr cov dot regression`、`pct_change log_returns cumsum zscore sharpe`、`max_drawdown(prices[, allow_leading_zeros])` |
| 金融包 | `npv(rate, flows[, start])`（start=0 首笔 t=0；start=1 首笔第 1 年末）、`annuity_pv discount_factor irr bond_price bond_duration black_scholes_call black_scholes_put` |
| 分布包 | `norm_pdf norm_cdf norm_quantile t_pdf chi2_pdf` |
| 线代包 | `det inv eigenvals solve_linear transpose matmul` |
| 微积分包 | `integrate limit taylor nintegrate summation` |
| 特殊函数包 | `gamma erf besselj factorial binomial beta zeta` |
| 策略包 | `check_antiderivative by_parts apart trigsimp check_integral` |
| 单位包 | `unit_convert unit_mul unit_div unit_add unit_pow`（函数式，返回 [值, 单位]） |
| 单位包（中缀） | `unit_eval("10 m / 5 s")`；`temp_convert(值,"C","F")` |
| 日期包 | `days_between date_add weekday` |
| 货币包 | `currency_convert currency_rate`（汇率来自 .calc/currency.json，AI 可联网更新） |
| 百分比包 | `pct_part yoy tax_included tax_excluded discount_price growth_multiple` |
| 工程包 | `stress strain youngs_modulus bending_stress beam_cantilever_point beam_simply_supported_point heat_flux thermal_resistance thermal_expansion` |
| 口径模板 | `报价 含税 去税 折扣价 到手价 毛利 毛利率 加成率 损耗后 剩余本金` |
| 人力模板 | `加班费 补偿N加1 个税 社保基数` |
| 物流模板 | `体积重 计费重 运费` |
| 制造模板 | `良率 OEE 材料成本 工时成本` |
| 零售模板 | `折上折 返点 客单价 售罄率` |
| ODE 包 | `dsolve` |

### 数组
`[1,2,3]`；可作参数传。**不支持**逐元素 `ln([...])`、`x*y` 两个数组——需要时用能力包或代码。

## 3. 输出示例

```text
calc({expr:"1/3"})            → 1/3 ≈ 0.333…
calc({expr:"sqrt(2)"})        → sqrt(2) ≈ 1.414…
calc({expr:"0.1+0.2"})        → 0.3
calc({expr:"10^100"})         → 1 后面 100 个 0（精确）
calc({expr:"solve(x^2-5*x+6, x)"}) → 2, 3
calc({expr:"corr([1,2,3,4],[2,4,5,4])"}) → 7*sqrt(95)/95
```

## 4. 常见模式

### A. 单值公式
```json
{"expr": "loan_pmt(1000000, 0.049, 30)"}
→ 5307.2672…
```

### B. 多步计算（推荐）
```json
{
  "steps": [
    {"name": "pv", "expr": "npv(0.1, [0,100,120,150,180,200])"},
    {"name": "tv", "expr": "200*(1.03)/(0.1-0.03)"},
    {"name": "ev", "expr": "pv + tv/(1.1)^5"}
  ],
  "expr": "ev"
}
→ 243631000/102487 ≈ 2377.19  [steps: pv=…, tv=…, ev=…]
```
每步可引用前面的名字；出错会报 `step "x" failed`。

### C. 批量统计
```json
{"expr": "[mean(v), std(v), quantile(v, 0.9)]",
 "steps": [{"name": "v", "expr": "[12,15,9,22,30,18]"}]}
```

### D. 重复计算
```json
{"expr": "sum(series(1000*1.05^x, x, 1, 12))"}
```

### E. 自定义公式
```json
{"expr": "含税(折后(1000, 0.1))",
 "defs": "{\"fn\":{\"折后\":{\"p\":[\"x\",\"d\"],\"e\":\"x*(1-d)\"},\"含税\":{\"p\":[\"x\"],\"e\":\"x*(1+0.13)\"}}}"}
→ 1017
```

### F. 单位
```json
{"expr": "convert(120, \"km/h\", \"m/s\")"}  → 100/3 ≈ 33.333…
{"expr": "convert(2, \"GB\", \"kg\")"}       → 错误：dimension mismatch
```

## 5. 错误与自愈

| 返回 | 含义 | 怎么改 |
|---|---|---|
| `unknown function 'corr'` | 函数不存在/拼错 | 看 `did you mean` 或支持的函数列表 |
| `not an expression (hint: …)` | 传了代码（赋值/循环/推导式） | 改成单个表达式，或换 `std([...])` |
| `division by zero` | 除零 | 检查分母 |
| `dimension mismatch: GB vs kg` | 单位量纲不符 | 换同维度单位 |
| `series: more than N elements` | 序列超限 | 缩小范围或改聚合 |
| `step "x" failed: …` | 某一步出错 | 改那一步 |
| `list truncated: N items (max M)` | 输出被摘要化 | 先聚合再返回，或调高限额 |

## 6. 限额（默认）

| 项 | 默认 |
|---|---|
| `series` 元素 | 10000 |
| 输出列表条数 | 200（超出转摘要） |
| 表达式字符 | 2000 |
| 数组元素 | 100000 |
| `steps` 步数 | 50 |

（可在 设置 → 计算器 → 限额 调整；这里不需要模型关心。）

## 7. 反模式

- ❌ 先心算再调工具"验证"——直接调工具
- ❌ 传 Python 代码（推导式/循环/赋值）——只收表达式
- ❌ 忽略 `exact=false` 仍称"精确"
- ❌ 对本来就是小整数的题也调工具（token 不划算）
- ❌ 把几十个数字手抄进表达式（应先聚合或用代码）

## 8. 一句话

**你负责把问题翻译成表达式（或 steps），它负责算准。**
翻译错了它会报错但不会替你改；算错了它几乎不会——除非 `exact=false`。
