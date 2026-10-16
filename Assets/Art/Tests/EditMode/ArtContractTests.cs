using System.Collections.Generic;
using System.Linq;
using CatDash.Art;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace CatDash.Art.Tests
{
    /// <summary>
    /// EditMode tests for the generated art assets and the two contract types Agent B owns
    /// (<see cref="PaletteSpec"/>, <see cref="RunCycleSpec"/>). Owner: Agent B (batch CD-B1).
    ///
    /// These tests are the Unity-side half of the art check. They assert what the sandbox
    /// could not: that Unity actually imports the FBXs, that the tri budgets hold after
    /// import, that every model ends up with one material carrying its texture, and that the
    /// atlas regions are disjoint. They do not judge the look — that is the owner's capture
    /// (docs/GAME_BRIEF.md, "Visual acceptance gate").
    /// </summary>
    public class ArtContractTests
    {
        private const string GeneratedFolder = "Assets/Art/Generated";
        private const string TextureFolder = "Assets/Art/Generated/Textures";

        // ---- atlas / palette contracts ------------------------------------------

        [Test]
        public void CatAtlas_RegionsAreInsideTheTextureAndDisjoint()
        {
            // (PaletteSpec builds these with named Rect arguments; the names are asserted
            //  here only for readability — the values come from the single source.)
            var regions = new (string Name, Rect Rect)[]
            {
                ("Body", PaletteSpec.CatAtlas.Body),
                ("Head", PaletteSpec.CatAtlas.Head),
                ("Leg", PaletteSpec.CatAtlas.Leg),
                ("Tail", PaletteSpec.CatAtlas.Tail),
                ("Ear", PaletteSpec.CatAtlas.Ear),
                ("Eye", PaletteSpec.CatAtlas.Eye),
                ("Muzzle", PaletteSpec.CatAtlas.Muzzle),
                ("FurSpare", PaletteSpec.CatAtlas.FurSpare),
            };

            foreach (var (name, rect) in regions)
            {
                // IsTrue with explicit operators, so the test does not depend on which
                // float overloads this NUnit version happens to expose.
                Assert.IsTrue(rect.width > 0f, $"{name} width must be positive");
                Assert.IsTrue(rect.height > 0f, $"{name} height must be positive");
                Assert.IsTrue(rect.xMin >= 0f, $"{name} left edge outside the texture");
                Assert.IsTrue(rect.yMin >= 0f, $"{name} bottom edge outside the texture");
                Assert.IsTrue(rect.xMax <= 1f, $"{name} right edge outside the texture");
                Assert.IsTrue(rect.yMax <= 1f, $"{name} top edge outside the texture");
            }

            for (int i = 0; i < regions.Length; i++)
            {
                for (int j = i + 1; j < regions.Length; j++)
                {
                    // Regions may share an edge; overlapping area is the bug (a pale fill once
                    // flooded the crate cap region, which washed the whole prop out).
                    bool disjoint = regions[i].Rect.xMax <= regions[j].Rect.xMin
                                    || regions[j].Rect.xMax <= regions[i].Rect.xMin
                                    || regions[i].Rect.yMax <= regions[j].Rect.yMin
                                    || regions[j].Rect.yMax <= regions[i].Rect.yMin;
                    Assert.IsTrue(disjoint,
                        $"{regions[i].Name} and {regions[j].Name} overlap in the cat atlas");
                }
            }
        }

        [Test]
        public void BodyRingMapping_BellyAndSpineMatchThePainter()
        {
            // Region-relative fractions (u = 0 belly wraps to u = 1; u = 0.5 is the spine,
            // which is where the "mouse" blaze is painted).
            Assert.AreEqual(0f, PaletteSpec.CatAtlas.BodyBellyAtU, 1e-5f);
            Assert.AreEqual(0.5f, PaletteSpec.CatAtlas.BodySpineAtU, 1e-5f);
            Assert.AreEqual(0f, PaletteSpec.CatAtlas.BodyTailAtV, 1e-5f);
            Assert.AreEqual(1f, PaletteSpec.CatAtlas.BodyChestAtV, 1e-5f);
        }

        [Test]
        public void RunCycleSpec_PoseOrderMatchesTheReferenceSheet()
        {
            // docs/art/refs/cat-v2-run-cycle-sheet.png reads left to right:
            // contact, down, up, air. Reviewer comparisons depend on this order.
            CollectionAssert.AreEqual(
                new[] { RunCycleSpec.RunPose.Contact, RunCycleSpec.RunPose.Down,
                        RunCycleSpec.RunPose.Up, RunCycleSpec.RunPose.Air },
                RunCycleSpec.PoseOrder);
            Assert.AreEqual(4, RunCycleSpec.PoseCount);
            Assert.AreEqual(0, RunCycleSpec.FrameOf(RunCycleSpec.RunPose.Contact));
            Assert.AreEqual(3, RunCycleSpec.FrameOf(RunCycleSpec.RunPose.Down));
            Assert.AreEqual(6, RunCycleSpec.FrameOf(RunCycleSpec.RunPose.Up));
            Assert.AreEqual(9, RunCycleSpec.FrameOf(RunCycleSpec.RunPose.Air));

            float previous = -1f;
            foreach (var pose in RunCycleSpec.PoseOrder)
            {
                float phase = RunCycleSpec.PhaseOf(pose);
                Assert.IsTrue(phase > previous, "pose phases must increase in sheet order");
                previous = phase;
            }
        }

        [Test]
        public void PaletteHexValues_AllParseToRealColours()
        {
            var fields = typeof(PaletteSpec)
                .GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static)
                .Where(f => f.FieldType == typeof(string) && f.Name.EndsWith("Hex"));

            Assert.IsNotEmpty(fields, "PaletteSpec should expose its hex values");
            foreach (var field in fields)
            {
                var hex = (string)field.GetValue(null);
                var parsed = PaletteSpec.FromSrgb(hex);
                // Compare channels directly: UnityEngine.Color exposes maxColorComponent but
                // NOT minColorComponent (the assertion here used to be error CS1061), and
                // Assert.AreNotEqual(Color, Color) is an ambiguous NUnit overload.
                bool parsedToRealColour = !(parsed.r == Color.magenta.r
                                            && parsed.g == Color.magenta.g
                                            && parsed.b == Color.magenta.b);
                Assert.IsTrue(parsedToRealColour,
                    $"PaletteSpec.{field.Name} ('{hex}') did not parse into a real colour");
                // Same purpose as before: every channel must stay inside 0..1.
                Assert.IsTrue(parsed.r >= 0f && parsed.r <= 1f
                              && parsed.g >= 0f && parsed.g <= 1f
                              && parsed.b >= 0f && parsed.b <= 1f
                              && parsed.a >= 0f && parsed.a <= 1f,
                    $"PaletteSpec.{field.Name} ('{hex}') parsed outside the 0..1 range");
            }
        }

        // ---- run cycle contract --------------------------------------------------

        [Test]
        public void RunCycleSpec_FreezesTheSixBoneContract()
        {
            Assert.AreEqual("Run", RunCycleSpec.ClipName, "clip name is part of the contract");
            Assert.AreEqual(6, RunCycleSpec.BoneNames.Length, "bone count");
            Assert.AreEqual(RunCycleSpec.BoneCount, RunCycleSpec.BoneNames.Length);
            CollectionAssert.AllItemsAreUnique(RunCycleSpec.BoneNames);
            Assert.IsFalse(RunCycleSpec.RootMotion, "root motion stays off; PlayerMover owns speed");
            Assert.IsFalse(RunCycleSpec.HasEmbeddedAnimation,
                "Cat.fbx ships no clip this batch (skinning is explicitly out of scope)");
            Assert.AreEqual("+Z", RunCycleSpec.ForwardAxis);
        }

        [Test]
        public void RunCycleSpec_LegSwingIsSymmetricAndPhaseShifted()
        {
            Assert.AreEqual(0f, RunCycleSpec.LegPitchDegrees(0f, 0f), 1e-4f);
            Assert.AreEqual(RunCycleSpec.LegSwingDegrees, RunCycleSpec.LegPitchDegrees(0.25f, 0f), 1e-3f);
            Assert.AreEqual(-RunCycleSpec.LegSwingDegrees, RunCycleSpec.LegPitchDegrees(0.75f, 0f), 1e-3f);
            Assert.AreEqual(0f, RunCycleSpec.LegPitchDegrees(0f, RunCycleSpec.HindPhaseOffset), 1e-4f,
                "hind legs are half a cycle behind, so phase 0 of the hind pair is also the zero crossing");
            Assert.AreEqual(RunCycleSpec.LegPitchDegrees(0.3f, 0f),
                RunCycleSpec.LegPitchDegrees(0.3f + 1f, 0f), 1e-4f, "cycle wraps");
        }

        [Test]
        public void RunCycleSpec_BodyBobPeaksTwicePerCycle()
        {
            // Convention frozen in RunCycleSpec.BodyBobMetresAt: 0 = the contact height, so
            // the run DIPS at both contacts and rises at mid-stance (0.25) and at the
            // airborne apex (0.75). Asserted with exact comparisons on purpose: the previous
            // Sin-based curve peaked on the contacts and returned 1.8e-18 (Sin(pi)) at the
            // quarters, which is what failed CI. A raised cosine plus the documented epsilon
            // snap puts the contacts on the baseline exactly.
            Assert.IsTrue(RunCycleSpec.BodyBobMetresAt(0.25f) == RunCycleSpec.BodyBobMetres,
                "mid-stance (0.25) must sit exactly at the peak offset");
            Assert.IsTrue(RunCycleSpec.BodyBobMetresAt(0.75f) == RunCycleSpec.BodyBobMetres,
                "airborne apex (0.75) must sit exactly at the peak offset");
            Assert.IsTrue(RunCycleSpec.BodyBobMetresAt(0f) == 0f,
                "the first contact must sit exactly on the baseline, not at a 1e-18 residue");
            Assert.IsTrue(RunCycleSpec.BodyBobMetresAt(0.5f) == 0f,
                "the second contact must sit exactly on the baseline");

            // No residue anywhere else either, and the curve stays inside its documented range.
            for (int i = 0; i <= 100; i++)
            {
                float cycles = i / 100f;
                float bob = RunCycleSpec.BodyBobMetresAt(cycles);
                Assert.IsTrue(bob >= 0f && bob <= RunCycleSpec.BodyBobMetres,
                    $"body bob left its documented range at cycles={cycles}: {bob}");
                Assert.IsTrue(bob == 0f || bob > 1e-9f,
                    $"numerical residue at cycles={cycles}: {bob} (floating-point noise is not a bob)");
            }
        }

        // ---- generated assets, as imported by Unity ------------------------------

        private static readonly (string Path, int Budget)[] BudgetedAssets =
        {
            ($"{GeneratedFolder}/Cat.fbx", 4000),
            ($"{GeneratedFolder}/Prop_Crate.fbx", 800),
            ($"{GeneratedFolder}/Prop_Barrier.fbx", 800),
            ($"{GeneratedFolder}/Prop_Pot.fbx", 800),
            ($"{GeneratedFolder}/Road_Segment.fbx", 3000),
        };

        [Test]
        public void GeneratedModels_ImportWithinTriangleBudget()
        {
            foreach (var (path, budget) in BudgetedAssets)
            {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Assert.IsNotNull(model, $"{path} did not import as a model");
                var meshes = model.GetComponentsInChildren<MeshFilter>()
                    .Select(filter => filter.sharedMesh)
                    .Where(mesh => mesh != null)
                    .ToArray();
                Assert.IsNotEmpty(meshes, $"{path} imported with no meshes");
                int triangles = meshes.Sum(mesh => mesh.triangles.Length / 3);
                // A mesh imported without Read/Write enabled returns an EMPTY triangles
                // array rather than throwing, which would let this budget check pass at
                // zero triangles. Assert the count is real before comparing it.
                Assert.IsTrue(triangles > 0,
                    $"{path} reported 0 triangles — the import is unreadable or broken, "
                    + "so this budget check cannot be trusted (see the .fbx.meta isReadable)");
                Assert.IsTrue(triangles <= budget,
                    $"{path} has {triangles} triangles, over the {budget} budget");
            }
        }

        [Test]
        public void GeneratedModels_UseOneMaterialEachAndCarryATexture()
        {
            foreach (var (path, _) in BudgetedAssets)
            {
                var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                Assert.IsNotNull(model, $"{path} did not import as a model");

                var renderers = model.GetComponentsInChildren<MeshRenderer>()
                    .Where(renderer => renderer.sharedMaterials != null
                                       && renderer.sharedMaterials.Length > 0)
                    .ToArray();
                Assert.IsNotEmpty(renderers, $"{path} imported with no renderer");

                var materials = new HashSet<Material>();
                foreach (var renderer in renderers)
                {
                    foreach (var material in renderer.sharedMaterials)
                    {
                        if (material != null)
                        {
                            materials.Add(material);
                        }
                    }
                }
                Assert.AreEqual(1, materials.Count,
                    $"{path} should use exactly one material, found {materials.Count}");
                var single = materials.First();
                Assert.IsNotNull(single.mainTexture,
                    $"{path}: material '{single.name}' lost its texture on import "
                    + "(check the FBX texture path resolves inside Assets/)");
            }
        }

        [Test]
        public void GeneratedTextures_ExistWithTheRightSizeAndNoHdr()
        {
            var expected = new (string Path, int Size)[]
            {
                ($"{TextureFolder}/Cat_1024.png", 1024),
                ($"{TextureFolder}/Road_Segment_1024.png", 1024),
                ($"{TextureFolder}/Prop_Crate_512.png", 512),
                ($"{TextureFolder}/Prop_Barrier_512.png", 512),
                ($"{TextureFolder}/Prop_Pot_512.png", 512),
            };

            foreach (var (path, size) in expected)
            {
                var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
                Assert.IsNotNull(texture, $"{path} missing");
                Assert.AreEqual(size, texture.width, $"{path} width");
                Assert.AreEqual(size, texture.height, $"{path} height");
                Assert.IsTrue(size <= 1024, $"{path} exceeds the 1024 cap");
            }
        }

        [Test]
        public void Cat_KeepsItsPartHierarchyForTheFutureRig()
        {
            var cat = AssetDatabase.LoadAssetAtPath<GameObject>($"{GeneratedFolder}/Cat.fbx");
            Assert.IsNotNull(cat, "Cat.fbx did not import");

            // Unity names the imported root GameObject after the FILE ("Cat"), not after the
            // empty root node the generator exports ("CatDash_Cat" — that node does not become
            // an object of its own). The islands are therefore the root's DESCENDANTS, and the
            // importer behaviour is asserted deliberately here (see
            // RunCycleSpec.ImportedRootName) instead of being worked around in the test.
            Assert.AreEqual(RunCycleSpec.ImportedRootName, cat.transform.name,
                "the imported root name changed; scene/rig code looks the model up by it");

            var descendants = cat.GetComponentsInChildren<Transform>(true)
                .Where(transform => transform != cat.transform)
                .Select(transform => transform.name)
                .ToArray();

            // RunCycleSpec's skinning rule is "one island = one bone", so every island must
            // survive the import as its own object with its joint pivot.
            var expected = new[]
            {
                "Body", "Neck", "Head", "EyeL", "EyeR", "Muzzle",
                "EarL", "EarR", "LegFrontL", "LegFrontR", "LegHindL", "LegHindR", "Tail",
            };
            CollectionAssert.AreEquivalent(expected, descendants,
                "the cat's island set changed; RunCycleSpec's bone mapping assumes exactly these "
                + "thirteen objects below the root");
            foreach (var name in expected)
            {
                CollectionAssert.Contains(descendants, name,
                    $"Cat.fbx lost the '{name}' object; RunCycleSpec assumes it exists");
            }
        }
    }
}
