using System;
using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using CatDash.Gameplay;

public class CatDashRunFlowTests
{
    private GameObject playerGo;
    private GameObject obstacleGo;
    private RunController rc;
    private PlayerMover mover;
    private CountingObserver observer;

    [UnitySetUp]
    public IEnumerator SetUp()
    {
        RunController.ResetStatics();

        playerGo = new GameObject("player");
        rc = playerGo.AddComponent<RunController>();
        mover = playerGo.AddComponent<PlayerMover>();
        var playerCol = playerGo.AddComponent<BoxCollider>();
        playerCol.isTrigger = true;
        var rb = playerGo.AddComponent<Rigidbody>();
        rb.isKinematic = true;

        SetController(mover, rc);

        obstacleGo = new GameObject("obstacle");
        obstacleGo.AddComponent<ObstacleMarker>();
        var obstacleCol = obstacleGo.AddComponent<BoxCollider>();

        observer = new CountingObserver();
        rc.RegisterObserver(observer);

        yield return null;
    }

    [UnityTearDown]
    public IEnumerator TearDown()
    {
        if (playerGo != null) UnityEngine.Object.Destroy(playerGo);
        if (obstacleGo != null) UnityEngine.Object.Destroy(obstacleGo);
        RunController.ResetStatics();
        yield return null;
    }

    [UnityTest]
    public IEnumerator ObstacleHit_GameOver_RestartChain()
    {
        rc.BeginRun();

        // Overlap the obstacle with the player so the trigger fires.
        playerGo.transform.position = Vector3.zero;
        obstacleGo.transform.position = Vector3.zero;

        float timeout = 2f;
        float elapsed = 0f;
        while (rc.State != RunState.GameOver && elapsed < timeout)
        {
            elapsed += Time.fixedDeltaTime;
            yield return new WaitForFixedUpdate();
        }

        Assert.AreEqual(RunState.GameOver, rc.State);
        Assert.AreEqual(1, observer.Count);

        float distanceAfterHit = rc.DistanceMeters;
        rc.Tick(0.5f);
        Assert.AreEqual(distanceAfterHit, rc.DistanceMeters, 0.001f);

        rc.Restart();
        Assert.AreEqual(0f, rc.DistanceMeters, 0.001f);
        Assert.AreEqual(RunState.Running, rc.State);

        mover.ResetToStart();
        Assert.AreEqual(Lane.Center, mover.CurrentLane);
        Assert.AreEqual(mover.PlayerZForDistance(0f), playerGo.transform.position.z, 0.001f);

        yield return null;
    }

    private static void SetController(PlayerMover mover, RunController rc)
    {
        var f = typeof(PlayerMover).GetField("controller", BindingFlags.NonPublic | BindingFlags.Instance);
        if (f != null) f.SetValue(mover, rc);
    }

    private class CountingObserver : IRunObserver
    {
        public int Count;
        public void OnRunStateChanged(RunState state) { }
        public void OnDistanceChanged(float meters) { }
        public void OnRunEnded(float finalMeters) { Count++; }
    }
}
