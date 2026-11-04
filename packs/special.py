"""special 能力包：特殊函数与组合数。"""

NAME = "special"
VERSION = "0.1.0"
DESCRIPTION = "gamma / erf / besselj / factorial / binomial / beta / zeta"
REQUIRES = []

from fractions import Fraction

import sympy as sp

import calc_core as _core


def _wrap(v):
    return _core._wrap(v)


def _sp(v):
    return getattr(v, "e", v)


def gamma(x):
    e = sp.sympify(_sp(x))
    if e.is_Integer and e <= 0:
        raise ValueError("gamma: pole at non-positive integers (x=%s)" % e)
    return _wrap(sp.gamma(e))


def erf(x):
    return _wrap(sp.erf(_sp(x)))


def besselj(n, x):
    return _wrap(sp.besselj(sp.sympify(_sp(n)), _sp(x)))


def factorial(n):
    value = _core.int_arg(n, "n")
    if value < 0 or value > 10000:
        raise ValueError("factorial: n must be between 0 and 10000")
    return _wrap(sp.factorial(value))


def binomial(n, k):
    nn = _core.int_arg(n, "n")
    kk = _core.int_arg(k, "k")
    if nn < 0 or kk < 0 or kk > nn:
        raise ValueError("binomial: need integers with 0 <= k <= n")
    return _wrap(sp.binomial(nn, kk))


def beta(a, b):
    return _wrap(sp.beta(_sp(a), _sp(b)))


def zeta(s):
    e = sp.sympify(_sp(s))
    if e == 1:
        raise ValueError("zeta: pole at s=1")
    return _wrap(sp.zeta(e))


def register(reg):
    reg.func("gamma", ["x"], gamma, doc="伽马函数")
    reg.func("erf", ["x"], erf, doc="误差函数")
    reg.func("besselj", ["n", "x"], besselj, doc="第一类贝塞尔函数")
    reg.func("factorial", ["n"], factorial, doc="阶乘")
    reg.func("binomial", ["n", "k"], binomial, doc="组合数")
    reg.func("beta", ["a", "b"], beta, doc="贝塔函数")
    reg.func("zeta", ["s"], zeta, doc="黎曼 zeta")
