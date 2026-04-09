"""
Performance tests for the scoring pipeline.
Target: 5000-point path scored in < 2 seconds.
"""
import time
import pytest
from app.services.scoring import compute_score


def make_path(n: int, start_lat=37.5, start_lng=127.0, step=0.00001):
    """Generate a long straight path with n points."""
    return [[start_lat + i * step, start_lng + i * step] for i in range(n)]


def test_scoring_5000_points_under_2s():
    blueprint = make_path(5000)
    actual = make_path(5000, start_lat=37.5, start_lng=127.0, step=0.000011)  # slight offset

    start = time.perf_counter()
    result = compute_score(blueprint, actual)
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, f"Scoring took {elapsed:.2f}s — exceeds 2s budget"
    assert 0 <= result["score"] <= 100
    print(f"\n5000-point scoring: {elapsed:.3f}s | score={result['score']}")


def test_scoring_1000_points_under_1s():
    blueprint = make_path(1000)
    actual = make_path(1000, step=0.000011)

    start = time.perf_counter()
    result = compute_score(blueprint, actual)
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Scoring took {elapsed:.2f}s — exceeds 1s budget"
    print(f"\n1000-point scoring: {elapsed:.3f}s | score={result['score']}")


def test_downsampling_reduces_to_budget():
    from app.services.scoring import downsample, MAX_POINTS_DTW
    long_path = make_path(5000)
    ds = downsample(long_path)
    assert len(ds) <= MAX_POINTS_DTW
