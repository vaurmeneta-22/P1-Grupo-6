using UnityEngine;
using System.IO;
using System.Collections.Generic;

public class EdificioLoader : MonoBehaviour
{
    public string jsonFileName = "Edificio.json";
    public float scale = 0.01f;

    public Material columnMat;
    public Material beamXMat;
    public Material beamYMat;
    public Material nodeMat;
    public Material supportMat;
    public Material wallMat;
    public Material lozaMat;
    public Material steelMat;

    [Header("Colores (como el visor 3D)")]
    public Color columnColor = new Color(0.906f, 0.298f, 0.235f);   // #e74c3c
    public Color beamXColor = new Color(0.204f, 0.596f, 0.859f);    // #3498db
    public Color beamYColor = new Color(0.180f, 0.800f, 0.443f);    // #2ecc71
    public Color nodeColor = new Color(0.102f, 0.737f, 0.612f);    // #1abc9c
    public Color supportColor = new Color(0.608f, 0.349f, 0.714f);  // #9b59b6
    public Color wallColor = new Color(0.608f, 0.349f, 0.714f);     // #9b59b6
    public Color lozaColor = new Color(0.902f, 0.404f, 0.133f);     // #e67e22
    public Color steelColor = new Color(0.945f, 0.769f, 0.059f);    // #f1c40f

    [Header("Modo hormigon")]
    public KeyCode hormigonKey = KeyCode.H;
    public Color hormigonColor = new Color(0.62f, 0.62f, 0.63f);        // concreto claro
    public Color zapataColor = new Color(0.36f, 0.37f, 0.39f);          // concreto mas oscuro

    [Header("Teclas")]
    public KeyCode columnsKey = KeyCode.C;
    public KeyCode beamsXKey = KeyCode.X;
    public KeyCode beamsYKey = KeyCode.Y;
    public KeyCode wallsKey = KeyCode.W;
    public KeyCode lozasKey = KeyCode.L;
    public KeyCode supportsKey = KeyCode.P;
    public KeyCode nodesKey = KeyCode.N;
    public KeyCode axesKey = KeyCode.E;
    public KeyCode diaphKey = KeyCode.D;
    public KeyCode steelKey = KeyCode.G;

    [Header("Diafragmas (como el visor HTML)")]
    public Color diaphFillColor = new Color(0f, 1f, 1f);            // cian casi transparente
    public Color diaphEdgeColor = new Color(0f, 0.898f, 1f);        // #00e5ff
    public float diaphFillOpacity = 0.05f;
    public float diaphEdgeOpacity = 0.6f;

    private GameObject elementsGroup;
    private GameObject columnGroup;
    private GameObject beamXGroup;
    private GameObject beamYGroup;
    private GameObject wallGroup;
    private GameObject lozaGroup;
    private GameObject steelGroup;
    private GameObject supportGroup;
    private GameObject axesGroup;
    private GameObject nodeGroup;
    private GameObject diaphGroup;
    private Material diaphFillMat;
    private Material diaphEdgeMat;
    private HashSet<int> supportIds = new HashSet<int>();
    private List<Transform> labels = new List<Transform>();
    private Material labelBgMat;
    private Material[] axisMats;
    private Material hormigonMat;
    private Material zapataMat;
    private bool hormigonMode = false;
    private Dictionary<Renderer, Material> originalMaterials = new Dictionary<Renderer, Material>();
    private float labelScale = 0.04f;
    private float axisfontSize = 48f;
    private TributaryInspector inspector;

    // Componentes de interaccion creados en runtime (para el HUD por capas,
    // el boton de modo y el pintado de reacciones).
    public AnalysisMode analysisMode;
    public DataPanel dataPanel;
    public VerifPanel verifPanel;
    public int NodeCount;
    public int ElementCount;

    // Grupo raiz de los solidos (para el hover/doble-clic del PickHighlight).
    public GameObject ElementsGroup { get { return elementsGroup; } }

    void Start()
    {
        QualitySettings.antiAliasing = 4;
        Application.targetFrameRate = 60;

        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        string json = File.ReadAllText(path);
        EdificioData data = JsonUtility.FromJson<EdificioData>(json);

        // Resultados del analisis (mismos datos que ANALYSIS_MAP del visor HTML).
        LoadAnalysisMap();

        NodeCount = data.nodes != null ? data.nodes.Count : 0;
        ElementCount = data.elements != null ? data.elements.Count : 0;

        CreateMaterials();
        BuildSupportSet(data);

        elementsGroup = new GameObject("Elementos");
        columnGroup = new GameObject("Columnas");
        beamXGroup = new GameObject("VigasX");
        beamYGroup = new GameObject("VigasY");
        wallGroup = new GameObject("Muros");
        lozaGroup = new GameObject("Lozas");
        steelGroup = new GameObject("Metalicas");
        supportGroup = new GameObject("Apoyos");
        axesGroup = new GameObject("Ejes");
        nodeGroup = new GameObject("Nodos");
        diaphGroup = new GameObject("Diafragmas");
        axesGroup.SetActive(false);

        columnGroup.transform.parent = elementsGroup.transform;
        beamXGroup.transform.parent = elementsGroup.transform;
        beamYGroup.transform.parent = elementsGroup.transform;
        wallGroup.transform.parent = elementsGroup.transform;
        lozaGroup.transform.parent = elementsGroup.transform;
        steelGroup.transform.parent = elementsGroup.transform;
        supportGroup.transform.parent = elementsGroup.transform;

        foreach (NodeData node in data.nodes)
        {
            CreateNode(node, nodeGroup);
        }

        foreach (ElementData elem in data.elements)
        {
            CreateElement(elem, data.nodes);
        }

        CreateDiaphragms();

        TrySetupInspector();
        SetupAnalysisMode();
        SetupDataPanel();
        SetupVerifPanel();
        SetupPickHighlight();
        SetupViewerHud();

        DisableShadows();

        Camera cam = Camera.main;
        if (cam != null)
        {
            cam.farClipPlane = 500f;
            Vector3 center = ComputeModelCenter(data);
            CameraController ctrl = cam.GetComponent<CameraController>();
            if (ctrl != null)
            {
                // La camara orbital apunta al centro real del modelo (determinista,
                // independiente del orden de ejecucion de los Start()).
                ctrl.TargetModelCenter(center);
            }
            else
            {
                CenterCameraOnModel(cam, center);
            }
        }
    }

