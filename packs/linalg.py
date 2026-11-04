"""linalg 能力包：小矩阵行列式、逆、特征值、线性方程组、转置、乘法。"""

NAME = "linalg"
VERSION = "0.1.0"
DESCRIPTION = "det / inv / eigenvals / solve_linear / transpose / matmul"
REQUIRES = []

import sympy as sp

import calc_core as _core


def _wrap(v):
    return _core._wrap(v)


def _matrix(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected a matrix as [[a, b], [c, d]]")
    if not isinstance(rows[0], list):
        rows = [[item] for item in rows]  # column vector
    if len(rows) > 12 or len(rows[0]) > 12:
        raise ValueError("matrix too large (max 12x12)")
    return sp.Matrix(rows)


def _to_rows(matrix):
    return [[_wrap(item) for item in row] for row in matrix.tolist()]


def det(rows):
    return _wrap(_matrix(rows).det())


def inv(rows):
    m = _matrix(rows)
    if m.det() == 0:
        raise ValueError("inv: matrix is singular")
    return _to_rows(m.inv())


def eigenvals(rows):
    return [_wrap(value) for value in _matrix(rows).eigenvals().keys()]


def solve_linear(a, b):
    ma, mb = _matrix(a), _matrix(b)
    return _to_rows(ma.LUsolve(mb))


def transpose(rows):
    return _to_rows(_matrix(rows).T)


def matmul(a, b):
    return _to_rows(_matrix(a) * _matrix(b))


def register(reg):
    reg.func("det", ["rows"], det, doc="行列式")
    reg.func("inv", ["rows"], inv, doc="逆矩阵")
    reg.func("eigenvals", ["rows"], eigenvals, doc="特征值")
    reg.func("solve_linear", ["a", "b"], solve_linear, doc="解线性方程组")
    reg.func("transpose", ["rows"], transpose, doc="转置")
    reg.func("matmul", ["a", "b"], matmul, doc="矩阵乘法")
