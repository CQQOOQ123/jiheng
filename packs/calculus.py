"""calculus 能力包：符号积分、极限、泰勒展开。

证明“框架可扩展”：内核不用改，加一个包就能做 SymPy 级的符号运算。
"""

NAME = "calculus"
VERSION = "0.1.0"
DESCRIPTION = "integrate / limit / taylor"
REQUIRES = []

import sympy as sp  # noqa: E402

import calc_core as _core  # noqa: E402


def _sp(value):
    return getattr(value, "e", value)


def _wrap(value):
    return _core._wrap(value)


def integrate(expr, var):
    if not hasattr(var, "e"):
        raise ValueError("integrate: second argument must be a single-letter variable")
    return _wrap(sp.integrate(_sp(expr), var.e))


def limit(expr, var, point):
    if not hasattr(var, "e"):
        raise ValueError("limit: second argument must be a single-letter variable")
    return _wrap(sp.limit(_sp(expr), var.e, _sp(point)))


def taylor(expr, var, point, order):
    if not hasattr(var, "e"):
        raise ValueError("taylor: second argument must be a single-letter variable")
    n = _core.int_arg(order, "order")
    if n < 0 or n > 20:
        raise ValueError("taylor: order must be between 0 and 20")
    return _wrap(sp.series(_sp(expr), var.e, _sp(point), n + 1).removeO())


def register(reg):
    reg.func("integrate", ["expr", "var"], integrate, doc="符号积分")
    reg.func("limit", ["expr", "var", "point"], limit, doc="极限")
    reg.func("taylor", ["expr", "var", "point", "order"], taylor, doc="泰勒展开")
