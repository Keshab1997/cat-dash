#!/usr/bin/env python3
"""Cat Dash — generated-asset verification (Agent B, batch CD-B1).

    blender --background --python tool/blender_verify_assets.py -- [--json out.json]

Re-imports every FBX in Assets/Art/Generated, then reports, per asset:
  * object hierarchy and per-object triangle count;
  * world-space bounds (metres) and the pivot offset (is the mesh on the ground?);
  * material slots and whether a UV map survived the round trip;
  * budget verdicts against the CD-B1 caps (cat <= 4000, prop <= 800, road <= 3000).

For the cat it also checks the RIG and the embedded run cycle (batch CD-B1, rig block):
  * six bones named exactly as RunCycleSpec.BoneNames, no leaf-bone extras;
  * one FBX take, named RunCycleSpec.ClipName, keyed on KeyedFrames only at SampleRate;
  * every island rigidly parented to the bone RunCycleSpec names for it;
  * at each pose frame, the numbers RunCycleSpec publishes actually reach the mesh: the
    body bob (measured on the Body island), leg pitch, tail sway and head counter-rotation.

The numbers are not copied here: the pose formulas come from the generator
(tool/blender_cat.py) and the constants are parsed out of Assets/Art/RunCycleSpec.cs, so a
drift between the C# contract, the generator and the FBX fails this check. It is still an
import check in Blender — NOT a Unity import, not a Unity animation check, and not a visual
check; only the Editor can confirm what Unity makes of the clip.

Fails loudly (exit code 1) on: missing .meta, duplicate GUIDs, a budget breach, or a
pivot that does not sit on the authored ground plane. This is an import check in
Blender — it is NOT a Unity import/visual verification and must not be reported as one.
"""
from __future__ import annotations

import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import blender_artlib as art  # noqa: E402
import blender_cat as catgen  # noqa: E402  (pose formulas + bone/island tables)

BUDGETS = {"Cat": 4000, "Prop_Crate": 800, "Prop_Barrier": 800, "Prop_Pot": 800,
           "Road_Segment": 3000}
# Expected lowest vertex per asset: cat and props rest on the authored ground plane, the
# road segment's driving surface is the pivot and its 0.30 m slab is meant to hang below.
EXPECTED_ZMIN = {"Cat": 0.0, "Prop_Crate": 0.0, "Prop_Barrier": 0.0, "Prop_Pot": 0.0,
                 "Road_Segment": -0.30}
PIVOT_TOLERANCE = 0.002


# --------------------------------------------------------------------------- #
# Run-cycle / rig contract, read from the C# spec so the three copies cannot drift
# --------------------------------------------------------------------------- #
SPEC_RELATIVE = Path("Assets/Art/RunCycleSpec.cs")
POSE_TOLERANCE_DEGREES = 0.5
POSE_TOLERANCE_METRES = 1e-4


