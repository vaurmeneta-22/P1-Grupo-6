using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

// World-space canvas: both eyes see the same UI at a real depth. The board is
// follows horizontal viewing direction; looking down freezes it for selection.
public class VRWorldUI
{
    public GameObject Root { get; private set; }
    public Transform Chart { get; private set; }
    public Text Heading, Detail, Readout, Notice;
    public Image Progress;
    public readonly List<VRAction> Arrows = new List<VRAction>();
    public readonly List<VRAction> FloorButtons = new List<VRAction>();
    public bool IsNavigation { get; private set; } = true;
    public Vector3 NavigationForward { get; private set; } = Vector3.forward;
    Font font;
    Transform board;
    Transform graph;
    Material lineMaterial;
    VRFloorTour tour;
    bool selectingControls;
    const float Scale = .002f;

    static void Release(GameObject go)
    {
        if(go==null) return;
        go.SetActive(false);
        if(Application.isPlaying) UnityEngine.Object.Destroy(go);
        else UnityEngine.Object.DestroyImmediate(go);
    }

    public VRWorldUI(VRFloorTour owner, Material material)
    {
        tour = owner; lineMaterial = material;
        font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        Root = new GameObject("Panel VR",typeof(RectTransform),typeof(Canvas));
        var canvas = Root.GetComponent<Canvas>(); canvas.renderMode=RenderMode.WorldSpace;
        canvas.sortingOrder=20;
        Root.GetComponent<RectTransform>().sizeDelta=new Vector2(1000,780);
        Root.transform.localScale=Vector3.one*Scale;
        board=Root.transform;
        Heading = Label(board,tour.NavigationTitle,new Vector2(0,210),new Vector2(940,46),27,FontStyle.Bold);
        Notice = Label(board,"Mira un elemento · mantén la mirada o pulsa Cardboard",new Vector2(0,167),new Vector2(930,50),20);
        MakeNavigation();
    }

    public void Align(Camera camera)
    {
        var forward=Vector3.ProjectOnPlane(camera.transform.forward,Vector3.up).normalized;
        if (forward.sqrMagnitude<.01f) forward=NavigationForward;
        NavigationForward=forward;
        selectingControls=false;
        Root.transform.position=camera.transform.position+forward*1.7f-Vector3.up*(IsNavigation?.35f:.08f);
        Root.transform.rotation=Quaternion.LookRotation(forward,Vector3.up);
    }

    public void FollowNavigation(Camera camera,float dt,bool controlsFocused)
    {
        if(!IsNavigation) return; // Keep diagrams stable while they are read.
        // The arrows sit below eye level. Looking down locks the last corridor
        // heading, so looking sideways at a lateral arrow cannot steer advance.
        bool lookingDown=camera.transform.forward.y < -Mathf.Sin(12f*Mathf.Deg2Rad);
        var horizontal=Vector3.ProjectOnPlane(camera.transform.forward,Vector3.up);
        // A large turn retrieves arrows while walking. Looking farther down
        // at the floor selector keeps the board fixed even between buttons.
        bool largeTurn=horizontal.sqrMagnitude>.01f && Vector3.Angle(horizontal,NavigationForward)>35f;
        bool lookingAtFloorRow=camera.transform.forward.y < -Mathf.Sin(25f*Mathf.Deg2Rad);
        bool selecting=controlsFocused || (lookingDown && (!largeTurn || lookingAtFloorRow));
        if(selecting && !selectingControls && !controlsFocused)
            Root.transform.rotation=Quaternion.LookRotation(NavigationForward,Vector3.up);
        if(!selecting)
        {
            var forward=horizontal;
            if(forward.sqrMagnitude>.01f)
            {
                NavigationForward=forward.normalized;
                var target=Quaternion.LookRotation(NavigationForward,Vector3.up);
                if(Quaternion.Angle(Root.transform.rotation,target)>3f)
                    Root.transform.rotation=Quaternion.RotateTowards(Root.transform.rotation,target,240f*Mathf.Min(dt,.1f));
            }
        }
        selectingControls=selecting;
        Root.transform.position=camera.transform.position+Root.transform.forward*1.7f-Vector3.up*.35f;
    }

    public void Translate(Vector3 delta) { Root.transform.position+=delta; }

    Text Label(Transform parent,string text,Vector2 p,Vector2 size,int fontSize=20,FontStyle style=FontStyle.Normal)
    {
        var go=new GameObject("Texto",typeof(RectTransform),typeof(Text)); go.transform.SetParent(parent,false);
        var rt=go.GetComponent<RectTransform>(); rt.sizeDelta=size; rt.anchoredPosition=p;
        var label=go.GetComponent<Text>(); label.font=font; label.text=text; label.color=new Color(.90f,.95f,1);
        label.material=lineMaterial;
        label.fontSize=fontSize; label.fontStyle=style; label.alignment=TextAnchor.MiddleCenter;
        label.horizontalOverflow=HorizontalWrapMode.Wrap; label.verticalOverflow=VerticalWrapMode.Overflow;
        label.raycastTarget=false;
        return label;
    }

