"""templates_manufacturing：制造/生产口径模板。"""

NAME = "templates_manufacturing"
VERSION = "0.1.0"
DESCRIPTION = "良率 / OEE / 材料成本 / 工时成本"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def 良率(良品数, 总数):
    if _f(总数) == 0:
        raise ValueError("良率: 总数不能为 0")
    return _wrap(_f(良品数) / _f(总数))


def OEE(可用率, 性能率, 良率值):
    """设备综合效率 = 可用率 × 性能率 × 良率。"""
    return _wrap(_f(可用率) * _f(性能率) * _f(良率值))


def 材料成本(单耗, 产量, 单价, 损耗率):
    """材料成本 = 单耗 × 产量 × 单价 × (1 + 损耗率)。"""
    return _wrap(_f(单耗) * _f(产量) * _f(单价) * (1 + _f(损耗率)))


def 工时成本(标准工时, 数量, 时薪):
    return _wrap(_f(标准工时) * _f(数量) * _f(时薪))


def register(reg):
    reg.func("良率", ["良品数", "总数"], 良率, doc="良品/总数")
    reg.func("OEE", ["可用率", "性能率", "良率值"], OEE, doc="三率相乘")
    reg.func("材料成本", ["单耗", "产量", "单价", "损耗率"], 材料成本, doc="含损耗")
    reg.func("工时成本", ["标准工时", "数量", "时薪"], 工时成本, doc="工时×数量×时薪")
