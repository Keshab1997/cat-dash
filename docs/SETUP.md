# Setup — Android, GitHub-only builds, Mac activation

## 1. Project and repository
Install into the repo root. Existing projects keep their packages, settings, scene
list and Unity version. Starter mode adds a minimal Built-in Render Pipeline
physics scene generator, not a complete game or third-person controller.

Set unity-kit.json: real packageName, productName, semver versionName. Existing
Play apps MUST keep their existing package ID and upload key. Keep projectPath `.`.
Read AGENTS.md, fill docs/GAME_BRIEF.md, commit to main. Workflows remain manual.

The starter pins **6000.3.3f1**, a known Unity 6.3 release baseline, NOT a claim to
be the latest patched editor. Before first build, verify a GameCI Android image
exists for your chosen exact version, check release/security notes, and choose a
newer compatible patch if needed via installer --unity-version. No silent upgrades.
Test Framework baseline is 1.4.5; package resolution is not verified until Unity
runs. Commit Unity-generated packages-lock/settings/scene changes after validation.
The build method uses IL2CPP ARM64, minimum Android API 26, and explicit target API.
Workflow default target API is 36; verify current Play policy, SDK and Editor support.

## 2. Unity Personal activation (Mac, one-time prerequisite)
Check your Unity plan eligibility first. Install Unity Hub on Mac, log in, then
Preferences/Settings → Licenses → Add → free Personal license. Install the pinned
Editor if needed. Locate the generated license according to current GameCI docs;
common Mac path: /Library/Application Support/Unity/Unity_lic.ulf.

In GitHub → game repo → Settings → Secrets and variables → Actions, YOU add:
- UNITY_LICENSE — full .ulf contents
- UNITY_EMAIL — account email
- UNITY_PASSWORD — account password

Never paste any of these into agent chat, files in git, screenshots, or logs.
Do not weaken your password or bypass licensing. Activation availability can change;
if this flow fails, stop and use current supported Unity/GameCI instructions.
No guarantee that a Mac activation alone makes every CI activation succeed.
https://game.ci/docs/github/activation/

## 3. Upload signing
Reuse the existing game's UPLOAD keystore. Do not confuse it with Play App Signing's
app-signing key. For a brand-new game, generate an upload key locally only with owner
approval; back it up securely. Add repo secrets yourself:
- ANDROID_KEYSTORE_BASE64 — base64 contents of upload keystore
- KEYSTORE_PASSWORD — keystore password
- KEY_ALIAS — upload key alias
- KEY_PASSWORD — upload key password

These signing names and PLAY_SERVICE_ACCOUNT_JSON match flutter-builder exactly.
Names match, but GitHub does not copy secret VALUES between repositories. Add them
in the actual GAME repo, not unity-agent-kit or flutter-builder. For an existing
published app use that app's correct upload key; matching names do not mean all apps
should share a signing key.

Migration from the initial kit: ANDROID_KEYSTORE_PASS → KEYSTORE_PASSWORD,
ANDROID_KEYALIAS_NAME → KEY_ALIAS, ANDROID_KEYALIAS_PASS → KEY_PASSWORD.
If already installed, manually review/merge the updated workflow and ci_gate.py;
the conservative installer refuses to overwrite changed files. Add the canonical
secret names yourself before build/internal. Old secret names alone no longer work;
this change does not rename/copy/delete any actual GitHub secrets.

No auto-generation/rotation and no key values in this repository.

## 4. Google Play API — only when ready to upload
Create/choose a Google Cloud project, enable Google Play Android Developer API,
create a dedicated service account and securely obtain its JSON credentials.
In Play Console, invite that service account and grant ONLY the target app and
permissions needed to manage testing releases (not production/admin).
Add PLAY_SERVICE_ACCOUNT_JSON via GitHub's secrets UI yourself (raw JSON, not Base64).
If reusing an existing Flutter Play service account, explicitly grant it testing-release
access to the new game in Play Console, then add the original JSON to the game's repo.
GitHub cannot reveal an existing stored secret for copying. Per-app service accounts
reduce the impact of a leaked credential; broad production/admin access is unnecessary.

Create/configure GitHub environment `play-internal` in the GAME repo. Restrict it to
main; add required human reviewers if available, and disable self-review as desired.
Workflow references this environment but does not configure its protection for you.
Credentials are repo secrets in this v1; environment protection gates the upload job,
not the earlier build job. Never run untrusted workflow code with these secrets.

The app must already exist in Play Console; initial/manual upload, app-signing
setup, API terms, store/policy forms or draft-app restrictions may need manual work.
Internal testing is not a bypass for Google review or production requirements.
A draft-only app can reject `completed`; finish its Console setup rather than blind retries.

