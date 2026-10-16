# CD-B2-A — camera/framing/sky/shadow (gameplay asmdef; no scene file, no art assets)
Baseline main `9bb4e75`. Branch `work/agent-a/cd-b2-camera-stage`. Owns ONLY: `Assets/CatDash/Runtime/Gameplay/**`
(plus its asmdef), `Assets/CatDash/Tests/EditMode/**`. Never touch `Assets/CatDash/Runtime/Presentation/**`,
`Assets/CatDash/Editor/**`, `Assets/Art/**`, any `.unity`, `ProjectSettings/**`, `.github/**`.

Owner-visible defects from `Screenshot_2026-10-16-19-17-03-17` (device, main `4de93a04`): the cat occupies ~4 % of screen
height, ~55 % of the frame is empty flat sky, the road is an untextured grey corridor, and there is a full-width grey band
plus a rounded grey blob at the screen edges — geometry crossing the camera near plane (camera is at y=3.2, z=-5.5,
`nearClipPlane = 0.1`).

1. `RearFollowCamera.cs`: add `[SerializeField] private float minNearPlane = 0.45f;` and every frame set
   `cam.nearClipPlane = Mathf.Max(minNearPlane, <distance to the closest point of the follow target's renderer bounds>)`;
   expose `public float NearPlaneForTest` + `public float FrameFractionForTest` = target world height / visible world height
   at the target distance (`2 * dist * tan(0.5 * cam.fieldOfView * Mathf.Deg2Rad)`). Fully qualified `UnityEngine.Mathf` /
   `Camera` usage; no new assembly references.
2. Framing constants the scene generator will adopt (publish them, do not edit the scene):
   `public const float StagePitchDegrees = 9f; StageFieldOfView = 55f; StageOffsetY = 2.55f; StageOffsetZ = -4.55f;`
   Target: cat silhouette ≈ 18–26 % of screen height, sky ≈ 25–35 % (the brief wants the cat prominent in the lower
   foreground — `docs/GAME_BRIEF.md` "Camera/composition").
3. New `Assets/CatDash/Runtime/Gameplay/StageEnvironment.cs`: `public static void Apply(GameObject lightGO, Camera cam,
   float segmentLength, int segmentCount)` — one call that sets skybox `RenderSettings.skybox = null` +
   `cam.clearFlags = CameraClearFlags.SolidColor`, `RenderSettings.ambientMode = AmbientMode.Trilight` with
   sky/equator/ground read from `Assets/Art/PaletteSpec.cs` if already referenced by the Gameplay asmdef, else from
   parameters you expose; `QualitySettings.shadowDistance = segmentLength * segmentCount * 0.6f`,
   `light.shadows = LightShadows.Soft`, `light.shadowStrength = 0.72f`, `light.shadowAngle = 5f`. Guard every Unity call
   so a null light/camera logs `UnityEngine.Debug.LogWarning` and returns instead of throwing (PlayMode harnesses pass nulls).
4. Tests (EditMode, no scene scanning): near plane never below `minNearPlane`; `FrameFractionForTest` in 0.18–0.26 for a
   0.42 m tall target at `StageOffsetZ` with the Stage constants; `QualitySettings.shadowDistance` after `Apply` equals the
   formula. Use Unity's destroyed-aware `==` for any Unity-object check, never NUnit `IsNull`.
Handoff ≤5 lines: branch, SHA, files, preflight output, Unity NOT RUN.
