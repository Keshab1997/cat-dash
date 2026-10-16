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

### 2026-10-16 — phone-APK stage wired, first dispatch died in the gate; added `.github/workflows/kit-stage-probe.yml`
Cherry-picking `54c971c` onto the green checkpoint conflicted only in `docs/batches/CD-B1.md` (both sides insert a section at the same anchor), so
`ci/build-check` = `d3420ed76c20a87e0420610c4a916f0c179290be` = `fdcdf710` + the workflow/gate files only. Dispatching `stage=apk` there returned **HTTP 422**
until the branch actually carried the new `options:` list — `workflow_dispatch` validates inputs against the workflow file *of the dispatched ref*, and
`ref` must be a branch/tag, never a raw SHA. With the file in place the run dispatched but failed in ~15 s at `Fail fast — inputs and required secrets`, i.e.
`tool/ci_gate.py` found a missing secret (its ERROR lines are not in the annotations API, and job logs are 401 to this token — known limitation).
To name the missing secret without me ever reading a value, I added `kit-stage-probe.yml`: it prints secret NAMES (SET/MISSING) and each stage's gate verdict
into the job summary, then nothing else. Delete it once the answer is known. Note for the owner: `ci/build-check` is my scratch ref for build experiments — it is
not agent-owned, do not push to it.

### 2026-10-16 — run 10 (`dbe0ccb9`): 93/96 — B4's rig imports, 2 of B's own art tests are red; owner approved a phone-APK stage in CI
Red tests, both about how Unity re-times the clip, not about the model: `RunClip_KeysOneKeyframePerPose` fails because the FBX importer **bakes one key per
frame** (`resampleCurves: 0` = "Bake Into Clip", it does not preserve authored keys) so `Head.m_LocalRotation.x` is keyed at 0.0417 s; and
`RunClip_BobLandsOnTheMeshAtEveryPose` measured 0.00015 m where the spec says 0.015 m on `BoneNames[0]` — 100×, i.e. a centimetre-space parent scale in the
imported armature hierarchy, on a channel whose authored value was right. Unity import was, as B documented, the unproven half.
**CI change (owner-approved: "CI workflow-te APK build jog koro"):** `.github/workflows/unity-android.yml` gained an `apk` dispatch stage —
`androidExportType: ${{ inputs.stage == 'apk' && 'androidApk' || 'androidAppBundle' }}`, versionCode defaulting to 1 for sideload (Play stages still require an
explicit code), provenance now checksums `Game.aab`/`Game.apk` whichever exists, and a separate `Store installable APKs` artifact step; `tool/ci_gate.py`
accepts `apk` and requires the four keystore secrets for it. `build`/`internal` conditions were rewritten as "any stage past full", which is equivalent for
them (verified by parsing the YAML: batch has 14 steps, AAB artifact name unchanged so the `internal` job still finds it). Tests still gate the build.
Kit has NO `apk-tool` package (checked: only `template/docs/SETUP.md` mentions APK, "No APK/AAB build or upload") — this is our own edit, keep it in mind on
`tool/kit_update.py` runs, a kit refresh can overwrite the workflow file. Phone install: download the `android-apk-<sha>` artifact; if `Game-split-*.apk`
files are present use `adb install-multiple Game.apk Game-split-*.apk`, otherwise `adb install Game.apk`.

### 2026-10-16 — B4 (cat rig + `Run` clip) reviewed and MERGED — B worked ahead of the block I drafted, and it is a good piece of work
B `6f95e85503f9440d70aefa6fa633893ba4e6aa9e` on `work/agent-b/cd-b1-cat-rig`, base `43bcfab6` (contains B3), zero conflicts against the now-green main,
ownership clean (`Assets/Art/**` + `tool/blender_*` + `docs/ASSETS.md` only). Cat.fbx 86156 → 100908 B, meta: `importAnimation: 1`, `animationType: 1`
(Legacy), `animationCompression: 0`, `animationWrapMode: 2`, `resampleCurves: 0`, `optimizeBones: 0` — the last one is deliberate and documented: rigid bone
parenting leaves no vertices on bones, so bone optimisation could drop the rig.
Captain-side checks that passed: (1) every `RunCycleSpec.X` the 264 new test lines reference exists in `RunCycleSpec.cs` (no CS0117 risk — `ClipName`=`Run`,
`FrameCount`=12, `SampleRate`=24, `LengthSeconds`=0.5, `RootMotion`=false, `BoneCount`=6 with a 6-entry `BoneNames`, `HasEmbeddedAnimation`=true);
(2) I scanned the FBX binary myself — the old `Take 001`/`Default Take` strings are gone and a `Run.tak` plus `ActiveAnimStackName` exist, which corroborates
B's own minimal-FBX-reader claim that Unity will name the Legacy clip `Run`; the armature strings are `CatDash_Rig`/`Root` while the six *bones* are not
named in the spec list. B did not touch `SidePhaseOffset` semantics, only documented that a 6-bone rig cannot express L/R phasing.
B's own stated limit: everything is verified in Blender + by reading the FBX bytes, **Unity import is NOT proven** — Legacy clip creation, the resulting clip
name and the `optimizeBones` interaction are exactly what CI's art tests and the owner's Editor capture must confirm. Next: run 10 on this SHA.

