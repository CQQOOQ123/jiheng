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
    result = sp.integrate(_sp(expr), var.e)
    if result.has(sp.Integral):
        raise ValueError(
            "integrate: no closed form found; the result would be an unevaluated Integral. "
            "Use nintegrate(expr, x, a, b) for a numeric value."
        )
    return _wrap(result)


def limit(expr, var, point):
    if not hasattr(var, "e"):
        raise ValueError("limit: second argument must be a single-letter variable")
    e = sp.sympify(_sp(expr))
    v = var.e
    p = sp.sympify(_sp(point))
    result = sp.limit(e, v, p)
    if p.is_finite:
        left = sp.limit(e, v, p, dir="-")
        right = sp.limit(e, v, p, dir="+")
        if left != right:
            raise ValueError(
                "limit: two-sided limit does not exist at %s (left=%s, right=%s); "
                "one-sided limits are not supported" % (p, left, right)
            )
    if result is sp.nan or result.has(sp.AccumBounds):
        raise ValueError("limit: no well-defined limit at %s (got %s)" % (p, result))
    return _wrap(result)


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
