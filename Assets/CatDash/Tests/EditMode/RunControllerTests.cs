using System;
using NUnit.Framework;
using UnityEngine;
using CatDash.Gameplay;

public class RunControllerTests
{
    private GameObject go;
    private RunController rc;

    [SetUp]
    public void SetUp()
    {
        RunController.ResetStatics();
        go = new GameObject("RunControllerTests");
        rc = go.AddComponent<RunController>();
    }

    [TearDown]
    public void TearDown()
    {
        if (go != null) UnityEngine.Object.DestroyImmediate(go);
        RunController.ResetStatics();
    }

    [Test]
    public void InitialState_IsReady()
    {
        Assert.AreEqual(RunState.Ready, rc.State);
        Assert.IsFalse(rc.IsRunning);
    }

    [Test]
    public void BeginRun_FromReady_BecomesRunning()
    {
        rc.BeginRun();
        Assert.AreEqual(RunState.Running, rc.State);
        Assert.IsTrue(rc.IsRunning);
    }

    [Test]
    public void EndRun_IsIdempotent()
    {
        rc.BeginRun();
        int endedCount = 0;
        var observer = new CountingObserver { OnEnded = () => endedCount++ };
        rc.RegisterObserver(observer);
        rc.EndRun();
        rc.EndRun();
        Assert.AreEqual(RunState.GameOver, rc.State);
        Assert.AreEqual(1, endedCount);
    }

    [Test]
    public void Restart_ResetsDistanceSpeedState()
    {
        rc.BeginRun();
        rc.Tick(1f);
        rc.EndRun();
        rc.Restart();
        Assert.AreEqual(0f, rc.DistanceMeters, 0.001f);
        Assert.AreEqual(rc.Tuning.startSpeed, rc.SpeedMetersPerSecond, 0.001f);
        Assert.AreEqual(RunState.Running, rc.State);
    }

    [Test]
    public void Tick_ClampsSpeedToMax()
    {
        rc.BeginRun();
        for (int i = 0; i < 1000; i++) rc.Tick(1f);
        Assert.LessOrEqual(rc.SpeedMetersPerSecond, rc.Tuning.maxSpeed + 0.001f);
    }

    [Test]
    public void Tick_WhenPaused_DoesNotAdvanceDistance()
    {
        rc.BeginRun();
        rc.Tick(0.5f);
        float before = rc.DistanceMeters;
        rc.OnApplicationPause(true);
        rc.Tick(0.5f);
        Assert.AreEqual(before, rc.DistanceMeters, 0.001f);
        rc.OnApplicationPause(false);
        rc.Tick(0.5f);
        Assert.Greater(rc.DistanceMeters, before);
    }

    private class CountingObserver : IRunObserver
    {
        public Action OnEnded;
        public void OnRunStateChanged(RunState state) { }
        public void OnDistanceChanged(float meters) { }
        public void OnRunEnded(float finalMeters) { if (OnEnded != null) OnEnded(); }
    }

    [Test]
    public void Active_ClearedOnDestroy_WithoutResetStatics()
    {
        RunController.ResetStatics();
        var go2 = new GameObject("ActiveClear");
        var rc2 = go2.AddComponent<RunController>();
        Assert.AreEqual(rc2, RunController.Active);
        UnityEngine.Object.DestroyImmediate(go2);
        Assert.IsNull(RunController.Active);
    }
}
