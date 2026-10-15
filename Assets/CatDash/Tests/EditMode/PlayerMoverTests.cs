using System;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using CatDash.Gameplay;

public class PlayerMoverTests
{
    private GameObject go;
    private RunController rc;
    private PlayerMover mover;

    [SetUp]
    public void SetUp()
    {
        go = new GameObject("PlayerMoverTests");
        rc = go.AddComponent<RunController>();
        mover = go.AddComponent<PlayerMover>();
        SetController(mover, rc);
    }

    [TearDown]
    public void TearDown()
    {
        if (go != null) UnityEngine.Object.DestroyImmediate(go);
    }

    [Test]
    public void Step_AtRightLane_IsIgnored()
    {
        mover.MoveToLane(Lane.Right);
        mover.Step(1);
        Assert.AreEqual(Lane.Right, mover.CurrentLane);
    }

    [Test]
    public void Step_AtLeftLane_IsIgnored()
    {
        mover.MoveToLane(Lane.Left);
        mover.Step(-1);
        Assert.AreEqual(Lane.Left, mover.CurrentLane);
    }

    [Test]
    public void Step_UsesLanesClamp()
    {
        mover.MoveToLane(Lane.Center);
        mover.Step(5);
        Assert.AreEqual(Lane.Right, mover.CurrentLane);
        mover.Step(-10);
        Assert.AreEqual(Lane.Left, mover.CurrentLane);
    }

    [Test]
    public void ResetToStart_ResetsLaneAndLongitudinalPosition()
    {
        mover.transform.position = new Vector3(5f, 0f, 10f);
        mover.ResetToStart();
        Assert.AreEqual(Lane.Center, mover.CurrentLane);
        Assert.AreEqual(0f, mover.transform.position.x, 0.001f);
        Assert.AreEqual(0f, mover.transform.position.z, 0.001f);
    }

    [Test]
    public void HandleObstacleContact_WithObstacleMarker_EndsRun()
    {
        rc.BeginRun();
        var other = new GameObject("obstacle");
        other.AddComponent<ObstacleMarker>();
        var col = other.AddComponent<BoxCollider>();
        mover.HandleObstacleContact(col);
        Assert.AreEqual(RunState.GameOver, rc.State);
        UnityEngine.Object.DestroyImmediate(other);
    }

    [Test]
    public void HandleObstacleContact_WithoutMarker_DoesNotEndRun()
    {
        rc.BeginRun();
        var other = new GameObject("not-obstacle");
        var col = other.AddComponent<BoxCollider>();
        mover.HandleObstacleContact(col);
        Assert.AreEqual(RunState.Running, rc.State);
        UnityEngine.Object.DestroyImmediate(other);
    }

    [Test]
    public void HandleObstacleContact_WithMarker_EndsRun()
    {
        rc.BeginRun();
        var other = new GameObject("obstacle");
        other.AddComponent<ObstacleMarker>();
        var col = other.AddComponent<BoxCollider>();
        mover.HandleObstacleContact(col);
        Assert.AreEqual(RunState.GameOver, rc.State);
        UnityEngine.Object.DestroyImmediate(other);
    }

    [Test]
    public void HandleObstacleContact_WithoutMarker_StaysRunning()
    {
        rc.BeginRun();
        var other = new GameObject("not-obstacle");
        var col = other.AddComponent<BoxCollider>();
        mover.HandleObstacleContact(col);
        Assert.AreEqual(RunState.Running, rc.State);
        UnityEngine.Object.DestroyImmediate(other);
    }

    [Test]
    public void HandleObstacleContact_AfterGameOver_DoesNotNotifyTwice()
    {
        rc.BeginRun();
        int endedCount = 0;
        var observer = new CountingObserver { OnEnded = () => endedCount++ };
        rc.RegisterObserver(observer);
        var other = new GameObject("obstacle");
        other.AddComponent<ObstacleMarker>();
        var col = other.AddComponent<BoxCollider>();
        mover.HandleObstacleContact(col);
        mover.HandleObstacleContact(col);
        Assert.AreEqual(1, endedCount);
        UnityEngine.Object.DestroyImmediate(other);
    }

    [Test]
    public void UnityMessages_OnTriggerEnterAndStay_ArePrivate()
    {
        var enter = typeof(PlayerMover).GetMethod("OnTriggerEnter", BindingFlags.NonPublic | BindingFlags.Instance);
        var stay = typeof(PlayerMover).GetMethod("OnTriggerStay", BindingFlags.NonPublic | BindingFlags.Instance);
        Assert.IsNotNull(enter);
        Assert.IsNotNull(stay);
    }

    private static void SetController(PlayerMover mover, RunController rc)
    {
        var f = typeof(PlayerMover).GetField("controller", BindingFlags.NonPublic | BindingFlags.Instance);
        if (f != null) f.SetValue(mover, rc);
    }

    private class CountingObserver : IRunObserver
    {
        public Action OnEnded;
        public void OnRunStateChanged(RunState state) { }
        public void OnDistanceChanged(float meters) { }
        public void OnRunEnded(float finalMeters) { if (OnEnded != null) OnEnded(); }
    }
}
