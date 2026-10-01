using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.Rendering;
using System.IO;

/// <summary>
/// Build del visor para Android (Semana 5 - prep movil).
/// Ejemplo (modo batch desde una terminal):
///   Unity.exe -batchmode -quit -projectPath "<ruta>\Unity" \
///       -executeMethod BuildMobile.BuildAndroid -logFile build_android.log
///
/// Requisitos previos:
///   * Modulo "Android Build Support" (con SDK/NDK/OpenJDK) instalado en Unity Hub.
///   * ProjectSettings: minSdkVersion 26, arquitecturas ARMv7+ARM64 (o solo ARM64).
/// El APK queda en  Builds/BuildLabAndroid.apk
/// </summary>
public static class BuildMobile
{
    public static void BuildRealScale()
    {
        ARWeek6Setup.CreateARScene();
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel29;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
        Build(Path.Combine(Application.dataPath, "..", "Builds", "P1_Grupo6_AR_RealScale_v1.apk"), new[] { "Assets/Scenes/ARViga185.unity" });
    }
    public static void BuildAndroid()
    {
        const string scene = "Assets/Scenes/SampleScene.unity";
        string apk = Path.Combine(Application.dataPath, "..", "Builds", "BuildLabAndroid.apk");
        Build(apk, new[] { scene });
    }

    public static void BuildAndroidAR()
    {
        const string scene = "Assets/Scenes/ARViga185.unity";
        string apk = Path.Combine(Application.dataPath, "..", "Builds", "BuildLabAndroid_AR.apk");
        if (!File.Exists(Path.Combine(Application.dataPath, "Scenes", "ARViga185.unity")))
        {
            Debug.LogError("No existe Assets/Scenes/ARViga185.unity. Ejecuta Lab/AR Semana 6/Crear escena AR Viga 185.");
            EditorApplication.Exit(1);
            return;
        }

        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel29;
        PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
        PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
#if USE_AR_FOUNDATION
        ARWeek6Setup.EnsureARBackgroundRendererFeature();
#endif
        Build(apk, new[] { scene });
    }

    static void Build(string apk, string[] scenes)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(apk));

        if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.Android)
        {
            EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);
        }

        BuildPlayerOptions opts = new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = apk,
            target = BuildTarget.Android,
            options = BuildOptions.None
        };

        BuildReport report = BuildPipeline.BuildPlayer(opts);
        BuildSummary sum = report.summary;
        Debug.Log($"BuildAndroid resultado={sum.result} tamano={sum.totalSize} bytes " +
                  $"tiempo={sum.totalTime}");
        EditorApplication.Exit(sum.result == BuildResult.Succeeded ? 0 : 1);
    }
}
