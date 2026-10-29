# Icon assets

- `Equipment/`: equipment inventory artwork, named after each item with lowercase words separated by hyphens. The 20 ordinary equipment PNGs are 256×256 with transparent alpha. Existing Frostweave artwork retains its original resolution and is fitted by the renderer.
- `Weapons/`: reserved for future weapon slot icons.
- `Characters/Frost Mage/`: supplied front and back illustrations. The front view supplies the shared circular headshot on the title page, menu headers, Codex, and champion panel. The renderer crops its display viewport without changing either original file.

Keep ready-to-use icons in these folders. Larger generated originals and generation records belong in `../Sources/Equipment/`, outside the runtime icon folders. Do not keep ZIP archives or duplicate exports with the icons.

The renderer selects equipment artwork by item name, preserves proportions, and falls back to a drawn slot symbol if artwork is missing. Rank labels and borders are drawn separately.

In-game Frost Mage cutouts live in `../Sprites/frost-mage-views.png`, alongside
the built-in image-edit prompt and source references in
`frost-mage-views.generation.json`. Both supplied views are preserved in the
original `Characters/Frost Mage/` folder. The runtime caches front/back frames,
mirrors them for left/right travel, and aligns their boot baselines. Menu
portraits continue to use the original front illustration.

`../Sprites/frost-mage-walk-front.png` and `frost-mage-walk-back.png` each hold
four walk poses in a 2×2 grid, read left to right, then top to bottom. Their
source and exact built-in edit prompts are in `frost-mage-walk.generation.json`.
The runtime registers the poses on a common center and boot baseline without
rescaling each pose. One complete walk cycle covers 1.6 world tiles; animation
only advances on actual travel. The standing atlas remains the idle/fallback.
