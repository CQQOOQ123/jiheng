# 扩展指南：公式包与能力包

计算器有两种扩展方式，按“需不需要写代码”区分。

## 1. 公式包（JSON，无需写代码）

位置：`.calc/packs/*.json`，每个请求都会重新读取（**保存即生效**）。

```json
{
  "name": "my-formulas",
  "version": 1,
  "const": { "vat": 0.13 },
  "fn": {
    "含税": { "p": ["x"], "e": "x*(1+vat)" },
    "折后含税": { "p": ["x", "d"], "e": "含税(x*(1-d))" }
  }
}
```

- `const`：常量表，可引用前面的常量
- `fn`：`p` 是参数名数组，`e` 是表达式（可用其他函数/常量）
- 函数名允许中文；保存前会做表达式解析校验

**通过设置页或接口写入（推荐，带自测与冲突检测）**：

```jsonc
POST /calc/packs
{
  "op": "add",
  "pack": "my-formulas",
  "name": "含税",
  "params": ["x"],
  "body": "x*1.13",
  "tests": [{ "args": ["1000"], "expect": "1130" }]
}
```

- 自测不通过 → 拒绝写入
- 同名且公式体不同 → 冲突；需 `"overwrite": true`
- 包版本 / 函数版本在修改时自增

## 2. 能力包（Python，写代码）

位置：`.calc/plugins/*.py`，**新增/修改/删除都会自动重载**，无需重启 worker。

```python
NAME = "mypack"
VERSION = "0.1.0"
DESCRIPTION = "一句话说明"

from fractions import Fraction


def register(reg):
    reg.func("twice", ["x"], twice, doc="两倍")


def twice(x):
    return Fraction(2) * x
```

**契约**

- 纯函数：无 IO、无网络、无全局状态
- 输入输出用内核认识的类型：`Fraction`、`int`、`list`（`Sym` 也可）
- 出错抛 `ValueError("mypack: ...")`，信息里带函数名
- 函数名不要和内置冲突（会覆盖内置）

**测试**：把用例写进 `dsh-calc/test_packs.py`，CI 里跑 `python dsh-calc/test_packs.py`。

## 3. 让 AI 自己扩展

```text
AI 发现缺函数
  → 写公式（JSON）或能力包（Python）
  → 用 /calc/packs 接口保存（带 1–2 条自测）
  → 自测通过后立即调用
```

原则：**常用公式固化成包，不每次重写**；算法级需求（回归、回撤、收益率）放能力包；
需要文件/循环/绘图时不要硬塞进计算器，交给代码模式。

## 4. 安全

能力包是本地 Python 代码，**没有沙箱**，能读文件、联网、起进程。
只放可信代码；不要从不可信来源直接复制 `.py` 到 `plugins/`。