    // Carga los resultados del analisis desde StreamingAssets (analysis_map.json),
    // indispensable para el inspector (fuerzas por caso) y los modos deformada/esfuerzos.
    void LoadAnalysisMap()
    {
        string amPath = Path.Combine(Application.streamingAssetsPath, "analysis_map.json");
        if (AnalysisMap.Load(amPath))
        {
            Debug.Log("AnalysisMap cargado: " + AnalysisMap.ElementsByTag.Count +
                      " elementos, fuerzas en " + string.Join(",", AnalysisMap.Forces.Keys));
        }
        else
        {
            Debug.LogWarning("AnalysisMap no disponible: " + AnalysisMap.LoadError);
        }
    }

    // Nombre del piso por elevacion estructural (metros), igual que el visor HTML.
    static string NombrePisoLocal(float yM)
    {
        if (yM < 3.56f) return "Subterraneo";
        if (yM < 7.12f) return "Piso 1";
        if (yM < 10.68f) return "Piso 2";
        if (yM < 14.24f) return "Piso 3";
        if (yM < 17.8f) return "Piso 4";
        return "Techo";
    }

    // Centroide de todos los nodos (mundo Unity, con el mismo espejo de NodeToPos).
    public Vector3 ComputeModelCenter(EdificioData data)
    {
        if (data.nodes == null || data.nodes.Count == 0) return Vector3.zero;
        Vector3 sum = Vector3.zero;
        foreach (NodeData n in data.nodes) sum += NodeToPos(n);
        return sum / data.nodes.Count;
    }

    // Ubica la camara para encuadrar el modelo alrededor de su centro (sin CameraController).
    void CenterCameraOnModel(Camera cam, Vector3 center)
    {
        Vector3 camPos = center + new Vector3(-40f, 35f, 45f);
        cam.transform.position = camPos;
        cam.transform.LookAt(center);
    }

    void Update()
    {
        if (Input.GetKeyDown(columnsKey)) { ToggleGroup(columnGroup); }
        if (Input.GetKeyDown(beamsXKey)) { ToggleGroup(beamXGroup); }
        if (Input.GetKeyDown(beamsYKey)) { ToggleGroup(beamYGroup); }
        if (Input.GetKeyDown(wallsKey)) { ToggleGroup(wallGroup); }
        if (Input.GetKeyDown(lozasKey)) { ToggleGroup(lozaGroup); }
        if (Input.GetKeyDown(supportsKey)) { ToggleGroup(supportGroup); }
        if (Input.GetKeyDown(nodesKey)) { ToggleGroup(nodeGroup); }
        if (Input.GetKeyDown(axesKey))
        {
            // Igual que el visor HTML: E alterna los solidos y los palitos juntos.
            ToggleGroup(elementsGroup);
            ToggleGroup(axesGroup);
        }
        if (Input.GetKeyDown(diaphKey)) { ToggleGroup(diaphGroup); }
        if (Input.GetKeyDown(steelKey)) { ToggleGroup(steelGroup); }
        if (Input.GetKeyDown(hormigonKey))
        {
            ToggleHormigon();
        }
        BillboardLabels();
    }

    void ToggleGroup(GameObject group)
    {
        if (group != null) group.SetActive(!group.activeSelf);
    }

    // Alterna el modo hormigon: todo el edificio de un solo color de concreto,
    // con las fundaciones (cubos de apoyo) en un tono mas oscuro.
    void ToggleHormigon()
    {
        hormigonMode = !hormigonMode;
        if (hormigonMode)
        {
            ApplyMaterialToGroup(nodeGroup, hormigonMat, true);
            ApplyMaterialToGroup(elementsGroup, hormigonMat, true);
        }
        else
        {
            RestoreAllMaterials();
        }
    }

    // Aplica un material a los renderers (mesh) del grupo. Si guardarOriginales es
    // true, memoriza el material previo para poder restaurarlo. Los "Fundacion"
    // (cubos de la zapata) reciben el material de zapata oscuro.
    void ApplyMaterialToGroup(GameObject group, Material mat, bool saveOriginals)
    {
        if (group == null) return;
        foreach (Renderer r in group.GetComponentsInChildren<Renderer>())
        {
            if (r is LineRenderer) continue;
            if (IsLabelRenderer(r)) continue;
            if (saveOriginals && !originalMaterials.ContainsKey(r))
            {
                originalMaterials[r] = r.sharedMaterial;
            }
            bool esZapata = r.gameObject.name == "Fundacion";
            r.sharedMaterial = esZapata ? zapataMat : mat;
        }
    }

