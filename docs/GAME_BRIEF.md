# Cat Dash — first playable brief

## Confirmed by owner
- New public Android Unity test project, to be handed to Head for subsequent work.
- A cat runs along a road; obstacles appear; hitting an obstacle ends the run.
- Beautiful AI-assisted assets/art direction.
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
