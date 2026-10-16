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

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402

bpy = art.bpy  # the same lazy Blender handle the library holds (None outside Blender)

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
    """Torso tile. Ring mapping: u_rel 0 and 1 are the BELLY (the ring seam, so both tile
    edges are the same place on the model and the white belly wash is painted against
    both), u_rel 0.5 is the SPINE (where the "mouse" blaze goes); v runs from the tail
    end (0) to the chest (1)."""
    u0, v0, u1, v1 = R_BODY
    span = u1 - u0
    canvas.fill(u0, v0, u1, v1, FUR)
    canvas.grain_tiled(u0, v0, u1, v1, amount=0.05, block=64)

    # mackerel stripes: constant-v bands = rings around the torso, densest mid-flank
    stripe_rows = (0.040, 0.112, 0.184, 0.256, 0.328, 0.400, 0.472, 0.544, 0.616,
                   0.688, 0.760, 0.832, 0.904)
    # Mackerel stripes are broken, not continuous rings: each stripe is drawn as 2-3
    # segments of slightly different width with gaps between them, and every third
    # stripe skips its middle segment. A uniform ring set made the cat look like a
    # striped tube sock rather than a tabby.
    segments = ((0.015, 0.295), (0.345, 0.640), (0.690, 0.985))
    for index, row in enumerate(stripe_rows):
        v = v0 + (v1 - v0) * row
        base_half = 0.0085 if index % 2 else 0.0115
        colour = FUR_STRIPE if index % 3 else FUR_STRIPE_DK
        for seg_index, (u_start, u_end) in enumerate(segments):
            if index % 3 == 2 and seg_index == 1:
                continue  # the gap that keeps the pattern from reading as a ring
            jitter = (0.85, 1.0, 1.15)[(index + seg_index) % 3]
            canvas.bands_y(u0 + span * u_start, u0 + span * u_end, [v],
                           (v1 - v0) * base_half * jitter, colour, alpha=1.0)

    # white chest and belly: u edges (belly) plus a wash towards the chest end
    for edge in (u0, u1 - span * 0.18):
        canvas.blend(edge, v0, edge + span * 0.15, v1, CREAM, 0.90)
        canvas.blend(edge + span * 0.15, v0, edge + span * 0.20, v1, CREAM, 0.40)
    for edge in (u0, u1 - span * 0.13):
        canvas.blend(edge, v1 - (v1 - v0) * 0.34, edge + span * 0.13, v1, CREAM, 0.55)
        canvas.blend(edge, v1 - (v1 - v0) * 0.18, edge + span * 0.13, v1, CREAM, 0.80)

    # Mouse-shaped blaze on the back (owner note: "পিঠে mouse-shaped blaze"). Drawn as a
    # readable mouse SILHOUETTE — outlined body, head, two ears and a long tail — because an
    # earlier plain cream oval read as a white smudge/band rather than a mouse.
    centre_u = u0 + span * 0.5
    mouse_u, mouse_v = centre_u, v0 + (v1 - v0) * 0.62   # mid-back, clear of neck and hips
    du = span * 0.062
    dv = (v1 - v0) * 0.135

    def mouse_spot(du_scale, dv_scale, offset_u, offset_v, colour, alpha):
        canvas.ellipse(mouse_u + du * offset_u, mouse_v + dv * offset_v,
                       du * du_scale, dv * dv_scale, colour, alpha)

    outline, fill = FUR_STRIPE_DK, CREAM
    # tail first (drawn "under" the body): long, thin, curving towards the hips
    canvas.segment(mouse_u + du * 0.62, mouse_v - dv * 0.72,
                   mouse_u + du * 0.30, mouse_v - dv * 2.9, outline, 0.0060, alpha=0.85)
    mouse_spot(1.00, 0.62, 0.0, 0.0, outline, 0.95)      # body outline
    mouse_spot(0.90, 0.54, 0.0, 0.0, fill, 1.0)          # body
    mouse_spot(0.42, 0.36, 0.86, 0.22, outline, 0.95)    # head outline
    mouse_spot(0.34, 0.28, 0.88, 0.22, fill, 1.0)        # head
    mouse_spot(0.26, 0.22, 0.74, 0.52, outline, 0.95)    # ear (near)
    mouse_spot(0.17, 0.14, 0.75, 0.52, fill, 1.0)
    mouse_spot(0.24, 0.20, 1.00, 0.42, outline, 0.90)    # ear (far)
    mouse_spot(0.15, 0.12, 1.01, 0.42, fill, 1.0)
    mouse_spot(0.07, 0.05, 0.97, 0.20, EYE_PUPIL, 0.85)  # eye
    mouse_spot(0.10, 0.08, 0.50, 0.30, FUR_LIGHT, 0.45)  # shoulder shading on the body

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
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.085), span_u * 0.108, span_v * 0.085, CREAM, 0.95)
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.150), span_u * 0.085, span_v * 0.060, CREAM, 0.50)
    canvas.ellipse(*rect(R_HEAD, 0.50, 0.100), span_u * 0.058, span_v * 0.050, CREAM_WARM, 0.45)

    # No painted eyeliner: EyeL/EyeR carry their own dark rim, and a second painted
    # ring around the socket read as smudges on the fur.

    # Tabby "M" above the eyes: two short strokes per side, angled outward, plus a
    # centre pair that stops well above the brow. The centre stroke used to run from
    # v_rel 0.56 to 0.92, which painted one dark line straight down the middle of the
    # face and read as a "crack" in the render.
    for side in (-1, 1):
        canvas.segment(*rect(R_HEAD, 0.50 + side * 0.032, 0.870),
                       *rect(R_HEAD, 0.50 + side * 0.070, 0.735),
                       FUR_STRIPE, 0.0042, alpha=0.70)
        canvas.segment(*rect(R_HEAD, 0.50 + side * 0.092, 0.885),
                       *rect(R_HEAD, 0.50 + side * 0.128, 0.750),
                       FUR_STRIPE, 0.0038, alpha=0.65)

    # cheek strokes
    for side in (-1, 1):
        for index, (u_a, v_a, u_b, v_b) in enumerate(
                ((0.290, 0.330, 0.235, 0.295), (0.295, 0.375, 0.245, 0.340))):
            canvas.segment(*rect(R_HEAD, 0.50 + side * u_a, v_a),
                           *rect(R_HEAD, 0.50 + side * u_b, v_b),
                           FUR_STRIPE, 0.0030 - index * 0.0005, alpha=0.45)

    # crown stripes (kept off the u wrap seam at 0/1, which is the nape)
    for u_rel in (0.055, 0.945):
        canvas.bands_x(v0 + span_v * 0.78, v0 + span_v * 0.92,
                       [u0 + span_u * u_rel], span_u * 0.009, FUR_STRIPE, alpha=0.40)


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
    for row in (0.045, 0.115, 0.185, 0.255, 0.325, 0.395, 0.465, 0.535, 0.605):
        canvas.bands_y(u0, u1, [v0 + span * row], span * 0.022, FUR_STRIPE, alpha=1.0)
    canvas.vgrad(u0, v0 + span * 0.66, u1, v0 + span * 0.76, FUR, CREAM)
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
    disk(96.0, EYE_RIM, 1.0)
    disk(92.0, EYE_TEAL_DK)
    disk(86.0, EYE_TEAL)
    disk(44.0, EYE_TEAL, 1.0)
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
    "EyeL": (-0.0530, -0.3830, 0.4155),
    "EyeR": (0.0530, -0.3830, 0.4155),
    "Muzzle": (0.0, -0.355, 0.348),
    "EarL": (-0.058, -0.283, 0.448),
    "EarR": (0.058, -0.283, 0.448),
    "LegFrontL": (-0.052, -0.150, 0.200),
    "LegFrontR": (0.052, -0.150, 0.200),
    "LegHindL": (-0.062, 0.140, 0.215),
    "LegHindR": (0.062, 0.140, 0.215),
    "Tail": (0.0, 0.245, 0.285),
}


