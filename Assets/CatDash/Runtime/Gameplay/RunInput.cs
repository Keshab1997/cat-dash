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

        public bool InputEnabled { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public void EnableInput() { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void DisableInput() { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Test/debug entry point: raises LaneRequested subject to InputEnabled.</summary>
        public void RaiseSwipe(int direction) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