def read_spec_constants(root: Path) -> dict:
    """Parse the numbers the Unity tests assert out of Assets/Art/RunCycleSpec.cs.

    Deliberately a tiny regex reader rather than a C# parser: it fails loudly if a constant
    is renamed, which is the point — this check exists to catch the C# contract, the Python
    generator and the exported FBX drifting apart.
    """
    text = (root / SPEC_RELATIVE).read_text(encoding="utf-8")

    def number(name):
        match = re.search(
            rf"\b{name}\s*=\s*(-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)f?\s*;", text)
        if not match:
            raise SystemExit(f"error: {SPEC_RELATIVE}: cannot read {name}")
        return float(match.group(1))

    def string(name):
        match = re.search(rf'\b{name}\s*=\s*"([^"]+)"', text)
        if not match:
            raise SystemExit(f"error: {SPEC_RELATIVE}: cannot read {name}")
        return match.group(1)

    def numbers(name):
        block = re.search(rf"\b{name}\s*=\s*\{{(.*?)\}}\s*;", text, re.S)
        if not block:
            raise SystemExit(f"error: {SPEC_RELATIVE}: cannot read {name}")
        return [float(value) for value in re.findall(r"(-?\d+(?:\.\d+)?)f?", block.group(1))]

    return {
        "clip_name": string("ClipName"),
        "frame_count": number("FrameCount"),
        "sample_rate": number("SampleRate"),
        "pose_count": number("PoseCount"),
        "pose_phase": numbers("PosePhase"),
        "leg_swing": number("LegSwingDegrees"),
        "hind_offset": number("HindPhaseOffset"),
        "bob": number("BodyBobMetres"),
        "tail_sway": number("TailSwayDegrees"),
        "tail_lag": number("TailPhaseLag"),
        "head_steady": number("HeadSteadyDegrees"),
        "bone_names": re.findall(r'"([^"]+)"', re.search(
            r"BoneNames\s*=\s*\{(.*?)\}\s*;", text, re.S).group(1)),
        "island_names": re.findall(r'"([^"]+)"', re.search(
            r"expected = new\[\]\s*\{(.*?)\}\s*;", text, re.S).group(1))
        if re.search(r"expected = new\[\]\s*\{", text, re.S) else [],
    }


# --------------------------------------------------------------------------- #
# Minimal binary FBX reader — the take Unity actually sees
# --------------------------------------------------------------------------- #
FBX_KTIME = 46186158000  # ktime units per second in FBX 7.x
FBX_NODE = struct.Struct("<III")


def _fbx_properties(buf, pos, end):
    props = []
    while pos < end:
        code = chr(buf[pos])
        pos += 1
        if code == "Y":
            props.append(struct.unpack_from("<h", buf, pos)[0]); pos += 2
        elif code == "C":
            props.append(bool(buf[pos])); pos += 1
        elif code == "I":
            props.append(struct.unpack_from("<i", buf, pos)[0]); pos += 4
        elif code == "F":
            props.append(struct.unpack_from("<f", buf, pos)[0]); pos += 4
        elif code == "D":
            props.append(struct.unpack_from("<d", buf, pos)[0]); pos += 8
        elif code == "L":
            props.append(struct.unpack_from("<q", buf, pos)[0]); pos += 8
        elif code in "fdlib":
            length, encoding, _compressed = struct.unpack_from("<III", buf, pos)
            pos += 12
            fmt = {"f": "<f", "d": "<d", "l": "<q", "i": "<i", "b": "?"}[code]
            size = struct.calcsize(fmt)
            if encoding == 1:
                import zlib
                raw = zlib.decompress(buf[pos:pos + _compressed])
            else:
                raw = buf[pos:pos + length * size]
            pos += _compressed if encoding == 1 else length * size
            props.append(list(struct.unpack(f"<{len(raw) // size}{fmt[1]}", raw)))
        elif code == "S":
            length = struct.unpack_from("<I", buf, pos)[0]; pos += 4
            props.append(buf[pos:pos + length]); pos += length
        elif code == "R":
            length = struct.unpack_from("<I", buf, pos)[0]; pos += 4
            props.append(buf[pos:pos + length]); pos += length
        else:
            raise SystemExit(f"error: unknown FBX property type '{code}'")
    return props, pos


def read_fbx_nodes(path: Path):
    """Read an FBX 7.x binary file into `(name, properties, children)` tuples.

    Blender's own importer renames actions and offsets the imported keys by a frame, so the
    only way to check what Unity's FBX SDK will read — the take name, its duration and the
    key times of every curve — is to read the file this check is about.
    """
    buf = path.read_bytes()
    if not buf.startswith(b"Kaydara FBX Binary"):
        raise SystemExit(f"error: {path.name} is not a binary FBX")
    version = struct.unpack_from("<I", buf, 23)[0]
    wide = version >= 7500
    header = struct.Struct("<QQQ") if wide else FBX_NODE

    def read_node(pos, depth):
        end, num_props, prop_len = header.unpack_from(buf, pos)
        pos += header.size
        name_len = buf[pos]
        pos += 1
        if end == 0 and num_props == 0 and prop_len == 0 and name_len == 0:
            return None, pos
        name = buf[pos:pos + name_len]
        pos += name_len
        props, pos = _fbx_properties(buf, pos, pos + prop_len)
        children = []
        while pos < end:
            child, pos = read_node(pos, depth + 1)
            if child is None:
                break
            children.append(child)
        return (name, props, children), pos

    nodes = []
    pos = 23 + 4
    while pos < len(buf):
        node, pos = read_node(pos, 0)
        if node is None:
            break
        nodes.append(node)
    return nodes, version


