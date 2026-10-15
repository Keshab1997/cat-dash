using System.Collections.Generic;
using UnityEngine;

namespace CatDash.Presentation
{
    /// <summary>Bounded road/props recycling. Owner: CONTENT.</summary>
    /// <remarks>
    /// Segments are world-space Z slots: segment i spans [z, z + SegmentLength]. The loop keeps every
    /// adopted segment inside the window [playerZ - SegmentLength, playerZ - SegmentLength + span) where
    /// span = SegmentLength * segmentCount, so the number of segments in play is constant (bounded) and
    /// recycling is a pure position function of playerZ: no Instantiate/Destroy during a run.
    /// The segment list comes from <c>segmentRoot</c>'s children (the scene generator builds them);
    /// RoadLoop never invents geometry.
    /// </remarks>
    public class RoadLoop : MonoBehaviour
    {
        [SerializeField] private Transform segmentRoot;
        [SerializeField] private float segmentLength = 20f;
        [SerializeField] private int segmentCount = 6;
        [SerializeField] private Transform player;

        private readonly List<Transform> segments = new List<Transform>();
        private bool adopted;

        public float SegmentLength { get { return segmentLength; } }

        /// <summary>Adopted segments currently in play: never more than <c>segmentCount</c>.</summary>
        public int ActiveSegmentCount { get { EnsureAdopted(); return segments.Count; } }

        /// <summary>Scene-generator / test wiring: no reflection, no YAML rewriting.</summary>
        public void Bind(Transform root, Transform playerTransform, float length, int count)
        {
            segmentRoot = root;
            player = playerTransform;
            if (length > 0f) segmentLength = length;
            if (count > 0) segmentCount = count;
            adopted = false;
            EnsureAdopted();
        }

        /// <summary>Segment i starts at playerZ - SegmentLength + i * SegmentLength (run start layout).</summary>
        public void ResetToStart(float playerZ)
        {
            EnsureAdopted();
            if (segments.Count == 0 || segmentLength <= 0f) return;

            float startZ = playerZ - segmentLength;
            for (int i = 0; i < segments.Count; i++)
            {
                SetSegmentZ(segments[i], startZ + i * segmentLength);
            }
        }

        /// <summary>Idempotent: segments already inside the window are left untouched (no per-frame dirtying).</summary>
        public void RecycleAhead(float playerZ)
        {
            EnsureAdopted();
            if (segments.Count == 0 || segmentLength <= 0f) return;

            float span = segmentLength * segments.Count;
            float windowStart = playerZ - segmentLength;
            for (int i = 0; i < segments.Count; i++)
            {
                Transform segment = segments[i];
                if (segment == null) continue;

                float z = segment.position.z;
                float wrapped = windowStart + Mathf.Repeat(z - windowStart, span);
                if (Mathf.Abs(wrapped - z) > 0.001f) SetSegmentZ(segment, wrapped);
            }
        }

        private void Update()
        {
            if (player == null) return;
            RecycleAhead(player.position.z);
        }

        private void EnsureAdopted()
        {
            if (adopted) return;
            adopted = true;
            segments.Clear();
            if (segmentRoot == null) return;

            int limit = Mathf.Max(0, segmentCount);
            for (int i = 0; i < segmentRoot.childCount && segments.Count < limit; i++)
            {
                Transform child = segmentRoot.GetChild(i);
                if (child != null) segments.Add(child);
            }
        }

        private static void SetSegmentZ(Transform segment, float z)
        {
            Vector3 position = segment.position;
            position.z = z;
            segment.position = position;
        }
    }
}
