using NUnit.Framework;
using UnityEngine;
using System.Reflection;
using CatDash.Gameplay;

public class RearFollowCameraTests
{
    private GameObject go;
    private RearFollowCamera cam;

    [SetUp]
    public void SetUp()
    {
        go = new GameObject("RearFollowCameraTests");
        cam = go.AddComponent<RearFollowCamera>();
    }

    [TearDown]
    public void TearDown()
    {
        if (go != null) UnityEngine.Object.DestroyImmediate(go);
    }

    [Test]
    public void ComputeDesiredPosition_AddsOffset()
    {
        Vector3 target = new Vector3(1f, 2f, 3f);
        Vector3 expected = target + new Vector3(0f, 3.2f, -5.5f);
        Vector3 actual = cam.ComputeDesiredPosition(target);
        Assert.AreEqual(expected.x, actual.x, 0.001f);
        Assert.AreEqual(expected.y, actual.y, 0.001f);
        Assert.AreEqual(expected.z, actual.z, 0.001f);
    }

    [Test]
    public void SetTarget_StoresTarget()
    {
        var targetGo = new GameObject("target");
        cam.SetTarget(targetGo.transform);
        Assert.AreEqual(targetGo.transform, cam.Target);
        UnityEngine.Object.DestroyImmediate(targetGo);
    }

    [Test]
    public void ComputeDesiredRotation_IsFinite()
    {
        Quaternion q = cam.ComputeDesiredRotation(new Vector3(0f, 0f, 0f));
        Assert.IsFalse(float.IsNaN(q.x) || float.IsNaN(q.y) || float.IsNaN(q.z) || float.IsNaN(q.w));
    }

    [Test]
    public void ComputeDesiredPosition_ClampsLowOffsetY()
    {
        var f = typeof(RearFollowCamera).GetField("offset", BindingFlags.NonPublic | BindingFlags.Instance);
        Vector3 off = (Vector3)f.GetValue(cam);
        off.y = 0.5f;
        f.SetValue(cam, off);
        Vector3 target = new Vector3(1f, 2f, 3f);
        Vector3 pos = cam.ComputeDesiredPosition(target);
        Assert.AreEqual(target.y + 2.2f, pos.y, 0.001f);
    }
}
