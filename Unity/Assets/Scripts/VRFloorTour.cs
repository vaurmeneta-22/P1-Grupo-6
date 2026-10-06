using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Networking;
using Google.XR.Cardboard;

public class VRFloorTour : MonoBehaviour
{
    public Camera head;
    public CharacterController body;
    public Material lineMaterial;
    public Shader geometryShader, spriteShader; // Retain dynamic geometry shaders in APK.
    public float speed=.8f;
    public VRFloorModel Floor { get; private set; }
    public GameObject Solids { get; private set; }
    public bool Ready { get; private set; }
    public Vector3 NavigationForward { get { return ui!=null?ui.NavigationForward:head.transform.forward; } }
    public readonly VRResults Results=new VRResults();
    VRWorldUI ui;
    ElementTag hover, selected;
    VRAction action;
    float dwell, cooldown;
    bool modal, focused=true, activated;
    bool collisionSettingChanged, previousCollisionSetting;
    Vector3 initial;
    float yaw, pitch;
    Transform reticle;
    Material ceilingMaterial;
    Material passageMaterial;
    EdificioData source;
    EdificioLoader floorLoader;
    class Level
    {
        public VRFloorModel floor;
        public GameObject root, solids;
    }
    readonly Dictionary<int,Level> levels=new Dictionary<int,Level>();
    public int CurrentFloor { get { return Floor!=null ? Floor.Number : 3; } }
    public string NavigationTitle { get { return "PISO "+CurrentFloor+" · "+
        (MobileLabMenu.Instance==null || !MobileLabMenu.Instance.NativeVR ? "VISTA PREVIA (sin estéreo)" : "GRUPO 6"); } }

    IEnumerator Start()
    {
#if UNITY_EDITOR
        // Preview mouse controls must not be overwritten by an absent XR device.
        var pose=head.GetComponent<UnityEngine.InputSystem.XR.TrackedPoseDriver>();
        if(pose!=null) pose.enabled=false;
#endif
        ui=new VRWorldUI(this,lineMaterial); ui.Align(head);
        ui.Notice.text="Cargando geometría y resultados OpenSees…";
        // Do not create a Sphere primitive: Android engine stripping can omit
        // SphereCollider, aborting Start before the asset-loading error handler.
        var dot=new GameObject("Mira VR",typeof(LineRenderer));
        dot.layer=2;
        reticle=dot.transform; reticle.SetParent(head.transform,false);
        reticle.localPosition=new Vector3(0,0,.8f); reticle.localScale=Vector3.one*.005f;
        var circle=dot.GetComponent<LineRenderer>(); circle.sharedMaterial=lineMaterial;
        circle.useWorldSpace=false; circle.loop=true; circle.positionCount=24;
        circle.startColor=circle.endColor=Color.white; circle.widthMultiplier=.0007f;
        circle.sortingOrder=30;
        for(int i=0;i<circle.positionCount;i++)
        {
            float angle=i*Mathf.PI*2/circle.positionCount;
            circle.SetPosition(i,new Vector3(Mathf.Cos(angle)*.5f,Mathf.Sin(angle)*.5f,0));
        }
        string model=null, map=null, failure=null;
        ui.Notice.text="1/3 · Leyendo el modelo del edificio…";
        yield return ReadAsset("Edificio.json",s=>model=s,e=>failure=e);
        if(failure==null)
        {
            ui.Notice.text="2/3 · Leyendo los resultados OpenSees…";
            yield return ReadAsset("analysis_map.json",s=>map=s,e=>failure=e);
        }
        if(failure!=null) { ShowLoadError(failure); yield break; }
        ui.Notice.text="3/3 · Construyendo el recorrido del piso 3…";
        yield return null;
        try
        {
            string path=Path.Combine(Application.temporaryCachePath,"vr_analysis_map.json");
            File.WriteAllText(path,map);
            if(!AnalysisMap.Load(path)) throw new InvalidOperationException(AnalysisMap.LoadError);
            BuildFloor(JsonUtility.FromJson<EdificioData>(model));
            initial=FindSpawn();
            body.enabled=false; body.transform.position=initial; body.enabled=true;
            ui.Align(head); Ready=true;
            ui.Notice.text="Gira hacia el pasillo y baja la mirada a las flechas.\nMira una flecha 0,7 s para moverte; deja de mirarla para parar.";
            ui.Heading.text=NavigationTitle;
            Debug.Log("VR FLOOR READY: elements="+Solids.GetComponentsInChildren<ElementTag>().Length+"; slabs="+Floor.Walkable.Count+"; ground_m="+Floor.Ground+"; spawn="+initial);
        }
        catch(Exception ex) { ShowLoadError(ex.Message); Debug.LogException(ex); }
    }

