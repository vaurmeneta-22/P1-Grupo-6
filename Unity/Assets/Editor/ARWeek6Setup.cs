using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
#if USE_AR_FOUNDATION
using UnityEngine.XR.ARFoundation;
using Unity.XR.CoreUtils;
using UnityEngine.XR.ARSubsystems;
using UnityEditor.XR.ARSubsystems;
using UnityEngine.Rendering.Universal;
#endif
using System.IO;

// Tooling de Semana 6: crea marker PNG y escena AR base para la demo Viga 185.
public static class ARWeek6Setup
{
    const string MarkerDir = "Assets/AR/Markers";
    const string MarkerPath = MarkerDir + "/Grupo6_Viga185_AR.png";
    const string ImageLibraryPath = "Assets/AR/Grupo6_Viga185_ImageLibrary.asset";
    const string ScenePath = "Assets/Scenes/ARViga185.unity";
    const string MobileRendererPath = "Assets/Settings/Mobile_Renderer.asset";

    [MenuItem("Lab/AR Semana 6/Crear marker Viga 185")]
    public static void CreateMarker()
    {
        Directory.CreateDirectory(Path.Combine(Application.dataPath, "AR/Markers"));
        Texture2D tex = new Texture2D(1024, 1024, TextureFormat.RGBA32, false);
        Color white = Color.white;
        Color black = Color.black;
        Color cyan = new Color(0.0f, 0.75f, 1f, 1f);
        Color orange = new Color(1f, 0.55f, 0f, 1f);

        for (int y = 0; y < tex.height; y++)
            for (int x = 0; x < tex.width; x++)
                tex.SetPixel(x, y, white);

        Fill(tex, 0, 0, 1024, 60, black);
        Fill(tex, 0, 964, 1024, 60, black);
        Fill(tex, 0, 0, 60, 1024, black);
        Fill(tex, 964, 0, 60, 1024, black);

        Fill(tex, 105, 680, 300, 240, black);
        Fill(tex, 145, 720, 220, 160, white);
        Fill(tex, 185, 760, 140, 80, black);

        Fill(tex, 620, 110, 300, 240, black);
        Fill(tex, 660, 150, 220, 160, white);
        Fill(tex, 700, 190, 140, 80, black);

        Fill(tex, 125, 140, 120, 120, cyan);
        Fill(tex, 285, 230, 110, 260, black);
        Fill(tex, 455, 140, 95, 510, orange);
        Fill(tex, 600, 430, 280, 95, black);
        Fill(tex, 690, 610, 180, 160, cyan);

        tex.Apply();
        File.WriteAllBytes(Path.Combine(Application.dataPath, "AR/Markers/Grupo6_Viga185_AR.png"), tex.EncodeToPNG());
        Object.DestroyImmediate(tex);
        AssetDatabase.ImportAsset(MarkerPath);
        TextureImporter importer = AssetImporter.GetAtPath(MarkerPath) as TextureImporter;
        if (importer != null)
        {
            importer.textureType = TextureImporterType.Default;
            importer.mipmapEnabled = false;
            importer.isReadable = true;
            importer.SaveAndReimport();
        }
        Debug.Log("Marker creado: " + MarkerPath + ". Agregarlo a una XR Reference Image Library con nombre Grupo6_Viga185_AR y ancho fisico 0.20 m.");
    }

