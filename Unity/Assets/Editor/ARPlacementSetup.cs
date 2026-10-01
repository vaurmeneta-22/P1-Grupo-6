using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
#if USE_AR_FOUNDATION
using Unity.XR.CoreUtils;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.Rendering.Universal;
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
using UnityEngine.XR.Management;
using UnityEditor.XR.Management;
#endif

public static class ARPlacementSetup
{
    public const string ScenePath = "Assets/Scenes/ARBeamPlacement.unity";

    [MenuItem("Lab/AR/Crear colocacion estable v2")]
    public static void CreateScene()
    {
#if !USE_AR_FOUNDATION
        throw new InvalidOperationException("USE_AR_FOUNDATION must be enabled; refusing to build an AR stub.");
#else
        ARWeek6Setup.EnsureARBackgroundRendererFeature();
        var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        var session = new GameObject("AR Session", typeof(ARSession), typeof(ARInputManager));
        var originGo = new GameObject("XR Origin", typeof(XROrigin), typeof(ARPlaneManager), typeof(ARRaycastManager), typeof(ARAnchorManager));
        var origin = originGo.GetComponent<XROrigin>();
        origin.CameraYOffset = 0f;
        origin.RequestedTrackingOriginMode = XROrigin.TrackingOriginMode.Device;
        originGo.GetComponent<ARPlaneManager>().requestedDetectionMode = PlaneDetectionMode.Horizontal;
        var offset = new GameObject("Camera Offset");
        offset.transform.SetParent(originGo.transform, false);
        var cameraGo = new GameObject("AR Camera", typeof(Camera), typeof(AudioListener), typeof(ARCameraManager), typeof(ARCameraBackground), typeof(TrackedPoseDriver));
        cameraGo.transform.SetParent(offset.transform, false);
        cameraGo.tag = "MainCamera";
        var camera = cameraGo.GetComponent<Camera>();
        camera.clearFlags = CameraClearFlags.SolidColor;
        camera.backgroundColor = Color.black;
        camera.nearClipPlane = 0.05f;
        camera.farClipPlane = 100f;
        camera.GetUniversalAdditionalCameraData().renderPostProcessing = false;
        cameraGo.GetComponent<ARCameraManager>().requestedFacingDirection = CameraFacingDirection.World;
        origin.Camera = camera;
        origin.CameraFloorOffsetObject = offset;
        // Match the AR Foundation package's own XR Origin factory, including
        // both XRHMD and HandheldARInputDevice bindings.
        var poseDriver = cameraGo.GetComponent<TrackedPoseDriver>();
        var position = new InputAction("AR Position", binding: "<XRHMD>/centerEyePosition", expectedControlType: "Vector3");
        position.AddBinding("<HandheldARInputDevice>/devicePosition");
        var rotation = new InputAction("AR Rotation", binding: "<XRHMD>/centerEyeRotation", expectedControlType: "Quaternion");
        rotation.AddBinding("<HandheldARInputDevice>/deviceRotation");
        poseDriver.positionInput = new InputActionProperty(position);
        poseDriver.rotationInput = new InputActionProperty(rotation);
        poseDriver.trackingType = TrackedPoseDriver.TrackingType.RotationAndPosition;
        poseDriver.updateType = TrackedPoseDriver.UpdateType.UpdateAndBeforeRender;

        var placement = originGo.AddComponent<ARBeamPlacement>();
        placement.arCamera = camera;
        placement.beamMaterial = MakeMaterial("ARBeamBody", "Universal Render Pipeline/Lit", new Color(0.04f, 0.65f, 0.85f));
        placement.guideMaterial = MakeMaterial("ARBeamGuides", "Universal Render Pipeline/Unlit", new Color(1f, 0.85f, 0.1f));
        var diagrams = originGo.AddComponent<ARBeamDiagrams>();
        diagrams.arCamera = camera;
        diagrams.positiveMaterial = MakeMaterial("ARDiagramPositive", "Universal Render Pipeline/Unlit", new Color(0f, 0.95f, 1f));
        diagrams.negativeMaterial = MakeMaterial("ARDiagramNegative", "Universal Render Pipeline/Unlit", new Color(1f, 0.35f, 0.08f));
        diagrams.zeroMaterial = MakeMaterial("ARDiagramZero", "Universal Render Pipeline/Unlit", Color.white);
        var light = new GameObject("Directional Light", typeof(Light));
        light.GetComponent<Light>().type = LightType.Directional;
        light.GetComponent<Light>().intensity = 1.2f;
        light.transform.rotation = Quaternion.Euler(50, -30, 0);
        RenderSettings.ambientMode = AmbientMode.Flat;
        RenderSettings.ambientLight = new Color(0.65f, 0.65f, 0.65f);
        EditorSceneManager.SaveScene(scene, ScenePath);
        AssetDatabase.SaveAssets();
        ValidateScene();
#endif
    }

