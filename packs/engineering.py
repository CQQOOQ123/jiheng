"""engineering 能力包：常用工程公式（应力/梁/传热）。"""

NAME = "engineering"
VERSION = "0.1.0"
DESCRIPTION = "stress / strain / beam_deflection / bending_stress / heat_flux / thermal_resistance"
REQUIRES = []

from fractions import Fraction

import calc_core as _core


def _f(v):
    return v if isinstance(v, Fraction) else Fraction(str(getattr(v, "e", v)))


def _wrap(v):
    return _core._wrap(v)


def stress(force, area):
    """正应力 σ = F / A（Pa）。"""
    if _f(area) == 0:
        raise ValueError("stress: area must not be zero")
    return _wrap(_f(force) / _f(area))


def strain(deformation, length):
    """应变 ε = ΔL / L。"""
    if _f(length) == 0:
        raise ValueError("strain: length must not be zero")
    return _wrap(_f(deformation) / _f(length))


def youngs_modulus(stress_value, strain_value):
    """杨氏模量 E = σ / ε。"""
    if _f(strain_value) == 0:
        raise ValueError("youngs_modulus: strain must not be zero")
    return _wrap(_f(stress_value) / _f(strain_value))


def bending_stress(moment, distance, inertia):
    """弯曲应力 σ = M·c / I。"""
    if _f(inertia) == 0:
        raise ValueError("bending_stress: inertia must not be zero")
    return _wrap(_f(moment) * _f(distance) / _f(inertia))


def beam_cantilever_point(load, length, modulus, inertia):
    """悬臂梁端部集中载荷最大挠度 δ = P·L³ / (3·E·I)。"""
    if _f(modulus) == 0 or _f(inertia) == 0:
        raise ValueError("beam_cantilever_point: E and I must be non-zero")
    return _wrap(_f(load) * _f(length) ** 3 / (3 * _f(modulus) * _f(inertia)))


def beam_simply_supported_point(load, length, modulus, inertia):
    """简支梁跨中集中载荷最大挠度 δ = P·L³ / (48·E·I)。"""
    if _f(modulus) == 0 or _f(inertia) == 0:
        raise ValueError("beam_simply_supported_point: E and I must be non-zero")
    return _wrap(_f(load) * _f(length) ** 3 / (48 * _f(modulus) * _f(inertia)))


def heat_flux(conductivity, delta_t, thickness):
    """一维稳态热流密度 q = k·ΔT / d（W/m²）。"""
    if _f(thickness) == 0:
        raise ValueError("heat_flux: thickness must not be zero")
    return _wrap(_f(conductivity) * _f(delta_t) / _f(thickness))


def thermal_resistance(thickness, conductivity, area):
    """热阻 R = d / (k·A)（K/W）。"""
    if _f(conductivity) == 0 or _f(area) == 0:
        raise ValueError("thermal_resistance: k and area must be non-zero")
    return _wrap(_f(thickness) / (_f(conductivity) * _f(area)))


def thermal_expansion(length, alpha, delta_t):
    """热膨胀 ΔL = L·α·ΔT。"""
    return _wrap(_f(length) * _f(alpha) * _f(delta_t))


def register(reg):
    reg.func("stress", ["force", "area"], stress, doc="正应力 F/A")
    reg.func("strain", ["deformation", "length"], strain, doc="应变 ΔL/L")
    reg.func("youngs_modulus", ["stress", "strain"], youngs_modulus, doc="杨氏模量")
    reg.func("bending_stress", ["moment", "distance", "inertia"], bending_stress, doc="弯曲应力 M·c/I")
    reg.func("beam_cantilever_point", ["load", "length", "modulus", "inertia"], beam_cantilever_point, doc="悬臂梁端部载荷挠度")
    reg.func("beam_simply_supported_point", ["load", "length", "modulus", "inertia"], beam_simply_supported_point, doc="简支梁跨中载荷挠度")
    reg.func("heat_flux", ["conductivity", "delta_t", "thickness"], heat_flux, doc="热流密度")
    reg.func("thermal_resistance", ["thickness", "conductivity", "area"], thermal_resistance, doc="热阻")
    reg.func("thermal_expansion", ["length", "alpha", "delta_t"], thermal_expansion, doc="热膨胀")
