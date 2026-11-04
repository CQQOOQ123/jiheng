"""percent 能力包：办公常用百分比公式。"""

NAME = "percent"
VERSION = "0.1.0"
DESCRIPTION = "pct_part / yoy / tax_included / tax_excluded / discount_price / growth_multiple"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def pct_part(part, whole):
    """占比：part / whole。"""
    if _f(whole) == 0:
        raise ValueError("pct_part: whole must not be zero")
    return _wrap(_f(part) / _f(whole))


def yoy(current, previous):
    """同比/环比增长率：(current - previous) / previous。"""
    if _f(previous) == 0:
        raise ValueError("yoy: previous must not be zero")
    return _wrap((_f(current) - _f(previous)) / _f(previous))


def tax_included(amount, rate):
    """含税价：amount × (1 + rate)。"""
    return _wrap(_f(amount) * (1 + _f(rate)))


def tax_excluded(amount, rate):
    """去税价：amount / (1 + rate)。"""
    return _wrap(_f(amount) / (1 + _f(rate)))


def discount_price(price, discount):
    """折后价：price × (1 − discount)。"""
    return _wrap(_f(price) * (1 - _f(discount)))


def growth_multiple(current, previous):
    """增长倍数：current / previous。"""
    if _f(previous) == 0:
        raise ValueError("growth_multiple: previous must not be zero")
    return _wrap(_f(current) / _f(previous))


def register(reg):
    reg.func("pct_part", ["part", "whole"], pct_part, doc="占比")
    reg.func("yoy", ["current", "previous"], yoy, doc="同比/环比增长率")
    reg.func("tax_included", ["amount", "rate"], tax_included, doc="含税价")
    reg.func("tax_excluded", ["amount", "rate"], tax_excluded, doc="去税价")
    reg.func("discount_price", ["price", "discount"], discount_price, doc="折后价")
    reg.func("growth_multiple", ["current", "previous"], growth_multiple, doc="增长倍数")
