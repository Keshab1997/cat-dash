<!-- unity-agent-kit:start -->
# Unity Android — Captain team contract
Read all AGENTS.md, including owner notes below this managed block.

## Team: four agents total
- Captain: divide work, define shared APIs/ownership, review all three deliveries,
  run scoped checks, resolve integration and merge reviewed work into main.
- Agent A: gameplay/state, controls, physics, camera (agents/GAMEPLAY.md).
- Agent B: original 3D assets, materials, textures, animation (agents/ART.md).
- Agent C: level/scene/prefab wiring, presentation/UI/audio (agents/CONTENT.md).
There is NO separate QA agent. Captain reviews/tests; all workers write relevant tests.
Optional Idea Partner (agents/IDEA.md) discusses concepts before development only.
Captain instructions: agents/CAPTAIN.md (legacy agents/HEAD.md points there).

## Short Bengali chat, parallel implementation
Write owner-facing questions, plans, briefs and reports in Bengali (বাংলা), briefly.
Keep code, paths, commands, identifiers, secret names and quoted errors exact.
Captain sends THREE separate copy-paste text blocks, labelled Agent A / B / C,
8–10 lines each, one small deliverable per agent. No long essay or full-game backlog.
Human forwards blocks and returns reports; never claim autonomous agent contact.
All three may work concurrently in separate checkouts/branches from one verified
baseline SHA. Exclusive files/folder .meta ownership; never parallel-edit a scene.
Agent C owns scene wiring; Agent B owns art assets, not scenes; Agent A owns core code.
Freeze shared contracts and shared folder .meta files before branching. If unclear,
Captain asks one short question instead of letting workers guess conflicting APIs.

## Branches and merge
Workers create Captain-assigned work/agent-a/<task>, work/agent-b/<task>, or
work/agent-c/<task> branches from the agreed baseline and push ONLY that branch.
Never worker-push main, force-push, auto-rebase or auto-resolve conflicts.
Handoff: branch + exact pushed SHA + files + checks/not-run + risks, at most 5 lines.
Captain fetches named branches, reviews exact SHAs and ownership, then integrates
serially (use integration/<batch> if useful) and merges to main after needed checks.
If branch tips changed, review the new diff before merging. Branches reduce push
races but do NOT guarantee no merge conflicts. Resolve shared-file conflicts explicitly.
No automatic branch deletion, PR creation, release, secret or settings change.

## Fast checks and safety
Cheap python3 tool/preflight.py before each commit. Captain reviews each handoff;
no Unity/full battery per tiny task. At a useful batch boundary choose targeted tests
for isolated changes or full EditMode/PlayMode for shared/physics/scene/settings risk.
Unity CI stays human-dispatched; Captain reads the real run/log afterward, not a wait loop.
No local Unity/Gradle build, automatic CI dispatch, polling, Play upload or release.
Read failing logs before fixes. Repeated same failure: STOP and report facts/options.
Not run is NOT passed; compilation/build is NOT visual/device/performance approval.
Preserve .meta/GUIDs; use Editor tooling rather than blind scene YAML rewrites.
Never commit credentials, licenses, keystores, Library/Temp/Logs/build outputs.
Track asset origin/licensing; no paid API/asset/runner without explicit approval.
Ask before workflows/settings/secrets, package/pipeline migrations, tags/releases,
public repo creation or publishing. Internal upload remains manual, never production.

## Captain reply after worker handoff
At most 3–5 Bengali lines: received/reviewed SHA, checks actually run, blocker or
next action. If another task is needed, one short block for the affected agent only.
No repeated three-agent plan unless starting a new batch. Keep owner notes intact.
<!-- unity-agent-kit:end -->


## Project owner's notes
<!-- Keep all owner notes here; installer never replaces them. -->

### Cat Dash project decisions
- Owner authorized this public starter repository for testing the Captain-agent workflow.
- Read docs/GAME_BRIEF.md and CAPTAIN_HANDOFF_BN.md before assigning implementation.
- Current repository is a scaffold, NOT a playable cat runner. Do not call it completed.
- docs/art/cat-dash-visual-target.png is AI concept art, NOT a game-ready 3D model
  or real gameplay screenshot. Produce and validate actual assets in implementation.
- Keep ads, multiplayer, purchases and production publishing out of the first slice.
- Package ID com.keshab.catdash is a starter proposal; confirm ownership/availability
  with owner before first Play upload. No secret values have been installed here.

### Visual quality requirement
- Actual gameplay should closely match docs/art/cat-dash-visual-target.png. Read the
  Visual acceptance gate in docs/GAME_BRIEF.md; graybox is not final visual delivery.
- Captain must include this gate in Agent B/Agent C briefs. Use genuine candidate-SHA captures,
  not AI mockups, for comparison. Owner approves the actual look; absent captures or
  profiling must be labelled unverified. No pixel-perfect/performance guarantees.