    // True si el renderer pertenece a una etiqueta de texto (para no pintarlas).
    bool IsLabelRenderer(Renderer r)
    {
        Transform t = r.transform;
        while (t != null)
        {
            if (labels.Contains(t)) return true;
            t = t.parent;
        }
        return false;
    }

    void RestoreAllMaterials()
    {
        foreach (KeyValuePair<Renderer, Material> kvp in originalMaterials)
        {
            if (kvp.Key != null)
            {
                kvp.Key.sharedMaterial = kvp.Value;
            }
        }
        originalMaterials.Clear();
    }

    void CreateMaterials()
    {
        Shader urp = Shader.Find("Universal Render Pipeline/Lit");
        if (urp == null) urp = Shader.Find("Standard");

        columnMat = NewLitMat(urp, columnColor, 0.2f, 0f);
        beamXMat = NewLitMat(urp, beamXColor, 0.15f, 0f);
        beamYMat = NewLitMat(urp, beamYColor, 0.15f, 0f);
        supportMat = NewLitMat(urp, supportColor, 0.2f, 0f);
        wallMat = NewLitMat(urp, wallColor, 0.15f, 0f);
        lozaMat = NewLitMat(urp, lozaColor, 0.1f, 0f);
        steelMat = NewLitMat(urp, steelColor, 0.35f, 0.35f);

        nodeMat = NewLitMat(urp, nodeColor, 0.4f, 0f);
        nodeMat.EnableKeyword("_EMISSION");
        nodeMat.SetColor("_EmissionColor", new Color(0f, 0.3f, 0.25f) * 0.5f);

        // Materiales del modo hormigon (aplicados con la tecla).
        hormigonMat = NewLitMat(urp, hormigonColor, 0.2f, 0f);
        zapataMat = NewLitMat(urp, zapataColor, 0.2f, 0f);

        // Materiales de los diafragmas (como el visor HTML).
        Shader sper = Shader.Find("Universal Render Pipeline/Unlit");
        if (sper == null) sper = Shader.Find("Unlit/Color");
        diaphFillMat = new Material(sper != null ? sper : Shader.Find("Standard"));
        diaphFillMat.color = new Color(diaphFillColor.r, diaphFillColor.g, diaphFillColor.b, diaphFillOpacity);
        if (diaphFillMat.HasProperty("_BaseColor")) diaphFillMat.SetColor("_BaseColor", diaphFillMat.color);
        if (diaphFillMat.HasProperty("_Surface")) diaphFillMat.SetFloat("_Surface", 1f);
        if (diaphFillMat.HasProperty("_Blend")) diaphFillMat.SetFloat("_Blend", 0f);
        diaphFillMat.renderQueue = 3000;

        Shader sprite = Shader.Find("Sprites/Default");
        if (sprite == null) sprite = Shader.Find("Unlit/Color");
        diaphEdgeMat = NewLineMat(sprite, diaphEdgeColor);
        labelBgMat = new Material(sprite);
        labelBgMat.color = new Color(0f, 0f, 0f, 0.78f);

        axisMats = new Material[6];
        axisMats[0] = NewLineMat(sprite, columnColor);
        axisMats[1] = NewLineMat(sprite, beamXColor);
        axisMats[2] = NewLineMat(sprite, beamYColor);
        axisMats[3] = NewLineMat(sprite, wallColor);      // muros
        axisMats[4] = NewLineMat(sprite, lozaColor);      // lozas
        axisMats[5] = NewLineMat(sprite, steelColor);     // metalicas
    }

    Material NewLitMat(Shader s, Color c, float smooth, float metal)
    {
        Material m = new Material(s);
        m.color = c;
        if (m.HasProperty("_Smoothness")) m.SetFloat("_Smoothness", smooth);
        if (m.HasProperty("_Metallic")) m.SetFloat("_Metallic", metal);
        return m;
    }

    Material NewLineMat(Shader s, Color c)
    {
        Material m = new Material(s);
        m.color = c;
        return m;
    }

    void BuildSupportSet(EdificioData data)
    {
        if (data.supports == null) return;
        foreach (SupportInfo s in data.supports)
        {
            supportIds.Add(s.node);
        }
    }

    void CreateNode(NodeData node, GameObject parent)
    {
        Vector3 pos = NodeToPos(node);
        bool isSupport = supportIds.Contains(node.id);

        if (isSupport)
        {
            CreateWeldSupport(pos, node.id.ToString());
        }
        else
        {
            GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sphere.transform.position = pos;
            sphere.transform.localScale = Vector3.one * 0.25f;
            sphere.GetComponent<Renderer>().material = nodeMat;
            sphere.transform.parent = parent.transform;
            sphere.name = "Nodo_" + node.id;

            GameObject label = CreateLabel(node.id.ToString(), pos + Vector3.up * 0.6f);
            label.transform.parent = parent.transform;
            label.name = "Label_" + node.id;
        }
    }

