using System;
using UnityEngine;

namespace CatDash.Gameplay
{
    /// <summary>Forward auto-run + lane interpolation + obstacle contact. Owner: GAMEPLAY.</summary>
    public class PlayerMover : MonoBehaviour
    {
        [SerializeField] private RunController controller;

        public Lane CurrentLane { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        /// <summary>+1 right, -1 left; ignored at the outer lanes.</summary>
        public void Step(int direction) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void MoveToLane(Lane lane) { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Restart state: center lane, zero forward progress.</summary>
        public void ResetToStart() { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
