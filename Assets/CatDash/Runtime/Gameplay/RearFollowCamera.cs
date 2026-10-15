using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Rear follow camera with clipping avoidance. Owner: GAMEPLAY.</summary>
    public class RearFollowCamera : MonoBehaviour
    {
        private const float MinYOffset = 2.2f;

        [SerializeField] private Vector3 offset = new Vector3(0f, 3.2f, -5.5f);
        [SerializeField] private float smoothing = 8f;
        [SerializeField] private float lookAheadDistance = 4f;
        [SerializeField] private float lookHeight = 0.6f;

        private Transform target;

        public Transform Target { get { return target; } }

        public void SetTarget(Transform target)
        {
            this.target = target;
        }

        /// <summary>Pure helper: desired world position for a given target position (testable without frames).</summary>
        public Vector3 ComputeDesiredPosition(Vector3 targetPosition)
        {
            Vector3 position = targetPosition + offset;
            if (offset.y < MinYOffset)
            {
                position.y = targetPosition.y + MinYOffset;
            }
            return position;
        }

        public Quaternion ComputeDesiredRotation(Vector3 targetPosition)
        {
            Vector3 position = ComputeDesiredPosition(targetPosition);
            Vector3 look = targetPosition + new Vector3(0f, lookHeight, lookAheadDistance);
            Vector3 dir = look - position;
            if (dir.sqrMagnitude < 0.0001f) return Quaternion.identity;
            if (!float.IsFinite(dir.x) || !float.IsFinite(dir.y) || !float.IsFinite(dir.z)) return Quaternion.identity;
            return Quaternion.LookRotation(dir);
        }

        private void LateUpdate()
        {
            if (target == null) return;
            float dt = Time.deltaTime;
            float t = Mathf.Clamp01(smoothing * dt);
            Vector3 desiredPos = ComputeDesiredPosition(target.position);
            transform.position = Vector3.Lerp(transform.position, desiredPos, t);
            Quaternion desiredRot = ComputeDesiredRotation(target.position);
            transform.rotation = Quaternion.Slerp(transform.rotation, desiredRot, t);
        }
    }
}
