using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using CatDash.Gameplay;

public class RearFollowCameraFollowTests
{
    [UnityTest]
    public IEnumerator Camera_ConvergesToTargetPlusOffset()
    {
        var camGo = new GameObject("cam");
        var cam = camGo.AddComponent<RearFollowCamera>();
        var targetGo = new GameObject("target");

        cam.SetTarget(targetGo.transform);
        camGo.transform.position = Vector3.zero;
        targetGo.transform.position = Vector3.zero;

        for (int i = 0; i < 60; i++)
        {
            yield return null;
        }

        Vector3 desired = cam.ComputeDesiredPosition(targetGo.transform.position);
        Assert.Less(Vector3.Distance(camGo.transform.position, desired), 0.1f);

        UnityEngine.Object.Destroy(camGo);
        UnityEngine.Object.Destroy(targetGo);
        yield return null;
    }
}
