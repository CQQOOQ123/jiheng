"""stats 能力包：相关性、协方差、一元线性回归。

这就是"不是一行公式"的解法——把它写成模块，注册成函数，计算器直接调用。
契约：纯函数、无 IO、输入输出都是精确值（Fraction / Sym / list）。
"""

NAME = "stats"
VERSION = "0.1.0"
DESCRIPTION = "corr / cov / dot / regression(slope,intercept,r2)"
REQUIRES = []

from fractions import Fraction  # noqa: E402

import sympy as sp  # noqa: E402

import calc_core as _core  # noqa: E402


def _f(v):
    if isinstance(v, Fraction):
        return v
    inner = getattr(v, "e", None)
    if inner is not None:
        return inner
    if isinstance(v, sp.Basic):
        return v
    return Fraction(v)


def _wrap(v):
    return _core._wrap(v)


def _total(xs):
    return sum((_f(v) for v in xs), Fraction(0))


def _mean(xs):
    return _total(xs) / len(xs)


def dot(x, y):
    if len(x) != len(y):
        raise ValueError("dot: arrays must have equal length")
    return _wrap(sum((_f(a) * _f(b) for a, b in zip(x, y)), Fraction(0)))


def cov(x, y):
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("cov: need equal-length arrays with n >= 2")
    n = len(x)
    mx, my = _mean(x), _mean(y)
    s = sum(((_f(a) - mx) * (_f(b) - my) for a, b in zip(x, y)), Fraction(0))
    return _wrap(s / (n - 1))


def corr(x, y):
    c = cov(x, y)
    sx = _std_sample(x)
    sy = _std_sample(y)
    sx_s, sy_s = _core._sym(sx), _core._sym(sy)
    if sp.simplify(sx_s) == 0 or sp.simplify(sy_s) == 0:
        raise ValueError("corr: a series has zero variance")
    return _wrap(sp.simplify(_core._sym(c) / (sx_s * sy_s)))


def _std_sample(xs):
    n = len(xs)
    if n < 2:
        raise ValueError("sample standard deviation needs at least 2 values")
    m = _mean(xs)
    var = sum(((_f(v) - m) ** 2 for v in xs), Fraction(0)) / (n - 1)
    return sp.sqrt(sp.sympify(var))


def regression(x, y):
    """返回 [slope, intercept, r2]，全部精确。"""
    n = len(x)
    if len(y) != n or n < 2:
        raise ValueError("regression: need equal-length arrays with n >= 2")
    sx, sy = _total(x), _total(y)
    sxx = sum((_f(v) ** 2 for v in x), Fraction(0))
    syy = sum((_f(v) ** 2 for v in y), Fraction(0))
    sxy = dot(x, y)
    denom = n * sxx - sx * sx
    if denom == 0:
        raise ValueError("regression: x has no variance")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    r2 = (n * sxy - sx * sy) ** 2 / ((n * sxx - sx * sx) * (n * syy - sy * sy))
    return [_wrap(slope), _wrap(intercept), _wrap(r2)]


def pct_change(xs):
    """逐期百分比变化（小数，不是百分数）。"""
    if len(xs) < 2:
        raise ValueError("pct_change: need at least 2 values")
    return [_wrap((_f(b) - _f(a)) / _f(a)) for a, b in zip(xs, xs[1:])]


def log_returns(xs):
    """逐期对数收益率。"""
    if len(xs) < 2:
        raise ValueError("log_returns: need at least 2 values")
    out = []
    for a, b in zip(xs, xs[1:]):
        fa, fb = _f(a), _f(b)
        if fa <= 0 or fb <= 0:
            raise ValueError("log_returns: prices must be positive")
        out.append(_wrap(sp.log(sp.sympify(fb) / sp.sympify(fa))))
    return out


def cumsum(xs):
    """累计和。"""
    total = Fraction(0)
    out = []
    for value in xs:
        total += _f(value)
        out.append(_wrap(total))
    return out


def zscore(xs):
    """标准化（减均值除样本标准差）。"""
    if len(xs) < 2:
        raise ValueError("zscore: need at least 2 values")
    m = _mean(xs)
    s = _std_sample(xs)
    if s == 0:
        raise ValueError("zscore: series has zero variance")
    return [_wrap((_f(value) - m) / s) for value in xs]


def sharpe(returns, rf=0):
    """夏普比率（未年化）：(均值 - 无风险)/样本标准差。"""
    if len(returns) < 2:
        raise ValueError("sharpe: need at least 2 values")
    m = _mean(returns)
    s = _std_sample(returns)
    if s == 0:
        raise ValueError("sharpe: returns have zero variance; ratio is undefined")
    return _wrap((m - _f(rf)) / s)


def max_drawdown(prices):
    """最大回撤（负小数，如 -1/4）。

    价格必须严格为正：0 或负价格会让回撤定义变成 0/0 或负分母，
    这里直接报错，而不是静默返回 0。
    """
    if not prices:
        raise ValueError("max_drawdown: empty price series")
    peak = None
    worst = Fraction(0)
    for value in prices:
        v = _f(value)
        if v <= 0:
            raise ValueError("max_drawdown: prices must be > 0; drawdown is undefined for zero/negative prices")
        if peak is None or v > peak:
            peak = v
        dd = (v - peak) / peak
        if dd < worst:
            worst = dd
    return _wrap(worst)


def register(reg):
    reg.func("dot", ["x", "y"], dot, doc="点积/内积")
    reg.func("cov", ["x", "y"], cov, doc="样本协方差")
    reg.func("corr", ["x", "y"], corr, doc="Pearson 相关系数")
    reg.func("regression", ["x", "y"], regression, doc="一元线性回归 [slope, intercept, r2]")
    reg.func("pct_change", ["xs"], pct_change, doc="逐期百分比变化")
    reg.func("log_returns", ["xs"], log_returns, doc="逐期对数收益率")
    reg.func("cumsum", ["xs"], cumsum, doc="累计和")
    reg.func("zscore", ["xs"], zscore, doc="标准化")
    reg.func("sharpe", ["returns", "rf"], sharpe, doc="夏普比率（未年化）")
    reg.func("max_drawdown", ["prices"], max_drawdown, doc="最大回撤")
