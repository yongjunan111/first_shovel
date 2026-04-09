"""
Stencil (coordinate transform) service.

Applies Affine Transform to blueprint coordinates:
  1. Translate: align blueprint origin to target_lat/lng
  2. Rotate: rotate around target by rotation_angle (degrees, clockwise)
  3. Scale: zoom in/out around target

All math is done in a local metric space (meters) to avoid distortion
from working directly in lat/lng degrees.
"""
import math
from typing import List, Tuple


# Earth approximation constants
LAT_M = 111_320.0  # meters per degree latitude (fixed)


def _lng_m(lat_deg: float) -> float:
    """Meters per degree longitude at a given latitude."""
    return LAT_M * math.cos(math.radians(lat_deg))


def _to_local(coords: List[List[float]], ref_lat: float, ref_lng: float) -> List[Tuple[float, float]]:
    """Convert [[lat, lng], ...] to local (x, y) in meters relative to ref point."""
    cos_factor = _lng_m(ref_lat)
    return [
        ((lng - ref_lng) * cos_factor, (lat - ref_lat) * LAT_M)
        for lat, lng in coords
    ]


def _to_latlng(
    local: List[Tuple[float, float]],
    target_lat: float,
    target_lng: float,
) -> List[List[float]]:
    """Convert local (x, y) meters back to [[lat, lng], ...] anchored at target."""
    cos_factor = _lng_m(target_lat)
    return [
        [target_lat + y / LAT_M, target_lng + x / cos_factor]
        for x, y in local
    ]


def transform_coordinates(
    coordinates: List[List[float]],
    target_lat: float,
    target_lng: float,
    rotation_angle: float = 0.0,
    scale: float = 1.0,
) -> List[List[float]]:
    """
    Apply affine transform (translate + rotate + scale) to a list of coordinates.

    Parameters
    ----------
    coordinates : [[lat, lng], ...]  — original blueprint path
    target_lat, target_lng          — where the first point should land
    rotation_angle                  — clockwise degrees
    scale                           — multiplier (1.0 = no change)

    Returns
    -------
    [[lat, lng], ...]  — transformed coordinates
    """
    if not coordinates:
        return []

    ref_lat, ref_lng = coordinates[0]

    # 1. Convert to local metric space (origin = blueprint[0])
    local = _to_local(coordinates, ref_lat, ref_lng)

    # 2. Apply scale + rotation around origin (blueprint[0])
    angle_rad = math.radians(rotation_angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Clockwise rotation: negate the standard CCW formula's sin terms
    transformed = [
        (
            scale * (x * cos_a + y * sin_a),
            scale * (-x * sin_a + y * cos_a),
        )
        for x, y in local
    ]

    # 3. Convert back — origin (0,0) maps to target_lat/lng
    return _to_latlng(transformed, target_lat, target_lng)


def compute_bounds(coords: List[List[float]]) -> dict:
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return {
        "min_lat": min(lats),
        "max_lat": max(lats),
        "min_lng": min(lngs),
        "max_lng": max(lngs),
    }


def compute_center(coords: List[List[float]]) -> dict:
    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    return {
        "lat": (min(lats) + max(lats)) / 2,
        "lng": (min(lngs) + max(lngs)) / 2,
    }
