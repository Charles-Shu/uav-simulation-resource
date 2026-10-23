# City terrain texture sources

All maps below are original **Poly Haven CC0** assets, without watermarks.
[Official license](https://polyhaven.com/license). Original files remain unmodified.

Every JPG was checked against the **MD5 and byte count returned by the official API**; dimensions are 1024 × 1024. `sources.json` also records local SHA-256 hashes and direct download URLs. API responses are preserved alongside the files.

| Asset | Use | Source |
|---|---|---|
| grass_ground | Lawns / slopes | [Grass Ground](https://polyhaven.com/a/grass_ground) |
| leafy_grass | Natural grassy areas | [Leafy Grass](https://polyhaven.com/a/leafy_grass) |
| rock_boulder_dry | Mountain rock | [Rock Boulder Dry](https://polyhaven.com/a/rock_boulder_dry) |
| aerial_rocks_04 | Mountain rock | [Aerial Rocks 04](https://polyhaven.com/a/aerial_rocks_04) |
| brown_mud | Riverbank mud | [Brown Mud](https://polyhaven.com/a/brown_mud) |
| sand_01 | Riverbank sand | [Sand 01](https://polyhaven.com/a/sand_01) |
| clean_asphalt | Asphalt roads | [Clean Asphalt](https://polyhaven.com/a/clean_asphalt) |
| concrete_pavement_02 | Sidewalk slabs | [Concrete Pavement 02](https://polyhaven.com/a/concrete_pavement_02) |
| rough_concrete | Concrete structures | [Rough Concrete](https://polyhaven.com/a/rough_concrete) |

Available for every asset: `{asset}_diff_1k.jpg`, `{asset}_nor_gl_1k.jpg`, `{asset}_rough_1k.jpg`.

The first six assets are byte-for-byte copies of the previous mountain scene sources, revalidated against the current official API. The final three were downloaded for this city scene.

Diffuse maps use sRGB; normal and roughness maps are data and should use Non-Color in Blender. Do not derive friction or soil stiffness from texture roughness: physical parameters are configured separately in Gazebo.