    [MenuItem("Lab/AR Semana 6/Crear escena AR Viga 185")]
    public static void CreateARScene()
    {
        CreateMarker();
#if !USE_AR_FOUNDATION
        Debug.LogWarning("AR Foundation no esta activo. Instala paquetes AR compatibles y define USE_AR_FOUNDATION para crear la escena AR real.");
        return;
#else
        Directory.CreateDirectory(Path.Combine(Application.dataPath, "Scenes"));
        XRReferenceImageLibrary imageLibrary = CreateImageLibrary();
        EnsureARBackgroundRendererFeature();

        Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        RenderSettings.ambientLight = Color.white;

        GameObject sessionGO = new GameObject("AR Session");
        sessionGO.AddComponent<ARSession>();

        GameObject originGO = new GameObject("XR Origin");
        XROrigin origin = originGO.AddComponent<XROrigin>();
        ARTrackedImageManager imageManager = originGO.AddComponent<ARTrackedImageManager>();
        imageManager.referenceLibrary = imageLibrary;
        originGO.AddComponent<ARAnchorManager>();
        originGO.AddComponent<ARRaycastManager>();
        originGO.AddComponent<ARPlaneManager>();
        originGO.AddComponent<ARViga185Demo>();

        GameObject offsetGO = new GameObject("Camera Offset");
        offsetGO.transform.SetParent(originGO.transform, false);

        GameObject camGO = new GameObject("AR Camera");
        camGO.transform.SetParent(offsetGO.transform, false);
        camGO.tag = "MainCamera";
        Camera cam = camGO.AddComponent<Camera>();
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = Color.black;
        cam.nearClipPlane = 0.05f;
        cam.farClipPlane = 50f;
        camGO.AddComponent<AudioListener>();
        camGO.AddComponent<ARCameraManager>();
        camGO.AddComponent<ARCameraBackground>();
        var poseDriver = camGO.AddComponent<UnityEngine.SpatialTracking.TrackedPoseDriver>();
        poseDriver.SetPoseSource(UnityEngine.SpatialTracking.TrackedPoseDriver.DeviceType.GenericXRDevice,
            UnityEngine.SpatialTracking.TrackedPoseDriver.TrackedPose.Center);
        poseDriver.trackingType = UnityEngine.SpatialTracking.TrackedPoseDriver.TrackingType.RotationAndPosition;
        poseDriver.updateType = UnityEngine.SpatialTracking.TrackedPoseDriver.UpdateType.UpdateAndBeforeRender;

        origin.Camera = cam;
        origin.CameraFloorOffsetObject = offsetGO;

        GameObject lightGO = new GameObject("Directional Light");
        Light light = lightGO.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.2f;
        lightGO.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

        EditorSceneManager.SaveScene(scene, ScenePath);
        AddSceneToBuild(ScenePath);
        Debug.Log("Escena AR creada: " + ScenePath + " con Grupo6_Viga185_ImageLibrary asignada al ARTrackedImageManager.");
#endif
    }

#if USE_AR_FOUNDATION
    public static void EnsureARBackgroundRendererFeature()
    {
        ScriptableRendererData rendererData = AssetDatabase.LoadAssetAtPath<ScriptableRendererData>(MobileRendererPath);
        if (rendererData == null)
        {
            Debug.LogWarning("No se encontro " + MobileRendererPath + "; no se pudo configurar ARBackgroundRendererFeature.");
            return;
        }

        foreach (ScriptableRendererFeature existing in rendererData.rendererFeatures)
        {
            if (existing is ARBackgroundRendererFeature) return;
        }

        ARBackgroundRendererFeature feature = ScriptableObject.CreateInstance<ARBackgroundRendererFeature>();
        feature.name = "AR Background Renderer Feature";
        AssetDatabase.AddObjectToAsset(feature, rendererData);
        AssetDatabase.SaveAssets();

        if (!AssetDatabase.TryGetGUIDAndLocalFileIdentifier(feature, out string _, out long localId))
        {
            Debug.LogWarning("No se pudo obtener localId para ARBackgroundRendererFeature.");
            return;
        }

        SerializedObject so = new SerializedObject(rendererData);
        SerializedProperty features = so.FindProperty("m_RendererFeatures");
        SerializedProperty map = so.FindProperty("m_RendererFeatureMap");
        int index = features.arraySize;
        features.InsertArrayElementAtIndex(index);
        features.GetArrayElementAtIndex(index).objectReferenceValue = feature;
        map.InsertArrayElementAtIndex(index);
        map.GetArrayElementAtIndex(index).longValue = localId;
        so.ApplyModifiedProperties();
        rendererData.SetDirty();
        EditorUtility.SetDirty(rendererData);
        AssetDatabase.SaveAssets();
        Debug.Log("ARBackgroundRendererFeature agregado a " + MobileRendererPath + ".");
    }

    static XRReferenceImageLibrary CreateImageLibrary()
    {
        Directory.CreateDirectory(Path.Combine(Application.dataPath, "AR"));
        Texture2D marker = AssetDatabase.LoadAssetAtPath<Texture2D>(MarkerPath);
        XRReferenceImageLibrary library = AssetDatabase.LoadAssetAtPath<XRReferenceImageLibrary>(ImageLibraryPath);
        if (library == null)
        {
            library = ScriptableObject.CreateInstance<XRReferenceImageLibrary>();
            AssetDatabase.CreateAsset(library, ImageLibraryPath);
        }
        while (library.count > 0) library.RemoveAt(0);
        library.Add();
        library.SetName(0, "Grupo6_Viga185_AR");
        library.SetTexture(0, marker, true);
        library.SetSpecifySize(0, true);
        library.SetSize(0, new Vector2(0.20f, 0.20f));
        EditorUtility.SetDirty(library);
        AssetDatabase.SaveAssets();
        return library;
    }
#endif

    static void AddSceneToBuild(string scenePath)
    {
        var scenes = new System.Collections.Generic.List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
        if (!scenes.Exists(s => s.path == scenePath))
        {
            scenes.Add(new EditorBuildSettingsScene(scenePath, true));
            EditorBuildSettings.scenes = scenes.ToArray();
        }
    }

    static void Fill(Texture2D tex, int x0, int y0, int w, int h, Color c)
    {
        for (int y = y0; y < y0 + h && y < tex.height; y++)
            for (int x = x0; x < x0 + w && x < tex.width; x++)
                tex.SetPixel(x, y, c);
    }
}