    void CreateWeldSupport(Vector3 pos, string nodeId)
    {
        GameObject holder = new GameObject("Apoyo_" + nodeId);
        holder.transform.parent = supportGroup.transform;

        GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        sphere.transform.parent = holder.transform;
        sphere.transform.position = pos;
        sphere.transform.localScale = Vector3.one * 0.3f;
        sphere.GetComponent<Renderer>().material = supportMat;

        GameObject foundation = GameObject.CreatePrimitive(PrimitiveType.Cube);
        foundation.transform.parent = holder.transform;
        foundation.transform.position = pos + new Vector3(0, -0.5f, 0);
        foundation.transform.localScale = new Vector3(2f, 1f, 2f);
        foundation.GetComponent<Renderer>().material = supportMat;
        foundation.name = "Fundacion";

        GameObject label = CreateLabel("a" + nodeId, pos + Vector3.up * 0.7f);
        label.transform.parent = nodeGroup.transform;
        label.name = "Label_" + nodeId;
    }

    Vector3 NodeToPos(NodeData n)
    {
        // Espejo en X para igualar la orientacion del visor 3D (Three.js es
        // right-handed; Unity es left-handed) -> el desnivel queda a la izquierda.
        return new Vector3(-n.x * scale, n.z * scale, n.y * scale);
    }

    void ComputeElementExtremes(ElementData elem, NodeData ni, NodeData nj, out Vector3 start, out Vector3 end)
    {
        start = NodeToPos(ni);
        end = NodeToPos(nj);

        float lift = elem.lift_cm * scale;
        start.y += lift;
        end.y += lift;

        string type = elem.type;
        if (type == "column")
        {
            float beamHalfH = 0.4f;
            end.y += beamHalfH;
            start.y -= elem.ext_bot_cm * scale;
        }
        else if (type == "beam_y")
        {
            start.z += elem.ext_start_cm * scale;
            end.z += elem.ext_end_cm * scale;
        }
        else if (type == "beam_x")
        {
            // El eje X va espejado en Unity, asi que la extension invierte el signo
            start.x -= elem.ext_start_cm * scale;
            end.x -= elem.ext_end_cm * scale;
        }
    }

    void CreateElement(ElementData elem, List<NodeData> allNodes)
    {
        string type = elem.type;

        if (type == "loza")
        {
            CreateLoza(elem, lozaGroup);
            return;
        }
        if (type == "wall")
        {
            CreateWall(elem, wallGroup);
            return;
        }
        if (type == "steel_column" || type == "steel_beam")
        {
            CreateSteel(elem, steelGroup);
            return;
        }

        NodeData ni = allNodes.Find(n => n.id == elem.node_i);
        NodeData nj = allNodes.Find(n => n.id == elem.node_j);
        if (ni == null || nj == null) return;

        Vector3 startPos, endPos;
        ComputeElementExtremes(elem, ni, nj, out startPos, out endPos);

        Material mat = columnMat;
        GameObject parent;
        if (type == "beam_x") { mat = beamXMat; parent = beamXGroup; }
        else if (type == "beam_y") { mat = beamYMat; parent = beamYGroup; }
        else { parent = columnGroup; }

        if (type == "column")
        {
            GameObject c = CreateBox(elem.id, startPos, endPos, elem.b * scale, elem.b * scale, parent, mat, type);
            AttachElementTag(c, elem, startPos, endPos, ni, nj);
        }
        else if (type == "beam_x" || type == "beam_y")
        {
            GameObject c = CreateBox(elem.id, startPos, endPos, elem.b * scale, elem.h * scale, parent, mat, type);
            AttachElementTag(c, elem, startPos, endPos, ni, nj);
        }

        CreateAxisLine(elem, startPos, endPos);
    }

    // Anade la etiqueta de identificacion al collider del elemento para el
    // inspector por clic (raycast). Las posiciones world usan cm * scale = metros.
    void AttachElementTag(GameObject go, ElementData elem, Vector3 start, Vector3 end,
                          NodeData ni, NodeData nj)
    {
        ElementTag tag = go.GetComponent<ElementTag>();
        if (tag == null) tag = go.AddComponent<ElementTag>();
        tag.elementId = elem.id;
        tag.type = elem.type;
        tag.section = elem.section;
        tag.bCm = elem.b;
        tag.hCm = elem.h;
        tag.start = start;
        tag.end = end;
        tag.niNode = elem.node_i;
        tag.njNode = elem.node_j;

        // Coordenadas estructurales (metros, antes del espejo X).
        if (ni != null)
        {
            tag.structX_I = ni.x;
            tag.structY_I = ni.z;
            tag.structZ_I = ni.y;
        }
        if (nj != null)
        {
            tag.structX_J = nj.x;
            tag.structY_J = nj.z;
            tag.structZ_J = nj.y;
        }

        tag.piso = ni != null ? ni.floor : "";

        // Enriquecer desde analysis_map si esta disponible.
        AnalysisMap.ElementInfo ei = AnalysisMap.Element(elem.id);
        if (ei != null)
        {
            tag.material = ei.material;
            tag.supI = ei.supI;
            tag.supJ = ei.supJ;
        }
    }