# --------------------------------------------------------------------------- #
# Rig — six bones, one island per bone, four-pose run cycle
# Mirrors Assets/Art/RunCycleSpec.cs (the contract). Kept as plain numbers here because
# this generator is Python, not C#; tool/blender_verify_assets.py re-derives the clip from
# the same formulas and checks the exported FBX against the contract values.
# --------------------------------------------------------------------------- #
RIG_NAME = "CatDash_Rig"
CLIP_NAME = "Run"                    # RunCycleSpec.ClipName
FRAME_COUNT = 12                     # RunCycleSpec.FrameCount
POSE_COUNT = 4                       # RunCycleSpec.PoseCount
SAMPLE_RATE = 24                     # RunCycleSpec.SampleRate
POSE_PHASE = (0.0, 0.25, 0.5, 0.75)  # RunCycleSpec.PosePhase
LEG_SWING_DEGREES = 28.0             # RunCycleSpec.LegSwingDegrees
HIND_PHASE_OFFSET = 0.5              # RunCycleSpec.HindPhaseOffset
BODY_BOB_METRES = 0.015              # RunCycleSpec.BodyBobMetres
BODY_BOB_CONTACT_EPSILON = 1e-6      # RunCycleSpec.BodyBobContactEpsilon
BODY_BOB_FREQUENCY = 2.0             # RunCycleSpec.BodyBobFrequencyMultiplier
TAIL_SWAY_DEGREES = 8.0              # RunCycleSpec.TailSwayDegrees
TAIL_PHASE_LAG = 0.125               # RunCycleSpec.TailPhaseLag
HEAD_STEADY_DEGREES = 2.0            # RunCycleSpec.HeadSteadyDegrees
# The pose frames are 3 apart, and the FBX exporter samples every BAKE_STEP-th frame, so the
# exported clip keys exactly the pose frames plus the closing frame (never every frame).
POSE_SPACING = FRAME_COUNT // POSE_COUNT

