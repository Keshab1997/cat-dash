using CatDash.Gameplay;
using CatDash.Presentation;
using NUnit.Framework;

namespace CatDash.Tests.EditMode
{
    /// <summary>Focused tests for the pure pattern rules. Authored by Agent C; execution happens in CI/manual runs.</summary>
    public class PatternSafetyTests
    {
        [Test]
        public void FreeLanes_Null_Row_Leaves_Every_Lane_Free()
        {
            Lane[] free = PatternSafety.FreeLanes(null);

            Assert.AreEqual(Lanes.Count, free.Length);
            CollectionAssert.AreEqual(new[] { Lane.Left, Lane.Center, Lane.Right }, free);
        }

        [Test]
        public void FreeLanes_Returns_The_Complement_In_Lane_Order()
        {
            Lane[] free = PatternSafety.FreeLanes(new[] { Lane.Left, Lane.Right });

            Assert.AreEqual(1, free.Length);
            Assert.AreEqual(Lane.Center, free[0]);
        }

        [Test]
        public void FreeLanes_Does_Not_Modify_The_Input_Row()
        {
            Lane[] blocked = { Lane.Center, Lane.Left };
            PatternSafety.FreeLanes(blocked);

            CollectionAssert.AreEqual(new[] { Lane.Center, Lane.Left }, blocked);
        }

        [Test]
        public void IsRowSafe_Accepts_A_Free_Lane_Next_Door()
        {
            Assert.IsTrue(PatternSafety.IsRowSafe(new[] { Lane.Left }, Lane.Center));
            Assert.IsTrue(PatternSafety.IsRowSafe(new[] { Lane.Left, Lane.Center }, Lane.Right));
        }

        [Test]
        public void IsRowSafe_Rejects_Two_Lane_Jump_And_All_Blocked()
        {
            // Only the left lane is free, the cat sits on the right: two lanes away.
            Assert.IsFalse(PatternSafety.IsRowSafe(new[] { Lane.Center, Lane.Right }, Lane.Right));

            Lane[] everything = { Lane.Left, Lane.Center, Lane.Right };
            Assert.IsFalse(PatternSafety.IsRowSafe(everything, Lane.Center));
            Assert.IsFalse(PatternSafety.IsRowSafe(everything, Lane.Left));
        }

        [Test]
        public void IsRowSafe_Clamps_An_Out_Of_Range_Reachability_Lane()
        {
            // Clamp(Left - 1) == Left, so a "come from further left" never crashes and still resolves.
            Assert.IsTrue(PatternSafety.IsRowSafe(new[] { Lane.Right }, (Lane)(-5)));
            Assert.IsTrue(PatternSafety.IsRowSafe(new[] { Lane.Left }, (Lane)99));
        }

        [Test]
        public void Sanitize_Caps_The_Row_And_Keeps_It_Sorted_And_Distinct()
        {
            Lane[] sanitized = PatternSafety.Sanitize(new[] { Lane.Right, Lane.Right, Lane.Left, Lane.Center });

            Assert.AreEqual(PatternSafety.MaxBlockedPerRow, sanitized.Length);
            CollectionAssert.AreEqual(new[] { Lane.Left, Lane.Right }, sanitized);
        }

        [Test]
        public void Sanitize_Never_Blocks_Every_Lane()
        {
            Lane[] sanitized = PatternSafety.Sanitize(new[] { Lane.Left, Lane.Center, Lane.Right });

            Assert.Less(sanitized.Length, Lanes.Count);
            Assert.GreaterOrEqual(PatternSafety.FreeLanes(sanitized).Length, 1);
        }

        [Test]
        public void Sanitize_Is_Cheap_For_An_Empty_Or_Null_Row()
        {
            Assert.AreEqual(0, PatternSafety.Sanitize(null).Length);
            Assert.AreEqual(0, PatternSafety.Sanitize(new Lane[0]).Length);
        }
    }
}
