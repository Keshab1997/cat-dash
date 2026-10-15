using System.Collections.Generic;
using CatDash.Gameplay;
using UnityEngine;

namespace CatDash.Presentation
{
    /// <summary>Bounded obstacle spawning/recycling with guaranteed safe path. Owner: CONTENT.</summary>
    /// <remarks>
    /// Layout: rows are logical Z slices at <c>rowIndex * rowSpacing</c> (world Z equals distance in metres;
    /// the spawner and the run origin share z = 0). Row 0 is always left empty as a calm run-in.
    /// Determinism: <see cref="BlockedLanesForRow"/> is a pure function of (seed, rowIndex) — a hash-driven
    /// System.Random per row, so the same seed always yields the same rows in any call order.
    /// Bounds: every obstacle instance comes from a per-prefab pool capped at <c>poolSizePerPrefab</c>;
    /// if a pool is exhausted the lane is simply left free (never an on-the-fly Instantiate, never a
    /// destroyed-then-recreated instance). Obstacles behind the player are returned to their pool.
    /// Registration: Agent A's RunController does not discover observers, so this component registers
    /// itself with <see cref="RunController.Active"/> through the frozen RegisterObserver API (the same
    /// pattern Agent A used for RunInput) and unregisters on disable.
    /// Contact: PlayerMover reacts to triggers only (OnTriggerEnter/OnTriggerStay), so pooled clones are
    /// normalised to expose trigger colliders (never the prefab asset).
    /// </remarks>
    public class ObstacleSpawner : MonoBehaviour, IRunObserver
    {
        [SerializeField] private ObstacleMarker[] obstaclePrefabs;
        [SerializeField] private float rowSpacing = 8f;
        [SerializeField] private float spawnAheadDistance = 60f;
        [SerializeField] private float despawnBehindDistance = 15f;
        [SerializeField] private int poolSizePerPrefab = 8;
        [SerializeField] private int seed = 20261016;
        [SerializeField] private float obstacleYOffset = 0f;
        [SerializeField] private Transform poolRoot;

        private const int MaxRowsPerUpdate = 256;

        private readonly List<ObstacleMarker> active = new List<ObstacleMarker>();
        private readonly List<ObstacleMarker> created = new List<ObstacleMarker>();
        private readonly Dictionary<ObstacleMarker, Stack<ObstacleMarker>> freeByPrefab = new Dictionary<ObstacleMarker, Stack<ObstacleMarker>>();
        private readonly Dictionary<ObstacleMarker, int> createdByPrefab = new Dictionary<ObstacleMarker, int>();
        private readonly Dictionary<ObstacleMarker, ObstacleMarker> prefabOf = new Dictionary<ObstacleMarker, ObstacleMarker>();

        private int spawnedRows;
        private int nextRowIndex = 1;
        private float playerZ;
        private RunState state = RunState.Ready;
        private Transform poolParent;
        private RunController registeredController;

        /// <summary>Obstacles currently in the scene (not pooled); never above <see cref="MaxPooledInstances"/>.</summary>
        public int ActiveObstacleCount
        {
            get
            {
                int count = 0;
                for (int i = 0; i < active.Count; i++)
                {
                    if (active[i] != null) count++;
                }
                return count;
            }
        }

        public int SpawnedRows { get { return spawnedRows; } }

        /// <summary>Upper bound on instantiated obstacle instances: prefabs × poolSizePerPrefab.</summary>
        public int MaxPooledInstances
        {
            get
            {
                int prefabs = obstaclePrefabs == null ? 0 : obstaclePrefabs.Length;
                return prefabs * Mathf.Max(0, poolSizePerPrefab);
            }
        }

        public int Seed { get { return seed; } }

        /// <summary>Scene-generator / test wiring for prebuilt obstacles; drops any existing pool.</summary>
        public void Configure(ObstacleMarker[] prefabs, int poolSize)
        {
            ReleasePooledInstances();
            obstaclePrefabs = prefabs;
            poolSizePerPrefab = Mathf.Max(0, poolSize);
        }