    void CreateLoza(ElementData elem, GameObject parent)
    {
        // Coordenadas directas en cm -> world (con espejo en X).
        Vector3 start = new Vector3(-elem.xi * scale, elem.yi * scale, elem.zi * scale);
        Vector3 end = new Vector3(-elem.xj * scale, elem.yj * scale, elem.zj * scale);
        Vector3 center = (start + end) * 0.5f;
        float w = Mathf.Abs(elem.xi - elem.xj) * scale;
        float d = Mathf.Abs(elem.zi - elem.zj) * scale;
        float th = Mathf.Max(elem.t, 0.01f) * scale;

        GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = "LOZA_" + elem.id;
        box.transform.position = center;
        box.transform.localScale = new Vector3(w, th, d);
        box.GetComponent<Renderer>().material = lozaMat;
        box.transform.parent = parent.transform;

        ElementTag tag = box.AddComponent<ElementTag>();
        tag.elementId = elem.id;
        tag.type = elem.type;
        tag.section = elem.section;
        tag.bCm = elem.b;
        tag.hCm = elem.h;
        tag.start = start;
        tag.end = end;
        tag.niNode = elem.node_i;
        tag.njNode = elem.node_j;
        tag.structX_I = elem.xi;
        tag.structY_I = elem.yi;
        tag.structZ_I = elem.zi;
        tag.structX_J = elem.xj;
        tag.structY_J = elem.yj;
        tag.structZ_J = elem.zj;
        tag.piso = NombrePisoLocal(elem.yi * scale);

        // Eje (como el visor HTML): linea diagonal entre los extremos del panel.
        AddAxisLine(axisMats[4], start, end, elem.id);
    }

    void CreateWall(ElementData elem, GameObject parent)
    {
        // Muro/pantalla. El visor distingue alma (avanza en X) y ala (avanza en Y).
        // Guardamos coordenadas directas igual que loza.
        Vector3 start = new Vector3(-elem.xi * scale, elem.yi * scale, elem.zi * scale);
        Vector3 end = new Vector3(-elem.xj * scale, elem.yj * scale, elem.zj * scale);
        Vector3 dir = end - start;
        Vector3 center = (start + end) * 0.5f;
        float b = elem.b * scale;
        float h = elem.h * scale;

        GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = "WALL_" + elem.id;
        box.transform.position = center;
        if (Mathf.Abs(dir.x) > 0.001f && Mathf.Abs(dir.z) < 0.001f)
        {
            // Tramo horizontal (avanza en X): largo=|dx|, alto=h, espesor=b
            box.transform.localScale = new Vector3(Mathf.Abs(elem.xi - elem.xj) * scale, h, b);
        }
        else
        {
            // Tramo vertical (avanza en Y): espesor=b, ancho=h, alto=largo
            box.transform.localScale = new Vector3(b, dir.magnitude, h);
        }
        box.GetComponent<Renderer>().material = wallMat;
        box.transform.parent = parent.transform;

        // Centro del muro en planta (con espejo del mismo signo en X).
        float cx = -(elem.xi + elem.xj) / 2f * scale;
        float cz = (elem.zi + elem.zj) / 2f * scale;
        Vector3 a = new Vector3(cx, start.y, cz);
        Vector3 top = new Vector3(cx, end.y, cz);
        AddAxisLine(axisMats[3], a, top, elem.id);

        ElementTag tag = box.AddComponent<ElementTag>();
        tag.elementId = elem.id;
        tag.type = elem.type;
        tag.section = elem.section;
        tag.bCm = elem.b;
        tag.hCm = elem.h;
        tag.start = a;
        tag.end = top;
        tag.niNode = elem.node_i;
        tag.njNode = elem.node_j;
        tag.structX_I = elem.xi;
        tag.structY_I = elem.yi;
        tag.structZ_I = elem.zi;
        tag.structX_J = elem.xj;
        tag.structY_J = elem.yj;
        tag.structZ_J = elem.zj;
        tag.piso = NombrePisoLocal(elem.yi * scale);
        AnalysisMap.ElementInfo eiWall = AnalysisMap.Element(elem.id);
        if (eiWall != null)
        {
            tag.material = eiWall.material;
            tag.supI = eiWall.supI;
            tag.supJ = eiWall.supJ;
            if (tag.niNode == 0 && eiWall.ni > 0) tag.niNode = eiWall.ni;
            if (tag.njNode == 0 && eiWall.nj > 0) tag.njNode = eiWall.nj;
        }
    }

    void CreateAxisLine(ElementData elem, Vector3 start, Vector3 end)
    {
        int idx = elem.type == "column" ? 0 : (elem.type == "beam_x" ? 1 : 2);
        AddAxisLine(axisMats[idx], start, end, elem.id);
    }

