using System;
using System.Collections;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

// Run without -quit: the update callback exits after the real Play Mode check.
public static class VRPlayCheck
{
    static IEnumerator routine;
    static double deadline;
    static bool optionsEnabled;
    static EnterPlayModeOptions options;
    static RenderPipelineAsset pipeline,quality;
    static int errors;
    public static void Run()
    {
        VRMobileSetup.CreateScenes();
        optionsEnabled=EditorSettings.enterPlayModeOptionsEnabled;
        options=EditorSettings.enterPlayModeOptions;
        EditorSettings.enterPlayModeOptionsEnabled=true;
        EditorSettings.enterPlayModeOptions=EnterPlayModeOptions.DisableDomainReload;
        pipeline=GraphicsSettings.defaultRenderPipeline; quality=QualitySettings.renderPipeline;
        GraphicsSettings.defaultRenderPipeline=AssetDatabase.LoadAssetAtPath<RenderPipelineAsset>("Assets/Settings/Mobile_RPAsset.asset");
        QualitySettings.renderPipeline=GraphicsSettings.defaultRenderPipeline;
        EditorSceneManager.OpenScene("Assets/Scenes/MobileLabMenu.unity");
        Application.logMessageReceived+=Log;
        deadline=EditorApplication.timeSinceStartup+240;
        routine=Check(); EditorApplication.update+=Tick;
        EditorApplication.EnterPlaymode();
    }
    static void Log(string text,string trace,LogType type)
    { if(type==LogType.Error || type==LogType.Exception || type==LogType.Assert) errors++; }
    static void Assert(bool value,string text)
    { if(!value) throw new Exception("H1 PLAY CHECK: "+text); }
    static void Tick()
    {
        try
        {
            if(EditorApplication.timeSinceStartup>deadline) throw new Exception("H1 Play Mode timeout");
            if(!routine.MoveNext()) Finish(errors==0?0:1);
        }
        catch(Exception ex) { Debug.LogException(ex); Finish(1); }
    }
    static IEnumerator Check()
    {
        while(!EditorApplication.isPlaying || MobileLabMenu.Instance==null) yield return null;
        var menu=MobileLabMenu.Instance; menu.OpenVR();
        VRFloorTour tour;
        while((tour=UnityEngine.Object.FindAnyObjectByType<VRFloorTour>())==null || !tour.Ready || menu.Busy) yield return null;
        Assert(!menu.NativeVR,"Editor preview must not claim native stereo");
        Assert(tour.Floor.CeilingIds.Count==48,"Roof includes 48 original slabs");
        tour.head.transform.localRotation=Quaternion.Euler(0,90,0);
        for(int i=0;i<35;i++) yield return null;
        Assert(Vector3.Angle(tour.NavigationForward,Vector3.right)<1,"Corridor heading follows right turn");
        // With the upper floor row removed, this ray can dwell on a real
        // element. Close its card before testing deliberate locomotion.
        tour.CloseResults();
        tour.head.transform.localRotation=Quaternion.Euler(22,103,0);
        for(int i=0;i<3;i++) yield return null;
        Assert(Vector3.Angle(tour.NavigationForward,Vector3.right)<1,"Looking at lateral arrows does not steer advance");
        var corridorOrigin=tour.body.transform.position;
        Assert(tour.Move(0,.05f),"Advance after turning moves the visitor");
        var corridorDelta=tour.body.transform.position-corridorOrigin;
        Assert(corridorDelta.x>.02f && Mathf.Abs(corridorDelta.z)<.01f,"Advance uses right corridor, not lateral-button gaze");
        tour.head.transform.localRotation=Quaternion.identity; tour.CenterUI(); tour.ResetPosition();
        foreach(float jointZ in new[]{8.5f,9f})
        {
            tour.body.enabled=false;
            tour.body.transform.position=new Vector3(-1,tour.Floor.Ground+.02f,jointZ);
            tour.body.enabled=true;
            tour.head.transform.localRotation=Quaternion.Euler(0,90,0); tour.CenterUI();
            Physics.SyncTransforms();
            for(int i=0;i<30;i++) tour.Move(0,.05f);
            Assert(tour.body.transform.position.x>.4f,"Joint crossed with real colliders at z="+jointZ);
            for(int i=0;i<30;i++) tour.Move(1,.05f);
            Assert(tour.body.transform.position.x<-.9f,"Joint crossed in reverse at z="+jointZ);
        }
        Assert(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,11f)),"Stair opening is not bridged");
        tour.head.transform.localRotation=Quaternion.identity; tour.ResetPosition();
        int[] expectedSlabs={27,41,45,48}, expectedRoofs={41,45,48,38};
        foreach(int number in new[]{1,2,4,3,1,4,3})
        {
            var floorButton=GameObject.Find("Piso "+number).GetComponent<VRAction>();
            Assert(floorButton!=null && floorButton.GetComponent<Collider>()!=null,"Selectable floor button "+number);
            var buttonPosition=floorButton.transform.position;
            var visitorPosition=tour.body.transform.position;
            tour.head.transform.rotation=Quaternion.LookRotation(buttonPosition-tour.head.transform.position,Vector3.up);
            yield return null; yield return null;
            Assert(Vector3.Distance(buttonPosition,floorButton.transform.position)<.001f,"Floor button stays fixed while aiming "+number);
            Assert(Vector3.Distance(visitorPosition,tour.body.transform.position)<.001f,"Aiming at floor buttons does not move visitor "+number);
            RaycastHit floorHit;
            Assert(Physics.Raycast(tour.head.transform.position,tour.head.transform.forward,out floorHit,30f,1<<5) && floorHit.collider.GetComponent<VRAction>()==floorButton,"Gaze reaches floor button "+number);
            floorButton.activate(); yield return null;
            Assert(tour.CurrentFloor==number && tour.Ready,"Floor switch completed "+number);
            Assert(tour.Floor.Walkable.Count==expectedSlabs[number-1] && tour.Floor.CeilingIds.Count==expectedRoofs[number-1],"Real floor and ceiling on "+number);
            Assert(tour.Floor.CanStand(tour.body.transform.position),"Safe spawn on "+number);
            Assert(tour.GetComponentsInChildren<ElementTag>().Length==tour.Solids.GetComponentsInChildren<ElementTag>().Length,"Only active floor colliders/IDs on "+number);
            Assert(tour.Floor.JointPassages.Count==1,"Independent central passage on "+number);
            foreach(float jointZ in new[]{8.5f,9f})
            {
                tour.body.enabled=false; tour.body.transform.position=new Vector3(-1,tour.Floor.Ground+.02f,jointZ); tour.body.enabled=true;
                tour.head.transform.localRotation=Quaternion.Euler(0,90,0); tour.CenterUI(); Physics.SyncTransforms();
                for(int i=0;i<30;i++) tour.Move(0,.05f);
                Assert(tour.body.transform.position.x>.4f,"Real joint crossing on "+number+" at "+jointZ);
                for(int i=0;i<30;i++) tour.Move(1,.05f);
                Assert(tour.body.transform.position.x<-.9f,"Reverse joint crossing on "+number+" at "+jointZ);
            }
            Assert(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,11f)),"Joint stair hole preserved on "+number);
            Assert(!tour.Floor.CanStand(new Vector3(5,tour.Floor.Ground,4)),"Other stair hole preserved on "+number);
            Assert(!tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,2f)) && !tour.Floor.CanStand(new Vector3(-.2f,tour.Floor.Ground,14f)),"Joint walls remain blocked on "+number);
            var sample= tour.Solids.GetComponentsInChildren<ElementTag>().First(t=>t.type=="column");
            tour.OpenResults(sample); tour.SetCase("COMBO"); tour.SetView(2); yield return null;
            Assert(tour.Results.LastError==null,"Results accessible on "+number);
            Assert(!tour.SelectFloor(number==4?1:4),"Modal result card prevents accidental floor change");
            tour.CloseResults(); tour.head.transform.localRotation=Quaternion.identity; tour.ResetPosition();
        }
        var tags=tour.Solids.GetComponentsInChildren<ElementTag>();
        foreach(var tag in tags.Where(t=>t.type!="loza").GroupBy(t=>t.type).Select(g=>g.First()))
        {
            tour.OpenResults(tag);
            var before=tour.body.transform.position;
            Assert(!tour.Move(0,.1f) && tour.body.transform.position==before,"Results pause locomotion");
            foreach(string loadCase in new[]{"G","Q","EX","EY","COMBO"})
            {
                tour.SetCase(loadCase);
                for(int view=0;view<5;view++)
                {
                    tour.SetView(view); tour.StepSample(1); tour.TogglePlane();
                    yield return null;
                }
            }
            tour.CloseResults(); yield return null;
        }
        tour.ResetPosition(); var origin=tour.body.transform.position;
        for(int arrow=0;arrow<4;arrow++)
        {
            tour.Move(arrow,.05f);
            Assert(tour.Floor.CanStand(tour.body.transform.position),"Movement stays on slabs");
            Assert(Mathf.Abs(tour.body.transform.position.y-origin.y)<.02f,"Movement stays at floor height");
        }
        tour.Exit();
        while(menu.Busy || SceneManager.GetActiveScene().name!=MobileLabMenu.MenuScene) yield return null;
        Assert(UnityEngine.Object.FindAnyObjectByType<VRFloorTour>()==null,"Tour unloaded on exit");
        menu.OpenVR();
        while((tour=UnityEngine.Object.FindAnyObjectByType<VRFloorTour>())==null || !tour.Ready || menu.Busy) yield return null;
        Assert(tour.Solids.GetComponentsInChildren<ElementTag>().Length==tags.Length,"Reentry loads same structural IDs");
        menu.ReturnToMenu(); while(menu.Busy) yield return null;
        Assert(errors==0,"No runtime errors: "+errors);
        Debug.Log("H1 PLAY CHECK: PASS; floors 1-4, floor buttons/repeated switches, independent joints crossed both ways, protected stairs/walls, menu/reentry, loading, selection, five cases/views, movement and modal pause.");
    }
    static void Finish(int code)
    {
        EditorApplication.update-=Tick; Application.logMessageReceived-=Log;
        EditorSettings.enterPlayModeOptionsEnabled=optionsEnabled; EditorSettings.enterPlayModeOptions=options;
        GraphicsSettings.defaultRenderPipeline=pipeline; QualitySettings.renderPipeline=quality;
        EditorApplication.Exit(code);
    }
}
