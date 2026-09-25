using System;
using System.Collections.Generic;
using UnityEngine;

// SQ4: prototipo de carga movil asociada al usuario/camara.
// Identifica el panel/losa bajo el centro de pantalla, busca vigas receptoras
// desde analysis_map.tributarias y reparte P_user segun areas tributarias.
public class MobileLoadSQ4 : MonoBehaviour
{
    class Receiver
    {
        public int beamId;
        public double area;
        public double weight;
        public double load;
        public string edge;
        public float distance;
        public float overlap;
    }

    EdificioLoader loader;
    Camera cam;
    bool active;
    bool pinnedPanel;
    float userLoad = 50f;
    int panelId = -1;
    string panelName = "-";
    string repartoModo = "-";
    bool edgeFallbackUsed;
    bool draggingMarker;
    bool markerMoved;
    Vector3 panelPoint;
    Vector2 scroll;

    readonly Dictionary<int, Renderer> renderers = new Dictionary<int, Renderer>();
    readonly Dictionary<Renderer, Material> saved = new Dictionary<Renderer, Material>();
    readonly List<Receiver> receivers = new List<Receiver>();
    Material loadMat;
    Material visualMat;
    Material hammerMat;
    Material lineMat;
    GameObject visualGroup;

    public void Setup(EdificioLoader l)
    {
        loader = l;
    }

    void Start()
    {
        cam = Camera.main;
        BuildRendererMap();
        Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
        if (unlit == null) unlit = Shader.Find("Unlit/Color");
        loadMat = new Material(unlit != null ? unlit : Shader.Find("Standard"));
        loadMat.color = new Color(1f, 0.92f, 0.18f, 1f);
        visualMat = new Material(unlit != null ? unlit : Shader.Find("Standard"));
        visualMat.color = new Color(0.0f, 0.95f, 1f, 1f);
        hammerMat = new Material(unlit != null ? unlit : Shader.Find("Standard"));
        hammerMat.color = new Color(1f, 0.18f, 0.62f, 1f);
        Shader lineShader = Shader.Find("Sprites/Default");
        if (lineShader == null) lineShader = Shader.Find("Unlit/Color");
        lineMat = new Material(lineShader != null ? lineShader : Shader.Find("Standard"));
        lineMat.color = new Color(0.0f, 0.95f, 1f, 1f);
        visualGroup = new GameObject("SQ4Visuals");
        visualGroup.transform.SetParent(transform, false);
    }

