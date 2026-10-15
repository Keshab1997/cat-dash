using System.Collections.Generic;
using CatDash.Gameplay;
using CatDash.Presentation;
using NUnit.Framework;
using UnityEngine;

namespace CatDash.Tests.EditMode
{
    /// <summary>
    /// Focused tests for obstacle patterns and the bounded pool. Authored by Agent C;
    /// execution happens in CI/owner runs (never in this sandbox).
    /// </summary>
    public class ObstacleSpawnerTests
    {
        private GameObject spawnerRoot;
        private GameObject prefabRoot;
        private ObstacleSpawner spawner;
        private ObstacleMarker prefab;

        [SetUp]
        public void SetUp()
        {
            RunController.ResetStatics();
            spawnerRoot = new GameObject("Test Obstacle Spawner");
            spawner = spawnerRoot.AddComponent<ObstacleSpawner>();

            prefabRoot = new GameObject("Test Obstacle Prefab");
            prefab = prefabRoot.AddComponent<ObstacleMarker>();

            spawner.Configure(new[] { prefab }, 2);
        }

        [TearDown]
        public void TearDown()
        {
            if (spawnerRoot != null) Object.DestroyImmediate(spawnerRoot);
            if (prefabRoot != null) Object.DestroyImmediate(prefabRoot);
        }

        [Test]
        public void BlockedLanes_Are_Deterministic_For_The_Same_Seed()
        {
            spawner.ResetAndReseed(4242);
            List<string> first = SnapshotRows(1, 60);

            spawner.ResetAndReseed(4242);
            List<string> second = SnapshotRows(1, 60);

            CollectionAssert.AreEqual(first, second);
        }

        [Test]
        public void Different_Seeds_Produce_A_Different_Layout()
        {
            spawner.ResetAndReseed(11);
            List<string> first = SnapshotRows(1, 64);

            spawner.ResetAndReseed(12);
            List<string> second = SnapshotRows(1, 64);

            bool differs = false;
            for (int i = 0; i < first.Count && !differs; i++)
            {
                if (first[i] != second[i]) differs = true;
            }
            Assert.IsTrue(differs, "Two different seeds produced identical 64-row layouts.");
        }

        [Test]
        public void Every_Row_Keeps_At_Least_One_Reachable_Free_Lane()
        {
            for (int seed = 1; seed <= 8; seed++)
            {
                spawner.ResetAndReseed(seed);
                for (int row = 0; row < 200; row++)
                {
                    Lane[] blocked = spawner.BlockedLanesForRow(row);

                    Assert.LessOrEqual(blocked.Length, PatternSafety.MaxBlockedPerRow,
                                       "Row " + row + " (seed " + seed + ") blocks more lanes than allowed.");
                    Assert.Less(blocked.Length, Lanes.Count,
                                "Row " + row + " (seed " + seed + ") blocks every lane.");

                    Lane[] free = PatternSafety.FreeLanes(blocked);
                    Assert.GreaterOrEqual(free.Length, 1, "Row " + row + " (seed " + seed + ") has no free lane.");

                    bool reachable = false;
                    for (int i = 0; i < free.Length; i++)
                    {
                        if (PatternSafety.IsRowSafe(blocked, free[i]))
                        {
                            reachable = true;
                            break;
                        }
                    }
                    Assert.IsTrue(reachable, "Row " + row + " (seed " + seed + ") has no reachable free lane.");
                }
            }
        }

        [Test]
        public void Rows_Are_Sorted_And_Free_Of_Duplicates()
        {
            spawner.ResetAndReseed(99);
            for (int row = 0; row < 80; row++)
            {
                Lane[] blocked = spawner.BlockedLanesForRow(row);
                for (int i = 1; i < blocked.Length; i++)
                {
                    Assert.AreNotEqual(blocked[i - 1], blocked[i], "Row " + row + " has a duplicate or unsorted lane.");
                }
            }
        }

        [Test]
        public void Patterns_Actually_Use_The_Allowed_Range()
        {
            spawner.ResetAndReseed(7);

            int rowsWithObstacle = 0;
            int rowsFullyBlocking = 0;
            for (int row = 1; row <= 64; row++)
            {
                Lane[] blocked = spawner.BlockedLanesForRow(row);
                if (blocked.Length >= 1) rowsWithObstacle++;
                if (blocked.Length == PatternSafety.MaxBlockedPerRow) rowsFullyBlocking++;
            }

            Assert.Greater(rowsWithObstacle, 0, "No row was blocked at all: the pattern generator is degenerate.");
            Assert.Greater(rowsFullyBlocking, 0, "No row ever used the maximum block count.");
        }

        [Test]
        public void Running_Fills_The_Window_Ahead_Without_Exceeding_The_Pool()
        {
            spawner.OnRunStateChanged(RunState.Running);
            Assert.Greater(spawner.SpawnedRows, 0, "Starting a run did not prefill the window ahead.");
            Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances);