# (bone, head, tail, parent) in authoring axes. Order is RunCycleSpec.BoneNames; Root is
# first because the vertical bob is keyed on it. Root points straight up, which makes its
# own axis the vertical one; the leg bones point down, so a pitch about world X swings them
# fore/aft; the tail bone points up-and-back so a yaw about world Z sways it side to side.
RIG_BONES = (
    ("Root", (0.0, 0.0, 0.0), (0.0, 0.0, 0.215), None),
    ("Body", (0.0, 0.140, 0.215), (0.0, -0.150, 0.245), "Root"),
    ("Head", (0.0, -0.260, 0.365), (0.0, -0.400, 0.365), "Body"),
    ("FrontLegs", (0.0, -0.150, 0.200), (0.0, -0.150, 0.010), "Body"),
    ("HindLegs", (0.0, 0.140, 0.215), (0.0, 0.170, 0.010), "Body"),
    ("Tail", (0.0, 0.245, 0.285), (0.0, 0.318, 0.460), "Body"),
)

# island -> driving bone, straight from RunCycleSpec.BoneNames' comments
# ("one island = one bone, weight 1.0"): rigid parenting, no skinning, no re-topology.
ISLAND_BONES = {
    "Body": "Body", "Neck": "Body",
    "Head": "Head", "EyeL": "Head", "EyeR": "Head", "Muzzle": "Head",
    "EarL": "Head", "EarR": "Head",
    "LegFrontL": "FrontLegs", "LegFrontR": "FrontLegs",
    "LegHindL": "HindLegs", "LegHindR": "HindLegs",
    "Tail": "Tail",
}


def wrap01(cycles: float) -> float:
    phase = cycles % 1.0
    return phase + 1.0 if phase < 0.0 else phase


def body_bob_metres_at(cycles: float) -> float:
    """RunCycleSpec.BodyBobMetresAt: the UPWARD offset above the contact height, as a raised
    cosine — exactly 0 at both contacts (via the epsilon snap), +BodyBobMetres at mid-stance
    and at the airborne apex, never negative."""
    phase = wrap01(cycles)
    angle = phase * BODY_BOB_FREQUENCY * 2.0 * math.pi
    offset = BODY_BOB_METRES * ((1.0 - math.cos(angle)) / 2.0)
    return 0.0 if offset < BODY_BOB_CONTACT_EPSILON else offset


def leg_pitch_degrees(cycles: float, phase_offset: float) -> float:
    """RunCycleSpec.LegPitchDegrees, degrees about world X; +28 deg swings the paw back."""
    return LEG_SWING_DEGREES * math.sin(wrap01(cycles + phase_offset) * 2.0 * math.pi)


