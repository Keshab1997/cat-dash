using System.Collections;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
namespace UnityAgentKit.Tests
{
    public class PhysicsSmokeTests
    {
        [UnityTest] public IEnumerator RigidbodyFallsUnderGravity()
        {
            var go = new GameObject("PhysicsSmoke");
            go.transform.position = Vector3.up * 10;
            var body = go.AddComponent<Rigidbody>();
            body.useGravity = true;
            try
            {
                for (int i = 0; i < 10; i++) yield return new WaitForFixedUpdate();
                Assert.Less(go.transform.position.y, 10f);
            }
            finally { Object.Destroy(go); }
        }
    }
}
