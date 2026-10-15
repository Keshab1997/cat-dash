#!/usr/bin/env python3
"""Cat Dash — obstacle prop generator: crate / barrier / pot (Agent B, batch CD-B1).

    blender --background --python tool/blender_propset.py -- \
        --asset crate --output Assets/Art/Generated/Prop_Crate.fbx

One script, one asset per run (same pattern as the kit's tool/blender_props.py).
Each prop is a single mesh object, flat-shaded, one 512 px material/texture,
<= 800 triangles, pivot at the bottom centre so Content can drop it into a lane.

Sizing is measured against Lanes.LaneWidth = 1.8 m: crate 0.80 m, barrier 1.60 m
wide, pot 0.60 m across. ObstacleMarker + a trigger Collider are attached by
Agent C in the scene generator (this FBX deliberately ships no prefab/components).
"""
from __future__ import annotations

import math
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

# --------------------------------------------------------------------------- #
# Palette (mirrors Assets/Art/PaletteSpec.cs)
# --------------------------------------------------------------------------- #
WOOD = art.srgb("#B87E4C")
WOOD_DARK = art.srgb("#94562A")
WOOD_LIGHT = art.srgb("#D9A96C")
WOOD_FRAME_RGB = art.srgb("#F3EBD9")
METAL = art.srgb("#4A4E57")
METAL_LIGHT = art.srgb("#6E7480")
BARRIER_RED = art.srgb("#E4764A")
BARRIER_TEAL = art.srgb("#57BFB4")
BARRIER_WHITE = art.srgb("#F7EEDD")
TERRACOTTA = art.srgb("#C4623C")
TERRACOTTA_DARK = art.srgb("#9E4A2B")
SOIL = art.srgb("#4A3524")
LEAF = art.srgb("#5FA24A")
LEAF_DARK = art.srgb("#3F7A35")

# crate / barrier / pot texture regions (512 px atlas)
R_WOOD_SIDE = (0.00, 0.00, 1.00, 0.50)
R_WOOD_CAP = (0.00, 0.50, 1.00, 0.75)
R_WOOD_FRAME = (0.00, 0.75, 1.00, 1.00)
R_BARRIER_STRIPES = (0.00, 0.00, 1.00, 0.50)
R_BARRIER_EDGE = (0.00, 0.50, 1.00, 0.62)
R_METAL = (0.00, 0.62, 0.50, 1.00)
R_POT_WALL = (0.00, 0.00, 1.00, 0.60)
R_POT_SOIL = (0.00, 0.60, 0.50, 1.00)
R_POT_LEAF = (0.50, 0.60, 1.00, 1.00)


# --------------------------------------------------------------------------- #
# Crate: chamfered wooden box with a perimeter that lands the plank grooves
# --------------------------------------------------------------------------- #
CRATE_SIZE = 0.80
CRATE_BEVEL = 0.055
CRATE_PLANKS = 3  # plank grooves per flat side


def crate_profile():
    """Octagonal chamfered square, CCW, starting mid-way along the -Y side."""
    half = CRATE_SIZE * 0.5
    b = CRATE_BEVEL
    return [(-half + b, -half), (half - b, -half), (half, -half + b), (half, half - b),
            (half - b, half), (-half + b, half), (-half, half - b), (-half, -half + b)]


def crate_side_density():
    """Per-flat-side fraction of the perimeter (used to place plank grooves)."""
    profile = crate_profile()
    lengths = []
    for i in range(len(profile)):
        x0, y0 = profile[i]
        x1, y1 = profile[(i + 1) % len(profile)]
        lengths.append(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5)
    total = sum(lengths)
    return [length / total for length in lengths]


def build_crate():
    profile = crate_profile()
    rings = [(0.0, 0.90), (CRATE_BEVEL, 1.0), (CRATE_SIZE - CRATE_BEVEL, 1.0), (CRATE_SIZE, 0.90)]
    part = art.prism(profile, rings, R_WOOD_SIDE, R_WOOD_CAP, R_WOOD_CAP)
    # raised corner posts: give the silhouette an edge and carry the pale frame
    half = CRATE_SIZE * 0.5 - 0.045
    posts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            posts.append(art.box((0.075, 0.075, CRATE_SIZE - 0.03),
                                 (sx * half, sy * half, CRATE_SIZE * 0.5), uv=R_WOOD_FRAME))
    part = art.combine([part, *posts])
    return part, {"size_m": [CRATE_SIZE, CRATE_SIZE, CRATE_SIZE],
                  "collider": {"type": "BoxCollider", "size": [CRATE_SIZE, CRATE_SIZE, CRATE_SIZE],
                               "center": [0.0, 0.30, 0.0]},
                  "note": "obstacle: ObstacleMarker + isTrigger collider placed by Agent C"}


