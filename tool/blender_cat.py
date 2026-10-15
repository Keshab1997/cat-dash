#!/usr/bin/env python3
"""Cat Dash — original low-poly tabby cat generator (Agent B, batch CD-B1).

    blender --background --python tool/blender_cat.py -- \
        --output Assets/Art/Generated/Cat.fbx

Writes the FBX, its 1024 px sRGB atlas (Assets/Art/Generated/Textures/) and the
hand-written .meta files for both. One material, one texture, budget <= 4000 tris.

Authoring axes: the cat faces -Y in Blender, so after export (axis_forward='-Z',
axis_up='Y') it faces Unity +Z, +Y up. Pivot is at the ground between the paws.

The mesh ships as a small hierarchy (Body/Head/Ears/Legs/Tail) with each part's
pivot on its joint, so a rigid "run" can be faked this batch and the same loose
islands can be skinned by the 6-bone rig specified in Assets/Art/RunCycleSpec.cs.
No skinning is attempted here.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

# --------------------------------------------------------------------------- #
# Palette (kept in sync with Assets/Art/PaletteSpec.cs and docs/ASSETS.md)
# --------------------------------------------------------------------------- #
FUR = art.srgb("#E9953F")
FUR_MID = art.srgb("#F0A855")
FUR_DARK = art.srgb("#A85A16")
CREAM = art.srgb("#FBEFD9")
NOSE = art.srgb("#E8918F")
EYE = art.srgb("#2A1C12")
IRIS = art.srgb("#D9A24B")
HIGHLIGHT = art.srgb("#FFFFFF")

# --------------------------------------------------------------------------- #
# Texture atlas regions (u0, v0, u1, v1) in the 1024 px atlas
# --------------------------------------------------------------------------- #
R_FUR_BODY = (0.00, 0.00, 0.50, 0.50)   # body: u wraps around, v runs tail -> chest
R_FUR_FLAT = (0.00, 0.50, 0.25, 0.75)   # plain fur (ears, outer)
R_CREAM = (0.25, 0.50, 0.50, 0.75)      # plain cream (inner ear)
R_LEG = (0.00, 0.75, 0.25, 1.00)        # paw (v=0) -> hip (v=1)
R_TAIL = (0.25, 0.75, 0.50, 1.00)       # base (v=0) -> cream tip (v=1)
R_HEAD = (0.50, 0.00, 1.00, 0.50)       # face is centred on u=0.75, chin v=0, crown v=0.5
R_MUZZLE = (0.50, 0.50, 0.75, 0.75)     # cream muzzle, pink nose strip on top

SCALE = 0.95  # cat units -> metres: ~0.60 m long, ~0.58 m to the ear tips, ~0.22 m wide


def s(value: float) -> float:
    return value * SCALE


def point(x, y, z):
    return (s(x), s(y), s(z))


def local(part: art.Part, joint) -> art.Part:
    """Re-centre a world-space part on its joint so the object pivot sits there."""
    return part.transformed(offset=(-joint[0], -joint[1], -joint[2]))


# --------------------------------------------------------------------------- #
# Atlas
# --------------------------------------------------------------------------- #
def paint_atlas(size: int) -> art.Canvas:
    canvas = art.Canvas(size, seed=11)

    # -- body: orange back with stripes, cream belly only (u = ring: 0 belly, 0.5 spine)
    u0, v0, u1, v1 = R_FUR_BODY
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.035, block=128)
    # Cream belly: u = u0 and u = u1 are the SAME place on the model (the ring wraps),
    # so the wash has to be painted against both edges or the belly shows a seam.
    for edge in (u0, u1 - 0.145):
        canvas.blend(edge, v0, edge + 0.115, v1, CREAM, 0.88)
        canvas.blend(edge + 0.115, v0, edge + 0.145, v1, CREAM, 0.35)
    v_span = v1 - v0
    for centre in (0.035, 0.105, 0.175, 0.245, 0.315, 0.385):
        canvas.bands_y(u0, u1, [v0 + v_span * centre], 0.011, FUR_DARK, alpha=0.95)
        canvas.bands_y(u0, u1, [v0 + v_span * (centre + 0.028)], 0.006, FUR_MID, alpha=0.5)
    # (no mirror_tile here: the tiled grain and the horizontal bands already repeat)

    # -- plain fur + cream swatches -------------------------------------------- #
    fu0, fv0, fu1, fv1 = R_FUR_FLAT
    canvas.fill(fu0, fv0, fu1, fv1, FUR)
    canvas.grain_tiled(fu0, fv0, fu1, fv1, amount=0.035, block=64)
    cu0, cv0, cu1, cv1 = R_CREAM
    canvas.fill(cu0, cv0, cu1, cv1, CREAM)
    canvas.grain_tiled(cu0, cv0, cu1, cv1, amount=0.04, block=64)
    canvas.blend(cu0, cv0, cu1, cv0 + 0.04, NOSE, 0.35)

    # -- legs: cream sock at v=0 (paw) fading to orange at the hip --------------- #
    lu0, lv0, lu1, lv1 = R_LEG
    canvas.vgrad(lu0, lv0, lu1, lv0 + 0.035, CREAM, CREAM)
    canvas.vgrad(lu0, lv0 + 0.035, lu1, lv0 + 0.11, CREAM, FUR)
    canvas.vgrad(lu0, lv0 + 0.11, lu1, lv1, FUR, FUR)
    canvas.grain_tiled(lu0, lv0, lu1, lv1, amount=0.05, block=64)

    # -- tail: orange with bands, cream tip ------------------------------------- #
    tu0, tv0, tu1, tv1 = R_TAIL
    canvas.vgrad(tu0, tv0, tu1, tv0 + 0.17, FUR, FUR)
    canvas.vgrad(tu0, tv0 + 0.17, tu1, tv1, FUR, CREAM)
    canvas.bands_y(tu0, tu1, [0.06, 0.12], 0.016, FUR_DARK, alpha=0.8)
    canvas.grain_tiled(tu0, tv0, tu1, tv1, amount=0.05, block=64)

    # -- head: face centred on u=0.75 (front), chin at v=0, crown at v=0.5 ------ #
    hu0, hv0, hu1, hv1 = R_HEAD

    def head_uv(u_rel, v_rel):
        return (hu0 + (hu1 - hu0) * u_rel, hv0 + (hv1 - hv0) * v_rel)

    def head_scale(u_rel, v_rel):
        return ((hu1 - hu0) * u_rel, (hv1 - hv0) * v_rel)

    canvas.fill(hu0, hv0, hu1, hv1, FUR)
    canvas.grain_tiled(hu0, hv0, hu1, hv1, amount=0.035, block=128)
    # Forehead stripes: above the eyes, i.e. v_rel 0.55..0.72 (0.5 = equator).
    for u_rel in (0.45, 0.50, 0.55):
        canvas.bands_x(hv0 + (hv1 - hv0) * 0.55, hv0 + (hv1 - hv0) * 0.72,
                       [hu0 + (hu1 - hu0) * u_rel], 0.005, FUR_DARK, alpha=0.80)
    # Crown stripes that read from a rear follow camera, kept clear of the back seam (0.5).
    # Neither band may straddle u_rel 0/1: that edge IS the back seam of the model, so a
    # band crossing it would be cut in half and show as a line. Two stripes sit just
    # either side of the seam instead, which reads as a symmetric double stripe from behind.
    for u_rel in (0.022, 0.978, 0.075, 0.925):
        canvas.bands_x(hv0 + (hv1 - hv0) * 0.78, hv0 + (hv1 - hv0) * 0.93,
                       [hu0 + (hu1 - hu0) * u_rel], 0.006, FUR_DARK, alpha=0.7)
    # cream muzzle patch around the chin/nose area
    for alpha, grow in ((0.55, 1.35), (0.85, 1.0)):
        du, dv = head_scale(0.075 * grow, 0.085 * grow)
        cu, cv = head_uv(0.50, 0.16)
        canvas.ellipse(cu, cv, du, dv, CREAM, alpha)
    # eyes with amber iris and a highlight
    for side in (-1, 1):
        eu, ev = head_uv(0.50 + side * 0.047, 0.30)
        du, dv = head_scale(0.042, 0.050)
        canvas.ellipse(eu, ev, du, dv, EYE, 1.0)
        iu, iv = head_uv(0.50 + side * 0.047, 0.295)
        du, dv = head_scale(0.026, 0.032)
        canvas.ellipse(iu, iv, du, dv, IRIS, 0.95)
        hu, hv = head_uv(0.50 + side * 0.047 - 0.008, 0.318)
        du, dv = head_scale(0.008, 0.010)
        canvas.ellipse(hu, hv, du, dv, HIGHLIGHT, 0.95)
    # block=128 divides the 512 px head region exactly, so the tiled grain is seamless

    # -- muzzle: cream with a pink nose strip on the top face ------------------- #
    mu0, mv0, mu1, mv1 = R_MUZZLE
    canvas.fill(mu0, mv0, mu1, mv1, CREAM)
    canvas.blend(mu0, mv1 - 0.035, mu1, mv1, NOSE, 0.95)
    canvas.blend(mu0, mv0, mu1, mv0 + 0.010, EYE, 0.35)  # soft mouth shadow
    canvas.grain(mu0, mv0, mu1, mv1, amount=0.035, cells=40)

    # -- reserved quadrant: plain fur so nothing samples a wrong colour --------- #
    canvas.fill(0.75, 0.50, 1.00, 1.00, FUR)
    canvas.grain_tiled(0.75, 0.50, 1.00, 1.00, amount=0.035, block=64)
    return canvas


# --------------------------------------------------------------------------- #
# Geometry
# --------------------------------------------------------------------------- #
BODY_SEGMENTS = 16


def build_body() -> art.Part:
    """Torso tube. The atlas tile is painted with the belly in its middle and the
    spine on both edges, so ring u=0 must be the belly; `phase` picks the side and
    the choice is verified from the emitted vertices instead of assumed."""
    path = [point(0, 0.155, 0.245), point(0, 0.075, 0.255), point(0, -0.005, 0.262),
            point(0, -0.090, 0.262), point(0, -0.175, 0.253)]
    radii = [s(r) for r in (0.090, 0.108, 0.115, 0.110, 0.094)]
    ring_v = [R_FUR_BODY[1] + (R_FUR_BODY[3] - R_FUR_BODY[1]) * t
              for t in (0.05, 0.15, 0.25, 0.35, 0.45)]
    u0, _, u1, _ = R_FUR_BODY
    axis_z = path[2][2]
    part = None
    for phase in (0.0, 3.141592653589793):
        candidate = art.tube(path, radii, segments=BODY_SEGMENTS, u_range=(u0, u1),
                             ring_v=ring_v, phase=phase, hint=(1.0, 0.0, 0.0),
                             squash=0.88)
        if candidate.verts[0][2] < axis_z:  # ring 0, segment 0 sits under the spine
            part = candidate
            break
    if part is None:
        raise SystemExit("error: could not orient the torso belly/back UV seam")
    span = u1 - u0

    def tile_u(u: float) -> float:
        ring_u = (u - u0) / span
        return u0 + span * (0.5 * ((ring_u + 0.5) % 1.0))

    wrap = [[(tile_u(u), v) for u, v in face_uv] for face_uv in part.face_uvs]
    return art.Part(part.verts, part.faces, wrap)


def build_neck() -> art.Part:
    """Short collar joining chest and head so the silhouette reads as one animal."""
    return art.tube([point(0, -0.135, 0.280), point(0, -0.185, 0.325), point(0, -0.225, 0.365)],
                    [s(0.082), s(0.076), s(0.070)], segments=10,
                    u_range=(R_FUR_FLAT[0], R_FUR_FLAT[2]),
                    ring_v=[R_FUR_FLAT[1] + (R_FUR_FLAT[3] - R_FUR_FLAT[1]) * t
                            for t in (0.0, 0.5, 1.0)],
                    hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_head() -> art.Part:
    return art.sphere(point(0, -0.285, 0.395), (s(0.118), s(0.118), s(0.112)),
                      segments=16, rows=11, u_range=(R_HEAD[0], R_HEAD[2]),
                      v_range=(R_HEAD[1], R_HEAD[3]), phase=3.141592653589793)


def build_muzzle() -> art.Part:
    """Cream muzzle pad: squashed sphere pushed through the lower face."""
    return art.sphere(point(0, -0.352, 0.350), (s(0.066), s(0.052), s(0.044)),
                      segments=12, rows=7, u_range=(R_MUZZLE[0], R_MUZZLE[2]),
                      v_range=(R_MUZZLE[1], R_MUZZLE[3]), phase=3.141592653589793)


def build_ear(side: int) -> art.Part:
    base = point(side * 0.062, -0.285, 0.462)
    apex = point(side * 0.092, -0.290, 0.605)
    part = art.pyramid(base, (s(0.082), s(0.060)), apex, R_FUR_FLAT, R_CREAM)
    # pyramid(): face 0 is the front (-Y, inner ear = cream), faces 1-3 the sides
    # (triangles, 3 UVs) and face 4 the base (quad, 4 UVs). Keep cream on the front
    # only; the sides become plain fur so the ear does not read as two-tone.
    uvs = [part.face_uvs[0], part.face_uvs[1], part.face_uvs[2], part.face_uvs[1],
           part.face_uvs[4]]
    return art.Part(part.verts, part.faces, uvs)


def build_leg(name: str, side: int, front: bool) -> art.Part:
    x = side * (0.052 if front else 0.060)
    y = -0.115 if front else 0.105
    top = 0.185 if front else 0.195
    path = [point(x, y, top), point(x, y - 0.004, top * 0.5), point(x, y - 0.004, 0.0)]
    radii = [s(r) for r in ((0.044, 0.031, 0.036) if front else (0.056, 0.034, 0.038))]
    v_rows = [R_LEG[3], R_LEG[1] + (R_LEG[3] - R_LEG[1]) * 0.5, R_LEG[1]]
    return art.tube(path, radii, segments=8, u_range=(R_LEG[0], R_LEG[2]),
                    ring_v=v_rows, hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_tail() -> art.Part:
    path = [point(0, 0.165, 0.245), point(0, 0.228, 0.300), point(0, 0.268, 0.385),
            point(0, 0.264, 0.468), point(0, 0.232, 0.538), point(0, 0.196, 0.575)]
    radii = [s(r) for r in (0.050, 0.040, 0.032, 0.026, 0.022, 0.018)]
    ring_v_rows = (0.0, 0.18, 0.36, 0.56, 0.78, 1.0)
    ring_v = [R_TAIL[1] + (R_TAIL[3] - R_TAIL[1]) * t for t in ring_v_rows]
    return art.tube(path, radii, segments=10, u_range=(R_TAIL[0], R_TAIL[2]),
                    ring_v=ring_v, hint=(1.0, 0.0, 0.0), caps=(True, True))


def main() -> None:
    args = art.standard_args(
        "Generate the original Cat Dash tabby cat (FBX + atlas + .meta)")
    if args.texture_size != 1024:
        raise SystemExit("error: the cat atlas is authored for 1024 px (budget ceiling)")
    art.reset_scene()

    canvas = paint_atlas(args.texture_size)
    root = art.repo_root(Path(args.output).resolve())
    texture_rel = Path("Assets/Art/Generated/Textures") / f"Cat_{args.texture_size}.png"
    scratch_texture = root / texture_rel
    canvas.save(scratch_texture)
    material = art.make_material("M_Cat_Fur", scratch_texture, FUR, roughness=0.85)

    # joint pivots (Blender space, metres)
    joints = {
        "CatDash_Cat": (0.0, 0.0, 0.0),
        "Body": point(0, -0.02, 0.265),
        "Neck": point(0, -0.135, 0.280),
        "Head": point(0, -0.225, 0.365),
        "Muzzle": point(0, -0.325, 0.350),
        "EarL": point(-0.062, -0.285, 0.462),
        "EarR": point(0.062, -0.285, 0.462),
        "LegFrontL": point(-0.052, -0.115, 0.185),
        "LegFrontR": point(0.052, -0.115, 0.185),
        "LegHindL": point(-0.060, 0.105, 0.195),
        "LegHindR": point(0.060, 0.105, 0.195),
        "Tail": point(0, 0.165, 0.245),
    }

    root_empty = art.make_empty("CatDash_Cat")
    build = [
        ("Body", build_body(), joints["Body"]),
        ("Neck", build_neck(), joints["Neck"]),
        ("Head", build_head(), joints["Head"]),
        ("Muzzle", build_muzzle(), joints["Muzzle"]),
        ("EarL", build_ear(-1), joints["EarL"]),
        ("EarR", build_ear(1), joints["EarR"]),
        ("LegFrontL", build_leg("LegFrontL", -1, True), joints["LegFrontL"]),
        ("LegFrontR", build_leg("LegFrontR", 1, True), joints["LegFrontR"]),
        ("LegHindL", build_leg("LegHindL", -1, False), joints["LegHindL"]),
        ("LegHindR", build_leg("LegHindR", 1, False), joints["LegHindR"]),
        ("Tail", build_tail(), joints["Tail"]),
    ]

    parts = []
    for name, part, joint in build:
        # build_*() already returns metres (point() applies SCALE), so no second scale here
        art.make_object(name, local(part, joint), material=material, smooth=True,
                        parent=root_empty).location = joint
        parts.append((name, part))

    total = sum(part.tri_count() for _, part in parts)
    if total > 4000:
        raise SystemExit(f"error: cat budget exceeded: {total} triangles > 4000")

    art.finish("Cat", args,
               texture_canvas=None,  # written above so the material could load it
               parts=parts, material_name="M_Cat_Fur", object_name="CatDash_Cat",
               pivot="ground level, centred between the paws (Blender 0,0,0; Unity 0,0,0)",
               forward="faces Blender -Y => Unity +Z",
               texture_name=f"Cat_{args.texture_size}.png", texture_written=True,
               extra={"parts_pivots": {k: [round(c, 4) for c in v] for k, v in joints.items()},
                      "atlas_regions": {"body": R_FUR_BODY, "fur_flat": R_FUR_FLAT,
                                        "cream": R_CREAM, "leg": R_LEG, "tail": R_TAIL,
                                        "head": R_HEAD, "muzzle": R_MUZZLE},
                      "rig": "no skinning this batch; see Assets/Art/RunCycleSpec.cs"})
    print(f"note: cat parts: {[name for name, _ in parts]}")


if __name__ == "__main__":
    main()
