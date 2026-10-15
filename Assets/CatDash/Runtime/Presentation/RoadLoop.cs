using System;
using UnityEngine;

namespace CatDash.Presentation
{
    /// <summary>Bounded road/props recycling. Owner: CONTENT.</summary>
    public class RoadLoop : MonoBehaviour
    {
        [SerializeField] private Transform segmentRoot;
        [SerializeField] private float segmentLength = 20f;
        [SerializeField] private int segmentCount = 6;

        public float SegmentLength { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public int ActiveSegmentCount { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public void ResetToStart(float playerZ) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void RecycleAhead(float playerZ) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
