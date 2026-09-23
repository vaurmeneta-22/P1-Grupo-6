using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;
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
    public static void BuildAndroid()
    {
        const string scene = "Assets/Scenes/SampleScene.unity";
        string apk = Path.Combine(Application.dataPath, "..", "Builds", "BuildLabAndroid.apk");
        Directory.CreateDirectory(Path.GetDirectoryName(apk));

        BuildPlayerOptions opts = new BuildPlayerOptions
        {
            scenes = new[] { scene },
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