        /// <summary>Deterministic layout for tests: same seed = same blocked-lane rows.</summary>
        public void ResetAndReseed(int newSeed)
        {
            seed = newSeed;
            ClearAll();
            spawnedRows = 0;
            nextRowIndex = 1;
            playerZ = 0f;
        }

        public void ClearAll()
        {
            for (int i = active.Count - 1; i >= 0; i--) ReturnToPool(active[i]);
            active.Clear();
        }

        /// <summary>Pure helper used by tests: blocked lanes for a row index under the current seed.</summary>
        public Lane[] BlockedLanesForRow(int rowIndex)
        {
            var rng = new System.Random(RowSeed(rowIndex));
            int blockedCount = rng.Next(0, PatternSafety.MaxBlockedPerRow + 1);

            var lanes = new[] { Lane.Left, Lane.Center, Lane.Right };
            for (int i = lanes.Length - 1; i > 0; i--)
            {
                int j = rng.Next(i + 1);
                Lane swap = lanes[i];
                lanes[i] = lanes[j];
                lanes[j] = swap;
            }

            var row = new Lane[blockedCount];
            for (int i = 0; i < blockedCount; i++) row[i] = lanes[i];

            // Sanitize enforces MaxBlockedPerRow and "never block every lane", and sorts the row.
            return PatternSafety.Sanitize(row);
        }

        public void OnRunStateChanged(RunState runState)
        {
            state = runState;
            if (runState == RunState.Running)
            {
                // Fresh, seed-identical layout, then fill the window ahead of the player at once.
                ResetAndReseed(seed);
                SpawnRowsUpTo(spawnAheadDistance);
            }
            else if (runState == RunState.Ready)
            {
                ResetAndReseed(seed);
            }
        }

        public void OnDistanceChanged(float meters)
        {
            if (state != RunState.Running) return;

            playerZ = meters;
            DespawnBehind(playerZ);
            SpawnRowsUpTo(playerZ + spawnAheadDistance);

            // Safety net for a large jump (pause/resume, a hitch, or a caller that steps straight to 400 m):
            // nothing may stay live behind the despawn line once this step has finished. The spawn pass below
            // already refuses to plan rows behind the player, so this is normally a cheap no-op; it is kept
            // because a live obstacle behind the player is unreachable waste, and the verify cost is O(active).
            if (AnyActiveObstacleBehind(playerZ)) DespawnBehind(playerZ);
        }

        public void OnRunEnded(float finalMeters)
        {
            playerZ = finalMeters;
            state = RunState.GameOver;
        }

        private void OnEnable()
        {
            EnsureRegistered();
        }

        private void OnDisable()
        {
            ReleaseRegistration();
        }

        private void Update()
        {
            EnsureRegistered(); // RunController.Active may appear after this component was enabled
        }

        private void EnsureRegistered()
        {
            RunController controller = RunController.Active;
            if (controller == null || registeredController == controller) return;

            ReleaseRegistration();
            registeredController = controller;
            controller.RegisterObserver(this);
        }

        private void ReleaseRegistration()
        {
            if (registeredController != null) registeredController.UnregisterObserver(this);
            registeredController = null;
        }

        private int RowSeed(int rowIndex)
        {
            unchecked
            {
                return (seed * 73856093) ^ (rowIndex * 19349663) ^ 0x5F3759DF;
            }
        }

