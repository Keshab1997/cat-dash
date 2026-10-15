using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Touch swipe lane input (+ optional clearly-labelled desktop debug keys). Owner: GAMEPLAY.</summary>
    public class RunInput : MonoBehaviour
    {
        [SerializeField] private float swipeThresholdPixels = 60f;

        /// <summary>-1 = left lane, +1 = right lane. Never raised twice for one gesture.</summary>
        public event Action<int> LaneRequested;

        private bool inputEnabled = false;
        private bool tracking = false;
        private Vector2 startPos = Vector2.zero;

        public bool InputEnabled { get { return inputEnabled; } }

        public void EnableInput() { inputEnabled = true; }
        public void DisableInput() { inputEnabled = false; tracking = false; }

        /// <summary>Test/debug entry point: raises LaneRequested subject to InputEnabled.</summary>
        public void RaiseSwipe(int direction)
        {
            if (!inputEnabled) return;
            LaneRequested?.Invoke(direction);
        }

        private void Update()
        {
            if (!inputEnabled) return;

            if (Input.touchCount > 0)
            {
                Touch t = Input.GetTouch(0);
                if (t.phase == TouchPhase.Began)
                {
                    startPos = t.position;
                    tracking = true;
                }
                else if (tracking && (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled))
                {
                    float dx = t.position.x - startPos.x;
                    if (Mathf.Abs(dx) >= swipeThresholdPixels)
                    {
                        LaneRequested?.Invoke(dx > 0 ? 1 : -1);
                    }
                    tracking = false;
                }
            }
            else
            {
                if (Input.GetMouseButtonDown(0))
                {
                    startPos = Input.mousePosition;
                    tracking = true;
                }
                else if (tracking && Input.GetMouseButtonUp(0))
                {
                    float dx = Input.mousePosition.x - startPos.x;
                    if (Mathf.Abs(dx) >= swipeThresholdPixels)
                    {
                        LaneRequested?.Invoke(dx > 0 ? 1 : -1);
                    }
                    tracking = false;
                }
            }

            // Clearly-labelled desktop debug keys (optional).
            if (Input.GetKeyDown(KeyCode.LeftArrow)) RaiseSwipe(-1);
            if (Input.GetKeyDown(KeyCode.RightArrow)) RaiseSwipe(1);
        }

        private void OnApplicationPause(bool pauseStatus)
        {
            if (pauseStatus) DisableInput();
        }

        private void OnApplicationFocus(bool hasFocus)
        {
            if (!hasFocus) DisableInput();
        }
    }
}
