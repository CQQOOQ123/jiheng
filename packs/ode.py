"""ode 能力包：一阶常微分方程解析解 y' = f(x, y)。"""

NAME = "ode"
VERSION = "0.1.0"
DESCRIPTION = "dsolve (first-order y' = f(x, y))"
REQUIRES = []

import sympy as sp

import calc_core as _core


def _wrap(v):
    return _core._wrap(v)


def _sp(v):
    return getattr(v, "e", v)


def dsolve(rhs, x):
    """解 y' = rhs（rhs 中 y 用字母 y 表示），返回 y(x) 的通解。"""
    if not hasattr(x, "e"):
        raise ValueError("dsolve: second argument must be a single-letter variable")
    y = sp.Function("y")
    equation = sp.Eq(y(x.e).diff(x.e), _sp(rhs).subs(sp.Symbol("y"), y(x.e)))
    solution = sp.dsolve(equation, y(x.e))
    return _wrap(solution.rhs)


def register(reg):
    reg.func("dsolve", ["rhs", "x"], dsolve, doc="一阶常微分方程通解")
