"""Unit tests for the stencil coordinate transform service."""
import math
import pytest
from app.services.stencil import transform_coordinates, compute_bounds, compute_center


# A simple 3-point "L-shape" path: origin + east + north
BLUEPRINT = [
    [37.5000, 127.0000],  # origin
    [37.5000, 127.0010],  # ~88 m east
    [37.5010, 127.0010],  # ~111 m north from previous
]

TARGET = (37.5500, 127.1000)


def approx(a: float, b: float, tol: float = 1e-5) -> bool:
    return abs(a - b) < tol


# ── Test 1: translation only ─────────────────────────────────────────────────
def test_translation_only():
    """First point must land exactly at target; relative shape is preserved."""
    result = transform_coordinates(BLUEPRINT, *TARGET, rotation_angle=0.0, scale=1.0)

    assert len(result) == 3

    # First point == target
    assert approx(result[0][0], TARGET[0]), f"lat mismatch: {result[0][0]} vs {TARGET[0]}"
    assert approx(result[0][1], TARGET[1]), f"lng mismatch: {result[0][1]} vs {TARGET[1]}"

    # Relative offset from point 0 to point 1 should be preserved (east only)
    assert approx(result[1][0], result[0][0], tol=1e-4)   # same latitude
    assert result[1][1] > result[0][1]                     # east of origin


# ── Test 2: rotation + translation ───────────────────────────────────────────
def test_rotation_90():
    """90° clockwise rotation: east becomes south in local space."""
    result = transform_coordinates(BLUEPRINT, *TARGET, rotation_angle=90.0, scale=1.0)

    # First point still at target
    assert approx(result[0][0], TARGET[0])
    assert approx(result[0][1], TARGET[1])

    # Point[1] was due-east; after 90° CW rotation it should be due-south
    # i.e. same longitude as origin, latitude below
    assert result[1][0] < result[0][0]                     # south
    assert approx(result[1][1], result[0][1], tol=1e-4)   # same longitude


# ── Test 3: full transform (scale + rotation + translation) ──────────────────
def test_full_transform():
    """Scale=2 doubles all distances from the first point."""
    result_1x = transform_coordinates(BLUEPRINT, *TARGET, rotation_angle=45.0, scale=1.0)
    result_2x = transform_coordinates(BLUEPRINT, *TARGET, rotation_angle=45.0, scale=2.0)

    # Both still start at target
    assert approx(result_1x[0][0], TARGET[0])
    assert approx(result_2x[0][0], TARGET[0])

    # Distance from origin to point[1] should be ~2x
    def dist(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    d1 = dist(result_1x[0], result_1x[1])
    d2 = dist(result_2x[0], result_2x[1])

    assert approx(d2, d1 * 2, tol=1e-6), f"Expected 2x distance, got {d2:.8f} vs {d1 * 2:.8f}"


# ── Test 4: empty input ───────────────────────────────────────────────────────
def test_empty_input():
    assert transform_coordinates([], *TARGET) == []


# ── Test 5: bounds / center helpers ──────────────────────────────────────────
def test_bounds_and_center():
    coords = [[37.0, 127.0], [38.0, 128.0]]
    b = compute_bounds(coords)
    assert b["min_lat"] == 37.0
    assert b["max_lat"] == 38.0
    c = compute_center(coords)
    assert approx(c["lat"], 37.5)
    assert approx(c["lng"], 127.5)