def run_pose(cycles: float) -> dict:
    """Every bone's pose at a cycle position, taken from the spec's numbers:

      Root       vertical bob (local +Y is up, because the Root bone points up).
      FrontLegs  pitch about world X, quarters of the cycle at the swing extremes.
      HindLegs   the same curve half a cycle behind the front pair.
      Tail       yaw about world Z, lagging the body by an eighth of a cycle.
      Head       counter-rotation against the bob (HeadSteadyDegrees), keeping the face level.
      Body       holds still: the spec gives the trunk no rotation term.

    The left/right legs of a pair share one bone, so a pair swings rigidly together — that is
    RunCycleSpec.SkinningRule by construction; the spec's SidePhaseOffset needs more than six
    bones and is therefore not expressible in this rig.
    """
    bob = body_bob_metres_at(cycles)
    return {
        "Root": {"location": (0.0, bob, 0.0)},
        "Body": {},
        "Head": {"axis_angle": ((1.0, 0.0, 0.0), -HEAD_STEADY_DEGREES * bob / BODY_BOB_METRES)},
        "FrontLegs": {"axis_angle": ((1.0, 0.0, 0.0), leg_pitch_degrees(cycles, 0.0))},
        "HindLegs": {"axis_angle": ((1.0, 0.0, 0.0),
                                    leg_pitch_degrees(cycles, HIND_PHASE_OFFSET))},
        "Tail": {"axis_angle": ((0.0, 0.0, 1.0), TAIL_SWAY_DEGREES * math.sin(
            wrap01(cycles - TAIL_PHASE_LAG) * 2.0 * math.pi))},
    }


def run_keyed_poses():
    """(frame, pose) for the four poses plus the loop-closing repeat of Contact at
    FRAME_COUNT — without that key the clip would end on the Air pose and a 0.5 s loop
    would pop back to Contact instantly."""
    keyed = [(pose * POSE_SPACING, run_pose(POSE_PHASE[pose])) for pose in range(POSE_COUNT)]
    keyed.append((FRAME_COUNT, run_pose(0.0)))
    for frame, _ in keyed:
        if frame % POSE_SPACING:
            raise SystemExit(f"error: keyed frame {frame} is not on the "
                             f"{POSE_SPACING}-frame pose grid the FBX sampling assumes")
    return keyed


def build_rig(objects: dict):
    """Armature, rigid bone parenting for the thirteen islands, and the run action."""
    armature = art.make_armature(RIG_NAME, RIG_BONES)
    for island, bone in ISLAND_BONES.items():
        art.parent_to_bone(objects[island], armature, bone)
    action = art.make_pose_action(armature, CLIP_NAME, run_keyed_poses())
    return armature, action


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
    # No UV re-wrap. art.tube() already starts ring u at the belly (verified by the phase
    # pick above), so u_rel 0/1 is the belly — the tile's left/right edges, which are the
    # same place on the model — and u_rel 0.5 is the spine, the tile's centre. The previous
    # "wrap" formula scaled by 0.5, which folded the whole ring into HALF the tile: the
    # belly-white then landed on the spine (the cat had a white back) and half the body
    # texture was never sampled.
    return part


