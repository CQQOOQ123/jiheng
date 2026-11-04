#!/usr/bin/env python
"""能力包测试：加载 .calc/plugins 下的包并验证函数结果。"""
import sys
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import calc_core as cp  # noqa: E402

PASS, FAIL = 0, 0


def res(expr):
    return cp.format_result(cp.calc(expr))


def check(expr, expected):
    global PASS, FAIL
    got = res(expr)["v"]
    if got == expected:
        PASS += 1
        print("ok   %-46s => %s" % (expr, got))
    else:
        FAIL += 1
        print("FAIL %-46s => %r (want %r)" % (expr, got, expected))


PACKS_DIR = next(
    (path for path in (HERE / "packs", ROOT / ".calc" / "plugins") if path.is_dir()),
    None,
)
assert PACKS_DIR is not None, "能力包目录不存在"
loaded = cp.load_packs(PACKS_DIR)
print("packs:", loaded)
assert "stats.py" in loaded and "finance.py" in loaded, "示例能力包未加载"

check("dot([1,2,3],[4,5,6])", "32")
check("cov([1,2,3,4],[2,4,5,4])", "7/6")
check("corr([1,2,3,4],[2,4,5,4])", "7*sqrt(95)/95")
check("regression([1,2,3,4],[2,4,5,4])", ["0.7", "2", "49/95"])
check("npv(0.1, [-500, 100, 200, 300])", "-24500/1331")
check("discount_factor(0.05, 3)", "8000/9261")
check("pct_change([100,110,121])", ["0.1", "0.1"])
check("cumsum([1,2,3])", ["1", "3", "6"])
check("max_drawdown([100,120,90,110])", "-0.25")
check("zscore([1,2,3])", ["-1", "0", "1"])
check("sharpe([0.01,0.02,-0.01,0.03])", "sqrt(105)/14")
check("log_returns([100,110])", ["log(11/10)"])
check("integrate(x^2, x)", "x**3/3")
check("limit(sin(x)/x, x, 0)", "1")
check("taylor(exp(x), x, 0, 3)", "x**3/6 + x**2/2 + x + 1")
check("subs(integrate(x^2, x), x, 3)", "9")

check("det([[1,2],[3,4]])", "-2")
check("eigenvals([[2,0],[0,3]])", ["2", "3"])
check("solve_linear([[2,0],[0,3]],[4,9])", [["2"], ["3"]])
check("matmul([[1,2],[3,4]],[[1,0],[0,1]])", [["1", "2"], ["3", "4"]])
check("summation(x, x, 1, 10)", "55")
check("gamma(5)", "24")
check("binomial(5,2)", "10")
check("factorial(5)", "120")
check("zeta(2)", "pi**2/6")
check("dsolve(y, x)", "C1*exp(x)")
check("norm_cdf(0)", "0.5")
check("norm_quantile(0.5)", "0")


def check_prefix(expr, prefix):
    global PASS, FAIL
    got = res(expr)["v"]
    if str(got).startswith(prefix):
        PASS += 1
        print("ok   %-46s => %s" % (expr, str(got)[:38]))
    else:
        FAIL += 1
        print("FAIL %-46s => %r (want prefix %r)" % (expr, got, prefix))


check_prefix("irr([-500,100,200,300])", "0.08208")
check_prefix("black_scholes_call(100,100,1,0.05,0.2)", "10.4505")
check_prefix("bond_price(1000,0.05,10,0.06)", "162015600304")
check_prefix("nintegrate(x^2, x, 0, 1)", "0.333333")
check_prefix("t_pdf(0,5)", "8*sqrt(5)")

def raises(expr, needle):
    global PASS, FAIL
    try:
        res(expr)
        FAIL += 1
        print("FAIL %-46s expected error" % expr)
    except Exception as ex:
        if needle in str(ex):
            PASS += 1
            print("ok   %-46s => rejected" % expr)
        else:
            FAIL += 1
            print("FAIL %-46s => %s (want %r)" % (expr, ex, needle))


