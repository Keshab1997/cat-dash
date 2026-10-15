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

            spawner.OnDistanceChanged(200f);

            Assert.Greater(spawner.ActiveObstacleCount, 0, "No obstacle was actually placed over 200 m.");
            Assert.LessOrEqual(spawner.ActiveObstacleCount, spawner.MaxPooledInstances);
            Assert.LessOrEqual(spawner.ActiveObstacleCount, 2, "poolSizePerPrefab = 2 must cap live instances.");
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
            spawner.OnRunStateChanged(RunState.Running);
            spawner.OnDistanceChanged(400f);

            float playerZ = 400f;
            float limit = playerZ - 15f; // despawnBehindDistance default
            int activeFound = 0;
            foreach (Transform child in spawner.transform)
            {
                if (child.name != "Obstacle Pool") continue;
                foreach (Transform instance in child)
                {
                    if (!instance.gameObject.activeSelf) continue;
                    activeFound++;
                    Assert.GreaterOrEqual(instance.position.z, limit,
                                          "Obstacle at z = " + instance.position.z + " was not recycled behind the player.");
                }
            }

            Assert.Greater(activeFound, 0, "No live obstacle was found under the pool object.");
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
