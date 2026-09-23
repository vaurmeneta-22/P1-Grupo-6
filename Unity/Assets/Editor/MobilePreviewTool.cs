using System;
using System.IO;
using UnityEditor;
using UnityEngine;

/// <summary>
/// Herramienta de "preview movil" para el lab estructural (Semana 5, prep movil).
/// Sin celular fisico: abre el Device Simulator de Unity (presets de telefono
/// provistos por el paquete com.unity.device-simulator.devices) y permite
/// capturar screenshots del Game view en resolucion de telefono.
///
/// Uso manual (interactivo):
///   1) Unity Hub -> proyecto Unity/ -> abrir Assets/Scenes/SampleScene.unity
///   2) Menu Lab/Preview Movil/Abrir Device Simulator y elegir un dispositivo.
///   3) Play y luego Lab/Preview Movil/Capturar screenshot.
/// Las capturas quedan en Unity/Builds/MobilePreview/*.png
/// </summary>
public static class MobilePreviewTool
{
    public const string MenuRoot = "Lab/Preview Movil/";

    [MenuItem(MenuRoot + "Abrir Device Simulator", priority = 1)]
    public static void OpenDeviceSimulator()
    {
        // El paquete com.unity.device-simulator.devices agrega los presets al Device Simulator.
        EditorApplication.ExecuteMenuItem("Window/Device Simulator");
    }

    [MenuItem(MenuRoot + "Capturar screenshot", priority = 2)]
    public static void Capture()
    {
        string path = CapturePath();
        ScreenCapture.CaptureScreenshot(path);
        Debug.Log($"[MobilePreview] Captura guardada: {path}");
    }

    [MenuItem(MenuRoot + "Abrir carpeta de capturas", priority = 3)]
    public static void OpenCapturesFolder()
    {
        CapturePath();
        EditorUtility.RevealInFinder(CapturePath());
    }

    static string CapturePath()
    {
        string dir = Path.Combine(Application.dataPath, "..", "Builds", "MobilePreview");
        Directory.CreateDirectory(dir);
        return Path.Combine(dir, "preview_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + ".png");
    }
}