check("by_parts(x, exp(x), x)", "(x - 1)*exp(x)")
check("check_antiderivative(x*exp(x) - exp(x), x*exp(x), x)", "0")
check("apart((x+1)/(x^2-1), x)", "1/(x - 1)")
check("unit_div(10, \"m\", 5, \"s\")", ["2", "m/s"])
check("unit_add(1, \"m\", 100, \"cm\")", ["2", "m"])
check("unit_pow(2, \"m\", 2)", ["4", "m^2"])
check_prefix("unit_convert(120, \"km/h\", \"m/s\")", "100/3")
raises("unit_convert(1, \"m\", \"s\")", "dimension mismatch")
check("days_between(\"2026-01-01\", \"2026-02-01\")", "31")
check("date_add(\"2026-01-31\", 1)", "2026-02-01")
check("weekday(\"2026-01-01\")", "3")
check("min([3,1,2])", "1")
check("max([3,1,2])", "3")
raises("min([])", "empty")
raises("max([])", "empty")
raises("quantile([1,2], 1.5)", "between 0 and 1")
raises("quantile([1,2], -0.1)", "between 0 and 1")
raises("bond_duration(0, 0.05, 2, 0.05, 1)", "face must be > 0")
raises("date_add('2026-01-01', 1.5)", "days must be an integer")
raises("discount_factor(0.1, 1.5)", "n must be an integer")
raises("annuity_pv(100, 0.05, 2.5)", "periods must be an integer")
raises("factorial(1.5)", "n must be an integer")
raises("binomial(5, 2.5)", "k must be an integer")
raises("binomial(3, 5)", "0 <= k <= n")
raises("gamma(-1)", "pole")
raises("zeta(1)", "pole")
raises("unit_pow(2, 'm', 1.5)", "exponent must be an integer")
raises("diff(x^3, x, 1.5)", "order must be an integer")
raises("max_drawdown([])", "empty")
check("loan_pmt(100000, 0, 10)", "2500/3")
raises("cagr(110, 100, 0)", "years must be non-zero")
raises("cagr(110, 0, 1)", "start must be > 0")
raises("temp_convert(-300, 'C', 'K')", "absolute zero")
raises("去税(100, -1)", "分母为 0")
raises("bond_price(100, 0.05, 2.5, 0.05, 1)", "refusing to truncate")
check("bond_price(100, 0.05, 2.5, 0.05, 2)", "100")
raises("irr([-100, 230, -132])", "multiple IRRs")
raises("sharpe([1, 1, 1])", "zero variance")
raises("zscore([1, 1, 1])", "zero variance")
raises("std_sample([5])", "at least 2")
check("var([1,2,3])", "2/3")
check_prefix("black_scholes_call(100, 1000, 0.1, 0.05, 0.2)", "1.602049234")
raises("weekday(\"2026-02-30\")", "invalid date")
raises("weekday(\"2026-13-01\")", "month must be 1..12")
raises("weekday(8)", "expected YYYY-MM-DD")
check("weekday(\"2024-02-29\")", "3")
check("temp_convert(100, \"C\", \"F\")", "212")
check("temp_convert(32, \"F\", \"C\")", "0")
check("currency_convert(100, \"USD\", \"CNY\")", "720")
check("currency_rate(\"USD\")", "1")
check("pct_part(25, 200)", "0.125")
check("yoy(110, 100)", "0.1")
check("tax_included(1000, 0.13)", "1130")
check("tax_excluded(1130, 0.13)", "1000")
check("discount_price(1000, 0.1)", "900")
check("growth_multiple(150, 100)", "1.5")
check("stress(1000, 0.01)", "100000")
check("strain(0.001, 1)", "0.001")
check("youngs_modulus(200000000, 0.001)", "200000000000")
check("bending_stress(1000, 0.05, 0.000001)", "50000000")
check("beam_cantilever_point(100, 2, 200000000000, 0.000001)", "1/750")
check("beam_simply_supported_point(100, 2, 200000000000, 0.000001)", "1/12000")
check("heat_flux(0.5, 10, 0.2)", "25")
check("thermal_resistance(0.2, 0.5, 2)", "0.2")
check("thermal_expansion(1, 0.000012, 50)", "0.0006")
check("报价(100, 0.2)", "125")
check("含税(1000, 0.13)", "1130")
check("去税(1130, 0.13)", "1000")
check("折扣价(1000, 0.1)", "900")
check("到手价(1000, 0.1, 0.13)", "1017")
check("毛利(120, 100)", "20")
check("毛利率(120, 100)", "1/6")
check("加成率(120, 100)", "0.2")
check("损耗后(100, 0.05)", "95")
check("剩余本金(1000000, 0.049, 30, 0)", "1000000")
check("剩余本金(1000000, 0.049, 30, 360)", "0")
check("加班费(50, 1.5, 3)", "225")
check("补偿N加1(10000, 3)", "40000")
check("个税(10000)", "790")
check("社保基数(5000, 3000, 20000)", "5000")
check("体积重(50, 40, 30, 6000)", "10")
check("计费重(8, 10)", "10")
check("运费(10, 12, 1, 3)", "39")
check("良率(95, 100)", "0.95")
check("OEE(0.9, 0.95, 0.98)", "0.8379")
check("材料成本(2, 100, 5, 0.05)", "1050")
check("工时成本(2, 100, 50)", "10000")
check("折上折(1000, 0.1, 0.2)", "720")
check("返点(100000, 0.03)", "3000")
check("客单价(100000, 200)", "500")
check("售罄率(80, 100)", "0.8")

print("\n%d passed, %d failed" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
