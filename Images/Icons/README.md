# Icon assets

- `Equipment/`: equipment inventory artwork, named after each item with lowercase words separated by hyphens. The 20 ordinary equipment PNGs are 256×256 with transparent alpha. Existing Frostweave artwork retains its original resolution and is fitted by the renderer.
- `Weapons/`: reserved for future weapon slot icons.
- `Characters/`: reserved for future character icons.

Keep ready-to-use icons in these folders. Larger generated originals and generation records belong in `../Sources/Equipment/`, outside the runtime icon folders. Do not keep ZIP archives or duplicate exports with the icons.

The renderer selects equipment artwork by item name, preserves proportions, and falls back to a drawn slot symbol if artwork is missing. Rank labels and borders are drawn separately.