    // Metálico (steel_column / steel_beam): tubo amarillo entre extremos.
    // Usa las coordenadas directas (xi/yi/zi) como wall/loza (no tiene lift/ext).
    void CreateSteel(ElementData elem, GameObject parent)
    {
        Vector3 start = new Vector3(-elem.xi * scale, elem.yi * scale, elem.zi * scale);
        Vector3 end = new Vector3(-elem.xj * scale, elem.yj * scale, elem.zj * scale);
        Vector3 dir = end - start;
        Vector3 center = (start + end) * 0.5f;
        float length = Mathf.Max(dir.magnitude, 0.01f);

        GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = "STEEL_" + elem.id;
        box.transform.position = center;
        box.transform.rotation = Quaternion.LookRotation(dir.normalized);
        box.transform.localScale = new Vector3(elem.b * scale, elem.b * scale, length);
        box.GetComponent<Renderer>().material = steelMat;
        box.transform.parent = parent.transform;

        ElementTag tag = box.AddComponent<ElementTag>();
        tag.elementId = elem.id;
        tag.type = elem.type;
        tag.section = elem.section;
        tag.bCm = elem.b;
        tag.hCm = elem.h;
        tag.start = start;
        tag.end = end;
        tag.niNode = elem.node_i;
        tag.njNode = elem.node_j;
        tag.structX_I = elem.xi;
        tag.structY_I = elem.yi;
        tag.structZ_I = elem.zi;
        tag.structX_J = elem.xj;
        tag.structY_J = elem.yj;
        tag.structZ_J = elem.zj;
        tag.piso = NombrePisoLocal(elem.yi * scale);
        AnalysisMap.ElementInfo eiSteel = AnalysisMap.Element(elem.id);
        if (eiSteel != null)
        {
            tag.material = eiSteel.material;
            tag.supI = eiSteel.supI;
            tag.supJ = eiSteel.supJ;
            if (tag.niNode == 0 && eiSteel.ni > 0) tag.niNode = eiSteel.ni;
            if (tag.njNode == 0 && eiSteel.nj > 0) tag.njNode = eiSteel.nj;
        }

        AddAxisLine(axisMats[5], start, end, elem.id);
    }

    // Dibuja una linea de eje entre dos puntos del mundo en el grupo de ejes.
    void AddAxisLine(Material mat, Vector3 start, Vector3 end, int id)
    {
        GameObject lineGO = new GameObject("Eje_" + id);
        lineGO.transform.parent = axesGroup.transform;
        LineRenderer lr = lineGO.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startWidth = 0.15f;
        lr.endWidth = 0.15f;
        lr.positionCount = 2;
        lr.SetPosition(0, start);
        lr.SetPosition(1, end);
    }

    GameObject CreateBox(int id, Vector3 start, Vector3 end, float width, float height, GameObject parent, Material mat, string type)
    {
        Vector3 dir = end - start;
        float length = dir.magnitude;
        Vector3 center = (start + end) * 0.5f;

        GameObject box = GameObject.CreatePrimitive(PrimitiveType.Cube);
        box.name = type.ToUpper() + "_" + id;
        box.transform.position = center;

        if (type == "column")
        {
            box.transform.localScale = new Vector3(width, length, width);
        }
        else if (type == "beam_x")
        {
            box.transform.localScale = new Vector3(length, height, width);
        }
        else
        {
            box.transform.localScale = new Vector3(width, height, length);
        }

        box.GetComponent<Renderer>().material = mat;
        box.transform.parent = parent.transform;
        return box;
    }

    GameObject CreateLabel(string text, Vector3 position)
    {
        GameObject holder = new GameObject("Label_Text");
        holder.transform.position = position;

        GameObject bg = GameObject.CreatePrimitive(PrimitiveType.Quad);
        bg.transform.parent = holder.transform;
        bg.transform.localPosition = Vector3.zero;
        bg.transform.localScale = new Vector3(0.9f, 0.9f, 1f);
        bg.GetComponent<Renderer>().material = labelBgMat;
        bg.name = "Fondo";

        GameObject textGO = new GameObject("Texto");
        textGO.transform.parent = holder.transform;
        textGO.transform.localPosition = new Vector3(0f, 0f, 0.01f);
        TextMesh tm = textGO.AddComponent<TextMesh>();
        tm.text = text;
        tm.fontSize = (int)axisfontSize;
        tm.characterSize = labelScale;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.alignment = TextAlignment.Center;
        tm.color = Color.white;
        tm.fontStyle = FontStyle.Bold;

        Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        if (font != null)
        {
            tm.font = font;
            Renderer tmr = tm.GetComponent<Renderer>();
            if (tmr != null) tmr.sharedMaterial = font.material;
        }

        labels.Add(holder.transform);
        return holder;
    }

    void BillboardLabels()
    {
        if (labels.Count == 0) return;
        Camera cam = Camera.main;
        if (cam == null) return;
        foreach (Transform t in labels)
        {
            Vector3 dir = t.position - cam.transform.position;
            if (dir.sqrMagnitude < 0.0001f) continue;
            t.rotation = Quaternion.LookRotation(dir.normalized);
        }
    }

