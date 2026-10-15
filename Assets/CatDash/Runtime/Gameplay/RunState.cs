using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Run lifecycle. FROZEN in the Batch 1 baseline: extend, never rename.</summary>
    public enum RunState { Ready = 0, Running = 1, GameOver = 2 }

    /// <summary>Lane index across the road. FROZEN. Do not reorder.</summary>
    public enum Lane { Left = 0, Center = 1, Right = 2 }

    /// <summary>Lane geometry, single source of truth for runtime and scene layout.</summary>
    public static class Lanes
    {
        public const int Count = 3;
        public const float LaneWidth = 1.8f;
        public static float Offset(Lane lane) { return ((int)lane - 1) * LaneWidth; }
        public static Lane Clamp(Lane lane)
        {
            if ((int)lane < 0) return Lane.Left;
            if ((int)lane > 2) return Lane.Right;
            return lane;
        }
    }

    /// <summary>Tuning shared by Gameplay runtime and the scene generator. Values live in scene data.</summary>
    [Serializable]
    public class RunTuning
    {
        public float startSpeed = 6f;
        public float maxSpeed = 14f;
        public float speedGainPerSecond = 0.35f;
        public float laneWidth = Lanes.LaneWidth;
        public float laneChangeSpeed = 8f;
    }

    /// <summary>Presentation-side observer (HUD, spawner). Registered at runtime by RunController.</summary>
    public interface IRunObserver
    {
        void OnRunStateChanged(RunState state);
        void OnDistanceChanged(float meters);
        void OnRunEnded(float finalMeters);
    }

    /// <summary>Attached by Content to every obstacle prefab. Gameplay tests for this component.</summary>
    public class ObstacleMarker : MonoBehaviour { }
}