### 2026-10-16 — CI GREEN: run 9 `38855390443` on `fdcdf7106b38755424f9a3e1d77754ceceb06957` — job `batch` success
EditMode 93 tests: **92 passed, 0 failed, 1 skipped** (the intentional `[Explicit]` `CatDashSceneGeneratorTests.GeneratedScene_Loads_As_A_SceneAsset`);
PlayMode **3/3** (`RearFollowCameraFollowTests` green). `Cheap source preflight` 0 errors, `Require real, nonempty passing Unity results` success,
build/provenance/upload steps `skipped` because stage was `full` (tests only), `internal` job skipped — no artifact was published, as designed.
Trail of the `Active` saga (all merged, in order): A10 lazy lookup → A11 two-way pause sync + guard → A13 setter-guard removal (A12 rejected: its
`activeScanned` cache leaked across fixtures and dropped later registrations) → A14 cache deleted + `RunInputTests` `ResetStatics` isolation →
A15 `RegisterForTest` seam → A16 destroy-the-fixture-inside-the-test isolation → A17 `HasActiveForTest` seam (`Active != null`, i.e. Unity destroyed-aware
equality) + destroy-before-assert order. Lesson recorded for future batches: **an assert about a scene-discovered reference must use Unity's `==`, not
NUnit `IsNull`/`AreEqual(…, null)`, and a test that destroys a controller must destroy it before asserting the unregistered state.**
A-side batch work: `RunControllerTests`/`RunInputTests`/`ObstacleSpawnerTests` + `RunController`/`RunInput` are green and stable across runs 5-9;
`PauseCallCount` and `RegisterForTest`/`HasActiveForTest` are documented test seams, nothing is `[Ignore]`d or weakened.
Still open after this: owner-captured Unity/device visual gate for `Cat.fbx` (NOT RUN), real device FPS (NOT RUN), and B's rig + run-cycle block (B4).

### 2026-10-16 — runs 6 & 7, A12/A13/A14 history, A15 merged (`3847b665fca50a0d1f2416135d170e23e94719cd`)
Captain now drives CI directly (`workflow_dispatch`, stage `full`) and reads the artifact XML — no owner round trip.
Run 6 `38850014512`(SHA `43bcfab6`) → 89/91 + PlayMode 3/3: the `private static bool activeScanned` cache I prescribed in A12 leaked across fixtures
(`RunInputTests` has no `ResetStatics`) and silently dropped later registrations → 5 fails. **A12 was never merged.**
A13 `825069ce` (drop the setter guard) merged after I re-verified all six assertions in a Unity-`==` emulation → run `38850892449` (`18220bde`) still red in
`RunInputTests`, because the *cache* was the poison, not the guard.
A14 `a5e41e31` (delete cache, `ReferenceEquals` guard, assert live fallback) → run 7 `38851791944` (`b5a3a93c`): **all 5 RunInputTests green**, 3 red in
`RunControllerTests` (`:104` `Expected: same as <rc> But was: <null>`, `:117`/`:138` mirror images). Root cause of my A14 error: I assumed the EditMode scene
scan reliably returns the fixture's `rc`; the log shows it is inconsistent — sometimes null, sometimes `rc`, and `AddComponent` sometimes appears not to fire
`OnEnable`. Any assert of the form "`Active` is/ isn't some controller the scene also holds" is nondeterministic.
A15 `0c1d686cd8bf24c8427e9f919a42ffcc63fa6aa2` merged: `public static void RegisterForTest(RunController)` seam + the 3 lifecycle tests rewritten to
register explicitly (`AreSame` after `RegisterForTest`, `IsNull` after `DestroyImmediate`/`RegisterForTest(null)`), `RunInputTests` isolation kept, production
getter/OnDisable untouched (it is green as-is via `RunInputTests`). `activeScanned` is gone for good. Next: A16 — isolate the fixture inside the 3 tests
(`UnityEngine.Object.DestroyImmediate(go); rc = null;` as first line) so no second live controller can win the scan; then run 8.

