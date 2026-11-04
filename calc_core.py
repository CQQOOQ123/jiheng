#!/usr/bin/env python
"""calc_core v4 — 精确有理数 + 符号计算（SymPy），小数只是附加展示。

核心原则：
- 能用精确形式就用精确形式：1/3 保持 "1/3"，sqrt(2) 保持 "sqrt(2)"
- 数值近似只作为附加字段 d（30 位），不替代精确值
- 永远不静默舍入：精确值、近似值、截断都显式标注

值的类型：
  Fraction  → 有理数（快路径，覆盖金额/四则/统计）
  Sym       → SymPy 符号表达式（根号、π、超越函数）
  str/list  → 单位名、数组

输出契约：
  {"v": 精确形式, "d": 数值近似(可选), "exact": bool, "w": 告警(可选)}
"""
import ast
import difflib
import re
import math
import sys
from decimal import Decimal
from fractions import Fraction

import sympy as sp
from mpmath import iv, mp

LIMITS = {
    "display_digits": 30,
    "max_symbol_len": 120,
    "max_decimal_len": 4000,
    "max_series": 10000,
    "max_array_items": 100000,
    "max_expr_chars": 2000,
    "max_output_items": 200,
    "max_steps": 50,
    "exact_only": 1,
    "strict_numeric": 0,
}
DEFAULT_LIMITS = dict(LIMITS)


def apply_limits(overrides=None):
    """用配置覆盖默认限额；未知键或非法值忽略。"""
    global DISPLAY_DIGITS, MAX_SYMBOL_LEN, MAX_DECIMAL_LEN
    for key, value in (overrides or {}).items():
        if key not in LIMITS:
            continue
        if key in ("exact_only", "strict_numeric"):
            LIMITS[key] = 1 if value in (1, True, "1", "true", "True") else 0
            continue
        if isinstance(value, (int, float)) and value > 0:
            LIMITS[key] = int(value)
    DISPLAY_DIGITS = LIMITS["display_digits"]
    MAX_SYMBOL_LEN = LIMITS["max_symbol_len"]
    MAX_DECIMAL_LEN = LIMITS["max_decimal_len"]


DISPLAY_DIGITS = LIMITS["display_digits"]
MAX_SYMBOL_LEN = LIMITS["max_symbol_len"]
MAX_DECIMAL_LEN = LIMITS["max_decimal_len"]


class Sym:
    """精确符号值（SymPy 表达式）。"""

    __slots__ = ("e",)

    def __init__(self, e):
        e = sp.sympify(e)
        if e.is_Rational:
            raise ValueError("rational should be normalized to Fraction")
        self.e = e

    def __repr__(self):
        return "Sym(%s)" % sp.sstr(self.e)


# ---------- 转换 ----------

def _frac(v):
    if isinstance(v, Fraction):
        return v
    if isinstance(v, bool):
        raise ValueError("bool is not a number")
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, float):
        return Fraction(str(v))
    if isinstance(v, Decimal):
        return Fraction(v)
    raise ValueError("not a number: %r" % (v,))


class IntervalValue:
    """区间结果：可证明包住真实值的上下界，不参与后续算术。"""

    def __init__(self, lo, hi):
        self.lo = lo
        self.hi = hi

    def __repr__(self):
        return "IntervalValue(%s, %s)" % (self.lo, self.hi)


def _sym(v):
    if isinstance(v, Sym):
        return v.e
    if isinstance(v, Fraction):
        return sp.Rational(v.numerator, v.denominator)
    return sp.Integer(_frac(v))


_ASSUMPTIONS = {}


def _symbol(name):
    """按已注册的假设构造符号；无假设时等价于普通 Symbol。"""
    return sp.Symbol(name, **_ASSUMPTIONS.get(name, {}))


def _assume(var, kind):
    """给单字母符号加假设：positive / nonnegative / negative / real / integer / rational。"""
    name = getattr(getattr(var, "e", None), "name", None)
    if not name:
        raise ValueError("assume: first argument must be a single-letter variable")
    mapping = {
        "positive": {"positive": True},
        "nonnegative": {"nonnegative": True},
        "negative": {"negative": True},
        "real": {"real": True},
        "integer": {"integer": True},
        "rational": {"rational": True},
    }
    key = str(kind).strip().lower()
    if key not in mapping:
        raise ValueError("assume: kind must be one of " + ", ".join(sorted(mapping)))
    _ASSUMPTIONS[name] = mapping[key]
    return Fraction(1)


