using System;
using System.Collections.Generic;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Owns run lifecycle, distance score and speed ramp. Owner: GAMEPLAY.</summary>
    public class RunController : MonoBehaviour
    {
        private static RunController active;
        private static bool activeScanned = false;
        /// <summary>Most recently enabled controller, or null. Cleared by OnDisable/ResetStatics.</summary>
        public static RunController Active
        {
            get
            {
                if (active == null && !activeScanned)
                {
                    active = UnityEngine.Object.FindFirstObjectByType<RunController>();
                    activeScanned = true;
                }
                if (active == null && !UnityEngine.Object.ReferenceEquals(active, null))
                {
                    active = null;
                    activeScanned = false;
                }
                return active;
            }
            private set
            {
                if (value != null && activeScanned) return;
                active = value;
                if (value != null) activeScanned = false;
            }
        }

        [SerializeField] private RunTuning tuning = new RunTuning();
        [SerializeField] private Transform player;

        public RunTuning Tuning { get { return tuning; } }
        public Transform Player { get { return player; } }

        private RunState state = RunState.Ready;
        private float distanceMeters = 0f;
        private float speedMetersPerSecond = 0f;
        private bool speedInitialized = false;
        private readonly List<IRunObserver> observers = new List<IRunObserver>();
        private bool paused = false;

        public RunState State { get { return state; } }
        public bool IsRunning { get { return state == RunState.Running; } }
        /// <summary>Test seam: number of times OnApplicationPause has been invoked.</summary>
        public int PauseCallCount { get; private set; }
        public float DistanceMeters { get { return distanceMeters; } }
        public float SpeedMetersPerSecond
        {
            get
            {
                if (!speedInitialized)
                {
                    if (tuning == null) tuning = new RunTuning();
                    speedMetersPerSecond = tuning.startSpeed;
                    speedInitialized = true;
                }
                return speedMetersPerSecond;
            }
        }

        private void Awake()
        {
            if (tuning == null) tuning = new RunTuning();
            speedMetersPerSecond = tuning.startSpeed;
            speedInitialized = true;
            Active = this;
        }

        private void OnEnable() { Active = this; }
        private void OnDisable() { if (active == this) active = null; }
        private void OnDestroy() { if (active == this) active = null; }

        public void BeginRun()
        {
            if (state != RunState.Ready) return;
            if (tuning == null) tuning = new RunTuning();
            state = RunState.Running;
            paused = false;
            speedMetersPerSecond = tuning.startSpeed;
            speedInitialized = true;
            NotifyStateChanged();
        }

        public void Restart()
        {
            if (tuning == null) tuning = new RunTuning();
            distanceMeters = 0f;
            speedMetersPerSecond = tuning.startSpeed;
            speedInitialized = true;
            state = RunState.Running;
            paused = false;
            NotifyStateChanged();
            NotifyDistanceChanged();
        }

        /// <summary>Idempotent: only the first call while Running ends the run.</summary>
        public void EndRun()
        {
            if (state != RunState.Running) return;
            state = RunState.GameOver;
            paused = false;
            NotifyStateChanged();
            foreach (var o in observers.ToArray())
            {
                try { o.OnRunEnded(distanceMeters); } catch { }
            }
        }

        public void RegisterObserver(IRunObserver observer)
        {
            if (observer == null) return;
            if (!observers.Contains(observer)) observers.Add(observer);
        }

        public void UnregisterObserver(IRunObserver observer)
        {
            observers.Remove(observer);
        }

        /// <summary>Test hook: clears the static Active reference between PlayMode tests.</summary>
        public static void ResetStatics() { active = null; activeScanned = false; }

        /// <summary>Test hook: advances the simulation by deltaTime.</summary>
        public void Tick(float deltaTime)
        {
            if (!IsRunning) return;
            if (paused) return;
            if (tuning == null) tuning = new RunTuning();
            speedMetersPerSecond = Mathf.Min(tuning.maxSpeed, speedMetersPerSecond + tuning.speedGainPerSecond * deltaTime);
            speedInitialized = true;
            distanceMeters += speedMetersPerSecond * deltaTime;
            NotifyDistanceChanged();
        }

        private void Update()
        {
            Tick(Time.deltaTime);
        }

        public void OnApplicationPause(bool pauseStatus)
        {
            PauseCallCount++;
            paused = pauseStatus;
            var input = UnityEngine.Object.FindFirstObjectByType<RunInput>();
            if (input != null) input.OnApplicationPause(pauseStatus);
        }

        public void OnApplicationFocus(bool hasFocus)
        {
            paused = !hasFocus;
            var input = UnityEngine.Object.FindFirstObjectByType<RunInput>();
            if (input != null) input.OnApplicationFocus(hasFocus);
        }

        private void NotifyStateChanged()
        {
            foreach (var o in observers.ToArray())
            {
                try { o.OnRunStateChanged(state); } catch { }
            }
        }

        private void NotifyDistanceChanged()
        {
            foreach (var o in observers.ToArray())
            {
                try { o.OnDistanceChanged(distanceMeters); } catch { }
            }
        }
    }
}
