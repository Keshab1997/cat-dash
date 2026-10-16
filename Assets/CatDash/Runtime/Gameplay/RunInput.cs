using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Touch swipe lane input (+ optional clearly-labelled desktop debug keys). Owner: GAMEPLAY.</summary>
    public class RunInput : MonoBehaviour, IRunObserver
    {
        [SerializeField] private float swipeThresholdPixels = 60f;

        /// <summary>-1 = left lane, +1 = right lane. Never raised twice for one gesture.</summary>
        public event Action<int> LaneRequested;

        private bool inputEnabled = false;
        private bool syncing = false;
        private bool tracking = false;
        private Vector2 startPos = Vector2.zero;
        private RunController registeredController;

        public bool InputEnabled { get { return inputEnabled; } }
        public bool IsRegistered { get { return ResolveController() != null; } }

        public void EnableInput() { inputEnabled = true; }
        public void DisableInput() { inputEnabled = false; tracking = false; }

        /// <summary>Test/debug entry point: raises LaneRequested subject to InputEnabled.</summary>
        public void RaiseSwipe(int direction)
        {
            if (!inputEnabled) return;
            LaneRequested?.Invoke(direction);
        }

        public void OnRunStateChanged(RunState state)
        {
            if (state == RunState.Running) EnableInput();
            else DisableInput();
        }

        public void OnDistanceChanged(float meters) { }

        public void OnRunEnded(float finalMeters)
        {
            DisableInput();
        }

        private void Awake()
        {
            TryRegister();
        }

        private void OnEnable()
        {
            TryRegister();
        }

        private void OnDisable()
        {
            if (registeredController != null)
            {
                registeredController.UnregisterObserver(this);
                registeredController = null;
            }
        }

        private RunController ResolveController()
        {
            if (registeredController == null || registeredController != RunController.Active) TryRegister();
            return registeredController;
        }

        private void TryRegister()
        {
            if (registeredController == RunController.Active) return;
            if (registeredController != null)
            {
                registeredController.UnregisterObserver(this);
                registeredController = null;
            }
            if (RunController.Active != null)
            {
                registeredController = RunController.Active;
                registeredController.RegisterObserver(this);
            }
        }

        private void Update()
        {
            if (registeredController == null || registeredController != RunController.Active)
            {
                TryRegister();
            }

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

        /// <summary>Public seam (same convention as RunController.OnApplicationPause) so EditMode tests
        /// and the self-registration path can drive pause/resume directly.</summary>
        public void OnApplicationPause(bool pauseStatus)
        {
            if (syncing) return;
            syncing = true;
            try
            {
                var rc = ResolveController();
                if (pauseStatus)
                {
                    DisableInput();
                    if (rc != null) rc.OnApplicationPause(true);
                }
                else
                {
                    if (rc == null || rc.IsRunning) EnableInput();
                    if (rc != null) rc.OnApplicationPause(false);
                }
            }
            finally
            {
                syncing = false;
            }
        }

        /// <summary>Public seam; see OnApplicationPause.</summary>
        public void OnApplicationFocus(bool hasFocus)
        {
            if (syncing) return;
            syncing = true;
            try
            {
                var rc = ResolveController();
                if (!hasFocus)
                {
                    DisableInput();
                    if (rc != null) rc.OnApplicationFocus(false);
                }
                else
                {
                    if (rc == null || rc.IsRunning) EnableInput();
                    if (rc != null) rc.OnApplicationFocus(true);
                }
            }
            finally
            {
                syncing = false;
            }
        }
    }
}