    void ShowLoadError(string text)
    {
        Ready=false;
        ui.Notice.text="No se pudo cargar el recorrido: "+text+"\nPulsa Inicio para volver e intentar nuevamente.";
        Debug.LogError("VR LOAD FAILED: "+text);
    }

    static IEnumerator ReadAsset(string name,Action<string> success,Action<string> failure)
    {
        // Join as a URI for Android's jar:file://...!/assets, not a Windows path.
        string path=Application.streamingAssetsPath.TrimEnd('/','\\')+"/"+name;
        if(path.Contains("://"))
        {
            UnityWebRequest request=null;
            try { request=UnityWebRequest.Get(path); request.timeout=20; }
            catch(Exception ex) { failure("No se pudo abrir "+name+": "+ex.Message); }
            if(request==null) yield break;
            using(request)
            {
                UnityWebRequestAsyncOperation operation=null;
                try { operation=request.SendWebRequest(); }
                catch(Exception ex) { failure("No se pudo leer "+name+": "+ex.Message); }
                if(operation==null) yield break;
                yield return operation;
                if(request.result==UnityWebRequest.Result.Success) success(request.downloadHandler.text);
                else failure("No se pudo cargar "+name+": "+request.error);
            }
        }
        else
        {
            try { success(File.ReadAllText(path)); }
            catch(Exception ex) { failure("No se pudo cargar "+name+": "+ex.Message); }
        }
    }