        private void SpawnRowsUpTo(float zLimit)
        {
            if (rowSpacing <= 0f) return;

            // CD-B1 second CI run (2026-10-16): after a single OnDistanceChanged(400f) jump with
            // poolSizePerPrefab = 2, an instance stayed live at z = 64 while the despawn limit was 385 — a
            // 321 m gap BEHIND the player (row 8; reported by ObstacleSpawnerTests). The spawn pass resumed
            // at the oldest unplanned row and rented pool instances for rows the player had already passed,
            // so the pool was spent behind the player instead of in the window he is running into. Rows
            // fully behind the live line are therefore skipped, never populated: they cannot be reached.
            // (The stepped 0 -> 2000 m sweep never exposed this, because each step only planned ~8 m of new
            // rows, all of them ahead of the line.)
            float liveStart = DespawnLimit(playerZ);
            int firstLiveRow = Mathf.Max(1, Mathf.CeilToInt(liveStart / rowSpacing));
            if (nextRowIndex < firstLiveRow) nextRowIndex = firstLiveRow;

            int guard = 0;
            while (nextRowIndex * rowSpacing <= zLimit && guard < MaxRowsPerUpdate)
            {
                int rowIndex = nextRowIndex;
                nextRowIndex++;
                guard++;

                if (rowIndex * rowSpacing < liveStart) continue; // belt and braces behind the fast-forward
                SpawnRow(rowIndex);
            }
        }

        private void SpawnRow(int rowIndex)
        {
            Lane[] blocked = BlockedLanesForRow(rowIndex);
            float rowZ = rowIndex * rowSpacing;
            for (int i = 0; i < blocked.Length; i++)
            {
                TrySpawn(blocked[i], rowZ, rowIndex);
            }
            spawnedRows++;
        }

        private bool TrySpawn(Lane lane, float rowZ, int rowIndex)
        {
            ObstacleMarker prefab = PickPrefab(rowIndex, lane);
            if (prefab == null) return false;

            // Pool exhausted => leave the lane free. That can only ever remove a hazard.
            ObstacleMarker instance = Rent(prefab);
            if (instance == null) return false;

            Transform instanceTransform = instance.transform;
            instanceTransform.SetParent(PoolParent, false);
            instanceTransform.rotation = transform.rotation;
            instanceTransform.position = transform.position +
                                        new Vector3(Lanes.Offset(lane), obstacleYOffset, rowZ);
            instance.gameObject.SetActive(true);
            active.Add(instance);
            return true;
        }

        private ObstacleMarker PickPrefab(int rowIndex, Lane lane)
        {
            if (obstaclePrefabs == null || obstaclePrefabs.Length == 0) return null;

            int start = Mathf.Abs(rowIndex + (int)lane) % obstaclePrefabs.Length;
            for (int i = 0; i < obstaclePrefabs.Length; i++)
            {
                ObstacleMarker candidate = obstaclePrefabs[(start + i) % obstaclePrefabs.Length];
                if (candidate != null) return candidate;
            }
            return null;
        }

        private ObstacleMarker Rent(ObstacleMarker prefab)
        {
            Stack<ObstacleMarker> free;
            if (freeByPrefab.TryGetValue(prefab, out free))
            {
                while (free.Count > 0)
                {
                    ObstacleMarker reused = free.Pop();
                    if (reused != null) return reused;
                }
            }

            int spawned;
            if (!createdByPrefab.TryGetValue(prefab, out spawned)) spawned = 0;
            if (spawned >= Mathf.Max(0, poolSizePerPrefab)) return null;

            ObstacleMarker instance = UnityEngine.Object.Instantiate(prefab);
            instance.name = prefab.name + "_pooled";
            ApplyContactContract(instance);
            createdByPrefab[prefab] = spawned + 1;
            created.Add(instance);
            prefabOf[instance] = prefab;
            return instance;
        }

        private void ReturnToPool(ObstacleMarker instance)
        {
            if (instance == null) return;

            instance.gameObject.SetActive(false);
            instance.transform.SetParent(PoolParent, false);

            ObstacleMarker prefab;
            if (prefabOf.TryGetValue(instance, out prefab) && prefab != null)
            {
                Stack<ObstacleMarker> free;
                if (!freeByPrefab.TryGetValue(prefab, out free))
                {
                    free = new Stack<ObstacleMarker>();
                    freeByPrefab[prefab] = free;
                }
                free.Push(instance);
            }
            else
            {
                // Owner prefab is gone (asset change / teardown): drop the instance instead of leaking it.
                DestroyObject(instance.gameObject);
            }
        }