def walk(nodes):
    for name, props, children in nodes:
        yield name, props, children
        yield from walk(children)


def fbx_animation_facts(path: Path, clip_name: str, problems: list[str]) -> dict:
    """Take name, duration and per-curve key times, read straight out of the FBX."""
    nodes, version = read_fbx_nodes(path)
    # An AnimationStack node is [uid, "Name\x00\x01AnimStack", ""]; the name is the take name,
    # which is what Unity's Legacy importer names the AnimationClip after.
    stacks = [(label.split(b"\x00")[0].decode("utf-8", "replace"), children)
              for name, props, children in walk(nodes)
              if name == b"AnimationStack"
              for label in [next((value for value in props if isinstance(value, bytes)), b"")]]
    facts = {"fbx_version": version, "takes": [take for take, _children in stacks]}
    if len(stacks) != 1:
        problems.append(f"Cat.fbx: expected exactly one animation take, found "
                        f"{[take for take, _children in stacks]}")
    elif stacks[0][0] != clip_name:
        problems.append(f"Cat.fbx: the take is named '{stacks[0][0]}', so Unity would name "
                        f"the clip that too, not '{clip_name}'")

    for take_name, children in stacks:
        # A "P" property is [name, type, label, flags, value]; the exporter omits properties
        # that still hold their default, so an absent LocalStart means the take starts at 0.
        entries = {props[0].decode(): props[4] / FBX_KTIME
                   for name, props, _children in walk(children)
                   if name == b"P" and len(props) >= 5 and isinstance(props[0], bytes)
                   and isinstance(props[4], (int, float))}
        start = entries.get("LocalStart", 0.0)
        stop = entries.get("LocalStop")
        facts[f"{take_name}_range_s"] = [round(start, 6),
                                        round(stop, 6) if stop is not None else None]
        if abs(start) > 1e-9:
            problems.append(f"Cat.fbx: take '{take_name}' starts at {start:.6f} s instead of 0")
        expected_stop = catgen.FRAME_COUNT / catgen.SAMPLE_RATE
        if stop is None or abs(stop - expected_stop) > 1e-6:
            problems.append(f"Cat.fbx: take '{take_name}' runs {start:.6f}..{stop} s, expected "
                            f"0..{expected_stop:.6f} s")

    all_times = set()
    curves = 0
    loop_closed = True
    for name, props, _children in walk(nodes):
        if name != b"AnimationCurve":
            continue
        times = values = None
        for child_name, child_props, _ in walk([(name, props, _children)]):
            if child_name == b"KeyTime":
                times = child_props[0]
            elif child_name == b"KeyValueFloat":
                values = child_props[0]
        if not times:
            continue
        curves += 1
        all_times.update(round(ktime / FBX_KTIME, 6) for ktime in times)
        if values and abs(values[0] - values[-1]) > 1e-5:
            loop_closed = False
    facts["curves"] = curves
    facts["key_times_s"] = sorted(all_times)
    facts["loop_closes"] = loop_closed
    expected_times = sorted(round(frame / catgen.SAMPLE_RATE, 6)
                            for frame, _pose in catgen.run_keyed_poses())
    if sorted(all_times) != expected_times:
        problems.append(f"Cat.fbx: curve key times are {sorted(all_times)} s, expected "
                        f"{expected_times} s (the four poses plus the loop-closing key)")
    if curves and not loop_closed:
        problems.append("Cat.fbx: a curve's last key does not repeat its first value, so the "
                        "0.5 s loop would pop instead of running")
    return facts


