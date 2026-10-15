using System;
using CatDash.Gameplay;
using UnityEngine;

namespace CatDash.Presentation
{
    /// <summary>Bounded obstacle spawning/recycling with guaranteed safe path. Owner: CONTENT.</summary>
    public class ObstacleSpawner : MonoBehaviour, IRunObserver
    {
        [SerializeField] private ObstacleMarker[] obstaclePrefabs;
        [SerializeField] private float rowSpacing = 8f;
        [SerializeField] private float spawnAheadDistance = 60f;
        [SerializeField] private float despawnBehindDistance = 15f;
        [SerializeField] private int poolSizePerPrefab = 8;

        public int ActiveObstacleCount { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public int SpawnedRows { get { throw new NotImplementedException("Batch 1: implement per brief."); } }

        /// <summary>Deterministic layout for tests: same seed = same blocked-lane rows.</summary>
        public void ResetAndReseed(int seed) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void ClearAll() { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Pure helper used by tests: blocked lanes for a row index under the current seed.</summary>
        public Lane[] BlockedLanesForRow(int rowIndex) { throw new NotImplementedException("Batch 1: implement per brief."); }

        public void OnRunStateChanged(RunState state) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void OnDistanceChanged(float meters) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void OnRunEnded(float finalMeters) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