        private Transform PoolParent
        {
            get
            {
                if (poolRoot != null) return poolRoot;
                if (poolParent == null)
                {
                    var holder = new GameObject("Obstacle Pool");
                    holder.transform.SetParent(transform, false);
                    poolParent = holder.transform;
                }
                return poolParent;
            }
        }

        /// <summary>World Z below which an obstacle counts as behind the player. Single source for the rule.</summary>
        private float DespawnLimit(float playerZValue)
        {
            return playerZValue - Mathf.Max(0f, despawnBehindDistance);
        }

        /// <summary>
        /// Test seam: how many live obstacles sit behind the despawn line for this player position. The
        /// contract is that this is 0 whenever an OnDistanceChanged step has returned; recycled instances are
        /// inactive and back in their per-prefab pool, so they are not counted. Assertions should use this
        /// (or ActiveObstacleCount) rather than walking the "Obstacle Pool" hierarchy: TrySpawn parents every
        /// live instance under that same holder, so an active child there is not proof of a leak.
        /// </summary>
        public int CountActiveBehind(float playerZValue)
        {
            float limit = DespawnLimit(playerZValue);
            int behind = 0;
            for (int i = 0; i < active.Count; i++)
            {
                ObstacleMarker obstacle = active[i];
                if (obstacle == null) continue;
                if (obstacle.transform.position.z < limit) behind++;
            }
            return behind;
        }

        /// <summary>True when any live obstacle is still behind the despawn line (see <see cref="CountActiveBehind"/>).</summary>
        private bool AnyActiveObstacleBehind(float playerZValue)
        {
            return CountActiveBehind(playerZValue) > 0;
        }

        private void DespawnBehind(float playerZValue)
        {
            float limit = DespawnLimit(playerZValue);
            for (int i = active.Count - 1; i >= 0; i--)
            {
                ObstacleMarker obstacle = active[i];
                if (obstacle == null)
                {
                    active.RemoveAt(i);
                    continue;
                }
                if (obstacle.transform.position.z >= limit) continue;

                active.RemoveAt(i);
                ReturnToPool(obstacle);
            }
        }

        /// <summary>
        /// Agent A's PlayerMover reacts to trigger contacts only. Every collider of a pooled clone therefore
        /// becomes a trigger, and a generated trigger BoxCollider is added when the source ships none.
        /// Only the clone is touched: the prefab asset is never modified.
        /// </summary>
        private static void ApplyContactContract(ObstacleMarker instance)
        {
            Collider[] colliders = instance.GetComponentsInChildren<Collider>(true);
            if (colliders.Length > 0)
            {
                for (int i = 0; i < colliders.Length; i++)
                {
                    if (colliders[i] != null) colliders[i].isTrigger = true;
                }
                return;
            }

            var box = instance.gameObject.AddComponent<BoxCollider>();
            box.isTrigger = true;
            Bounds bounds = MeasureInstanceBounds(instance.gameObject);
            box.center = bounds.center - instance.transform.position;
            box.size = new Vector3(Mathf.Max(0.2f, bounds.size.x), Mathf.Max(0.2f, bounds.size.y),
                                   Mathf.Max(0.2f, bounds.size.z));
        }

        private static Bounds MeasureInstanceBounds(GameObject root)
        {
            Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) return new Bounds(new Vector3(0f, 0.45f, 0f), new Vector3(0.9f, 0.9f, 0.9f));

            Bounds bounds = renderers[0].bounds;
            for (int i = 1; i < renderers.Length; i++) bounds.Encapsulate(renderers[i].bounds);
            return bounds;
        }

        private void ReleasePooledInstances()
        {
            ClearAll();
            for (int i = 0; i < created.Count; i++)
            {
                if (created[i] != null) DestroyObject(created[i].gameObject);
            }
            created.Clear();
            freeByPrefab.Clear();
            createdByPrefab.Clear();
            prefabOf.Clear();
        }

        private static void DestroyObject(GameObject target)
        {
            if (target == null) return;
            if (Application.isPlaying) UnityEngine.Object.Destroy(target);
            else UnityEngine.Object.DestroyImmediate(target);
        }
    }
}
