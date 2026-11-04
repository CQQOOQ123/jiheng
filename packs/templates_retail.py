"""templates_retail：零售/渠道口径模板。"""

NAME = "templates_retail"
VERSION = "0.1.0"
DESCRIPTION = "折上折 / 返点 / 客单价 / 售罄率"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def 折上折(标价, 折扣1, 折扣2):
    """折上折 = 标价 × (1-折扣1) × (1-折扣2)。"""
    return _wrap(_f(标价) * (1 - _f(折扣1)) * (1 - _f(折扣2)))


def 返点(销售额, 比例):
    return _wrap(_f(销售额) * _f(比例))


def 客单价(销售额, 客数):
    if _f(客数) == 0:
        raise ValueError("客单价: 客数不能为 0")
    return _wrap(_f(销售额) / _f(客数))


def 售罄率(销量, 进货量):
    if _f(进货量) == 0:
        raise ValueError("售罄率: 进货量不能为 0")
    return _wrap(_f(销量) / _f(进货量))


def register(reg):
    reg.func("折上折", ["标价", "折扣1", "折扣2"], 折上折, doc="两次折扣")
    reg.func("返点", ["销售额", "比例"], 返点, doc="销售额×比例")
    reg.func("客单价", ["销售额", "客数"], 客单价, doc="销售额/客数")
    reg.func("售罄率", ["销量", "进货量"], 售罄率, doc="销量/进货量")
