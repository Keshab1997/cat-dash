#!/usr/bin/env python3
"""Cat Dash — generated-asset verification (Agent B, batch CD-B1).

    blender --background --python tool/blender_verify_assets.py -- [--json out.json]

Re-imports every FBX in Assets/Art/Generated, then reports, per asset:
  * object hierarchy and per-object triangle count;
  * world-space bounds (metres) and the pivot offset (is the mesh on the ground?);
  * material slots and whether a UV map survived the round trip;
  * budget verdicts against the CD-B1 caps (cat <= 4000, prop <= 800, road <= 3000).

Fails loudly (exit code 1) on: missing .meta, duplicate GUIDs, a budget breach, or a
pivot that does not sit on the authored ground plane. This is an import check in
Blender — it is NOT a Unity import/visual verification and must not be reported as one.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

BUDGETS = {"Cat": 4000, "Prop_Crate": 800, "Prop_Barrier": 800, "Prop_Pot": 800,
           "Road_Segment": 3000}
# Expected lowest vertex per asset: cat and props rest on the authored ground plane, the
# road segment's driving surface is the pivot and its 0.30 m slab is meant to hang below.
EXPECTED_ZMIN = {"Cat": 0.0, "Prop_Crate": 0.0, "Prop_Barrier": 0.0, "Prop_Pot": 0.0,
                 "Road_Segment": -0.30}
PIVOT_TOLERANCE = 0.002


def verify(root: Path) -> tuple[list[str], list[dict]]:
    art.require_blender()
    import bpy  # noqa: E402

    problems: list[str] = []
    reports: list[dict] = []
    generated = root / "Assets/Art/Generated"
    guids: dict[str, str] = {}

    for fbx in sorted(generated.glob("*.fbx")):
        meta = fbx.with_name(fbx.name + ".meta")
        if not meta.exists():
            problems.append(f"{fbx.name}: missing .meta next to the FBX")
        else:
            text = meta.read_text(encoding="utf-8")
            guid_line = [line for line in text.splitlines() if line.startswith("guid: ")]
            if not guid_line:
                problems.append(f"{meta.name}: no guid")
            else:
                guid = guid_line[0].split(": ", 1)[1].strip()
                if guid in guids:
                    problems.append(f"{meta.name}: duplicate GUID with {guids[guid]}")
                guids[guid] = meta.name

        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(fbx), axis_forward="-Z", axis_up="Y")
        objects = list(bpy.context.scene.objects)
        meshes = [o for o in objects if o.type == "MESH"]
        if not meshes:
            problems.append(f"{fbx.name}: no mesh objects after import")
            continue

        import mathutils  # noqa: E402
        xs, ys, zs = [], [], []
        per_object = []
        triangles = 0
        materials = set()
        uv_ok = True
        for obj in meshes:
            mesh = obj.data
            tri = sum(len(poly.vertices) - 2 for poly in mesh.polygons)
            triangles += tri
            per_object.append({"name": obj.name, "triangles": tri,
                               "parent": obj.parent.name if obj.parent else None})
            for corner in obj.bound_box:
                world = obj.matrix_world @ mathutils.Vector(corner)
                xs.append(world.x); ys.append(world.y); zs.append(world.z)
            materials.update(slot.material.name for slot in obj.material_slots if slot.material)
            if not mesh.uv_layers:
                uv_ok = False

        name = fbx.stem
        budget = BUDGETS.get(name)
        if budget is None:
            problems.append(f"{name}: no budget registered in BUDGETS")
        elif triangles > budget:
            problems.append(f"{name}: {triangles} triangles exceed the {budget} budget")

        z_min = min(zs)
        expected_zmin = EXPECTED_ZMIN.get(name)
        if expected_zmin is None:
            problems.append(f"{name}: no expected lowest vertex registered in EXPECTED_ZMIN")
        elif abs(z_min - expected_zmin) > PIVOT_TOLERANCE:
            problems.append(f"{name}: lowest vertex is y={z_min:.4f}; expected "
                            f"{expected_zmin:+.2f} (tolerance {PIVOT_TOLERANCE})")
        if not uv_ok:
            problems.append(f"{name}: a mesh lost its UV map on import")
        if len(materials) != 1:
            problems.append(f"{name}: expected exactly 1 material, found {sorted(materials)}")

        reports.append({
            "asset": name,
            "triangles": triangles,
            "budget": budget,
            "objects": per_object,
            "materials": sorted(materials),
            "size_m": {"x": round(max(xs) - min(xs), 4), "y": round(max(ys) - min(ys), 4),
                       "z": round(max(zs) - min(zs), 4)},
            "bounds_m": {"x": [round(min(xs), 4), round(max(xs), 4)],
                         "y": [round(min(ys), 4), round(max(ys), 4)],
                         "z": [round(min(zs), 4), round(max(zs), 4)]},
            "lowest_vertex_m": round(z_min, 4),
            "expected_lowest_vertex_m": expected_zmin,
            "pivot_as_authored": expected_zmin is not None
                                 and abs(z_min - expected_zmin) <= PIVOT_TOLERANCE,
            "clips": [a.name for a in bpy.data.actions],
        })
    return problems, reports


def main() -> int:
    target = None
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--json" in argv:
        target = Path(argv[argv.index("--json") + 1])
    root = art.repo_root(Path(__file__).resolve())
    problems, reports = verify(root)

    print("=" * 72)
    for report in reports:
        print(f"{report['asset']:<16} {report['triangles']:>5} tris "
              f"(budget {report['budget']})  size {report['size_m']}  "
              f"materials={report['materials']}  lowest_y={report['lowest_vertex_m']} "
              f"(expected {report['expected_lowest_vertex_m']})")
        for obj in report["objects"]:
            print(f"    - {obj['name']:<14} {obj['triangles']:>4} tris  parent={obj['parent']}")
        if report["clips"]:
            print(f"    clips: {report['clips']}")
    print("=" * 72)
    for problem in problems:
        print("PROBLEM:", problem)
    print(f"Blender import check: {len(reports)} asset(s), {len(problems)} problem(s). "
          "Unity import/scale/material verification is still NOT RUN (needs the Editor).")
    if target:
        target.write_text(json.dumps({"reports": reports, "problems": problems}, indent=2),
                          encoding="utf-8")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