def reset_assumptions():
    """清空符号假设（worker 在每个请求开始时调用，避免跨请求泄漏）。"""
    _ASSUMPTIONS.clear()


def _forget(var):
    name = getattr(getattr(var, "e", None), "name", None)
    if not name:
        raise ValueError("forget: argument must be a single-letter variable")
    _ASSUMPTIONS.pop(name, None)
    return Fraction(1)


def _wrap(e):
    """把 SymPy 结果归一化：整数/有理数回到 Fraction，其余包成 Sym。"""
    e = sp.sympify(e)
    if e.is_Integer:
        return Fraction(int(e))
    if e.is_Rational:
        return Fraction(int(e.p), int(e.q))
    return Sym(e)


def int_arg(value, name="value"):
    """严格整数输入：拒绝小数，绝不静默截断。"""
    inner = getattr(value, "e", value)
    try:
        e = sp.sympify(inner)
    except Exception:
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if not e.is_Integer:
        raise ValueError("%s must be an integer, got %s (refusing to truncate)" % (name, value))
    return int(e)


def _num(v):
    if isinstance(v, IntervalValue):
        raise ValueError("interval values cannot be used in further arithmetic; "
                         "compute the whole expression with interval(expr, digits) instead")
    return v if isinstance(v, (Fraction, Sym)) else _frac(v)


# ---------- 基础运算 ----------

def _add(a, b):
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(_sym(a) + _sym(b))
    return _frac(a) + _frac(b)


def _sub(a, b):
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(_sym(a) - _sym(b))
    return _frac(a) - _frac(b)


def _mul(a, b):
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(_sym(a) * _sym(b))
    return _frac(a) * _frac(b)


def _div(a, b):
    if not isinstance(b, Sym) and _frac(b) == 0:
        raise ValueError("division by zero")
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(_sym(a) / _sym(b))
    return _frac(a) / _frac(b)


def _mod(a, b):
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(sp.Mod(_sym(a), _sym(b)))
    fb = _frac(b)
    if fb == 0:
        raise ValueError("modulo by zero")
    return _frac(a) % fb


def _pow(a, b):
    if isinstance(a, Sym) or isinstance(b, Sym):
        return _wrap(sp.Pow(_sym(a), _sym(b)))
    fa, fb = _frac(a), _frac(b)
    if fb.denominator == 1:
        return fa ** fb.numerator
    if fa < 0:
        raise ValueError("fractional power of a negative number is not supported")
    return _wrap(sp.sqrt(fa)) if fb == Fraction(1, 2) else _wrap(sp.Pow(fa, fb))


# ---------- 函数 ----------

def _sqrt(v):
    if isinstance(v, Sym):
        return _wrap(sp.sqrt(v.e))
    f = _frac(v)
    if f < 0:
        raise ValueError("sqrt of a negative number is not supported")
    rn, rd = math.isqrt(f.numerator), math.isqrt(f.denominator)
    if rn * rn == f.numerator and rd * rd == f.denominator:
        return Fraction(rn, rd)
    return _wrap(sp.sqrt(f))


def _round(v, n=0):
    """四舍五入（half away from zero），负数对称。"""
    n = int(_frac(n))
    if isinstance(v, Sym):
        x = _sym(v) * sp.Integer(10) ** n
        # sign(x) * floor(|x| + 1/2)，对负数也正确
        return _wrap(sp.sign(x) * sp.floor(sp.Abs(x) + sp.Rational(1, 2)) / sp.Integer(10) ** n)
    f = _frac(v)
    scale = 10 ** n
    x = f * scale
    neg = x < 0
    xa = -x if neg else x
    whole = int(xa)
    if xa - whole >= Fraction(1, 2):
        whole += 1
    if neg:
        whole = -whole
    return Fraction(whole, scale)


def _abs(v):
    return _wrap(sp.Abs(_sym(v))) if isinstance(v, Sym) else abs(_frac(v))


def _floor(v):
    if isinstance(v, Sym):
        return Fraction(int(sp.floor(v.e)))
    return Fraction(math.floor(_frac(v)))


def _ceil(v):
    if isinstance(v, Sym):
        return Fraction(int(sp.ceiling(v.e)))
    return Fraction(math.ceil(_frac(v)))


def _fn1(fn):
    return lambda v: _wrap(fn(_sym(v)))