def check_rig_contract(root: Path, problems: list[str]) -> dict:
    """Compare RunCycleSpec.cs and the generator's constants, then check the imported cat."""
    import bpy  # noqa: E402
    import mathutils  # noqa: E402

    spec = read_spec_constants(root)
    report = {"spec": spec}

    expected = {
        "clip name": (catgen.CLIP_NAME, spec["clip_name"]),
        "frame count": (float(catgen.FRAME_COUNT), spec["frame_count"]),
        "sample rate": (float(catgen.SAMPLE_RATE), spec["sample_rate"]),
        "pose count": (float(catgen.POSE_COUNT), spec["pose_count"]),
        "pose phase": (list(catgen.POSE_PHASE), spec["pose_phase"]),
        "leg swing degrees": (catgen.LEG_SWING_DEGREES, spec["leg_swing"]),
        "hind phase offset": (catgen.HIND_PHASE_OFFSET, spec["hind_offset"]),
        "body bob metres": (catgen.BODY_BOB_METRES, spec["bob"]),
        "tail sway degrees": (catgen.TAIL_SWAY_DEGREES, spec["tail_sway"]),
        "tail phase lag": (catgen.TAIL_PHASE_LAG, spec["tail_lag"]),
        "head steady degrees": (catgen.HEAD_STEADY_DEGREES, spec["head_steady"]),
    }
    for label, (generator_value, spec_value) in expected.items():
        if generator_value != spec_value:
            problems.append(f"{SPEC_RELATIVE} vs tool/blender_cat.py: {label} is "
                            f"{spec_value} in C# but {generator_value} in the generator")
    if [b[0] for b in catgen.RIG_BONES] != spec["bone_names"]:
        problems.append(f"{SPEC_RELATIVE} BoneNames {spec['bone_names']} do not match the "
                        f"generator's rig {[b[0] for b in catgen.RIG_BONES]}")

    scene = bpy.context.scene
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if len(armatures) != 1:
        problems.append(f"Cat.fbx: expected exactly 1 armature, found {len(armatures)}")
        return report
    armature = armatures[0]
    report["rig"] = {"name": armature.name, "bones": [b.name for b in armature.data.bones]}

    bones = [bone.name for bone in armature.data.bones]
    if bones != [b[0] for b in catgen.RIG_BONES]:
        problems.append(f"Cat.fbx: bones {bones} do not match RunCycleSpec.BoneNames "
                        f"{spec['bone_names']} (a leaf-bone extra shows up here)")
    for bone_name, _head, _tail, parent in catgen.RIG_BONES:
        bone = armature.data.bones.get(bone_name)
        if bone is None:
            continue
        actual = bone.parent.name if bone.parent else None
        if actual != parent:
            problems.append(f"Cat.fbx: bone {bone_name} is parented to {actual}, expected {parent}")

    # --- the take Unity will import as the clip -----------------------------------
    actions = [action for action in bpy.data.actions if action.name]
    report["actions"] = [action.name for action in actions]
    # Blender's importer renames an imported action ("CatDash_Rig|CatDash_Rig|Run") and shifts
    # the keys by a frame; the take name and the absolute times are read off the FBX itself in
    # fbx_animation_facts. What is checked here is the SHAPE of the imported clip: one key per
    # pose, poses spaced by the contract, spanning the contract's 0.5 s.
    if len(actions) != 1 or actions[0].name.split("|")[-1] != spec["clip_name"]:
        problems.append(f"Cat.fbx: expected one imported action for the '{spec['clip_name']}' "
                        f"take, found {[action.name for action in actions]}")
    scene_fps = (scene.render.fps / scene.render.fps_base) if scene.render.fps else 0.0
    if abs(scene_fps - spec["sample_rate"]) > 1e-6:
        problems.append(f"Cat.fbx: imported at {scene_fps} fps, the clip is authored at "
                        f"{spec['sample_rate']} fps")
    keyed_count = len(catgen.run_keyed_poses())
    pose_spacing = spec["frame_count"] / spec["pose_count"]
    pose_count = int(spec["pose_count"])
    allowed_times = {round(frame / spec["sample_rate"], 4)
                     for frame, _pose in catgen.run_keyed_poses()}
    key_frames = set()
    curve_count = 0
    loose_curves = []
    for action in actions:
        for fcurve in action.fcurves:
            curve_count += 1
            frames = [point.co.x for point in fcurve.keyframe_points]
            key_frames.update(round(frame) for frame in frames)
            origin = min(frames) if frames else 0.0
            stray = {round((frame - origin) / scene_fps, 4) for frame in frames} - allowed_times
            if stray:
                problems.append(f"Cat.fbx: {action.name} {fcurve.data_path} is keyed at "
                                f"{sorted(stray)} s, which is not a pose frame — the clip was "
                                "resampled or baked instead of keyed on the poses")
            # The FBX exporter drops a trailing key whose value repeats the one before it, so a
            # channel that holds still across the loop (the tail yaw) carries fewer than
            # pose_count + 1 keys. More keys than that is the real failure.
            if len(frames) > keyed_count:
                problems.append(f"Cat.fbx: {action.name} {fcurve.data_path} has {len(frames)} "
                                f"keyframes, more than the {keyed_count} poses")
            elif len(frames) < keyed_count:
                loose_curves.append(f"{fcurve.data_path}[{fcurve.array_index}]={len(frames)}")
    key_frames = sorted(key_frames)
    report["clip"] = {"name": spec["clip_name"], "curves": curve_count,
                      "key_frames": key_frames, "fps": scene_fps,
                      "short_curves": loose_curves}
    if len(key_frames) != keyed_count:
        problems.append(f"Cat.fbx: the clip is keyed on Blender frames {key_frames}; expected "
                        f"{keyed_count} distinct pose frames")
    else:
        gaps = sorted({second - first for first, second in zip(key_frames, key_frames[1:])})
        if gaps != [pose_spacing]:
            problems.append(f"Cat.fbx: pose keys are {gaps} frames apart, the contract spaces "
                            f"poses {pose_spacing:g} frames apart")
        span = (key_frames[-1] - key_frames[0]) / scene_fps
        expected_span = spec["frame_count"] / spec["sample_rate"]
        if abs(span - expected_span) > 1e-6:
            problems.append(f"Cat.fbx: the clip spans {span:.6f} s, expected "
                            f"{expected_span:.6f} s")
        report["clip"]["span_s"] = round(span, 6)
        if len(key_frames) - 1 != pose_count:
            problems.append(f"Cat.fbx: the clip has {len(key_frames)} keyframes; the contract "
                            f"has one per pose ({pose_count}) plus the loop-closing repeat")

    # --- rigid parenting: one island = one bone -----------------------------------
    parented = {}
    for island, bone in catgen.ISLAND_BONES.items():
        obj = scene.objects.get(island)
        if obj is None:
            problems.append(f"Cat.fbx: island {island} missing after import")
            continue
        if obj.parent is not armature or obj.parent_type != "BONE" or obj.parent_bone != bone:
            problems.append(
                f"Cat.fbx: island {island} is parented to "
                f"{obj.parent.name if obj.parent else 'nothing'}"
                f"/{obj.parent_type}/'{obj.parent_bone}', expected the {bone} bone")
            continue
        parented[island] = obj

    # --- the spec's numbers, measured on the imported mesh ------------------------
    # Every published term is checked on the MESH, not on the bones: the legs' pitch, the
    # tail's sway and the head's counter-rotation are all "rotate this island about the joint
    # its bone sits on", and the bob is "lift the whole model". Blender's importer rebuilds
    # bone rest orientations, so a rest-relative bone reading would measure the importer; a
    # tracked vertex measured from the clip's own Contact pose measures the deliverable.
    if actions:
        if armature.animation_data is None:
            armature.animation_data_create()
        armature.animation_data.action = actions[0]
        # Blender 4.4+ binds an action to an ID through a slot; assign it when present.
        slots = getattr(actions[0], "slots", None)
        if slots and hasattr(armature.animation_data, "action_slot"):
            armature.animation_data.action_slot = slots[0]

    pivots = {bone: head for bone, head, _tail, _parent in catgen.RIG_BONES}
    island_bone = {"LegFrontL": "FrontLegs", "LegHindL": "HindLegs"}
    # island -> the joint its bone turns about: the one driven island of each moving bone
    # (the eyes/ears/muzzle ride the head bone and the right-side islands mirror the left)
    tracked = {island: pivots[island_bone.get(island, island)]
               for island in ("LegFrontL", "LegHindL", "Head", "Tail")}

    def island_angle(island, cycles):
        """(axis, degrees) the generator publishes for an island's bone at a cycle position."""
        axis, degrees = catgen.run_pose(cycles)[island_bone.get(island, island)]["axis_angle"]
        return tuple(axis), degrees

    def rotate(point, axis, pivot, degrees):
        local = mathutils.Vector(point) - mathutils.Vector(pivot)
        return mathutils.Vector(pivot) + mathutils.Matrix.Rotation(
            math.radians(degrees), 3, mathutils.Vector(axis)) @ local

    poses = {}
    samples = {}
    for pose_index, phase in enumerate(spec["pose_phase"]):
        frame = (key_frames[pose_index] if pose_index < len(key_frames)
                 else pose_index * pose_spacing)
        scene.frame_set(int(frame))
        bpy.context.view_layer.update()

        measured = {}
        body = parented.get("Body")
        if body is not None:
            measured["bob_m"] = round(body.matrix_world.translation.z
                                      - catgen.JOINTS["Body"][2], 6)
            expected_bob = catgen.body_bob_metres_at(phase)
            if abs(measured["bob_m"] - expected_bob) > POSE_TOLERANCE_METRES:
                problems.append(f"Cat.fbx: pose {pose_index} (phase {phase}): the Body island "
                                f"is {measured['bob_m']:.6f} m up, RunCycleSpec says "
                                f"{expected_bob:.6f} m")

        for island, pivot in tracked.items():
            obj = parented.get(island)
            if obj is None:
                continue
            if pose_index == 0:
                # farthest vertex from the island's pivot: the rotation shows up clearest there
                vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
                index = max(range(len(vertices)),
                            key=lambda i: (vertices[i] - mathutils.Vector(pivot)).length)
                samples[island] = (index, vertices[index].copy())
                continue
            index, contact_point = samples[island]
            axis, degrees = island_angle(island, phase)
            axis_contact, degrees_contact = island_angle(island, spec["pose_phase"][0])
            bob = catgen.body_bob_metres_at(phase) - catgen.body_bob_metres_at(
                spec["pose_phase"][0])
            expected_point = rotate(contact_point, axis, pivot, degrees - degrees_contact)
            expected_point = expected_point + mathutils.Vector((0.0, 0.0, bob))
            actual = obj.matrix_world @ obj.data.vertices[index].co
            error = (actual - expected_point).length
            measured[f"{island}_error_m"] = round(error, 6)
            if error > POSE_TOLERANCE_METRES:
                problems.append(
                    f"Cat.fbx: pose {pose_index} (phase {phase}): {island}'s motion is "
                    f"{error * 1000:.2f} mm away from RunCycleSpec's formula "
                    f"({degrees:.2f} deg about {axis} plus a {bob * 1000:.2f} mm bob)")
        poses[f"pose_{pose_index}_phase_{phase}"] = measured
    report["poses"] = poses

    # The bob has to have two extremes per cycle, a body-height apart: this is the contract's
    # "the contact poses sit on the baseline, the airborne poses sit BodyBobMetres above it"
    # read off the mesh. The grouping comes from the spec, not from the pose names.
    measured_bobs = [poses[key]["bob_m"] for key in poses if "bob_m" in poses[key]]
    baselines = [bob for index, bob in enumerate(measured_bobs)
                 if catgen.body_bob_metres_at(spec["pose_phase"][index]) == 0.0]
    peaks = [bob for index, bob in enumerate(measured_bobs)
             if catgen.body_bob_metres_at(spec["pose_phase"][index]) > 0.0]
    report["bob_baseline_m"] = baselines
    report["bob_peak_m"] = peaks
    if len(baselines) != 2 or len(peaks) != 2:
        problems.append(f"Cat.fbx: RunCycleSpec puts {len(baselines)} poses on the bob baseline "
                        f"and {len(peaks)} at the peak; expected two of each")
    elif any(abs(value) > POSE_TOLERANCE_METRES for value in baselines):
        problems.append(f"Cat.fbx: the baseline poses measured {baselines} m of bob, "
                        "RunCycleSpec returns exactly 0 there")
    elif any(abs(value - spec["bob"]) > POSE_TOLERANCE_METRES for value in peaks):
        problems.append(f"Cat.fbx: the peak poses measured {peaks} m of bob, RunCycleSpec "
                        f"asks for {spec['bob']} m")
    elif abs((peaks[0] - baselines[0]) - spec["bob"]) > POSE_TOLERANCE_METRES:
        problems.append(f"Cat.fbx: the two bob extremes are {peaks[0] - baselines[0]:.6f} m "
                        f"apart, RunCycleSpec asks for {spec['bob']:.6f} m")

    # At the Contact pose every rotation is zero and the bob is on its baseline, so each
    # island must sit exactly on its joint: this is what proves rigid parenting survived the
    # FBX round trip without nudging a part off the model.
    scene.frame_set(0)
    bpy.context.view_layer.update()
    for island, obj in parented.items():
        joint = mathutils.Vector(catgen.JOINTS[island])
        drift = (obj.matrix_world.translation - joint).length
        if drift > POSE_TOLERANCE_METRES:
            problems.append(f"Cat.fbx: island {island} sits {drift:.5f} m off its joint "
                            f"({tuple(round(c, 4) for c in joint)}) in the Contact pose")
    report["contact_pose_origins_on_joints"] = not any(
        "off its joint" in problem for problem in problems)
    return report


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

        rig_contract = None
        if name == "Cat":
            rig_contract = check_rig_contract(root, problems)
            rig_contract["fbx"] = fbx_animation_facts(fbx, rig_contract["spec"]["clip_name"],
                                                      problems)

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
            "rig_contract": rig_contract,
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
        rig = report.get("rig_contract")
        if rig:
            fbx_facts = rig.get("fbx", {})
            print(f"    rig: {rig.get('rig', {}).get('bones')}  clip: {rig.get('clip')}")
            take_range = fbx_facts.get(rig["spec"]["clip_name"] + "_range_s")
            print(f"    take: {fbx_facts.get('takes')} range {take_range} s, "
                  f"keys at {fbx_facts.get('key_times_s')} s over {fbx_facts.get('curves')} "
                  f"curves, loop closes: {fbx_facts.get('loop_closes')}")
            print(f"    bob on the mesh: baseline {rig.get('bob_baseline_m')} m, "
                  f"peak {rig.get('bob_peak_m')} m")
            for label, pose in rig.get("poses", {}).items():
                errors = {name: value for name, value in pose.items() if name.endswith("_error_m")}
                print(f"      {label}: bob={pose.get('bob_m')} m  island error {errors}")
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
