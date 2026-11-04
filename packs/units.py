"""units 能力包：函数式单位运算 + 中缀解析（7 个 SI 基本量纲）。

量纲顺序：(L 长度, M 质量, T 时间, I 电流, K 温度, N 物质的量, J 发光强度)
"""

NAME = "units"
VERSION = "0.2.0"
DESCRIPTION = "unit_convert / unit_mul / unit_div / unit_add / unit_pow / unit_eval / temp_convert"
REQUIRES = []

import re
from fractions import Fraction

import calc_core as _core

_ZERO = (0,) * 7
_LABELS = ("m", "kg", "s", "A", "K", "mol", "cd")


def _d(dims):
    return tuple(dims) + (0,) * (7 - len(dims))


# 单位 -> (换算到基准的因子, (L, M, T, I, K, N, J))
_UNITS = {
    # 长度（基准 m）
    "m": (Fraction(1), _d((1, 0, 0))),
    "km": (Fraction(1000), _d((1, 0, 0))),
    "cm": (Fraction(1, 100), _d((1, 0, 0))),
    "mm": (Fraction(1, 1000), _d((1, 0, 0))),
    "ft": (Fraction(3048, 10000), _d((1, 0, 0))),
    "inch": (Fraction(254, 10000), _d((1, 0, 0))),
    "mile": (Fraction(1609344, 1000), _d((1, 0, 0))),
    "yd": (Fraction(9144, 10000), _d((1, 0, 0))),
    # 质量（基准 kg）
    "kg": (Fraction(1), _d((0, 1, 0))),
    "g": (Fraction(1, 1000), _d((0, 1, 0))),
    "t": (Fraction(1000), _d((0, 1, 0))),
    "lb": (Fraction(45359237, 100000000), _d((0, 1, 0))),
    "oz": (Fraction(28349523125, 1000000000000), _d((0, 1, 0))),
    "ton": (Fraction(90718474, 100000), _d((0, 1, 0))),
    # 时间（基准 s）
    "s": (Fraction(1), _d((0, 0, 1))),
    "min": (Fraction(60), _d((0, 0, 1))),
    "h": (Fraction(3600), _d((0, 0, 1))),
    "day": (Fraction(86400), _d((0, 0, 1))),
    "week": (Fraction(604800), _d((0, 0, 1))),
    "year": (Fraction(31536000), _d((0, 0, 1))),
    # 电流 / 温度 / 物质的量 / 发光强度
    "A": (Fraction(1), _d((0, 0, 0, 1))),
    "mA": (Fraction(1, 1000), _d((0, 0, 0, 1))),
    "K": (Fraction(1), _d((0, 0, 0, 0, 1))),
    "mol": (Fraction(1), _d((0, 0, 0, 0, 0, 1))),
    "cd": (Fraction(1), _d((0, 0, 0, 0, 0, 0, 1))),
    # 速度
    "m/s": (Fraction(1), _d((1, 0, -1))),
    "km/h": (Fraction(1000, 3600), _d((1, 0, -1))),
    "mph": (Fraction(44704, 100000), _d((1, 0, -1))),
    "knot": (Fraction(1852, 3600), _d((1, 0, -1))),
    # 面积
    "m^2": (Fraction(1), _d((2, 0, 0))),
    "km^2": (Fraction(1000000), _d((2, 0, 0))),
    "cm^2": (Fraction(1, 10000), _d((2, 0, 0))),
    "acre": (Fraction(40468564224, 10000000), _d((2, 0, 0))),
    "ha": (Fraction(10000), _d((2, 0, 0))),
    "ft^2": (Fraction(9290304, 100000000), _d((2, 0, 0))),
    # 体积
    "L": (Fraction(1, 1000), _d((3, 0, 0))),
    "mL": (Fraction(1, 1000000), _d((3, 0, 0))),
    "m^3": (Fraction(1), _d((3, 0, 0))),
    "gal": (Fraction(3785411784, 1000000000000), _d((3, 0, 0))),
    "ft^3": (Fraction(28316846592, 1000000000000), _d((3, 0, 0))),
    # 能量 / 压力 / 功率
    "J": (Fraction(1), _d((2, 1, -2))),
    "kJ": (Fraction(1000), _d((2, 1, -2))),
    "cal": (Fraction(4184, 1000), _d((2, 1, -2))),
    "kcal": (Fraction(4184), _d((2, 1, -2))),
    "kWh": (Fraction(3600000), _d((2, 1, -2))),
    "eV": (Fraction(1602176634, 10 ** 28), _d((2, 1, -2))),
    "Pa": (Fraction(1), _d((-1, 1, -2))),
    "kPa": (Fraction(1000), _d((-1, 1, -2))),
    "bar": (Fraction(100000), _d((-1, 1, -2))),
    "atm": (Fraction(101325), _d((-1, 1, -2))),
    "psi": (Fraction(6894757293168, 1000000000), _d((-1, 1, -2))),
    "W": (Fraction(1), _d((2, 1, -3))),
    "kW": (Fraction(1000), _d((2, 1, -3))),
    "hp": (Fraction(745699871582, 1000000000), _d((2, 1, -3))),
    # 电磁
    "C": (Fraction(1), _d((0, 0, 1, 1))),
    "V": (Fraction(1), _d((2, 1, -3, -1))),
    "ohm": (Fraction(1), _d((2, 1, -3, -2))),
    "F": (Fraction(1), _d((-2, -1, 4, 2))),
    "Wb": (Fraction(1), _d((2, 1, -2, -1))),
    "H": (Fraction(1), _d((2, 1, -2, -2))),
    "T": (Fraction(1), _d((0, 1, -2, -1))),
    "Hz": (Fraction(1), _d((0, 0, -1))),
    "N": (Fraction(1), _d((1, 1, -2))),
}

