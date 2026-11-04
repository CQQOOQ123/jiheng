"""templates_logistics：物流/运费口径模板。"""

NAME = "templates_logistics"
VERSION = "0.1.0"
DESCRIPTION = "体积重 / 计费重 / 运费"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def 体积重(长_cm, 宽_cm, 高_cm, 系数):
    """体积重（kg）= 长×宽×高 / 系数（常见 6000）。"""
    divisor = _f(系数)
    if divisor == 0:
        raise ValueError("体积重: 系数不能为 0")
    return _wrap(_f(长_cm) * _f(宽_cm) * _f(高_cm) / divisor)


def 计费重(实重, 体积重值):
    """计费重 = max(实重, 体积重)。"""
    return _wrap(max(_f(实重), _f(体积重值)))


def 运费(计费重值, 首重价, 首重kg, 续重价):
    """运费 = 首重价 + max(0, 计费重 - 首重kg) × 续重价（按 kg 向上取整由调用方处理）。"""
    weight = _f(计费重值)
    first = _f(首重kg)
    if weight <= first:
        return _wrap(_f(首重价))
    return _wrap(_f(首重价) + (weight - first) * _f(续重价))


def register(reg):
    reg.func("体积重", ["长_cm", "宽_cm", "高_cm", "系数"], 体积重, doc="长×宽×高/系数")
    reg.func("计费重", ["实重", "体积重值"], 计费重, doc="max(实重,体积重)")
    reg.func("运费", ["计费重值", "首重价", "首重kg", "续重价"], 运费, doc="首重+续重")