def paint_crate(canvas: art.Canvas) -> None:
    u0, v0, u1, v1 = R_WOOD_SIDE
    canvas.vgrad(u0, v0, u1, v1, WOOD_DARK, WOOD)
    canvas.grain(u0, v0, u1, v1, amount=0.10, cells=90)
    # plank grooves at exact perimeter fractions of each flat side
    densities = crate_side_density()
    u = 0.0
    for index, density in enumerate(densities):
        start = u
        u += density
        if density < 0.12:  # chamfer: darker frame band
            canvas.blend(u0 + (u1 - u0) * start, v0, u0 + (u1 - u0) * u, v1, WOOD_DARK, 0.75)
            continue
        for plank in range(1, CRATE_PLANKS):
            groove = start + density * plank / CRATE_PLANKS
            canvas.blend(u0 + (u1 - u0) * (groove - 0.004), v0,
                         u0 + (u1 - u0) * (groove + 0.004), v1, WOOD_DARK, 0.85)
        su0, su1 = u0 + (u1 - u0) * start, u0 + (u1 - u0) * u
        canvas.speckle(su0, v0, su1, v1, WOOD_LIGHT, count=10, radius=0.004, alpha=0.35)
        # pale frame along the top and bottom of the side, plus the X brace
        canvas.fill(su0, v1 - 0.042, su1, v1 - 0.030, WOOD_FRAME_RGB)
        canvas.fill(su0, v0 + 0.030, su1, v0 + 0.042, WOOD_FRAME_RGB)
        canvas.segment(su0 + 0.012, v0 + 0.042, su1 - 0.012, v1 - 0.042, WOOD_FRAME_RGB, 0.010)
        canvas.segment(su0 + 0.012, v1 - 0.042, su1 - 0.012, v0 + 0.042, WOOD_FRAME_RGB, 0.010)
    cu0, cv0, cu1, cv1 = R_WOOD_CAP
    canvas.fill(cu0, cv0, cu1, cv1, WOOD)
    canvas.grain(cu0, cv0, cu1, cv1, amount=0.10, cells=70)
    canvas.bands_y(cu0, cu1, [cv0 + (cv1 - cv0) * t for t in (0.25, 0.5, 0.75)], 0.012,
                   WOOD_DARK, alpha=0.75)
    canvas.bands_x(cv0, cv1, [cu0 + (cu1 - cu0) * t for t in (0.25, 0.5, 0.75)], 0.012,
                   WOOD_DARK, alpha=0.55)
    fu0, fv0, fu1, fv1 = R_WOOD_FRAME
    canvas.fill(fu0, fv0, fu1, fv1, WOOD_FRAME_RGB)
    canvas.grain(fu0, fv0, fu1, fv1, amount=0.06, cells=40)


# --------------------------------------------------------------------------- #
# Barrier: striped board on two posts with feet
# --------------------------------------------------------------------------- #
BARRIER_WIDTH = 1.60
BARRIER_HEIGHT = 0.90
BARRIER_DEPTH = 0.30
BARRIER_POST = 0.09


def build_barrier():
    post_x = BARRIER_WIDTH * 0.5 - BARRIER_POST * 0.5 - 0.055
    board_h = 0.26
    board_z = BARRIER_HEIGHT - board_h * 0.5
    parts = [
        art.box((BARRIER_WIDTH, 0.06, board_h), (0.0, 0.0, board_z),
                faces_uv=[R_BARRIER_EDGE, R_BARRIER_EDGE, R_BARRIER_STRIPES,
                          R_BARRIER_STRIPES, R_BARRIER_EDGE, R_BARRIER_EDGE]),
        art.box((BARRIER_POST, BARRIER_POST, BARRIER_HEIGHT),
                (-post_x, 0.0, BARRIER_HEIGHT * 0.5), uv=R_METAL),
        art.box((BARRIER_POST, BARRIER_POST, BARRIER_HEIGHT),
                (post_x, 0.0, BARRIER_HEIGHT * 0.5), uv=R_METAL),
        art.box((0.24, BARRIER_DEPTH, 0.08), (-post_x, 0.0, 0.04), uv=R_METAL),
        art.box((0.24, BARRIER_DEPTH, 0.08), (post_x, 0.0, 0.04), uv=R_METAL),
        # cream cap on top of each post, like the target's little finials
        art.box((0.11, 0.11, 0.05), (-post_x, 0.0, BARRIER_HEIGHT + 0.025), uv=R_METAL),
        art.box((0.11, 0.11, 0.05), (post_x, 0.0, BARRIER_HEIGHT + 0.025), uv=R_METAL),
    ]
    return art.combine(parts), {
        "size_m": [BARRIER_WIDTH, BARRIER_DEPTH, BARRIER_HEIGHT],
        "collider": {"type": "BoxCollider", "size": [BARRIER_WIDTH, 0.90, BARRIER_DEPTH],
                     "center": [0.0, 0.45, 0.0]},
        "note": "obstacle: ObstacleMarker + isTrigger collider placed by Agent C"}


