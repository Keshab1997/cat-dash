using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Forward auto-run + lane interpolation + obstacle contact. Owner: GAMEPLAY.</summary>
    public class PlayerMover : MonoBehaviour
    {
        [SerializeField] private RunController controller;

        private Lane currentLane = Lane.Center;

        public Lane CurrentLane { get { return currentLane; } }

        /// <summary>+1 right, -1 left; ignored at the outer lanes.</summary>
        public void Step(int direction)
        {
            currentLane = Lanes.Clamp((Lane)((int)currentLane + direction));
        }

        public void MoveToLane(Lane lane)
        {
            currentLane = Lanes.Clamp(lane);
        }

        /// <summary>Restart state: center lane, zero forward progress. DistanceMeters-ই scene-এর single longitudinal basis (C-র spawner এটার উপর ভরসা করবে).</summary>
        public void ResetToStart()
        {
            currentLane = Lane.Center;
            if (transform != null)
            {
                Vector3 pos = transform.position;
                pos.x = Lanes.Offset(Lane.Center);
                pos.z = PlayerZForDistance(0f);
                transform.position = pos;
            }
        }

        /// <summary>Maps a run distance to the player's world Z. DistanceMeters-ই scene-এর single longitudinal basis.</summary>
        public float PlayerZForDistance(float distanceMeters)
        {
            return distanceMeters;
        }

        private void Update()
        {
            if (controller == null) return;
            if (!controller.IsRunning) return;
            float dt = Time.deltaTime;
            Vector3 pos = transform.position;
            pos.z += controller.SpeedMetersPerSecond * dt;
            float targetX = Lanes.Offset(currentLane);
            float changeSpeed = 8f;
            if (controller.Tuning != null) changeSpeed = controller.Tuning.laneChangeSpeed;
            pos.x = Mathf.MoveTowards(pos.x, targetX, changeSpeed * dt);
            transform.position = pos;
        }

        /// <summary>Test seam: central obstacle-contact handling.</summary>
        public void HandleObstacleContact(Collider other)
        {
            if (controller == null) return;
            if (!controller.IsRunning) return;
            if (other == null) return;
            if (other.GetComponent<ObstacleMarker>() != null)
            {
                controller.EndRun();
            }
        }

        private void OnTriggerEnter(Collider other)
        {
            HandleObstacleContact(other);
        }

        private void OnTriggerStay(Collider other)
        {
            HandleObstacleContact(other);
        }
    }
}
