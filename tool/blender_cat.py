#!/usr/bin/env python3
"""Cat Dash — original low-poly tabby cat generator (Agent B, batch CD-B1).

    blender --background --python tool/blender_cat.py -- \
        --output Assets/Art/Generated/Cat.fbx

Rewritten against the owner-approved references (see docs/ASSETS.md):
  * docs/art/refs/cat-v2-stylized-3d-render.png — hero look: real-kitten proportions,
    golden coat with dense mackerel stripes, white chest/paws, teal eyes, long
    upcurved tail with a cream tip.
  * docs/art/refs/cat-v2-run-cycle-sheet.png — the four poses the rig contract must
    name (contact/down/up/air).
The references drive the *look only*: every vertex, polygon and UV below is written
by this script, and the atlas is painted procedurally. No AI image is ever used as
a mesh or a texture map.

Writes the FBX, its 1024 px sRGB atlas (Assets/Art/Generated/Textures/) and the
hand-written .meta files. One material, one texture, <= 4000 triangles.

Authoring axes: the cat faces Blender -Y, so after export (axis_forward='-Z',
axis_up='Y') it faces Unity +Z with +Y up. Pivot: ground between the paws.

Islands (each its own object, pivot on the joint that should drive it) stay the
6-bone rigid-rig contract of Assets/Art/RunCycleSpec.cs: no skinning this batch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

# --------------------------------------------------------------------------- #
# Palette — mirrors Assets/Art/PaletteSpec.cs (hero render sampled values)
# --------------------------------------------------------------------------- #
FUR = art.srgb("#D9944F")          # golden base coat (sampled from the hero render)
FUR_LIGHT = art.srgb("#E8AC6B")    # lit top of the coat / ear outer rim
FUR_STRIPE = art.srgb("#9A4A15")   # mackerel stripe (sampled #7E3711, lifted for albedo)
FUR_STRIPE_DK = art.srgb("#7A3A10")
CREAM = art.srgb("#FBF1DE")        # chest, muzzle, paw socks
CREAM_WARM = art.srgb("#F3E0C0")
NOSE_PINK = art.srgb("#DE8A85")
EAR_PINK = art.srgb("#DD9490")
EYE_TEAL = art.srgb("#2FA48C")     # iris (sampled #32927C, lifted for albedo)
EYE_TEAL_DK = art.srgb("#1B7365")
EYE_PUPIL = art.srgb("#12201F")
EYE_BACK = art.srgb("#4A2E1A")     # hidden hemisphere inside the head
EYE_RIM = art.srgb("#3B2415")      # dark ring around the iris
EYE_SCLERA = art.srgb("#F7F2E7")   # visible eyeball white
WHITE = art.srgb("#FFFFFF")

# --------------------------------------------------------------------------- #
# Atlas regions — every edge lands on a 64 px multiple so tiled grain stays seamless
# --------------------------------------------------------------------------- #
R_BODY = (0.000, 0.000, 0.625, 0.375)    # 640 x 384 px
R_HEAD = (0.625, 0.000, 1.000, 0.375)    # 384 x 384 px
R_LEG = (0.000, 0.375, 0.250, 0.625)     # 256 x 256 px
R_TAIL = (0.250, 0.375, 0.625, 0.625)    # 384 x 256 px
R_EAR = (0.625, 0.375, 0.875, 0.625)     # 256 x 256 px
R_EYE = (0.875, 0.500, 1.000, 0.625)     # 128 x 128 px
R_MUZZLE = (0.000, 0.625, 0.375, 1.000)  # 384 x 384 px
R_FUR_SPARE = (0.625, 0.625, 1.000, 1.000)  # plain golden fallback


def rect(region, u_rel, v_rel):
    """A relative (u, v) inside a region -> absolute atlas coordinate."""
    return (region[0] + (region[2] - region[0]) * u_rel,
            region[1] + (region[3] - region[1]) * v_rel)


def region_uv(region, u_rel0, v_rel0, u_rel1, v_rel1):
    u0, v0 = rect(region, u_rel0, v_rel0)
    u1, v1 = rect(region, u_rel1, v_rel1)
    return (u0, v0, u1, v1)


# --------------------------------------------------------------------------- #
# Atlas painting
# --------------------------------------------------------------------------- #
def paint_body(canvas: art.Canvas) -> None:
    """Torso tile. Ring mapping: u_rel 0 = belly, 0.5 = spine, 1 = belly again
    (the ring wraps, so the belly wash is painted against both u edges); v goes
    from the tail end (0) to the chest (1)."""
    u0, v0, u1, v1 = R_BODY
    span = u1 - u0
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)

    # mackerel stripes: constant-v bands = rings around the torso, densest mid-flank
    stripe_rows = (0.045, 0.125, 0.205, 0.285, 0.365, 0.445, 0.525, 0.605, 0.685, 0.765, 0.845)
    for index, row in enumerate(stripe_rows):
        v = v0 + (v1 - v0) * row
        half = 0.016 if index % 2 else 0.021
        colour = FUR_STRIPE if index % 3 else FUR_STRIPE_DK
        canvas.bands_y(u0, u1, [v], (v1 - v0) * half, colour, alpha=0.95)

    # white chest and belly: u edges (belly) plus a wash towards the chest end
    for edge in (u0, u1 - span * 0.18):
        canvas.blend(edge, v0, edge + span * 0.15, v1, CREAM, 0.90)
        canvas.blend(edge + span * 0.15, v0, edge + span * 0.20, v1, CREAM, 0.40)
    for edge in (u0, u1 - span * 0.13):
        canvas.blend(edge, v1 - (v1 - v0) * 0.34, edge + span * 0.13, v1, CREAM, 0.55)
        canvas.blend(edge, v1 - (v1 - v0) * 0.18, edge + span * 0.13, v1, CREAM, 0.80)

    # mouse-shaped blaze on the back (owner note: "পিঠে mouse-shaped blaze"):
    # an outlined oval body with a thin tapering tail running towards the hips,
    # straddling the spine (u_rel 0.5) on the shoulder/upper back.
    centre_u = u0 + span * 0.5
    body_v = v0 + (v1 - v0) * 0.44
    du = span * 0.048
    dv = (v1 - v0) * 0.105
    canvas.ellipse(centre_u, body_v, du, dv, FUR_STRIPE_DK, 0.85)             # outline
    canvas.ellipse(centre_u, body_v, du * 0.86, dv * 0.82, CREAM, 0.85)       # mouse body
    canvas.ellipse(centre_u, body_v + dv * 0.35, du * 0.30, dv * 0.28, FUR_LIGHT, 0.7)  # ear
    canvas.ellipse(centre_u - du * 0.55, body_v + dv * 0.55, du * 0.26, dv * 0.26,
                   FUR_LIGHT, 0.7)                                                   # ear
    canvas.ellipse(centre_u + du * 0.42, body_v + dv * 0.18, du * 0.10, dv * 0.10,
                   EYE_PUPIL, 0.6)                                                    # eye
    canvas.segment(centre_u + du * 0.30, body_v - dv * 0.75,
                   centre_u + du * 0.55, body_v - dv * 3.1, FUR_STRIPE_DK, 0.0045,
                   alpha=0.75)                                                        # tail
    tail_start = body_v - dv * 0.9
    for index, (frac, thickness) in enumerate(((0.30, 0.0060), (0.55, 0.0040), (0.78, 0.0022))):
        next_frac = (0.55, 0.78, 1.0)[index]
        canvas.segment(centre_u + du * 0.55, tail_start - (v1 - v0) * frac,
                       centre_u + du * 0.30, tail_start - (v1 - v0) * next_frac,
                       FUR_STRIPE_DK, thickness, alpha=0.55)

    # spare tile keeps plain golden fur so nothing samples an unpainted pixel
    su0, sv0, su1, sv1 = R_FUR_SPARE
    canvas.fill(su0, sv0, su1, sv1, FUR)
    canvas.grain_tiled(su0, sv0, su1, sv1, amount=0.045, block=64)


def paint_head(canvas: art.Canvas) -> None:
    """Head tile. u_rel 0 = back of the head, 0.5 = the face, v_rel 0 = chin,
    1 = crown. The eyes are geometry (EyeL/EyeR islands); this paints the fur
    around them: white muzzle/chin mask, dark eyeliner rings, tabby "M" brow
    stripes, cheek strokes and crown stripes."""
    u0, v0, u1, v1 = R_HEAD
    span_u, span_v = u1 - u0, v1 - v0
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)

    # white/cream mask over the chin, muzzle base and lower cheeks
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.070), span_u * 0.098, span_v * 0.070, CREAM, 0.95)
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.125), span_u * 0.078, span_v * 0.052, CREAM, 0.50)
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.085), span_u * 0.052, span_v * 0.042, CREAM_WARM, 0.45)

    # No painted eyeliner: EyeL/EyeR carry their own dark rim, and a second painted
    # ring around the socket read as smudges on the fur.

    # tabby "M": vertical stripes between and above the eyes
    for u_rel in (0.460, 0.500, 0.540):
        canvas.bands_x(v0 + span_v * 0.56, v0 + span_v * 0.92,
                       [u0 + span_u * u_rel], span_u * 0.011, FUR_STRIPE, alpha=0.98)
    for side in (-1, 1):
        canvas.segment(*rect(R_HEAD, 0.50 + side * 0.040, 0.58),
                       *rect(R_HEAD, 0.50 + side * 0.150, 0.70),
                       FUR_STRIPE, 0.0055, alpha=0.8)

    # cheek strokes
    for side in (-1, 1):
        for index, (u_a, v_a, u_b, v_b) in enumerate(
                ((0.295, 0.360, 0.205, 0.300), (0.300, 0.415, 0.215, 0.360))):
            canvas.segment(*rect(R_HEAD, 0.50 + side * u_a, v_a),
                           *rect(R_HEAD, 0.50 + side * u_b, v_b),
                           FUR_STRIPE, 0.0038 - index * 0.0006, alpha=0.55)

    # crown stripes (kept off the u wrap seam at 0/1, which is the nape)
    for u_rel in (0.022, 0.978, 0.080, 0.920, 0.165, 0.835):
        canvas.bands_x(v0 + span_v * 0.74, v0 + span_v * 0.96,
                       [u0 + span_u * u_rel], span_u * 0.012, FUR_STRIPE, alpha=0.75)


def paint_legs(canvas: art.Canvas) -> None:
    """Leg tile. v = 0 paw -> 1 hip, so stripes are rings around the leg."""
    u0, v0, u1, v1 = R_LEG
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)
    canvas.vgrad(u0, v0, u1, v0 + (v1 - v0) * 0.16, CREAM, CREAM)
    canvas.vgrad(u0, v0 + (v1 - v0) * 0.16, u1, v0 + (v1 - v0) * 0.30, CREAM, FUR)
    for row, alpha in ((0.38, 0.85), (0.56, 0.90), (0.74, 0.95), (0.90, 0.90)):
        canvas.bands_y(u0, u1, [v0 + (v1 - v0) * row], (v1 - v0) * 0.028, FUR_STRIPE, alpha=alpha)


def paint_tail(canvas: art.Canvas) -> None:
    """Tail tile. v = 0 base -> 1 tip: rings along the tail, cream tip."""
    u0, v0, u1, v1 = R_TAIL
    span = v1 - v0
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)
    for row in (0.06, 0.15, 0.24, 0.33, 0.42, 0.51, 0.60):
        canvas.bands_y(u0, u1, [v0 + span * row], span * 0.030, FUR_STRIPE, alpha=0.92)
    canvas.vgrad(u0, v0 + span * 0.68, u1, v0 + span * 0.80, FUR, CREAM)
    canvas.vgrad(u0, v0 + span * 0.80, u1, v1, CREAM, CREAM)


def paint_ears(canvas: art.Canvas) -> None:
    """Ear tile. u_rel 0.5 faces forward (inner ear), v runs base -> tip."""
    u0, v0, u1, v1 = R_EAR
    span_u, span_v = u1 - u0, v1 - v0
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)
    canvas.bands_x(v0, v1, [u0 + span_u * 0.5], span_u * 0.072, EAR_PINK, alpha=1.0)
    canvas.bands_x(v0, v1, [u0 + span_u * 0.5], span_u * 0.046, art.srgb("#F3BFC2"), alpha=1.0)
    for edge in (0.428, 0.572):
        canvas.bands_x(v0, v1, [u0 + span_u * edge], span_u * 0.006, CREAM, alpha=0.55)
    canvas.blend(u0 + span_u * 0.40, v0, u0 + span_u * 0.60, v0 + span_v * 0.18,
                 CREAM, 0.45)


def paint_eye(canvas: art.Canvas) -> None:
    """Eye tile. u_rel 0.5 faces outward; a sphere maps 360 deg around u but only
    180 deg across v, so the iris is authored in degrees and scaled per axis."""
    u0, v0, u1, v1 = R_EYE
    span_u, span_v = u1 - u0, v1 - v0
    # The visible half of the eyeball must read as an eye from every angle: sclera
    # around the iris, and the dark backing only on the rear cap (which sits inside
    # the head). Painting it dark all over made side views look like a dead eye.
    canvas.fill(u0, v0, u1, v1, EYE_SCLERA)
    canvas.bands_x(v0, v1, [u0 + span_u * 0.045], span_u * 0.075, EYE_BACK, alpha=1.0)
    canvas.bands_x(v0, v1, [u0 + span_u * 0.955], span_u * 0.075, EYE_BACK, alpha=1.0)
    cu, cv = rect(R_EYE, 0.5, 0.5)

    def disk(radius_deg, colour, alpha=1.0, du_deg=0.0, dv_deg=0.0):
        canvas.ellipse(cu + span_u * du_deg / 360.0, cv + span_v * dv_deg / 180.0,
                       span_u * radius_deg / 360.0, span_v * radius_deg / 180.0,
                       colour, alpha)

    # The reference eye is nearly all iris inside a dark rim with a bright catchlight.
    # It has to wrap well past 90 deg: a narrower iris left the eye reading as a white
    # ball with a teal dot whenever the head turned away from the camera.
    # 78 deg keeps the iris inside the 90 deg the sphere exposes in v (a 130 deg iris
    # wrapped past the pole and read as a flat teal cap), while still being large
    # enough that the eye does not look like a white ball from the side.
    disk(88.0, EYE_RIM, 1.0)
    disk(84.0, EYE_TEAL_DK)
    disk(78.0, EYE_TEAL)
    disk(40.0, EYE_TEAL, 1.0)
    disk(26.0, EYE_PUPIL)
    disk(9.0, WHITE, 0.95, du_deg=-16.0, dv_deg=14.0)
    disk(4.0, WHITE, 0.9, du_deg=-20.0, dv_deg=16.0)


def paint_muzzle(canvas: art.Canvas) -> None:
    """Muzzle tile: cream pad plus a pink nose patch the nose wedge samples."""
    u0, v0, u1, v1 = R_MUZZLE
    span_u, span_v = u1 - u0, v1 - v0
    canvas.fill(u0, v0, u1, v1, CREAM)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.035, block=64)
    canvas.blend(u0, v0, u1, v0 + span_v * 0.10, CREAM_WARM, 0.6)
    canvas.ellipse(*rect(R_MUZZLE, 0.5, 0.5), span_u * 0.30, span_v * 0.30, CREAM_WARM, 0.5)
    # pink nose patch in the upper-right corner of the tile
    canvas.fill(u0 + span_u * 0.62, v0 + span_v * 0.80, u1, v1, NOSE_PINK)
    canvas.blend(u0 + span_u * 0.62, v0 + span_v * 0.80, u1, v0 + span_v * 0.86,
                 art.srgb("#C96A74"), 0.5)
    # mouth line under the nose
    # No mouth line: at this scale it read as a smudge under the nose, and the muzzle
    # pad's own shading already separates nose from chin.


# --------------------------------------------------------------------------- #
# Geometry (metres; Blender space: +X right, -Y forward, +Z up)
# --------------------------------------------------------------------------- #
BODY_RINGS = ((0.200, 0.082), (0.120, 0.118), (0.020, 0.124),
              (-0.080, 0.120), (-0.150, 0.114), (-0.190, 0.096))
BODY_SEGMENTS = 18

# joint pivots (Blender space, metres) — shared by the mesh build and the report
JOINTS = {
    "CatDash_Cat": (0.0, 0.0, 0.0),
    "Body": (0.0, -0.020, 0.245),
    "Neck": (0.0, -0.145, 0.280),
    "Head": (0.0, -0.260, 0.365),
    "EyeL": (-0.0510, -0.3835, 0.4160),
    "EyeR": (0.0510, -0.3835, 0.4160),
    "Muzzle": (0.0, -0.355, 0.348),
    "EarL": (-0.058, -0.283, 0.448),
    "EarR": (0.058, -0.283, 0.448),
    "LegFrontL": (-0.052, -0.150, 0.200),
    "LegFrontR": (0.052, -0.150, 0.200),
    "LegHindL": (-0.062, 0.140, 0.215),
    "LegHindR": (0.062, 0.140, 0.215),
    "Tail": (0.0, 0.245, 0.285),
}


def build_body() -> art.Part:
    """Torso: chunky kitten barrel with haunches at the hip end. Ring u_rel 0 must
    be the belly (the atlas tile paints the white belly along both u edges), so the
    phase is chosen from the emitted vertices rather than assumed."""
    u0, v0, u1, v1 = R_BODY
    path = [(0.0, y, 0.245 if -0.1 < y < 0.2 else 0.240) for y, _ in BODY_RINGS]
    radii = [radius for _, radius in BODY_RINGS]
    ring_v = [v0 + (v1 - v0) * t for t in (0.02, 0.20, 0.40, 0.60, 0.80, 0.98)]
    axis_z = path[2][2]
    part = None
    for phase in (0.0, 3.141592653589793):
        candidate = art.tube(path, radii, segments=BODY_SEGMENTS, u_range=(u0, u1),
                             ring_v=ring_v, phase=phase, hint=(1.0, 0.0, 0.0), squash=1.0)
        if candidate.verts[0][2] < axis_z:   # ring 0, segment 0 sits under the spine
            part = candidate
            break
    if part is None:
        raise SystemExit("error: could not orient the torso belly/back UV seam")
    span = u1 - u0
    wrapped = [[((u0 + span * (0.5 * (((u - u0) / span + 0.5) % 1.0))), v)
                for u, v in face] for face in part.face_uvs]
    return art.Part(part.verts, part.faces, wrapped)


def build_neck() -> art.Part:
    return art.tube([(0.0, -0.140, 0.275), (0.0, -0.190, 0.310), (0.0, -0.232, 0.345)],
                    [0.090, 0.084, 0.078], segments=12,
                    u_range=(R_FUR_SPARE[0], R_FUR_SPARE[2]),
                    ring_v=[R_FUR_SPARE[1] + (R_FUR_SPARE[3] - R_FUR_SPARE[1]) * t
                            for t in (0.0, 0.5, 1.0)],
                    hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_head() -> art.Part:
    """Head sphere plus cheek pads (one island, one bone)."""
    # A single smooth sphere: an earlier cheek-pad pair poked out of the silhouette and
    # dragged a stray white blob under the eye, so the cheeks are painted (the cream
    # mask) instead of modelled.
    return art.sphere((0.0, -0.305, 0.395), (0.106, 0.118, 0.104),
                      segments=24, rows=14, u_range=(R_HEAD[0], R_HEAD[2]),
                      v_range=(R_HEAD[1], R_HEAD[3]), phase=3.141592653589793)


EYE_YAW = -0.12  # radians: how far the left eye looks outward (right eye mirrors it)


def build_eyes() -> tuple[art.Part, art.Part]:
    """Big glossy eye spheres. The iris is painted at pattern u_rel 0.5, so phase=pi
    lands it on Blender -Y (straight ahead); EYE_YAW then turns the left eye outward
    and the right eye is that finished eye mirrored across X."""
    proto = art.sphere((0.0, 0.0, 0.0), (0.039, 0.035, 0.040),
                       segments=14, rows=9, u_range=(R_EYE[0], R_EYE[2]),
                       v_range=(R_EYE[1], R_EYE[3]), phase=3.141592653589793)
    left = proto.transformed(offset=JOINTS["EyeL"], rot_z=EYE_YAW)
    return left, left.mirrored_x()


def build_muzzle() -> art.Part:
    """Pink nose wedge only.

    An earlier version also modelled a cream muzzle pad, but a separate pad sphere
    always came out as either a hanging blob or a horizontal "grimace" band. The
    muzzle is therefore painted (the cream mask on the head tile) and only the nose
    is geometry, sitting on the face where the head ellipsoid lets it protrude.
    """
    nose_uv = region_uv(R_MUZZLE, 0.70, 0.86, 0.96, 0.99)
    return art.pyramid((0.0, -0.404, 0.344), (0.028, 0.016), (0.0, -0.414, 0.337),
                       nose_uv, nose_uv)


def build_ear(side: int) -> art.Part:
    """Rounded triangular ear: a short tapered cone (base -> rounded tip) whose
    forward face samples the pink inner-ear band of the ear tile."""
    base = (side * 0.058, -0.283, 0.448)
    path = [base, (base[0] + side * 0.012, base[1] - 0.003, base[2] + 0.052),
            (base[0] + side * 0.020, base[1] - 0.005, base[2] + 0.097)]
    radii = [0.060, 0.036, 0.011]
    u0, v0, u1, v1 = R_EAR
    return art.tube(path, radii, segments=10, u_range=(u0, u1),
                    ring_v=[v0 + (v1 - v0) * t for t in (0.0, 0.45, 0.95)],
                    phase=3.141592653589793, hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_leg(side: int, front: bool) -> art.Part:
    """Front leg: near-straight. Hind leg: hip -> hock -> paw, so the bent hock of
    the reference reads in silhouette. Both end on a flat ring at y=0."""
    if front:
        x, y, top = side * 0.052, -0.150, 0.200
        path = [(x, y, top), (x, y - 0.004, top * 0.55), (x, y - 0.004, 0.0)]
        radii = [0.046, 0.032, 0.034]
    else:
        x = side * 0.062
        path = [(x, 0.140, 0.215), (x, 0.196, 0.115), (x, 0.196, 0.0)]
        radii = [0.062, 0.038, 0.032]
    u0, v0, u1, v1 = R_LEG
    return art.tube(path, radii, segments=10, u_range=(u0, u1),
                    ring_v=[v1, v0 + (v1 - v0) * 0.5, v0], phase=3.141592653589793,
                    hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_tail() -> art.Part:
    """Long tail curving up and forward, cream tip last ~20% (atlas v)."""
    path = [(0.0, 0.245, 0.285), (0.0, 0.290, 0.390), (0.0, 0.282, 0.500),
            (0.0, 0.240, 0.600), (0.0, 0.186, 0.660)]
    radii = [0.043, 0.035, 0.029, 0.023, 0.018]
    u0, v0, u1, v1 = R_TAIL
    ring_v = [v0 + (v1 - v0) * t for t in (0.0, 0.24, 0.48, 0.72, 0.98)]
    return art.tube(path, radii, segments=12, u_range=(u0, u1), ring_v=ring_v,
                    phase=3.141592653589793, hint=(1.0, 0.0, 0.0), caps=(True, True))


def main() -> None:
    args = art.standard_args("Generate the original Cat Dash tabby cat (FBX + atlas + .meta)")
    if args.texture_size != 1024:
        raise SystemExit("error: the cat atlas is authored for 1024 px (budget ceiling)")
    if "cat" not in args.output.lower():
        raise SystemExit("error: refusing to write the cat to a path without 'cat' in it")
    art.reset_scene()

    canvas = art.Canvas(args.texture_size, seed=17)
    for painter in (paint_body, paint_head, paint_legs, paint_tail, paint_ears, paint_eye,
                    paint_muzzle):
        painter(canvas)
    root = art.repo_root(Path(args.output).resolve())
    texture_path = Path("Assets/Art/Generated/Textures") / f"Cat_{args.texture_size}.png"
    canvas.save(root / texture_path)
    material = art.make_material("M_Cat_Fur", root / texture_path, FUR, roughness=1.0)

    joints = JOINTS
    eye_left, eye_right = build_eyes()
    build = [
        ("Body", build_body(), "Body"),
        ("Neck", build_neck(), "Neck"),
        ("Head", build_head(), "Head"),
        ("EyeL", eye_left, "EyeL"),
        ("EyeR", eye_right, "EyeR"),
        ("Muzzle", build_muzzle(), "Muzzle"),
        ("EarL", build_ear(-1), "EarL"),
        ("EarR", build_ear(1), "EarR"),
        ("LegFrontL", build_leg(-1, True), "LegFrontL"),
        ("LegFrontR", build_leg(1, True), "LegFrontR"),
        ("LegHindL", build_leg(-1, False), "LegHindL"),
        ("LegHindR", build_leg(1, False), "LegHindR"),
        ("Tail", build_tail(), "Tail"),
    ]

    root_empty = art.make_empty("CatDash_Cat")
    parts = []
    for name, part, joint_name in build:
        joint = joints[joint_name]
        art.make_object(name, part.transformed(offset=(-joint[0], -joint[1], -joint[2])),
                        material=material, smooth=True, parent=root_empty).location = joint
        parts.append((name, part))

    total = sum(part.tri_count() for _, part in parts)
    if total > 4000:
        raise SystemExit(f"error: cat budget exceeded: {total} triangles > 4000")

    art.finish("Cat", args, texture_canvas=None, parts=parts, material_name="M_Cat_Fur",
               object_name="CatDash_Cat",
               pivot="ground level, centred between the paws (Blender 0,0,0; Unity 0,0,0)",
               forward="faces Blender -Y => Unity +Z",
               texture_name=f"Cat_{args.texture_size}.png", texture_written=True,
               extra={"parts_pivots": {k: [round(c, 4) for c in v] for k, v in joints.items()},
                      "atlas_regions": {name: list(region) for name, region in
                                        (("body", R_BODY), ("head", R_HEAD), ("leg", R_LEG),
                                         ("tail", R_TAIL), ("ear", R_EAR), ("eye", R_EYE),
                                         ("muzzle", R_MUZZLE), ("fur_spare", R_FUR_SPARE))},
                      "references": ["docs/art/refs/cat-v2-stylized-3d-render.png",
                                     "docs/art/refs/cat-v2-run-cycle-sheet.png"],
                      "flags": ["white chest/belly", "mackerel stripe rings",
                                "mouse-shaped blaze on the back", "pink inner ears",
                                "pink nose", "teal eyes with white highlight",
                                "cream paw socks", "cream tail tip"],
                      "rig": "no skinning this batch; see Assets/Art/RunCycleSpec.cs"})
    print(f"note: cat islands: {[name for name, _, _ in build]}")


if __name__ == "__main__":
    main()
