using CatDash.Gameplay;
using CatDash.Presentation;
using NUnit.Framework;
using UnityEngine;

namespace CatDash.Tests.EditMode
{
    /// <summary>
    /// Focused HUD state-machine tests. The HUD is deliberately usable unwired (no UGUI references set), so
    /// these tests need no canvas and no UGUI types. Authored by Agent C; execution happens in CI/owner runs.
    /// </summary>
    public class CatDashHudTests
    {
        private GameObject root;
        private CatDashHud hud;

        [SetUp]
        public void SetUp()
        {
            RunController.ResetStatics();
            root = new GameObject("Test HUD");
            hud = root.AddComponent<CatDashHud>();
        }

        [TearDown]
        public void TearDown()
        {
            if (root != null) Object.DestroyImmediate(root);
        }

        [Test]
        public void Hud_Starts_By_Asking_For_A_Run()
        {
            Assert.IsTrue(hud.StartPromptVisible);
            Assert.IsFalse(hud.GameOverVisible);
        }

        [Test]
        public void Running_Hides_The_Start_Prompt()
        {
            hud.OnRunStateChanged(RunState.Running);

            Assert.IsFalse(hud.StartPromptVisible);
            Assert.IsFalse(hud.GameOverVisible);
        }

        [Test]
        public void Distance_Is_Formatted_In_Whole_Metres()
        {
            hud.OnRunStateChanged(RunState.Running);
            hud.OnDistanceChanged(12.7f);

            Assert.AreEqual("12 m", hud.DistanceLabelText);
        }

        [Test]
        public void GameOver_Shows_The_Final_Distance()
        {
            hud.OnRunStateChanged(RunState.Running);
            hud.OnDistanceChanged(123.6f);
            hud.OnRunEnded(123.6f);

            Assert.IsTrue(hud.GameOverVisible);
            Assert.IsFalse(hud.StartPromptVisible);
            Assert.AreEqual("123 m", hud.GameOverDistanceText);
        }

        [Test]
        public void Distance_Freezes_After_The_Run_Ends()
        {
            hud.OnRunStateChanged(RunState.Running);
            hud.OnDistanceChanged(50.4f);
            hud.OnRunEnded(50.4f);

            hud.OnDistanceChanged(999f);

            Assert.AreEqual("50 m", hud.DistanceLabelText, "Distance kept counting after game over.");
            Assert.AreEqual("50 m", hud.GameOverDistanceText);
        }

        [Test]
        public void Ready_After_GameOver_Shows_The_Start_Prompt_Again()
        {
            hud.OnRunStateChanged(RunState.GameOver);
            Assert.IsTrue(hud.GameOverVisible);

            hud.OnRunStateChanged(RunState.Ready);

            Assert.IsTrue(hud.StartPromptVisible);
            Assert.IsFalse(hud.GameOverVisible);
            Assert.AreEqual("0 m", hud.DistanceLabelText);
        }

        [Test]
        public void SetVisible_Hides_Everything_And_Restores_The_State()
        {
            hud.SetVisible(false);
            Assert.IsFalse(hud.StartPromptVisible);
            Assert.IsFalse(hud.GameOverVisible);

            hud.OnRunStateChanged(RunState.GameOver);
            Assert.IsFalse(hud.GameOverVisible, "A hidden HUD must stay hidden.");

            hud.SetVisible(true);
            Assert.IsTrue(hud.GameOverVisible);
        }

        [Test]
        public void OnStartButton_Without_An_Active_Controller_Cannot_Get_Stuck()
        {
            Assert.IsNull(RunController.Active);

            Assert.DoesNotThrow(() => hud.OnStartButton());

            Assert.IsFalse(hud.StartPromptVisible, "The start prompt must not survive a dead Start tap.");
            Assert.IsFalse(hud.GameOverVisible);
        }

        [Test]
        public void OnRestartButton_Without_An_Active_Controller_Returns_To_The_Prompt()
        {
            hud.OnRunEnded(42f);

            Assert.DoesNotThrow(() => hud.OnRestartButton());

            Assert.IsTrue(hud.StartPromptVisible);
            Assert.IsFalse(hud.GameOverVisible);
        }

        [Test]
        public void FormatDistance_Is_Invariant_And_Never_Negative()
        {
            Assert.AreEqual("0 m", CatDashHud.FormatDistance(-5f));
            Assert.AreEqual("0 m", CatDashHud.FormatDistance(0f));
            Assert.AreEqual("1000 m", CatDashHud.FormatDistance(1000.9f));
        }
    }
}
