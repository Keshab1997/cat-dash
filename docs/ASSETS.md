# Asset register

| Path | Creator/source | License/permission | Generated how | Budget/cleanup | Verified in Unity |
|---|---|---|---|---|---|
| docs/art/cat-dash-visual-target.png | AI-generated for this project | Provider terms apply; no third-party franchise reference requested | Text-to-image concept | Reference only, not bundled in Assets | Not a mesh / not gameplay |

Content worker must register every actual 3D mesh, material, texture and animation
with provenance and mobile budgets before shipping. Concept generation alone does
not establish legal clearance for every jurisdiction or platform.

## Generated meshes (Agent B, batch CD-B1)

All five meshes are **original procedural geometry**: every vertex, polygon and UV is
written by the generator scripts in `tool/`, from a palette defined in
`Assets/Art/PaletteSpec.cs`. No third-party model, no paid AI mesh service, no
texture from an external source. Blender 4.5.14 LTS is only the *runtime* that
evaluates the scripts and writes FBX.

| Path | Creator/source | License/permission | Generated how | Budget/cleanup | Verified in Unity |
|---|---|---|---|---|---|
| Assets/Art/Generated/Cat.fbx | Original procedural, Agent B (tool/blender_cat.py) | Own work, repo license | Blender 4.5.14 LTS, explicit verts/faces/UVs, 11 loose islands on joint pivots | 1008 tris (cap 4000), 1 material, 1024² atlas, 0.22 × 0.67 × 0.57 m | Import/budget/material asserted by `CatDash.Art.Tests.EditMode`; **owner capture pending** |
| Assets/Art/Generated/Prop_Crate.fbx | Original procedural, Agent B (tool/blender_propset.py --asset crate) | Own work, repo license | Chamfered octagonal prism + corner posts, procedural atlas | 112 tris (cap 800), 1 material, 512² atlas, 0.80 m cube | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Prop_Barrier.fbx | Original procedural, Agent B (tool/blender_propset.py --asset barrier) | Own work, repo license | Striped board on two posts with feet and caps | 84 tris (cap 800), 1 material, 512² atlas, 1.64 × 0.30 × 0.95 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Prop_Pot.fbx | Original procedural, Agent B (tool/blender_propset.py --asset pot) | Own work, repo license | Tapered planter, soil disc, 6 leaf pyramids | 180 tris (cap 800), 1 material, 512² atlas, 0.60 × 0.60 × 0.69 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Road_Segment.fbx | Original procedural, Agent B (tool/blender_road.py) | Own work, repo license | 12 m tileable slab: 5.4 m road, 1.2 m sidewalks, 0.15 m curb, top-planar UVs | 36 tris (cap 3000), 1 material, 1024² atlas, tile step 12 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Textures/*.png | Original procedural, Agent B (painted in the generators) | Own work, repo license | Deterministic pixel painting (stripes, paving, hazard stripes, X-braces) | 8-bit sRGB, ≤ 1024², no HDR/unlit | Same test assembly |

### Notes for integrators

- **Pivots.** Cat and props rest on the authored ground plane (`y = 0`); the road
  segment's pivot *is* its driving surface and its 0.30 m slab hangs below so the
  tile has no visible underside at the join. Verified numerically by
  `tool/blender_verify_assets.py` (Blender import check, not a Unity check).
- **Facing.** Exported with `axis_forward='-Z', axis_up='Y'`: the cat faces Unity
  +Z, the road runs along Unity Z, the barrier board faces Unity +Z.
- **Obstacles.** `Prop_Crate` / `Prop_Barrier` / `Prop_Pot` deliberately contain no
  prefab and no collider component: Agent C attaches `ObstacleMarker` plus a trigger
  `Collider` when building the scene (frozen contact point in `docs/batches/CD-B1.md`).
  Suggested box colliders are in the generator's `REPORT_JSON` output.
- **Materials.** Each FBX carries one material and a relative texture reference
  (`Textures/<Name>.png`), imported with material description import enabled. If a
  material ever loses its texture, `GeneratedModels_UseOneMaterialEachAndCarryATexture`
  fails and the fix is a one-line import setting, not a re-export.
- **Budget check.** `python3 tool/preflight.py` covers repository hygiene;
  `blender --background --python tool/blender_verify_assets.py` re-imports the FBXs
  and checks tri budgets, single material, UV survival and pivot heights;
  `CatDash.Art.Tests.EditMode` re-checks budgets, materials, textures and the atlas
  contract inside Unity (runs in CI's `full` stage).

### Regenerating

Blender is not installed by CI and is never required to build the project; the FBXs
are committed. To regenerate after a palette or proportion change:

```bash
blender --background --python tool/blender_cat.py     -- --output Assets/Art/Generated/Cat.fbx
blender --background --python tool/blender_propset.py -- --asset crate   --output Assets/Art/Generated/Prop_Crate.fbx
blender --background --python tool/blender_propset.py -- --asset barrier --output Assets/Art/Generated/Prop_Barrier.fbx
blender --background --python tool/blender_propset.py -- --asset pot     --output Assets/Art/Generated/Prop_Pot.fbx
blender --background --python tool/blender_road.py    -- --output Assets/Art/Generated/Road_Segment.fbx
blender --background --python tool/blender_verify_assets.py
```

Generators refuse to overwrite an existing FBX (delete it first if intended) and
re-emit the `.meta` files with deterministic GUIDs derived from the asset path, so a
regeneration never renumbers GUIDs or disturbs scene references.