    static Material MakeMaterial(string name, string shaderName, Color color)
    {
        if (!AssetDatabase.IsValidFolder("Assets/AR")) AssetDatabase.CreateFolder("Assets", "AR");
        if (!AssetDatabase.IsValidFolder("Assets/AR/Placement")) AssetDatabase.CreateFolder("Assets/AR", "Placement");
        string path = "Assets/AR/Placement/" + name + ".mat";
        var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
        Shader shader = Shader.Find(shaderName);
        if (shader == null) throw new InvalidOperationException("Missing shader: " + shaderName);
        if (mat == null) { mat = new Material(shader); AssetDatabase.CreateAsset(mat, path); }
        mat.shader = shader;
        mat.SetColor("_BaseColor", color);
        EditorUtility.SetDirty(mat);
        return mat;
    }

    static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException("AR PLACEMENT CHECK FAILED: " + message);
    }

    public static void ValidateScene()
    {
#if USE_AR_FOUNDATION
        Require(UnityEngine.Object.FindObjectsByType<Camera>().Length == 1, "Exactly one AR camera");
        Require(UnityEngine.Object.FindObjectsByType<ARInputManager>().Length == 1, "ARInputManager enables device pose subsystem");
        Require(UnityEngine.Object.FindObjectsByType<ARSession>().Length == 1, "Exactly one ARSession");
        Require(UnityEngine.Object.FindObjectsByType<ARTrackedImageManager>().Length == 0, "No marker dependency");
        var origin = UnityEngine.Object.FindAnyObjectByType<XROrigin>();
        Require(origin != null && origin.CameraYOffset == 0f && origin.transform.lossyScale == Vector3.one, "Metric XR origin with no height offset");
        var placement = UnityEngine.Object.FindAnyObjectByType<ARBeamPlacement>();
        Require(placement != null && placement.arCamera == origin.Camera && placement.beamMaterial != null && placement.guideMaterial != null, "Serialized camera and materials");
        var diagrams = origin.GetComponent<ARBeamDiagrams>();
        Require(diagrams != null && diagrams.arCamera == origin.Camera && diagrams.positiveMaterial != null && diagrams.negativeMaterial != null && diagrams.zeroMaterial != null, "Diagram camera and materials");
        var driver = placement.arCamera.GetComponent<TrackedPoseDriver>();
        Require(driver != null && driver.positionInput.action.bindings.Count == 2 && driver.rotationInput.action.bindings.Count == 2, "Position and rotation bindings for mobile AR");
        Require(driver.trackingType == TrackedPoseDriver.TrackingType.RotationAndPosition, "Track both position and rotation");
        Require(driver.updateType == TrackedPoseDriver.UpdateType.UpdateAndBeforeRender, "Update camera before rendering");
        Require(origin.GetComponent<ARAnchorManager>() != null && origin.GetComponent<ARRaycastManager>() != null && origin.GetComponent<ARPlaneManager>() != null, "Plane, raycast and anchor managers");
        var xr = XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android);
        Require(xr != null && xr.InitManagerOnStart && xr.Manager != null, "Android XR initializes on launch");
        bool arcore = false;
        foreach (var loader in xr.Manager.activeLoaders) if (loader != null && loader.GetType().Name == "ARCoreLoader") arcore = true;
        Require(arcore, "Android ARCore provider configured");
        Debug.Log("AR PLACEMENT SCENE CHECKS PASS");
#else
        throw new InvalidOperationException("USE_AR_FOUNDATION missing");
