# Asset register

| Path | Reference | Creator/source | License/permission | Generated how | Budget/cleanup | Verified in Unity |
|---|---|---|---|---|---|---|
| docs/art/cat-dash-visual-target.png | — (superseded) | AI-generated for this project | Provider terms apply; no third-party franchise reference requested | Text-to-image concept | Reference only, not bundled in Assets | Not a mesh / not gameplay |
| docs/art/refs/cat-v2-stylized-3d-render.png | — (this IS a reference) | AI-generated, published by Captain / owner-approved look | Provider terms apply; no third-party franchise reference requested | Text-to-image hero render | Look source for Cat.fbx; not bundled in Assets | Not a mesh / not gameplay |
| docs/art/refs/cat-v2-run-cycle-sheet.png | — (this IS a reference) | AI-generated, published by Captain / owner-approved look | Provider terms apply | Text-to-image pose sheet | Look source for the Run poses; not bundled | Not a mesh / not gameplay |
| docs/art/refs/props-road-sheet.png | — (this IS a reference) | AI-generated, published by Captain / owner-approved look | Provider terms apply | Text-to-image prop/road sheet | Look source for props + road; not bundled | Not a mesh / not gameplay |

Content worker must register every actual 3D mesh, material, texture and animation
with provenance and mobile budgets before shipping. Concept generation alone does
not establish legal clearance for every jurisdiction or platform.

**"Reference" means look only.** Every mesh below is original procedural geometry: all
vertices, polygons and UVs are written by the generators in `tool/`, and every texture
is painted pixel-by-pixel by those same scripts. No AI image is ever used as a mesh, a
texture map, or a source of geometry — the sheets are compared against, never sampled.

## Generated meshes (Agent B, batch CD-B1)

