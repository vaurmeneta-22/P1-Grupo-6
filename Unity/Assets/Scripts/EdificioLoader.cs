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

    [Header("Colores (como el visor 3D)")]
    public Color columnColor = new Color(0.906f, 0.298f, 0.235f);   // #e74c3c
    public Color beamXColor = new Color(0.204f, 0.596f, 0.859f);    // #3498db
    public Color beamYColor = new Color(0.180f, 0.800f, 0.443f);    // #2ecc71
    public Color nodeColor = new Color(0.945f, 0.769f, 0.059f);     // #f1c40f
    public Color supportColor = new Color(0.608f, 0.349f, 0.714f);  // #9b59b6
    public Color wallColor = new Color(0.608f, 0.349f, 0.714f);     // #9b59b6
    public Color lozaColor = new Color(0.902f, 0.404f, 0.133f);     // #e67e22

    [Header("Teclas")]
    public KeyCode nodesKey = KeyCode.N;
    public KeyCode axesKey = KeyCode.E;

    private GameObject elementsGroup;
    private GameObject axesGroup;
    private GameObject nodeGroup;
    private HashSet<int> supportIds = new HashSet<int>();
    private List<Transform> labels = new List<Transform>();
    private Material labelBgMat;
    private Material[] axisMats;
    private float labelScale = 0.04f;
    private float axisfontSize = 48f;

    void Start()
    {
        QualitySettings.antiAliasing = 4;
        Application.targetFrameRate = 60;

        string path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        string json = File.ReadAllText(path);
        EdificioData data = JsonUtility.FromJson<EdificioData>(json);

        CreateMaterials();
        BuildSupportSet(data);

        elementsGroup = new GameObject("Elementos");
        axesGroup = new GameObject("Ejes");
        nodeGroup = new GameObject("Nodos");
        axesGroup.SetActive(false);

        foreach (NodeData node in data.nodes)
        {
            CreateNode(node, nodeGroup);
        }

        foreach (ElementData elem in data.elements)
        {
            CreateElement(elem, data.nodes, elementsGroup);
        }

        Camera cam = Camera.main;
        if (cam != null)
        {
            cam.farClipPlane = 500f;
            cam.transform.position = new Vector3(-10f, 35f, 55f);
            cam.transform.LookAt(new Vector3(-10f, 9f, 8f));
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(nodesKey))
        {
            nodeGroup.SetActive(!nodeGroup.activeSelf);
        }
        if (Input.GetKeyDown(axesKey))
        {
            elementsGroup.SetActive(!elementsGroup.activeSelf);
            axesGroup.SetActive(!elementsGroup.activeSelf);
        }
        BillboardLabels();
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

        nodeMat = NewLitMat(urp, nodeColor, 0.4f, 0f);
        nodeMat.EnableKeyword("_EMISSION");
        nodeMat.SetColor("_EmissionColor", new Color(0.4f, 0.3f, 0f) * 0.5f);

        Shader sprite = Shader.Find("Sprites/Default");
        if (sprite == null) sprite = Shader.Find("Unlit/Color");
        labelBgMat = new Material(sprite);
        labelBgMat.color = new Color(0f, 0f, 0f, 0.78f);

        axisMats = new Material[3];
        axisMats[0] = NewLineMat(sprite, columnColor);
        axisMats[1] = NewLineMat(sprite, beamXColor);
        axisMats[2] = NewLineMat(sprite, beamYColor);
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
        holder.transform.parent = elementsGroup.transform;

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

    void CreateElement(ElementData elem, List<NodeData> allNodes, GameObject parent)
    {
        string type = elem.type;

        if (type == "loza")
        {
            CreateLoza(elem, parent);
            return;
        }
        if (type == "wall")
        {
            CreateWall(elem, parent);
            return;
        }

        NodeData ni = allNodes.Find(n => n.id == elem.node_i);
        NodeData nj = allNodes.Find(n => n.id == elem.node_j);
        if (ni == null || nj == null) return;

        Vector3 startPos, endPos;
        ComputeElementExtremes(elem, ni, nj, out startPos, out endPos);

        Material mat = columnMat;
        if (type == "beam_x") mat = beamXMat;
        else if (type == "beam_y") mat = beamYMat;

        if (type == "column")
        {
            CreateBox(elem.id, startPos, endPos, elem.b * scale, elem.b * scale, parent, mat, type);
        }
        else if (type == "beam_x" || type == "beam_y")
        {
            CreateBox(elem.id, startPos, endPos, elem.b * scale, elem.h * scale, parent, mat, type);
        }

        CreateAxisLine(elem, startPos, endPos);
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
    }

    void CreateAxisLine(ElementData elem, Vector3 start, Vector3 end)
    {
        int idx = elem.type == "column" ? 0 : (elem.type == "beam_x" ? 1 : 2);
        GameObject lineGO = new GameObject("Eje_" + elem.id);
        lineGO.transform.parent = axesGroup.transform;
        LineRenderer lr = lineGO.AddComponent<LineRenderer>();
        lr.material = axisMats[idx];
        lr.startWidth = 0.15f;
        lr.endWidth = 0.15f;
        lr.positionCount = 2;
        lr.SetPosition(0, start);
        lr.SetPosition(1, end);
    }

    void CreateBox(int id, Vector3 start, Vector3 end, float width, float height, GameObject parent, Material mat, string type)
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