"""currency 能力包：货币换算（静态汇率表 + 可被 AI 更新的 JSON 文件）。

AI 可以联网查最新汇率后写入 .calc/currency.json（每 1 USD 等于多少该货币），
本包每次调用都会重新读取，无需重启。
"""

NAME = "currency"
VERSION = "0.1.0"
DESCRIPTION = "currency_convert / currency_rate"
REQUIRES = []

import json
import os
from fractions import Fraction
from pathlib import Path

import calc_core as _core

# 每 1 USD 兑换多少该货币（内置参考值，可被 .calc/currency.json 覆盖）
_DEFAULTS = {
    "USD": 1,
    "CNY": 7.2,
    "EUR": 0.92,
    "JPY": 150,
    "GBP": 0.79,
    "HKD": 7.8,
    "KRW": 1350,
    "AUD": 1.5,
    "CAD": 1.36,
    "SGD": 1.34,
    "CHF": 0.88,
    "TWD": 32,
    "INR": 83,
    "RUB": 92,
    "BRL": 5.0,
}


def _home():
    return Path(os.environ.get("CALC_HOME", Path.cwd() / ".calc"))


def _rates():
    rates = dict(_DEFAULTS)
    try:
        data = json.loads((_home() / "currency.json").read_text(encoding="utf-8"))
        if isinstance(data, dict):
            source = data.get("rates") if isinstance(data.get("rates"), dict) else data
            for code, value in source.items():
                try:
                    rates[str(code).upper()] = Fraction(str(value))
                except Exception:
                    continue
    except Exception:
        pass
    for code in list(rates):
        try:
            rates[code] = Fraction(str(rates[code]))
        except Exception:
            rates.pop(code, None)
    return rates


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def currency_rate(code):
    """返回 1 USD 等于多少该货币。"""
    rates = _rates()
    key = str(code).strip().upper()
    if key not in rates:
        raise ValueError("currency_rate: unknown currency %r; update .calc/currency.json" % key)
    return _core._wrap(rates[key])


def currency_convert(value, from_unit, to_unit):
    rates = _rates()
    source = str(from_unit).strip().upper()
    target = str(to_unit).strip().upper()
    for code in (source, target):
        if code not in rates:
            raise ValueError("currency_convert: unknown currency %r; update .calc/currency.json" % code)
    amount = _f(value)
    usd = amount / rates[source]
    return _core._wrap(usd * rates[target])


def register(reg):
    reg.func("currency_convert", ["value", "from_unit", "to_unit"], currency_convert, doc="货币换算")
    reg.func("currency_rate", ["code"], currency_rate, doc="1 USD 兑多少该货币")
