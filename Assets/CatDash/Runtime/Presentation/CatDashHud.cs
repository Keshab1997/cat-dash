using System;
using CatDash.Gameplay;
using UnityEngine;

namespace CatDash.Presentation
{
    /// <summary>Score / start / game-over / restart HUD (UGUI). Owner: CONTENT.</summary>
    public class CatDashHud : MonoBehaviour, IRunObserver
    {
        public bool GameOverVisible { get { throw new NotImplementedException("Batch 1: implement per brief."); } }
        public bool StartPromptVisible { get { throw new NotImplementedException("Batch 1: implement per brief."); } }

        public void OnRunStateChanged(RunState state) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void OnDistanceChanged(float meters) { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void OnRunEnded(float finalMeters) { throw new NotImplementedException("Batch 1: implement per brief."); }
        /// <summary>Wired to the Start button (and tap-to-start) by the scene generator.</summary>
        public void OnStartButton() { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void OnRestartButton() { throw new NotImplementedException("Batch 1: implement per brief."); }
        public void SetVisible(bool visible) { throw new NotImplementedException("Batch 1: implement per brief."); }
    }
}