    public void BuildFloor(EdificioData data, int number=3)
    {
        var nextFloor=new VRFloorModel(data,number);
        source=data;
        foreach(var level in levels.Values) level.root.SetActive(false);
        Level cached;
        if(levels.TryGetValue(number,out cached))
        {
            Floor=cached.floor; Solids=cached.solids; cached.root.SetActive(true);
            Physics.SyncTransforms(); return;
        }
        Floor=nextFloor;
        if(floorLoader==null)
        {
            floorLoader=gameObject.AddComponent<EdificioLoader>(); floorLoader.enabled=false;
            floorLoader.lozaColor=new Color(.63f,.68f,.71f,1);
        }
        var levelRoot=new GameObject("Recorrido "+Floor.Name);
        levelRoot.transform.SetParent(transform,false);
        var loader=floorLoader;
        Solids=loader.BuildSolids(Floor.Data,levelRoot.transform);
        levels.Add(number,new Level { floor=Floor,root=levelRoot,solids=Solids });
        Physics.SyncTransforms();
        var jointObstacles=new List<Bounds>();
        foreach(var collider in Solids.GetComponentsInChildren<Collider>()) jointObstacles.Add(collider.bounds);
        Floor.RestrictJointPassagesToClearSpace(jointObstacles);
        if(passageMaterial==null) passageMaterial=new Material(loader.lozaMat);
        passageMaterial.color=new Color(.32f,.36f,.38f,1);
        if(passageMaterial.HasProperty("_BaseColor")) passageMaterial.SetColor("_BaseColor",passageMaterial.color);
        var passages=new GameObject("Pasos VR sobre junta · sin elementos estructurales");
        passages.transform.SetParent(levelRoot.transform,false);
        foreach(var rect in Floor.JointPassages)
        {
            var cover=GameObject.CreatePrimitive(PrimitiveType.Cube);
            cover.name="Cubrejunta VR";
            cover.transform.SetParent(passages.transform,false);
            cover.transform.position=new Vector3(rect.center.x,Floor.Ground-.015f,rect.center.y);
            cover.transform.localScale=new Vector3(rect.width,.03f,rect.height);
            cover.GetComponent<Renderer>().sharedMaterial=passageMaterial;
            // No ElementTag: this cover is solely a navigation aid.
        }
        if(ceilingMaterial==null) ceilingMaterial=new Material(geometryShader);
        ceilingMaterial.color=new Color(.79f,.80f,.76f,1);
        if(ceilingMaterial.HasProperty("_BaseColor")) ceilingMaterial.SetColor("_BaseColor",ceilingMaterial.color);
        if(ceilingMaterial.HasProperty("_Surface")) ceilingMaterial.SetFloat("_Surface",0);
        if(ceilingMaterial.HasProperty("_ZWrite")) ceilingMaterial.SetFloat("_ZWrite",1);
        if(ceilingMaterial.HasProperty("_Cull")) ceilingMaterial.SetFloat("_Cull",0);
        ceilingMaterial.renderQueue=2000;
        var ids=new HashSet<int>();
        foreach(var tag in Solids.GetComponentsInChildren<ElementTag>())
        {
            if(!ids.Add(tag.elementId)) throw new InvalidOperationException("Elemento duplicado "+tag.elementId);
            if(AnalysisMap.Element(tag.elementId)==null) throw new InvalidOperationException("ID no presente en el mapa: "+tag.elementId);
            if(Floor.CeilingIds.Contains(tag.elementId))
            {
                var slab=Floor.Data.elements.Find(e=>e.id==tag.elementId);
                var size=tag.transform.localScale;
                size.y=Mathf.Max(.045f,slab.t*.01f); // Actual cm thickness, visual only.
                tag.transform.localScale=size;
                tag.GetComponent<Renderer>().sharedMaterial=ceilingMaterial;
                tag.gameObject.name="TECHO_"+tag.elementId;
            }
        }
        // UI is interactive but never blocks the player's collision capsule.
        if(Application.isPlaying && !collisionSettingChanged)
        {
            previousCollisionSetting=Physics.GetIgnoreLayerCollision(2,5);
            Physics.IgnoreLayerCollision(2,5,true); collisionSettingChanged=true;
        }
        Physics.SyncTransforms();
    }

    public bool SelectFloor(int number)
    {
        if(!Ready || modal || source==null || number<1 || number>4) return false;
        if(number==CurrentFloor) return true;
        int previous=CurrentFloor;
        Vector3 previousPosition=body.transform.position;
        try
        {
            if(action!=null) action.Hover(false);
            if(hover!=null) Highlight(hover,false);
            action=null; hover=null; selected=null; Results.Selected=null;
            activated=false; dwell=0; cooldown=1;
            body.enabled=false;
            BuildFloor(source,number);
            initial=FindSpawn(); body.transform.position=initial; body.enabled=true;
            ui.ShowNavigation(); ui.Align(head);
            ui.Notice.text="Estás en el piso "+number+". Mira las flechas para recorrerlo.\nEl paso sobre la junta está limitado a las zonas libres.";
            return true;
        }
        catch(Exception ex)
        {
            BuildFloor(source,previous);
            initial=FindSpawn(); body.transform.position=previousPosition; body.enabled=true;
            ui.ShowNavigation(); ui.Align(head);
            ui.Notice.text="No se pudo abrir el piso "+number+": "+ex.Message;
            Debug.LogException(ex); return false;
        }
    }

    public Vector3 FindSpawn()
    {
        var rectangles=new List<Rect>(Floor.Walkable);
        rectangles.Sort((a,b)=>(b.width*b.height).CompareTo(a.width*a.height));
        foreach(var rect in rectangles)
        {
            var centre=new Vector3(rect.center.x,Floor.Ground+.02f,rect.center.y);
            if(SafeSpawn(centre)) return centre;
            for(float x=rect.xMin+.6f;x<rect.xMax-.6f;x+=1f)
                for(float z=rect.yMin+.6f;z<rect.yMax-.6f;z+=1f)
                {
                    var candidate=new Vector3(x,Floor.Ground+.02f,z);
                    if(SafeSpawn(candidate)) return candidate;
                }
        }
        throw new InvalidOperationException("No hay un punto inicial libre de columnas o muros.");
    }

