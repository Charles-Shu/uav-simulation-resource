"""Deterministic 1 km alpine terrain; metres, world +Y is north.

Public API:
    height_and_zones(x, y) -> (surface elevation, uint8 material ids)
    terrain_height(x, y)  -> surface elevation (including frozen lakes)
    bed_height(x, y)      -> lake beds instead of the ice surface
    lake_masks(x, y)     -> tuple of boolean masks, one per LAKES entry
Coordinates can be scalars or broadcast-compatible NumPy arrays. Material ids:
0 snow, 1 exposed rock, 2 thawed mud, 3 winter grass, 4 frozen lake.
The constants below freeze one authored, reproducible realization. None of the
functions depends on the extent/resolution of the arrays passed by a caller.
"""
from __future__ import annotations
import numpy as np

EXTENT_M = 1000.0
WORLD_BOUNDS = (-500.0, 500.0, -500.0, 500.0)
ZONE_NAMES = {0: 'snow', 1: 'rock', 2: 'mud', 3: 'grass', 4: 'ice'}
SNOW, ROCK, MUD, GRASS, ICE = range(5)
LAKES = (
    {'name': 'glacier_lake', 'center': (140.0, -170.0),
     'radii': (100.0, 70.0), 'level': 11.3, 'depth': 5.5, 'phase': 0.6},
    {'name': 'western_pond', 'center': (-260.0, -280.0),
     'radii': (55.0, 40.0), 'level': 12.0, 'depth': 3.4, 'phase': 2.1},
)
# These are fixed classification thresholds, never array-wise percentiles.
ROCK_SCORE_THRESHOLD = 108.0
THAW_SCORE_THRESHOLD = 0.45
MAX_GRASS_ELEVATION = 32.0
MUD_SCORE_THRESHOLD = 0.68
MAX_MUD_ELEVATION = 22.0
SHORE_MUD_WIDTH = 0.065


def _xy(x, y):
    return np.broadcast_arrays(np.asarray(x, dtype=np.float64),
                               np.asarray(y, dtype=np.float64))


def _hash(ix, iy, seed):
    # Exact integer hash: stable across machines and independent of array shape.
    with np.errstate(over="ignore"):
        h = (ix.astype(np.uint64) * np.uint64(374761393)
             + iy.astype(np.uint64) * np.uint64(668265263)
             + np.uint64(seed) * np.uint64(1442695041))
        h = (h ^ (h >> np.uint64(13))) * np.uint64(1274126177)
        h ^= h >> np.uint64(16)
    return (h & np.uint64(0xffffffff)).astype(np.float64) / 2147483647.5 - 1.0


