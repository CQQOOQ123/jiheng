"""finance 能力包：NPV、年金、折现、IRR、债券、Black-Scholes。"""

NAME = "finance"
VERSION = "0.2.0"
DESCRIPTION = "npv / annuity_pv / discount_factor / irr / bond / black_scholes"
REQUIRES = []

import math
from fractions import Fraction

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
    """内部收益率：在 (-0.9999, 10) 上二分求 NPV=0。"""
    flows = [_f(cf) for cf in cashflows]
    if not any(cf < 0 for cf in flows) or not any(cf > 0 for cf in flows):
        raise ValueError("irr: cashflows need both negative and positive values")

    def npv_at(rate):
        return sum(float(cf) / (1 + rate) ** t for t, cf in enumerate(flows))

    lo, hi = -0.9999, 10.0
    if npv_at(lo) * npv_at(hi) > 0:
        raise ValueError("irr: no sign change in (-0.9999, 10)")
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv_at(lo) * npv_at(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return _approx((lo + hi) / 2)


def bond_price(face, coupon_rate, years, ytm, freq=1):
    """债券价格：面值 + 票息，按年或按频次折现。"""
    n = int(_f(freq))
    periods = int(_f(years)) * n
    c = _f(face) * _f(coupon_rate) / n
    y = _f(ytm) / n
    total = Fraction(0)
    for t in range(1, periods + 1):
        total += c / (1 + y) ** t
    total += _f(face) / (1 + y) ** periods
    return total


def bond_duration(face, coupon_rate, years, ytm, freq=1):
    """麦考利久期（年）。"""
    n = int(_f(freq))
    periods = int(_f(years)) * n
    c = _f(face) * _f(coupon_rate) / n
    y = _f(ytm) / n
    price = bond_price(face, coupon_rate, years, ytm, freq)
    weighted = Fraction(0)
    for t in range(1, periods + 1):
        weighted += t * c / (1 + y) ** t
    weighted += periods * _f(face) / (1 + y) ** periods
    return weighted / price / n


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def black_scholes_call(spot, strike, years, rate, vol):
    S, K, T, r, sigma = map(float, (spot, strike, years, rate, vol))
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        raise ValueError("black_scholes: spot/strike/vol must be > 0 and years > 0")
    d1 = (math.log(S / K) + (r + sigma * sigma / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return _approx(S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2))


def black_scholes_put(spot, strike, years, rate, vol):
    S, K, T, r = map(float, (spot, strike, years, rate))
    call = float(black_scholes_call(spot, strike, years, rate, vol).e)
    return _approx(call - S + K * math.exp(-r * T))


def register(reg):
    reg.func("npv", ["rate", "cashflows", "start"], npv, doc="净现值；start=0 首笔 t=0，start=1 首笔第 1 年末")
    reg.func("annuity_pv", ["payment", "rate", "periods"], annuity_pv, doc="年金现值")
    reg.func("discount_factor", ["rate", "n"], discount_factor, doc="折现因子")
    reg.func("irr", ["cashflows"], irr, doc="内部收益率（数值）")
    reg.func("bond_price", ["face", "coupon_rate", "years", "ytm", "freq"], bond_price, doc="债券价格")
    reg.func("bond_duration", ["face", "coupon_rate", "years", "ytm", "freq"], bond_duration, doc="麦考利久期")
    reg.func("black_scholes_call", ["spot", "strike", "years", "rate", "vol"], black_scholes_call, doc="看涨期权")
    reg.func("black_scholes_put", ["spot", "strike", "years", "rate", "vol"], black_scholes_put, doc="看跌期权")