| Path | Reference | Creator/source | License/permission | Generated how | Budget/cleanup | Verified in Unity |
|---|---|---|---|---|---|---|
| Assets/Art/Generated/Cat.fbx | docs/art/refs/cat-v2-stylized-3d-render.png (look), docs/art/refs/cat-v2-run-cycle-sheet.png (poses) | Original procedural, Agent B (`tool/blender_cat.py`) | Own work, repo license | Blender 4.5.14 LTS; explicit verts/faces/UVs; 13 islands on joint pivots, rigidly parented to a 6-bone rig; embedded `Run` clip | 1870 tris (cap 4000), 1 material, 1024² atlas, 0.24 × 0.78 × 0.70 m, 6 bones, 1 clip 0.5 s | Blender round trip + spec-to-mesh asserted by `tool/blender_verify_assets.py`; import/keys/bob asserted by `CatDash.Art.Tests.EditMode`; **owner capture pending** |
| Assets/Art/Generated/Prop_Crate.fbx | docs/art/refs/props-road-sheet.png | Original procedural, Agent B (`tool/blender_propset.py --asset crate`) | Own work, repo license | Chamfered octagonal prism + corner posts; teal band on every face | 112 tris (cap 800), 1 material, 512² atlas, 0.80 m cube | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Prop_Barrier.fbx | docs/art/refs/props-road-sheet.png | Original procedural, Agent B (`tool/blender_propset.py --asset barrier`) | Own work, repo license | Cream board with orange hazard stripes on a splayed wooden trestle | 72 tris (cap 800), 1 material, 512² atlas, 1.60 × 0.35 × 0.92 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Prop_Pot.fbx | docs/art/refs/props-road-sheet.png | Original procedural, Agent B (`tool/blender_propset.py --asset pot`) | Own work, repo license | Tapered terracotta planter, soil disc, 5 stems with rounded leaves | 564 tris (cap 800), 1 material, 512² atlas, 0.60 × 0.60 × 0.73 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Road_Segment.fbx | docs/art/refs/props-road-sheet.png | Original procedural, Agent B (`tool/blender_road.py`) | Own work, repo license | 12 m tileable slab: 5.4 m asphalt, 1.2 m paving sidewalks, 0.15 m curb, top-planar UVs | 36 tris (cap 3000), 1 material, 1024² atlas, tile step 12 m | Same test assembly; **owner capture pending** |
| Assets/Art/Generated/Textures/*.png | (same sheets as the mesh each one serves) | Original procedural, Agent B (painted in the generators) | Own work, repo license | Deterministic pixel painting: mackerel stripes, mouse blaze, teal iris, hazard stripes, paving | 8-bit sRGB, ≤ 1024², no HDR/unlit | Same test assembly |

### What the look references fixed (CD-B1 redo)

The first cat was rejected for reading as a chubby cartoon. The redo moved to the
reference's real-kitten proportions and markings, and these are the flags the meshes
now carry (also emitted in each generator's `REPORT_JSON`):

- **Cat** — long tail curving up with a cream tip; dense mackerel stripe rings over a
  golden coat; white chest/belly and cream paw socks; a cream "mouse" blaze with ears,
  eye and tail outlined on the upper back (straddling the spine); pink inner ears with
  cream fluff rims; pink nose; large teal irises with a dark rim and a white catchlight.
- **Crate** — teal band around every face, light chamfer bands, plank grooves; the
  earlier white X-brace is gone (the sheet's crate has no brace).
- **Barrier** — cream board with orange diagonal stripes on a splayed wooden trestle
  with a cross bar; the earlier teal/grey metal version is gone.
- **Pot** — terracotta planter with a pale band, dark soil and five stems carrying
  rounded leaves (was six stiff blades).
- **Road** — darker asphalt with cream dashed lane paint, cream paving sidewalks and
  cream curbs (was grey/noisy paving).

### Notes for integrators

- **Pivots.** Cat and props rest on the authored ground plane (`y = 0`); the road
  segment's pivot *is* its driving surface and its 0.30 m slab hangs below so the
  tile has no visible underside at the join. Verified numerically by
  `tool/blender_verify_assets.py` (Blender import check, not a Unity check).
- **Facing.** Exported with `axis_forward='-Z', axis_up='Y'`: the cat faces Unity
  +Z, the road runs along Unity Z, the barrier board faces Unity +Z.
- **Imported root name.** Unity names the imported root GameObject after the FILE, so
  `Cat.fbx` imports as a root object called **`Cat`** — not `CatDash_Cat` (the empty node
  the generator exports does not become an object of its own), and the 13 part islands are
  its descendants. Frozen as `RunCycleSpec.ImportedRootName` and asserted by
  `Cat_KeepsItsPartHierarchyForTheFutureRig`; scene/rig code must look the model up by it.
- **Obstacles.** `Prop_Crate` / `Prop_Barrier` / `Prop_Pot` deliberately contain no
  prefab and no collider component: Agent C attaches `ObstacleMarker` plus a trigger
  `Collider` when building the scene (frozen contact point in `docs/batches/CD-B1.md`).
  Suggested box colliders are in the generator's `REPORT_JSON` output.
- **Materials.** Each FBX carries one material and a relative texture reference
  (`Textures/<Name>.png`), imported with material description import enabled. If a
  material ever loses its texture, `GeneratedModels_UseOneMaterialEachAndCarryATexture`
  fails and the fix is a one-line import setting, not a re-export.
- **Read/Write Enabled.** The generated FBX metas set `isReadable: 1` on purpose: the
  EditMode art tests read `mesh.triangles`, and a non-readable mesh returns an EMPTY
  array instead of throwing, which would let a triangle-budget assertion pass at zero.
  `GeneratedModels_ImportWithinTriangleBudget` asserts a non-zero count for that reason.
  These meshes are a few hundred triangles, so the memory cost is nil.
- **Animation import settings.** `Cat.fbx.meta` imports the cat as a LEGACY model
  (`animationType: 1`, `importAnimation: 1`) so the take becomes a clip named `Run`
  (Unity names a Legacy clip after the FBX take). `animationCompression: 0` keeps every
  authored key, `animationWrapMode: 2` loops it, `resampleCurves: 0` stops the importer
  re-timing the keys, and `optimizeBones: 0` keeps the rig: with rigid bone parenting the
  bones carry no vertices, and bone optimisation would otherwise be free to drop them.
- **Take name.** Blender names the FBX take after the SCENE on the export path this rig
  uses, and `<object>|<action>` on its per-action path - so `tool/blender_cat.py` names
  the scene `Run`. That is why the clip is called `Run` and not `CatDash_Rig|Run`; the
  name is asserted on the FBX itself by `tool/blender_verify_assets.py`.
- **Keyframes.** The exporter samples every `bake_anim_step`-th frame, so the step is the
  pose spacing (3): the clip is keyed on the pose frames and nothing else, instead of
  being baked to one key per frame. A channel whose value repeats its neighbour (the tail
  yaw reaches the same angle at the Air and the Contact poses) carries four keys rather
  than five, because the exporter merges a trailing duplicate; the clip as a whole is
  still keyed on exactly `RunCycleSpec.KeyedFrames()`.
- **Budget check.** `python3 tool/preflight.py` covers repository hygiene;
  `blender --background --python tool/blender_verify_assets.py` re-imports the FBXs
  and checks tri budgets, single material, UV survival and pivot heights; for the cat it
  also reads the take name, duration and key times straight out of the FBX binary, and
  measures every published run-cycle number (bob, leg pitch, tail sway, head
  counter-rotation) on the imported meshes, comparing them with the constants parsed out
  of `Assets/Art/RunCycleSpec.cs` so the C#, the generator and the FBX cannot drift;
  `CatDash.Art.Tests.EditMode` re-checks budgets, materials, textures, the atlas
  contract and the run-cycle pose order inside Unity (runs in CI's `full` stage).

### Known limitations (stated, not hidden)

- The cat is a stylised approximation of the hero render, not a match of its fur:
  fur groom, whiskers as geometry, and sub-surface fuzz are out of scope for a
  low-poly mobile asset. Markings are painted at ~1024², so a close-up camera will
  show flat colour where the reference shows individual hairs.
- The rig is RIGID, not skinned: each of the 13 islands is parented to exactly one
  bone (RunCycleSpec.SkinningRule), because the islands were modelled with their pivots
  on the joints. There are no weights and no blend shapes, so the cat stays crisp but
  cannot deform - which is the intended low-poly mobile look, not a shortcut.
- The embedded clip is the four poses of `cat-v2-run-cycle-sheet.png`
  (`RunPose` order contact → down → up → air), keyed on frames 0/3/6/9 at 24 fps with
  the Contact pose repeated on frame 12 so the 0.5 s loop closes. The vertical bob is a
  translation on the `Root` bone, the Contact pose is the model's rest pose, and the
  left/right legs of a pair swing together because a pair shares one bone
  (`SidePhaseOffset` needs more than six bones and is not expressible yet).
- The body-bob curve in `RunCycleSpec.BodyBobMetresAt` is a raised cosine whose baseline
  is the contact height: 0 at both contacts, `+BodyBobMetres` at mid-stance (0.25) and at
  the airborne apex (0.75). It replaced a `Sin`-based curve that peaked on the contacts
  and returned a 1.8e-18 residue at the quarters (the value CI failed on).
- The "mouse" blaze on the back is painted at ~55 % of a 384 px tile, so it reads as a
  small marking rather than a big graphic; it is verified by eye in the Blender previews,
  not by an automated test.
- **Animation: verified in Blender, NOT in Unity.** The round trip proves the FBX holds
  the right take, the right pose keys and the right values (the measured error against
  the spec formulas is 0.0 mm on legs, tail and head, and 0.000/0.015 m for the bob).
  It does NOT prove how Unity's importer reads it - Legacy clip creation, the clip name,
  the wrap mode and the `optimizeBones` interaction can only be confirmed by the Editor,
  and the art tests in CI are what will confirm them.
- **Visual gate: NOT RUN.** Only an owner-captured Unity screenshot/clip from the
  reviewed candidate SHA can clear it (docs/GAME_BRIEF.md, "Visual acceptance gate").

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

Regenerating the cat also rewrites its `.meta` with the animation import settings above.
The FBX embeds a creation timestamp, so regenerating is not byte-reproducible; what is
reproducible (and checked) is the geometry, the atlas, the rig and the clip's take name,
keys and pose values.

Generators refuse to overwrite an existing FBX (delete it first if intended) and
re-emit the `.meta` files with deterministic GUIDs derived from the asset path, so a
regeneration never renumbers GUIDs or disturbs scene references.
