"""strategy 能力包：辅助拆解（分部积分、部分分式、三角化简）与结果验证。"""

NAME = "strategy"
VERSION = "0.1.0"
DESCRIPTION = "check_antiderivative / by_parts / apart / trigsimp / check_integral"
REQUIRES = []

import sympy as sp

import calc_core as _core


def _sp(v):
    return getattr(v, "e", v)


def _wrap(v):
    return _core._wrap(v)


def _require_var(var, fname):
    if not hasattr(var, "e") or not getattr(var.e, "is_Symbol", False):
        raise ValueError("%s: second argument must be a single-letter variable" % fname)
    return var.e


def check_antiderivative(F, expr, x):
    """验证 F 是 expr 的原函数：返回 diff(F,x) - expr（0 表示正确）。"""
    xv = _require_var(x, "check_antiderivative")
    gap = sp.simplify(sp.diff(_sp(F), xv) - _sp(expr))
    return _wrap(gap)


def by_parts(u, dv, x):
    """分部积分：∫ u·dv = u·v − ∫ v·du，其中 v=∫dv。"""
    xv = _require_var(x, "by_parts")
    v = sp.integrate(_sp(dv), xv)
    du = sp.diff(_sp(u), xv)
    rest = sp.integrate(v * du, xv)
    result = sp.simplify(_sp(u) * v - rest)
    if result.has(sp.Integral):
        raise ValueError("by_parts: could not integrate the remainder; try another u/dv split")
    return _wrap(result)


def apart(expr, x):
    """部分分式分解。"""
    xv = _require_var(x, "apart")
    return _wrap(sp.apart(_sp(expr), xv))


def trigsimp(expr):
    return _wrap(sp.trigsimp(_sp(expr)))


def check_integral(F, expr, x, a, b):
    """定积分验证：返回数值差 |∫_a^b expr − (F(b)−F(a))|（0 表示一致）。"""
    xv = _require_var(x, "check_integral")
    try:
        numeric = sp.N(sp.integrate(_sp(expr), (xv, _sp(a), _sp(b))), 20)
        exact = sp.N(_sp(F).subs(xv, _sp(b)) - _sp(F).subs(xv, _sp(a)), 20)
        return _wrap(sp.Float(abs(numeric - exact), 5))
    except Exception as ex:
        raise ValueError("check_integral: comparison failed: %s" % ex)


def register(reg):
    reg.func("check_antiderivative", ["F", "expr", "x"], check_antiderivative, doc="验证原函数")
    reg.func("by_parts", ["u", "dv", "x"], by_parts, doc="分部积分")
    reg.func("apart", ["expr", "x"], apart, doc="部分分式")
    reg.func("trigsimp", ["expr"], trigsimp, doc="三角化简")
    reg.func("check_integral", ["F", "expr", "x", "a", "b"], check_integral, doc="定积分验证")
