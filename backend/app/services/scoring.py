"""
DTW-based scoring service.

Pipeline:
  1. Downsample both paths (Douglas-Peucker) if too long
  2. Convert [[lat, lng], ...] → local metres for fair distance comparison
  3. Run fastdtw to get raw DTW distance (metres)
  4. Normalise against blueprint length → 0-100 score
  5. Apply bonuses/penalties: completion rate, max deviation

Score formula
─────────────
  base_score      = max(0, 100 - (avg_deviation_m / PERFECT_DEVIATION_M) * 100)
  completion_bonus = 0 if completion_rate >= 0.95 else -(1 - completion_rate) * 30
  max_dev_penalty  = 0 if max_deviation_m < MAX_DEV_THRESHOLD else capped penalty

  final = clamp(base + completion_bonus - max_dev_penalty, 0, 100)
"""
import math
from typing import List, Tuple

import numpy as np
from fastdtw import fastdtw

# ── tuneable constants ──────────────────────────────────────────────────────
PERFECT_DEVIATION_M = 10.0       # avg deviation this small → near-100 score
MAX_DEV_THRESHOLD_M = 200.0      # deviations beyond this get penalised harder
MAX_POINTS_DTW = 500             # downsample target for DTW
LAT_M = 111_320.0                # metres per degree latitude


# ── helpers ─────────────────────────────────────────────────────────────────

def _lng_m(lat_deg: float) -> float:
    return LAT_M * math.cos(math.radians(lat_deg))


def _to_metres(coords: List[List[float]]) -> np.ndarray:
    """Convert [[lat, lng], ...] to local (x, y) metres. Reference = first point."""
    if not coords:
        return np.empty((0, 2))
    ref_lat, ref_lng = coords[0]
    cos_factor = _lng_m(ref_lat)
    return np.array([
        [(lng - ref_lng) * cos_factor, (lat - ref_lat) * LAT_M]
        for lat, lng in coords
    ])


def _path_length_m(pts: np.ndarray) -> float:
    if len(pts) < 2:
        return 0.0
    diffs = np.diff(pts, axis=0)
    return float(np.sum(np.hypot(diffs[:, 0], diffs[:, 1])))


# ── Douglas-Peucker downsampling ─────────────────────────────────────────────

def _douglas_peucker(pts: np.ndarray, epsilon: float) -> List[int]:
    """Return indices of points to keep.
    Uses fully vectorised perpendicular-distance computation — no Python loop."""
    if len(pts) <= 2:
        return list(range(len(pts)))

    start, end = pts[0], pts[-1]
    line_vec = end - start
    line_len_sq = float(np.dot(line_vec, line_vec))

    if line_len_sq == 0:
        return [0, len(pts) - 1]

    # Vectorised: compute perpendicular distances for all interior points at once
    vecs = pts[1:-1] - start                                       # (n-2, 2)
    proj = np.clip(vecs @ line_vec / line_len_sq, 0, 1)           # (n-2,)
    closest = start + proj[:, np.newaxis] * line_vec              # (n-2, 2)
    distances = np.linalg.norm(pts[1:-1] - closest, axis=1)      # (n-2,)

    max_idx_interior = int(np.argmax(distances))
    max_dist = float(distances[max_idx_interior])
    max_idx = max_idx_interior + 1  # shift back to full array index

    if max_dist > epsilon:
        left = _douglas_peucker(pts[:max_idx + 1], epsilon)
        right = _douglas_peucker(pts[max_idx:], epsilon)
        return left[:-1] + [max_idx + r for r in right]
    return [0, len(pts) - 1]


def downsample(coords: List[List[float]], max_points: int = MAX_POINTS_DTW) -> List[List[float]]:
    """Reduce coordinate list to at most max_points using Douglas-Peucker."""
    if len(coords) <= max_points:
        return coords
    pts = _to_metres(coords)
    # adaptive epsilon: increase until we're under budget
    epsilon = 1.0
    while True:
        indices = _douglas_peucker(pts, epsilon)
        if len(indices) <= max_points:
            break
        epsilon *= 2
    return [coords[i] for i in indices]


