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
