# mountain_lakes_1km editable sources

`blender/mountain_lakes_1km.blend` is a compressed, editable import of the published Gazebo visuals, with textures packed inside. Recreate it with:

```bash
blender --background --python tools/export_blender.py -- --scene mountain_lakes_1km --no-render
```

Run from the repository root. Blender 4.5 LTS was used. The Blender file is for visual editing; `.world` and model SDF files remain authoritative for collision and physics. Editing the blend does not automatically update those files.

`terrain_data.npz` and the field Python file preserve terrain data/functions; source textures, metadata and licenses are under `source_textures/`. Scene/forest layout JSON files, where present, record object placement. These files do not replace the ready-to-run assets in `worlds/`.

Project-authored assets use the root MIT license. Embedded OSRF tree/house assets retain CC BY 3.0; Kenney, Fuel and Poly Haven assets retain CC0. See [third-party notices](../../THIRD_PARTY_NOTICES.md) and [scene instructions](../../docs/scenes/README.md).