_DERIVED = {
    _d((1, 0, -1)): "m/s",
    _d((0, 0, -1)): "Hz",
    _d((1, 1, -2)): "N",
    _d((2, 1, -2)): "J",
    _d((2, 1, -3)): "W",
    _d((-1, 1, -2)): "Pa",
    _d((2, 0, 0)): "m^2",
    _d((3, 0, 0)): "m^3",
    _d((0, 0, 1, 1)): "C",
    _d((2, 1, -3, -1)): "V",
    _d((2, 1, -3, -2)): "ohm",
    _d((-2, -1, 4, 2)): "F",
    _d((2, 1, -2, -1)): "Wb",
    _d((2, 1, -2, -2)): "H",
    _d((0, 1, -2, -1)): "T",
}


def _parse(unit):
    text = str(unit).replace(" ", "").replace("**", "^")
    if text in _UNITS:
        factor, dims = _UNITS[text]
        return Fraction(factor), tuple(dims)
    parts = re.split(r"([*/])", text)
    factor = Fraction(1)
    dims = [0] * 7
    sign = 1
    for token in parts:
        if token == "*":
            sign = 1
            continue
        if token == "/":
            sign = -1
            continue
        if not token:
            continue
        exponent = 1
        if "^" in token:
            base, power = token.split("^")
            token, exponent = base, int(power)
        if token not in _UNITS:
            raise ValueError("units: unknown unit %r" % token)
        unit_factor, unit_dims = _UNITS[token]
        factor *= Fraction(unit_factor) ** (sign * exponent)
        for index in range(7):
            dims[index] += sign * exponent * unit_dims[index]
    return factor, tuple(dims)


def _name(dims):
    if dims in _DERIVED:
        return _DERIVED[dims]
    numerator, denominator = [], []
    for label, power in zip(_LABELS, dims):
        if power > 0:
            numerator.append(label if power == 1 else "%s^%d" % (label, power))
        elif power < 0:
            magnitude = -power
            denominator.append(label if magnitude == 1 else "%s^%d" % (label, magnitude))
    top = "*".join(numerator) or "1"
    return top if not denominator else top + "/" + "*".join(denominator)


def _wrap(v):
    return _core._wrap(v)


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def unit_convert(value, from_unit, to_unit):
    from_factor, from_dims = _parse(from_unit)
    to_factor, to_dims = _parse(to_unit)
    if from_dims != to_dims:
        raise ValueError("unit_convert: dimension mismatch %s vs %s (%s vs %s)"
                         % (from_unit, to_unit, _name(from_dims), _name(to_dims)))
    return _wrap(_f(value) * from_factor / to_factor)


def unit_mul(v1, u1, v2, u2):
    f1, d1 = _parse(u1)
    f2, d2 = _parse(u2)
    dims = tuple(a + b for a, b in zip(d1, d2))
    return [_wrap(_f(v1) * _f(v2) * f1 * f2), _name(dims)]


def unit_div(v1, u1, v2, u2):
    f1, d1 = _parse(u1)
    f2, d2 = _parse(u2)
    if _f(v2) == 0:
        raise ValueError("unit_div: division by zero")
    dims = tuple(a - b for a, b in zip(d1, d2))
    return [_wrap(_f(v1) / _f(v2) * f1 / f2), _name(dims)]