    bool SafeSpawn(Vector3 point)
    {
        return Floor.CanStand(point) && !Physics.CheckCapsule(point+Vector3.up*.26f,point+Vector3.up*1.42f,
            VRFloorModel.BodyRadius,1,QueryTriggerInteraction.Ignore);
    }

    void Update()
    {
        // Keep Inicio usable during loading and after a loading failure.
        if(ui==null || reticle==null || !focused || (MobileLabMenu.Instance!=null && MobileLabMenu.Instance.Busy)) return;
        if(Keyboard.current!=null && Keyboard.current.escapeKey.wasPressedThisFrame) { Exit(); return; }
        PreviewInput();
        if(cooldown>0) cooldown-=Time.unscaledDeltaTime;
        bool native=MobileLabMenu.Instance!=null && MobileLabMenu.Instance.NativeVR;
        bool trigger=native && Api.IsTriggerPressed;
        if(native && Api.IsTriggerHeldPressed) { StartCoroutine(RecenterHead()); return; }
        Ray ray=new Ray(head.transform.position,head.transform.forward);
        // In editor/mono preview a left click directly selects what it points at.
        bool click=!native && Mouse.current!=null && Mouse.current.leftButton.wasPressedThisFrame;
        if(click) ray=head.ScreenPointToRay(Mouse.current.position.ReadValue());
        RaycastHit controlHit;
        bool controlsFocused=Physics.Raycast(ray,out controlHit,30f,1<<5,QueryTriggerInteraction.Ignore)
            && controlHit.collider.GetComponent<VRAction>()!=null;
        ui.FollowNavigation(head,Time.unscaledDeltaTime,controlsFocused);
        Physics.SyncTransforms();
        VRAction next=null; ElementTag nextTag=null;
        RaycastHit hit;
        // Overlay controls remain usable even when a structural wall is close.
        if(Physics.Raycast(ray,out hit,30f,1<<5,QueryTriggerInteraction.Ignore))
            next=hit.collider.GetComponent<VRAction>();
        if(next==null && Ready && !modal && Physics.Raycast(ray,out hit,30f,1,QueryTriggerInteraction.Ignore))
        {
            var tag=hit.collider.GetComponent<ElementTag>();
            if(tag!=null && tag.type!="loza") nextTag=tag;
        }
        if(next!=action || nextTag!=hover)
        {
            if(action!=null) action.Hover(false);
            if(hover!=null && hover!=selected) Highlight(hover,false);
            action=next; hover=nextTag; dwell=0; activated=false;
            if(action!=null) action.Hover(true);
            if(hover!=null) Highlight(hover,true);
        }
        dwell+=Time.unscaledDeltaTime;
        ui.SetProgress((action!=null || hover!=null)?dwell:0);
        if(action!=null)
        {
            if(action.movement>=0 && !modal)
            {
                if(trigger||click) Move(action.movement,.35f);
                else if(dwell>=.7f) Move(action.movement,speed*Time.deltaTime);
            }
            else if((trigger||click||(!activated && dwell>=1.1f)) && cooldown<=0)
            {
                var activate=action.activate;
                dwell=0; cooldown=.7f; activated=true;
                if(activate!=null) activate();
            }
        }
        else if(hover!=null && cooldown<=0 && (trigger||click||dwell>=1f)) OpenResults(hover);
        reticle.localScale=Vector3.one*((action!=null || hover!=null)? .009f:.005f);
    }

