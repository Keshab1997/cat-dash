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
            var regions = new (string Name, Rect Rect)[]
            {
                ("Body", PaletteSpec.CatAtlas.Body),
                ("FurFlat", PaletteSpec.CatAtlas.FurFlat),
                ("Cream", PaletteSpec.CatAtlas.Cream),
                ("Leg", PaletteSpec.CatAtlas.Leg),
                ("Tail", PaletteSpec.CatAtlas.Tail),
                ("Head", PaletteSpec.CatAtlas.Head),
                ("Muzzle", PaletteSpec.CatAtlas.Muzzle),
            };

            foreach (var (name, rect) in regions)
            {
                Assert.Greater(rect.width, 0f, $"{name} width");
                Assert.Greater(rect.height, 0f, $"{name} height");
                Assert.GreaterOrEqual(rect.xMin, 0f, $"{name} left edge");
                Assert.GreaterOrEqual(rect.yMin, 0f, $"{name} bottom edge");
                Assert.LessOrEqual(rect.xMax, 1f, $"{name} right edge");
                Assert.LessOrEqual(rect.yMax, 1f, $"{name} top edge");
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
            Assert.AreEqual(0f, PaletteSpec.CatAtlas.BodyBellyU, 1e-5f);
            Assert.AreEqual(0.5f, PaletteSpec.CatAtlas.BodySpineU, 1e-5f);
            Assert.AreEqual(0f, PaletteSpec.CatAtlas.BodyTailV, 1e-5f);
            Assert.AreEqual(0.5f, PaletteSpec.CatAtlas.BodyChestV, 1e-5f);
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
                Assert.AreNotEqual(Color.magenta, parsed,
                    $"{field.Name} ('{hex}') is not a valid #RRGGBB colour");
                Assert.IsTrue(parsed.maxColorComponent <= 1f && parsed.minColorComponent >= 0f,
                    $"{field.Name} parsed outside the 0..1 range");
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
            Assert.AreEqual(0f, RunCycleSpec.BodyBobMetresAt(0f), 1e-4f);
            Assert.AreEqual(RunCycleSpec.BodyBobMetres, RunCycleSpec.BodyBobMetresAt(0.25f), 1e-4f,
                "two contacts per cycle means a peak at a quarter and three quarters");
            Assert.AreEqual(-RunCycleSpec.BodyBobMetres, RunCycleSpec.BodyBobMetresAt(0.75f), 1e-4f);
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
                Assert.LessOrEqual(triangles, budget,
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
                Assert.LessOrEqual(size, 1024, $"{path} exceeds the 1024 cap");
            }
        }

        [Test]
        public void Cat_KeepsItsPartHierarchyForTheFutureRig()
        {
            var cat = AssetDatabase.LoadAssetAtPath<GameObject>($"{GeneratedFolder}/Cat.fbx");
            Assert.IsNotNull(cat, "Cat.fbx did not import");

            // RunCycleSpec's skinning rule is "one island = one bone", so the islands must
            // survive the import as separate objects with their joint pivots.
            var names = cat.GetComponentsInChildren<Transform>(true).Select(t => t.name).ToArray();
            foreach (var expected in new[]
                     {
                         "CatDash_Cat", "Body", "Neck", "Head", "Muzzle", "EarL", "EarR",
                         "LegFrontL", "LegFrontR", "LegHindL", "LegHindR", "Tail",
                     })
            {
                CollectionAssert.Contains(names, expected,
                    $"Cat.fbx lost the '{expected}' object; RunCycleSpec assumes it exists");
            }
        }
    }
}
