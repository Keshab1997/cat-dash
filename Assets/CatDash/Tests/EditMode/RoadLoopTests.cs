using CatDash.Presentation;
using NUnit.Framework;
using UnityEngine;

namespace CatDash.Tests.EditMode
{
    /// <summary>
    /// Focused road-recycling tests: constant segment count, one-length window behind the player and
    /// idempotent recycling. Authored by Agent C; execution happens in CI/owner runs.
    /// </summary>
    public class RoadLoopTests
    {
        private const float Length = 10f;
        private const int Count = 4;

        private GameObject root;
        private GameObject segmentsRoot;
        private GameObject player;
        private RoadLoop loop;

        [SetUp]
        public void SetUp()
        {
            root = new GameObject("Test RoadRoot");
            loop = root.AddComponent<RoadLoop>();

            segmentsRoot = new GameObject("Test Segments");
            segmentsRoot.transform.SetParent(root.transform, false);
            for (int i = 0; i < Count; i++)
            {
                var segment = new GameObject("Segment " + i);
                segment.transform.SetParent(segmentsRoot.transform, false);
                segment.transform.position = new Vector3(0f, 0f, i * Length);
            }

            player = new GameObject("Test Player");
            loop.Bind(segmentsRoot.transform, player.transform, Length, Count);
        }

        [TearDown]
        public void TearDown()
        {
            if (root != null) Object.DestroyImmediate(root);
            if (player != null) Object.DestroyImmediate(player);
        }

        [Test]
        public void Bind_Adopts_Segments_Without_Inventing_New_Geometry()
        {
            Assert.AreEqual(Count, loop.ActiveSegmentCount);

            loop.Bind(segmentsRoot.transform, player.transform, Length, 2);
            Assert.AreEqual(2, loop.ActiveSegmentCount);

            loop.Bind(segmentsRoot.transform, player.transform, Length, 99);
            Assert.AreEqual(Count, loop.ActiveSegmentCount, "RoadLoop must never invent geometry it was not given.");
        }

        [Test]
        public void ResetToStart_Lays_Segments_From_One_Length_Behind_The_Player()
        {
            loop.ResetToStart(100f);

            Assert.AreEqual(Count, loop.ActiveSegmentCount);
            CollectionAssert.AreEqual(new[] { 90f, 100f, 110f, 120f }, SegmentZ(), "Segment layout after ResetToStart.");
        }

        [Test]
        public void RecycleAhead_Moves_Only_Segments_Left_Behind()
        {
            loop.ResetToStart(100f);

            loop.RecycleAhead(130f);

            Assert.AreEqual(Count, loop.ActiveSegmentCount, "Recycling must not change the segment count.");
            CollectionAssert.AreEqual(new[] { 120f, 130f, 140f, 150f }, SegmentZ(), "Window after recycling at 130 m.");
            Assert.LessOrEqual(SegmentZ()[0], 130f, "The player must stand on a segment.");
            Assert.GreaterOrEqual(SegmentZ()[Count - 1], 130f, "The road must reach ahead of the player.");
        }

        [Test]
        public void RecycleAhead_Is_Idempotent()
        {
            loop.ResetToStart(0f);
            loop.RecycleAhead(57f);
            float[] first = SegmentZ();

            loop.RecycleAhead(57f);

            CollectionAssert.AreEqual(first, SegmentZ(), "Re-recycling the same player position moved segments.");
        }

        [Test]
        public void Long_Run_Keeps_The_Count_And_The_Window()
        {
            loop.ResetToStart(0f);

            for (float playerZ = 0f; playerZ <= 1000f; playerZ += 7.5f)
            {
                loop.RecycleAhead(playerZ);

                Assert.AreEqual(Count, loop.ActiveSegmentCount, "Segment count changed at " + playerZ + " m.");

                float[] z = SegmentZ();
                float windowStart = playerZ - Length;
                float windowEnd = windowStart + Length * Count;
                for (int i = 0; i < z.Length; i++)
                {
                    Assert.GreaterOrEqual(z[i], windowStart - 0.01f, "Segment " + i + " fell behind the window.");
                    Assert.LessOrEqual(z[i], windowEnd + 0.01f, "Segment " + i + " left the window.");
                }
            }
        }

        [Test]
        public void Without_A_Segment_Root_Nothing_Is_Created()
        {
            loop.Bind(null, player.transform, Length, Count);

            Assert.AreEqual(0, loop.ActiveSegmentCount);

            loop.ResetToStart(50f);
            loop.RecycleAhead(120f);

            Assert.AreEqual(0, loop.ActiveSegmentCount);
        }

        [Test]
        public void Zero_Length_Configuration_Is_Survivable()
        {
            loop.Bind(segmentsRoot.transform, player.transform, 0f, Count);

            Assert.AreEqual(Count, loop.ActiveSegmentCount);
            Assert.DoesNotThrow(() => loop.RecycleAhead(250f));
        }

        private float[] SegmentZ()
        {
            var positions = new float[segmentsRoot.transform.childCount];
            for (int i = 0; i < positions.Length; i++)
            {
                positions[i] = segmentsRoot.transform.GetChild(i).position.z;
            }
            System.Array.Sort(positions);
            return positions;
        }
    }
}