# ---------- 聚合 ----------

def _total(a):
    if any(isinstance(x, Sym) for x in a):
        return _wrap(sum((_sym(x) for x in a), sp.Integer(0)))
    return sum((_frac(x) for x in a), Fraction(0))


def _mean(a):
    if not a:
        raise ValueError("mean of an empty list")
    return _div(_total(a), len(a))


def _variance(a, ddof=0):
    n = len(a)
    denom = n - ddof
    if n == 0:
        raise ValueError("variance of an empty list")
    if denom <= 0:
        need = ddof + 1
        raise ValueError("variance: need at least %d values (got %d)" % (need, n))
    m = _mean(a)
    if isinstance(m, Sym):
        ss = sum(((_sym(x) - m.e) ** 2 for x in a), sp.Integer(0))
        return _wrap(ss / denom)
    ss = sum(((_frac(x) - m) ** 2 for x in a), Fraction(0))
    return ss / denom


def _std(a, ddof=0):
    return _sqrt(_variance(a, ddof))


def _sort_key(x):
    return float(sp.N(_sym(x), 30))


def _sorted_values(a):
    """排序：全 Fraction 时用精确比较；含符号时用 30 位近似做键（仅决定顺序，不改变值）。"""
    vals = [_num(x) for x in a]
    if all(isinstance(x, Fraction) for x in vals):
        return sorted(vals)
    return sorted(vals, key=lambda x: float(sp.N(_sym(x), 30)))


