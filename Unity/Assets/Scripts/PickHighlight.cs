using System;
using System.Collections.Generic;
using System.Text;
using UnityEngine;

// Hover magenta + doble clic en modo analisis, igual que el visor HTML:
// - Hover: primero el "palito" mas cercano al cursor (distancia en pantalla,
//   ~12px); si no hay palito, raycast fino sobre solidos saltando las lozas.
//   Se resaltan el palito Y su solido (mapa solidForElem del HTML).
// - Doble clic: viga/beam -> reporte con fuerzas LOCALES + DEF + tributarias;
//   columna/muro -> curva P-M de capacidad + punto de demanda (drawPM).
public class PickHighlight : MonoBehaviour
{
    EdificioLoader loader;
    AnalysisMode am;
    Camera cam;
    CameraController ctrl;

    Material magentaMat;

    // elementoId -> renderers solidos (para resaltar junto al palito).
    Dictionary<int, List<Renderer>> solidRenders = new Dictionary<int, List<Renderer>>();

    // hover actual
    int hoverElem = -1;
    int hoverTubeIdx = -1;
    int palitoVersion = -1;
    Dictionary<Renderer, Material> savedMats = new Dictionary<Renderer, Material>();

    // doble clic
    float lastClickTime = -10f;
    Vector2 lastClickPos;

    // reporte abierto (-1 ninguno, 0 viga, 1 P-M)
    int reportKind = -1;
    int reportId;
    string reportCaso = "";
    Vector2 reportScroll;

    public void Setup(EdificioLoader l, AnalysisMode mode)
    {
        loader = l;
        am = mode;
    }

    void Start()
    {
        cam = Camera.main;
        if (cam != null) ctrl = cam.GetComponent<CameraController>();
        BuildSolidMap();
    }