    // Crea los diafragmas rigidos por piso (poligonos de huella real), replicando
    // el visor HTML: un plano casi transparente + su borde, alternables con D.
    void CreateDiaphragms()
    {
        foreach (DiaphragmData.Diaph d in DiaphragmData.All)
        {
            GameObject holder = new GameObject("Diafragma_" + d.height);
            holder.transform.parent = diaphGroup.transform;

            // Borde del poligono (perimetro cerrado).
            Vector3[] edge = new Vector3[d.pts.Count + 1];
            for (int i = 0; i < d.pts.Count; i++)
            {
                edge[i] = new Vector3(-d.pts[i].x, d.height, d.pts[i].y);
            }
            edge[d.pts.Count] = edge[0];

            GameObject edgeGO = new GameObject("Borde");
            edgeGO.transform.parent = holder.transform;
            LineRenderer lr = edgeGO.AddComponent<LineRenderer>();
            lr.material = diaphEdgeMat;
            lr.loop = true;
            lr.startWidth = 0.1f;
            lr.endWidth = 0.1f;
            lr.positionCount = edge.Length;
            lr.SetPositions(edge);

            // Plano (superficie) mediante triangulacion ear-clipping.
            List<int> tris = TriangulatePolygon(d.pts);
            if (tris.Count > 0)
            {
                Mesh mesh = new Mesh();
                Vector3[] vertices = new Vector3[d.pts.Count];
                for (int i = 0; i < d.pts.Count; i++)
                {
                    vertices[i] = new Vector3(-d.pts[i].x, d.height, d.pts[i].y);
                }
                int[] triangles = tris.ToArray();
                mesh.vertices = vertices;
                mesh.triangles = triangles;
                mesh.RecalculateNormals();
                mesh.RecalculateBounds();

                GameObject plGO = new GameObject("Plano");
                plGO.transform.parent = holder.transform;
                MeshFilter mf = plGO.AddComponent<MeshFilter>();
                mf.sharedMesh = mesh;
                MeshRenderer mr = plGO.AddComponent<MeshRenderer>();
                mr.sharedMaterial = diaphFillMat;
            }
        }
    }

    // Crea el inspector por clic (panel de propiedades y cargas tributarias).
    void TrySetupInspector()
    {
        string tribPath = Path.Combine(Application.streamingAssetsPath, "tributary_map.js");
        GameObject inspGO = new GameObject("Inspector");
        inspector = inspGO.AddComponent<TributaryInspector>();
        inspector.Setup(tribPath, inspGO.transform);
    }

    // Crea el modo analisis (deformada / tubos M/N/V / reacciones) con datos del
    // analisis. Replica exactamente buildAnalysis() del visor HTML.
    void SetupAnalysisMode()
    {
        GameObject amGO = new GameObject("AnalysisMode");
        analysisMode = amGO.AddComponent<AnalysisMode>();
        analysisMode.transform.SetParent(elementsGroup.transform, false);
        // Se activa con TAB o con el boton de la barra superior.
    }

    // Crea el panel DATOS (tecla B): 6 pestanas (Sismo, Mom-Curv, P-M,
    // Reacciones, Tributarias, Diagramas) con datos del analisis.
    void SetupDataPanel()
    {
        GameObject dpGO = new GameObject("DataPanel");
        dpGO.transform.SetParent(transform, false);
        dataPanel = dpGO.AddComponent<DataPanel>();
    }

    // Crea el panel VERIFICACION (tecla V): trazabilidad 147 / 261 / 446.
    void SetupVerifPanel()
    {
        GameObject vpGO = new GameObject("VerifPanel");
        vpGO.transform.SetParent(transform, false);
        verifPanel = vpGO.AddComponent<VerifPanel>();
    }

    // Crea el hover magenta + doble-clic del modo analisis (reporte de viga /
    // curva P-M de capacidad), replicando visor.dblclick() del HTML.
    void SetupPickHighlight()
    {
        GameObject phGO = new GameObject("PickHighlight");
        var ph = phGO.AddComponent<PickHighlight>();
        ph.Setup(this, analysisMode);
    }

    // Crea la barra de modo superior (Modo + VISUALIZACION/ANALISIS + DATOS),
    // el HUD de info (nodos/elementos) y la leyenda de capas con checkboxes.
    void SetupViewerHud()
    {
        GameObject hudGO = new GameObject("ViewerHud");
        var hud = hudGO.AddComponent<ViewerHud>();
        hud.Setup(this, dataPanel);
    }

    // ---------- Capas por nombre (para el HUD con checkboxes) ----------
    GameObject GroupOf(string layer)
    {
        switch (layer)
        {
            case "columnas": return columnGroup;
            case "vigasX": return beamXGroup;
            case "vigasY": return beamYGroup;
            case "muros": return wallGroup;
            case "losas": return lozaGroup;
            case "metálicas": return steelGroup;
            case "apoyos": return supportGroup;
            case "nodos": return nodeGroup;
            case "ejes": return axesGroup;
            case "diafragmas": return diaphGroup;
            case "elementos": return elementsGroup;
            default: return null;
        }
    }

    public void SetLayerVisible(string layer, bool visible)
    {
        GameObject g = GroupOf(layer);
        if (g != null) g.SetActive(visible);
    }

    public bool IsLayerVisible(string layer)
    {
        GameObject g = GroupOf(layer);
        return g != null && g.activeSelf;
    }

    // "Todo" del visor HTML: activa todas las capas (incluidos los ejes).
    public void SetAllLayers(bool visible)
    {
        SetLayerVisible("columnas", visible);
        SetLayerVisible("vigasX", visible);
        SetLayerVisible("vigasY", visible);
        SetLayerVisible("muros", visible);
        SetLayerVisible("losas", visible);
        SetLayerVisible("metálicas", visible);
        SetLayerVisible("apoyos", visible);
        SetLayerVisible("nodos", visible);
        SetLayerVisible("ejes", visible);
        SetLayerVisible("diafragmas", visible);
    }

