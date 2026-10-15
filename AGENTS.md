<!-- unity-agent-kit:start -->
# Unity Android — agent operating contract
Read all AGENTS.md before editing, including user notes below this managed block.

## Human-routed team: four agents total (development)
Head + Gameplay + Content + Reviewer/QA. The human copies briefs and returns handoffs.
An optional fifth role, Game Idea / Design Partner (agents/IDEA.md), discusses concepts
before development and returns a self-contained Head prompt; it never edits or runs CI.
Head briefs two implementation workers first, then Reviewer/QA at the batch boundary.
Head is NOT a background orchestrator. Never claim to have contacted another agent.
Read agents/HEAD.md, agents/GAMEPLAY.md, agents/CONTENT.md or agents/QA.md for your role.
Workers use separate checkouts. Head integrates; only Head pushes main.
Never give both workers ownership of the same scene, prefab, meta or shared API.
Reviewer/QA is read-only by default; only Head-assigned exclusive test files may be edited.
QA does not replace worker-authored tests, launch CI, or become a second integrator.

## Implement first, check at the batch boundary
- Cheap `python3 tool/preflight.py` before a commit. No Unity per tiny edit.
- `python3 tool/plan_checks.py --base <batch-start-sha>` gives an advisory plan.
- Head reviews risk: docs-only = preflight; isolated C# = filtered Unity tests;
  shared interfaces/physics/scene/prefab/packages/settings = full EditMode + PlayMode.
- No local Unity/Gradle builds unless the user explicitly changes this policy.
- User runs Unity Android workflow, manually, once the batch is ready.
- No push/PR/schedule trigger; no automatic CI dispatch or polling loop.
- Read the failing log before fixing. One focused fix, then hand off for human rerun.
  Same failure twice: STOP, report cause/evidence/options. No blind retry loop.
- Not run is NOT passed. Passing tests is NOT device QA. Never promise all bugs caught.

## Unity and Android safety
- Pin exact Unity Editor version in ProjectSettings/ProjectVersion.txt. Confirm image
  availability and current Android/Play requirements before first release.
- Visible Meta Files + Force Text. Move asset with its .meta; preserve GUIDs.
- No blind scene/prefab YAML rewrites. Use Unity Editor scripts; validate in Editor.
- Keep runtime/editor/test assemblies separate. Add focused tests with code.
- Never commit Library, Temp, Obj, Logs, UserSettings, builds, credentials or licenses.
- Ask before render pipeline/input/package migrations or shared API changes.
- Track asset origin/license in docs/ASSETS.md. No paid API/asset by default.
- Android IL2CPP + ARM64 for store builds; explicit versionCode greater than every
  previously uploaded code. Never generate/rotate upload keys without approval.
- Play upload is INTERNAL ONLY, opt-in manual stage + exact confirmation string.
  Head must not upload, dispatch CI, tag/release, or change secrets/settings.
- Changes to workflows/settings/secrets/public publishing require explicit approval.

## Done
Focused conventional commits; changed paths and test evidence; checks not run;
known risks; human device checklist; local SHA equals remote SHA after push.
Say: “batch ready — Actions → Unity Android → Run workflow”. Do not wait on CI.
<!-- unity-agent-kit:end -->

## Project owner's notes
<!-- Keep all owner notes here; installer never replaces them. -->

### Cat Dash project decisions
- Owner authorized this public starter repository for testing the Head-agent workflow.
- Read docs/GAME_BRIEF.md and HEAD_HANDOFF_BN.md before assigning implementation.
- Current repository is a scaffold, NOT a playable cat runner. Do not call it completed.
- docs/art/cat-dash-visual-target.png is AI concept art, NOT a game-ready 3D model
  or real gameplay screenshot. Produce and validate actual assets in implementation.
- Keep ads, multiplayer, purchases and production publishing out of the first slice.
- Package ID com.keshab.catdash is a starter proposal; confirm ownership/availability
  with owner before first Play upload. No secret values have been installed here.