    void BuildRendererMap()
    {
        renderers.Clear();
        if (loader == null || loader.ElementsGroup == null) return;
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
        {
            Renderer r = tag.GetComponent<Renderer>();
            if (r != null && !renderers.ContainsKey(tag.elementId)) renderers[tag.elementId] = r;
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.U)) SetActive(!active);
        if (!active) return;
        if (AnalysisMode.Current == null || !AnalysisMode.Current.Active)
        {
            SetActive(false);
            return;
        }
        if (cam == null) cam = Camera.main;
        HandleMarkerDrag();
        RefreshPanelAndReceivers();
    }

    public void SetActive(bool v)
    {
        if (active == v) return;
        active = v;
        if (!active)
        {
            ClearHighlight();
            panelId = -1;
            pinnedPanel = false;
            draggingMarker = false;
            markerMoved = false;
            ElementInfoStyle.SQ4Dragging = false;
            receivers.Clear();
        }
    }

    public bool Active { get { return active; } }

    public void ShowPanel(int id, Vector3 hitPoint)
    {
        if (id <= 0) return;
        active = true;
        pinnedPanel = true;
        panelId = id;
        panelName = "Losa " + panelId;
        panelPoint = hitPoint;
        if (panelPoint == Vector3.zero) panelPoint = ElementCenter(id);
        draggingMarker = false;
        markerMoved = false;
        BuildReceivers();
        ApplyHighlight();
        FrameSQ4View();
    }

    void RefreshPanelAndReceivers()
    {
        if (pinnedPanel)
        {
            ComputeLoads();
            return;
        }
        int newPanel = PickPanel(out panelPoint);
        if (newPanel != panelId)
        {
            panelId = newPanel;
            panelName = panelId > 0 ? "Losa " + panelId : "sin panel";
            BuildReceivers();
            ApplyHighlight();
        }
        else
        {
            ComputeLoads();
        }
    }

    void HandleMarkerDrag()
    {
        if (!pinnedPanel || cam == null || panelId <= 0) return;
        if (Input.GetMouseButtonDown(0) && !ElementInfoStyle.PointerOverPanel)
        {
            Vector3 screen = cam.WorldToScreenPoint(panelPoint + Vector3.up * 0.35f);
            if (screen.z > 0f && Vector2.Distance(Input.mousePosition, new Vector2(screen.x, screen.y)) < 48f)
            {
                draggingMarker = true;
                ElementInfoStyle.SQ4Dragging = true;
            }
        }
        if (Input.GetMouseButtonUp(0))
        {
            draggingMarker = false;
            ElementInfoStyle.SQ4Dragging = false;
        }
        if (!draggingMarker) return;

        Vector3 p;
        if (MousePointOnPanel(out p))
        {
            panelPoint = p;
            markerMoved = true;
            ComputeLoads();
            BuildLoadVisuals();
        }
    }

    bool MousePointOnPanel(out Vector3 p)
    {
        p = panelPoint;
        Ray ray = cam.ScreenPointToRay(Input.mousePosition);
        RaycastHit[] hits = Physics.RaycastAll(ray, 1000f);
        Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit h in hits)
        {
            ElementTag tag = h.collider.GetComponentInParent<ElementTag>();
            if (tag != null && tag.elementId == panelId)
            {
                p = ClampToPanelBounds(h.point);
                return true;
            }
        }

        Plane plane = new Plane(Vector3.up, panelPoint);
        float enter;
        if (plane.Raycast(ray, out enter))
        {
            p = ClampToPanelBounds(ray.GetPoint(enter));
            return true;
        }
        return false;
    }

    Vector3 ClampToPanelBounds(Vector3 p)
    {
        Bounds b;
        if (!ElementBounds(panelId, out b)) return p;
        p.x = Mathf.Clamp(p.x, b.min.x + 0.08f, b.max.x - 0.08f);
        p.z = Mathf.Clamp(p.z, b.min.z + 0.08f, b.max.z - 0.08f);
        p.y = b.max.y + 0.02f;
        return p;
    }

    int PickPanel(out Vector3 hitPoint)
    {
        hitPoint = Vector3.zero;
        if (cam == null) return -1;

        Ray ray = cam.ScreenPointToRay(new Vector2(Screen.width * 0.5f, Screen.height * 0.5f));
        RaycastHit[] hits = Physics.RaycastAll(ray, 1000f);
        Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit h in hits)
        {
            ElementTag tag = h.collider.GetComponentInParent<ElementTag>();
            if (tag == null || tag.type != "loza") continue;
            hitPoint = h.point;
            return tag.elementId;
        }

        return ClosestSlabToCamera(out hitPoint);
    }

    int ClosestSlabToCamera(out Vector3 point)
    {
        point = cam != null ? cam.transform.position : Vector3.zero;
        if (loader == null || loader.ElementsGroup == null) return -1;

        Vector3 p = point;
        int best = -1;
        float bestD = float.MaxValue;
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
        {
            if (tag.type != "loza") continue;
            Vector3 c = (tag.start + tag.end) * 0.5f;
            float d = new Vector2(c.x - p.x, c.z - p.z).sqrMagnitude;
            if (d < bestD)
            {
                bestD = d;
                best = tag.elementId;
                point = c;
            }
        }
        return best;
    }

    void BuildReceivers()
    {
        receivers.Clear();
        edgeFallbackUsed = false;
        if (panelId <= 0) return;

        string pid = panelId.ToString();
        if (AnalysisMap.Tribu != null)
        {
            foreach (KeyValuePair<int, AnalysisMap.TribuInfo> kv in AnalysisMap.Tribu)
            {
                AnalysisMap.TribuInfo t = kv.Value;
                if (t == null || t.aportes == null) continue;
                foreach (object ap in t.aportes)
                {
                    string losa = MiniJson.St(ap, "losa");
                    if (losa != pid) continue;

                    Receiver r = new Receiver();
                    r.beamId = kv.Key;
                    r.area = Math.Max(0.0, MiniJson.Db(ap, "area_m2"));
                    r.edge = MiniJson.St(ap, "borde") ?? "tributaria";
                    r.distance = BeamDistance(kv.Key, panelPoint);
                    receivers.Add(r);
                    break;
                }
            }
        }
        if (receivers.Count == 0) BuildNearestBeamFallback();
        ComputeLoads();
    }

    void BuildNearestBeamFallback()
    {
        if (loader == null || loader.ElementsGroup == null) return;
        ElementTag panelTag = FindElementTag(panelId);
        float panelY = panelTag != null ? ElementCenter(panelId).y : panelPoint.y;
        string panelFloor = panelTag != null ? panelTag.piso : "";
        if (panelTag != null) BuildEdgeBeamCandidates(panelTag, panelFloor, panelY);
        if (receivers.Count > 0) return;

        List<Receiver> candidates = new List<Receiver>();
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
        {
            if (tag.type != "beam_x" && tag.type != "beam_y") continue;
            if (!SameLevel(tag, panelFloor, panelY)) continue;
            Receiver r = new Receiver();
            r.beamId = tag.elementId;
            r.edge = "cercana";
            r.distance = DistancePointToSegmentXZ(panelPoint, tag.start, tag.end);
            r.area = 0.0; // ultimo fallback por distancia inversa.
            candidates.Add(r);
        }
        candidates.Sort((a, b) => a.distance.CompareTo(b.distance));
        int take = Math.Min(4, candidates.Count);
        for (int i = 0; i < take; i++) receivers.Add(candidates[i]);
    }

    void BuildEdgeBeamCandidates(ElementTag panel, string panelFloor, float panelY)
    {
        List<Receiver> candidates = new List<Receiver>();
        BuildPhysicsEdgeCandidates(panel.elementId, candidates);
        if (candidates.Count == 0) BuildCoordinateEdgeCandidates(panel, panelFloor, panelY, candidates);
        PickBestEdgeReceivers(candidates);
    }

    void BuildPhysicsEdgeCandidates(int slabId, List<Receiver> candidates)
    {
        Bounds slab;
        if (!ElementBounds(slabId, out slab)) return;
        const float margin = 0.45f;
        const float edgeBand = 0.55f;
        const float halfHeight = 0.75f;

        AddOverlapEdge(candidates, "sur",
            new Vector3(slab.center.x, slab.center.y, slab.min.z),
            new Vector3(slab.extents.x + margin, halfHeight, edgeBand));
        AddOverlapEdge(candidates, "norte",
            new Vector3(slab.center.x, slab.center.y, slab.max.z),
            new Vector3(slab.extents.x + margin, halfHeight, edgeBand));
        AddOverlapEdge(candidates, "oeste",
            new Vector3(slab.min.x, slab.center.y, slab.center.z),
            new Vector3(edgeBand, halfHeight, slab.extents.z + margin));
        AddOverlapEdge(candidates, "este",
            new Vector3(slab.max.x, slab.center.y, slab.center.z),
            new Vector3(edgeBand, halfHeight, slab.extents.z + margin));
    }

    void AddOverlapEdge(List<Receiver> candidates, string edgeName, Vector3 center, Vector3 halfExtents)
    {
        Collider[] hits = Physics.OverlapBox(center, halfExtents, Quaternion.identity);
        foreach (Collider col in hits)
        {
            ElementTag tag = col.GetComponentInParent<ElementTag>();
            if (tag == null || (tag.type != "beam_x" && tag.type != "beam_y")) continue;
            Bounds b;
            if (!ElementBounds(tag.elementId, out b)) continue;
            float overlap;
            float distance;
            if (edgeName == "sur" || edgeName == "norte")
            {
                overlap = Overlap1D(b.min.x, b.max.x, center.x - halfExtents.x, center.x + halfExtents.x);
                distance = Mathf.Abs(b.center.z - center.z);
            }
            else
            {
                overlap = Overlap1D(b.min.z, b.max.z, center.z - halfExtents.z, center.z + halfExtents.z);
                distance = Mathf.Abs(b.center.x - center.x);
            }
            AddEdgeCandidate(candidates, tag.elementId, edgeName, true, overlap, distance, 2.0f);
        }
    }

    void BuildCoordinateEdgeCandidates(ElementTag panel, string panelFloor, float panelY, List<Receiver> candidates)
    {
        float xmin = Mathf.Min(panel.start.x, panel.end.x);
        float xmax = Mathf.Max(panel.start.x, panel.end.x);
        float zmin = Mathf.Min(panel.start.z, panel.end.z);
        float zmax = Mathf.Max(panel.start.z, panel.end.z);
        const float edgeTol = 1.1f;

        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
        {
            if (tag.type != "beam_x" && tag.type != "beam_y") continue;
            if (!SameLevel(tag, panelFloor, panelY)) continue;

            Bounds b;
            if (!ElementBounds(tag.elementId, out b)) continue;
            float bx0 = b.min.x, bx1 = b.max.x;
            float bz0 = b.min.z, bz1 = b.max.z;
            float dx = Mathf.Abs(bx1 - bx0);
            float dz = Mathf.Abs(bz1 - bz0);
            bool alongX = dx >= dz;
            bool alongZ = dz > dx;

            AddEdgeCandidate(candidates, tag.elementId, "sur", alongX,
                Overlap1D(bx0, bx1, xmin, xmax), Mathf.Abs(b.center.z - zmin), edgeTol);
            AddEdgeCandidate(candidates, tag.elementId, "norte", alongX,
                Overlap1D(bx0, bx1, xmin, xmax), Mathf.Abs(b.center.z - zmax), edgeTol);
            AddEdgeCandidate(candidates, tag.elementId, "oeste", alongZ,
                Overlap1D(bz0, bz1, zmin, zmax), Mathf.Abs(b.center.x - xmin), edgeTol);
            AddEdgeCandidate(candidates, tag.elementId, "este", alongZ,
                Overlap1D(bz0, bz1, zmin, zmax), Mathf.Abs(b.center.x - xmax), edgeTol);
        }
    }

    bool ElementBounds(int id, out Bounds bounds)
    {
        Renderer r;
        if (renderers.TryGetValue(id, out r) && r != null)
        {
            bounds = r.bounds;
            return true;
        }
        bounds = new Bounds();
        return false;
    }

    void AddEdgeCandidate(List<Receiver> candidates, int beamId, string edgeName, bool orientationOk,
                          float overlap, float distance, float edgeTol)
    {
        if (!orientationOk || overlap <= 0.20f || distance > edgeTol) return;
        foreach (Receiver existing in candidates)
        {
            if (existing.beamId == beamId && existing.edge == edgeName)
            {
                if (overlap > existing.overlap)
                {
                    existing.overlap = overlap;
                    existing.area = overlap;
                    existing.distance = Mathf.Max(0.01f, distance);
                }
                return;
            }
        }
        Receiver r = new Receiver();
        r.beamId = beamId;
        r.edge = edgeName;
        r.distance = Mathf.Max(0.01f, distance);
        r.overlap = overlap;
        r.area = overlap; // reparto por longitud de borde/solape.
        candidates.Add(r);
    }

    void PickBestEdgeReceivers(List<Receiver> candidates)
    {
        string[] edges = { "sur", "norte", "oeste", "este" };
        foreach (string edgeName in edges)
        {
            Receiver best = null;
            float bestScore = -1f;
            foreach (Receiver r in candidates)
            {
                if (r.edge != edgeName) continue;
                float score = r.overlap / (1f + r.distance);
                if (score > bestScore)
                {
                    bestScore = score;
                    best = r;
                }
            }
            if (best != null) receivers.Add(best);
        }

        // En losas apoyadas por vigas partidas puede haber mas de una viga por borde.
        // Si quedaron pocos apoyos, completa con candidatos de alto solape sin duplicar.
        if (receivers.Count < 4)
        {
            candidates.Sort((a, b) =>
            {
                float sa = a.overlap / (1f + a.distance);
                float sb = b.overlap / (1f + b.distance);
                return sb.CompareTo(sa);
            });
            foreach (Receiver r in candidates)
            {
                if (receivers.Count >= 4) break;
                bool exists = false;
                foreach (Receiver e in receivers) if (e.beamId == r.beamId) { exists = true; break; }
                if (!exists) receivers.Add(r);
            }
        }
        if (receivers.Count > 0) edgeFallbackUsed = true;
    }

    static float Overlap1D(float a0, float a1, float b0, float b1)
    {
        return Mathf.Max(0f, Mathf.Min(a1, b1) - Mathf.Max(a0, b0));
    }

    ElementTag FindElementTag(int id)
    {
        if (loader == null || loader.ElementsGroup == null) return null;
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
            if (tag.elementId == id) return tag;
        return null;
    }

    bool SameLevel(ElementTag beam, string panelFloor, float panelY)
    {
        if (!string.IsNullOrEmpty(panelFloor) && beam.piso == panelFloor) return true;
        Renderer r;
        if (renderers.TryGetValue(beam.elementId, out r) && r != null)
            return Mathf.Abs(r.bounds.center.y - panelY) < 1.2f;
        float y = (beam.start.y + beam.end.y) * 0.5f;
        return Mathf.Abs(y - panelY) < 1.2f;
    }

    static float DistancePointToSegmentXZ(Vector3 p, Vector3 a, Vector3 b)
    {
        Vector2 pp = new Vector2(p.x, p.z);
        Vector2 aa = new Vector2(a.x, a.z);
        Vector2 bb = new Vector2(b.x, b.z);
        Vector2 ab = bb - aa;
        float len2 = ab.sqrMagnitude;
        float t = len2 > 1e-8f ? Vector2.Dot(pp - aa, ab) / len2 : 0f;
        t = Mathf.Clamp01(t);
        return Vector2.Distance(pp, aa + ab * t);
    }

    float BeamDistance(int id, Vector3 p)
    {
        Renderer r;
        if (renderers.TryGetValue(id, out r) && r != null)
        {
            Vector3 c = r.bounds.center;
            return Vector3.Distance(new Vector3(c.x, 0, c.z), new Vector3(p.x, 0, p.z));
        }
        return 0f;
    }

    Vector3 ElementCenter(int id)
    {
        Renderer r;
        if (renderers.TryGetValue(id, out r) && r != null) return r.bounds.center;
        return Vector3.zero;
    }

    void ComputeLoads()
    {
        if (receivers.Count == 0) return;
        if (markerMoved)
        {
            double sumInfluence = 0.0;
            foreach (Receiver r in receivers)
            {
                r.distance = DistanceToBeam(r.beamId, panelPoint);
                r.weight = 1.0 / Math.Max(0.25, r.distance);
                sumInfluence += r.weight;
            }
            repartoModo = "movil por distancia";
            foreach (Receiver r in receivers)
            {
                r.weight = sumInfluence > 1e-9 ? r.weight / sumInfluence : 0.0;
                r.load = userLoad * r.weight;
            }
            return;
        }
        double sumArea = 0.0;
        foreach (Receiver r in receivers) sumArea += r.area;

        if (sumArea > 1e-9)
        {
            repartoModo = edgeFallbackUsed ? "borde por solape" : "tributario por area";
            foreach (Receiver r in receivers)
            {
                r.weight = r.area / sumArea;
                r.load = userLoad * r.weight;
            }
            return;
        }

        double sumW = 0.0;
        foreach (Receiver r in receivers)
        {
            double w = 1.0 / Math.Max(0.25, r.distance);
            r.weight = w;
            sumW += w;
        }
        repartoModo = "fallback distancia inversa";
        foreach (Receiver r in receivers)
        {
            r.weight = sumW > 1e-9 ? r.weight / sumW : 0.0;
            r.load = userLoad * r.weight;
        }
    }

    void ApplyHighlight()
    {
        ClearHighlight();
        Paint(panelId);
        foreach (Receiver r in receivers) Paint(r.beamId);
        BuildLoadVisuals();
    }

    void BuildLoadVisuals()
    {
        ClearVisuals();
        if (visualGroup == null || receivers.Count == 0) return;

        DrawApplicationMarker(panelPoint + Vector3.up * 0.22f);

        foreach (Receiver r in receivers)
        {
            Vector3 c = BeamTopPoint(r.beamId);
            if (c == Vector3.zero) continue;
            Vector3 target = c + Vector3.up * 0.08f;
            DrawLink(panelPoint + Vector3.up * 0.24f, target, "SQ4_link_" + r.beamId);
            float h = Mathf.Clamp((float)(r.load / Math.Max(1.0, userLoad)) * 1.45f, 0.28f, 1.45f);
            DrawLoadArrow(c, h, r.beamId);
            CreateLabel(r.load.ToString("F1") + " kN", c + Vector3.up * (0.34f + h));
        }
    }

    float DistanceToBeam(int id, Vector3 p)
    {
        ElementTag tag = FindElementTag(id);
        if (tag != null) return DistancePointToSegmentXZ(p, tag.start, tag.end);
        return BeamDistance(id, p);
    }

    void DrawApplicationMarker(Vector3 pos)
    {
        DrawHammer(pos + Vector3.up * 0.08f);

        GameObject ring = new GameObject("SQ4_AroAplicacion");
        ring.transform.SetParent(visualGroup.transform, false);
        LineRenderer lr = ring.AddComponent<LineRenderer>();
        lr.material = lineMat;
        lr.startWidth = 0.035f;
        lr.endWidth = 0.035f;
        lr.loop = true;
        lr.positionCount = 48;
        float radius = 0.48f;
        for (int i = 0; i < lr.positionCount; i++)
        {
            float a = (i / (float)lr.positionCount) * Mathf.PI * 2f;
            lr.SetPosition(i, pos + new Vector3(Mathf.Cos(a) * radius, 0.03f, Mathf.Sin(a) * radius));
        }
    }

    void DrawHammer(Vector3 pos)
    {
        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Cube);
        head.name = "SQ4_MartilloCabeza";
        head.transform.SetParent(visualGroup.transform, false);
        head.transform.position = pos + Vector3.up * 0.28f;
        head.transform.localScale = new Vector3(0.58f, 0.28f, 0.30f);
        head.transform.rotation = Quaternion.Euler(0f, 25f, 0f);
        head.GetComponent<Renderer>().sharedMaterial = hammerMat;
        Destroy(head.GetComponent<Collider>());

        GameObject handle = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        handle.name = "SQ4_MartilloMango";
        handle.transform.SetParent(visualGroup.transform, false);
        handle.transform.position = pos - Vector3.up * 0.02f;
        handle.transform.localScale = new Vector3(0.07f, 0.36f, 0.07f);
        handle.transform.rotation = Quaternion.Euler(0f, 25f, 16f);
        handle.GetComponent<Renderer>().sharedMaterial = hammerMat;
        Destroy(handle.GetComponent<Collider>());
    }

    void DrawLink(Vector3 a, Vector3 b, string name)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(visualGroup.transform, false);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = lineMat;
        lr.startWidth = 0.025f;
        lr.endWidth = 0.045f;
        lr.positionCount = 3;
        Vector3 mid = (a + b) * 0.5f + Vector3.up * 0.28f;
        lr.SetPosition(0, a);
        lr.SetPosition(1, mid);
        lr.SetPosition(2, b);
    }

    void DrawLoadArrow(Vector3 beamTop, float height, int id)
    {
        Vector3 top = beamTop + Vector3.up * height;
        Vector3 bottom = beamTop + Vector3.up * 0.06f;
        DrawLine(top, bottom, 0.055f, "SQ4_arrow_body_" + id);

        GameObject head = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        head.name = "SQ4_arrow_head_" + id;
        head.transform.SetParent(visualGroup.transform, false);
        head.transform.position = bottom;
        head.transform.localScale = new Vector3(0.24f, 0.12f, 0.24f);
        head.GetComponent<Renderer>().sharedMaterial = visualMat;
        Destroy(head.GetComponent<Collider>());
    }

    Vector3 BeamCenter(int id)
    {
        Renderer r;
        if (renderers.TryGetValue(id, out r) && r != null) return r.bounds.center;
        return Vector3.zero;
    }

    Vector3 BeamTopPoint(int id)
    {
        Renderer r;
        if (renderers.TryGetValue(id, out r) && r != null)
            return new Vector3(r.bounds.center.x, r.bounds.max.y + 0.04f, r.bounds.center.z);
        return Vector3.zero;
    }

    void DrawLine(Vector3 a, Vector3 b, float width, string name)
    {
        GameObject go = new GameObject(name);
        go.transform.SetParent(visualGroup.transform, false);
        LineRenderer lr = go.AddComponent<LineRenderer>();
        lr.material = lineMat;
        lr.startWidth = width;
        lr.endWidth = width;
        lr.positionCount = 2;
        lr.SetPosition(0, a);
        lr.SetPosition(1, b);
    }

    void CreateLabel(string text, Vector3 pos)
    {
        GameObject go = new GameObject("SQ4_label");
        go.transform.SetParent(visualGroup.transform, false);
        go.transform.position = pos;
        TextMesh tm = go.AddComponent<TextMesh>();
        tm.text = text;
        tm.fontSize = 36;
        tm.characterSize = 0.045f;
        tm.anchor = TextAnchor.MiddleCenter;
        tm.alignment = TextAlignment.Center;
        tm.color = new Color(0.02f, 0.08f, 0.10f, 1f);
        Font font = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        if (font != null) tm.font = font;
        Camera camera = Camera.main;
        if (camera != null) go.transform.rotation = Quaternion.LookRotation(go.transform.position - camera.transform.position);
    }

    void FrameSQ4View()
    {
        Camera camera = Camera.main;
        if (camera == null) return;
        CameraController ctrl = camera.GetComponent<CameraController>();
        if (ctrl == null) return;

        Bounds b = new Bounds(panelPoint, Vector3.one * 0.5f);
        Renderer panelRenderer;
        if (renderers.TryGetValue(panelId, out panelRenderer) && panelRenderer != null)
            b.Encapsulate(panelRenderer.bounds);
        foreach (Receiver r in receivers)
        {
            Renderer rr;
            if (renderers.TryGetValue(r.beamId, out rr) && rr != null) b.Encapsulate(rr.bounds);
        }
        b.Expand(Mathf.Max(3f, b.size.magnitude * 0.35f));
        ctrl.FrameBounds(b);
    }

    void Paint(int id)
    {
        Renderer r;
        if (!renderers.TryGetValue(id, out r) || r == null) return;
        if (!saved.ContainsKey(r)) saved[r] = r.sharedMaterial;
        r.sharedMaterial = loadMat;
    }

    void ClearHighlight()
    {
        foreach (KeyValuePair<Renderer, Material> kv in saved)
            if (kv.Key != null) kv.Key.sharedMaterial = kv.Value;
        saved.Clear();
        ClearVisuals();
    }

    void ClearVisuals()
    {
        if (visualGroup == null) return;
        for (int i = visualGroup.transform.childCount - 1; i >= 0; i--)
            Destroy(visualGroup.transform.GetChild(i).gameObject);
    }

    void OnGUI()
    {
        ElementInfoStyle.SQ4Area = new Rect();
        if (!active) return;

        Rect area = new Rect(Mathf.Max(384, Screen.width - 472), 88, 460, Mathf.Min(470, Screen.height - 106));
        ElementInfoStyle.SQ4Area = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        bool close = ElementInfoStyle.Header("SQ4 carga movil", "PROTOTIPO  /  USUARIO -> PANEL -> VIGAS");
        scroll = GUILayout.BeginScrollView(scroll, false, false);
        ElementInfoStyle.Note("En ANALISIS, doble clic sobre una losa fija el panel. U cierra/abre. No reanaliza OpenSees: reparte una carga didactica sobre vigas tributarias.");
        if (pinnedPanel) ElementInfoStyle.Note("Panel fijado por doble clic sobre losa en modo ANALISIS.");
        ElementInfoStyle.Section("CARGA DEL USUARIO");
        GUILayout.Label("P_user = " + userLoad.ToString("F0") + " kN");
        float newLoad = GUILayout.HorizontalSlider(userLoad, 0f, 200f);
        if (Mathf.Abs(newLoad - userLoad) > 0.1f)
        {
            userLoad = Mathf.Round(newLoad);
            ComputeLoads();
            ApplyHighlight();
        }

        ElementInfoStyle.Section("PANEL / REGION");
        ElementInfoStyle.Pair("Detectado", panelName);
        ElementInfoStyle.Pair("Posicion", "x=" + (-panelPoint.x).ToString("F2") + " m, y=" + panelPoint.z.ToString("F2") + " m");
        ElementInfoStyle.Pair("Vigas receptoras", receivers.Count.ToString());
        ElementInfoStyle.Pair("Regla fisica", "carga puntual movil sobre losa");
        ElementInfoStyle.Pair("Modo reparto", repartoModo);
        ElementInfoStyle.Note("Arrastra el martillo rosado dentro de la losa para mover la carga; las flechas actualizan P_i en vivo.");

        ElementInfoStyle.Section("REPARTO A VIGAS");
        if (receivers.Count == 0)
        {
            ElementInfoStyle.Note("Sin vigas tributarias asociadas al panel detectado.");
        }
        else
        {
            ElementInfoStyle.Row(new[] { "Viga", "Borde", "Sol[m]", "w", "P[kN]" }, new[] { 0.7f, 0.8f, 0.7f, 0.7f, 0.9f }, true);
            double sum = 0.0;
            foreach (Receiver r in receivers)
            {
                sum += r.load;
                string solape = r.overlap > 0.001f ? r.overlap.ToString("F2") : r.distance.ToString("F2");
                ElementInfoStyle.Row(new[] { r.beamId.ToString(), r.edge, solape, r.weight.ToString("F2"), r.load.ToString("F1") },
                                     new[] { 0.7f, 0.8f, 0.7f, 0.7f, 0.9f });
            }
            ElementInfoStyle.Pair("Σ asignada", sum.ToString("F1") + " kN");
            ElementInfoStyle.Pair("Error conserv.", Math.Abs(sum - userLoad).ToString("F4") + " kN");
            ElementInfoStyle.Note("Conservacion: ΣP_i = P_user. Visual: losa amarilla, vigas receptoras, punto de aplicacion, lineas y flechas proporcionales a P_i.");
        }
        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);

        if (close) SetActive(false);
    }

    void OnDestroy()
    {
        ClearHighlight();
        if (loadMat != null) Destroy(loadMat);
        if (visualMat != null) Destroy(visualMat);
        if (hammerMat != null) Destroy(hammerMat);
        if (lineMat != null) Destroy(lineMat);
    }
}