### 2026-10-16 — run 5 (`38850014512`, SHA `43bcfab6`): 89/91 + PlayMode 3/3 → A12 rejected, A13 merged (`18220bde96f6186455a982abf67ee15e88676eaf`)
Run 5 cleared 7 of run 4's 8 failures (A10 lazy lookup, B3 art, A11 two-way pause sync all green). One new red: `RunControllerTests.cs:104`
`Assert.IsNull(RunController.Active)` got `<RunControllerTests (…RunController)>` — A10's lazy rescan *resurrected the destroyed controller*.
A12 `1940bf7d` fixed the resurrection (its `activeScanned` cache is correct and I re-verified all six assertions) but introduced a second bug:
`private set { if (value != null && activeScanned) return; … }` silently drops registration whenever the getter had already been touched — and in the real
scene the HUD/Spawner `Update` touches `Active` before the controller registers, so `Active` would stay null forever (game dead, tests possibly still green).
**NOT merged.** Captain-side emulation of Unity `==`/fake-null semantics was what caught it: `Registration_NotDropped` fails on A12, passes on A13.
A13 `825069ce` (same branch, files: `RunController.cs`, `RunControllerTests.cs`, zero conflicts, preflight 0) keeps A12's getter and reverts the setter to
`private set { active = value; }`; it also adds `Registration_NotDropped_AfterMissedScan`. Note: with `OnDisable`/`OnDestroy` clearing `active` directly, the
getter's fake-null branch is defensive-only (unreachable in tests) — harmless, left in place. Owner dispatched run 6 on `18220bde` with stage `full`.

