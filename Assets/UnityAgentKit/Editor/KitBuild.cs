using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace UnityAgentKit.Editor
{
    // Only explicitly invoked. Never rewrites scenes during import/test execution.
    public static class KitBuild
    {
        [Serializable] private class Config
        {
            public string packageName;
            public string productName;
            public string versionName;
        }
        private static string Arg(string key)
        {
            var args = Environment.GetCommandLineArgs();
            var index = Array.IndexOf(args, "-" + key);
            return index >= 0 && index + 1 < args.Length ? args[index + 1] : "";
        }
        [MenuItem("Unity Agent Kit/Create prototype scene (only if no build scenes)")]
        public static void CreatePrototype()
        {
            if (EditorBuildSettings.scenes.Any(s => s.enabled)) return;
            const string path = "Assets/UnityAgentKit/Scenes/Prototype.unity";
            if (File.Exists(path)) throw new BuildFailedException("Prototype already exists. Configure build scenes; refusing to overwrite.");
            Directory.CreateDirectory("Assets/UnityAgentKit/Scenes");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.name = "Ground";
            var ball = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            ball.name = "PhysicsDemo";
            ball.transform.position = Vector3.up * 3;
            ball.AddComponent<Rigidbody>();
            var camera = new GameObject("Main Camera");
            camera.tag = "MainCamera";
            camera.AddComponent<Camera>();
            camera.AddComponent<AudioListener>();
            camera.transform.position = new Vector3(0, 5, -8);
            camera.transform.LookAt(Vector3.up);
            var light = new GameObject("Sun").AddComponent<Light>();
            light.type = LightType.Directional;
            light.transform.rotation = Quaternion.Euler(50, -30, 0);
            EditorSceneManager.SaveScene(scene, path);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(path, true) };
            AssetDatabase.Refresh();
        }
        public static void BuildAndroid()
        {
            var config = JsonUtility.FromJson<Config>(File.ReadAllText("unity-kit.json"));
            if (config == null || string.IsNullOrWhiteSpace(config.packageName) || config.packageName.StartsWith("com.example."))
                throw new BuildFailedException("Configure a real packageName in unity-kit.json first.");
            EditorSettings.serializationMode = SerializationMode.ForceText;
            PlayerSettings.SetApplicationIdentifier(NamedBuildTarget.Android, config.packageName);
            PlayerSettings.productName = config.productName;
            PlayerSettings.bundleVersion = config.versionName;
            if (!int.TryParse(Arg("androidVersionCode"), out var code) || code <= 0 || code > 2100000000)
                throw new BuildFailedException("Explicit valid androidVersionCode is required.");
            PlayerSettings.Android.bundleVersionCode = code;
            PlayerSettings.SetScriptingBackend(NamedBuildTarget.Android, ScriptingImplementation.IL2CPP);
            PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64;
            PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel26;
            EditorUserBuildSettings.buildAppBundle = true;
            PlayerSettings.Android.useCustomKeystore = true;
            PlayerSettings.Android.keystoreName = Arg("androidKeystoreName");
            PlayerSettings.Android.keystorePass = Arg("androidKeystorePass");
            PlayerSettings.Android.keyaliasName = Arg("androidKeyaliasName");
            PlayerSettings.Android.keyaliasPass = Arg("androidKeyaliasPass");
            if (string.IsNullOrWhiteSpace(PlayerSettings.Android.keystoreName) ||
                string.IsNullOrWhiteSpace(PlayerSettings.Android.keystorePass) ||
                string.IsNullOrWhiteSpace(PlayerSettings.Android.keyaliasName) ||
                string.IsNullOrWhiteSpace(PlayerSettings.Android.keyaliasPass))
                throw new BuildFailedException("Missing upload signing configuration.");
            var sdk = Arg("androidTargetSdkVersion");
            if (!int.TryParse(sdk, out var api) || api < 35 || !Enum.IsDefined(typeof(AndroidSdkVersions), api))
                throw new BuildFailedException("Set a supported Android API >=35. Check current Play policy and installed SDK.");
            PlayerSettings.Android.targetSdkVersion = (AndroidSdkVersions)api;
            // Only the starter can opt into this via a checked-in marker file.
            if (!EditorBuildSettings.scenes.Any(s => s.enabled))
            {
                if (!File.Exists("ProjectSettings/UnityAgentKitPrototype"))
                    throw new BuildFailedException("No enabled scenes. Configure build scenes in Unity.");
                CreatePrototype();
            }
            const string output = "build/Android/Game.aab";
            Directory.CreateDirectory("build/Android");
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray(),
                locationPathName = output, target = BuildTarget.Android, options = BuildOptions.None
            });
            if (report.summary.result != BuildResult.Succeeded)
                throw new BuildFailedException("Android build failed: " + report.summary.result);
            Debug.Log("Unity Agent Kit: signed ARM64 AAB produced. Phone QA still required.");
        }
    }
}
