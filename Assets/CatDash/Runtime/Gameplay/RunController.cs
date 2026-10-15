using System;
using System.Collections.Generic;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Owns run lifecycle, distance score and speed ramp. Owner: GAMEPLAY.</summary>
    public class RunController : MonoBehaviour
    {
        /// <summary>Most recently enabled controller, or null. Cleared by OnDisable/ResetStatics.</summary>
        public static RunController Active { get; private set; }

        [SerializeField] private RunTuning tuning = new RunTuning();
        [SerializeField] private Transform player;

        public RunTuning Tuning { get { return tuning; } }
        public Transform Player { get { return player; } }

        public RunState State { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public bool IsRunning { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public float DistanceMeters { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public float SpeedMetersPerSecond { get { throw new NotImplementedException("Batch 1: implement per brief."); } }

        public void BeginRun() { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void Restart() { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Idempotent: only the first call while Running ends the run.</summary>
        public void EndRun() { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void RegisterObserver(IRunObserver observer) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void UnregisterObserver(IRunObserver observer) { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Test hook: clears the static Active reference between PlayMode tests.</summary>
        public static void ResetStatics() { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
