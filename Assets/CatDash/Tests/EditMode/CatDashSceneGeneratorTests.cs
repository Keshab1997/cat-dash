using CatDash.EditorTools;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;

namespace CatDash.Tests.EditMode
{
    /// <summary>
    /// Authored, NOT RUN: CD-B1 deliberately commits no .unity scene (docs/batches/CD-B1.md, risk 3), so the
    /// generated scene cannot be asserted here yet. The test is [Explicit] and self-ignores while the scene is
    /// absent, so CI stays green and the label "NOT RUN" is never silently read as a pass.
    /// </summary>
    public class CatDashSceneGeneratorTests
    {
        [Test]
        [Explicit("Owner-run only: pass after 'CatDash/Generate CatDash scene' has produced the scene.")]
        [Category("SceneGenerator")]
        public void GeneratedScene_Loads_As_A_SceneAsset()
        {
            var scene = AssetDatabase.LoadAssetAtPath<SceneAsset>(CatDashSceneGenerator.ScenePath);

            if (scene == null)
            {
                Assert.Ignore("No scene at " + CatDashSceneGenerator.ScenePath +
                              " yet — generator not run/committed. Authored but NOT RUN (never a pass).");
            }

            Assert.IsNotNull(scene, "Generated CatDash scene failed to load as a SceneAsset.");
            Assert.AreEqual(CatDashSceneGenerator.SceneFolder, System.IO.Path.GetDirectoryName(CatDashSceneGenerator.ScenePath).Replace('\\', '/'),
                            "Scene path must stay inside the CatDash scenes folder.");
        }
    }
}
