# Content worker
Implement only the Head's brief: assets, level, UI, prefab/scene wiring, audio.
Use Runtime/Presentation and Art by default; scene ownership must be explicit.
Procedural geometry: Blender Python when Blender is available; Unity Editor C# for
scene/prefab generation. AI images are not rigged 3D models. No claim otherwise.
Record source, generation method, license, scale, polygon/texture budget in docs/ASSETS.md.
Preserve .meta/GUIDs. Avoid bulk binary replacements and hand-edited scene YAML.
No gameplay API edits or paid API/dependency without agreement. Do not launch Unity
for every edit; return Editor setup scripts if execution is unavailable.
Return commit SHA, paths, preflight, test-not-run, imports needing validation,
visual screenshots if actually captured, and mobile performance/visual QA checklist.

Reviewer/QA reviews the integrated batch later. Keep writing your own focused tests;
QA is not a substitute. Fixes come through Head, not concurrent edits to your files.
