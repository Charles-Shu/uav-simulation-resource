"""Authored 1 km mountain watershed: all coordinates and elevations in metres.

The terrain is solid land / lake bed, and water is a separate horizontal visual
with a fluid plugin. No function ever replaces a lake bed with solid water.
Material IDs: 0 exposed rock, 1 grass, 2 wet mud, 3 sand, 4 water-covered bed.
All samplers are deterministic and accept scalars or broadcastable arrays.
"""
from __future__ import annotations
import numpy as np

EXTENT_M = 1000.0
WORLD_BOUNDS = (-500.0, 500.0, -500.0, 500.0)
ROCK, GRASS, MUD, SAND, WATER = range(5)
ZONE_NAMES = {ROCK: 'rock', GRASS: 'grass', MUD: 'mud', SAND: 'sand', WATER: 'water'}
LAKES = (
    dict(name='eastern_lake', center=(140.0, -130.0), radii=(130.0, 85.0),
         level=22.0, depth=12.0, phase=0.6),
    dict(name='western_lake', center=(-270.0, -250.0), radii=(80.0, 55.0),
         level=26.0, depth=8.0, phase=2.1),
)


def _xy(x, y):
    return np.broadcast_arrays(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))


def _ease(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _hash(ix, iy, seed):
    with np.errstate(over='ignore'):
        h = (ix.astype(np.uint64) * np.uint64(374761393)
             + iy.astype(np.uint64) * np.uint64(668265263)
             + np.uint64(seed) * np.uint64(1442695041))
        h = (h ^ (h >> np.uint64(13))) * np.uint64(1274126177)
        h ^= h >> np.uint64(16)
    return (h & np.uint64(0xffffffff)).astype(np.float64) / 2147483647.5 - 1.0


def noise(x, y, scale=100.0, seed=1):
    """Smooth lattice noise in [-1,1], independent of caller array size."""
    x, y = _xy(x, y)
    xx, yy = x / scale + 17.123, y / scale - 8.713
    ix, iy = np.floor(xx).astype(np.int64), np.floor(yy).astype(np.int64)
    tx, ty = _ease(xx - ix), _ease(yy - iy)
    return ((_hash(ix, iy, seed) * (1-tx) + _hash(ix+1, iy, seed) * tx) * (1-ty)
            + (_hash(ix, iy+1, seed) * (1-tx) + _hash(ix+1, iy+1, seed) * tx) * ty)


def _gauss(x, y, cx, cy, sx, sy, angle=0):
    dx, dy = x-cx, y-cy
    u, v = np.cos(angle)*dx + np.sin(angle)*dy, -np.sin(angle)*dx + np.cos(angle)*dy
    return np.exp(-0.5*((u/sx)**2 + (v/sy)**2))


def lake_radius(x, y, lake):
    """Normalized irregular shoreline coordinate; <=1 is liquid-water area."""
    x, y = _xy(x, y)
    cx, cy = lake['center']; rx, ry = lake['radii']; phase = lake['phase']
    u, v = (x-cx)/rx, (y-cy)/ry
    theta = np.arctan2(v, u)
    outline = (1 + .085*np.sin(3*theta+phase) + .045*np.cos(5*theta-.7*phase)
               + .022*np.sin(9*theta+1.3))
    return np.hypot(u, v)/outline


def lake_masks(x, y):
    return tuple(lake_radius(x, y, lake) <= 1.0 for lake in LAKES)


def _unshaped_terrain(x, y):
    wx = x + 25*noise(x, y, 170, 113)
    wy = y + 20*noise(x, y, 153, 117)
    # Long bent ridgelines and asymmetric spurs, rather than isolated round hills.
    west_axis = -252 + .22*(wy-200) + 36*np.sin(wy/115)
    east_axis = 246 - .18*(wy-250) + 31*np.sin(wy/123 + .7)
    north_window = np.exp(-.5*((wy-290)/235)**4)
    west = 158*np.exp(-.5*(np.abs(wx-west_axis)/93)**1.65)*north_window
    east = 164*np.exp(-.5*(np.abs(wx-east_axis)/103)**1.7)*north_window
    west *= .83 + .17*np.cos((wy-290)/69)
    east *= .85 + .15*np.cos((wy-355)/75)
    # Oblique buttresses make branched drainages and accessible saddles.
    spurs = (52*_gauss(wx, wy, -400, 70, 58, 190, -.42)
             + 48*_gauss(wx, wy, 405, 15, 63, 205, .34)
             + 32*_gauss(wx, wy, -138, 75, 46, 145, -.62))
    massif = west + east + spurs
    strength = np.clip(massif/90, 0, 1)
    crags = strength*(17*noise(wx, wy, 83, 141) + 6*noise(wx, wy, 39, 142)
                     + 1.4*noise(wx, wy, 17, 143) + .22*noise(wx, wy, 7, 144))
    foothills = (22*_gauss(x, y, -60, -335, 150, 150, -.35)
                 + 26*_gauss(x, y, 375, -355, 112, 190, .2)
                 + 13*_gauss(x, y, -440, -430, 100, 150, 0))
    h = (35 + .012*y + massif + foothills + crags
         + 5.5*noise(x, y, 205, 131) + 3.2*noise(x, y, 91, 132)
         + .55*noise(x, y, 31, 133))
    # A continuous lower central valley separates the two chains.
    valley_x = -25 + 24*np.sin(y/180)
    valley = np.exp(-.5*((x-valley_x)/43)**2)
    h -= 12*valley*_ease(np.clip((y+150)/330, 0, 1))
    return h


def terrain_height(x, y):
    """True solid ground, with submerged bowl-shaped mineral lake beds."""
    x, y = _xy(x, y)
    h = _unshaped_terrain(x, y)
    for lake in LAKES:
        r = lake_radius(x, y, lake)
        level = lake['level']
        # Land joins the shoreline continuously. A broad terrace prevents peaks
        # piercing the water or isolated submerged pockets outside the basin.
        bank = level + 3.0 + .8*noise(x, y, 83, 171)
        weight = 1-_ease(np.clip((r-1.65)/.6, 0, 1))
        raised = h + np.maximum(bank-h, 0)*weight
        shore = _ease(np.clip((r-1.0)/.65, 0, 1))
        h = np.where(r<1.65, level+(raised-level)*shore, raised)
        bowl = level-lake['depth']*np.maximum(0, 1-r*r)**1.4
        h = np.where(r<=1, bowl, h)
    return h


bed_height = terrain_height


def surface_height(x, y):
    """Visible upper surface: includes perfectly horizontal lake water."""
    x, y = _xy(x, y)
    h = terrain_height(x, y)
    for lake, mask in zip(LAKES, lake_masks(x, y)):
        h = np.where(mask, lake['level'], h)
    return h


def height_and_zones(x, y):
    """Return solid-bed elevation and uint8 surface material ID."""
    x, y = _xy(x, y)
    h = terrain_height(x, y)
    zone = np.full(h.shape, GRASS, dtype=np.uint8)
    exposure = h + 18*noise(x, y, 110, 181) + 7*noise(x, y, 37, 182)
    zone[exposure > 74] = ROCK
    # Damp sheltered depressions form contiguous mud patches in lower valleys.
    wet = noise(x, y, 142, 191) + .18*noise(x, y, 49, 192)
    zone[(h<73) & (wet>.65)] = MUD
    # A sinuous alluvial strip links the southern floodplain to the main basin.
    bar_axis = -285 + 25*np.sin((x+50)/83) + 12*noise(x, y*0, 135, 199)
    bar = (np.abs(y-bar_axis)<12+5*noise(x,y,70,198)) & (x>-110) & (x<340) & (h<60)
    zone[bar] = SAND
    for lake in LAKES:
        r = lake_radius(x, y, lake)
        sandy_bank = noise(x, y, 95, 193) > -.12
        zone[(r>1) & (r<1.60) & sandy_bank] = SAND
        zone[(r>1) & (r<1.42) & ~sandy_bank] = MUD
        zone[r<=1] = WATER
    return h, zone


def slope_degrees(x, y, step=2.0):
    """Local physical ground slope from symmetric metre-spaced samples."""
    dx = (terrain_height(np.asarray(x)+step,y)-terrain_height(np.asarray(x)-step,y))/(2*step)
    dy = (terrain_height(x,np.asarray(y)+step)-terrain_height(x,np.asarray(y)-step))/(2*step)
    return np.degrees(np.arctan(np.hypot(dx,dy)))


def sample_statistics(n=501):
    axis = np.linspace(-500, 500, n)
    xx, yy = np.meshgrid(axis, axis)
    h,z = height_and_zones(xx,yy)
    slope = slope_degrees(xx,yy)
    plantable = (z==GRASS) & (slope>=5) & (slope<=25)
    south = (yy<0) & (z!=WATER)
    return dict(grid=[n,n], height_min_max_m=[float(h.min()),float(h.max())],
        coverage_percent={name:float(100*np.mean(z==i)) for i,name in ZONE_NAMES.items()},
        slope_percentiles_deg={str(p):float(np.percentile(slope[z!=WATER],p)) for p in (25,50,75,90,95,99)},
        south_slope_percentiles_deg={str(p):float(np.percentile(slope[south],p)) for p in (25,50,75,90,95)},
        plantable_grass_5_to_25deg_samples=int(plantable.sum()),
        plantable_grass_5_to_25deg_area_m2=float(1e6*np.mean(plantable)),
        grass_below_25deg_percent=float(100*np.mean(slope[z==GRASS]<=25)),
        lake_area_m2={l['name']:float(1e6*np.mean(m)) for l,m in zip(LAKES,lake_masks(xx,yy))})


if __name__ == '__main__':
    import json
    print(json.dumps(sample_statistics(),indent=2))