    public VRAction Button(string text,Vector2 p,Vector2 size,Action activate,int movement=-1)
    {
        var go=new GameObject(text,typeof(RectTransform),typeof(Image),typeof(BoxCollider),typeof(VRAction));
        go.layer=5; go.transform.SetParent(board,false);
        var rt=go.GetComponent<RectTransform>(); rt.sizeDelta=size; rt.anchoredPosition=p;
        go.GetComponent<BoxCollider>().size=new Vector3(size.x,size.y,12);
        var action=go.GetComponent<VRAction>(); action.background=go.GetComponent<Image>(); action.background.material=lineMaterial;
        action.activate=activate; action.movement=movement; action.Hover(false);
        Label(go.transform,text,Vector2.zero,size-new Vector2(8,4),20,FontStyle.Bold);
        return action;
    }

    void MakeNavigation()
    {
        Arrows.Clear();
        FloorButtons.Clear();
        for(int floor=1;floor<=4;floor++)
        {
            int number=floor;
            var button=Button("Piso "+number+(number==tour.CurrentFloor?" · actual":""),
                new Vector2(-270+(floor-1)*180,-267),new Vector2(168,48),()=>tour.SelectFloor(number));
            FloorButtons.Add(button);
        }
        Arrows.Add(Button("↑ Avanzar",new Vector2(0,-130),new Vector2(180,58),null,0));
        Arrows.Add(Button("↓ Retroceder",new Vector2(0,-198),new Vector2(180,58),null,1));
        Arrows.Add(Button("← Izquierda",new Vector2(-198,-165),new Vector2(185,58),null,2));
        Arrows.Add(Button("Derecha →",new Vector2(198,-165),new Vector2(185,58),null,3));
        Button("Inicio",new Vector2(-365,-334),new Vector2(125,46),tour.Exit);
        Button("Centrar panel",new Vector2(0,-334),new Vector2(200,46),tour.CenterUI);
        Button("Volver al inicio",new Vector2(332,-334),new Vector2(185,46),tour.ResetPosition);
        var progressGo=new GameObject("Progreso",typeof(RectTransform),typeof(Image)); progressGo.transform.SetParent(board,false);
        var rt=progressGo.GetComponent<RectTransform>(); rt.anchoredPosition=new Vector2(0,123); rt.sizeDelta=new Vector2(130,5);
        Progress=progressGo.GetComponent<Image>(); Progress.color=new Color(.05f,.88f,.94f); Progress.rectTransform.sizeDelta=new Vector2(0,5);
        Progress.material=lineMaterial;
    }

    void ClearContent()
    {
        for(int i=board.childCount-1;i>=0;i--) Release(board.GetChild(i).gameObject);
        Chart=null; Detail=null; Readout=null; Arrows.Clear(); FloorButtons.Clear();
    }

    public void ShowNavigation()
    {
        ClearContent();
        IsNavigation=true;
        Heading=Label(board,tour.NavigationTitle,new Vector2(0,210),new Vector2(940,46),27,FontStyle.Bold);
        Notice=Label(board,"Gira hacia el pasillo y baja la mirada a las flechas",new Vector2(0,167),new Vector2(930,50),20);
        MakeNavigation();
    }