def paint_barrier(canvas: art.Canvas) -> None:
    u0, v0, u1, v1 = R_BARRIER_STRIPES
    canvas.fill(u0, v0, u1, v1, BARRIER_WHITE)
    canvas.diagonal_stripes(u0, v0, u1, v1, BARRIER_RED, BARRIER_TEAL, period=0.115, slope=0.55)
    canvas.grain(u0, v0, u1, v1, amount=0.05, cells=50)
    canvas.grain(u0, v0, u1, v1, amount=0.06, cells=60)
    canvas.blend(u0, v0, u1, v0 + 0.03, METAL, 0.25)
    eu0, ev0, eu1, ev1 = R_BARRIER_EDGE
    canvas.fill(eu0, ev0, eu1, ev1, BARRIER_WHITE)
    canvas.grain(eu0, ev0, eu1, ev1, amount=0.07, cells=40)
    mu0, mv0, mu1, mv1 = R_METAL
    canvas.vgrad(mu0, mv0, mu1, mv1, BARRIER_WHITE, art.srgb("#E4D9C4"))
    canvas.grain(mu0, mv0, mu1, mv1, amount=0.06, cells=40)
    canvas.blend(mu0, mv0, mu1, mv0 + 0.05, art.srgb("#D9CDB6"), 0.5)


# --------------------------------------------------------------------------- #
# Pot: terracotta planter with soil and a few low-poly leaves
# --------------------------------------------------------------------------- #
POT_HEIGHT = 0.50
POT_RADIUS = 0.30
POT_SEGMENTS = 12


def build_pot():
    wall = art.tube([(0.0, 0.0, 0.0), (0.0, 0.0, 0.20), (0.0, 0.0, POT_HEIGHT - 0.06),
                     (0.0, 0.0, POT_HEIGHT)],
                    [POT_RADIUS - 0.075, POT_RADIUS - 0.035, POT_RADIUS - 0.010, POT_RADIUS],
                    segments=POT_SEGMENTS, u_range=(R_POT_WALL[0], R_POT_WALL[2]),
                    ring_v=[R_POT_WALL[1], R_POT_WALL[1] + 0.20, R_POT_WALL[1] + 0.42,
                            R_POT_WALL[3]],
                    hint=(0.0, 1.0, 0.0), caps=(True, False))
    rim = art.annulus((0.0, 0.0, POT_HEIGHT), POT_RADIUS - 0.045, POT_RADIUS, POT_SEGMENTS,
                      (R_POT_WALL[0], R_POT_WALL[3] - 0.03, R_POT_WALL[2], R_POT_WALL[3]))
    inner = art.tube([(0.0, 0.0, POT_HEIGHT), (0.0, 0.0, POT_HEIGHT - 0.09)],
                     [POT_RADIUS - 0.045, POT_RADIUS - 0.085], segments=POT_SEGMENTS,
                     u_range=(R_POT_WALL[0], R_POT_WALL[2]),
                     ring_v=[R_POT_WALL[3], R_POT_WALL[1] + 0.30],
                     hint=(0.0, 1.0, 0.0), caps=(False, False))
    soil = art.disc((0.0, 0.0, POT_HEIGHT - 0.09), POT_RADIUS - 0.085, POT_SEGMENTS,
                    R_POT_SOIL)
    parts = [wall, rim, inner, soil]
    # leaves: squashed pyramids fanning out of the soil
    leaf_base = POT_HEIGHT - 0.07
    for angle, height, lean in ((15, 0.20, 0.05), (75, 0.26, 0.07), (135, 0.17, 0.05),
                                (200, 0.23, 0.06), (265, 0.19, 0.05), (320, 0.24, 0.06)):
        radians = angle * math.pi / 180.0
        base_r = 0.075
        base_x = base_r * math.cos(radians)
        base_y = base_r * math.sin(radians)
        apex = ((base_r + lean) * 1.6 * math.cos(radians),
                (base_r + lean) * 1.6 * math.sin(radians),
                leaf_base + height)
        parts.append(art.pyramid((base_x, base_y, leaf_base), (0.10, 0.05), apex,
                                 R_POT_LEAF, R_POT_LEAF))
    return art.combine(parts), {
        "size_m": [POT_RADIUS * 2, POT_RADIUS * 2, 0.69],
        "collider": {"type": "BoxCollider", "size": [POT_RADIUS * 2, POT_HEIGHT, POT_RADIUS * 2],
                     "center": [0.0, POT_HEIGHT * 0.5, 0.0]},
        "note": "obstacle body is the pot; foliage is decoration, collider covers the pot"}


