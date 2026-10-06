using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.XR.Management;
using UnityEditor.XR.Management.Metadata;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.XR;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.SceneManagement;
using UnityEngine.XR.Management;

public static class VRMobileSetup
{
    const string MenuPath="Assets/Scenes/MobileLabMenu.unity";
    const string VRPath="Assets/Scenes/VRFloor3.unity";
    const string APK="Builds/P1_Grupo6_AR_VR_v11.apk";

    [Serializable] class Evidence
    {
        public int floor,elements,slabs,ceiling_slabs,joint_passages,diagrams,capacity;
        public float ground_m;
        public double max_diagram_error_M_kNm,max_diagram_error_V_kN,max_diagram_error_N_kN;
        public string checks,physical_cardboard_test;
    }

    static void Require(bool condition,string text)
    { if(!condition) throw new InvalidOperationException("H1 CHECK FAILED: "+text); }

    [MenuItem("Lab/Móvil/Crear escenas AR + VR pisos 1 a 4")]
    public static void CreateScenes()
    {
        var xr=XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android);
        Require(xr!=null && xr.Manager!=null,"Android XR settings");
        Require(XRPackageMetadataStore.AssignLoader(xr.Manager,"Google.XR.Cardboard.XRLoader",BuildTargetGroup.Android)
            || xr.Manager.activeLoaders.Any(l=>l is Google.XR.Cardboard.XRLoader),"Cardboard loader registered");
        var ar=xr.Manager.activeLoaders.FirstOrDefault(l=>l.GetType().Name=="ARCoreLoader");
        var vr=xr.Manager.activeLoaders.FirstOrDefault(l=>l is Google.XR.Cardboard.XRLoader);
        Require(ar!=null && vr!=null,"Both ARCore and Cardboard registered");
        Require(xr.Manager.TrySetLoaders(new List<XRLoader>{ar,vr}),"ARCore first for legacy AR-only builds");
        // AR's legacy scene validator expects startup initialization. Combined
        // APK switches explicitly, and sets InitManagerOnStart=false at build.
        bool previousInit=xr.InitManagerOnStart;
        xr.InitManagerOnStart=true;
        try { ARPlacementSetup.CreateScene(); }
        finally { xr.InitManagerOnStart=previousInit; }
        var menuScene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var menu=new GameObject("Mobile modes",typeof(MobileLabMenu)).GetComponent<MobileLabMenu>();
        menu.arLoader=ar; menu.cardboardLoader=vr;
        var menuCamera=new GameObject("Menu camera",typeof(Camera)); menuCamera.tag="MainCamera";
        menuCamera.GetComponent<Camera>().clearFlags=CameraClearFlags.SolidColor;
        menuCamera.GetComponent<Camera>().backgroundColor=new Color(.045f,.08f,.12f);
        EditorSceneManager.SaveScene(menuScene,MenuPath);

        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        var root=new GameObject("Recorrido pisos 1 a 4",typeof(VRFloorTour));
        var tour=root.GetComponent<VRFloorTour>();
        var player=new GameObject("Visitante",typeof(CharacterController)); player.layer=2;
        var body=player.GetComponent<CharacterController>(); body.height=1.7f; body.radius=VRFloorModel.BodyRadius;
        body.center=new Vector3(0,.85f,0); body.stepOffset=0; body.skinWidth=.02f; body.minMoveDistance=0;
        var cameraGO=new GameObject("Cabeza VR",typeof(Camera),typeof(AudioListener),typeof(TrackedPoseDriver));
        cameraGO.tag="MainCamera"; cameraGO.transform.SetParent(player.transform,false); cameraGO.transform.localPosition=Vector3.up*1.6f;
        var camera=cameraGO.GetComponent<Camera>(); camera.nearClipPlane=.05f; camera.farClipPlane=180; camera.fieldOfView=75;
        camera.clearFlags=CameraClearFlags.SolidColor; camera.backgroundColor=new Color(.30f,.43f,.57f);
        camera.stereoTargetEye=StereoTargetEyeMask.Both;
        var pose=cameraGO.GetComponent<TrackedPoseDriver>();
        var rotation=new InputAction("Cardboard head rotation",binding:"<XRHMD>/centerEyeRotation",expectedControlType:"Quaternion");
        rotation.AddBinding("<XRHMD>/deviceRotation");
        pose.rotationInput=new InputActionProperty(rotation); pose.trackingType=TrackedPoseDriver.TrackingType.RotationOnly;
        pose.updateType=TrackedPoseDriver.UpdateType.UpdateAndBeforeRender; pose.ignoreTrackingState=true;
        tour.head=camera; tour.body=body;
        tour.geometryShader=Shader.Find("Universal Render Pipeline/Lit"); tour.spriteShader=Shader.Find("Sprites/Default");
        Require(tour.geometryShader!=null && tour.spriteShader!=null,"Geometry and graph shaders retained");
        if(!AssetDatabase.IsValidFolder("Assets/VR")) AssetDatabase.CreateFolder("Assets","VR");
        var material=AssetDatabase.LoadAssetAtPath<Material>("Assets/VR/VRGraph.mat");
        var uiShader=Shader.Find("Grupo6/VR UI"); Require(uiShader!=null,"Stereo-compatible world UI shader");
        if(material==null) { material=new Material(uiShader); AssetDatabase.CreateAsset(material,"Assets/VR/VRGraph.mat"); }
        material.shader=uiShader; EditorUtility.SetDirty(material);
        tour.lineMaterial=material;
        var light=new GameObject("Luz",typeof(Light)); var sun=light.GetComponent<Light>(); sun.type=LightType.Directional; sun.intensity=1.1f; sun.shadows=LightShadows.None;
        light.transform.rotation=Quaternion.Euler(48,-35,0);
        RenderSettings.ambientMode=AmbientMode.Flat; RenderSettings.ambientLight=new Color(.65f,.68f,.72f);
        EditorSceneManager.SaveScene(scene,VRPath);
        var scenes=EditorBuildSettings.scenes.ToList();
        foreach(string path in new[]{MenuPath,"Assets/Scenes/ARBeamPlacement.unity",VRPath})
        {
            int index=scenes.FindIndex(s=>s.path==path);
            if(index<0) scenes.Add(new EditorBuildSettingsScene(path,true));
            else scenes[index]=new EditorBuildSettingsScene(path,true);
        }
        EditorBuildSettings.scenes=scenes.ToArray();
        AssetDatabase.SaveAssets();
        Debug.Log("H1 SCENES CREATED: mobile menu, AR placement and VR floors 1-4 (start on 3).");
    }

    [MenuItem("Lab/Móvil/Verificar VR pisos 1 a 4")]
    public static void Validate()
    {
        for(int number=1;number<=4;number++) ValidateFloor(number);
        EditorSceneManager.OpenScene(VRPath);
    }

    static void ValidateFloor(int number)
    {
        EditorSceneManager.OpenScene(VRPath);
        var tour=UnityEngine.Object.FindAnyObjectByType<VRFloorTour>();
        Require(tour!=null && tour.head!=null && tour.body!=null,"Tour, camera and collision controller");
        Require(tour.head.stereoTargetEye==StereoTargetEyeMask.Both,"Both eyes enabled");
        Require(tour.head.GetComponent<TrackedPoseDriver>().trackingType==TrackedPoseDriver.TrackingType.RotationOnly,"Head tracking without positional drift");
        Require(AnalysisMap.Load(Path.Combine(Application.streamingAssetsPath,"analysis_map.json")),"Analysis map loads");
        var data=JsonUtility.FromJson<EdificioData>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"Edificio.json")));
        tour.BuildFloor(data,number);
        Require(tour.Floor.JointPassages.Count==1,"Joint cover confined to unobstructed central corridor");
        foreach(float z in new[]{8.5f,9f})
            for(float x=-1f;x<=.5f;x+=.025f)
                Require(tour.Floor.CanStand(new Vector3(x,tour.Floor.Ground,z)),"Continuous joint support at "+x+" / "+z);
        Require(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,11f)),"Joint cover does not fill stair opening");
        Require(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,2f)),"No joint cover through front wall");
        Require(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,14f)),"No joint cover through rear wall");
        Require(!tour.Floor.CanStand(new Vector3(5,tour.Floor.Ground,4)),"Other stair opening preserved");
        int[] slabCounts={27,41,45,48}, roofCounts={41,45,48,38};
        Require(tour.Floor.Walkable.Count==slabCounts[number-1],"Actual floor slabs retained on "+number);
        Require(tour.Floor.CeilingIds.Count==roofCounts[number-1],"Actual ceiling slabs retained on "+number);
        foreach(var ceiling in tour.Solids.GetComponentsInChildren<ElementTag>().Where(t=>tour.Floor.CeilingIds.Contains(t.elementId)))
        {
            Require(ceiling.GetComponent<Renderer>().sharedMaterial.color.a==1,"Opaque ceiling underside "+ceiling.elementId);
            float thickness=data.elements.Find(e=>e.id==ceiling.elementId).t*.01f;
            Require(Mathf.Abs(ceiling.transform.localScale.y-thickness)<1e-5f,"Ceiling structural thickness in metres "+ceiling.elementId);
        }
        var ids=new HashSet<int>(); var tags=tour.Solids.GetComponentsInChildren<ElementTag>();
        int diagrams=0,capacity=0;
        double maxM=0,maxV=0,maxN=0;
        foreach(var tag in tags)
        {
            Require(ids.Add(tag.elementId),"Unique selected ID "+tag.elementId);
            Require(AnalysisMap.Element(tag.elementId)!=null,"Contract ID in results "+tag.elementId);
            if(tag.type=="loza") continue;
            foreach(string name in new[]{"G","Q","EX","EY","COMBO"})
                for(int plane=0;plane<2;plane++)
                {
                    var r=ElementDiagrams.Construir(tag.elementId,name,plane);
                    if(r.error!=null) continue; // Real missing data stays explicit in UI.
                    Require(r.diag.x.Length==r.diag.M.Length && r.diag.x.Length>1,"Diagram samples "+tag.elementId);
                    foreach(double value in r.diag.M.Concat(r.diag.V).Concat(r.diag.N)) Require(!double.IsInfinity(value)&&!double.IsNaN(value),"Finite results");
                    maxM=Math.Max(maxM,r.errM); maxV=Math.Max(maxV,r.errV); maxN=Math.Max(maxN,r.errN); diagrams++;
                }
            if(PickHighlight.CapacityCur(AnalysisMap.Element(tag.elementId))!=null) capacity++;
        }
        Require(diagrams>0 && capacity>0,"Results and capacity accessible");
        Require(maxM<1e-4 && maxV<1e-4 && maxN<1e-4,"Diagram closure tolerance in kN and kN-m");
        var spawn=tour.FindSpawn();
        Require(tour.Floor.CanStand(spawn),"Spawn has slab support");
        Require(!tour.Floor.CanStand(new Vector3(10000,spawn.y,10000)),"Reject walking beyond floor");
        for(int arrow=0;arrow<4;arrow++) Require(Mathf.Abs(VRFloorModel.Direction(new Vector3(.3f,-.5f,1),arrow).y)<1e-6,"Horizontal movement "+arrow);
        Require(Vector3.Dot(VRFloorModel.Direction(Vector3.forward,0),VRFloorModel.Direction(Vector3.forward,1))<-.999,"Forward / backward opposed");
        Require(Vector3.Dot(VRFloorModel.Direction(Vector3.forward,2),VRFloorModel.Direction(Vector3.forward,3))<-.999,"Left / right opposed");
        tour.body.enabled=false; tour.body.transform.position=spawn; tour.body.enabled=true;
        var obstacle=GameObject.CreatePrimitive(PrimitiveType.Cube); obstacle.name="H1 collision test";
        obstacle.transform.position=spawn+new Vector3(0,.9f,.8f); obstacle.transform.localScale=new Vector3(2,1.8f,.1f);
        Physics.SyncTransforms();
        for(int i=0;i<20;i++) tour.Move(0,.1f);
        Require(tour.body.transform.position.z < spawn.z+.65f,"Collision prevents walking through wall");
        UnityEngine.Object.DestroyImmediate(obstacle);
        tour.body.enabled=false; tour.body.transform.position=spawn; tour.body.enabled=true;

        var ui=new VRWorldUI(tour,tour.lineMaterial);
        Require(ui.Arrows.Count==4 && ui.Arrows.All(a=>a.GetComponent<Collider>()!=null),"Four gaze-selectable arrows");
        Require(ui.FloorButtons.Count==4 && ui.FloorButtons.All(a=>a.GetComponent<Collider>()!=null && a.activate!=null),"Four gaze-selectable floors");
        Require(ui.Heading.text.Contains("PISO "+number),"Navigation heading matches active floor");
        tour.head.transform.rotation=Quaternion.Euler(0,90,0);
        for(int i=0;i<20;i++) ui.FollowNavigation(tour.head,.05f,false);
        Require(Vector3.Angle(ui.Root.transform.forward,Vector3.right)<3.1f,"Controls follow right turn");
        tour.head.transform.rotation=Quaternion.Euler(22,103,0);
        var panelHeading=ui.Root.transform.rotation;
        ui.FollowNavigation(tour.head,.1f,false);
        Require(Quaternion.Angle(panelHeading,ui.Root.transform.rotation)<.001f,"Looking down freezes control selection");
        Require(Vector3.Angle(ui.NavigationForward,Vector3.right)<.001f,"Advance retains corridor heading while selecting lateral controls");
        tour.head.transform.rotation=Quaternion.Euler(22,180,0);
        ui.FollowNavigation(tour.head,.1f,false);
        Require(Vector3.Angle(ui.NavigationForward,Vector3.back)<.001f,"Large turn retrieves controls even while looking down");
        tour.head.transform.rotation=Quaternion.identity; ui.Align(tour.head);
        var floorRowPose=ui.Root.transform.rotation;
        var floorRowPosition=ui.Root.transform.position;
        tour.head.transform.rotation=Quaternion.Euler(30,50,0);
        ui.FollowNavigation(tour.head,.1f,false);
        Require(Quaternion.Angle(floorRowPose,ui.Root.transform.rotation)<.001f && Vector3.Distance(floorRowPosition,ui.Root.transform.position)<.001f,"Floor selection keeps panel fixed between buttons despite yaw");
        Require(ui.FloorButtons.All(a=>a.GetComponent<RectTransform>().anchoredPosition.y < ui.Arrows.Min(b=>b.GetComponent<RectTransform>().anchoredPosition.y)-50),"Floor row below all movement arrows");
        tour.head.transform.rotation=Quaternion.identity;
        var beam=tags.FirstOrDefault(t=>t.type=="beam_x"||t.type=="beam_y");
        var column=tags.FirstOrDefault(t=>t.type=="column"&&t.section=="70x70");
        Require(beam!=null && column!=null,"Beam and column selectable");
        var result=new VRResults { Selected=beam };
        ui.ShowResults(beam);
        var stableCard=ui.Root.transform.rotation;
        ui.FollowNavigation(tour.head,.1f,false);
        Require(Quaternion.Angle(stableCard,ui.Root.transform.rotation)<.001f,"Result card remains stable while reading");
        foreach(string name in new[]{"G","Q","EX","EY","COMBO"})
            for(int view=0;view<3;view++) for(int plane=0;plane<2;plane++)
            { result.Case=name; result.View=view; result.Plane=plane; result.Render(ui); Require(result.LastError==null,"Render diagram "+name+"/"+view+"/"+plane); }
        result.Selected=column; ui.ShowResults(column);
        result.View=3; result.Render(ui); Require(result.LastError==null,"Render P-M capacity and demand");
        result.View=4; result.Render(ui); Require(result.LastError==null,"Render moment-curvature reference");
        if(number==3) CapturePreview(tour,ui,result,beam,column,spawn);
        else
        {
            ui.ShowNavigation(); ui.Align(tour.head); tour.head.aspect=16f/9f;
            Capture(tour.head,"Builds/H1_floor"+number+"_preview.png");
        }
        ui.Dispose();
        var evidence=new Evidence {
            floor=number,elements=ids.Count, slabs=tour.Floor.Walkable.Count, ceiling_slabs=tour.Floor.CeilingIds.Count, joint_passages=tour.Floor.JointPassages.Count, ground_m=tour.Floor.Ground,
            diagrams=diagrams, capacity=capacity, max_diagram_error_M_kNm=maxM, max_diagram_error_V_kN=maxV,max_diagram_error_N_kN=maxN,
            checks="IDs, units, actual floor and opaque ceiling slabs, joint continuity and stair holes, four floor buttons, four arrows, yaw-following and locked corridor heading, collisions, head driver, both eyes, 5 cases / 2 planes, capacity and M-curvature UI",
            physical_cardboard_test="pending"
        };
        Directory.CreateDirectory("Builds");
        File.WriteAllText("Builds/H1_floor"+number+"_checks.json",JsonUtility.ToJson(evidence,true));
        if(number==3) File.WriteAllText("Builds/H1_checks.json",JsonUtility.ToJson(evidence,true));
        Debug.Log("H1 CHECKS PASS: floor="+number+"; elements="+ids.Count+"; diagrams="+diagrams+"; capacity="+capacity+"; maxM="+maxM+"; maxV="+maxV+"; maxN="+maxN);
        // Discard runtime-generated geometry rather than save duplicate elements.
        EditorSceneManager.OpenScene(VRPath);
    }

    static void CapturePreview(VRFloorTour tour,VRWorldUI ui,VRResults result,ElementTag beam,ElementTag column,Vector3 spawn)
    {
        Directory.CreateDirectory("Builds");
        tour.head.aspect=16f/9f;
        tour.head.transform.rotation=Quaternion.identity;
        ui.ShowNavigation(); ui.Align(tour.head);
        Capture(tour.head,"Builds/H1_navigation_preview.png");
        tour.head.transform.rotation=Quaternion.Euler(-55,0,0);
        Capture(tour.head,"Builds/H1_ceiling_preview.png");
        tour.head.transform.rotation=Quaternion.identity;
        ui.ShowResults(beam); ui.Align(tour.head); result.Selected=beam; result.Case="G"; result.View=2; result.Plane=0;
        result.Render(ui); Capture(tour.head,"Builds/H1_moment_preview.png");
        ui.ShowResults(column); ui.Align(tour.head); result.Selected=column; result.View=3;
        result.Render(ui); Capture(tour.head,"Builds/H1_capacity_preview.png");
    }

    static void Capture(Camera camera,string path)
    {
        Canvas.ForceUpdateCanvases();
        var target=new RenderTexture(1600,900,24,RenderTextureFormat.ARGB32);
        var previous=RenderTexture.active;
        var previousPipeline=GraphicsSettings.defaultRenderPipeline;
        var previousQuality=QualitySettings.renderPipeline;
        try
        {
            GraphicsSettings.defaultRenderPipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
            QualitySettings.renderPipeline=GraphicsSettings.defaultRenderPipeline;
            camera.targetTexture=target;
            camera.Render();
            RenderPipeline.SubmitRenderRequest(camera,new UniversalRenderPipeline.SingleCameraRequest { destination=target });
            RenderTexture.active=target;
            var texture=new Texture2D(1600,900,TextureFormat.RGB24,false);
            texture.ReadPixels(new Rect(0,0,1600,900),0,0); texture.Apply();
            File.WriteAllBytes(path,texture.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(texture);
        }
        finally {
            camera.targetTexture=null; RenderTexture.active=previous; target.Release(); UnityEngine.Object.DestroyImmediate(target);
            GraphicsSettings.defaultRenderPipeline=previousPipeline; QualitySettings.renderPipeline=previousQuality;
        }
    }

    static void PrepareGradle()
    {
        string folder="Assets/Plugins/Android"; Directory.CreateDirectory(folder);
        string templates=Path.Combine(EditorApplication.applicationContentsPath,"PlaybackEngines/AndroidPlayer/Tools/GradleTemplates");
        string path=folder+"/mainTemplate.gradle";
        string text=File.Exists(path)?File.ReadAllText(path):File.ReadAllText(Path.Combine(templates,"mainTemplate.gradle"));
        if(!text.Contains("play-services-vision"))
        {
            const string deps="    implementation 'androidx.appcompat:appcompat:1.6.1'\n    implementation 'com.google.android.gms:play-services-vision:20.1.3'\n    implementation 'com.google.android.material:material:1.12.0'\n    implementation 'com.google.protobuf:protobuf-javalite:3.19.4'\n";
            Require(text.Contains("dependencies {"),"Gradle dependencies marker");
            text=text.Replace("dependencies {","dependencies {\n"+deps);
            File.WriteAllText(path,text);
        }
        path=folder+"/gradleTemplate.properties";
        text=File.Exists(path)?File.ReadAllText(path):File.ReadAllText(Path.Combine(templates,"gradleTemplate.properties"));
        if(!text.Contains("android.enableJetifier=")) text+="\nandroid.enableJetifier=true\n";
        if(!text.Contains("android.useAndroidX=")) text+="android.useAndroidX=true\n";
        File.WriteAllText(path,text);
        var settings=new SerializedObject(Unsupported.GetSerializedAssetInterfaceSingleton("PlayerSettings"));
        settings.FindProperty("useCustomMainGradleTemplate").boolValue=true;
        settings.FindProperty("useCustomGradlePropertiesTemplate").boolValue=true;
        settings.ApplyModifiedPropertiesWithoutUndo();
        AssetDatabase.Refresh();
    }

    [MenuItem("Lab/Móvil/Compilar APK AR + Cardboard VR")]
    public static void BuildAndroid()
    {
        CreateScenes(); Validate(); PrepareGradle();
        var xr=XRGeneralSettingsPerBuildTarget.XRGeneralSettingsForBuildTarget(BuildTargetGroup.Android);
        var target=UnityEditor.Build.NamedBuildTarget.Android;
        string previousName=PlayerSettings.productName, previousVersion=PlayerSettings.bundleVersion;
        string previousId=PlayerSettings.GetApplicationIdentifier(target);
        int previousCode=PlayerSettings.Android.bundleVersionCode;
        bool previousInit=xr.InitManagerOnStart;
        var previousOrientation=PlayerSettings.defaultInterfaceOrientation;
        var previousEntry=PlayerSettings.Android.applicationEntry;
        var previousPipeline=GraphicsSettings.defaultRenderPipeline;
        var previousQuality=QualitySettings.renderPipeline;
        var previousAPI=PlayerSettings.GetGraphicsAPIs(BuildTarget.Android);
        bool previousDefaultAPI=PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.Android);
        var previousFramePacing=PlayerSettings.Android.optimizedFramePacing;
        var previousTargetSDK=PlayerSettings.Android.targetSdkVersion;
        try
        {
            xr.InitManagerOnStart=false; EditorUtility.SetDirty(xr);
            PlayerSettings.productName="Laboratorio Grupo 6"; PlayerSettings.bundleVersion="0.6.1"; PlayerSettings.Android.bundleVersionCode=11;
            PlayerSettings.SetApplicationIdentifier(target,"com.grupo6.p1.arplacement");
            PlayerSettings.defaultInterfaceOrientation=UIOrientation.Portrait;
            PlayerSettings.Android.applicationEntry=AndroidApplicationEntry.Activity;
            PlayerSettings.Android.optimizedFramePacing=false;
            PlayerSettings.Android.minSdkVersion=AndroidSdkVersions.AndroidApiLevel29;
            PlayerSettings.Android.targetSdkVersion=AndroidSdkVersions.AndroidApiLevel36;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android,false);
            PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,new[]{GraphicsDeviceType.OpenGLES3});
            GraphicsSettings.defaultRenderPipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
            QualitySettings.renderPipeline=GraphicsSettings.defaultRenderPipeline;
            PlayerSettings.Android.forceInternetPermission=true;
            AssetDatabase.SaveAssets();
            var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions {
                scenes=new[]{MenuPath,ARPlacementSetup.ScenePath,VRPath},target=BuildTarget.Android,locationPathName=APK,options=BuildOptions.None
            });
            Require(report.summary.result==UnityEditor.Build.Reporting.BuildResult.Succeeded,"Android build: "+report.summary.result);
            Debug.Log("H1 MOBILE BUILD: Succeeded; apk="+APK+"; bytes="+new FileInfo(APK).Length);
        }
        finally
        {
            xr.InitManagerOnStart=previousInit; EditorUtility.SetDirty(xr);
            PlayerSettings.productName=previousName; PlayerSettings.bundleVersion=previousVersion; PlayerSettings.Android.bundleVersionCode=previousCode;
            PlayerSettings.SetApplicationIdentifier(target,previousId); PlayerSettings.defaultInterfaceOrientation=previousOrientation;
            PlayerSettings.Android.applicationEntry=previousEntry; PlayerSettings.Android.optimizedFramePacing=previousFramePacing;
            PlayerSettings.Android.targetSdkVersion=previousTargetSDK;
            PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.Android,previousDefaultAPI); PlayerSettings.SetGraphicsAPIs(BuildTarget.Android,previousAPI);
            GraphicsSettings.defaultRenderPipeline=previousPipeline; QualitySettings.renderPipeline=previousQuality;
            AssetDatabase.SaveAssets();
        }
    }
}