# ── main scoring function ─────────────────────────────────────────────────────

def compute_score(
    blueprint_coords: List[List[float]],
    actual_coords: List[List[float]],
) -> dict:
    """
    Compare actual GPS path against blueprint and return score details.

    Returns
    -------
    {
        score: float,            # 0–100
        dtw_distance: float,     # raw DTW distance in metres
        details: {
            completion_rate: float,
            avg_deviation_m: float,
            max_deviation_m: float,
            segment_scores: list[float],
            blueprint_length_m: float,
            actual_length_m: float,
        }
    }
    """
    if not blueprint_coords or not actual_coords:
        return _zero_score("empty coordinates")

    # Single-point paths can't form a meaningful DTW comparison
    if len(blueprint_coords) < 2 or len(actual_coords) < 2:
        return _zero_score("path must have at least 2 points")

    # 1. Downsample
    bp_ds = downsample(blueprint_coords)
    ac_ds = downsample(actual_coords)

    # 2. Convert to metres (shared reference = blueprint[0])
    ref_lat, ref_lng = blueprint_coords[0]
    cos_f = _lng_m(ref_lat)

    def to_m(coords):
        return np.array([
            [(lng - ref_lng) * cos_f, (lat - ref_lat) * LAT_M]
            for lat, lng in coords
        ])

    bp_m = to_m(bp_ds)
    ac_m = to_m(ac_ds)

    bp_length = _path_length_m(bp_m)
    ac_length = _path_length_m(ac_m)

    # 3. DTW
    dtw_dist, path = fastdtw(bp_m, ac_m, dist=_euclidean)
    dtw_dist = float(dtw_dist)

    # 4. Per-point deviations along the warping path
    deviations = [float(np.linalg.norm(bp_m[i] - ac_m[j])) for i, j in path]
    avg_dev = float(np.mean(deviations)) if deviations else 0.0
    max_dev = float(np.max(deviations)) if deviations else 0.0

    # 5. Completion rate: fraction of blueprint covered by actual path
    completion_rate = min(1.0, ac_length / bp_length) if bp_length > 0 else 0.0

    # 6. Segment scores (split into 5 equal segments)
    n = len(deviations)
    seg_size = max(1, n // 5)
    segment_scores = []
    for i in range(0, n, seg_size):
        seg = deviations[i:i + seg_size]
        seg_avg = float(np.mean(seg))
        segment_scores.append(round(max(0.0, 100 - (seg_avg / PERFECT_DEVIATION_M) * 100), 1))

    # 7. Score calculation
    base = max(0.0, 100.0 - (avg_dev / PERFECT_DEVIATION_M) * 100.0)

    completion_penalty = 0.0
    if completion_rate < 0.95:
        completion_penalty = (1.0 - completion_rate) * 30.0

    max_dev_penalty = 0.0
    if max_dev > MAX_DEV_THRESHOLD_M:
        max_dev_penalty = min(20.0, (max_dev - MAX_DEV_THRESHOLD_M) / 100.0 * 5.0)

    final_score = max(0.0, min(100.0, base - completion_penalty - max_dev_penalty))

    return {
        "score": round(final_score, 2),
        "dtw_distance": round(dtw_dist, 2),
        "details": {
            "completion_rate": round(completion_rate, 4),
            "avg_deviation_m": round(avg_dev, 2),
            "max_deviation_m": round(max_dev, 2),
            "segment_scores": segment_scores,
            "blueprint_length_m": round(bp_length, 2),
            "actual_length_m": round(ac_length, 2),
        },
    }


def _euclidean(a, b) -> float:
    return float(np.linalg.norm(np.array(a) - np.array(b)))


def _zero_score(reason: str = "") -> dict:
    return {
        "score": 0.0,
        "dtw_distance": 0.0,
        "details": {
            "completion_rate": 0.0,
            "avg_deviation_m": 0.0,
            "max_deviation_m": 0.0,
            "segment_scores": [],
            "blueprint_length_m": 0.0,
            "actual_length_m": 0.0,
        },
    }
