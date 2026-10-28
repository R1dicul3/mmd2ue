"""Unit tests for the VMD Bezier interpolation (D-M1-6)."""

from __future__ import annotations

from mmd2ue.core.bezier import cubic_bezier, bezier_interpolate


def test_cubic_bezier_endpoints():
    # Endpoints return exactly the control endpoints.
    assert cubic_bezier(0.0, 0.25, 0.75, 1.0, 0.0) == 0.0
    assert cubic_bezier(0.0, 0.25, 0.75, 1.0, 1.0) == 1.0


def test_cubic_bezier_linear_midpoint():
    # Linear control points (p1=p0, p2=p3) give t itself: midpoint = 0.5.
    assert abs(cubic_bezier(0.0, 0.0, 1.0, 1.0, 0.5) - 0.5) < 1e-9


def test_cubic_bezier_known_value():
    # Symmetric ease curve: p0=0, p1=0, p2=1, p3=1 (fast-out). At t=0.5:
    # B(0.5) = 3*(0.25)*(0.5) + 1*(0.125) = 0.375 + 0.125 = 0.5.
    assert abs(cubic_bezier(0.0, 0.0, 1.0, 1.0, 0.5) - 0.5) < 1e-9


def test_bezier_interpolate_returns_pair_in_range():
    x, y = bezier_interpolate(64, 127, 20, 100, 0.5)
    assert 0.0 <= x <= 1.0
    assert 0.0 <= y <= 1.0


def test_bezier_interpolate_identity():
    # With control points x1=x2=127 and y1=y2=127, each normalized to 1.0, the
    # cubic is (0, 1, 1, 1): at t=0.5 it is 0.875 for both axes. This is a
    # known analytical value validating the 0..127 fixed-point normalization.
    x, y = bezier_interpolate(127, 127, 127, 127, 0.5)
    assert abs(x - 0.875) < 0.001
    assert abs(y - 0.875) < 0.001
