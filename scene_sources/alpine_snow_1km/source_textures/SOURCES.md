# Terrain texture provenance

Downloaded from official Poly Haven texture URLs on 2026-10-21.
All texture maps are CC0-1.0. Official license: https://polyhaven.com/license
License deed: https://creativecommons.org/publicdomain/zero/1.0/

No preview thumbnails, logos, or watermarked renders are used. Each map is 1024 x 1024.
Diffuse maps contain color; normal and roughness maps are optional shading inputs. They do not create physical friction or deformable snow.

| Asset | Author | Original scale | Use |
|---|---|---|---|
| [snow_02](https://polyhaven.com/a/snow_02) | Rob Tuytel | 2.0 m | Recommended snow; original cool grey diffuse retains texture detail. Avoid pure-white multiplication and overbright ambient. |
| [aerial_rocks_04](https://polyhaven.com/a/aerial_rocks_04) | Rob Tuytel | 80.0 m | Alternate broad rocky ground; includes moss. Best at exposed transitional slopes, not clean high summit rock. |
| [aerial_grass_rock](https://polyhaven.com/a/aerial_grass_rock) | Rob Tuytel | 15.0 m | Recommended lowland sparse grass/moss and gravel; desaturate moderately for dormant alpine winter vegetation. |
| [brown_mud_leaves_01](https://polyhaven.com/a/brown_mud_leaves_01) | Rob Tuytel | 1.3 m | Optional only; leaf litter may be unsuitable without nearby trees. |
| [brown_mud](https://polyhaven.com/a/brown_mud) | Rob Tuytel | 1.3 m | Recommended lowland brown soil; use low diffuse brightness and moderate gloss if depicting damp exposed unfrozen mud. |
| [rock_boulder_dry](https://polyhaven.com/a/rock_boulder_dry) | Dimitrios Savva (photography); Rico Cilliers (processing) | 1.8 m | Recommended bare rock; weathered pale grey-beige surface. Scale as a rock material, not one tile across the entire mountain. |
| [grass_path_2](https://polyhaven.com/a/grass_path_2) | Rob Tuytel | 1.0 m | Optional grass/soil close-view detail. |

Recommended primary maps: `snow_02`, `rock_boulder_dry`, `aerial_grass_rock`, `brown_mud`.
Filename pattern: `<asset>_diff_1k.jpg`, `<asset>_nor_gl_1k.jpg`, `<asset>_rough_1k.jpg`.

Ice: Generate an original procedural ice material: low-saturation cyan/blue, broad low-frequency cloudiness, sparse branching white cracks, subtle roughness and frosted shoreline. Keep lake top horizontal and relatively smooth; avoid mesh waves or bowl-shaped ice surface. Ice is a rigid low-friction region; cracks here are visual unless separately modeled.

Machine-readable provenance, exact download URLs, file sizes, dimensions and SHA-256 values are in `sources.json`.
