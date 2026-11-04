"""templates 能力包：常用业务口径（报价/税/折扣/毛利/摊销）。"""

NAME = "templates"
VERSION = "0.1.0"
DESCRIPTION = "报价 / 含税 / 去税 / 折扣价 / 到手价 / 毛利 / 毛利率 / 加成率 / 剩余本金 / 损耗后"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def 报价(cost, margin):
    """报价 = 成本 / (1 - 毛利率)。"""
    m = _f(margin)
    if m >= 1:
        raise ValueError("报价: 毛利率必须 < 1")
    return _wrap(_f(cost) / (1 - m))


def 含税(price, rate):
    """含税价 = 不含税价 × (1 + 税率)。"""
    return _wrap(_f(price) * (1 + _f(rate)))


def 去税(price, rate):
    """不含税价 = 含税价 / (1 + 税率)。"""
    denom = 1 + _f(rate)
    if denom == 0:
        raise ValueError("去税: 税率不能为 -1（分母为 0）")
    return _wrap(_f(price) / denom)


def 折扣价(price, discount):
    """折后价 = 标价 × (1 - 折扣率)。"""
    return _wrap(_f(price) * (1 - _f(discount)))


def 到手价(price, discount, tax):
    """到手价 = 标价 × (1 - 折扣率) × (1 + 税率)。"""
    return _wrap(_f(price) * (1 - _f(discount)) * (1 + _f(tax)))


def 毛利(price, cost):
    """毛利 = 售价 - 成本。"""
    return _wrap(_f(price) - _f(cost))


def 毛利率(price, cost):
    """毛利率 = (售价 - 成本) / 售价。"""
    p = _f(price)
    if p == 0:
        raise ValueError("毛利率: 售价不能为 0")
    return _wrap((p - _f(cost)) / p)


def 加成率(price, cost):
    """加成率 = (售价 - 成本) / 成本。"""
    c = _f(cost)
    if c == 0:
        raise ValueError("加成率: 成本不能为 0")
    return _wrap((_f(price) - c) / c)


def 损耗后(quantity, loss):
    """损耗后数量 = 数量 × (1 - 损耗率)。"""
    return _wrap(_f(quantity) * (1 - _f(loss)))


def _pmt(principal, annual, years):
    r = _f(annual) / 12
    n = _core.int_arg(_f(years) * 12, "years * 12")
    if r == 0:
        return _f(principal) / n
    factor = (1 + r) ** n
    return _f(principal) * r * factor / (factor - 1)


def 剩余本金(principal, annual, years, paid_periods):
    """等额本息第 k 期后的剩余本金。"""
    p = _f(principal)
    r = _f(annual) / 12
    n = _core.int_arg(_f(years) * 12, "years * 12")
    k = _core.int_arg(paid_periods, "paid_periods")
    if k < 0 or k > n:
        raise ValueError("剩余本金: 期数必须在 0 到总期数之间")
    payment = _pmt(principal, annual, years)
    if r == 0:
        return _wrap(p - payment * k)
    factor = (1 + r) ** k
    return _wrap(p * factor - payment * (factor - 1) / r)


def register(reg):
    reg.func("报价", ["cost", "margin"], 报价, doc="成本/(1-毛利率)")
    reg.func("含税", ["price", "rate"], 含税, doc="不含税价×(1+税率)")
    reg.func("去税", ["price", "rate"], 去税, doc="含税价/(1+税率)")
    reg.func("折扣价", ["price", "discount"], 折扣价, doc="标价×(1-折扣率)")
    reg.func("到手价", ["price", "discount", "tax"], 到手价, doc="折后含税价")
    reg.func("毛利", ["price", "cost"], 毛利, doc="售价-成本")
    reg.func("毛利率", ["price", "cost"], 毛利率, doc="(售价-成本)/售价")
    reg.func("加成率", ["price", "cost"], 加成率, doc="(售价-成本)/成本")
    reg.func("损耗后", ["quantity", "loss"], 损耗后, doc="数量×(1-损耗率)")
    reg.func("剩余本金", ["principal", "annual", "years", "paid_periods"], 剩余本金, doc="等额本息剩余本金")