    void BuildSolidMap()
    {
        solidRenders.Clear();
        if (loader == null || loader.ElementsGroup == null) return;
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>())
        {
            Renderer r = tag.GetComponent<Renderer>();
            if (r == null) continue;
            List<Renderer> list;
            if (!solidRenders.TryGetValue(tag.elementId, out list))
            {
                list = new List<Renderer>();
                solidRenders[tag.elementId] = list;
            }
            list.Add(r);
        }
    }

    void Update()
    {
        if (loader == null || am == null) return;
        DetectDoubleClick();
        UpdateHover();
    }

    void UpdateHover()
    {
        if (cam == null) cam = Camera.main;
        if (cam == null) return;

        if (ElementInfoStyle.PointerOverPanel) { ClearHover(); return; }

        bool busy;
        if (ctrl != null) busy = ctrl.Busy;
        else busy = Input.GetMouseButton(0) || Input.GetMouseButton(1) ||
                   Mathf.Abs(Input.GetAxis("Mouse ScrollWheel")) > 0.001f;
        if (busy) { ClearHover(); return; }

        int id, tubeIdx;
        if (am.Active)
        {
            PalitoAt(Input.mousePosition, out id, out tubeIdx);
            if (id < 0) { id = RaycastSolid(Input.mousePosition); tubeIdx = -1; }
        }
        else
        {
            id = RaycastSolid(Input.mousePosition);
            tubeIdx = -1;
        }

        // Rebuild del modo analisis (caso/vista/reacciones): los palitos cambiaron.
        if (am.Active && am.Palitos.Count != palitoVersion)
        {
            palitoVersion = am.Palitos.Count;
            ClearHover();
        }

        if (id == hoverElem && tubeIdx == hoverTubeIdx) return;
        ClearHover();
        ApplyHover(id, tubeIdx);
    }

    void ApplyHover(int id, int tubeIdx)
    {
        if (id < 0) return;
        hoverElem = id;
        hoverTubeIdx = tubeIdx;

        List<Renderer> list;
        if (solidRenders.TryGetValue(id, out list))
            foreach (Renderer r in list)
                if (r != null) PaintMagenta(r);

        if (tubeIdx >= 0 && am != null && am.Drew != null &&
            tubeIdx < am.Drew.Count && am.Drew[tubeIdx] != null)
        {
            Renderer r = am.Drew[tubeIdx].GetComponent<Renderer>();
            if (r != null) PaintMagenta(r);
        }
    }

    void PaintMagenta(Renderer r)
    {
        if (savedMats.ContainsKey(r)) return;
        savedMats[r] = r.sharedMaterial;
        r.sharedMaterial = Magenta();
    }

    Material Magenta()
    {
        if (magentaMat != null) return magentaMat;
        Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
        if (unlit == null) unlit = Shader.Find("Unlit/Color");
        magentaMat = new Material(unlit != null ? unlit : Shader.Find("Standard"));
        magentaMat.color = new Color(1f, 0f, 1f, 1f); // #ff00ff
        return magentaMat;
    }

    void ClearHover()
    {
        foreach (KeyValuePair<Renderer, Material> kvp in savedMats)
            if (kvp.Key != null) kvp.Key.sharedMaterial = kvp.Value;
        savedMats.Clear();
        hoverElem = -1;
        hoverTubeIdx = -1;
    }

    // Palito mas cercano al cursor (distancia en pantalla al segmento proyectado).
    // MISMA logica que palitoAt() del HTML (umbral 12 px).
    bool PalitoAt(Vector2 mouse, out int id, out int tubeIdx)
    {
        id = -1;
        tubeIdx = -1;
        if (am == null || am.Palitos.Count == 0 || cam == null) return false;
        int best = -1;
        float bestDist = 12f;
        for (int i = 0; i < am.Palitos.Count; i++)
        {
            AnalysisMode.Palito p = am.Palitos[i];
            Vector3 s0 = cam.WorldToScreenPoint(p.p0);
            Vector3 s1 = cam.WorldToScreenPoint(p.p1);
            if (s0.z < 0f || s1.z < 0f) continue;
            float dx = s1.x - s0.x, dy = s1.y - s0.y;
            float ll = dx * dx + dy * dy;
            float t = ll > 0f ? ((mouse.x - s0.x) * dx + (mouse.y - s0.y) * dy) / ll : 0f;
            t = Mathf.Clamp01(t);
            float px = s0.x + t * dx, py = s0.y + t * dy;
            float d = Vector2.Distance(mouse, new Vector2(px, py));
            if (d < bestDist) { bestDist = d; best = i; }
        }
        if (best < 0) return false;
        id = am.Palitos[best].elementId;
        tubeIdx = best;
        return true;
    }

    // Raycast fino sobre solidos: toma el primer elemento NO-loza (el rayo las
    // atraviesa), y si no hay ninguno, la loza mas cercana (mismo orden que HTML).
    int RaycastSolid(Vector2 mouse)
    {
        if (cam == null) return -1;
        Ray ray = cam.ScreenPointToRay(mouse);
        RaycastHit[] hits = Physics.RaycastAll(ray, 1000f);
        if (hits.Length == 0) return -1;
        Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        int first = -1;
        foreach (RaycastHit h in hits)
        {
            ElementTag t = h.collider.GetComponentInParent<ElementTag>();
            if (t == null) continue;
            if (first < 0) first = t.elementId;
            if (t.type != "loza") return t.elementId;
        }
        return first;
    }

    ElementTag RaycastNearestTag(Vector2 mouse, out Vector3 hitPoint)
    {
        hitPoint = Vector3.zero;
        if (cam == null) return null;
        Ray ray = cam.ScreenPointToRay(mouse);
        RaycastHit[] hits = Physics.RaycastAll(ray, 1000f);
        if (hits.Length == 0) return null;
        Array.Sort(hits, (a, b) => a.distance.CompareTo(b.distance));
        foreach (RaycastHit h in hits)
        {
            ElementTag t = h.collider.GetComponentInParent<ElementTag>();
            if (t == null) continue;
            hitPoint = h.point;
            return t;
        }
        return null;
    }

    void DetectDoubleClick()
    {
        if (ElementInfoStyle.PointerOverPanel) return;
        Vector2 pos;
        bool pressed;
        if (Input.touchCount > 0)
        {
            pressed = Input.GetTouch(0).phase == TouchPhase.Began;
            pos = Input.GetTouch(0).position;
        }
        else
        {
            pressed = Input.GetMouseButtonDown(0);
            pos = Input.mousePosition;
        }
        if (!pressed) return;
        float now = Time.time;
        float dist = Vector2.Distance(pos, lastClickPos);
        bool dbl = (now - lastClickTime) < 0.35f && dist < 20f;
        lastClickTime = now;
        lastClickPos = pos;
        if (!dbl) return;
        if (!am.Active) return;

        Vector3 hitPoint;
        ElementTag nearest = RaycastNearestTag(pos, out hitPoint);
        if (nearest != null && nearest.type == "loza")
        {
            if (loader != null && loader.mobileLoadSQ4 != null)
                loader.mobileLoadSQ4.ShowPanel(nearest.elementId, hitPoint);
            reportKind = -1;
            ElementInfoStyle.AnalysisArea = new Rect();
            return;
        }

        int id, tubeIdx;
        if (!PalitoAt(pos, out id, out tubeIdx)) id = RaycastSolid(pos);
        if (id < 0) return;
        AnalysisMap.ElementInfo meta = AnalysisMap.Element(id);
        if (meta == null) return;

        reportKind = (meta.type == "beam_x" || meta.type == "beam_y") ? 0 : 1;
        reportId = id;
        reportCaso = am.Caso;
        reportScroll = Vector2.zero;
        ElementInfoStyle.AnalysisArea = ElementInfoStyle.PanelRect();
    }

    // ----------------------------- reporte -----------------------------

    void OnGUI()
    {
        DrawReport();
    }

    void DrawReport()
    {
        ElementInfoStyle.AnalysisArea = new Rect();
        if (reportKind < 0 || am == null || !am.Active || ElementInfoStyle.DataArea.width > 0) return;
        Rect area = ElementInfoStyle.PanelRect();
        ElementInfoStyle.AnalysisArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        AnalysisMap.ElementInfo meta = AnalysisMap.Element(reportId);
        string name = meta != null ? TipoNombre(meta.type) : "Elemento";
        bool close = ElementInfoStyle.Header(name + " · " + reportId,
            "ANÁLISIS  /  " + (reportKind == 0 ? "REPORTE DE FUERZAS" : "CAPACIDAD Y DEMANDA P-M"));
        reportCaso = am.Caso;
        ElementInfoStyle.Note("Caso del reporte: " + reportCaso);
        reportScroll = GUILayout.BeginScrollView(reportScroll, false, false);
        if (reportKind == 0) BeamReportContent(reportId, reportCaso);
        else if (reportKind == 1) PMContent(reportId, reportCaso);
        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);
        if (close) { reportKind = -1; ElementInfoStyle.AnalysisArea = new Rect(); }
    }

    void ElementProperties(AnalysisMap.ElementInfo meta)
    {
        ElementInfoStyle.Section("PROPIEDADES Y GEOMETRÍA");
        ElementInfoStyle.Pair("Material", MaterialNombre(meta.material));
        ElementInfoStyle.Pair("Sección", meta.section);
        ElementInfoStyle.Pair("Nodo i · " + meta.ni, PuntoEstructural(meta.ni));
        ElementInfoStyle.Pair("Nodo j · " + meta.nj, PuntoEstructural(meta.nj));
    }

    void EndTable(string[] i, string[] j, bool displacement)
    {
        float[] widths = { 1.2f, 1, 1 };
        ElementInfoStyle.Row(new[] { "Componente", "Extremo i", "Extremo j" }, widths, true);
        string[] names = { "N [kN]", "Vy [kN]", "Vz [kN]", "T [kN-m]", "My [kN-m]", "Mz [kN-m]", "DEF [mm]" };
        for (int k = 0; k < (displacement ? 7 : 6); k++)
            ElementInfoStyle.Row(new[] { names[k], i[k + 1], j[k + 1] }, widths);
    }

    void BeamReportContent(int id, string caso)
    {
        AnalysisMap.ElementInfo meta = AnalysisMap.Element(id);
        if (meta == null) { GUILayout.Label("Elemento id " + id + " no esta en el analisis."); return; }
        string tipo = TipoNombre(meta.type);

        ElementProperties(meta);

        AnalysisMap.EndForces f = AnalysisMap.Fuerzas(caso, id);
        double[] li = (f != null) ? f.li : null;
        double[] lj = (f != null) ? f.lj : null;
        double[] di = AnalysisMap.Desp(caso, meta.ni);
        double[] dj = AnalysisMap.Desp(caso, meta.nj);
        double defi = di != null && di.Length >= 3
            ? Math.Sqrt(di[0] * di[0] + di[2] * di[2] + di[1] * di[1]) * 1000 : double.NaN;
        double defj = dj != null && dj.Length >= 3
            ? Math.Sqrt(dj[0] * dj[0] + dj[2] * dj[2] + dj[1] * dj[1]) * 1000 : double.NaN;

        ElementInfoStyle.Section("FUERZAS LOCALES Y DESPLAZAMIENTOS");
        EndTable(MakeFila("i", li, defi), MakeFila("j", lj, defj), true);
        ElementInfoStyle.Note("Valores en modulo. N=axial, Vy/Vz=cortes, T=torsion, My/Mz=momentos de flexion · " +
                        "DEF=modulo del desplazamiento nodal.");

        AnalysisMap.TribuInfo t = AnalysisMap.Tributaria(id);
        if (t != null && t.aportes != null && t.aportes.Count > 0)
        {
            ElementInfoStyle.Section("CARGA DE LOSA · APORTES TRIBUTARIOS");
            DrawRow(new[] { "Losa", "Borde", "Tramo [m]", "A [m2]", "G [kN]" },
                    new float[] { 90, 60, 80, 60, 60 });
            foreach (object ap in t.aportes)
            {
                string losa = MiniJson.St(ap, "losa");
                string borde = MiniJson.St(ap, "borde");
                double[] tr = MiniJson.NumArrayValue(MiniJson.Get(ap, "tramo_m"));
                string tramo = (tr != null && tr.Length >= 1 ? tr[0].ToString("F1") : "-") + "..." +
                               (tr != null && tr.Length >= 2 ? tr[1].ToString("F1") : "-");
                DrawRow(new[] { losa, borde, tramo, MiniJson.Db(ap, "area_m2").ToString("F2"),
                                MiniJson.Db(ap, "W_G_kN").ToString("F1") },
                        new float[] { 90, 60, 80, 60, 60 });
            }
            GUILayout.Label("Totales: Σ A = " + t.area.ToString("F2") + " m2 · W_G = " + t.Wg.ToString("F1") +
                            " kN · W_Q = " + t.Wq.ToString("F1") + " kN");
        }
    }

    string[] MakeFila(string extr, double[] r, double def)
    {
        if (r == null || r.Length < 6)
            return new[] { extr, "(sin dato)", "", "", "", "", "", DefStr(def) };
        return new[]
        {
            extr,
            Abs1(r[0]), Abs1(r[1]), Abs1(r[2]), Abs1(r[3]), Abs1(r[4]), Abs1(r[5]),
            DefStr(def)
        };
    }

    static string Abs1(double v) { return Math.Abs(v).ToString("F1"); }

    static string DefStr(double v)
    {
        return double.IsNaN(v) ? "-" : v.ToString("F1");
    }

    void PMContent(int id, string caso)
    {
        AnalysisMap.ElementInfo meta = AnalysisMap.Element(id);
        if (meta == null) { GUILayout.Label("Elemento id " + id + " no esta en el analisis."); return; }
        string tipo = TipoNombre(meta.type);
        string sec = meta.section;

        ElementProperties(meta);
        ElementInfoStyle.Section("DIAGRAMA P-M");

        Dictionary<string, object> cur = CapacityCur(meta);
        if (cur == null)
        {
            GUILayout.Label("");
            GUILayout.Label(tipo + " seccion " + sec);
            GUILayout.Label("Curva P-M de capacidad no disponible para esta seccion.");
            return;
        }

        double[] P = MiniJson.NumArrayValue(MiniJson.Get(cur, "P"));
        double[] Mc = MiniJson.NumArrayValue(MiniJson.Get(cur, "M"));

        AnalysisMap.EndForces f = AnalysisMap.Fuerzas(caso, id);
        double Pd, Md;
        DemandaPM(f, meta, out Pd, out Md);

        Rect rc = GUILayoutUtility.GetRect(466, 240);
        double Mcap;
        Plot2D.DrawPMLab(rc, P, Mc, Pd, Md, caso, out Mcap);
        double pct = Mcap != 0 ? (Md / Mcap) * 100.0 : 0;
        string estado = Md <= Mcap ? "(dentro de la curva)" : "(FUERA de la curva / no cumple)";
        GUILayout.Space(6);
        ElementInfoStyle.Section("DEMANDA Y CAPACIDAD · " + caso);
        ElementInfoStyle.Pair("Demanda P", Pd.ToString("F1") + " kN");
        ElementInfoStyle.Pair("Demanda M", Md.ToString("F1") + " kN-m");
        ElementInfoStyle.Pair("M cap. a esa P", Mcap.ToString("F1") + " kN-m");
        ElementInfoStyle.Pair("Demanda / capacidad", pct.ToString("F1") + "%  " + estado);

        if (f != null && f.li != null && f.lj != null)
        {
            GUILayout.Space(6);
            ElementInfoStyle.Section("FUERZAS LOCALES · " + caso);
            ElementInfoStyle.Note("Valores en módulo · N, Vy, Vz en kN; T, My, Mz en kN-m.");
            EndTable(MakeFila("i", f.li, double.NaN), MakeFila("j", f.lj, double.NaN), false);
        }
    }

    void FilaFuerzas(string extr, double[] r)
    {
        if (r == null || r.Length < 6)
        {
            DrawRow(new[] { extr, "(sin dato)", "", "", "", "", "" },
                    new float[] { 40, 70, 70, 70, 74, 74, 74 });
            return;
        }
        DrawRow(new[] { extr, Abs1(r[0]), Abs1(r[1]), Abs1(r[2]), Abs1(r[3]), Abs1(r[4]), Abs1(r[5]) },
                new float[] { 40, 70, 70, 70, 74, 74, 74 });
    }

    // Criterio del visor: columna 70 usa su curva, luego borde, muros[sec],
    // luego '70x70'->columna, '30x356'->muro y steel[sec].
    Dictionary<string, object> CapacityCur(AnalysisMap.ElementInfo meta)
    {
        if (AnalysisMap.Capacidad == null) return null;
        Dictionary<string, object> C = AnalysisMap.Capacidad;
        if (meta.id == 70 && C.ContainsKey("columna_id70"))
        {
            Dictionary<string, object> d = MiniJson.AsDict(C["columna_id70"]);
            if (d != null) return d;
        }
        if (meta.borde && C.ContainsKey("columna_borde"))
        {
            Dictionary<string, object> d = MiniJson.AsDict(C["columna_borde"]);
            if (d != null) return d;
        }
        if (C.ContainsKey("muros"))
        {
            Dictionary<string, object> muros = MiniJson.AsDict(C["muros"]);
            if (muros != null)
            {
                object v;
                if (muros.TryGetValue(meta.section, out v))
                {
                    Dictionary<string, object> d = MiniJson.AsDict(v);
                    if (d != null) return d;
                }
            }
        }
        if (meta.section == "70x70" && C.ContainsKey("columna"))
        {
            Dictionary<string, object> d = MiniJson.AsDict(C["columna"]);
            if (d != null) return d;
        }
        if (meta.section == "30x356" && C.ContainsKey("muro"))
        {
            Dictionary<string, object> d = MiniJson.AsDict(C["muro"]);
            if (d != null) return d;
        }
        if (C.ContainsKey("steel"))
        {
            Dictionary<string, object> stl = MiniJson.AsDict(C["steel"]);
            if (stl != null)
            {
                object v;
                if (stl.TryGetValue(meta.section, out v))
                {
                    Dictionary<string, object> d = MiniJson.AsDict(v);
                    if (d != null) return d;
                }
            }
        }
        return null;
    }

    // demandaColumnaMuro() del HTML: extremo de mayor |M|, P = axial proyectado
    // sobre el eje del elemento, M = flexion TRANSVERSAL al eje. Las vistas y
    // fuerzas usan (x, y=altura, z) = OpenSees (X, h, Y) -> indice (0,2,1).
    void DemandaPM(AnalysisMap.EndForces f, AnalysisMap.ElementInfo meta, out double P, out double M)
    {
        P = 0;
        M = 0;
        if (f == null || meta == null) return;
        double[] ci, cj;
        if (!AnalysisMap.StructCoords.TryGetValue(meta.ni.ToString(), out ci) ||
            !AnalysisMap.StructCoords.TryGetValue(meta.nj.ToString(), out cj) ||
            ci.Length < 3 || cj.Length < 3) return;
        double dx = cj[0] - ci[0];   // x estructural
        double dy = cj[2] - ci[2];   // altura
        double dz = cj[1] - ci[1];   // y en planta
        double L = Math.Sqrt(dx * dx + dy * dy + dz * dz);
        if (L < 1e-9) return;
        double ux = dx / L, uy = dy / L, uz = dz / L;

        double[] fg = ExtremoMayor(f);
        double fvx = fg[0], fvy = fg[2], fvz = fg[1];
        P = Math.Abs(fvx * ux + fvy * uy + fvz * uz);

        double Mvx = fg[3], Mvy = fg[5], Mvz = fg[4];
        double mt = Mvx * ux + Mvy * uy + Mvz * uz;
        double tx = Mvx - mt * ux, ty = Mvy - mt * uy, tz = Mvz - mt * uz;
        M = Math.Sqrt(tx * tx + ty * ty + tz * tz);
    }

    static double[] ExtremoMayor(AnalysisMap.EndForces f)
    {
        double[] gi = (f.gi != null && f.gi.Length >= 6) ? f.gi : new double[6];
        double[] gj = (f.gj != null && f.gj.Length >= 6) ? f.gj : gi;
        double mi = Mag3(gi, 3), mj = Mag3(gj, 3);
        return mi >= mj ? gi : gj;
    }

    static double Mag3(double[] v, int o)
    {
        return Math.Sqrt(v[o] * v[o] + v[o + 1] * v[o + 1] + v[o + 2] * v[o + 2]);
    }

    // ----------------------------- helpers -----------------------------

    string PuntoEstructural(int tag)
    {
        double[] c;
        if (AnalysisMap.StructCoords.TryGetValue(tag.ToString(), out c) && c.Length >= 3)
            return "(" + c[0].ToString("F2") + ", " + c[1].ToString("F2") + ", h=" + c[2].ToString("F2") + " m)";
        return "(?)";
    }

    static string TipoNombre(string t)
    {
        return t == "column" ? "Columna" :
               t == "wall" ? "Muro" :
               t == "steel_column" ? "Columna MET" :
               t == "steel_beam" ? "Viga MET" :
               t == "beam_x" || t == "beam_y" ? "Viga" : t;
    }

    static string MaterialNombre(string m)
    {
        return m == "A240ES" ? "A240ES (acero estructural)" : "HA35 (hormigon armado)";
    }

    void DrawRow(string[] cells, float[] widths, bool mono = false)
    {
        ElementInfoStyle.Row(cells, widths, cells.Length > 0 && cells[0] == "Losa");
    }

    void OnDestroy()
    {
        ClearHover();
        if (magentaMat != null) Destroy(magentaMat);
    }
}
