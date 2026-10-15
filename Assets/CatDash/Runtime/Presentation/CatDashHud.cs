using CatDash.Gameplay;
using UnityEngine;
using UnityEngine.UI;

namespace CatDash.Presentation
{
    /// <summary>Score / start / game-over / restart HUD (UGUI). Owner: CONTENT.</summary>
    /// <remarks>
    /// Every visual reference is optional: an unwired HUD still tracks state (used by EditMode tests) and
    /// never throws. Start/Restart go through the frozen RunController API only
    /// (<c>BeginRun</c> / <c>Restart</c> via <see cref="RunController.Active"/>); distance comes from the
    /// <see cref="IRunObserver"/> callbacks the controller raises.
    /// Registration: Agent A's RunController does not discover observers, so the HUD registers itself with
    /// <see cref="RunController.Active"/> through the frozen RegisterObserver API (as RunInput does) and
    /// unregisters on disable.
    /// </remarks>
    public class CatDashHud : MonoBehaviour, IRunObserver
    {
        [SerializeField] private GameObject startPromptRoot;
        [SerializeField] private GameObject distanceLabelRoot;
        [SerializeField] private GameObject gameOverRoot;
        [SerializeField] private Text distanceLabel;
        [SerializeField] private Text gameOverDistanceLabel;

        private RunController registeredController;
        private bool hudVisible = true;
        private bool gameOver;
        private RunState state = RunState.Ready;
        private float distanceMeters;
        private int shownWholeMeters = -1;
        private string distanceText = "0 m";
        private string gameOverText = "0 m";

        public bool GameOverVisible { get { return hudVisible && gameOver; } }

        public bool StartPromptVisible { get { return hudVisible && !gameOver && state == RunState.Ready; } }

        /// <summary>Observability for tests / editor tooling: the string the distance label shows.</summary>
        public string DistanceLabelText { get { return distanceText; } }

        /// <summary>Observability for tests / editor tooling: the string the game-over panel shows.</summary>
        public string GameOverDistanceText { get { return gameOverText; } }

        /// <summary>Whole metres with a unit suffix, invariant culture. Never negative.</summary>
        public static string FormatDistance(float meters)
        {
            int whole = Mathf.FloorToInt(Mathf.Max(0f, meters));
            return whole.ToString(System.Globalization.CultureInfo.InvariantCulture) + " m";
        }

        private void OnEnable()
        {
            EnsureRegistered();
        }

        private void OnDisable()
        {
            ReleaseRegistration();
        }

        private void Update()
        {
            EnsureRegistered(); // RunController.Active may appear after this component was enabled
        }

        private void EnsureRegistered()
        {
            RunController controller = RunController.Active;
            if (controller == null || registeredController == controller) return;

            ReleaseRegistration();
            registeredController = controller;
            controller.RegisterObserver(this);
        }

        private void ReleaseRegistration()
        {
            if (registeredController != null) registeredController.UnregisterObserver(this);
            registeredController = null;
        }

        public void OnRunStateChanged(RunState runState)
        {
            state = runState;
            if (runState == RunState.Running)
            {
                gameOver = false;
            }
            else if (runState == RunState.Ready)
            {
                gameOver = false;
                distanceMeters = 0f;
                distanceText = FormatDistance(0f);
            }
            else if (runState == RunState.GameOver)
            {
                gameOver = true;
            }
            Apply();
        }

        public void OnDistanceChanged(float meters)
        {
            if (gameOver) return;

            distanceMeters = Mathf.Max(0f, meters);
            distanceText = FormatDistance(distanceMeters);
            Apply();
        }

        public void OnRunEnded(float finalMeters)
        {
            gameOver = true;
            gameOverText = FormatDistance(finalMeters);
            Apply();
        }

        /// <summary>Wired to the Start button (and tap-to-start) by the scene generator.</summary>
        public void OnStartButton()
        {
            RunController controller = RunController.Active;
            if (controller == null)
            {
                Debug.LogWarning("[CatDashHud] OnStartButton: no active RunController; hiding the start prompt so the UI cannot stick.");
                gameOver = false;
                state = RunState.Running;
                Apply();
                return;
            }
            controller.BeginRun();
        }

        public void OnRestartButton()
        {
            RunController controller = RunController.Active;
            if (controller == null)
            {
                Debug.LogWarning("[CatDashHud] OnRestartButton: no active RunController; showing the start prompt again.");
                gameOver = false;
                state = RunState.Ready;
                distanceMeters = 0f;
                distanceText = FormatDistance(0f);
                gameOverText = FormatDistance(0f);
                Apply();
                return;
            }
            controller.Restart();
        }

        public void SetVisible(bool visible)
        {
            hudVisible = visible;
            Apply();
        }

        private void Apply()
        {
            SetActive(startPromptRoot, StartPromptVisible);
            SetActive(gameOverRoot, GameOverVisible);
            SetActive(distanceLabelRoot, hudVisible);

            int whole = Mathf.FloorToInt(distanceMeters);
            if (whole != shownWholeMeters)
            {
                shownWholeMeters = whole;
                if (distanceLabel != null) distanceLabel.text = distanceText;
            }

            if (gameOverDistanceLabel != null && gameOverDistanceLabel.text != gameOverText)
            {
                gameOverDistanceLabel.text = gameOverText;
            }
        }

        private static void SetActive(GameObject target, bool active)
        {
            if (target != null && target.activeSelf != active) target.SetActive(active);
        }
    }
}