def _ease(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def noise(x, y, scale=100.0, seed=1):
    """Smooth coordinate noise in [-1,1]; scale is lattice spacing in metres."""
    xx = np.asarray(x) / scale + 17.123
    yy = np.asarray(y) / scale - 8.713
    ix, iy = np.floor(xx).astype(np.int64), np.floor(yy).astype(np.int64)
    tx, ty = _ease(xx - ix), _ease(yy - iy)
    n00, n10 = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    n01, n11 = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    return (n00 * (1 - tx) + n10 * tx) * (1 - ty) + (n01 * (1 - tx) + n11 * tx) * ty


def _gauss(x, y, cx, cy, sx, sy, angle=0.0):
    dx, dy = x - cx, y - cy
    a, b = np.cos(angle), np.sin(angle)
    u, v = a * dx + b * dy, -b * dx + a * dy
    return np.exp(-0.5 * ((u / sx) ** 2 + (v / sy) ** 2))


def lake_radius(x, y, lake):
    """Irregular elliptical shoreline coordinate: radius <= 1 is frozen water."""
    cx, cy = lake['center']; rx, ry = lake['radii']; phase = lake['phase']
    u, v = (x - cx) / rx, (y - cy) / ry
    theta = np.arctan2(v, u)
    outline = (1 + 0.085 * np.sin(3 * theta + phase)
                 + 0.045 * np.cos(5 * theta - 0.7 * phase)
                 + 0.022 * np.sin(9 * theta + 1.3))
    return np.hypot(u, v) / outline


def lake_masks(x, y):
    x, y = _xy(x, y)
    return tuple(lake_radius(x, y, lake) <= 1.0 for lake in LAKES)


def _unshaped_terrain(x, y):
    # Broad, asymmetric mountain massifs. Domain warping breaks simple ellipses.
    wx = x + 24.0 * noise(x, y, 175, 13)
    wy = y + 19.0 * noise(x, y, 153, 17)
    nw = _gauss(wx, wy, -295, 325, 122, 151, -0.22)
    ne = _gauss(wx, wy, 215, 350, 130, 153, 0.20)
    east = _gauss(wx, wy, 407, 108, 65, 130, -0.16)
    west = _gauss(wx, wy, -436, 53, 65, 112, 0.20)
    massif = 123 * nw + 118 * ne + 67 * east + 58 * west
    envelope = np.minimum(1.0, massif / 75.0)
    # A wide north/south valley and an oblique tributary stay traversable.
    valley_x = -30 + 38 * noise(x * 0, y, 240, 51)
    corridor = np.exp(-0.5 * ((x - valley_x) / 49.0) ** 2)
    north_weight = _ease(np.clip((y + 80) / 310, 0, 1))
    massif *= 1 - 0.40 * corridor * north_weight
    rolling = (4.2 * noise(x, y, 270, 31)
               + 3.4 * noise(x, y, 120, 32)
               + 0.75 * noise(x, y, 47, 33)
               + 0.17 * noise(x, y, 18, 34))
    # Small ridges become stronger in the mountains, while valleys remain smooth.
    crags = envelope * (18.0 * noise(wx, wy, 90, 41)
                        + 7.0 * noise(wx, wy, 43, 42)
                        + 2.0 * noise(wx, wy, 18, 43)
                        + 0.35 * noise(wx, wy, 8, 44))
    h = 19.0 + 0.008 * y + massif + rolling + crags
    h += 9.0 * _gauss(x, y, -75, -360, 105, 150, -0.5)
    h += 13.0 * _gauss(x, y, 365, -355, 90, 150, 0.3)
    # Glacial depressions are wider than the frozen surfaces, forming natural banks.
    h -= 6.7 * _gauss(x, y, 145, -170, 175, 130, 0.1)
    h -= 6.0 * _gauss(x, y, -260, -280, 108, 90, 0.0)
    return h


def _terrain(x, y, include_beds=False):
    h = _unshaped_terrain(x, y)
    for lake in LAKES:
        r = lake_radius(x, y, lake)
        level = lake['level']
        # A local low bank prevents accidental below-water terrain near the lake.
        bank_target = level + 2.2 + 0.8 * noise(x, y, 90, 71)
        # A wide low terrace also buries the margins of each continuous ice slab.
        bank_weight = 1.0 - _ease(np.clip((r - 2.2) / 0.65, 0, 1))
        raised = h + np.maximum(bank_target - h, 0.0) * bank_weight
        # Zero value and slope at the waterline; outer edge joins the natural land.
        shore_t = _ease(np.clip((r - 1.0) / 0.48, 0, 1))
        land = level + (raised - level) * shore_t
        h = np.where(r < 1.48, land, raised)
        if include_beds:
            # Basin bed rises continuously to the shore. Ice thickness is handled
            # by the scene's ice geometry; this is the underlying mineral bed.
            bowl = level - lake['depth'] * np.maximum(0.0, 1 - r * r) ** 1.35
            h = np.where(r <= 1, bowl, h)
        else:
            h = np.where(r <= 1, level, h)
    return h


def terrain_height(x, y):
    x, y = _xy(x, y)
    return _terrain(x, y, False)


def bed_height(x, y):
    x, y = _xy(x, y)
    return _terrain(x, y, True)


def height_and_zones(x, y):
    x, y = _xy(x, y)
    h = _terrain(x, y, False)
    zones = np.zeros(h.shape, dtype=np.uint8)
    # High exposed outcrops with a weathered, naturally irregular snowline.
    rock_score = (h + 38 * noise(x, y, 100, 81)
                  + 18 * noise(x, y, 38, 82) + 10 * noise(x, y, 16, 83))
    zones[rock_score > ROCK_SCORE_THRESHOLD] = ROCK
    # Thaw occurs in contiguous sheltered low-lying patches, never high peaks.
    thaw = noise(x, y, 155, 91) + 0.22 * noise(x, y, 57, 92)
    zones[(h < MAX_GRASS_ELEVATION) & (thaw > THAW_SCORE_THRESHOLD)] = GRASS
    zones[(h < MAX_MUD_ELEVATION) & (thaw > MUD_SCORE_THRESHOLD)] = MUD
    for lake in LAKES:
        r = lake_radius(x, y, lake)
        # Thin exposed sediment along selected shore sections, not a uniform ring.
        sediment = noise(x, y, 65, 93) > -0.15
        zones[(r > 1) & (r < 1 + SHORE_MUD_WIDTH) & sediment] = MUD
        zones[r <= 1] = ICE
    return h, zones


def sample_statistics(n=257):
    """Return reproducible horizontal coverage and terrain statistics."""
    axis = np.linspace(-500, 500, n)
    xx, yy = np.meshgrid(axis, axis)
    h, z = height_and_zones(xx, yy)
    gy, gx = np.gradient(h, 1000.0 / (n - 1))
    slopes = np.degrees(np.arctan(np.hypot(gx, gy)))
    gentle = (yy < 50) & (z != ICE)
    return {
        'grid': [n, n],
        'height_min_max_m': [float(h.min()), float(h.max())],
        'coverage_percent': {name: float(100 * np.mean(z == zone))
                             for zone, name in ZONE_NAMES.items()},
        'slope_percentiles_deg': {str(p): float(np.percentile(slopes, p))
                                  for p in (25, 50, 75, 90, 95, 99, 100)},
        'south_slope_percentiles_deg': {str(p): float(np.percentile(slopes[gentle], p))
                                        for p in (25, 50, 75, 90, 95, 99)},
        'snow_percent_below_12deg': float(100 * np.mean(slopes[z == SNOW] < 12)),
        'lake_area_m2': {l['name']: float(1e6 * np.mean(mask))
                         for l, mask in zip(LAKES, lake_masks(xx, yy))},
    }


if __name__ == '__main__':
    import json
    print(json.dumps(sample_statistics(), indent=2))
