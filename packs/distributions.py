"""distributions 能力包：常见分布的 pdf / cdf / 分位数。"""

NAME = "distributions"
VERSION = "0.1.0"
DESCRIPTION = "norm_pdf / norm_cdf / norm_quantile / t_pdf / chi2_pdf"
REQUIRES = []

import math
from fractions import Fraction

import sympy as sp

import calc_core as _core


def _f(v):
    if isinstance(v, sp.Basic):  # 支持 steps 里传下来的符号中间量
        return v
    inner = getattr(v, "e", None)  # calc_core.Sym 包装
    if inner is not None:
        return inner
    return v if isinstance(v, Fraction) else Fraction(v)


def _wrap(v):
    return _core._wrap(v)


def norm_pdf(x, mu=0, sigma=1):
    mu, sigma = _f(mu), _f(sigma)
    if sigma <= 0:
        raise ValueError("norm_pdf: sigma must be > 0")
    z = (_f(x) - mu) / sigma
    return _wrap(sp.exp(-z * z / 2) / (sigma * sp.sqrt(2 * sp.pi)))


def norm_cdf(x, mu=0, sigma=1):
    mu, sigma = _f(mu), _f(sigma)
    if sigma <= 0:
        raise ValueError("norm_cdf: sigma must be > 0")
    z = (_f(x) - mu) / sigma
    return _wrap((1 + sp.erf(z / sp.sqrt(2))) / 2)


def norm_quantile(p):
    p = _f(p)
    if not (0 < p < 1):
        raise ValueError("norm_quantile: p must be between 0 and 1")
    return _wrap(sp.sqrt(2) * sp.erfinv(2 * p - 1))


def t_pdf(x, df):
    df = _f(df)
    if df <= 0:
        raise ValueError("t_pdf: df must be > 0")
    x = _f(x)
    return _wrap(sp.gamma((df + 1) / 2) / (sp.sqrt(df * sp.pi) * sp.gamma(df / 2))
                 * (1 + x * x / df) ** (-(df + 1) / 2))


def chi2_pdf(x, k):
    k = _f(k)
    if k <= 0:
        raise ValueError("chi2_pdf: k must be > 0")
    x = _f(x)
    if x < 0:
        raise ValueError("chi2_pdf: x must be >= 0")
    return _wrap(x ** (k / 2 - 1) * sp.exp(-x / 2) / (2 ** (k / 2) * sp.gamma(k / 2)))


def register(reg):
    reg.func("norm_pdf", ["x", "mu", "sigma"], norm_pdf, doc="正态密度")
    reg.func("norm_cdf", ["x", "mu", "sigma"], norm_cdf, doc="正态累积分布")
    reg.func("norm_quantile", ["p"], norm_quantile, doc="正态分位数")
    reg.func("t_pdf", ["x", "df"], t_pdf, doc="t 分布密度")
    reg.func("chi2_pdf", ["x", "k"], chi2_pdf, doc="卡方分布密度")