def paint_pot(canvas: art.Canvas) -> None:
    u0, v0, u1, v1 = R_POT_WALL
    canvas.vgrad(u0, v0, u1, v1, TERRACOTTA_DARK, TERRACOTTA)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=96)
    canvas.blend(u0, v1 - 0.05, u1, v1, TERRACOTTA_DARK, 0.45)   # rim shading
    for centre, colour in ((0.26, art.srgb("#F2E4CE")), (0.44, TERRACOTTA_DARK)):
        canvas.bands_y(u0, u1, [v0 + (v1 - v0) * centre], 0.022, colour, alpha=0.85)
    su0, sv0, su1, sv1 = R_POT_SOIL
    canvas.vgrad(su0, sv0, su1, sv1, SOIL, art.srgb("#5C452F"))
    canvas.speckle(su0, sv0, su1, sv1, art.srgb("#2E2013"), count=140, radius=0.004, alpha=0.6)
    lu0, lv0, lu1, lv1 = R_POT_LEAF
    canvas.vgrad(lu0, lv0, lu1, lv1, LEAF_DARK, LEAF)
    canvas.grain(lu0, lv0, lu1, lv1, amount=0.10, cells=40)
    canvas.bands_x(lv0, lv1, [lu0 + (lu1 - lu0) * 0.5], 0.006, art.srgb("#8CBF6A"), alpha=0.6)


def check_regions(name, regions):
    """Guard: two atlas regions may share edges but never overlap (a pale frame
    fill once flooded the cap region, which washed out the crate)."""
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            (au0, av0, au1, av1), (bu0, bv0, bu1, bv1) = regions[i][1], regions[j][1]
            if au0 < bu1 and bu0 < au1 and av0 < bv1 and bv0 < av1:
                raise SystemExit(f"error: {name}: atlas regions {regions[i][0]} and "
                                 f"{regions[j][0]} overlap")
    return True


REGION_SETS = {
    "crate": [("side", R_WOOD_SIDE), ("cap", R_WOOD_CAP), ("frame", R_WOOD_FRAME)],
    "barrier": [("stripes", R_BARRIER_STRIPES), ("edge", R_BARRIER_EDGE), ("metal", R_METAL)],
    "pot": [("wall", R_POT_WALL), ("soil", R_POT_SOIL), ("leaf", R_POT_LEAF)],
}

ASSETS = {
    "crate": {"object": "Prop_Crate", "builder": build_crate, "painter": paint_crate,
              "material": "M_Prop_Crate", "colour": WOOD, "texture": "Prop_Crate_512.png",
              "roughness": 0.8},
    "barrier": {"object": "Prop_Barrier", "builder": build_barrier, "painter": paint_barrier,
                "material": "M_Prop_Barrier", "colour": BARRIER_RED,
                "texture": "Prop_Barrier_512.png", "roughness": 0.6},
    "pot": {"object": "Prop_Pot", "builder": build_pot, "painter": paint_pot,
            "material": "M_Prop_Pot", "colour": TERRACOTTA, "texture": "Prop_Pot_512.png",
            "roughness": 0.75},
}


def main() -> None:
    def add_asset_arg(parser):
        parser.add_argument("--asset", required=True, choices=sorted(ASSETS),
                            help="which obstacle prop to generate")

    args = art.standard_args("Generate a Cat Dash obstacle prop (FBX + 512 px atlas + .meta)",
                             extra=add_asset_arg, texture_size=512)
    if args.texture_size != 512:
        raise SystemExit("error: prop atlases are authored for 512 px")
    spec = ASSETS[args.asset]
    check_regions(args.asset, REGION_SETS[args.asset])
    art.reset_scene()

    part, extra = spec["builder"]()
    if part.tri_count() > 800:
        raise SystemExit(f"error: {args.asset} budget exceeded: {part.tri_count()} > 800")

    canvas = art.Canvas(args.texture_size, seed=int(zlib.crc32(args.asset.encode())) % 9973)
    spec["painter"](canvas)
    root = art.repo_root(Path(args.output).resolve())
    texture_path = Path("Assets/Art/Generated/Textures") / spec["texture"]
    canvas.save(root / texture_path)
    material = art.make_material(spec["material"], root / texture_path, spec["colour"],
                                 roughness=spec["roughness"])
    art.make_object(spec["object"], part, material=material, smooth=False)

    art.finish(spec["object"], args, texture_canvas=None, parts=[(spec["object"], part)],
               material_name=spec["material"], object_name=spec["object"],
               pivot="bottom centre (Blender 0,0,0 at the ground; Unity 0,0,0)",
               forward="barrier board faces Blender -Y => Unity +Z; crate/pot are symmetric",
               texture_name=spec["texture"], texture_written=True,
               extra={"proxy_kind": "obstacle", **extra,
                      "lane_fit": "sized against Lanes.LaneWidth = 1.8 m"})


if __name__ == "__main__":
    main()
