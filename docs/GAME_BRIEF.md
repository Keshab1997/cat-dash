# Cat Dash — first playable brief

## Confirmed by owner
- New public Android Unity test project, to be handed to Head for subsequent work.
- A cat runs along a road; obstacles appear; hitting an obstacle ends the run.
- Beautiful AI-assisted assets/art direction.
- Owner requires the actual rendered game to closely match the supplied visual target,
  not just use it as decorative concept art. Placeholder gameplay alone is not final.
- Existing Play Console account; Mac Unity Hub Personal license activated.
- No ads now; optional AdMob later. Manual CI only, no surprise paid services.

## Proposed defaults — Head should confirm only material open decisions
- Portrait, three-lane runner; swipe left/right to change lanes.
- Auto-forward movement; rear follow camera; no jump/slide required in first slice.
- Cozy stylized low-poly street, original orange tabby cat, cream/teal/orange palette.
- Recycled road segments, obstacle patterns with at least one reachable safe path.
- Distance score, gently increasing speed with a cap, start/game-over/restart UI.
- Offline single player; no account/network/analytics/ads/monetization.
- Provisional target: smooth 60 FPS on an agreed mid-range Android device; not measured.
- Starter package ID com.keshab.catdash; owner must confirm before publishing.

## First-slice acceptance criteria
1. Start enters a run with a recognizable cat and readable road/obstacle silhouettes.
2. Touch lane changes work; desktop debug control is optional and clearly labelled.
3. Camera follows smoothly and does not obscure upcoming obstacles.
4. Only active player/obstacle collision ends a run, once; stop movement and score.
5. Game Over shows distance and Restart; restart resets score, speed, obstacles/state.
6. Road and obstacle recycling is bounded; patterns avoid unavoidable blocked paths.
7. Pause/resume/focus loss do not advance score unfairly or leave input/state stuck.
8. Add focused tests for state transitions, collision handling, restart and pattern safety;
   label actual execution separately from authored tests.
9. Assets have source/generation records and mobile budgets; validate imports, scale,
   materials, colliders and any animation in Unity. No raw cube placeholder as final cat.
10. Integrate one small playable slice before UI extras or framework expansion.

## Art approach
Reference: art/cat-dash-visual-target.png (AI-generated concept only).
Use original procedural Blender mesh generation and/or available AI 3D tooling,
with no paid API by default. A hand-authored/procedural original model is an honest
fallback if AI mesh tools are unavailable; do not pretend an image is a rigged model.
Need an actual cat mesh, simple run animation, road, crates/barriers/pots, buildings,
materials, lighting and a clean HUD. Keep visual complexity within measured device limits.
Head must agree the asset toolchain with Content; do not install packages silently.

## Explicit non-goals
No multiplayer, shop, skins inventory, missions, IAP, live ads, online leaderboard,
production release or Play upload in this first implementation batch.

## Readiness / unknowns
- Repo contains kit + starter smoke tests and generic prototype scene generator only.
- Exact Editor pinned to 6000.3.3f1; newer patch migration needs owner agreement.
- Unity Editor, cat assets, gameplay and CatDash scene have NOT been implemented here.
- Owner reported credential setup complete, but THIS new repo has no copied secrets;
  verify secret names/presence without asking for values before manual Unity CI.
- Play signing key, package ownership, previous version codes, min device and art
  acceptance remain to be confirmed. No existing Play app is assumed.

## Visual acceptance gate — owner requirement
Reference: `docs/art/cat-dash-visual-target.png`. Aim for its recognizable look in
actual gameplay, not a promise of pixel-identical AI-image reproduction.

- Cat: appealing rounded orange tabby, cream paws/tail tip, visible stripes, ears,
  expressive silhouette and readable running animation; no capsule/cube as final art.
- Environment: charming pastel storefronts, striped awnings, planters/greenery,
  detailed sidewalks and clean road depth; avoid an empty gray primitive corridor.
- Obstacles: styled wooden crates, colorful barriers and pots with readable silhouettes;
  colliders should match gameplay expectations, not every decorative mesh detail.
- Camera/composition: portrait rear follow view, cat prominent in the lower foreground,
  obstacles readable ahead; preserve safe-path readability despite decorative detail.
- Lighting: warm soft daylight, coherent soft shadows, gentle atmospheric depth and
  orange/cream/teal palette. Do not require expensive real-time effects blindly.
- HUD: restrained, readable on phones; do not obscure the cat or road.

Content first targets ONE polished representative road segment + cat + obstacle set,
then reuses that quality in the runnable slice. Graybox can prove mechanics but must
be labelled graybox, never presented as finished visual delivery.

Head/QA must compare authentic Unity Game-view or device captures from the reviewed
candidate SHA against the reference. Include a representative gameplay screenshot
and short running clip when capture is available, plus a brief checklist of matches,
differences, unresolved gaps and actual device/profiler evidence where measured.
AI-generated pictures or edited mockups are NOT acceptable as gameplay evidence.
If Unity capture/device access is unavailable, mark visual verification NOT RUN and
request the owner's capture; do not silently weaken the acceptance gate.

Owner approval of the actual gameplay visuals is required before calling the look
accepted. Tests passing or an AAB building is not visual approval. Material visual
compromises or art-pipeline/package changes require discussion, not silent shortcuts.
Do not trigger CI/builds per art tweak; review captures at useful batch boundaries.
