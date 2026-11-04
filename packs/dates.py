"""dates 能力包：日期差、日期加减、星期。"""

NAME = "dates"
VERSION = "0.1.0"
DESCRIPTION = "days_between / date_add / weekday"
REQUIRES = []

from datetime import date, timedelta
from fractions import Fraction

import calc_core as _core


def _text(value):
    return str(getattr(value, "string", value))


def _parse(value):
    text = _text(value).strip()
    try:
        year, month, day = [int(part) for part in text.split("-")]
    except Exception:
        raise ValueError(
            "invalid date %r: expected YYYY-MM-DD, e.g. 2026-04-10; "
            "weekday() takes a date, and weekday numbers are 0..6 (Mon..Sun)" % text)
    if month < 1 or month > 12:
        raise ValueError("invalid date %r: month must be 1..12" % text)
    try:
        return date(year, month, day)
    except ValueError:
        import calendar
        last = calendar.monthrange(year, month)[1]
        raise ValueError(
            "invalid date %r: %04d-%02d has %d days (day %d does not exist). "
            "Do not roll over to the next month." % (text, year, month, last, day))


def days_between(start, end):
    """两个日期之间的天数（end - start，可为负）。"""
    return Fraction((_parse(end) - _parse(start)).days)


def date_add(start, days):
    """日期加减天数，返回 YYYY-MM-DD。"""
    amount = int(getattr(days, "e", days))
    return (_parse(start) + timedelta(days=amount)).isoformat()


def weekday(start):
    """星期几：0=周一 … 6=周日。"""
    return Fraction(_parse(start).weekday())


def register(reg):
    reg.func("days_between", ["start", "end"], days_between, doc="日期差（天）")
    reg.func("date_add", ["start", "days"], date_add, doc="日期加减")
    reg.func("weekday", ["start"], weekday, doc="星期（0=周一）")
