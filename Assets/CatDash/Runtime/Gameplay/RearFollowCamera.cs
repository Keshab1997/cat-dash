using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Rear follow camera with clipping avoidance. Owner: GAMEPLAY.</summary>
    public class RearFollowCamera : MonoBehaviour
    {
        [SerializeField] private Vector3 offset = new Vector3(0f, 3.2f, -5.5f);
        [SerializeField] private float smoothing = 8f;
        [SerializeField] private float lookAheadDistance = 4f;
        [SerializeField] private float lookHeight = 0.6f;

        public Transform Target { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public void SetTarget(Transform target) { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Pure helper: desired world position for a given target position (testable without frames).</summary>
        public Vector3 ComputeDesiredPosition(Vector3 targetPosition) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public Quaternion ComputeDesiredRotation(Vector3 targetPosition) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