            // Sweep instead of asserting on one step: whether any given row blocks a lane is seed data, so a
            // single step could legitimately place nothing. Across 320 m the pool must place something.
            int maxActive = 0;
            for (float metres = 0f; metres <= 320f; metres += 8f)
            {
                spawner.OnDistanceChanged(metres);
                maxActive = Mathf.Max(maxActive, spawner.ActiveObstacleCount);

                Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances);
                Assert.LessOrEqual(spawner.ActiveObstacleCount, 2, "poolSizePerPrefab = 2 must cap live instances.");
            }

            Assert.Greater(maxActive, 0, "No obstacle was ever live across 320 m: the pool never placed anything.");
        }

        [Test]
        public void Pool_Stays_Bounded_Across_A_Long_Run()
        {
            spawner.Configure(new[] { prefab }, 2);
            spawner.OnRunStateChanged(RunState.Running);

            for (float metres = 0f; metres <= 2000f; metres += 25f)
            {
                spawner.OnDistanceChanged(metres);
                Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances,
                                   "Live obstacles exceeded the pool at " + metres + " m.");
            }

            Assert.Greater(spawner.SpawnedRows, 100, "A 2 km run should have spawned many rows.");
        }

        [Test]
        public void Obstacles_Behind_The_Player_Are_Recycled()
        {
            // Contract, not hierarchy. The old version walked the "Obstacle Pool" children and treated every
            // active one as proof of a leak — but TrySpawn parents ALL live instances under that same holder
            // (ObstacleSpawner.cs, TrySpawn -> PoolParent), so an active child there says nothing about
            // recycling. It reported an instance live at z = 64 with the despawn limit at 385, which is a real
            // leak the hierarchy walk cannot distinguish from a normal live instance. Drive the distance in
            // rowSpacing (8 m) steps, like the 2 km pool test, and assert through the spawner's own accounting.
            spawner.Configure(new[] { prefab }, 4);
            spawner.OnRunStateChanged(RunState.Running);

            int steps = 0;
            int maxActive = 0;
            for (float metres = 0f; metres <= 2000f; metres += 8f)
            {
                spawner.OnDistanceChanged(metres);

                Assert.AreEqual(0, spawner.CountActiveBehind(metres),
                                "Step " + steps + " (" + metres + " m): live obstacle(s) behind the despawn line.");
                Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances,
                                   "Step " + steps + " (" + metres + " m): live obstacles exceeded the pool.");

                maxActive = Mathf.Max(maxActive, spawner.ActiveObstacleCount);
                steps++;
            }

            Assert.Greater(steps, 200, "The sweep did not run enough steps to be meaningful.");
            Assert.Greater(spawner.SpawnedRows, 0, "The sweep spawned no rows at all.");
            Assert.Greater(maxActive, 0, "No obstacle was ever live across 2 km: the sweep proved nothing.");
        }

        [Test]
        public void Active_Obstacles_Never_Sit_Behind_The_Player()
        {
            // The invariants this test exists for: after any OnDistanceChanged step — stepped or jumped —
            // there is no live obstacle behind the despawn line, and the live count never exceeds the pool.

            // Phase A: stepped run, 8 m steps, 0 -> 2000 m (the steady-state case).
            spawner.Configure(new[] { prefab }, 4);
            spawner.OnRunStateChanged(RunState.Running);
            for (float metres = 0f; metres <= 2000f; metres += 8f)
            {
                spawner.OnDistanceChanged(metres);
                Assert.AreEqual(0, spawner.CountActiveBehind(metres),
                                "Stepped run: live obstacle(s) behind the despawn line at " + metres + " m.");
            }

            // Phase B: a single 400 m jump through a fresh start. This is the case the pre-fix code failed:
            // instances stayed live at z = 64 while the despawn limit was 385 (CD-B1 second CI run).
            spawner.Configure(new[] { prefab }, 2);
            spawner.ResetAndReseed(20261016);
            spawner.OnRunStateChanged(RunState.Running);
            int rowsBeforeJump = spawner.SpawnedRows;

            spawner.OnDistanceChanged(400f);

            Assert.AreEqual(0, spawner.CountActiveBehind(400f),
                            "Jump: live obstacle(s) stayed behind the despawn line after OnDistanceChanged(400f).");
            Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances,
                               "Jump: live obstacles exceeded the pool.");
            Assert.Greater(spawner.SpawnedRows, rowsBeforeJump,
                           "Jump: no row was planned ahead of the player — the planner stalled behind them.");

            // The pool must serve the live window after a jump, not stay spent behind the player.
            int maxActiveAfterJump = 0;
            for (float metres = 400f; metres <= 500f; metres += 8f)
            {
                spawner.OnDistanceChanged(metres);
                maxActiveAfterJump = Mathf.Max(maxActiveAfterJump, spawner.ActiveObstacleCount);
                Assert.AreEqual(0, spawner.CountActiveBehind(metres),
                                "Post-jump run: live obstacle(s) behind the despawn line at " + metres + " m.");
            }

            Assert.Greater(maxActiveAfterJump, 0,
                           "No obstacle ever went live after the jump: the pool stayed spent on skipped rows.");
        }

        [Test]
        public void ClearAll_Returns_Every_Instance_To_The_Pool()
        {
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(120f);
            Assert.Greater(spawner.ActiveObstacleCount, 0);

            spawner.ClearAll();

            Assert.AreEqual(0, spawner.ActiveObstacleCount);
            foreach (Transform child in spawner.transform)
            {
                if (child.name != "Obstacle Pool") continue;
                foreach (Transform instance in child)
                {
                    Assert.IsFalse(instance.gameObject.activeSelf, "Pooled instance " + instance.name + " is still active.");
                }
            }
        }

        [Test]
        public void GameOver_Stops_Spawning()
        {
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(80f);
            int rowsAtDeath = spawner.SpawnedRows;

            spawner.OnRunEnded(80f);
            spawner.OnDistanceChanged(800f);

            Assert.AreEqual(rowsAtDeath, spawner.SpawnedRows);
        }

        [Test]
        public void Ready_State_Resets_Rows_And_Restart_Reproduces_The_Layout()
        {
            spawner.OnRunStateChanged(RunState.Running);
            int rowsAfterFreshStart = spawner.SpawnedRows;
            List<string> firstRun = SnapshotRows(1, 20);
            spawner.OnDistanceChanged(500f);

            spawner.OnRunStateChanged(RunState.Ready);
            Assert.AreEqual(0, spawner.SpawnedRows, "Ready did not reset the row counter.");

            spawner.OnRunStateChanged(RunState.Running);

            Assert.AreEqual(rowsAfterFreshStart, spawner.SpawnedRows, "Restart prefilled a different number of rows.");
            CollectionAssert.AreEqual(firstRun, SnapshotRows(1, 20), "Restart did not reproduce the same layout.");
        }

        [Test]
        public void Spawner_Without_Prefabs_Still_Counts_Rows_And_Places_Nothing()
        {
            spawner.Configure(new ObstacleMarker[0], 4);
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(200f);

            Assert.Greater(spawner.SpawnedRows, 0);
            Assert.AreEqual(0, spawner.ActiveObstacleCount);
            Assert.AreEqual(0, spawner.MaxPooledInstances);
        }

        [Test]
        public void Pooled_Obstacles_Expose_Trigger_Colliders()
        {
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(120f);

            int checkedInstances = 0;
            foreach (Transform poolChild in spawner.transform)
            {
                if (poolChild.name != "Obstacle Pool") continue;
                foreach (Transform instance in poolChild)
                {
                    if (!instance.gameObject.activeSelf) continue;

                    Collider[] colliders = instance.GetComponentsInChildren<Collider>(true);
                    Assert.Greater(colliders.Length, 0, instance.name + " has no collider, so a hit could never register.");
                    for (int i = 0; i < colliders.Length; i++)
                    {
                        Assert.IsTrue(colliders[i].isTrigger,
                                      instance.name + " ships a blocking collider; Agent A's contact needs triggers.");
                    }
                    checkedInstances++;
                }
            }

            Assert.Greater(checkedInstances, 0, "No live obstacle was found to check.");
        }

        [Test]
        public void A_Blocking_Collider_Becomes_A_Trigger_Only_On_The_Clone()
        {
            var source = prefabRoot.AddComponent<BoxCollider>();
            Assert.IsFalse(source.isTrigger);

            spawner.Configure(new[] { prefab }, 1);
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(60f);

            foreach (Transform poolChild in spawner.transform)
            {
                if (poolChild.name != "Obstacle Pool") continue;
                foreach (Transform instance in poolChild)
                {
                    Collider[] colliders = instance.GetComponentsInChildren<Collider>(true);
                    for (int i = 0; i < colliders.Length; i++)
                    {
                        Assert.IsTrue(colliders[i].isTrigger, "The clone kept a blocking collider.");
                    }
                }
            }

            Assert.IsFalse(source.isTrigger, "The source prefab must never be modified.");
        }

        private List<string> SnapshotRows(int fromRow, int toRow)
        {
            var snapshot = new List<string>(toRow - fromRow + 1);
            for (int row = fromRow; row <= toRow; row++)
            {
                Lane[] blocked = spawner.BlockedLanesForRow(row);
                var parts = new List<string>(blocked.Length);
                for (int i = 0; i < blocked.Length; i++) parts.Add(blocked[i].ToString());
                snapshot.Add(string.Join(",", parts.ToArray()));
            }
            return snapshot;
        }
    }
}
