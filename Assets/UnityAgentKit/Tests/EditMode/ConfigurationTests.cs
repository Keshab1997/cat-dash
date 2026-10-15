using NUnit.Framework;
using UnityEngine;
namespace UnityAgentKit.Tests
{
    public class ConfigurationTests
    {
        [Test] public void GravityPointsDown() { Assert.Less(Physics.gravity.y, 0f); }
        [Test] public void TimeStepIsPositive() { Assert.Greater(Time.fixedDeltaTime, 0f); }
    }
}
