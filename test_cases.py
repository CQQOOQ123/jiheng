#!/usr/bin/env python
"""dsh-calc 回归测试（v4 精确有理数 + 符号计算）。

契约：{"v": 精确形式, "d": 小数近似(可选), "exact": bool, "w": 告警(可选)}
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calc_core as cp  # noqa: E402

PASS, FAIL = 0, 0


def res(expr, defs=None):
    env, funcs = {}, {}
    if defs:
        cp.apply_defs(defs, env, funcs)
    return cp.format_result(cp.calc(expr, env, funcs))


def check(expr, v=None, exact=None, d_prefix=None, defs=None):
    """v=None 表示只校验 exact/d。"""
    global PASS, FAIL
    try:
        r = res(expr, defs)
    except Exception as ex:
        FAIL += 1
        print("FAIL %s => ERROR %s: %s" % (expr, type(ex).__name__, ex))
        return
    ok = True
    if v is not None and r["v"] != v:
        ok = False
    if exact is not None and r["exact"] is not exact:
        ok = False
    if d_prefix is not None and not str(r.get("d", "")).startswith(d_prefix):
        ok = False
    if ok:
        PASS += 1
        print("ok   %-36s => v=%s%s exact=%s"
              % (expr, r["v"][:46], (" d=" + r["d"][:20]) if r.get("d") else "", r["exact"]))
    else:
        FAIL += 1
        print("FAIL %-36s => %r (want v=%r exact=%r d~%r)"
              % (expr, r, v, exact, d_prefix))


def raises(expr, contains):
    global PASS, FAIL
    try:
        res(expr)
        FAIL += 1
        print("FAIL %s: expected error containing %r, got value" % (expr, contains))
    except Exception as ex:
        if contains in str(ex):
            PASS += 1
            print("ok   %-36s => rejected" % expr)
        else:
            FAIL += 1
            print("FAIL %s: error %r missing %r" % (expr, str(ex), contains))


# ---- 分数：保留精确形式 ----
check("1/3", "1/3", True, d_prefix="0.333333")
check("1/3+1/6", "0.5", True)
check("1/7*7", "1", True)
check("0.1+0.2", "0.3", True)
check("2/4", "0.5", True)

# ---- 根号：保留符号形式 ----
check("sqrt(2)", "sqrt(2)", True, d_prefix="1.4142")
check("2^0.5", "sqrt(2)", True)
check("sqrt(4)", "2", True)
check("sqrt(1/4)", "0.5", True)
check("sqrt(2)*sqrt(2)", "2", True)

# ---- 大整数：逐位精确 ----
check("2^200", "1606938044258990275541962092341162602522202993782792835301376", True)
check("(10^30+7)*(10^30+7)",
      "1000000000000000000000000000014000000000000000000000000000049", True)
check("10^100", "1" + "0" * 100, True)

# ---- 统计 ----
check("std([12,15,9,22])", "sqrt(93)/2", True, d_prefix="4.8218")
check("var_pop([12,15,9,22])", "23.25", True)
check("mean([12,15,9,22])", "14.5", True)
check("median([3,1,4,1,5,9,2,6])", "3.5", True)

# ---- 符号常量/函数 ----
check("sin(pi/6)", "0.5", True)
check("log(1000,10)", "3", True)
check("pi", "pi", True, d_prefix="3.14159")

# ---- 语义函数 ----
check("discount(1000,8.75)", "912.5", True)
check('convert(2,"GB","MB")', "2048", True)
check('convert(120,"km/h","m/s")', "100/3", True, d_prefix="33.3333")
check("loan_pmt(1000000,0.049,30)", exact=False)

# ---- 符号计算 ----
check("solve(x^2-5*x+6, x)", ["2", "3"], True)
check("solve(2*x-4, x)", ["2"], True)
check("diff(x^3+2*x, x)", "3*x**2 + 2", True)
check("diff(sin(x), x)", "cos(x)", True)
check("simplify(sin(x)^2+cos(x)^2)", "1", True)
check("expand((x+1)^2)", "x**2 + 2*x + 1", True)
check("factor(x^2-1)", "(x - 1)*(x + 1)", True)
check("subs(x^2+1, x, 3)", "10", True)
check("solve_real(x^2-5*x+6, x)", ["2", "3"], True)
check("solve_real(x^2+1, x)", [], True)
check("first([3,1,4])", "3", True)
check("last([3,1,4])", "4", True)
check("series(1000*1.05^x, x, 1, 3)", ["1050", "1102.5", "1157.625"], True)
check("sum(series(1000*1.05^x, x, 1, 12))", "16712.982846464712158203125", True)
check("mean(series(x^2, x, 1, 10))", "38.5", True)
check("series(x^2, x, 0, 5, 2)", ["0", "4", "16"], True)

# ---- steps（计算计划） ----
def check_steps(steps, expr, expected):
    global PASS, FAIL
    v, _ = cp.eval_steps(steps, expr)
    got = cp.format_result(v)["v"]
    if got == expected:
        PASS += 1
        print("ok   steps -> %s" % got)
    else:
        FAIL += 1
        print("FAIL steps -> %r (want %r)" % (got, expected))

check_steps([{"name": "a", "expr": "1/3"}, {"name": "b", "expr": "a*3"}], "b", "1")
check_steps([{"name": "r", "expr": "0.049/12"}, {"name": "n", "expr": "360"},
             {"name": "f", "expr": "(1+r)^n"}, {"name": "pmt", "expr": "1000000*r*f/(f-1)"}],
            "pmt", "5307.26720622811041199517353180")

# ---- 舍入语义（half-up，不是银行家） ----
check("round(2.5)", "3", True)
check("round(-2.5)", "-3", True)
check("round(2.675, 2)", "2.68", True)

# ---- 自定义定义 ----
check("含税(1000)", "1130", True, defs={"fn": {"含税": {"p": ["x"], "e": "x*(1+0.13)"}}})
check("折后(含税(1000),0.1)", "1017", True, defs={"fn": {
    "含税": {"p": ["x"], "e": "x*(1+0.13)"},
    "折后": {"p": ["x", "d"], "e": "x*(1-d)"}}})

# ---- 错误提示 ----
raises("1/0", "division by zero")
raises("sqrt(sum([(x-mean([1,2]))^2 for x in [1,2]]))", "loops/comprehensions")
raises("a=1; b=2", "multiple statements")
raises("foo(1)", "unknown function")
raises('convert(2,"GB","kg")', "dimension mismatch")
raises("__import__('os').system('dir')", "unsupported")

# ---- 限额与摘要 ----
cp.apply_limits({"max_series": 3})
raises("series(x, x, 1, 5)", "more than 3")
cp.apply_limits({"max_expr_chars": 8})
raises("1+2+3+4+5+6", "expression too long")
cp.apply_limits({"max_output_items": 2})
r = cp.format_result([1, 2, 3, 4])
if r["v"].startswith("[4 values:") and r["exact"] is False:
    PASS += 1
    print("ok   list summary ->", r["v"][:40])
else:
    FAIL += 1
    print("FAIL list summary ->", r)
cp.apply_limits(cp.DEFAULT_LIMITS)

# ---- N() 与 strict_numeric ----
r = cp.format_result(cp.calc("N(pi/3, 30)"))
if r["exact"] is False and str(r["v"]).startswith("1.04719755119659774615421446109") and "numeric" in r.get("w", ""):
    PASS += 1
    print("ok   N(pi/3, 30)")
else:
    FAIL += 1
    print("FAIL N(pi/3, 30) ->", r)

cp.apply_limits({"strict_numeric": 1})
try:
    cp.format_result(cp.calc("loan_pmt(1000000, 0.049, 30)"))
    FAIL += 1
    print("FAIL strict_numeric should raise")
except ValueError as ex:
    PASS += 1
    print("ok   strict_numeric ->", str(ex)[:46])
r = cp.format_result(cp.calc("N(loan_pmt(1000000, 0.049, 30), 20)"))
if r["exact"] is False and str(r["v"]).startswith("5307.2672"):
    PASS += 1
    print("ok   strict_numeric + N")
else:
    FAIL += 1
    print("FAIL strict_numeric + N ->", r)
cp.apply_limits(cp.DEFAULT_LIMITS)

# ---- interval 区间算术 ----
r = cp.format_result(cp.calc("interval(sqrt(2), 10)"))
if str(r["v"]).startswith("[1.414213562") and r["exact"] is False and "interval" in r.get("w", ""):
    PASS += 1
    print("ok   interval(sqrt(2),10) ->", r["v"][:36])
else:
    FAIL += 1
    print("FAIL interval(sqrt(2),10) ->", r)

r = cp.format_result(cp.calc("interval(1/3, 12)"))
if str(r["v"]).startswith("[0.3333333333") and str(r["v"]).endswith("334]"):
    PASS += 1
    print("ok   interval(1/3,12)")
else:
    FAIL += 1
    print("FAIL interval(1/3,12) ->", r)

# ---- assume / forget 假设 ----
r = cp.format_result(cp.calc('assume(x, "positive") + simplify(sqrt(x^2))'))
if r["v"] == "x + 1":
    PASS += 1
    print("ok   assume(positive)")
else:
    FAIL += 1
    print("FAIL assume(positive) ->", r)
r = cp.format_result(cp.calc('forget(x) + simplify(sqrt(x^2))'))
if r["v"] == "sqrt(x**2) + 1":
    PASS += 1
    print("ok   forget()")
else:
    FAIL += 1
    print("FAIL forget() ->", r)

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