### 2026-10-16 — A11 reviewed and MERGED: `845bce304293c6f092fcc8b5fe27784baa53eb97` — CD-B1 code work complete
A11 `0064d0e08773bb087404e1292c7970fa2ea23a73` (base `a4427ea`, no conflicts, paths only `RunInput.cs`, `RunController.cs`, `RunInputTests.cs`).
Reviewed the guard rather than trusting it: the ping-pong closes on `RunInput`'s side only — controller→input lands while `syncing == true` and returns
immediately — so exactly one `rc.OnApplicationPause` per external call, which `SinglePauseCall_DoesNotRecurse` (`PauseCallCount == before + 1`) now proves;
`finally { syncing = false; }` is real (a leaked flag would have turned `Resume_AllowsDistanceAdvance_AfterInputPause` red). The last surviving failure
(`RunInputTests.cs:72`) is fixed by driving `rc.paused` from the input side. No assertion weakened, nothing `[Ignore]`d.
Batch state: 8 CI failures from run 4 all addressed (7 by A10, 2 art ones by B3, the last by A11); next owner run of stage `full` is the verdict — expected
EditMode 88 tests / 87 pass + 1 intentional `[Explicit]` skip (the art additions grow the total above run 4's 88) and PlayMode 3/3. Still NOT RUN by
definition: real device FPS/perf and the visual gate (owner's Unity capture of the merged SHA).

### 2026-10-16 — A10 and B3 reviewed and MERGED (`449f730986130f3b9a7384761444765b9cf5fad9`); one failure expected to survive
B3 `406774e6cd756f6f1773ecbf79845814d1654a06`: raised-cosine bob `BodyBobMetres * (1 - cos(angle)) / 2` with a `1e-6` contact snap, plus
`ImportedRootName = "Cat"` documenting that Unity names the FBX root after the file; the hierarchy assert now targets descendants, so the
13 islands are verified without inventing a `CatDash_Cat` node. I recomputed B's exact-equality test numerically
(float32(0.015 * (1-cos(π))/2) == 0.014999999664723873 == float32(0.015f), at both 0.25 and 0.75) — the `==` assertions are sound, not luck.
A10 `a4427ea640ecb87776c3ac5cf910792aa30f55a2` (still based on `f0b15f1`, so it never touched B's files; merged after B3, no conflicts, zero
overlap): lazy `Active` via `UnityEngine.Object.FindFirstObjectByType<RunController>()` and `RunInput.ResolveController()` — this should clear the
`Active`-null and `IsRegistered` failures without depending on Awake/OnEnable, and `FindFirstObjectByType` is the correct Unity 6 name
(`Object.FindFirstObjectByType` exists since 2023.1; the old `FindObjectOfType` is obsolete).
**Known remaining gap, found in review:** propagation is one-way. `RunController.OnApplicationPause` now drives the sibling `RunInput`, but
`RunInput.OnApplicationPause/OnApplicationFocus` do nothing about `RunController.paused`, so `RunInputTests.PauseResumeCycle_DistanceStaysAndInputReenabled`
(`RunInputTests.cs:72`, which only calls `input.OnApplicationPause(true)` before `rc.Tick(0.5f)`) still fails with distance advancing — 7 of 8
previous failures should go green, this one stays red unless fixed. A11 is that fix. A tiny re-entrancy guard is required (controller → input →
controller would otherwise ping-pong). Unity run is the only arbiter; visual gate and device perf still NOT RUN.

### 2026-10-16 — FOURTH CI run (111b67ae, run 38808616897): real numbers. PlayMode 3/3 green, EditMode 79/88 (1 intentional skip)
Everything compiles now and C2's recycle fix is green in CI; the camera convergence test passes. Three classes of failure, none in C:
1. **A8's EditMode lifecycle fix did not work — and that is my misdiagnosis.** All five `RunController`/`RunInput` failures are byte-identical
   to run 2 (`Active` still null at `RunControllerTests.cs:102`; `IsRegistered` false at `RunInputTests.cs:146`; the 4 resume cases unchanged):
   in this Unity, `Awake` is not invoked by `AddComponent` onto the inactive test-scene GameObject either, so moving the binding there bought
   nothing. Merged on reasoning with no local compiler to check it — recorded as a Captain error, and A10 must not rely on any Unity message
   (Awake/OnEnable/Start) for test setup: it must be an explicit call from `[SetUp]` or the component finding its own peer at use time.
2. **B2 introduced two art-contract test bugs of its own** (new in this run): `Cat_KeepsItsPartHierarchyForTheFutureRig` asserts a `CatDash_Cat`
   object that Unity's importer never creates — FBX root is named after the file (`Cat`), and the actual names show all 13 islands present, so the
   assertion is wrong, not the mesh; and `RunCycleSpec_BodyBobPeaksTwicePerCycle` expects 0.015 at a quarter cycle while
   `BodyBobMetresAt` = `0.015*Sin(2*2π*cycles)` returns ~0 there (1.8e-18 = float rounding of sin π) — a genuine half-cycle phase error in the
   bob curve (contact should dip, peak between), so the curve needs `-Cos`, not the test being deleted.
3. The `[Explicit]` scene test skip is by design (no committed `.unity`).
Gate status: Unity compile+EditMode+PlayMode now **measured** on `111b67ae`; visual gate and device perf remain NOT RUN.

### 2026-10-16 — A9 and B2 reviewed and MERGED: main `5f4a5e62d4d6766a45014b4901a7d9387104db79`
- A9 `f0b15f1cc14467f990dbb2449c32a4bf22a50ad2` (one line, `Debug.Log` → `UnityEngine.Debug.Log`; branch still based on `4e115ba`,
  C2's content preserved by merge, `merge-tree` no conflicts). My own review miss is recorded in the previous section — the fix is exactly
  the qualified call, no assertion touched.
- B2 `51d72c81d4c1c962cbe6d952ff6f42f3487e0b00` from main tip: `minColorComponent` replaced by real per-channel 0..1 assertions plus a
  direct channel compare against `Color.magenta` (comment names both traps: missing member and NUnit's ambiguous Color overload);
  the rejected cat look is rebuilt too (`Cat.fbx` 85.5→86.2 KB, 1870 tris ≤ 4000, dims updated), and B documented why FBX metas set
  `isReadable: 1` — a non-readable mesh returns an EMPTY triangles array, so budget asserts could pass at zero; the test asserts non-zero count.
  That is the right kind of paranoia about silent passes.
- Captain scan for the same compile class across `Assets/**/*.cs`: only two files pair `System*` with bare `Debug.`; one is fixed, the other is
  kit-managed `Assets/UnityAgentKit/Editor/KitBuild.cs` which imports only `UnityEngine` (no collision). Unity compile is still the real judge.
Ready for owner re-run: expect both previously-failing assemblies to compile; then EditMode 76 tests (1 `[Explicit]` skip) and PlayMode 3.
Visual gate still NOT RUN — the new `Cat.fbx` needs the owner's real Unity capture before the look counts as accepted.

### 2026-10-16 — THIRD CI run (13e370c): zero tests executed — two compile errors, one was already on main
Pipeline itself is healthy now (license entitlement returned, `6000.3.3f1` Editor booted, all 6 assemblies evaluated).
`*** Tundra build failed` / `Scripts have compiler errors.` → no results XML, so `Require real, nonempty passing Unity results`
correctly refused (artifact `unity-test-evidence-38804627764-1` has 3 logs and 0 XMLs). Exactly two errors:
1. `Assets/CatDash/Tests/PlayMode/RearFollowCameraFollowTests.cs:29 CS0104: 'Debug' is an ambiguous reference between
   'UnityEngine.Debug' and 'System.Diagnostics.Debug'` — **introduced by A8**, which added `using System.Diagnostics;` for the
   Stopwatch and then called bare `Debug.Log`. My A8 review read the diff and confirmed the `Debug.Log` line but did not notice the
   name collision with `using UnityEngine;` — that is on me, not on A.
2. `Assets/Art/Tests/EditMode/ArtContractTests.cs:117 CS1061: 'Color' does not contain a definition for 'minColorComponent'` —
   `minColorComponent` genuinely does not exist on `UnityEngine.Color`. This is **B's merged-but-never-compiled test**, i.e. the
   class of bug the "NOT RUN" label was protecting against; it only surfaced once CI actually compiled the Art test assembly.
Both are one-line fixes, no behaviour involved; batch stays un-verified until the next owner run.

### 2026-10-16 — CD-B1-A8 and CD-B1-C2 reviewed and MERGED (batch is ready for a re-run)
Both cut from `c53f13b` (= main tip at dispatch), zero file overlap, `--no-ff`, no conflicts; preflight 0 errors on each tip and on merged main.
- **A8** `4e115ba7069696bdadf2eaef2f53fe83aa0b7368`: `Active` now bound in `Awake` (the lifecycle Unity actually guarantees for the
  inactive EditMode test scene — that is why `AddComponent` alone left it null) plus `OnDestroy` clearing; `RunInput.Awake → TryRegister`;
  resume guard extended with the `RunController.Active` fallback; new `IsRegistered` seam and a test proving registration right after
  `AddComponent`; PlayMode camera test switched from 60 frames to a bounded `Stopwatch` wait with the elapsed time logged. No runtime
  behaviour beyond these, no assertion removed.
- **C2** `1d41ab9` + `b1ac268523f02fb5a7c62192cd384d7ed0439045`: C found the actual production bug I could not explain from reading —
  after a long distance jump `SpawnRowsUpTo` resumed at the *oldest unplanned* row, so it rented live pool instances for rows the player
  had already passed (z=64 with the limit at 385) instead of the window ahead. Fix: `nextRowIndex` fast-forwards past the despawn line
  (`firstLiveRow`), a per-row `continue` as belt-and-braces, and one post-pass `DespawnBehind` no-op guard; rule now single-sourced in
  `DespawnLimit`. Tests assert the contract through `CountActiveBehind` (stepped 0→2000, single 400 m jump, post-jump run) instead of
  walking the "Obstacle Pool" hierarchy, which C documents as inherently ambiguous because TrySpawn parents live instances there too.
  Pool-cap assertions are kept, not dropped; the one-step `> 0` check became a 320 m sweep, which is stronger, not weaker.
Merged `main`: `665c550f6b8f010db443058f86ed1ebe697463ad`. Expected on the next owner-dispatched run: EditMode 75/76 (1 skip stays
`[Explicit]` by design) and PlayMode 3/3. Still NOT RUN: device FPS/perf, the visual gate (owner's Unity capture from the merged SHA).

### 2026-10-16 — SECOND CI run (0ffad54): Unity actually ran. Real numbers, no more NOT RUN
game-ci fix worked: **compilation clean, all 5 assemblies + UGUI `2.0.0` discovered** (CD-B1 risk 1 and 2 = cleared),
EditMode 68/75 (1 skipped = C's `[Explicit]` scene test, by design), PlayMode 2/3 → **7 failed, 70/78**
(artifact `unity-test-evidence-38802268814-1` → `editmode-results.xml`, `playmode-results.xml`). Failure classes:
1. **EditMode lifecycle (5 failures, one cause).** NUnit EditMode test objects live in an inactive scene: `OnEnable`/`OnDisable`
   do not run on `AddComponent`/`DestroyImmediate`. Proof: `RunControllerTests.OnDisable_ClearsActive_WhenControllerDestroyed`
   fails on its *first* assert (`Expected <ActiveClear> But was: null`, line 102) — `Active` is set in `OnEnable`
   (RunController.cs:48) so it stays null; consequently `RunInput.OnEnable → TryRegister` never runs, so the 4
   `RunInputTests` resume cases fail `InputEnabled` Expected True / But was False (lines 85, 107, 125), and line 72 shows the
   mirror effect (`Expected 3.0875 But was 6.2625`). Fix belongs to A: bind `Active` in `Awake` as well, clear it in `OnDestroy`
   too, and let `RunInput` resume fall back to `RunController.Active`.
2. **PlayMode timing flake (1 failure).** `RearFollowCameraFollowTests.Camera_ConvergesToTargetPlusOffset` reports distance
   5.55200768 = `|offset(0,3.2,-5.5)|` exactly → the camera never moved: `Lerp(current, desired, Clamp01(8*Time.deltaTime))`
   with `deltaTime ≈ 0.0046s` in the `-batchmode -runTests` player and only 60 `yield return null` frames. Not a production bug:
   make the test assert a time-based bound instead of raw frame count.
3. **One real test/behaviour mismatch, unexplained by code reading (1 failure).** `ObstacleSpawnerTests.Obstacles_Behind_The_Player_Are_Recycled`:
   an instance under "Obstacle Pool" was still active at z=64 after `OnDistanceChanged(400)` (limit 385).
   `TrySpawn` parks ALL active instances under `PoolParent` (ObstacleSpawner.cs:224-230), `ReturnToPool` only deactivates,
   and `DespawnBehind`'s guard reads correct — so a same-call respawn/reuse ordering, not the recycle rule itself, is on trial.
   C owns this: assert on `active` membership + z (the real contract), plus one invariant assertion; no gameplay rule change.
No branch merged since; nothing was auto-retried. Owner dispatch remains the only CI trigger.

### 2026-10-16 — CD-B1-B1 + B2 reviewed and MERGED — every worker branch is now in `main`
Branch `work/agent-b/cd-b1-cat-props`: `f6675d7` (v1, held) + `edcd7abd5afad5c4e8ec53e1815138d6f6e93cc0` (redo), still cut from the old
`e6904bb` base; `git merge-tree` = **no conflicts** because B touches only its own tree. Verified in review: paths limited to
`Assets/Art/**` (+ its root `.meta`), `tool/blender_*.py`, `docs/ASSETS.md`; the reference sheets were NOT re-committed by B;
`RunCycleSpec` poses are exactly Contact/Down/Air/Up order with `RootMotion = false`, `ClipName = "Run"`, matching the approved sheet;
`docs/ASSETS.md` now carries a Reference column and states honestly that no AI image is used as mesh or texture map;
`ArtContractTests` checks real tri budgets from imported meshes (`Cat.fbx` ≤ 4000). Kept as-is: `importAnimation: 0` in `Cat.fbx.meta`
(no rig this batch — flip it when rig/run-cycle ships) and the fact that budget claims are authored, not executed. preflight 0 errors on
the branch tip and on merged `main`. Unity import/scale/material + visual gate: still **NOT RUN** — only owner-captured footage from the
merged SHA can clear the gate, and the first Unity verdict comes from the next CI run (on the fixed workflow).

### 2026-10-16 — owner-approved CI fix applied (workflow change)
`game-ci/unity-test-runner` retargeted from `32e5771…` (= tag **v4.4.0**, and the `v4` tag itself now points at the same broken
commit, so `# v4` was not an option) to **v4.3.2** = `fa6ced25861c16ef56187828c43f76d00df43a23`, and `coverageEnabled: false` was
removed — v4.3.2 does not define that input, so it can no longer emit the `--no-coverageEnabled` flag that strict-yargs CLI
`v0.1.72` (its latest release) rejects. `unity-kit.lock.json` hash for `.github/workflows/unity-android.yml` re-pinned
`4902733…` → `c44ce18…` because this repo now intentionally drifts from `Keshab1997/unity-agent-kit` until the kit ships the same fix
(`tool/kit_update.py` will show it as a local modification on the next refresh — expected, keep it).
**Residual, not fixable from here:** v4.4.0 added that input because Unity can crash with coverage on
(upstream #302/#306/#301), and v4.3.2 has no switch to turn coverage off, so the next run may die in coverage instead — the log will
name it. Also unverified as before: `com.unity.ugui 2.0.0` resolution and asmdef discovery on `6000.3.3f1`.
Next: owner re-runs `Unity Android` → stage `full` once; nothing is dispatched from the agent side.

### 2026-10-16 — first CI run (owner-dispatched, run 38800771749) RED: pipeline bug, not worker code
`head_sha` `166b9c96d3cbd6bbaafc015400e7f09cd177f9ee`, job `batch` failed after 56s. Step facts from the jobs API:
`Cheap source preflight` success, `Fail fast — inputs and required secrets` success (so the three UNITY_* secrets are present),
`Restore Unity Library` success, **`Unity batch tests` failure in 3s**, `Keep test evidence even on failure` success but with
"No files were found with the provided path: artifacts/tests" → the game-ci CLI never reached the Editor, so **no test of any
worker ran; everything stays NOT RUN**. Owner-pasted line: `[WARN] Unknown argument: noCoverageEnabled` immediately before
`Error: Test run failed with exit code 1`. Cause (highest-confidence): the workflow passes `coverageEnabled: false`
(unity-android.yml:91) to the pinned `game-ci/unity-test-runner@32e5771` — a fork whose action.yml adds that input ("Set to false
to omit -enableCodeCoverage/-coverageOptions/-coverageResultsPath … see #302/#306/#301") — and it forwards `--no-coverageEnabled`
to `game-ci` CLI v0.1.72, which does not accept that flag; the CLI's yargs is configured `.strict(true)`
(game-ci/cli `src/cli.ts`, comment at ~line 269 documents that strict mode makes unknown args fatal), so the invocation exits 1
before launching Unity. Not verified beyond that without the raw log lines above the `game-ci test` command — the job-log API is
rejected for this app (`401 Server failed to authenticate the request`) and `/actions/runs/.../artifacts` is empty.
Correction after checking upstream: the `coverageEnabled` input exists **only** in `game-ci/unity-test-runner@v4.4.0` and at our
pinned commit `32e5771` — `v4.3.2`, `v4` and `v5.0.0-beta.1` have no such input, and `game-ci/cli` latest release is exactly
`v0.1.72` (no newer CLI to move to, `cliVersion: 'latest'`). So the flag name can never match the CLI; the only clean fixes are
(a) retarget the action to `v4.3.2`/`v4` and delete `coverageEnabled: false` from the workflow, or (b) keep v4.4.0 and pin a CLI that
accepts `--no-coverageEnabled`, which does not exist. Option (a) restores coverage-on behaviour (the risk v4.4.0 was added to avoid).
Fix is a workflow/settings change → **Captain will not touch it without owner approval**;
`unity-kit.lock.json` also hashes that workflow, so it needs a re-pin.

### 2026-10-16 — CD-B1-A6 + A7 reviewed and MERGED (`e158334381f12aba5ce5eeb26fe640be96fe12c9`)
A7 (`49ae8bfdf29960aba9491d581db0155184c91f38`, one commit, only `RunInputTests.cs`, +6 lines) pairs every driver:
`input.OnApplicationPause(x)` is always followed by `rc.OnApplicationPause(x)` and the same for focus, so `rc.paused` is what
freezes the sim; the pause window now really is `paused == true` before `rc.Tick(0.5f)` and `paused == false` after resume.
Verified `RunController.OnApplicationPause/OnApplicationFocus` are public (RunController.cs:120-127) before merging, so the test
compiles by the same seam convention as `PlayerMover.HandleObstacleContact`. A's "don't touch AfterGameOver" respect was honoured —
it never asserts distance, so it stays as is. preflight = 0 errors on branch tip and on merged main; Unity = still NOT RUN.

### 2026-10-16 — CD-B1-A6 (polish) reviewed, held then cleared (see above): original finding
Branch `work/agent-a/cd-b1-polish`, tip `71056af3596b50c99827a6eefd5f49d7db01171c`, cut from `4cec55e` (correct baseline),
one commit, paths exactly the three assigned files, `git merge-tree` vs `main` = no conflicts, preflight = 0 errors.
Done well: `Update()` early-out `if (registeredController == null || registeredController != RunController.Active) TryRegister();`
and the misleading test renamed to `OnDisable_ClearsActive_WhenControllerDestroyed`.
**Why held:** `RunController.paused` is only set by `RunController.OnApplicationPause/OnApplicationFocus` (RunController.cs:120-127),
but `FocusPauseInterleaving_WhenRunning_ResumesInputAndFreezesDistance` calls only `input.OnApplicationPause(true)` and then
`rc.Tick(0.5f)` — `rc.paused` stays false, distance advances, and `Assert.AreEqual(before, rc.DistanceMeters, 0.001f)` fails
deterministically (SetUp registers only the observer; the test never calls `rc.OnApplicationPause`). The sibling `AfterGameOver`
test does pass because it never asserts distance. Fix is two added lines; A owns the file, so it goes back rather than being
silently patched. Unity execution still NOT RUN — this was found by reading, and CI would have been the first place it surfaced.
**Agent C is parked by owner decision** — `work/agent-c/cd-b1-pattern-hud-scene` (`db905c0`) is already merged; no further C blocks.

### 2026-10-16 — CD-B1-B1 reviewed, **held at review (not merged)**
Branch `work/agent-b/cd-b1-cat-props`, tip `f6675d7d6127eb1d9026d45279935d4cef116b85`, cut from the older baseline `e6904bb`.
Verified clean on structure: one commit, paths only inside `Assets/Art/**`, `tool/blender_*.py`, `docs/ASSETS.md` (no scene, no gameplay,
no shared batch doc), `python3 tool/preflight.py` = 0 errors on the branch tip, `git merge-tree` against `main` reports **no conflicts**,
new assemblies `CatDash.Art` / `CatDash.Art.Tests.EditMode` are self-contained (Art asmdef `references: []`, tests reference only Art +
TestRunner). Meshes/textures committed: `Cat.fbx`, `Prop_{Crate,Barrier,Pot}.fbx`, `Road_Segment.fbx`, five PNGs (1024²/512²) with `.meta`.
Held because the owner rejected the cat look; redo requested on the same branch against new reference sheets
committed on `main` so every checkout can read them:
  `docs/art/refs/cat-v2-stylized-3d-render.png` (hero cat look), `docs/art/refs/cat-v2-run-cycle-sheet.png` (4-pose run cycle),
  `docs/art/refs/props-road-sheet.png` (props + road). The earlier `cat-run-pose-sheet.png` is superseded and intentionally NOT
  committed (look rejected). Reference images are pipeline input only — never gameplay evidence for the visual gate.)
Unity import/scale/material verification and the whole visual gate remain **NOT RUN** — only owner-captured Unity footage can clear it.

### 2026-10-16 — CD-B1-A5 reviewed, merged with one Captain line-level correction
Branch `work/agent-a/cd-b1-resume-isolation`, tip `ad5f9046e45c1eac119a8fe6dbc8f1853b5401ac`, cut from `ae8465f` (main tip —
correct baseline). Resume fix is right on both `OnApplicationPause` and `OnApplicationFocus`; `RunController.paused` is already
cleared on resume (verified in the merged RunController). **Blocker found in review and fixed by Captain, not silently:**
A5 called the still-`private` `RunInput.OnApplicationPause/OnApplicationFocus` from `RunInputTests` (9 call sites) → CS0122 in
`CatDash.Tests.EditMode`. Both handlers are now `public`, matching `RunController`'s already-public handlers; commit
`fix(batch1-captain): make RunInput pause/focus seams public to unblock test compile`. A6 asked to rename the misleading test
`Active_ClearedOnDestroy_WithoutResetStatics` (it does call `ResetStatics()` first) and to drop the per-frame `TryRegister()` retry.
Baseline note: the SHA printed in A5's brief tail was mistyped by Captain; A worked from `origin/main` as instructed, so no harm.
`git rev-parse origin/main` is the authoritative baseline at every dispatch.

### 2026-10-16 — CD-B1-A4 and CD-B1-C1 reviewed and merged serially
- A4 `work/agent-a/cd-b1-playmode-integration` tip `79d4830e8047f24e284af8ce52ed5bd73f823da3` → `3bcd3c1f` (2 PlayMode test
  files + .meta; only new files, no Runtime change — Rigidbody(isKinematic) present, so trigger callbacks are real).
- C1 `work/agent-c/cd-b1-pattern-hud-scene` tip `db905c0e593cee99c6ac64fd892e63826847468a` (3 commits, cut from the older
  `e6904bb` baseline) → `2723dbe2`: `--no-ff`, **no conflicts** (verified with `git merge-tree` before touching main), C never
  touched `Runtime/Gameplay/**` or `RunState.cs`; greybox fallback + `[Explicit]` scene test (never a false pass);
  `ResetAndReseed` on Ready/Running keeps the restart contract. C added `UnityEngine.UI` to two asmdefs — UGUI was already
  owner-approved in this baseline, no package change.
- **Still NOT RUN: everything Unity.** No Editor in the sandbox; static review + preflight only. B (`cd-b1-cat-props`)
  has pushed nothing, so any visual comparison remains impossible and stays NOT RUN.

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