    public void ShowResults(ElementTag tag)
    {
        ClearContent();
        IsNavigation=false;
        var backdrop=new GameObject("Ficha",typeof(RectTransform),typeof(Image)); backdrop.transform.SetParent(board,false);
        backdrop.GetComponent<RectTransform>().sizeDelta=new Vector2(970,775);
        backdrop.GetComponent<Image>().color=new Color(.035f,.065f,.10f,.97f);
        backdrop.GetComponent<Image>().material=lineMaterial;
        Heading=Label(board,VRResults.TypeName(tag.type)+" "+tag.elementId+" · "+tag.section,new Vector2(0,347),new Vector2(940,50),26,FontStyle.Bold);
        string[] cases={"G","Q","EX","EY","COMBO"};
        for(int i=0;i<cases.Length;i++)
        {
            string value=cases[i]; Button(value,new Vector2(-360+i*180,286),new Vector2(168,48),()=>tour.SetCase(value));
        }
        string[] views={"Axial N","Corte V","Momento M","P-M","M-curv."};
        for(int i=0;i<views.Length;i++)
        {
            int value=i; Button(views[i],new Vector2(-360+i*180,225),new Vector2(168,48),()=>tour.SetView(value));
        }
        Button("Plano x-z / x-y",new Vector2(-285,164),new Vector2(280,42),tour.TogglePlane);
        Button("Recorrer piso",new Vector2(200,164),new Vector2(280,42),tour.CloseResults);
        Detail=Label(board,"",new Vector2(0,111),new Vector2(920,52),20);
        Chart=new GameObject("Grafico",typeof(RectTransform)).transform; Chart.SetParent(board,false);
        Readout=Label(board,"",new Vector2(0,-233),new Vector2(920,70),20);
        Notice=Label(board,"",new Vector2(0,-308),new Vector2(920,56),17);
        Button("◀ Muestra",new Vector2(-245,-361),new Vector2(220,42),()=>tour.StepSample(-1));
        Button("Muestra ▶",new Vector2(0,-361),new Vector2(220,42),()=>tour.StepSample(1));
        Button("Inicio",new Vector2(293,-361),new Vector2(175,42),tour.Exit);
        Progress=null;
    }

    public void BeginGraph(double xmin,double xmax,double ymin,double ymax,string xUnit,string yUnit,float tickSign=1)
    {
        if(graph!=null) Release(graph.gameObject);
        graph=new GameObject("Curvas").transform; graph.SetParent(Chart,false);
        // The graph's positive local Y is up. Moment alone passes a negative sign.
        for(int i=0;i<=4;i++)
        {
            float x=-360+i*180, y=-163+i*58;
            Line(new[]{new Vector3(x,-163, -3),new Vector3(x,69,-3)},new Color(.22f,.30f,.36f),1.3f);
            Line(new[]{new Vector3(-360,y,-3),new Vector3(360,y,-3)},new Color(.22f,.30f,.36f),1.3f);
            Label(graph,VRResults.F(xmin+(xmax-xmin)*i/4,2),new Vector2(x,-181),new Vector2(160,26),15);
            Label(graph,VRResults.F((ymin+(ymax-ymin)*i/4)*tickSign,1),new Vector2(-410,y),new Vector2(92,24),15);
        }
        Label(graph,xUnit,new Vector2(260,-201),new Vector2(200,25),16);
        Label(graph,yUnit,new Vector2(-338,88),new Vector2(200,25),16);
    }

    Vector3 Point(double x,double y,double xmin,double xmax,double ymin,double ymax)
    { return new Vector3(-360+720*(float)((x-xmin)/(xmax-xmin)),-163+232*(float)((y-ymin)/(ymax-ymin)),-5); }

    public void Curve(double[] x,double[] y,double xmin,double xmax,double ymin,double ymax,Color color,float sign=1)
    {
        var points=new Vector3[x.Length];
        for(int i=0;i<x.Length;i++) points[i]=Point(x[i],y[i]*sign,xmin,xmax,ymin,ymax);
        Line(points,color,2.4f);
    }

    public void Mark(double x,double y,double xmin,double xmax,double ymin,double ymax,Color color)
    {
        var p=Point(x,y,xmin,xmax,ymin,ymax);
        Line(new[]{p+Vector3.left*6,p+Vector3.right*6},color,3f);
        Line(new[]{p+Vector3.down*6,p+Vector3.up*6},color,3f);
    }

    public void Zero(double xmin,double xmax,double ymin,double ymax)
    {
        if(ymin<=0 && ymax>=0) Line(new[]{Point(xmin,0,xmin,xmax,ymin,ymax),Point(xmax,0,xmin,xmax,ymin,ymax)},Color.white,1.6f);
        if(xmin<0 && xmax>0) Line(new[]{Point(0,ymin,xmin,xmax,ymin,ymax),Point(0,ymax,xmin,xmax,ymin,ymax)},Color.white,1.6f);
    }

    void Line(Vector3[] p,Color color,float width)
    {
        var go=new GameObject("Linea",typeof(LineRenderer)); go.transform.SetParent(graph,false);
        var lr=go.GetComponent<LineRenderer>(); lr.sharedMaterial=lineMaterial; lr.useWorldSpace=false;
        lr.positionCount=p.Length; lr.SetPositions(p); lr.startColor=lr.endColor=color;
        // Positions inherit the canvas scale; LineRenderer widths are world units.
        lr.widthMultiplier=width*Scale; lr.numCapVertices=2; lr.sortingOrder=21;
    }

    public void SetProgress(float value) { if(Progress!=null) Progress.rectTransform.sizeDelta=new Vector2(130*Mathf.Clamp01(value),5); }
    public void Dispose() { Release(Root); }
}