## 5. Run manually, after a useful batch
Actions → **Unity Android** → Run workflow (main):
- preflight: cheap source/config checks, NO Unity/license needed.
- targeted: exact class/method filter, EditMode only; no build.
- full: EditMode AND PlayMode; no build.
- build: full tests once, then signed AAB; no Play upload.
- apk: full tests once, then a signed **installable APK** uploaded as the `android-apk-<sha>-<attempt>`
  artifact (this repo's addition, not kit v1); no Play upload, version_code optional (defaults to 1).
- internal: full tests once → signed AAB → environment gate → internal testing upload.

`build` and `apk` additionally require the four signing secrets `ANDROID_KEYSTORE_BASE64`, `KEYSTORE_PASSWORD`,
`KEY_ALIAS`, `KEY_PASSWORD` — none of them exist on this repo yet (proven by a throwaway probe run of `tool/ci_gate.py`
that printed only secret NAMES: `UNITY_*` = SET, all four keystore + `PLAY_SERVICE_ACCOUNT_JSON` = MISSING), so any
stage past `full` fails at `Fail fast` in ~15 s. For sideload-only phone testing any PKCS12 keystore works; keep the
Play upload keystore separate and never reuse it for a debug artifact.

Build/internal require explicit version_code greater than ALL previously uploaded
Play codes, plus supported target_api. This v1 does not query Play for the maximum:
owner must check Console. Duplicate codes fail safely at Play; no auto-increment/retry.
Internal also requires exact confirmation **UPLOAD INTERNAL**. No production choice.
Targeted PlayMode-only work should use full stage in v1.

Caches are version/package/platform keyed. Cold builds can take minutes; no guarantee
of instant CI. Stage all testing at batch boundaries. Only 3-day evidence/artifact
retention. Standard Linux runner only; no paid API, hosted service or runner required
by the kit. Artifact/cache/LFS quotas and Unity eligibility still apply.
Public repo code and build/test artifacts can be accessible to others; never place
credentials in artifacts. Obtain explicit owner approval for each public game repo.

## 6. Failures
Read failing job logs FIRST. License/config/SDK/disk failure is not a gameplay bug.
CI has timeouts, no poll loop and no retry loop. Preserve evidence, make a focused
fix, let owner rerun. After repeated same failure STOP and give options.
Rerunning only the upload job may not find a prior-attempt artifact; rerun the whole
workflow only deliberately and check whether the previous upload already succeeded.

Phone QA: install via internal testers link, exercise touch, camera, physics,
pause/resume, audio, low-end frame rate, loading, offline handling and save data.
No headless test can certify fun, visuals, crashes on every device, or Play approval.

## Optional procedural asset source
`tool/blender_props.py` generates an original low-poly crate using Blender Python.
Requires Blender separately; not a paid API and not installed/run by this kit.

```bash
blender --background --python tool/blender_props.py -- --output Assets/Art/Generated/Crate.fbx
```

FBX is the default for Unity import. Optional GLB export may need a reviewed glTF
importer; do not add importer packages silently. Import once in Unity to create
`.meta` files, verify scale/materials/collider and record the asset in ASSETS.md.
This is an example, not a complete character/rig/animation generation service.

## Secrets Check — safe manual readiness report
Actions → **Secrets Check** → Run workflow (main). Open the run **Summary**.
Every expected secret has ✅ present / ❌ missing plus basic validation details.
Missing/invalid secrets make this audit job fail intentionally; the summary still shows
all rows. Signing/Play secrets may legitimately be absent before those features are used.

- UNITY_LICENSE: XML shape only; email shape/password presence are NOT Unity login proof.
- Signing: Base64 decoding + local disposable JAR signed/verified with JDK jarsigner;
  password values are environment-only. No APK/AAB build or upload. PKCS12 may reuse
  the store password and ignore a separate key password; note that limitation.
- Play JSON: structure check only by default. Optional `check_play_live` sends a signed
  assertion to Google's fixed OAuth endpoint, then GETs this app's in-app product list.
  No product, edit, track or release is created/changed; no app is uploaded.
  Product-list access is NOT release permission or upload-key validation. A 403/404
  may mean API/permission/app setup rather than a bad key. Owner resolves it; no retries.
- No Unity installation or license activation in this workflow; use Unity Android tests
  for actual Unity activation proof. No credential values/response bodies/artifacts
  are printed/uploaded; temporary key/probe files are removed. No secrets/settings edited.
- It reports only the known expected secret names; it does not list arbitrary repo secrets.

Public run summaries expose only secret names/status, not values. Run only trusted main
code. New game repos need their own secrets; nothing is copied from the kit repo.