def _median(a):
    if not a:
        raise ValueError("median of an empty list")
    s = _sorted_values(a)
    n = len(s)
    if n % 2:
        return s[n // 2]
    return _div(_add(s[n // 2 - 1], s[n // 2]), 2)


def _quantile(a, q):
    if not a:
        raise ValueError("quantile of an empty list")
    s = _sorted_values(a)
    qv = _num(q)
    if isinstance(qv, Sym):
        qnum = float(sp.N(qv.e, 30))
    else:
        qnum = float(qv)
    if qnum < 0 or qnum > 1:
        raise ValueError("quantile: q must be between 0 and 1, got %s" % qv)
    pos = (len(s) - 1) * qv
    lo = int(sp.floor(_sym(pos))) if isinstance(pos, Sym) else int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    frac = _sub(pos, lo)
    return _add(s[lo], _mul(_sub(s[hi], s[lo]), frac))


# ---------- 语义函数 ----------

def _loan_pmt(P, annual_rate, years):
    P, r = _frac(P), _frac(annual_rate) / 12
    n = int_arg(_frac(years) * 12, "years * 12 (months)")
    if n <= 0:
        raise ValueError("loan_pmt: years must be positive")
    if r == 0:
        return P / n
    return P * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _cagr(end, start, years):
    start = _frac(start)
    years = _frac(years)
    if start <= 0:
        raise ValueError("cagr: start must be > 0")
    if years == 0:
        raise ValueError("cagr: years must be non-zero")
    return _sub(_pow(_div(end, start), _div(1, years)), 1)


def _fv(P, rate, n):
    return _mul(P, _pow(_add(1, rate), n))


def _discount(price, pct):
    return _mul(price, _sub(1, _div(pct, 100)))


def _markup(price, pct):
    return _mul(price, _add(1, _div(pct, 100)))


def _pct_of(x, pct):
    return _div(_mul(x, pct), 100)

def _as_float(v):
    if isinstance(v, Sym):
        return float(sp.N(v.e, 30))
    return float(v)


def _require_symbol(v, fname):
    if not isinstance(v, Sym):
        raise ValueError("%s: the variable must be a symbol such as x" % fname)
    return v


def _solve(expr, var):
    v = _require_symbol(var, "solve")
    sols = sp.solve(_sym(expr), v.e)
    out = []
    for sol in sols:
        if isinstance(sol, dict):
            sol = sol.get(v.e, sp.nan)
        out.append(_wrap(sol))
    return out


def _diff(expr, var, order=1):
    v = _require_symbol(var, "diff")
    n = int_arg(order, "order")
    if n < 0:
        raise ValueError("diff: order must be >= 0")
    if isinstance(expr, Fraction):
        return Fraction(0)
    return _wrap(sp.diff(_sym(expr), v.e, n))


def _simplify(expr):
    return _wrap(sp.simplify(_sym(expr)))


def _expand(expr):
    return _wrap(sp.expand(_sym(expr)))


def _factor(expr):
    return _wrap(sp.factor(_sym(expr)))


def _subs(expr, var, value):
    v = _require_symbol(var, "subs")
    return _wrap(_sym(expr).subs(v.e, _sym(value)))


def _solve_real(expr, var):
    """只返回实数根（IRR 这类场景用）。"""
    v = _require_symbol(var, "solve_real")
    out = []
    for sol in sp.solve(_sym(expr), v.e):
        if isinstance(sol, dict):
            sol = sol.get(v.e)
        if sol is None or sol in (sp.nan, sp.zoo):
            continue
        try:
            if sp.im(sol) == 0:
                out.append(_wrap(sol))
        except Exception:
            continue
    return out


def _numeric(value, digits):
    """显式数值化：N(expr, digits)。不覆盖符号形式，返回带精度的十进制约值。"""
    if isinstance(digits, Fraction):
        n = int(digits)
    else:
        n = int(_sym(digits))
    if n < 1 or n > 1000:
        raise ValueError("N: digits must be between 1 and 1000")
    e = _sym(value)
    if getattr(e, "free_symbols", None):
        raise ValueError("N: expression has free symbols; substitute values first")
    approx = sp.N(e, n)
    if isinstance(approx, sp.Float):
        return Sym(approx)
    return _wrap(approx)


_IV_FUNCS = {
    "exp": iv.exp,
    "log": iv.log,
    "sqrt": iv.sqrt,
    "sin": iv.sin,
    "cos": iv.cos,
    "tan": iv.tan,
    "atan": lambda value: iv.atan2(value, iv.mpf(1)),
}


def _iv_eval(e):
    e = sp.sympify(e)
    if e is sp.pi:
        return iv.pi
    if e is sp.E:
        return iv.e
    if e.is_Integer:
        return iv.mpf(int(e))
    if e.is_Rational:
        return iv.mpf(int(e.p)) / iv.mpf(int(e.q))
    if e.is_Add:
        total = iv.mpf(0)
        for term in e.args:
            total = total + _iv_eval(term)
        return total
    if e.is_Mul:
        total = iv.mpf(1)
        for factor in e.args:
            total = total * _iv_eval(factor)
        return total
    if e.is_Pow:
        base = _iv_eval(e.base)
        exponent = e.exp
        if exponent.is_Integer:
            return base ** int(exponent)
        if exponent == sp.Rational(1, 2):
            return iv.sqrt(base)
        raise ValueError("interval: unsupported exponent %s" % exponent)
    name = getattr(e.func, "__name__", "")
    handler = _IV_FUNCS.get(name)
    if handler is not None and len(e.args) == 1:
        return handler(_iv_eval(e.args[0]))
    raise ValueError("interval: unsupported operation %s" % e.func)


def _interval(expr, digits=20):
    """区间算术：返回 [下界, 上界]，可证明地包住真实值。"""
    if isinstance(digits, Fraction):
        n = int(digits)
    else:
        n = int(_sym(digits))
    if n < 1 or n > 200:
        raise ValueError("interval: digits must be between 1 and 200")
    e = _sym(expr)
    if getattr(e, "free_symbols", None):
        raise ValueError("interval: expression has free symbols; substitute values first")
    old_dps = iv.dps
    try:
        iv.dps = n + 10
        result = _iv_eval(e)
        lo_raw, hi_raw = result._mpi_
        lo_mpf = mp.make_mpf(lo_raw)
        hi_mpf = mp.make_mpf(hi_raw)

        old_mp_dps = mp.dps
        try:
            mp.dps = n + 20

            def outward(value, down):
                if value == 0:
                    return "0"
                exponent = int(mp.floor(mp.log10(abs(value)))) - n + 1
                scale = mp.power(10, exponent)
                scaled = value / scale
                rounded = mp.floor(scaled) if down else mp.ceil(scaled)
                return mp.nstr(rounded * scale, n + 2, strip_zeros=True)

            lo = outward(lo_mpf, True)
            hi = outward(hi_mpf, False)
        finally:
            mp.dps = old_mp_dps
        return IntervalValue(lo, hi)
    finally:
        iv.dps = old_dps


def _first(a):
    if not a:
        raise ValueError("first of an empty list")
    return _num(a[0])


def _last(a):
    if not a:
        raise ValueError("last of an empty list")
    return _num(a[-1])


def _series(expr, var, start, end, step=1):
    """对 x = start..end 逐点求值，返回列表（用于逐年复利、分期摊还、批量折算）。"""
    v = _require_symbol(var, "series")
    a, b, st = _num(start), _num(end), _num(step)
    step_f = _as_float(st)
    end_f = _as_float(b)
    if step_f == 0:
        raise ValueError("series: step must not be zero")
    out = []
    cur = a
    while True:
        cur_f = _as_float(cur)
        if (step_f > 0 and cur_f > end_f + 1e-12) or (step_f < 0 and cur_f < end_f - 1e-12):
            break
        if len(out) >= LIMITS["max_series"]:
            raise ValueError("series: more than %d elements (raise the range or use a filter)" % LIMITS["max_series"])
        if isinstance(expr, Sym):
            out.append(_wrap(expr.e.subs(v.e, _sym(cur))))
        else:
            out.append(expr)
        cur = _add(cur, st)
    return out


UNITS = {
    "m/s": ("speed", Fraction(1)),
    "km/h": ("speed", Fraction(1000, 3600)),
    "mph": ("speed", Fraction(44704, 100000)),
    "m": ("length", Fraction(1)),
    "km": ("length", Fraction(1000)),
    "cm": ("length", Fraction(1, 100)),
    "mm": ("length", Fraction(1, 1000)),
    "mile": ("length", Fraction(1609344, 1000)),
    "kg": ("mass", Fraction(1)),
    "g": ("mass", Fraction(1, 1000)),
    "MB": ("data", Fraction(1)),
    "GB": ("data", Fraction(1024)),
    "TB": ("data", Fraction(1048576)),
}


def _convert(v, frm, to):
    if frm not in UNITS or to not in UNITS:
        raise ValueError("unknown unit; supported: %s" % ", ".join(sorted(UNITS)))
    dimf, df = UNITS[frm]
    dimt, dt = UNITS[to]
    if dimf != dimt:
        raise ValueError("dimension mismatch: %s (%s) vs %s (%s)" % (frm, dimf, to, dimt))
    return _mul(v, _div(df, dt))


FUNCS = {
    "sqrt": _sqrt,
    "abs": _abs,
    "round": _round,
    "floor": _floor,
    "ceil": _ceil,
    "exp": _fn1(sp.exp),
    "ln": _fn1(sp.log),
    "log": lambda x, b=10: _wrap(sp.log(_sym(x), _sym(b))),
    "sin": _fn1(sp.sin),
    "cos": _fn1(sp.cos),
    "tan": _fn1(sp.tan),
    "atan": _fn1(sp.atan),
    "sum": _total,
    "count": lambda a: Fraction(len(a)),
    "min": lambda a: min((_num(x) for x in a), key=_sort_key),
    "max": lambda a: max((_num(x) for x in a), key=_sort_key),
    "mean": _mean,
    "std": lambda a: _std(a, 0),
    "var": lambda a: _variance(a, 0),
    "std_pop": lambda a: _std(a, 0),
    "std_sample": lambda a: _std(a, 1),
    "var_pop": lambda a: _variance(a, 0),
    "var_sample": lambda a: _variance(a, 1),
    "median": _median,
    "quantile": _quantile,
    "loan_pmt": _loan_pmt,
    "cagr": _cagr,
    "fv": _fv,
    "discount": _discount,
    "markup": _markup,
    "pct_of": _pct_of,
    "convert": _convert,
    "solve": _solve,
    "diff": _diff,
    "simplify": _simplify,
    "expand": _expand,
    "factor": _factor,
    "subs": _subs,
    "series": _series,
    "solve_real": _solve_real,
    "N": _numeric,
    "interval": _interval,
    "assume": _assume,
    "forget": _forget,
    "first": _first,
    "last": _last,
}


def _const(name):
    if name == "pi":
        return _wrap(sp.pi)
    if name == "e":
        return _wrap(sp.E)
    raise ValueError("unknown name %r" % name)


_NORMALIZE = str.maketrans({"^": "**", "×": "*", "÷": "/", "（": "(", "）": ")", "，": ","})

_CODE_LIKE = [
    (";", "multiple statements are not supported - send ONE expression"),
    ("=", "assignment is not supported - send ONE expression"),
    ("lambda ", "lambdas are not supported - send ONE expression"),
    ("def ", "function definitions are not supported - use defs instead"),
    ("import ", "imports are not supported"),
]


def _hint_code_like(text):
    for needle, hint in _CODE_LIKE:
        if needle in text:
            return hint
    if " for " in text or text.startswith("for "):
        return "loops/comprehensions are not supported - use std([...]), sum([...]), mean([...])"
    return None


def ev(node, env, funcs, depth=0):
    if depth > 64:
        raise ValueError("recursion too deep")
    if isinstance(node, ast.Expression):
        return ev(node.body, env, funcs, depth)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return _num(node.value)
        raise ValueError("unsupported constant")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        if node.id in ("pi", "e"):
            return _const(node.id)
        if re.fullmatch(r"[a-zA-Z]", node.id):
            return _wrap(_symbol(node.id))
        raise ValueError("unknown name %r" % node.id)
    if isinstance(node, ast.List):
        if len(node.elts) > LIMITS["max_array_items"]:
            raise ValueError("array literal too long: %d (max %d)"
                             % (len(node.elts), LIMITS["max_array_items"]))
        return [ev(x, env, funcs, depth) for x in node.elts]
    if isinstance(node, ast.UnaryOp):
        v = ev(node.operand, env, funcs, depth)
        if isinstance(node.op, ast.USub):
            return _wrap(-_sym(v)) if isinstance(v, Sym) else -_frac(v)
        if isinstance(node.op, ast.UAdd):
            return v
        raise ValueError("unsupported unary op")
    if isinstance(node, ast.BinOp):
        a = ev(node.left, env, funcs, depth)
        b = ev(node.right, env, funcs, depth)
        if isinstance(node.op, ast.Add):
            return _add(a, b)
        if isinstance(node.op, ast.Sub):
            return _sub(a, b)
        if isinstance(node.op, ast.Mult):
            return _mul(a, b)
        if isinstance(node.op, ast.Div):
            return _div(a, b)
        if isinstance(node.op, ast.Mod):
            return _mod(a, b)
        if isinstance(node.op, (ast.Pow, ast.BitXor)):
            return _pow(a, b)
        raise ValueError("unsupported binop")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        args = [ev(a, env, funcs, depth) for a in node.args]
        if name in funcs:
            params, body = funcs[name]
            if len(params) != len(args):
                raise ValueError("%s expects %d args, got %d" % (name, len(params), len(args)))
            scope = dict(env)
            for p, a in zip(params, args):
                scope[p] = a
            return ev(body, scope, funcs, depth + 1)
        if name == "convert":
            return FUNCS[name](*args)
        if name not in FUNCS:
            close = difflib.get_close_matches(name, list(FUNCS), n=1)
            guess = (" did you mean %r?" % close[0]) if close else ""
            raise ValueError("unknown function %r;%s supported: %s"
                             % (name, guess, ", ".join(sorted(FUNCS))))
        return FUNCS[name](*[a if isinstance(a, (list, str)) else _num(a) for a in args])
    raise ValueError("unsupported syntax: %s" % type(node).__name__)


def load_lib(path, env, funcs):
    import json as _json
    if str(path).lower().endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            apply_defs(_json.load(fh), env, funcs)
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("const "):
                name, _, expr = line[6:].partition("=")
                env[name.strip()] = calc(expr.strip(), env, funcs)
            elif line.startswith("fn "):
                sig, _, body = line[3:].partition("=")
                fname, _, params = sig.partition("(")
                params = [p.strip() for p in params.strip().rstrip(")").split(",") if p.strip()]
                funcs[fname.strip()] = (params, ast.parse(body.strip(), mode="eval"))
            else:
                raise ValueError("bad line in %s: %r" % (path, line))


def apply_defs(data, env, funcs):
    for name, val in data.get("const", {}).items():
        env[name] = calc(val, env, funcs) if isinstance(val, str) else _num(val)
    for name, spec in data.get("fn", {}).items():
        funcs[name] = (spec["p"], ast.parse(spec["e"], mode="eval"))


class PackRegistry:
    """能力包注册器：pack 通过 register(reg) 注册自己的函数。"""

    def __init__(self):
        self.entries = {}

    def func(self, name, params, impl, doc=""):
        self.entries[name] = (list(params), impl, doc)


FUNCS_DOCS = {}


def load_packs(directory, target=None):
    """从目录加载 *.py 能力包；每个包暴露 register(reg)。返回已加载的文件名。"""
    import importlib.util
    from pathlib import Path

    target = target if target is not None else FUNCS
    docs = FUNCS_DOCS
    loaded = []
    root = Path(directory)
    if not root.is_dir():
        return loaded
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location("calcpack_" + path.stem, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            register = getattr(module, "register", None)
            if not callable(register):
                continue
            registry = PackRegistry()
            register(registry)
            for name, (params, impl, _doc) in registry.entries.items():
                target[name] = impl
                if _doc:
                    docs[name] = (params, _doc)
            loaded.append(path.name)
        except Exception as ex:  # 一个坏包不影响其他包
            print("pack load failed %s: %s" % (path.name, ex), file=sys.stderr)
    return loaded


_DECIMAL_LITERAL = re.compile(
    r"(?<![\w.])(?:\d+\.\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+)(?![\w.])"
)


def _exactify_literals(text):
    """把小数/科学记数法字面量换成精确分数，避免 Python float 丢位。"""
    parts = re.split(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')', text)
    for index in range(0, len(parts), 2):
        def replace(match):
            value = Fraction(Decimal(match.group(0)))
            return "(%d/%d)" % (value.numerator, value.denominator)
        parts[index] = _DECIMAL_LITERAL.sub(replace, parts[index])
    return "".join(parts)


def calc(expr, env=None, funcs=None):
    env = env or {}
    funcs = funcs or {}
    text = expr.translate(_NORMALIZE)
    stripped = text.strip()
    if stripped in ("functions()", "functions ()"):
        return ", ".join(sorted(FUNCS))
    match = re.fullmatch(r"help\(\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?\s*\)", text)
    if match:
        name = match.group(1)
        if name not in FUNCS:
            raise ValueError("unknown function '%s' (call functions() to list names)" % name)
        doc = FUNCS_DOCS.get(name)
        if doc:
            params, description = doc
            return "%s(%s) — %s" % (name, ", ".join(params), description)
        return "%s(...) — no doc; call functions() for names" % name
    if len(text) > LIMITS["max_expr_chars"]:
        raise ValueError("expression too long: %d chars (max %d)"
                         % (len(text), LIMITS["max_expr_chars"]))
    hint = _hint_code_like(text)
    if hint:
        raise ValueError("not an expression (hint: %s)" % hint)
    text = _exactify_literals(text)
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as ex:
        raise ValueError(
            "syntax error at column %s (hint: send ONE expression; for standard deviation use std([...]), "
            "for variance var_pop([...]))" % (ex.offset or "?"))
    return ev(tree, env, funcs)


# ---------- 计算计划（steps） ----------

def eval_steps(steps, expr=None, env=None, funcs=None):
    """按顺序求值命名步骤，再求最终表达式；每步结果留在环境里供后续引用。

    返回 (最终值, [(name, value), ...])。
    """
    if len(steps) > LIMITS["max_steps"]:
        raise ValueError("too many steps: %d (max %d)" % (len(steps), LIMITS["max_steps"]))
    env = dict(env or {})
    funcs = funcs or {}
    results = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("steps: each step must be {name, expr}")
        name = step.get("name")
        sub = step.get("expr")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("steps: every step needs a non-empty name")
        if not isinstance(sub, str) or not sub.strip():
            raise ValueError("steps: step %r needs an expr" % name)
        try:
            value = calc(sub, env, funcs)
        except Exception as ex:
            raise ValueError("step %r failed: %s" % (name, ex))
        env[name.strip()] = value
        results.append((name.strip(), value))
    if expr is not None and str(expr).strip():
        final = calc(expr, env, funcs)
    else:
        if not results:
            raise ValueError("provide either expr or at least one step")
        final = results[-1][1]
    return final, results


# ---------- 渲染 ----------

def _terminating(f):
    d = f.denominator
    k2 = k5 = 0
    while d % 2 == 0:
        d //= 2
        k2 += 1
    while d % 5 == 0:
        d //= 5
        k5 += 1
    return d == 1, max(k2, k5)


def _exact_decimal(f):
    term, k = _terminating(f)
    if not term:
        return None
    num = f.numerator * (10 ** k // f.denominator)
    sign = "-" if num < 0 else ""
    s = str(abs(num)).rjust(k + 1, "0")
    if k:
        s = s[:-k] + "." + s[-k:]
        s = s.rstrip("0").rstrip(".")
    return sign + s


def _sym_text(v):
    return sp.sstr(v.e)


def _decimal_of(v, digits=DISPLAY_DIGITS):
    e = _sym(v)
    try:
        d = sp.N(e, digits)
        return sp.sstr(d)
    except Exception:
        return None


def fmt(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = _num(v)
    if isinstance(v, Sym):
        return _sym_text(v)
    if isinstance(v, Fraction):
        s = _exact_decimal(v)
        return s if s is not None else "%d/%d" % (v.numerator, v.denominator)
    raise ValueError("cannot format %r" % (v,))


def format_result(v):
    """返回 {v: 精确形式, d?: 数值近似, exact, w?}。"""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = _num(v)
    if isinstance(v, IntervalValue):
        return {"v": "[%s, %s]" % (v.lo, v.hi), "exact": False,
                "w": "interval arithmetic (guaranteed enclosure)"}
    if isinstance(v, list):
        if len(v) > LIMITS["max_output_items"]:
            head = ", ".join(fmt(x) for x in v[:3])
            tail = ", ".join(fmt(x) for x in v[-3:])
            return {"v": "[%d values: %s ... %s]" % (len(v), head, tail),
                    "exact": False,
                    "w": "list truncated: %d items (max %d)"
                         % (len(v), LIMITS["max_output_items"])}
        parts = [format_result(x) for x in v]
        out = {"v": [p["v"] for p in parts], "exact": all(p["exact"] for p in parts)}
        decimals = [p.get("d") for p in parts]
        if all(d is not None for d in decimals):
            out["d"] = decimals
        warns = [p["w"] for p in parts if p.get("w")]
        if warns:
            out["w"] = "; ".join(warns)
        return out

    if isinstance(v, Sym):
        if isinstance(v.e, sp.Interval):
            return {"v": "[%s, %s]" % (sp.sstr(v.e.start), sp.sstr(v.e.end)),
                    "exact": False, "w": "interval arithmetic (guaranteed enclosure)"}
        if isinstance(v.e, sp.Float):
            digits = int(round(v.e._prec * 0.3010299956639812))
            return {"v": sp.sstr(v.e), "exact": False,
                    "w": "numeric evaluation (N, ~%d digits)" % digits}
        text = _sym_text(v)
        if len(text) > MAX_SYMBOL_LEN:
            if LIMITS.get("exact_only"):
                out = {"v": text, "exact": True,
                       "w": "symbolic form kept (exact_only, %d chars)" % len(text)}
                dec = _decimal_of(v)
                if dec:
                    out["d"] = dec
                return out
            if LIMITS.get("strict_numeric"):
                raise ValueError("strict_numeric: symbolic result is %d chars; "
                                 "use N(expr, digits) or raise max_symbol_len" % len(text))
            dec = _decimal_of(v)
            return {"v": dec or text[:MAX_SYMBOL_LEN] + "…", "exact": False,
                    "w": "expression is too long; showing a numeric approximation"}
        out = {"v": text, "exact": True}
        if not v.e.free_symbols:
            dec = _decimal_of(v)
            if dec and dec != text:
                out["d"] = dec
        return out

    if isinstance(v, Fraction):
        s = _exact_decimal(v)
        if s is not None:
            if len(s) > MAX_DECIMAL_LEN:
                if LIMITS.get("strict_numeric"):
                    raise ValueError("strict_numeric: exact decimal would be %d digits; "
                                     "use N(expr, digits) or raise max_decimal_len" % len(s))
                return {"v": sp.sstr(sp.N(sp.Rational(v.numerator, v.denominator), DISPLAY_DIGITS)),
                        "exact": False,
                        "w": "number has %d digits; showing %d significant digits"
                             % (len(s), DISPLAY_DIGITS)}
            return {"v": s, "exact": True}
        fn, fd = str(v.numerator), str(v.denominator)
        out = {"v": "%s/%s" % (fn, fd), "exact": True,
               "d": sp.sstr(sp.N(sp.Rational(v.numerator, v.denominator), DISPLAY_DIGITS))}
        if len(fn) + len(fd) > MAX_SYMBOL_LEN:
            if LIMITS.get("strict_numeric"):
                raise ValueError("strict_numeric: exact fraction is %d digits; "
                                 "use N(expr, digits) or raise max_symbol_len" % (len(fn) + len(fd)))
            out["v"] = out.pop("d")
            out["exact"] = False
            out["w"] = "exact fraction is too large; showing %d significant digits" % DISPLAY_DIGITS
        return out

    return {"v": str(v), "exact": True}