    void PreviewInput()
    {
#if UNITY_EDITOR
        var mouse=Mouse.current;
        if(mouse!=null && mouse.rightButton.isPressed)
        {
            Vector2 delta=mouse.delta.ReadValue(); yaw+=delta.x*.12f; pitch=Mathf.Clamp(pitch-delta.y*.12f,-75,75);
            head.transform.localRotation=Quaternion.Euler(pitch,yaw,0);
        }
        if(Keyboard.current!=null && !modal)
        {
            var k=Keyboard.current;
            if(k.wKey.isPressed || k.upArrowKey.isPressed) Move(0,speed*Time.deltaTime);
            if(k.sKey.isPressed || k.downArrowKey.isPressed) Move(1,speed*Time.deltaTime);
            if(k.aKey.isPressed || k.leftArrowKey.isPressed) Move(2,speed*Time.deltaTime);
            if(k.dKey.isPressed || k.rightArrowKey.isPressed) Move(3,speed*Time.deltaTime);
        }
#endif
    }

    public bool Move(int arrow,float distance)
    {
        if(Floor==null || body==null || modal) return false;
        var before=body.transform.position;
        var delta=VRFloorModel.Direction(NavigationForward,arrow)*Mathf.Min(distance,.15f);
        if(!Floor.CanStand(before+delta)) return false;
        body.Move(delta);
        var after=body.transform.position;
        if(!Floor.CanStand(after))
        { body.enabled=false; body.transform.position=before; body.enabled=true; return false; }
        if(ui!=null) ui.Translate(after-before);
        return (after-before).sqrMagnitude>1e-8f;
    }

    public void OpenResults(ElementTag tag)
    {
        if(tag==null || !Ready) return;
        selected=tag; modal=true; Results.Selected=tag; Results.Sample=0; Results.View=0;
        ui.ShowResults(tag); ui.Align(head); Results.Render(ui); cooldown=.8f; dwell=0; action=null; hover=null;
    }
    public void SetCase(string value) { Results.Case=value; Results.Sample=0; Results.Render(ui); }
    public void SetView(int value) { Results.View=value; Results.Sample=0; Results.Render(ui); }
    public void TogglePlane() { Results.Plane=1-Results.Plane; Results.Sample=0; Results.Render(ui); }
    public void StepSample(int delta) { Results.Sample=Math.Max(0,Results.Sample+delta); Results.Render(ui); }
    public void CloseResults()
    {
        if(selected!=null) Highlight(selected,false); selected=null; modal=false; action=null; hover=null; dwell=0; cooldown=1;
        ui.ShowNavigation(); ui.Align(head);
    }
    public void CenterUI() { if(ui!=null) ui.Align(head); }
    IEnumerator RecenterHead()
    {
        MobileLabMenu.Instance.Recenter(); yield return null; yield return null; CenterUI(); dwell=0;
    }
    public void ResetPosition()
    {
        if(!Ready) return;
        body.enabled=false; body.transform.position=initial; body.enabled=true; CenterUI(); dwell=0;
    }
    public void Exit()
    {
        if(MobileLabMenu.Instance!=null) MobileLabMenu.Instance.ReturnToMenu();
        else UnityEngine.SceneManagement.SceneManager.LoadScene(MobileLabMenu.MenuScene);
    }
    static void Highlight(ElementTag tag,bool on)
    {
        var renderer=tag.GetComponent<Renderer>(); if(renderer==null) return;
        if(!on) { renderer.SetPropertyBlock(null); return; }
        var properties=new MaterialPropertyBlock(); properties.SetColor("_BaseColor",new Color(1,.80f,.10f)); properties.SetColor("_Color",new Color(1,.80f,.10f));
        renderer.SetPropertyBlock(properties);
    }
    void OnApplicationFocus(bool value) { focused=value; dwell=0; }
    void OnApplicationPause(bool value) { focused=!value; dwell=0; }
    void OnDestroy()
    {
        if(collisionSettingChanged) Physics.IgnoreLayerCollision(2,5,previousCollisionSetting);
        if(ui!=null) ui.Dispose();
        if(hover!=null) Highlight(hover,false);
        if(selected!=null) Highlight(selected,false);
        if(ceilingMaterial!=null)
        {
            if(Application.isPlaying) Destroy(ceilingMaterial);
            else DestroyImmediate(ceilingMaterial);
        }
        if(passageMaterial!=null)
        {
            if(Application.isPlaying) Destroy(passageMaterial);
            else DestroyImmediate(passageMaterial);
        }
    }
}
