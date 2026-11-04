"""templates_hr：人力/薪酬口径模板。"""

NAME = "templates_hr"
VERSION = "0.1.0"
DESCRIPTION = "加班费 / 补偿N+1 / 个税 / 社保基数"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def 加班费(时薪, 倍数, 小时):
    """加班费 = 时薪 × 倍数 × 小时。"""
    return _wrap(_f(时薪) * _f(倍数) * _f(小时))


def 补偿N加1(月薪, 年限):
    """离职补偿 = 月薪 × (年限 + 1)。"""
    return _wrap(_f(月薪) * (_f(年限) + 1))


def 个税(应纳税所得额):
    """工资薪金月度个税（简化七级超额累进）。"""
    taxable = _f(应纳税所得额)
    if taxable <= 0:
        return Fraction(0)
    brackets = [
        (Fraction(3000), Fraction(3, 100), Fraction(0)),
        (Fraction(12000), Fraction(10, 100), Fraction(210)),
        (Fraction(25000), Fraction(20, 100), Fraction(1410)),
        (Fraction(35000), Fraction(25, 100), Fraction(2660)),
        (Fraction(55000), Fraction(30, 100), Fraction(4410)),
        (Fraction(80000), Fraction(35, 100), Fraction(7160)),
        (None, Fraction(45, 100), Fraction(15160)),
    ]
    for limit, rate, deduction in brackets:
        if limit is None or taxable <= limit:
            return _wrap(taxable * rate - deduction)


def 社保基数(月薪, 下限, 上限):
    """社保缴费基数：月薪夹在上下限之间。"""
    salary = _f(月薪)
    low, high = _f(下限), _f(上限)
    if high < low:
        raise ValueError("社保基数: 上限不能小于下限")
    return _wrap(min(max(salary, low), high))


def register(reg):
    reg.func("加班费", ["时薪", "倍数", "小时"], 加班费, doc="时薪×倍数×小时")
    reg.func("补偿N加1", ["月薪", "年限"], 补偿N加1, doc="月薪×(年限+1)")
    reg.func("个税", ["应纳税所得额"], 个税, doc="月度个税")
    reg.func("社保基数", ["月薪", "下限", "上限"], 社保基数, doc="夹在上下限")
