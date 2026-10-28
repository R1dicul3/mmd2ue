"""VMD Bezier interpolation (M1, D-M1-6).

VMD stores, per axis (x/y), four 32-bit signed fixed-point control points that
specify a cubic Bezier curve used to interpolate between keyframes. This module
implements the pure evaluation: given the two inner control points and a time
parameter t in [0,1], return the interpolated coordinate.

The MMD convention uses the two X control points (value/axis) and two Y control
points (time) to map normalized frame time to a normalized curve parameter. For
M1 we implement the raw cubic Bezier evaluator plus the standard MMD
""bezier_to_tangent"" helper semantics described in the manual §6; the full
tangent/velocity application belongs to M3 (IK/motion baking).

Constraints C2/C3: standard library only.
"""

from __future__ import annotations


def cubic_bezier(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    """Evaluate a cubic Bezier curve at parameter t.

    p0..p3 are the four control values (p0 and p3 are the endpoints). Returns
    the interpolated value at t in [0, 1].
    """
    u = 1.0 - t
    return (
        u * u * u * p0
        + 3.0 * u * u * t * p1
        + 3.0 * u * t * t * p2
        + t * t * t * p3
    )


def bezier_interpolate(x1: float, x2: float, y1: float, y2: float, t: float) -> tuple:
    """Map normalized frame-time t through the MMD x/y Bezier control grid.

    MMD stores four control values: (x1, x2) on the horizontal (input) axis and
    (y1, y2) on the vertical (output) axis, both in signed fixed-point (0..127).
    This returns the normalized (x, y) position of the curve at the given
    normalized input t (also 0..1), mirroring the manual's ""bezier_to_tangent""
    input transform: input t is first mapped through the X Bezier to select the
    curve position, then the Y Bezier yields the output.

    Both X and Y use the fixed control points (0, x1, x2, 1) and (0, y1, y2, 1).
    """
    # Normalize control points from the 0..127 signed fixed-point domain.
    nx1 = x1 / 127.0
    nx2 = x2 / 127.0
    ny1 = y1 / 127.0
    ny2 = y2 / 127.0
    # X maps input time to curve parameter (with fixed 0 / 1 endpoints).
    x = cubic_bezier(0.0, nx1, nx2, 1.0, t)
    y = cubic_bezier(0.0, ny1, ny2, 1.0, t)
    return (x, y)


__all__ = ["cubic_bezier", "bezier_interpolate"]
