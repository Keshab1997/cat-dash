using System.Collections.Generic;
using CatDash.Gameplay;
using CatDash.Presentation;
using UnityEditor;
using UnityEditor.Events;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace CatDash.EditorTools
{
    /// <summary>
    /// Creates the single CatDash scene from code. Owner: CONTENT (Agent C).
    /// </summary>
    /// <remarks>
    /// Kit rules honoured here: the scene is Editor-generated (no hand-written YAML) and a committed
    /// .unity file is NOT required for CD-B1 (docs/batches/CD-B1.md, risk 3) — the owner runs
    /// <c>CatDash/Generate CatDash scene</c> once, reviews the Game view and commits the result.
    ///
    /// Wiring philosophy: Agent A's components are referenced through the frozen contract only. Their
    /// serialized fields are set through SerializedObject, and the single method call that is genuinely
    /// required (<c>RearFollowCamera.SetTarget</c>) is isolated in <see cref="TryWireContract"/> so an
    /// unimplemented stub cannot abort generation.
    ///
    /// Art: Agent B's assets are discovered with AssetDatabase.FindAssets under
    /// <see cref="GeneratedArtFolder"/>; every missing asset falls back to a labelled greybox and logs a
    /// "// GREYBOX" line. Greybox output is placeholder mechanics proof, never final art.
    /// </remarks>
    public static class CatDashSceneGenerator
    {
        public const string SceneFolder = "Assets/CatDash/Scenes";
        public const string ScenePath = SceneFolder + "/CatDash.unity";
        public const string GeneratedArtFolder = "Assets/Art/Generated";

        public const float SegmentLength = 20f;
        public const int SegmentCount = 6;
        public const int PoolSizePerPrefab = 8;
        public const float RowSpacing = 8f;
        public const float SpawnAheadDistance = 60f;
        public const float DespawnBehindDistance = 15f;
        public const int LayoutSeed = 20261016;

        private const string Greybox = "// GREYBOX";
        private const float ReferenceWidth = 1080f;
        private const float ReferenceHeight = 1920f;

        // Cozy cream / teal / orange palette from docs/GAME_BRIEF.md (greybox stand-ins for Agent B materials).
        private static readonly Color RoadColor = new Color(0.38f, 0.40f, 0.43f);
        private static readonly Color LanePaintColor = new Color(0.98f, 0.95f, 0.87f);
        private static readonly Color SidewalkColor = new Color(0.91f, 0.86f, 0.76f);
        private static readonly Color BuildingColor = new Color(0.90f, 0.72f, 0.60f);
        private static readonly Color CrateColor = new Color(0.72f, 0.45f, 0.24f);
        private static readonly Color BarrierColor = new Color(0.20f, 0.62f, 0.62f);
        private static readonly Color PotColor = new Color(0.95f, 0.55f, 0.20f);
        private static readonly Color CatFurColor = new Color(0.93f, 0.53f, 0.20f);
        private static readonly Color CatCreamColor = new Color(0.99f, 0.94f, 0.86f);
        private static readonly Color SkyColor = new Color(0.79f, 0.89f, 0.94f);
        private static readonly Color InkColor = new Color(0.98f, 0.96f, 0.92f);
        private static readonly Color PanelColor = new Color(0.07f, 0.09f, 0.11f, 0.45f);

        private static readonly string[] ObstacleKeywords = { "crate", "barrier", "pot", "obstacle", "box" };
        private static readonly string[] CatKeywords = { "cat", "kitten", "tabby" };

        [MenuItem("CatDash/Generate CatDash scene", priority = 10)]
        public static void GenerateFromMenu()
        {
            Generate();
        }

        /// <summary>Builds and saves Assets/CatDash/Scenes/CatDash.unity. Returns the path, or null on cancel.</summary>
        public static string Generate()
        {
            if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
            {
                Debug.LogWarning("CatDash scene generation cancelled: pending scene changes were not saved.");
                return null;
            }

            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var notes = new List<string>();

            Material road = CreateSceneMaterial(RoadColor, "Road (greybox)");
            Material lanePaint = CreateSceneMaterial(LanePaintColor, "Lane paint (greybox)");
            Material sidewalk = CreateSceneMaterial(SidewalkColor, "Sidewalk (greybox)");
            Material building = CreateSceneMaterial(BuildingColor, "Building (greybox)");
            Material crate = CreateSceneMaterial(CrateColor, "Crate (greybox)");
            Material barrier = CreateSceneMaterial(BarrierColor, "Barrier (greybox)");
            Material pot = CreateSceneMaterial(PotColor, "Pot (greybox)");
            Material catFur = CreateSceneMaterial(CatFurColor, "Cat fur (greybox)");
            Material catCream = CreateSceneMaterial(CatCreamColor, "Cat cream (greybox)");

            Transform player = BuildPlayer(catFur, catCream, notes);
            BuildRunRoot(player);
            BuildCamera(player);
            BuildLighting();
            BuildRoad(player, road, lanePaint, sidewalk, building, notes);
            BuildSpawner(crate, barrier, pot, notes);
            BuildHud(notes);

            EditorSceneManager.MarkSceneDirty(scene);
            EnsureFolder(SceneFolder);
            if (!EditorSceneManager.SaveScene(scene, ScenePath))
            {
                Debug.LogError("CatDash scene generation failed: could not save " + ScenePath);
                return null;
            }
            AssetDatabase.SaveAssets();

            Debug.Log("CatDash: generated " + ScenePath + ". Roots: Player, Main Camera, Run Root, Input, RoadRoot, " +
                      "Obstacle Spawner, HUD Canvas, EventSystem, Directional Light (warm). No committed scene exists in " +
                      "CD-B1: review the Game view/device capture, then commit the scene if the look is good.");
            if (notes.Count > 0)
            {
                Debug.Log(Greybox + " generation notes (" + notes.Count + "): " + string.Join(" | ", notes.ToArray()));
            }
            Debug.Log("CatDash: next manual steps — (1) add " + ScenePath + " to Build Settings via " +
                      "'CatDash/Add CatDash scene to Build Settings (only if empty)'; (2) set Device Orientation = Portrait " +
                      "in Player Settings. This generator deliberately does not change project settings.");
            return ScenePath;
        }

        [MenuItem("CatDash/Add CatDash scene to Build Settings (only if empty)", priority = 40)]
        public static void AddSceneToBuildSettingsIfEmpty()
        {
            if (!System.IO.File.Exists(ScenePath))
            {
                Debug.LogWarning("CatDash: " + ScenePath + " does not exist yet — run 'CatDash/Generate CatDash scene' first.");
                return;
            }

            EditorBuildSettingsScene[] existing = EditorBuildSettings.scenes;
            for (int i = 0; i < existing.Length; i++)
            {
                if (existing[i] != null && existing[i].enabled)
                {
                    Debug.Log("CatDash: Build Settings already contain an enabled scene; leaving them untouched " +
                              "(settings changes need owner approval).");
                    return;
                }
            }

            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            Debug.Log("CatDash: Build Settings scene list is now " + ScenePath + ". Owner-invoked settings change " +
                      "(without it the kit would fall back to its prototype scene).");
        }

        // ---------------------------------------------------------------- player

        private static Transform BuildPlayer(Material fur, Material cream, List<string> notes)
        {
            var player = new GameObject("Player");
            player.transform.position = Vector3.zero;

            Transform visual = InstantiateAgentBCat(player.transform, notes);
            if (visual == null)
            {
                Debug.Log(Greybox + " no cat model in " + GeneratedArtFolder + " — building the labelled greybox cat. " +
                          "Placeholder mechanics proof only, never final art (docs/GAME_BRIEF.md visual gate).");
                notes.Add("cat = greybox primitives (Agent B model missing)");
                visual = BuildGreyboxCat(player.transform, fur, cream);
            }

            Bounds bounds = MeasureBounds(visual.gameObject, new Bounds(new Vector3(0f, 0.5f, 0f), new Vector3(0.8f, 1f, 1.2f)));
            StripColliders(visual);

            var capsule = player.AddComponent<CapsuleCollider>();
            float height = Mathf.Max(0.6f, bounds.size.y);
            float radius = Mathf.Max(0.15f, Mathf.Min(bounds.size.x, bounds.size.z) * 0.5f);
            capsule.center = new Vector3(0f, bounds.center.y, 0f);
            capsule.height = height;
            capsule.radius = Mathf.Min(radius, height * 0.5f);

            // Greybox physics assumption flagged for Agent A in the handoff: transform-driven run with one
            // gameplay collider. If PlayerMover expects a CharacterController, replace these two components.
            var body = player.AddComponent<Rigidbody>();
            body.useGravity = false;
            body.constraints = RigidbodyConstraints.FreezeRotation;
            body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
            body.interpolation = RigidbodyInterpolation.Interpolate;

            player.AddComponent<PlayerMover>();
            return player.transform;
        }

        private static Transform InstantiateAgentBCat(Transform parent, List<string> notes)
        {
            List<string> models = FindGeneratedAssets("t:Model");
            if (models.Count == 0)
            {
                Debug.Log(Greybox + " AssetDatabase.FindAssets(\"t:Model\", new[] {\"" + GeneratedArtFolder +
                          "\"}) found no model assets.");
                return null;
            }

            string chosen = PickByKeyword(models, CatKeywords);
            if (chosen == null && models.Count == 1)
            {
                chosen = models[0];
                notes.Add("single model asset used as cat: " + System.IO.Path.GetFileName(chosen));
            }
            if (chosen == null)
            {
                Debug.Log(Greybox + " none of the " + models.Count + " model assets is cat-named, and guessing would be " +
                          "wrong (a crate is not a cat). Files: " + string.Join(", ", models.ToArray()));
                return null;
            }

            GameObject asset = AssetDatabase.LoadAssetAtPath<GameObject>(chosen);
            if (asset == null)
            {
                Debug.LogWarning("CatDash: model found but not loadable: " + chosen);
                return null;
            }

            GameObject instance = UnityEngine.Object.Instantiate(asset);
            instance.name = "CatVisual (" + asset.name + ")";
            instance.transform.SetParent(parent, false);
            instance.transform.localPosition = Vector3.zero;
            notes.Add("cat = " + chosen);
            return instance.transform;
        }

        private static Transform BuildGreyboxCat(Transform parent, Material fur, Material cream)
        {
            GameObject rootObject = NewChild(parent, "GREYBOX_CatVisual");
            Transform root = rootObject.transform;

            Transform body = AddPrimitive(root, PrimitiveType.Capsule, "GREYBOX_CatBody", fur);
            body.localScale = new Vector3(0.44f, 0.42f, 0.44f);
            body.localRotation = Quaternion.Euler(90f, 0f, 0f);
            body.localPosition = new Vector3(0f, 0.42f, 0.02f);

            Transform head = AddPrimitive(root, PrimitiveType.Sphere, "GREYBOX_CatHead", fur);
            head.localScale = new Vector3(0.34f, 0.32f, 0.32f);
            head.localPosition = new Vector3(0f, 0.62f, 0.36f);

            Transform muzzle = AddPrimitive(root, PrimitiveType.Sphere, "GREYBOX_CatMuzzle", cream);
            muzzle.localScale = new Vector3(0.20f, 0.16f, 0.16f);
            muzzle.localPosition = new Vector3(0f, 0.55f, 0.47f);

            Transform leftEar = AddPrimitive(root, PrimitiveType.Cube, "GREYBOX_CatEarL", fur);
            leftEar.localScale = new Vector3(0.11f, 0.16f, 0.05f);
            leftEar.localRotation = Quaternion.Euler(0f, 0f, 18f);
            leftEar.localPosition = new Vector3(-0.11f, 0.79f, 0.30f);

            Transform rightEar = AddPrimitive(root, PrimitiveType.Cube, "GREYBOX_CatEarR", fur);
            rightEar.localScale = new Vector3(0.11f, 0.16f, 0.05f);
            rightEar.localRotation = Quaternion.Euler(0f, 0f, -18f);
            rightEar.localPosition = new Vector3(0.11f, 0.79f, 0.30f);

            Transform tail = AddPrimitive(root, PrimitiveType.Cylinder, "GREYBOX_CatTail", fur);
            tail.localScale = new Vector3(0.09f, 0.22f, 0.09f);
            tail.localRotation = Quaternion.Euler(55f, 0f, 0f);
            tail.localPosition = new Vector3(0f, 0.52f, -0.42f);

            Transform tailTip = AddPrimitive(root, PrimitiveType.Sphere, "GREYBOX_CatTailTip", cream);
            tailTip.localScale = new Vector3(0.11f, 0.11f, 0.11f);
            tailTip.localPosition = new Vector3(0f, 0.72f, -0.53f);

            float[] legX = { -0.16f, 0.16f };
            float[] legZ = { -0.26f, 0.28f };
            for (int i = 0; i < legX.Length; i++)
            {
                for (int j = 0; j < legZ.Length; j++)
                {
                    Transform leg = AddPrimitive(root, PrimitiveType.Cylinder, "GREYBOX_CatPaw" + i + j, cream);
                    leg.localScale = new Vector3(0.10f, 0.14f, 0.10f);
                    leg.localPosition = new Vector3(legX[i], 0.14f, legZ[j]);
                }
            }

            return root;
        }

        // ---------------------------------------------------------------- run root / camera / light

        private static void BuildRunRoot(Transform player)
        {
            var runRoot = new GameObject("Run Root");
            RunController controller = runRoot.AddComponent<RunController>();

            var input = new GameObject("Input");
            input.AddComponent<RunInput>();

            PlayerMover mover = player.GetComponent<PlayerMover>();
            if (mover == null) mover = player.gameObject.AddComponent<PlayerMover>();

            var controllerSerialized = new SerializedObject(controller);
            SetObject(controllerSerialized, "player", player);
            SetFloat(controllerSerialized, "tuning.startSpeed", 6f);
            SetFloat(controllerSerialized, "tuning.maxSpeed", 14f);
            SetFloat(controllerSerialized, "tuning.speedGainPerSecond", 0.35f);
            SetFloat(controllerSerialized, "tuning.laneWidth", Lanes.LaneWidth);
            SetFloat(controllerSerialized, "tuning.laneChangeSpeed", 8f);
            controllerSerialized.ApplyModifiedPropertiesWithoutUndo();

            // Frozen contract: PlayerMover.controller is the only scene link Agent A's code needs.
            var moverSerialized = new SerializedObject(mover);
            SetObject(moverSerialized, "controller", controller);
            moverSerialized.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void BuildCamera(Transform player)
        {
            var cameraObject = new GameObject("Main Camera");
            cameraObject.tag = "MainCamera";
            cameraObject.transform.position = new Vector3(0f, 3.2f, -5.5f);
            cameraObject.transform.rotation = Quaternion.Euler(12f, 0f, 0f);

            var camera = cameraObject.AddComponent<Camera>();
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = SkyColor;
            camera.fieldOfView = 62f; // portrait composition: vertical FOV keeps road + sky in frame
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 260f;
            cameraObject.AddComponent<AudioListener>();

            RearFollowCamera follow = cameraObject.AddComponent<RearFollowCamera>();
            var followSerialized = new SerializedObject(follow);
            SetFloat(followSerialized, "smoothing", 8f);
            SetFloat(followSerialized, "lookAheadDistance", 4f);
            SetFloat(followSerialized, "lookHeight", 0.6f);
            SerializedProperty offset = followSerialized.FindProperty("offset");
            if (offset != null) offset.vector3Value = new Vector3(0f, 3.2f, -5.5f);
            followSerialized.ApplyModifiedPropertiesWithoutUndo();

            // The only Agent A method this generator must call; the stub throws until Agent A lands.
            Transform target = player;
            RearFollowCamera followCamera = follow;
            TryWireContract(delegate { followCamera.SetTarget(target); },
                "RearFollowCamera.SetTarget(player) — re-run this generator after Agent A merges so the camera tracks the cat");
        }

        private static void BuildLighting()
        {
            var lightObject = new GameObject("Directional Light (warm)");
            lightObject.transform.rotation = Quaternion.Euler(52f, -28f, 0f);
            var sun = lightObject.AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = new Color(1f, 0.96f, 0.89f);
            sun.intensity = 1.15f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.45f;

            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.72f, 0.82f, 0.86f);
            RenderSettings.ambientEquatorColor = new Color(0.66f, 0.68f, 0.62f);
            RenderSettings.ambientGroundColor = new Color(0.42f, 0.40f, 0.36f);
            RenderSettings.fog = true;
            RenderSettings.fogMode = FogMode.Linear;
            RenderSettings.fogColor = new Color(0.80f, 0.88f, 0.91f);
            RenderSettings.fogStartDistance = 40f;
            RenderSettings.fogEndDistance = 150f;
        }

        // ---------------------------------------------------------------- road

        private static void BuildRoad(Transform player, Material road, Material lanePaint, Material sidewalk,
                                      Material building, List<string> notes)
        {
            var rootObject = new GameObject("RoadRoot");
            var loop = rootObject.AddComponent<RoadLoop>();
            Transform segmentRoot = NewChild(rootObject.transform, "Road Segments").transform;

            float roadWidth = Lanes.Count * Lanes.LaneWidth + 2.4f; // lanes + shoulders
            for (int i = 0; i < SegmentCount; i++)
            {
                Transform segment = NewChild(segmentRoot, "Road Segment " + i).transform;
                segment.position = new Vector3(0f, 0f, i * SegmentLength);

                Transform surface = AddPrimitive(segment, PrimitiveType.Cube, "GREYBOX_RoadSurface", road);
                surface.localScale = new Vector3(roadWidth, 0.2f, SegmentLength);
                surface.localPosition = new Vector3(0f, -0.1f, SegmentLength * 0.5f);
                // The surface keeps its collider: the player physics works with or without gravity.

                for (int divider = 0; divider < Lanes.Count - 1; divider++)
                {
                    // Divider d sits between lane d and d+1: lane centres are ±LaneWidth, so dividers land on ±LaneWidth/2.
                    float x = (divider + 1) * Lanes.LaneWidth - (Lanes.Count * Lanes.LaneWidth) * 0.5f;
                    for (int dash = 0; dash < 5; dash++)
                    {
                        Transform stripe = AddPrimitive(segment, PrimitiveType.Cube,
                                                        "GREYBOX_LaneDash " + divider + "_" + dash, lanePaint);
                        stripe.localScale = new Vector3(0.12f, 0.02f, 2f);
                        stripe.localPosition = new Vector3(x, 0.011f, dash * 4f + 1f);
                        StripColliders(stripe);
                    }
                }

                for (int side = -1; side <= 1; side += 2)
                {
                    Transform walk = AddPrimitive(segment, PrimitiveType.Cube, "GREYBOX_Sidewalk", sidewalk);
                    walk.localScale = new Vector3(1.2f, 0.3f, SegmentLength);
                    walk.localPosition = new Vector3(side * (roadWidth * 0.5f + 0.6f), 0.15f, SegmentLength * 0.5f);
                    StripColliders(walk);

                    Transform store = AddPrimitive(segment, PrimitiveType.Cube, "GREYBOX_Storefront", building);
                    store.localScale = new Vector3(3f, 3.2f, 6f);
                    store.localPosition = new Vector3(side * (roadWidth * 0.5f + 3.4f), 1.6f, SegmentLength * 0.5f);
                    StripColliders(store);
                }
            }

            // Frozen contract: RoadLoop owns recycling; segmentRoot + player + geometry come from the scene.
            loop.Bind(segmentRoot, player, SegmentLength, SegmentCount);
            notes.Add("road = " + SegmentCount + " greybox segments x " + SegmentLength + " m (Agent B props pending)");
        }

        // ---------------------------------------------------------------- obstacles

        private static void BuildSpawner(Material crate, Material barrier, Material pot, List<string> notes)
        {
            var spawnerObject = new GameObject("Obstacle Spawner");
            spawnerObject.transform.position = Vector3.zero;
            ObstacleSpawner spawner = spawnerObject.AddComponent<ObstacleSpawner>();

            Transform templatesRoot = NewChild(null, "Obstacle Templates (inactive)").transform;
            templatesRoot.gameObject.SetActive(false);

            ObstacleMarker[] prefabs = CollectObstaclePrefabs(templatesRoot, crate, barrier, pot, notes);
            spawner.Configure(prefabs, PoolSizePerPrefab);

            var spawnerSerialized = new SerializedObject(spawner);
            SetFloat(spawnerSerialized, "rowSpacing", RowSpacing);
            SetFloat(spawnerSerialized, "spawnAheadDistance", SpawnAheadDistance);
            SetFloat(spawnerSerialized, "despawnBehindDistance", DespawnBehindDistance);
            SetInt(spawnerSerialized, "poolSizePerPrefab", PoolSizePerPrefab);
            SetInt(spawnerSerialized, "seed", LayoutSeed);
            spawnerSerialized.ApplyModifiedPropertiesWithoutUndo();

            notes.Add("obstacles = " + prefabs.Length + " prefab(s), pool size " + PoolSizePerPrefab + " each");
        }

        private static ObstacleMarker[] CollectObstaclePrefabs(Transform templatesRoot, Material crate,
                                                              Material barrier, Material pot, List<string> notes)
        {
            var markers = new List<ObstacleMarker>();

            // 1. Agent B prefabs that already carry ObstacleMarker are used as-is (assets, not copies).
            List<string> prefabPaths = FindGeneratedAssets("t:Prefab");
            for (int i = 0; i < prefabPaths.Count; i++)
            {
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPaths[i]);
                if (prefab == null) continue;

                ObstacleMarker marker = prefab.GetComponent<ObstacleMarker>();
                if (marker == null) continue;

                if (!HasTriggerCollider(prefab))
                {
                    Debug.LogWarning("CatDash: " + prefabPaths[i] + " ships no trigger collider. Agent A's PlayerMover " +
                                     "only reacts to trigger contacts; ObstacleSpawner normalises pooled clones at " +
                                     "runtime, but the prefab should carry a trigger collider for clarity.");
                }

                markers.Add(marker);
                notes.Add("obstacle prefab = " + prefabPaths[i]);
            }
            if (markers.Count > 0) return markers.ToArray();

            // 2. Agent B meshes without a prefab: wrap each model in a scene template (base-aligned pivot +
            //    gameplay BoxCollider + ObstacleMarker) so the pool can clone it.
            List<string> models = FindGeneratedAssets("t:Model");
            for (int i = 0; i < models.Count && markers.Count < 3; i++)
            {
                if (IsCatModel(models[i])) continue;
                if (PickKeyword(models[i]) == null) continue;

                GameObject asset = AssetDatabase.LoadAssetAtPath<GameObject>(models[i]);
                if (asset == null) continue;

                GameObject instance = UnityEngine.Object.Instantiate(asset);
                ObstacleMarker marker = CreateTemplate(templatesRoot, System.IO.Path.GetFileNameWithoutExtension(models[i]),
                                                       instance, null, Vector3.zero);
                if (marker == null) continue;

                markers.Add(marker);
                notes.Add("obstacle template = " + models[i]);
            }
            if (markers.Count > 0) return markers.ToArray();

            // 3. Nothing usable from Agent B: labelled greybox crate / barrier / pot.
            Debug.Log(Greybox + " no obstacle prefabs and no obstacle meshes in " + GeneratedArtFolder +
                      " — using greybox crate/barrier/pot templates.");
            markers.Add(CreateTemplate(templatesRoot, "crate", GameObject.CreatePrimitive(PrimitiveType.Cube),
                                       crate, new Vector3(0.9f, 0.9f, 0.9f)));
            markers.Add(CreateTemplate(templatesRoot, "barrier", GameObject.CreatePrimitive(PrimitiveType.Cube),
                                       barrier, new Vector3(1.7f, 0.85f, 0.4f)));
            markers.Add(CreateTemplate(templatesRoot, "pot", GameObject.CreatePrimitive(PrimitiveType.Cylinder),
                                       pot, new Vector3(0.6f, 0.7f, 0.6f)));
            notes.Add("obstacles = greybox crate/barrier/pot (Agent B assets missing)");
            return markers.ToArray();
        }

        /// <summary>
        /// Base-aligned pivot + one gameplay collider + ObstacleMarker, so the pool can clone it.
        /// <paramref name="targetSize"/> is a desired bounding-box size in metres, or Vector3.zero to keep
        /// Agent B's own scale.
        /// </summary>
        private static ObstacleMarker CreateTemplate(Transform templatesRoot, string name, GameObject visual,
                                                     Material material, Vector3 targetSize)
        {
            if (visual == null) return null;
            if (material != null) SetMaterial(visual, material);
            StripColliders(visual.transform);

            visual.transform.position = Vector3.zero;
            if (targetSize != Vector3.zero)
            {
                Bounds raw = MeasureBounds(visual, new Bounds(Vector3.zero, Vector3.one));
                Vector3 scale = visual.transform.localScale;
                visual.transform.localScale = new Vector3(
                    raw.size.x > 0.001f ? scale.x * targetSize.x / raw.size.x : scale.x,
                    raw.size.y > 0.001f ? scale.y * targetSize.y / raw.size.y : scale.y,
                    raw.size.z > 0.001f ? scale.z * targetSize.z / raw.size.z : scale.z);
            }

            var fallback = new Bounds(new Vector3(0f, 0.5f, 0f), targetSize == Vector3.zero ? Vector3.one : targetSize);
            Bounds bounds = MeasureBounds(visual, fallback);

            var template = new GameObject("Obstacle Template " + name);
            template.transform.SetParent(templatesRoot, false);
            visual.transform.SetParent(template.transform, false);
            visual.transform.localPosition = new Vector3(-bounds.center.x, -bounds.min.y, -bounds.center.z);

            // Contact contract with Agent A: PlayerMover reacts to OnTriggerEnter/OnTriggerStay, so obstacle
            // colliders must be triggers or a run would never end.
            var box = template.AddComponent<BoxCollider>();
            box.isTrigger = true;
            box.center = new Vector3(0f, bounds.extents.y, 0f);
            box.size = new Vector3(Mathf.Max(0.1f, bounds.size.x), Mathf.Max(0.1f, bounds.size.y),
                                   Mathf.Max(0.1f, bounds.size.z));

            ObstacleMarker marker = template.AddComponent<ObstacleMarker>();
            template.SetActive(false);
            return marker;
        }

        private static bool HasTriggerCollider(GameObject root)
        {
            Collider[] colliders = root.GetComponentsInChildren<Collider>(true);
            for (int i = 0; i < colliders.Length; i++)
            {
                if (colliders[i] != null && colliders[i].isTrigger) return true;
            }
            return false;
        }

        private static bool IsCatModel(string path)
        {
            return PickKeyword(path, CatKeywords) != null;
        }

        private static string PickKeyword(string path, string[] keywords)
        {
            string name = System.IO.Path.GetFileNameWithoutExtension(path).ToLowerInvariant();
            for (int k = 0; k < keywords.Length; k++)
            {
                if (name.Contains(keywords[k])) return keywords[k];
            }
            return null;
        }

        private static string PickKeyword(string path)
        {
            return PickKeyword(path, ObstacleKeywords);
        }

        // ---------------------------------------------------------------- HUD

        private static void BuildHud(List<string> notes)
        {
            Font font = GetBuiltinFont();
            Canvas canvas = BuildCanvas();
            GameObject canvasObject = canvas.gameObject;

            CatDashHud hud = canvasObject.AddComponent<CatDashHud>();

            Text distance = CreateLabel(canvasObject.transform, "Distance Label", "0 m", 64, TextAnchor.UpperCenter, InkColor, font);
            Anchor((RectTransform)distance.transform, new Vector2(0.5f, 1f), new Vector2(0f, -48f), new Vector2(520f, 100f));
            AddOutline(distance);

            GameObject startPanel = CreatePanel(canvasObject.transform, "Start Panel");
            Button startPanelButton = startPanel.AddComponent<Button>();
            SetTargetGraphic(startPanelButton, startPanel);

            Text title = CreateLabel(startPanel.transform, "Title", "Cat Dash", 120, TextAnchor.MiddleCenter, InkColor, font);
            Anchor((RectTransform)title.transform, new Vector2(0.5f, 0.5f), new Vector2(0f, 260f), new Vector2(900f, 200f));
            AddOutline(title);

            Text hint = CreateLabel(startPanel.transform, "Hint", "Swipe left or right to change lane", 48,
                                    TextAnchor.MiddleCenter, InkColor, font);
            Anchor((RectTransform)hint.transform, new Vector2(0.5f, 0.5f), new Vector2(0f, 130f), new Vector2(900f, 120f));

            Button startButton = CreateButton(startPanel.transform, "Start Button", "Start", BarrierColor, font);

            GameObject gameOverPanel = CreatePanel(canvasObject.transform, "Game Over Panel");
            Text gameOverTitle = CreateLabel(gameOverPanel.transform, "Title", "Game Over", 110, TextAnchor.MiddleCenter,
                                             PotColor, font);
            Anchor((RectTransform)gameOverTitle.transform, new Vector2(0.5f, 0.5f), new Vector2(0f, 240f), new Vector2(900f, 200f));
            AddOutline(gameOverTitle);

            Text finalDistance = CreateLabel(gameOverPanel.transform, "Final Distance", "0 m", 90, TextAnchor.MiddleCenter,
                                             InkColor, font);
            Anchor((RectTransform)finalDistance.transform, new Vector2(0.5f, 0.5f), new Vector2(0f, 110f), new Vector2(900f, 160f));
            AddOutline(finalDistance);

            Button restartButton = CreateButton(gameOverPanel.transform, "Restart Button", "Restart", BarrierColor, font);
            gameOverPanel.SetActive(false);

            var hudSerialized = new SerializedObject(hud);
            SetObject(hudSerialized, "startPromptRoot", startPanel);
            SetObject(hudSerialized, "distanceLabelRoot", distance.gameObject);
            SetObject(hudSerialized, "gameOverRoot", gameOverPanel);
            SetObject(hudSerialized, "distanceLabel", distance);
            SetObject(hudSerialized, "gameOverDistanceLabel", finalDistance);
            hudSerialized.ApplyModifiedPropertiesWithoutUndo();

            // Persistent UGUI listeners (the generator's job per the frozen CatDashHud comment): tapping the
            // start panel or the Start button begins the run, Restart restarts it.
            UnityEventTools.AddPersistentListener(startPanelButton.onClick, hud.OnStartButton);
            UnityEventTools.AddPersistentListener(startButton.onClick, hud.OnStartButton);
            UnityEventTools.AddPersistentListener(restartButton.onClick, hud.OnRestartButton);

            var eventSystem = new GameObject("EventSystem", typeof(RectTransform), typeof(EventSystem),
                                             typeof(StandaloneInputModule));
            eventSystem.transform.position = Vector3.zero;

            notes.Add("hud = UGUI canvas " + (int)ReferenceWidth + "x" + (int)ReferenceHeight +
                      " + start/game-over/restart wired by persistent listeners");
        }

        private static Canvas BuildCanvas()
        {
            var canvasObject = new GameObject("HUD Canvas", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler),
                                              typeof(GraphicRaycaster));
            var canvas = canvasObject.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;

            var scaler = canvasObject.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(ReferenceWidth, ReferenceHeight);
            scaler.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            scaler.matchWidthOrHeight = 0.5f;
            return canvas;
        }

        private static GameObject CreatePanel(Transform parent, string name)
        {
            var panel = new GameObject(name, typeof(RectTransform), typeof(Image));
            panel.transform.SetParent(parent, false);

            var rect = (RectTransform)panel.transform;
            rect.anchorMin = Vector2.zero;
            rect.anchorMax = Vector2.one;
            rect.offsetMin = Vector2.zero;
            rect.offsetMax = Vector2.zero;

            var image = panel.GetComponent<Image>();
            image.color = PanelColor;
            image.raycastTarget = true;
            return panel;
        }

        private static Button CreateButton(Transform parent, string name, string label, Color background, Font font)
        {
            var buttonObject = new GameObject(name, typeof(RectTransform), typeof(Image), typeof(Button));
            buttonObject.transform.SetParent(parent, false);
            Anchor((RectTransform)buttonObject.transform, new Vector2(0.5f, 0.5f), new Vector2(0f, -120f), new Vector2(460f, 150f));

            var image = buttonObject.GetComponent<Image>();
            image.color = background;

            Button button = buttonObject.GetComponent<Button>();
            button.targetGraphic = image;

            Text text = CreateLabel(buttonObject.transform, "Label", label, 56, TextAnchor.MiddleCenter, InkColor, font);
            RectTransform textRect = (RectTransform)text.transform;
            textRect.anchorMin = Vector2.zero;
            textRect.anchorMax = Vector2.one;
            textRect.offsetMin = Vector2.zero;
            textRect.offsetMax = Vector2.zero;
            AddOutline(text);
            return button;
        }

        private static void SetTargetGraphic(Button button, GameObject graphicSource)
        {
            if (button == null || graphicSource == null) return;
            var graphic = graphicSource.GetComponent<Graphic>();
            if (graphic != null) button.targetGraphic = graphic;
        }

        private static Text CreateLabel(Transform parent, string name, string value, int fontSize, TextAnchor alignment,
                                        Color color, Font font)
        {
            var labelObject = new GameObject(name, typeof(RectTransform), typeof(Text));
            labelObject.transform.SetParent(parent, false);

            var text = labelObject.GetComponent<Text>();
            text.font = font;
            text.text = value;
            text.fontSize = fontSize;
            text.alignment = alignment;
            text.color = color;
            text.horizontalOverflow = HorizontalWrapMode.Overflow;
            text.verticalOverflow = VerticalWrapMode.Overflow;
            text.supportRichText = false;
            text.raycastTarget = false;
            return text;
        }

        private static void Anchor(RectTransform rect, Vector2 anchor, Vector2 offset, Vector2 size)
        {
            rect.anchorMin = anchor;
            rect.anchorMax = anchor;
            rect.pivot = anchor;
            rect.anchoredPosition = offset;
            rect.sizeDelta = size;
        }

        private static void AddOutline(Text text)
        {
            var outline = text.gameObject.AddComponent<Outline>();
            outline.effectColor = new Color(0.05f, 0.06f, 0.08f, 0.65f);
            outline.effectDistance = new Vector2(2f, -2f);
        }

        private static Font GetBuiltinFont()
        {
            Font font = null;
            try { font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf"); }
            catch { font = null; }

            if (font == null)
            {
                try { font = Resources.GetBuiltinResource<Font>("Arial.ttf"); }
                catch { font = null; }
            }
            if (font == null)
            {
                Debug.LogWarning(Greybox + " no built-in UGUI font found; assign a font on the HUD Text objects manually.");
            }
            return font;
        }

        // ---------------------------------------------------------------- helpers

        private static GameObject NewChild(Transform parent, string name)
        {
            var child = new GameObject(name);
            child.transform.SetParent(parent, false);
            return child;
        }

        private static Transform AddPrimitive(Transform parent, PrimitiveType type, string name, Material material)
        {
            GameObject primitive = GameObject.CreatePrimitive(type);
            primitive.name = name;
            primitive.transform.SetParent(parent, false);
            primitive.transform.localPosition = Vector3.zero;
            if (material != null) SetMaterial(primitive, material);
            return primitive.transform;
        }

        private static Material CreateSceneMaterial(Color color, string name)
        {
            Shader shader = FindOpaqueShader();
            if (shader == null)
            {
                Debug.LogWarning(Greybox + " no opaque shader found (Standard / URP Lit / Legacy Diffuse); primitives keep " +
                                 "Unity's default material and the colour for " + name + " was not applied.");
                return null;
            }

            // Scene-embedded material: deliberately no asset writes into Agent B's Assets/Art/Generated folder.
            var material = new Material(shader);
            material.name = name;
            if (material.HasProperty("_Color")) material.color = color;
            else if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", color);
            return material;
        }

        private static Shader FindOpaqueShader()
        {
            Shader shader = Shader.Find("Standard");
            if (shader == null) shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) shader = Shader.Find("Legacy Shaders/Diffuse");
            return shader;
        }

        private static void SetMaterial(GameObject target, Material material)
        {
            if (target == null || material == null) return;
            var targetRenderer = target.GetComponent<Renderer>();
            if (targetRenderer != null) targetRenderer.sharedMaterial = material;
        }

        private static Bounds MeasureBounds(GameObject root, Bounds fallback)
        {
            if (root == null) return fallback;
            Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return fallback;

            Bounds bounds = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }

        private static void StripColliders(Transform root)
        {
            if (root == null) return;
            Collider[] colliders = root.GetComponentsInChildren<Collider>(true);
            for (int i = 0; i < colliders.Length; i++)
            {
                if (colliders[i] != null) UnityEngine.Object.DestroyImmediate(colliders[i]);
            }
        }

        private static List<string> FindGeneratedAssets(string filter)
        {
            var paths = new List<string>();
            string[] guids = AssetDatabase.FindAssets(filter, new[] { GeneratedArtFolder });
            for (int i = 0; i < guids.Length; i++)
            {
                string path = AssetDatabase.GUIDToAssetPath(guids[i]);
                if (string.IsNullOrEmpty(path) || AssetDatabase.IsValidFolder(path) || paths.Contains(path)) continue;
                paths.Add(path);
            }
            paths.Sort(System.StringComparer.OrdinalIgnoreCase);
            return paths;
        }

        private static string PickByKeyword(List<string> paths, string[] keywords)
        {
            for (int k = 0; k < keywords.Length; k++)
            {
                for (int i = 0; i < paths.Count; i++)
                {
                    if (PickKeyword(paths[i], keywords) != null) return paths[i];
                }
            }
            return null;
        }

        private static void EnsureFolder(string folder)
        {
            if (AssetDatabase.IsValidFolder(folder)) return;

            int slash = folder.LastIndexOf('/');
            if (slash <= 0) return;

            string parent = folder.Substring(0, slash);
            string leaf = folder.Substring(slash + 1);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        private static void TryWireContract(System.Action wiring, string description)
        {
            try
            {
                wiring();
            }
            catch (System.NotImplementedException)
            {
                Debug.LogWarning("CatDash: contract member not implemented yet (" + description + "). The scene was still " +
                                 "saved; re-run this generator after the owner merges Agent A.");
            }
        }

        private static void SetObject(SerializedObject target, string field, UnityEngine.Object value)
        {
            SerializedProperty property = Find(target, field);
            if (property == null) return;
            property.objectReferenceValue = value;
        }

        private static void SetFloat(SerializedObject target, string field, float value)
        {
            SerializedProperty property = Find(target, field);
            if (property == null) return;
            property.floatValue = value;
        }

        private static void SetInt(SerializedObject target, string field, int value)
        {
            SerializedProperty property = Find(target, field);
            if (property == null) return;
            property.intValue = value;
        }

        private static SerializedProperty Find(SerializedObject target, string field)
        {
            SerializedProperty property = target.FindProperty(field);
            if (property == null)
            {
                Debug.LogWarning("CatDash: " + target.targetObject.GetType().Name + " has no serialized field '" + field +
                                 "' — that wiring step was skipped (frozen contract changed?).");
            }
            return property;
        }
    }
}
