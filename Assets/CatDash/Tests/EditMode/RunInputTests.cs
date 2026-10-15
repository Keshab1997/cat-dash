using System;
using NUnit.Framework;
using UnityEngine;
using CatDash.Gameplay;

public class RunInputTests
{
    private GameObject go;
    private RunController rc;
    private RunInput input;

    [SetUp]
    public void SetUp()
    {
        go = new GameObject("RunInputTests");
        rc = go.AddComponent<RunController>();
        input = go.AddComponent<RunInput>();
        rc.RegisterObserver(input);
    }

    [TearDown]
    public void TearDown()
    {
        if (go != null) UnityEngine.Object.DestroyImmediate(go);
    }

    [Test]
    public void RaiseSwipe_WhenDisabled_DoesNotEmit()
    {
        int count = 0;
        input.LaneRequested += d => count++;
        input.RaiseSwipe(1);
        Assert.AreEqual(0, count);
    }

    [Test]
    public void RaiseSwipe_WhenEnabled_EmitsDirection()
    {
        input.EnableInput();
        int count = 0;
        int last = 0;
        input.LaneRequested += d => { count++; last = d; };
        input.RaiseSwipe(-1);
        Assert.AreEqual(1, count);
        Assert.AreEqual(-1, last);
    }

    [Test]
    public void RunState_Running_EnablesInput()
    {
        rc.BeginRun();
        Assert.IsTrue(input.InputEnabled);
    }

    [Test]
    public void RunState_GameOver_DisablesInput()
    {
        rc.BeginRun();
        rc.EndRun();
        Assert.IsFalse(input.InputEnabled);
    }

    [Test]
    public void PauseResumeCycle_DistanceStaysAndInputReenabled()
    {
        rc.BeginRun();
        rc.Tick(0.5f);
        float before = rc.DistanceMeters;
        input.OnApplicationPause(true);
        Assert.IsFalse(input.InputEnabled);
        rc.Tick(0.5f);
        Assert.AreEqual(before, rc.DistanceMeters, 0.001f);
        rc.Restart();
        Assert.IsTrue(input.InputEnabled);
    }

    [Test]
    public void PauseResume_WhenRunning_ReenablesInput()
    {
        rc.BeginRun();
        Assert.IsTrue(input.InputEnabled);
        input.OnApplicationPause(true);
        Assert.IsFalse(input.InputEnabled);
        input.OnApplicationPause(false);
        Assert.IsTrue(input.InputEnabled);
    }

    [Test]
    public void PauseResume_AfterGameOver_StaysDisabled()
    {
        rc.BeginRun();
        rc.EndRun();
        input.OnApplicationPause(true);
        input.OnApplicationPause(false);
        Assert.IsFalse(input.InputEnabled);
    }

    [Test]
    public void FocusLossAndRegain_WhenRunning_MatchesPauseBehavior()
    {
        rc.BeginRun();
        input.OnApplicationFocus(false);
        rc.OnApplicationFocus(false);
        Assert.IsFalse(input.InputEnabled);
        input.OnApplicationFocus(true);
        rc.OnApplicationFocus(true);
        Assert.IsTrue(input.InputEnabled);
    }

    [Test]
    public void FocusPauseInterleaving_WhenRunning_ResumesInputAndFreezesDistance()
    {
        rc.BeginRun();
        float before = rc.DistanceMeters;
        input.OnApplicationFocus(false);
        rc.OnApplicationFocus(false);
        input.OnApplicationPause(true);
        rc.OnApplicationPause(true);
        rc.Tick(0.5f);
        Assert.AreEqual(before, rc.DistanceMeters, 0.001f);
        input.OnApplicationPause(false);
        rc.OnApplicationPause(false);
        input.OnApplicationFocus(true);
        rc.OnApplicationFocus(true);
        Assert.IsTrue(input.InputEnabled);
    }

    [Test]
    public void FocusPauseInterleaving_AfterGameOver_StaysDisabled()
    {
        rc.BeginRun();
        rc.EndRun();
        input.OnApplicationFocus(false);
        input.OnApplicationPause(true);
        input.OnApplicationPause(false);
        input.OnApplicationFocus(true);
        Assert.IsFalse(input.InputEnabled);
    }

    [Test]
    public void IsRegistered_TrueImmediatelyAfterAddComponent()
    {
        var go2 = new GameObject("reg");
        var rc2 = go2.AddComponent<RunController>();
        var input2 = go2.AddComponent<RunInput>();
        Assert.IsTrue(input2.IsRegistered);
        UnityEngine.Object.DestroyImmediate(go2);
        RunController.ResetStatics();
    }
}