def build_neck() -> art.Part:
    return art.tube([(0.0, -0.135, 0.270), (0.0, -0.185, 0.312), (0.0, -0.230, 0.352)],
                    [0.092, 0.082, 0.068], segments=12,
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


EYE_YAW = -0.15  # radians: how far the left eye looks outward (right eye mirrors it)


def build_eyes() -> tuple[art.Part, art.Part]:
    """Big glossy eye spheres. The iris is painted at pattern u_rel 0.5, so phase=pi
    lands it on Blender -Y (straight ahead); EYE_YAW then turns the left eye outward
    and the right eye is that finished eye mirrored across X."""
    proto = art.sphere((0.0, 0.0, 0.0), (0.036, 0.033, 0.037),
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
    return art.pyramid((0.0, -0.408, 0.352), (0.033, 0.019), (0.0, -0.424, 0.344),
                       nose_uv, nose_uv)


def build_ear(side: int) -> art.Part:
    """Rounded triangular ear: a short tapered cone (base -> rounded tip) whose
    forward face samples the pink inner-ear band of the ear tile."""
    # Built upright at the origin, then splayed outward with rot_y. Modelling them
    # already-tilted (offsetting each ring sideways) made the two ears merge into one
    # lumpy mass over the crown in the last render.
    part = art.tube([(0.0, 0.0, 0.0), (0.0, -0.003, 0.050), (0.0, -0.005, 0.094)],
                    [0.052, 0.032, 0.010], segments=10, u_range=(R_EAR[0], R_EAR[2]),
                    ring_v=[R_EAR[1] + (R_EAR[3] - R_EAR[1]) * t for t in (0.0, 0.45, 0.95)],
                    phase=3.141592653589793, hint=(1.0, 0.0, 0.0), caps=(True, True))
    return part.transformed(offset=(side * 0.062, -0.286, 0.440), rot_y=side * 0.30)


def build_leg(side: int, front: bool) -> art.Part:
    """Front leg: near-straight. Hind leg: hip -> hock -> paw, so the bent hock of
    the reference reads in silhouette. Both end on a flat ring at y=0."""
    if front:
        x, y, top = side * 0.050, -0.152, 0.215
        path = [(x, y, top), (x, y - 0.004, top * 0.55), (x, y - 0.004, 0.0)]
        radii = [0.044, 0.028, 0.030]
    else:
        x = side * 0.062
        path = [(x, 0.145, 0.220), (x, 0.198, 0.110), (x, 0.198, 0.0)]
        radii = [0.060, 0.034, 0.029]
    u0, v0, u1, v1 = R_LEG
    return art.tube(path, radii, segments=10, u_range=(u0, u1),
                    ring_v=[v1, v0 + (v1 - v0) * 0.5, v0], phase=3.141592653589793,
                    hint=(1.0, 0.0, 0.0), caps=(True, True))


def build_tail() -> art.Part:
    """Long tail curving up and forward, cream tip last ~20% (atlas v)."""
    path = [(0.0, 0.250, 0.270), (0.0, 0.300, 0.360), (0.0, 0.318, 0.460),
            (0.0, 0.298, 0.560), (0.0, 0.248, 0.640), (0.0, 0.196, 0.686)]
    radii = [0.050, 0.043, 0.036, 0.030, 0.024, 0.019]
    u0, v0, u1, v1 = R_TAIL
    ring_v = [v0 + (v1 - v0) * t for t in (0.0, 0.16, 0.32, 0.48, 0.64, 0.96)]
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
    objects = {}
    for name, part, joint_name in build:
        joint = joints[joint_name]
        objects[name] = art.make_object(
            name, part.transformed(offset=(-joint[0], -joint[1], -joint[2])),
            material=material, smooth=True, parent=root_empty)
        objects[name].location = joint
        parts.append((name, part))

    total = sum(part.tri_count() for _, part in parts)
    if total > 4000:
        raise SystemExit(f"error: cat budget exceeded: {total} triangles > 4000")

    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = FRAME_COUNT
    scene.render.fps = SAMPLE_RATE
    scene.render.fps_base = 1.0
    # The FBX take (and therefore the Unity clip) is named after the SCENE on the export
    # path this rig uses; see art.export_fbx. That is how the clip ends up called "Run"
    # instead of something like "CatDash_Rig|Run".
    scene.name = CLIP_NAME

    armature, action = build_rig(objects)
    armature.parent = root_empty
    keyed_frames = [int(round(point.co.x)) for point in action.fcurves[0].keyframe_points]
    print(f"rig: {len(armature.data.bones)} bones {[b.name for b in armature.data.bones]}, "
          f"action '{action.name}' keyed on frames {keyed_frames} at {SAMPLE_RATE} fps "
          f"({FRAME_COUNT / SAMPLE_RATE:.3f} s), islands bone-parented: "
          f"{len(ISLAND_BONES)}")

    art.finish("Cat", args, texture_canvas=None, parts=parts, material_name="M_Cat_Fur",
               object_name="CatDash_Cat", animation=True, bake_step=POSE_SPACING,
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
                      "rig": {"bones": [b[0] for b in RIG_BONES], "clip": CLIP_NAME,
                              "keyed_frames": [f for f, _ in run_keyed_poses()],
                              "parenting": "one island = one bone, rigid (no weights)"}})
    print(f"note: cat islands: {[name for name, _, _ in build]}")


if __name__ == "__main__":
    main()