def unit_add(v1, u1, v2, u2):
    if _parse(u1)[1] != _parse(u2)[1]:
        raise ValueError("unit_add: dimension mismatch %s vs %s" % (u1, u2))
    return [_wrap(_f(v1) + unit_convert(v2, u2, u1)), str(u1)]


def unit_pow(value, unit, exponent):
    f, d = _parse(unit)
    n = int(_f(exponent))
    dims = tuple(power * n for power in d)
    return [_wrap(_f(value) ** n * f ** n), _name(dims)]


def temp_convert(value, from_unit, to_unit):
    source = str(from_unit).strip().upper()
    target = str(to_unit).strip().upper()
    raw = _f(value)
    if source == target:
        return raw
    if source == "C":
        celsius = raw
    elif source == "F":
        celsius = (raw - 32) * Fraction(5, 9)
    elif source == "K":
        celsius = raw - Fraction(5463, 20)
    else:
        raise ValueError("temp_convert: unit must be C, F or K")
    if target == "C":
        return celsius
    if target == "F":
        return celsius * Fraction(9, 5) + 32
    if target == "K":
        return celsius + Fraction(5463, 20)
    raise ValueError("temp_convert: unit must be C, F or K")


_TOKEN = re.compile(r"\s*([0-9]+(?:\.[0-9]+)?|[A-Za-z]+|[()+*/^-])")


def _tokens(text):
    out, position = [], 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if not match:
            raise ValueError("unit_eval: unexpected character at %d" % position)
        out.append(match.group(1))
        position = match.end()
    return out


def unit_eval(text):
    """解析中缀单位表达式，如 "10 m / 5 s"、"1 V / 1 ohm"。"""
    tokens = _tokens(str(text).replace("**", "^"))
    index = 0

    def peek():
        return tokens[index] if index < len(tokens) else None

    def take():
        nonlocal index
        token = tokens[index]
        index += 1
        return token

    def primary():
        token = peek()
        if token == "(":
            take()
            value, dims = expression()
            if peek() != ")":
                raise ValueError("unit_eval: missing )")
            take()
            return value, dims
        if token == "-":
            take()
            base, dims = primary()
            return -base, dims
        number = Fraction(1)
        if token is not None and token[0].isdigit():
            number = Fraction(take())
        unit_name = None
        if peek() is not None and peek()[0].isalpha():
            unit_name = take()
        if unit_name is None:
            return number, _ZERO
        factor, dims = _parse(unit_name)
        return number * factor, dims

    def power():
        base, dims = primary()
        if peek() == "^":
            take()
            exponent = int(take())
            return base ** exponent, tuple(item * exponent for item in dims)
        return base, dims

    def term():
        left, dims = power()
        while peek() in ("*", "/"):
            op = take()
            right, right_dims = power()
            if op == "*":
                left, dims = left * right, tuple(a + b for a, b in zip(dims, right_dims))
            else:
                if right == 0:
                    raise ValueError("unit_eval: division by zero")
                left, dims = left / right, tuple(a - b for a, b in zip(dims, right_dims))
        return left, dims

    def expression():
        left, dims = term()
        while peek() in ("+", "-"):
            op = take()
            right, right_dims = term()
            if dims != right_dims:
                raise ValueError("unit_eval: dimension mismatch (%s vs %s)"
                                 % (_name(dims), _name(right_dims)))
            left = left + right if op == "+" else left - right
        return left, dims

    value, dims = expression()
    if index != len(tokens):
        raise ValueError("unit_eval: unexpected token %r" % tokens[index])
    return [_wrap(value), _name(dims)]


def register(reg):
    reg.func("unit_convert", ["value", "from_unit", "to_unit"], unit_convert, doc="单位换算（支持复合单位）")
    reg.func("unit_mul", ["v1", "u1", "v2", "u2"], unit_mul, doc="带单位相乘")
    reg.func("unit_div", ["v1", "u1", "v2", "u2"], unit_div, doc="带单位相除")
    reg.func("unit_add", ["v1", "u1", "v2", "u2"], unit_add, doc="带单位相加")
    reg.func("unit_pow", ["value", "unit", "exponent"], unit_pow, doc="带单位乘方")
    reg.func("unit_eval", ["text"], unit_eval, doc='中缀单位表达式，如 "10 m / 5 s"')
    reg.func("temp_convert", ["value", "from_unit", "to_unit"], temp_convert, doc="温度换算 C/F/K")