#endif
    }

    // These checks exercise actual transforms with different camera poses. They
    // do not substitute for testing ARCore tracking on a physical device.
    public static void VerifyGeometry()
    {
        var parent = new GameObject("TestAnchor");
        var camera = new GameObject("TestCamera");
        Transform root = null;
        try
        {
            parent.transform.SetPositionAndRotation(new Vector3(2f, 1f, -3f), Quaternion.Euler(0f, 37f, 0f));
            root = ARBeamPlacement.CreateBeam(parent.transform, null, null);
            root.localPosition = Vector3.up * 0.4f;
            var body = root.Find("Viga185_10m_60x80cm");
            Require(body.lossyScale == new Vector3(10f, 0.8f, 0.6f), "Beam dimensions in metres");
            Require(Mathf.Abs(body.TransformPoint(new Vector3(0, -0.5f, 0)).y - parent.transform.position.y) < 1e-5f, "Bottom face rests on detected surface");
            Require(root.GetComponentsInChildren<ElementTag>().Length == 1, "Exactly one ElementTag");
            Require(root.GetComponentInChildren<ElementTag>().elementId == 185, "Element identity");
            Vector3 start = root.position;
            Quaternion orientation = root.rotation;
            camera.transform.SetPositionAndRotation(new Vector3(6f, 2f, 4f), Quaternion.Euler(15, 125, 8));
            Require(Vector3.Distance(root.position, start) < 1e-6f && Quaternion.Angle(root.rotation, orientation) < 0.001f, "Camera motion leaves placed content unchanged");
            foreach (var forward in new[] { Vector3.forward, Vector3.right, Vector3.back, Vector3.left })
            {
                var rotation = ARBeamPlacementMath.BeamRotation(forward, Vector3.Cross(Vector3.up, forward));
                Require(Vector3.Distance(rotation * Vector3.right, forward) < 1e-5f, "Longitudinal X points along arrow");
                var delta = ARBeamPlacementMath.CameraRelativeDelta(forward, Vector3.right, 0, 1, 0);
                Require(Vector3.Distance(delta, forward) < 1e-5f, "Away moves horizontally along view direction");
            }
            var down = ARBeamPlacementMath.HorizontalForward(Vector3.down, Vector3.right);
            Require(Vector3.Distance(down, Vector3.forward) < 1e-5f, "Downward camera has stable horizontal fallback");
            Vector3 centre = root.TransformPoint(new Vector3(5, 0, 0));
            ARBeamPlacementMath.RotateAboutCentre(root, 90);
            Require(Vector3.Distance(root.TransformPoint(new Vector3(5, 0, 0)), centre) < 1e-5f, "Rotation preserves beam centre");
            Require(Vector3.Distance(root.TransformPoint(new Vector3(10, 0, 0)), root.position) > 9.999f, "Rotation does not shrink the beam");
            Vector3 fixedPosition = root.position;
            Quaternion fixedRotation = root.rotation;
            var replacement = new GameObject("ReplacementAnchor");
            replacement.transform.SetPositionAndRotation(centre, root.rotation);
            root.SetParent(replacement.transform, true);
            Require(Vector3.Distance(root.position, fixedPosition) < 1e-5f && Quaternion.Angle(root.rotation, fixedRotation) < 0.01f, "Re-anchoring preserves visible pose");
            UnityEngine.Object.DestroyImmediate(replacement);
            root = null;
            Debug.Log("AR PLACEMENT GEOMETRY CHECKS PASS: scale, identity, camera independence, heading, translation, centre rotation, re-anchoring.");
        }
        finally
        {
            if (root != null) UnityEngine.Object.DestroyImmediate(root.gameObject);
            UnityEngine.Object.DestroyImmediate(parent);
            UnityEngine.Object.DestroyImmediate(camera);
        }
    }

    public static void BuildAndroid()
    {
        CreateScene();
        VerifyGeometry();
        Require(AnalysisMap.Load(Path.Combine(Application.streamingAssetsPath, "analysis_map.json")), "Analysis map loads");
        foreach (string name in new[] { "G", "Q", "EX", "EY", "COMBO" })
        {
            var d = ARBeamDiagrams.ValidatedDiagram(name);
            Debug.Log("AR DIAGRAM CHECK PASS: " + name + "; L=" + d.L + "; samples=" + d.x.Length + "; M_i=" + d.M[0] + "; M_j=" + d.M[d.M.Length - 1] + "; N_i=" + d.N[0] + "; displacement nodes=60,63,67,70; area_m2=" + AnalysisMap.Tributaria(185).area);
        }
        var mobile = AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
        Require(mobile != null, "Mobile renderer exists");
        // Restore project-wide settings after building so the desktop viewer keeps its configuration.
        var previousPipeline = GraphicsSettings.defaultRenderPipeline;
        var previousQualityPipeline = QualitySettings.renderPipeline;
        string previousName = PlayerSettings.productName;
        string previousVersion = PlayerSettings.bundleVersion;
        int previousCode = PlayerSettings.Android.bundleVersionCode;
        var previousOrientation = PlayerSettings.defaultInterfaceOrientation;
        string previousIdentifier = PlayerSettings.GetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android);
        try
        {
            GraphicsSettings.defaultRenderPipeline = mobile;
            QualitySettings.renderPipeline = mobile;
            PlayerSettings.productName = "Viga AR v4";
            PlayerSettings.bundleVersion = "0.4.0";
            PlayerSettings.Android.bundleVersionCode = 4;
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, "com.grupo6.p1.arplacement");
            PlayerSettings.defaultInterfaceOrientation = UIOrientation.Portrait;
            PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel29;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android, false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android, new[] { GraphicsDeviceType.OpenGLES3 });
            AssetDatabase.SaveAssets();
            var options = new UnityEditor.BuildPlayerOptions
            {
                scenes = new[] { ScenePath }, target = BuildTarget.Android,
                locationPathName = "Builds/P1_Grupo6_AR_Resultados_v4.apk", options = BuildOptions.None
            };
            Directory.CreateDirectory("Builds");
            var report = BuildPipeline.BuildPlayer(options);
            Debug.Log("AR PLACEMENT BUILD: " + report.summary.result + "; bytes=" + report.summary.totalSize);
            Require(report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded, "Android build succeeded");
        }
        finally
        {
            GraphicsSettings.defaultRenderPipeline = previousPipeline;
            QualitySettings.renderPipeline = previousQualityPipeline;
            PlayerSettings.productName = previousName;
            PlayerSettings.bundleVersion = previousVersion;
            PlayerSettings.Android.bundleVersionCode = previousCode;
            PlayerSettings.defaultInterfaceOrientation = previousOrientation;
            PlayerSettings.SetApplicationIdentifier(UnityEditor.Build.NamedBuildTarget.Android, previousIdentifier);
            AssetDatabase.SaveAssets();
        }
    }
}
