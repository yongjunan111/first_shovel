"""Unit tests for the DTW scoring service."""
import math
import pytest
from app.services.scoring import compute_score, downsample


# ── fixtures ─────────────────────────────────────────────────────────────────

def make_straight_path(start_lat, start_lng, n=50, step_lng=0.0001):
    """Generate a straight east-going path with n points."""
    return [[start_lat, start_lng + i * step_lng] for i in range(n)]


BLUEPRINT = make_straight_path(37.5000, 127.0000)


# ── Test 1: identical path → score near 100 ───────────────────────────────────
def test_same_path_scores_100():
    result = compute_score(BLUEPRINT, BLUEPRINT)
    assert result["score"] >= 95.0, f"Same path score too low: {result['score']}"
    assert result["details"]["avg_deviation_m"] < 0.01


# ── Test 2: completely different path → low score ────────────────────────────
def test_different_path_scores_low():
    # Path 500 m north of blueprint
    offset_path = [[lat + 0.005, lng] for lat, lng in BLUEPRINT]
    result = compute_score(BLUEPRINT, offset_path)
    assert result["score"] < 30.0, f"Different path score too high: {result['score']}"


# ── Test 3: slight deviation → score 80–95 ───────────────────────────────────
def test_slight_deviation_scores_mid():
    # ~2 m north offset (≈ 0.000018 degrees lat) → expect score 70–100
    slight_offset = [[lat + 0.000018, lng] for lat, lng in BLUEPRINT]
    result = compute_score(BLUEPRINT, slight_offset)
    assert 70.0 <= result["score"] <= 100.0, f"Slight deviation score out of range: {result['score']}"


# ── Test 4: empty coordinates → score 0 ──────────────────────────────────────
def test_empty_blueprint():
    result = compute_score([], BLUEPRINT)
    assert result["score"] == 0.0


def test_empty_actual():
    result = compute_score(BLUEPRINT, [])
    assert result["score"] == 0.0


# ── Test 5: completion rate penalised for short actual path ──────────────────
def test_incomplete_ride_penalty():
    half = BLUEPRINT[:len(BLUEPRINT) // 2]
    result_full = compute_score(BLUEPRINT, BLUEPRINT)
    result_half = compute_score(BLUEPRINT, half)
    assert result_half["score"] < result_full["score"]
    assert result_half["details"]["completion_rate"] < 0.6


# ── Test 6: downsampler reduces point count ───────────────────────────────────
def test_downsample():
    long_path = make_straight_path(37.5, 127.0, n=1000)
    ds = downsample(long_path, max_points=100)
    assert len(ds) <= 100
    # First and last points preserved
    assert ds[0] == long_path[0]
    assert ds[-1] == long_path[-1]


# ── Test 7: details structure is complete ────────────────────────────────────
def test_result_structure():
    result = compute_score(BLUEPRINT, BLUEPRINT)
    assert "score" in result
    assert "dtw_distance" in result
    details = result["details"]
    for key in ("completion_rate", "avg_deviation_m", "max_deviation_m",
                "segment_scores", "blueprint_length_m", "actual_length_m"):
        assert key in details, f"Missing key: {key}"
