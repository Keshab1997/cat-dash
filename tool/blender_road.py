#!/usr/bin/env python3
"""Cat Dash — road segment generator (Agent B, batch CD-B1).

    blender --background --python tool/blender_road.py -- \
        --output Assets/Art/Generated/Road_Segment.fbx

One 12 m tileable street segment: 5.4 m asphalt (three Lanes.LaneWidth = 1.8 m
lanes), two 1.2 m sidewalks with a 0.15 m curb. One 1024 px atlas, one material,
<= 3000 triangles (this mesh is ~96).

Contract for Agent C's RoadLoop:
  * pivot at the driving surface, centred: the road top is Blender z=0 => Unity y=0,
    geometry runs Blender y in [-6, +6] => Unity z in [-6, +6];
  * place segments at z = n * 12 m (Unity) and the dashes/paving continue across
    the seam because every painted pattern period divides 12 m exactly;
  * lane centres are Unity x = -1.8 / 0 / +1.8, lane boundaries x = +/-0.9, so the
    dashed lines sit exactly on the boundaries;
  * the mesh runs through, so a dark ground plane is not needed; the 0.30 m deep
    slab is skirted, i.e. no holes appear when a segment is recycled.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

# --------------------------------------------------------------------------- #
# Palette (mirrors Assets/Art/PaletteSpec.cs)
# --------------------------------------------------------------------------- #
ASPHALT = art.srgb("#54555A")
ASPHALT_DARK = art.srgb("#46474C")
ASPHALT_LIGHT = art.srgb("#6A6B70")
LINE_WHITE = art.srgb("#F2E7C9")
PAVING = art.srgb("#E3D6B4")
PAVING_DARK = art.srgb("#C6B693")
PAVING_LIGHT = art.srgb("#F0E6CC")
CURB = art.srgb("#EFE5C8")
CURB_DARK = art.srgb("#C9BA97")
GUTTER = art.srgb("#4E4F54")

# --------------------------------------------------------------------------- #
# Geometry: all in metres, Blender space (x across, y along, z up)
# --------------------------------------------------------------------------- #
LANE_WIDTH = 1.8          # matches Lanes.LaneWidth in the frozen RunState.cs
ROAD_HALF = LANE_WIDTH * 3 * 0.5   # 2.7 m -> 5.4 m asphalt
SIDEWALK_WIDTH = 1.2
SEGMENT_LENGTH = 12.0
SLAB_DEPTH = 0.30
CURB_HEIGHT = 0.15

TEXTURE_SPAN_X = 2 * (ROAD_HALF + SIDEWALK_WIDTH)   # 7.8 m mapped across the atlas
DASH_LENGTH = 1.2
DASH_GAP = 0.8
PAVE_CELL = 0.4


def build_segment() -> art.Part:
    slab = art.box((2 * ROAD_HALF, SEGMENT_LENGTH, SLAB_DEPTH),
                   (0.0, 0.0, -SLAB_DEPTH * 0.5))
    left = art.box((SIDEWALK_WIDTH, SEGMENT_LENGTH, SLAB_DEPTH + CURB_HEIGHT),
                   (-(ROAD_HALF + SIDEWALK_WIDTH * 0.5), 0.0,
                    (CURB_HEIGHT - SLAB_DEPTH) * 0.5))
    right = left.transformed(offset=(2 * (ROAD_HALF + SIDEWALK_WIDTH * 0.5), 0.0, 0.0))
    part = art.combine([slab, left, right])
    return art.planar_uv(part, -TEXTURE_SPAN_X * 0.5, -SEGMENT_LENGTH * 0.5,
                         TEXTURE_SPAN_X * 0.5, SEGMENT_LENGTH * 0.5)


def paint_atlas(size: int) -> art.Canvas:
    canvas = art.Canvas(size, seed=23)
    total_width = ROAD_HALF * 2 + SIDEWALK_WIDTH * 2

    def u_of(x: float) -> float:
        return (x + total_width * 0.5) / total_width

    road_u0, road_u1 = u_of(-ROAD_HALF), u_of(ROAD_HALF)
    walk_inner_u = u_of(ROAD_HALF)
    paver = PAVE_CELL / total_width        # u step of one paving cell
    paver_v = PAVE_CELL / SEGMENT_LENGTH   # v step of one paving cell

    # -- sidewalks ------------------------------------------------------------- #
    canvas.fill(0.0, 0.0, 1.0, 1.0, PAVING)
    canvas.grain_tiled(0.0, 0.0, 1.0, 1.0, amount=0.06, block=64)
    cells_x = int(round((SIDEWALK_WIDTH) / PAVE_CELL))
    for side in (0.0, 1.0 - SIDEWALK_WIDTH / total_width):
        for i in range(cells_x + 1):
            u = side + i * paver
            canvas.blend(u - 0.0025, 0.0, u + 0.0025, 1.0, PAVING_DARK, 0.55)
        canvas.blend(side, 0.0, side + 0.012, 1.0, PAVING_LIGHT, 0.35)
    for i in range(int(round(SEGMENT_LENGTH / PAVE_CELL)) + 1):
        v = i * paver_v
        canvas.blend(0.0, v - 0.0018, 1.0, v + 0.0018, PAVING_DARK, 0.5)
    # curb face (maps onto the sidewalk's inner vertical edge) + outer edge
    canvas.blend(u_of(-ROAD_HALF) - 0.012, 0.0, u_of(-ROAD_HALF), 1.0, CURB, 1.0)
    canvas.blend(walk_inner_u, 0.0, walk_inner_u + 0.012, 1.0, CURB, 1.0)
    canvas.blend(0.0, 0.0, 0.008, 1.0, CURB_DARK, 0.8)
    canvas.blend(0.992, 0.0, 1.0, 1.0, CURB_DARK, 0.8)

    # -- asphalt --------------------------------------------------------------- #
    canvas.fill(road_u0, 0.0, road_u1, 1.0, ASPHALT)
    canvas.grain_tiled(road_u0, 0.0, road_u1, 1.0, amount=0.07, block=64)
    for centre, width, alpha in ((0.50, 0.055, 0.30), (0.28, 0.04, 0.22), (0.72, 0.04, 0.22)):
        canvas.blend(centre - width, 0.0, centre + width, 1.0, ASPHALT_DARK, alpha)
    canvas.speckle(road_u0, 0.0, road_u1, 1.0, ASPHALT_LIGHT, count=260, radius=0.0025,
                   alpha=0.35)
    canvas.speckle(road_u0, 0.0, road_u1, 1.0, ASPHALT_DARK, count=220, radius=0.0022,
                   alpha=0.35)
    # gutter strips next to the curbs (uniform along v, so the curb face stays clean)
    canvas.blend(u_of(-ROAD_HALF), 0.0, u_of(-ROAD_HALF) + 0.012, 1.0, GUTTER, 0.9)
    canvas.blend(u_of(ROAD_HALF) - 0.012, 0.0, u_of(ROAD_HALF), 1.0, GUTTER, 0.9)

    # -- dashed lane lines exactly on the lane boundaries (+/-0.9 m) ----------- #
    dash_v = DASH_LENGTH / SEGMENT_LENGTH
    period_v = (DASH_LENGTH + DASH_GAP) / SEGMENT_LENGTH
    line_half_u = 0.06 / total_width
    for boundary in (-LANE_WIDTH * 0.5, LANE_WIDTH * 0.5):
        u = u_of(boundary)
        canvas.blend(u - line_half_u - 0.003, 0.0, u + line_half_u + 0.003, 1.0,
                     ASPHALT_LIGHT, 0.25)
        v = 0.0
        while v < 1.0:
            canvas.fill(u - line_half_u, v, u + line_half_u, min(v + dash_v, 1.0), LINE_WHITE)
            v += period_v
    # solid edge line along both gutters (thin, keeps the safe path readable)
    for boundary in (-ROAD_HALF + 0.18, ROAD_HALF - 0.18):
        u = u_of(boundary)
        canvas.fill(u - 0.0045, 0.0, u + 0.0045, 1.0, LINE_WHITE)
    return canvas


def main() -> None:
    args = art.standard_args("Generate the Cat Dash road segment (FBX + atlas + .meta)")
    if args.texture_size != 1024:
        raise SystemExit("error: the road atlas is authored for 1024 px")
    art.reset_scene()

    part = build_segment()
    if part.tri_count() > 3000:
        raise SystemExit(f"error: road budget exceeded: {part.tri_count()} > 3000")

    canvas = paint_atlas(args.texture_size)
    root = art.repo_root(Path(args.output).resolve())
    texture_path = Path("Assets/Art/Generated/Textures") / f"Road_Segment_{args.texture_size}.png"
    canvas.save(root / texture_path)
    material = art.make_material("M_Road_Segment", root / texture_path, ASPHALT,
                                 roughness=0.92)
    art.make_object("Road_Segment", part, material=material, smooth=False)

    x0, y0, z0, x1, y1, z1 = part.bounds()
    art.finish("Road_Segment", args, texture_canvas=None,
               parts=[("Road_Segment", part)], material_name="M_Road_Segment",
               object_name="Road_Segment",
               pivot="driving surface, centred (Blender 0,0,0; slab extends 0.30 m below)",
               forward="runs along Blender Y => Unity Z",
               texture_name=f"Road_Segment_{args.texture_size}.png", texture_written=True,
               extra={"segment_length_m": SEGMENT_LENGTH,
                      "tile_step_unity_z": SEGMENT_LENGTH,
                      "road_width_m": lane_total(),
                      "sidewalk_width_m": SIDEWALK_WIDTH,
                      "curb_height_m": CURB_HEIGHT,
                      "size_m": [round(x1 - x0, 4), round(y1 - y0, 4), round(z1 - z0, 4)],
                      "collider": "ground: Agent C uses a collider-less walkway or a single "
                                  "BoxCollider (7.8 x 0.30 x 12.0) at y=-0.15 per segment; "
                                  "avoid a mesh collider for mobile cost",
                      "seam_safe": "dash period 2.0 m and paving cell 0.4 m both divide 12 m"})


def lane_total() -> float:
    return LANE_WIDTH * 3


if __name__ == "__main__":
    main()
