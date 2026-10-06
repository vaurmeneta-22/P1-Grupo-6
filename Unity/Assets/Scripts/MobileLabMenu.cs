using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.XR;
using UnityEngine.XR.Management;
using Google.XR.Cardboard;

// Both loaders are registered in the Android build; only one runs at a time.
public class MobileLabMenu : MonoBehaviour
{
    public const string MenuScene = "MobileLabMenu";
    public const string VRScene = "VRFloor3";
    public const string ARScene = "ARBeamPlacement";
    public static MobileLabMenu Instance { get; private set; }
    public UnityEngine.XR.Management.XRLoader arLoader;
    public UnityEngine.XR.Management.XRLoader cardboardLoader;
    public bool Busy { get; private set; }
    public bool IsVR { get; private set; }
    public bool NativeVR { get; private set; }
    public string Error { get; private set; }
    string status = "Elige una experiencia.";

    void Awake()
    {
        if (Instance != null && Instance != this) { Destroy(gameObject); return; }
        Instance = this;
        DontDestroyOnLoad(gameObject);
        Screen.sleepTimeout = SleepTimeout.NeverSleep;
        Application.targetFrameRate = 60;
    }

    public void OpenVR() { if (!Busy) StartCoroutine(SwitchTo(VRScene)); }
    public void OpenAR() { if (!Busy) StartCoroutine(SwitchTo(ARScene)); }
    public void ReturnToMenu() { if (!Busy) StartCoroutine(SwitchTo(MenuScene)); }

    IEnumerator SwitchTo(string scene)
    {
        Busy = true; Error = null; status = "Preparando " + (scene == VRScene ? "Cardboard VR…" : "la experiencia…");
        // Unload trackable managers before stopping their native provider.
        if (SceneManager.GetActiveScene().name != MenuScene)
            yield return SceneManager.LoadSceneAsync(MenuScene);
        var manager = XRGeneralSettings.Instance != null ? XRGeneralSettings.Instance.Manager : null;
        if (manager != null && manager.isInitializationComplete) manager.DeinitializeLoader();
        NativeVR = false; IsVR = scene == VRScene;
        Screen.orientation = IsVR ? ScreenOrientation.LandscapeLeft : ScreenOrientation.Portrait;
        yield return null;
        yield return null;
        if (scene == MenuScene) { Busy = false; status = "Elige una experiencia."; yield break; }
#if UNITY_ANDROID && !UNITY_EDITOR
        var wanted = IsVR ? cardboardLoader : arLoader;
        if (manager == null || wanted == null || !manager.TrySetLoaders(new List<UnityEngine.XR.Management.XRLoader> { wanted }))
        { Fail("No se pudo seleccionar el proveedor XR. Vuelve a intentar desde Inicio."); yield break; }
        yield return manager.InitializeLoader();
        if (manager.activeLoader != wanted)
        { Fail("El proveedor " + wanted.name + " no pudo iniciar en este dispositivo."); yield break; }
        manager.StartSubsystems();
        yield return null;
        if (IsVR)
        {
            var display = wanted.GetLoadedSubsystem<XRDisplaySubsystem>();
            var input = wanted.GetLoadedSubsystem<XRInputSubsystem>();
            if (display == null || !display.running || input == null || !input.running)
            { Fail("Cardboard no inició imagen estéreo y seguimiento. Revisa el dispositivo y reinicia la app."); yield break; }
            NativeVR = true;
            if (!Api.HasDeviceParams()) Api.ScanDeviceParams();
        }
#endif
        yield return SceneManager.LoadSceneAsync(scene);
        Busy = false;
        Debug.Log("MOBILE MODE READY: " + scene + "; nativeVR=" + NativeVR);
    }

    void Fail(string text)
    {
        Error = text; Busy = false; IsVR = false; NativeVR = false;
        var manager = XRGeneralSettings.Instance != null ? XRGeneralSettings.Instance.Manager : null;
        if (manager != null && manager.isInitializationComplete) manager.DeinitializeLoader();
        Screen.orientation = ScreenOrientation.Portrait;
        Debug.LogError(text);
    }

    void Update()
    {
        if (!NativeVR || Busy) return;
        if (Api.IsCloseButtonPressed) { ReturnToMenu(); return; }
        if (Api.IsGearButtonPressed) Api.ScanDeviceParams();
        if (Api.HasNewDeviceParams()) Api.ReloadDeviceParams();
        Api.UpdateScreenParams();
    }

    public void Recenter()
    {
        if (NativeVR) Api.Recenter();
    }

    void OnGUI()
    {
        string scene = SceneManager.GetActiveScene().name;
        if (scene == VRScene) return; // VR UI is world-space, rendered to both eyes.
        var safe = Screen.safeArea;
        float scale = safe.width / 420f;
        var previous = GUI.matrix;
        GUI.matrix = Matrix4x4.TRS(new Vector3(safe.x, Screen.height-safe.yMax, 0), Quaternion.identity, Vector3.one*scale);
        float h = safe.height/scale;
        var label = new GUIStyle(GUI.skin.label) { fontSize = 19, wordWrap = true };
        var title = new GUIStyle(label) { fontSize = 27, fontStyle = FontStyle.Bold };
        var button = new GUIStyle(GUI.skin.button) { fontSize = 19, wordWrap = true };
        GUI.enabled = !Busy;
        if (scene == MenuScene)
        {
            GUILayout.BeginArea(new Rect(20, h*.18f, 380, h*.65f), GUI.skin.box);
            GUILayout.Label("Laboratorio · Grupo 6", title);
            GUILayout.Space(18);
            GUILayout.Label("Explora la viga en realidad aumentada o recorre los pisos 1 a 4 del edificio en VR.", label);
            GUILayout.Space(24);
            if (GUILayout.Button("Realidad aumentada · Viga 185", button, GUILayout.Height(70))) OpenAR();
            GUILayout.Space(18);
            GUILayout.Label("VR: coloca el teléfono horizontal en tu Cardboard. Mira las flechas para moverte y los elementos para consultar resultados. El pulsador también selecciona.", label);
            GUILayout.Space(18);
            GUILayout.Label(Error ?? status, label);
            GUILayout.EndArea();
            if (GUI.Button(new Rect(178, h-90, 225, 64), "Visualizador VR", button)) OpenVR();
        }
        else
        {
            if (GUI.Button(new Rect(8, h-52, 105, 44), "Inicio", button)) ReturnToMenu();
            if (GUI.Button(new Rect(185, h-52, 227, 44), "Visualizador VR", button)) OpenVR();
        }
        GUI.enabled = true; GUI.matrix = previous;
    }

    void OnDestroy() { if (Instance == this) Instance = null; }
}
