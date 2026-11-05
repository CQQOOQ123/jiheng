"""calculus2 能力包：数值积分与有限/无限求和。"""

NAME = "calculus2"
VERSION = "0.1.0"
DESCRIPTION = "nintegrate / summation"
REQUIRES = []

import mpmath as mp
import sympy as sp

import calc_core as _core


def _wrap(v):
    return _core._wrap(v)


def _sp(v):
    return getattr(v, "e", v)


def _float(v):
    return float(_sp(v))


def nintegrate(expr, var, a, b):
    """数值积分（mpmath.quad，自适应精度）。"""
    if not hasattr(var, "e"):
        raise ValueError("nintegrate: second argument must be a single-letter variable")
    function = sp.lambdify(var.e, _sp(expr), "mpmath")
    # 振荡积分需要更高 maxdegree；再算一遍做收敛核对
    value = mp.quad(function, [_float(a), _float(b)], maxdegree=10)
    check = mp.quad(function, [_float(a), _float(b)], maxdegree=14)
    if abs(value - check) > 1e-9 * max(1, abs(check)):
        raise ValueError("nintegrate: result did not converge (oscillatory?); "
                         "split the interval or use calc_shard")
    return _wrap(sp.Float(value, 15))


def summation(expr, var, a, b):
    """求和：sum_{var=a}^{b} expr（b 可以是 oo）。"""
    if not hasattr(var, "e"):
        raise ValueError("summation: second argument must be a single-letter variable")
    stop = sp.oo if str(_sp(b)) == "oo" else _sp(b)
    result = sp.summation(_sp(expr), (var.e, _sp(a), stop))
    if result.has(sp.zoo, sp.nan) or result in (sp.zoo, sp.nan):
        raise ValueError("summation: expression is undefined at one of the summation points "
                         "(singular term, got %s)" % result)
    return _wrap(result)


def register(reg):
    reg.func("nintegrate", ["expr", "var", "a", "b"], nintegrate, doc="数值积分")
    reg.func("summation", ["expr", "var", "a", "b"], summation, doc="求和")