    // Desactiva las sombras de todo el modelo y de la luz direccional, para que
    // el edificio se vea "plano" como el visor 3D (algunos renderes usan lineas,
    // cubos, losas y diafragmas que con sombras se ven ruidosos).
    void DisableShadows()
    {
        GameObject[] roots = { elementsGroup, nodeGroup, axesGroup, diaphGroup };
        foreach (GameObject root in roots)
        {
            if (root == null) continue;
            foreach (Renderer r in root.GetComponentsInChildren<Renderer>())
            {
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                r.receiveShadows = false;
            }
        }
        foreach (Light l in FindObjectsOfType<Light>())
        {
            l.shadows = LightShadows.None;
        }
    }

    // Triangula un poligono (posiblemente concavo) por "ear clipping".
    // Recibe los puntos en orden (x,z) del poligono y devuelve la lista de
    // indices de vertices (tercetos) de los triangulos.
    List<int> TriangulatePolygon(List<UnityEngine.Vector2> pts)
    {
        List<int> result = new List<int>();
        if (pts.Count < 3) return result;

        List<int> idx = new List<int>();
        float signed = 0f;
        for (int i = 0; i < pts.Count; i++)
        {
            int j = (i + 1) % pts.Count;
            signed += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
        }
        // Sentido antihorario para que la convencion de la normal sea positiva.
        if (signed < 0f)
        {
            for (int i = pts.Count - 1; i >= 0; i--) idx.Add(i);
        }
        else
        {
            for (int i = 0; i < pts.Count; i++) idx.Add(i);
        }

        int guard = pts.Count * pts.Count + 10;
        while (idx.Count > 3 && guard-- > 0)
        {
            bool earFound = false;
            int n = idx.Count;
            for (int i = 0; i < n && !earFound; i++)
            {
                int i0 = idx[(i - 1 + n) % n];
                int i1 = idx[i];
                int i2 = idx[(i + 1) % n];
                UnityEngine.Vector2 a = pts[i0], b = pts[i1], c = pts[i2];
                // El vertice debe ser convexo (producto cruz > 0 en sentido antihorario).
                if (Cross(b - a, c - b) <= 0f) continue;
                // Ningun otro vertice del poligono puede estar dentro del triangulo.
                if (ContainsAnyOther(pts, idx, i, a, b, c)) continue;
                result.Add(i0);
                result.Add(i1);
                result.Add(i2);
                idx.RemoveAt(i);
                earFound = true;
            }
            if (!earFound) break;
        }
        if (idx.Count == 3)
        {
            result.Add(idx[0]);
            result.Add(idx[1]);
            result.Add(idx[2]);
        }
        return result;
    }

    float Cross(UnityEngine.Vector2 a, UnityEngine.Vector2 b)
    {
        return a.x * b.y - a.y * b.x;
    }

    // Verifica si algun vertice restante del poligono (distinto de i1) cae dentro
    // del triangulo (a,b,c). corriente = la lista de indices aun en el poligono.
    bool ContainsAnyOther(List<UnityEngine.Vector2> pts, List<int> idx, int current,
                          UnityEngine.Vector2 a, UnityEngine.Vector2 b, UnityEngine.Vector2 c)
    {
        for (int k = 0; k < idx.Count; k++)
        {
            if (k == current) continue;
            UnityEngine.Vector2 p = pts[idx[k]];
            if (PointInTri(p, a, b, c)) return true;
        }
        return false;
    }

    bool PointInTri(UnityEngine.Vector2 p, UnityEngine.Vector2 a, UnityEngine.Vector2 b, UnityEngine.Vector2 c)
    {
        float d1 = Cross(p - a, b - a);
        float d2 = Cross(p - b, c - b);
        float d3 = Cross(p - c, a - c);
        bool hasNeg = (d1 < 0f) || (d2 < 0f) || (d3 < 0f);
        bool hasPos = (d1 > 0f) || (d2 > 0f) || (d3 > 0f);
        return !(hasNeg && hasPos);
    }
}

[System.Serializable]
public class EdificioData
{
    public ModelInfo model;
    public SectionInfo[] sections;
    public FloorInfo[] floors;
    public List<NodeData> nodes;
    public List<ElementData> elements;
    public SupportInfo[] supports;
}

[System.Serializable]
public class ModelInfo
{
    public string description;
    public int ndm;
    public int ndf;
    public UnitInfo units;
}

[System.Serializable]
public class UnitInfo
{
    public string length;
    public string force;
    public string moment;
}

[System.Serializable]
public class SectionInfo
{
    public string name;
    public float b;
    public float h;
}

[System.Serializable]
public class FloorInfo
{
    public string name;
    public float elevation_base;
    public float elevation_top;
    public float top_of_beam;
}

[System.Serializable]
public class NodeData
{
    public int id;
    public float x;
    public float y;
    public float z;
    public string floor;
}

[System.Serializable]
public class ElementData
{
    public int id;
    public string type;
    public string section;
    public int node_i;
    public int node_j;
    public float b;
    public float h;
    public float lift_cm;
    public float ext_start_cm;
    public float ext_end_cm;
    public float ext_bot_cm;
    // Coordenadas directas (cm) usadas por loza y wall
    public float xi;
    public float yi;
    public float zi;
    public float xj;
    public float yj;
    public float zj;
    public float t;
}

[System.Serializable]
public class SupportInfo
{
    public int node;
    public int[] DOF;
    public string type;
}