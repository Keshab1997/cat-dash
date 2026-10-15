# CD-B1 — Cat Dash first playable slice (batch record)

- **Batch:** CD-B1 (implement → integrate → QA)
- **Worker baseline SHA (start here):** `e6904bb476fa184c29372a5dab3412a227c80def`
  (re-pinned 2026-10-16 by Captain: this is `main` + the missing `Assets/CatDash.meta`
  folder meta that made `python3 tool/preflight.py` fail at the older pin `89db4db8`.
  Any branch cut from `89db4db8` must be re-cut from the SHA above.)
- **Skeleton commit inside that baseline:** `856aa9b2d8f66f0b7b6f4845d21048c18a72515b`
  ("chore(batch1): freeze Cat Dash skeleton, UGUI package and shared API contract") —
  the frozen contract/API surface lives in these files, not in prose.
- **Prepared by:** Head / integrator, 2026-10-16.

## Why this baseline exists

Workers cannot see each other's checkouts, so the shared surface is frozen in code
before parallel work starts instead of being described in prose:

- assemblies `CatDash.Gameplay`, `CatDash.Presentation` (→ Gameplay), `CatDash.Editor`,
  `CatDash.Tests.EditMode`, `CatDash.Tests.PlayMode` (modern asmdef style, unlike the
  kit's legacy `optionalUnityReferences` test asmdefs — watch the first CI log);
- shared contract `Assets/CatDash/Runtime/Gameplay/RunState.cs`: `RunState`, `Lane`,
  `Lanes` (3 lanes, 1.8 m), `RunTuning`, `IRunObserver`, `ObstacleMarker`;
- contract stubs (signature-only, bodies throw) for `RunController`, `PlayerMover`,
  `RunInput`, `RearFollowCamera`, `CatDashHud`, `ObstacleSpawner`, `RoadLoop`,
  `PatternSafety`. Workers replace bodies and must not rename members;
- approved package addition: `com.unity.ugui 2.0.0` (owner-approved; version confirmed
  against real Unity 6.x projects, not guessed).

## Scope of CD-B1

Gameplay: run state machine, distance score, speed ramp, lane movement, swipe input,
obstacle contact, rear follow camera + focused tests.
Content: procedural Blender cat (skinned, run cycle) and prop set, palette/materials,
code-generated scene, portrait HUD, road recycling, obstacle patterns with a guaranteed
reachable safe lane + focused tests.

Out of scope: jump/slide, ads, shop, multiplayer, audio, analytics, Play upload,
tags/releases, workflow/secret/settings changes, package changes beyond the approved UGUI
addition, paid assets or APIs.

## Visual gate

`docs/GAME_BRIEF.md` → "Visual acceptance gate" and `AGENTS.md` → "Visual quality
requirement" apply to this batch. The Unity-rendered comparison is **owner-captured**
(candidate SHA, Game view or device); neither worker nor Head can produce it in the
sandbox. Missing capture = visual check NOT RUN, never silently accepted.

## Batch boundary checks (planned)

| Change | Check |
|---|---|
| every worker commit | `python3 tool/preflight.py` |
| integration | preflight + `python3 tool/plan_checks.py --base <baseline>` |
| batch end | owner-run manual workflow: **stage `full`** (EditMode + PlayMode, no build) |

`full` needs only `UNITY_LICENSE`, `UNITY_EMAIL`, `UNITY_PASSWORD`. No CI dispatch, no
polling, no retry loop from the agent side; the owner runs it once per batch.

## Frozen cross-agent contact points (Captain, dispatch 2026-10-16)

These are the only names A/B/C may rely on across ownership lines; none of them renames
a frozen member. Implementations live in the owning agent's files.

- **Contact path (A ↔ B/C):** obstacles carry `ObstacleMarker` + a trigger `Collider`.
  `PlayerMover` calls `OnTriggerStay(Collider other)`, validates
  `other.GetComponent<ObstacleMarker>() != null`, then calls the frozen
  `RunController.EndRun()`. Nothing new is added to the `CatDash.Gameplay` public API.
- **Frame-free determinism (A):** `RunController.Tick(float deltaTime)` is public so
  EditMode tests can advance the sim without frames; the frozen members keep their
  signatures, `Update()` only forwards `Time.deltaTime`.
- **Art folder (B → C):** meshes under `Assets/Art/Generated/**` (`.fbx`), provenance
  table in `docs/ASSETS.md`. Agent C resolves them at generation time with
  `AssetDatabase.FindAssets("t:Model", new[]{"Assets/Art/Generated"})` and must fall
  back to gray-box primitives when the folder is empty (B lands in parallel).
- **One scene, one owner:** the CatDash scene and its generator belong to C only. B never
  touches scenes/UI; A never touches `Assets/Art/**` or scenes.

## Integration log (Captain)

- **2026-10-16 — CD-B1-A (gameplay core) reviewed and merged to `main` as `9cf8b8e29b9712e12a998652c54ceadac2c65ca4`**
  (branch `work/agent-a/cd-b1-gameplay-core`, tip `29863fd519679ff42a2276ac19191a037e8a4e9c`, `--no-ff`, no conflicts).
  Handoff reported `deb60c3` as tip — stale by one commit; only the tip SHA counts.
  Frozen members in `RunState.cs` untouched ✅. `docs/HANDOFF.md` template restored by Captain.
- **Carried defects (assigned back to A as CD-B1-A2, not fixed silently):**
  1. No tests were added — contract required focused EditMode tests.
  2. `RunInput` is never re-enabled: `OnApplicationPause(true)`/focus loss calls `DisableInput()`,
     nothing re-enables it, so after resume swipes stay dead (acceptance criterion 7).
  3. `PlayerMover.ResetToStart()` leaves world `z` increasing while `RunController.Restart()` zeroes
     `DistanceMeters` → two different longitudinal references for spawner/mover/camera.
- **Spawner coordinate rule (binding for C):** longitudinal placement uses `RunController.DistanceMeters`
  (zeroed on restart) as the world reference; on `Restart()` the scene generator resets `PlayerMover`
  and `RoadLoop.ResetToStart(0f)`.

## Known risks carried into the batch

1. This is the first real Unity run of the kit itself (kit `VALIDATION.md`: no Editor,
   no compilation, no tests ever executed). First `full` run may surface compile or
   asmdef-discovery issues; the failing log is read before any fix.
2. `com.unity.ugui 2.0.0` resolution is unverified for `6000.3.3f1` — if resolution
   fails, the log names the valid version and the fix is a one-line manifest change.
3. No committed `.unity` scene in CD-B1 (scene YAML is generated by code, kit rule).
   CI `full` runs tests only, which do not need a scene; the first signed AAB will need
   the owner to run the generator once and commit the result.
4. Hand-written `.meta` files for generated FBX assets are minimal; Unity normalises
   them on first import.
5. `Assets/UnityAgentKit/Tests/**.asmdef` are kit-managed and untouchable this batch.
