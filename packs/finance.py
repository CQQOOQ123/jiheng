"""finance 能力包：NPV、年金、折现、IRR、债券、Black-Scholes。"""

NAME = "finance"
VERSION = "0.2.0"
DESCRIPTION = "npv / annuity_pv / discount_factor / irr / bond / black_scholes"
REQUIRES = []

import math
from fractions import Fraction

import mpmath as mp

import sympy as sp

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(v)


def _wrap(v):
    return _core._wrap(v)


def _approx(x):
    return _wrap(sp.Float(x, 15))


def discount_factor(rate, n):
    r = _f(rate)
    if r <= -1:
        raise ValueError("discount_factor: rate must be > -1")
    return Fraction(1, 1) / (1 + r) ** int(_f(n))


def npv(rate, cashflows, start=0):
    """净现值。

    start=0（默认）：cashflows[0] 发生在 t=0（首笔不折现）。
    start=1：cashflows[0] 发生在第 1 年末（首笔折现 1 年）。
    """
    r = _f(rate)
    if r <= -1:
        raise ValueError("npv: rate must be > -1")
    offset = int(getattr(start, "e", start))
    if offset not in (0, 1):
        raise ValueError("npv: start must be 0 or 1")
    total = Fraction(0)
    for t, cf in enumerate(cashflows):
        total += _f(cf) / (1 + r) ** (t + offset)
    return total


def annuity_pv(payment, rate, periods):
    r = _f(rate)
    n = int(_f(periods))
    if r == 0:
        return _f(payment) * n
    return _f(payment) * (1 - (1 + r) ** (-n)) / r


def irr(cashflows):
    """内部收益率：在 (-0.9999, 10) 上二分求 NPV=0。

    现金流转号多于一次时，可能存在多个 IRR；这里明确拒绝，而不是只返回一个根。
    """
    flows = [_f(cf) for cf in cashflows]
    if not any(cf < 0 for cf in flows) or not any(cf > 0 for cf in flows):
        raise ValueError("irr: cashflows need both negative and positive values")

    signs = [1 if cf > 0 else -1 for cf in flows if cf != 0]
    changes = sum(1 for a, b in zip(signs, signs[1:]) if a != b)
    if changes > 1:
        raise ValueError(
            "irr: cashflows change sign %d times; multiple IRRs may exist and are not "
            "supported. Scan npv(rate, cashflows) over rates instead." % changes
        )

    def npv_at(rate):
        return sum(float(cf) / (1 + rate) ** t for t, cf in enumerate(flows))

    lo, hi = -0.9999, 10.0
    if npv_at(lo) * npv_at(hi) > 0:
        raise ValueError(
            "irr: no sign change of NPV in (-0.9999, 10); the root may be outside this range"
        )
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv_at(lo) * npv_at(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return _approx((lo + hi) / 2)


def _int_arg(value, name):
    f = _f(value)
    if f.denominator != 1:
        raise ValueError("%s must be an integer, got %s (refusing to truncate)" % (name, f))
    return int(f)


def _bond_periods(years, freq):
    n = _int_arg(freq, "freq")
    if n <= 0:
        raise ValueError("freq must be a positive integer")
    periods_f = _f(years) * n
    if periods_f.denominator != 1:
        raise ValueError(
            "years must be a multiple of 1/freq (e.g. years=2.5 with freq=2); "
            "refusing to truncate %s years" % _f(years)
        )
    periods = int(periods_f)
    if periods <= 0:
        raise ValueError("years * freq must be positive")
    return n, periods


def bond_price(face, coupon_rate, years, ytm, freq=1):
    """债券价格：面值 + 票息，按年或按频次折现。"""
    n, periods = _bond_periods(years, freq)
    c = _f(face) * _f(coupon_rate) / n
    y = _f(ytm) / n
    if y <= -1:
        raise ValueError("bond_price: ytm/freq must be > -1")
    total = Fraction(0)
    for t in range(1, periods + 1):
        total += c / (1 + y) ** t
    total += _f(face) / (1 + y) ** periods
    return total


def bond_duration(face, coupon_rate, years, ytm, freq=1):
    """麦考利久期（年）。"""
    n, periods = _bond_periods(years, freq)
    c = _f(face) * _f(coupon_rate) / n
    y = _f(ytm) / n
    price = bond_price(face, coupon_rate, years, ytm, freq)
    weighted = Fraction(0)
    for t in range(1, periods + 1):
        weighted += t * c / (1 + y) ** t
    weighted += periods * _f(face) / (1 + y) ** periods
    return weighted / price / n


def _mp(v):
    """把 Fraction / calc_core.Sym / int 转成高精度 mpmath 值。"""
    inner = getattr(v, "e", v)
    return mp.mpf(str(sp.N(inner, 60)))


def _norm_cdf_mp(x):
    # erfc 直接算小尾概率，避免 1 + erf(-36) 在 60 位精度下被舍入成 0
    return mp.erfc(-x / mp.sqrt(2)) / 2


def black_scholes_call(spot, strike, years, rate, vol):
    S, K, T, r, sigma = (_mp(spot), _mp(strike), _mp(years), _mp(rate), _mp(vol))
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        raise ValueError("black_scholes: spot/strike/vol must be > 0 and years > 0")
    mp.mp.dps = 60
    d1 = (mp.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * mp.sqrt(T))
    d2 = d1 - sigma * mp.sqrt(T)
    price = S * _norm_cdf_mp(d1) - K * mp.e ** (-r * T) * _norm_cdf_mp(d2)
    return _wrap(sp.Float(mp.nstr(price, 40), 40))


def black_scholes_put(spot, strike, years, rate, vol):
    S, K, T, r = (_mp(spot), _mp(strike), _mp(years), _mp(rate))
    call = black_scholes_call(spot, strike, years, rate, vol)
    price = sp.Float(call.e) - S + K * mp.e ** (-r * T)
    return _wrap(sp.Float(mp.nstr(price, 40), 40))


def register(reg):
    reg.func("npv", ["rate", "cashflows", "start"], npv, doc="净现值；start=0 首笔 t=0，start=1 首笔第 1 年末")
    reg.func("annuity_pv", ["payment", "rate", "periods"], annuity_pv, doc="年金现值")
    reg.func("discount_factor", ["rate", "n"], discount_factor, doc="折现因子")
    reg.func("irr", ["cashflows"], irr, doc="内部收益率（数值）")
    reg.func("bond_price", ["face", "coupon_rate", "years", "ytm", "freq"], bond_price, doc="债券价格")
    reg.func("bond_duration", ["face", "coupon_rate", "years", "ytm", "freq"], bond_duration, doc="麦考利久期")
    reg.func("black_scholes_call", ["spot", "strike", "years", "rate", "vol"], black_scholes_call, doc="看涨期权")
    reg.func("black_scholes_put", ["spot", "strike", "years", "rate", "vol"], black_scholes_put, doc="看跌期权")
