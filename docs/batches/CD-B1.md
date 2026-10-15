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
- **2026-10-16 — CD-B1-A2 (EditMode tests + pause/longitudinal fixes) reviewed and merged**
  (branch `work/agent-a/cd-b1-tests-pause`, tip `561da58cb5bd3e037d64d5fd96bb4e1a28b3e68c`, one commit,
  `--no-ff`, no conflicts; paths stayed inside A's ownership; 4 test files + `.meta` with unique GUIDs).
  `playerZForDistance` lowercase alias and the manual clamp in `PlayerMover.Step` are noted below.
- **Open defects after A2 (assigned to A as CD-B1-A3):**
  1. Obstacle contact uses only `OnTriggerStay` — a fast player can cross a collider between frames and
     the run continues; `OnTriggerEnter` is required for the first real contact.
  2. No camera framing rule: `ComputeDesiredPosition` is pure offset addition; nothing keeps the cat in the
     lower foreground or guarantees the near plane never clips it (brief criterion 3 + visual gate).
  3. Test isolation: no test calls the existing `RunController.ResetStatics()` hook, so the static `Active`
     reference survives between EditMode tests.
  4. Cosmetics: `playerZForDistance` lowercase alias and the hand-rolled clamp in `PlayerMover.Step`
     duplicate `Lanes.Clamp` — fold into A3.
- **Spawner coordinate rule (binding for C):** longitudinal placement uses `RunController.DistanceMeters`
  (zeroed on restart) as the world reference; on `Restart()` the scene generator resets `PlayerMover`
  and `RoadLoop.ResetToStart(0f)`.

## Known risks carried into the batch

### CD-B1-A3 (hit detection + camera framing) — blockers cleared, merged 2026-10-16
Branch `work/agent-a/cd-b1-hit-camera`, final tip `8bfb6246451432bf6c5fcc9fb7ea5e5e92c3fb23` (fix commit
`8bfb624`), `--no-ff` merge, no conflicts, paths inside A's ownership. Both held blockers are gone in the
diff: test call sites switched to `HandleObstacleContact` (no `mover.OnTriggerStay` left) and `float.IsFinite`
replaced by `IsNaN`/`IsInfinity`; reflection tests assert the private Unity messages still exist.
Unity EditMode execution still NOT RUN — first real proof is the owner-dispatched CI run.

### Held at review (historical): CD-B1-A3 (branch `work/agent-a/cd-b1-hit-camera`, tip `c56cf2686c4d35167e8b25ad51b66d3b1979dd35`)

Not merged to `main`. Evidence (static review only; Unity not run):

1. `PlayerMover.OnTriggerStay` became `private` in A3, but the merged A2 test still calls it
   from another assembly: `Assets/CatDash/Tests/EditMode/PlayerMoverTests.cs:71` and `:82`
   (`mover.OnTriggerStay(col);`) — CS0122, the `CatDash.Tests.EditMode` assembly would not compile.
2. `Assets/CatDash/Runtime/Gameplay/RearFollowCamera.cs:42` uses `float.IsFinite` — not part of the
   guaranteed `System.Single` surface; `float.IsNaN`/`float.IsInfinity` is the portable form.
3. Skipped from the block (acceptable): `RunInput.Update()` gate on `TryRegister`
   (performance only) and its test additions.

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
