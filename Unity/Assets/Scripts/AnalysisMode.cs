using UnityEngine;
using System.Collections.Generic;
using System.Linq;

// MODO ANALISIS (limamente igual al visor HTML): activa con TAB (o boton).
// - Deformada: tubos por elemento con desplazamiento nodal escalado (S.factor).
// - M / N / V: tubos coloreados con mapa calor, escala por percentil 90.
// - Reacciones: esferas en apoyos coloreadas por magnitud (checkbox).
// Datos: analysis_map.json (mismos que ANALYSIS del visor); la logica de
// colores y geometria replica 1:1 buildAnalysis()/extremoMayor()/paintReactions().
public class AnalysisMode : MonoBehaviour
{
    public KeyCode toggleKey = KeyCode.Tab;
    public KeyCode[] caseKeys = { KeyCode.Alpha1, KeyCode.Alpha2, KeyCode.Alpha3, KeyCode.Alpha4, KeyCode.Alpha5 };
    public bool enabledByDefault = false;

    // Referencia global (creada por EdificioLoader) para que el HUD, el panel
    // DATOS y el inspector sepan en que modo esta el visor.
    public static AnalysisMode Current;

    // Un "palito" del modo analisis: segmento de un elemento (con su id) en el
    // mundo, para hover/doble-clic por distancia en pantalla (como el HTML).
    public class Palito
    {
        public int elementId;
        public Vector3 p0;
        public Vector3 p1;
    }

    string[] vistas = { "deformada", "M", "N", "V" };
    int vistaIdx = 0;
    string caso = "COMBO";
    int factor = 120;
    bool pintarReac = false;
    bool active = false;

    GameObject group;
    List<GameObject> drew = new List<GameObject>();
    public readonly List<Palito> Palitos = new List<Palito>();
    int lastPalitoId;

    // Acceso para el PickHighlight: el tubo del hover esta en el MISMO indice
    // que su Palito (ambos se anaden en cada DrawTube).
    public List<GameObject> Drew { get { return drew; } }

    // escala del colormap (percentil 90) y maximo desplazamiento
    float scaleVmax = 1f;
    float scaleDmax = 1f;

    GameObject wallGroup;      // se oculta en analisis (como el visor)

    void Start()
    {
        Current = this;
        group = new GameObject("GrupoAnalisis");
        group.transform.SetParent(transform, false);
        active = enabledByDefault;
        FindWallGroup();
        if (active) Rebuild();
    }

    void FindWallGroup()
    {
        // El grupo de muros lo crea EdificioLoader (elementos mundo).
        Transform t = transform.parent;
        while (t != null)
        {
            foreach (Transform c in t)
            {
                if (c.name == "Muros" || c.name == "Muros (1)")
                {
                    wallGroup = c.gameObject;
                    return;
                }
            }
            t = t.parent;
        }
    }

    void Update()
    {
        if (Input.GetKeyDown(toggleKey)) ToggleMode();
        for (int i = 0; i < caseKeys.Length; i++)
        {
            if (Input.GetKeyDown(caseKeys[i]))
            {
                string[] cases = { "G", "Q", "EX", "EY", "COMBO" };
                if (i < cases.Length) SetCaso(cases[i]);
            }
        }
        if (active)
        {
            if (Input.GetKeyDown(KeyCode.M)) SetVista(1);
            if (Input.GetKeyDown(KeyCode.N)) SetVista(2);
            if (Input.GetKeyDown(KeyCode.V)) SetVista(3);
            if (Input.GetKeyDown(KeyCode.D)) SetVista(0);
            if (Input.GetKeyDown(KeyCode.Equals) || Input.GetKeyDown(KeyCode.KeypadPlus)) factor = Mathf.Min(600, factor + 10);
            if (Input.GetKeyDown(KeyCode.Minus) || Input.GetKeyDown(KeyCode.KeypadMinus)) factor = Mathf.Max(10, factor - 10);
            if (Input.GetKeyDown(KeyCode.R)) pintarReac = !pintarReac;
        }
    }

    public string Caso { get { return caso; } }
    public bool Active { get { return active; } }
    public bool PintarReac { get { return pintarReac; } }

    public void SetPintarReac(bool v)
    {
        if (pintarReac == v) return;
        pintarReac = v;
        if (active) Rebuild();
    }

    public void ToggleMode()
    {
        active = !active;
        if (active) Rebuild();
        else ClearDrew();
    }

    public void SetCaso(string c)
    {
        caso = c;
        if (active) Rebuild();
    }

    void SetVista(int idx)
    {
        vistaIdx = Mathf.Clamp(idx, 0, vistas.Length - 1);
        if (active) Rebuild();
    }

    void ClearDrew()
    {
        foreach (GameObject g in drew)
            if (g != null)
            {
                Renderer renderer = g.GetComponent<Renderer>();
                if (renderer != null && renderer.sharedMaterial != null) Destroy(renderer.sharedMaterial);
                Destroy(g);
            }
        drew.Clear();
        Palitos.Clear();
        if (wallGroup != null) wallGroup.SetActive(true);
    }

    void OnDestroy()
    {
        ClearDrew();
        if (group != null) Destroy(group);
    }

    // Aplica el mismo mapeo de color del visor: 0=azul, 0.5=verde, 1=rojo.
    public static Color Heat(float t)
    {
        t = Mathf.Clamp01(t);
        if (t < 0.33f) return new Color(0f, t / 0.33f, 1f);
        if (t < 0.66f) return new Color((t - 0.33f) / 0.33f, 1f, 1f - (t - 0.33f) / 0.33f);
        return new Color(1f, 1f - (t - 0.66f) / 0.34f, 0f);
    }

    void Rebuild()
    {
        ClearDrew();
        if (!AnalysisMap.Loaded) return;

        // ocultar muralla solida -> se ven los tubos (igual que el visor)
        if (wallGroup != null) wallGroup.SetActive(false);

        var D = AnalysisMap.Disp.ContainsKey(caso) ? AnalysisMap.Disp[caso] : new Dictionary<int, double[]>();
        var F = AnalysisMap.Forces.ContainsKey(caso) ? AnalysisMap.Forces[caso] : null;

        // vmax / dmax igual que el HTML
        float dmax = 0f;
        foreach (KeyValuePair<int, double[]> kv in D)
        {
            double[] du = kv.Value;
            if (du == null || du.Length < 3) continue;
            float dL = Mathf.Sqrt((float)(du[0] * du[0] + du[2] * du[2] + du[1] * du[1]));
            if (dL > dmax) dmax = dL;
        }
        Dictionary<int, float> values = new Dictionary<int, float>();
        float vmax = 0f;
        foreach (KeyValuePair<int, AnalysisMap.ElementInfo> kv in AnalysisMap.ElementsByTag)
        {
            AnalysisMap.ElementInfo meta = kv.Value;
            if (meta.ni <= 0) continue;
            float L = Length(meta);
            if (L < 1e-6f) continue;
            Vector3 u = Dir(meta);
            AnalysisMap.EndForces f;
            float v = 0f;
            if (F != null && F.TryGetValue(meta.id, out f))
            {
                double[] fA = ExtremoMayor(f);
                Vector3 fw = FuerzaUnity(fA);
                switch (vistaIdx)
                {
                    case 1: // M
                        v = Mathf.Sqrt((float)(fA[3] * fA[3] + fA[4] * fA[4] + fA[5] * fA[5]));
                        break;
                    case 2: // N
                        v = Mathf.Abs(Vector3.Dot(fw, u));
                        break;
                    case 3: // V
                        {
                            float ax = Vector3.Dot(fw, u);
                            Vector3 t = fw - u * ax;
                            v = t.magnitude;
                            break;
                        }
                }
            }
            values[meta.id] = v;
            if (v > vmax) vmax = v;
        }
        if (vmax < 1e-12f) vmax = 1f;
        // percentil 90 sobre valores > 0
        List<float> nz = values.Values.Where(x => x > 0f).ToList();
        nz.Sort();
        float sat = 0f;
        if (nz.Count > 0) sat = nz[Mathf.Min(nz.Count - 1, Mathf.FloorToInt(nz.Count * 0.90f))];
        if (sat <= 0f) sat = vmax;
        scaleVmax = sat;
        scaleDmax = dmax;

        foreach (KeyValuePair<int, AnalysisMap.ElementInfo> kv in AnalysisMap.ElementsByTag)
        {
            AnalysisMap.ElementInfo meta = kv.Value;
            if (meta.ni <= 0) continue;
            float L = Length(meta);
            if (L < 1e-6f) continue;
            Vector3 u = Dir(meta);
            if (!F.ContainsKey(meta.id)) continue;

            float fac = (vistaIdx == 0) ? factor : 0f;

            // segmentos deformados (beam_fractions o directo)
            List<Vector3[]> segs = Segmentos(meta, D, fac);

            Color color;
            if (vistaIdx == 0)
            {
                double[] du0;
                D.TryGetValue(meta.ni, out du0);
                float des = du0 != null && du0.Length >= 3
                    ? Mathf.Sqrt((float)(du0[0] * du0[0] + du0[2] * du0[2] + du0[1] * du0[1]))
                    : 0f;
                float denom = Mathf.Max(scaleDmax, 1e-9f);
                color = Heat(Mathf.Min(1f, des / (denom * 0.85f)));
            }
            else
            {
                color = Heat(Mathf.Min(1f, values[meta.id] / scaleVmax));
            }

            foreach (Vector3[] seg in segs)
            {
                Vector3 p0 = seg[0], p1 = seg[1];
                float sl = (p1 - p0).magnitude;
                if (sl < 1e-9f) continue;
                lastPalitoId = meta.id;
                DrawTube(p0, p1, sl, color);
            }
        }
        if (pintarReac) PaintReactions();
        if (vistaIdx == 0) FrameDeformada();
    }

    // Recuadra la camara sobre estructura + palitos deformados para que la
    // deformada nunca se salga del encuadre al subir la escala.
    void FrameDeformada()
    {
        if (Camera.main == null) return;
        CameraController ctrl = Camera.main.GetComponent<CameraController>();
        if (ctrl == null) return;

        Bounds b = new Bounds();
        bool any = false;
        foreach (KeyValuePair<string, Vector3> kv in AnalysisMap.NodeCoords)
        {
            if (!any) { b = new Bounds(kv.Value, Vector3.zero); any = true; }
            else b.Encapsulate(kv.Value);
        }
        foreach (Palito p in Palitos)
        {
            b.Encapsulate(p.p0);
            b.Encapsulate(p.p1);
        }
        if (!any && Palitos.Count == 0) return;
        b.Expand(b.size.magnitude * 0.12f);
        ctrl.FrameBounds(b);
    }

    // posicion mundial del nodo FE (node_coords en analysis_map).
    Vector3 NodoPos(int tag)
    {
        Vector3 v;
        if (AnalysisMap.NodeCoords.TryGetValue(tag.ToString(), out v)) return v;
        return Vector3.zero;
    }

    // largo del elemento en unidades viewer/mundo.
    float Length(AnalysisMap.ElementInfo meta)
    {
        return (NodoPos(meta.nj) - NodoPos(meta.ni)).magnitude;
    }

    // direccion unitaria en viewer (x, altura, y) -> mundo Unity (x, y, z).
    Vector3 Dir(AnalysisMap.ElementInfo meta)
    {
        Vector3 d = NodoPos(meta.nj) - NodoPos(meta.ni);
        return d.magnitude < 1e-9f ? Vector3.up : d.normalized;
    }

    // Fuerza global en coordenadas Unity (x-espejo, altura, y-plano).
    Vector3 FuerzaUnity(double[] f)
    {
        return new Vector3(-(float)f[0], (float)f[2], (float)f[1]);
    }

    // Extremo de mayor momento (igual que extremoMayor() del visor).
    static double[] ExtremoMayor(AnalysisMap.EndForces f)
    {
        double[] gi = f.gi != null && f.gi.Length >= 6 ? f.gi : new double[6];
        double[] gj = f.gj != null && f.gj.Length >= 6 ? f.gj : gi;
        double mi = Mag3(gi, 3);
        double mj = Mag3(gj, 3);
        return mi >= mj ? gi : gj;
    }

    static double Mag3(double[] v, int o)
    {
        return System.Math.Sqrt(v[o] * v[o] + v[o + 1] * v[o + 1] + v[o + 2] * v[o + 2]);
    }

    // Segmentos a dibujar: beam_fractions (subdivisiones FE) o un segmento
    // directo. Con desplazamiento nodal si fac > 0 (deformada).
    List<Vector3[]> Segmentos(AnalysisMap.ElementInfo meta, Dictionary<int, double[]> D, float fac)
    {
        List<Vector3[]> segs = new List<Vector3[]>();
        List<KeyValuePair<int, int>> fracs = null;
        AnalysisMap.BeamFractions.TryGetValue(meta.id, out fracs);
        if (fracs != null && fracs.Count > 0 && fac > 0)
        {
            foreach (KeyValuePair<int, int> fr in fracs)
            {
                double[] di, dj;
                D.TryGetValue(fr.Key, out di);
                D.TryGetValue(fr.Value, out dj);
                Vector3 p0 = NodoPos(fr.Key);
                Vector3 p1 = NodoPos(fr.Value);
                if (di != null && di.Length >= 3) p0 += Deformar(di, fac);
                if (dj != null && dj.Length >= 3) p1 += Deformar(dj, fac);
                segs.Add(new[] { p0, p1 });
            }
            return segs;
        }
        Vector3 a = NodoPos(meta.ni);
        Vector3 b = NodoPos(meta.nj);
        if (fac > 0)
        {
            double[] di0, dj0;
            D.TryGetValue(meta.ni, out di0);
            D.TryGetValue(meta.nj, out dj0);
            if (di0 != null && di0.Length >= 3) a += Deformar(di0, fac);
            if (dj0 != null && dj0.Length >= 3) b += Deformar(dj0, fac);
        }
        segs.Add(new[] { a, b });
        return segs;
    }

    // Traslacion por desplazamiento nodal (OpenSees X,Y-plano,Z-altura)
    // a Unity (-X, Z, Y) con factor visual.
    Vector3 Deformar(double[] d, float fac)
    {
        return new Vector3(-(float)d[0], (float)d[2], (float)d[1]) * fac;
    }

    void DrawTube(Vector3 p0, Vector3 p1, float sl, Color color)
    {
        GameObject tube = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
        tube.transform.parent = group.transform;
        tube.transform.position = (p0 + p1) * 0.5f;
        tube.transform.localScale = new Vector3(0.28f, sl / 2f, 0.28f); // radio 0.14
        Vector3 d = p1 - p0;
        if (d.magnitude > 1e-9f)
            tube.transform.rotation = Quaternion.FromToRotation(Vector3.up, d.normalized);
        Renderer r = tube.GetComponent<Renderer>();
        r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        r.receiveShadows = false;
        Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
        if (unlit == null) unlit = Shader.Find("Unlit/Color");
        Material m = new Material(unlit != null ? unlit : Shader.Find("Standard"));
        m.color = color;
        r.sharedMaterial = m;
        Destroy(tube.GetComponent<Collider>());
        tube.name = "Tube_" + drew.Count;
        drew.Add(tube);

        // Registro para hover/doble-clic por distancia en pantalla (como el HTML).
        Palitos.Add(new Palito { elementId = lastPalitoId, p0 = p0, p1 = p1 });
    }

    // Reacciones en apoyos: esfera coloreada por magnitud de reaccion.
    void PaintReactions()
    {
        if (!AnalysisMap.Reacciones.ContainsKey(caso)) return;
        var rmap = AnalysisMap.Reacciones[caso];
        float maxR = 0f;
        foreach (KeyValuePair<int, double[]> kv in rmap)
        {
            if (kv.Value == null || kv.Value.Length < 3) continue;
            float R = Mathf.Sqrt((float)(kv.Value[0] * kv.Value[0] + kv.Value[1] * kv.Value[1] + kv.Value[2] * kv.Value[2]));
            if (R > maxR) maxR = R;
        }
        if (maxR < 1e-9f) return;
        foreach (KeyValuePair<int, double[]> kv in rmap)
        {
            Vector3 c = NodoPos(kv.Key);
            if (!AnalysisMap.NodeCoords.ContainsKey(kv.Key.ToString())) continue;
            float R = Mathf.Sqrt((float)(kv.Value[0] * kv.Value[0] + kv.Value[1] * kv.Value[1] + kv.Value[2] * kv.Value[2]));
            Color col = Heat(R / maxR);
            GameObject sp = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sp.transform.parent = group.transform;
            sp.transform.position = c;
            sp.transform.localScale = Vector3.one * 0.7f;
            Renderer r = sp.GetComponent<Renderer>();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            r.receiveShadows = false;
            Shader unlit = Shader.Find("Universal Render Pipeline/Unlit");
            if (unlit == null) unlit = Shader.Find("Unlit/Color");
            Material m = new Material(unlit != null ? unlit : Shader.Find("Standard"));
            m.color = col;
            r.sharedMaterial = m;
            Destroy(sp.GetComponent<Collider>());
            drew.Add(sp);
        }
    }

    // ----------------------------- HUD (IMGUI) -----------------------------
    Vector2 controlsScroll;

    void OnGUI()
    {
        ElementInfoStyle.ControlsArea = new Rect();

        // El boton de modo (VISUALIZACION/ANALISIS + DATOS) lo dibuja ViewerHud
        // en la barra superior central, igual que el visor HTML (modebar).
        if (!active) return;

        // Panel de control (izquierda, bajo el HUD de info; la leyenda de capas
        // del ViewerHud ocupa abajo-izquierda).
        Rect area = new Rect(12, 88, 360, Mathf.Min(348, Screen.height - 100));
        ElementInfoStyle.ControlsArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        GUILayout.Label("Análisis estructural", new GUIStyle(GUI.skin.label) { fontSize = 22, fontStyle = FontStyle.Bold });
        controlsScroll = GUILayout.BeginScrollView(controlsScroll, false, false);
        ElementInfoStyle.Section("CASO DE CARGA · " + caso);
        GUILayout.BeginHorizontal();
        foreach (string cs in new[] { "G", "Q", "EX", "EY", "COMBO" })
        {
            if (ElementInfoStyle.Choice(caso == cs, cs) && caso != cs)
            {
                SetCaso(cs);
            }
        }
        GUILayout.EndHorizontal();

        ElementInfoStyle.Section("SUPERPOSICIÓN · FACTORES λ");
        if (AnalysisMap.Loaded)
        {
            double[] weights = (double[])AnalysisMap.Lambdas.Clone();
            bool changed = false;
            for (int i = 0; i < 4; i++)
            {
                GUILayout.BeginHorizontal();
                GUILayout.Label(AnalysisMap.BaseCases[i] + "  " + weights[i].ToString("F2"), GUILayout.Width(85));
                float value = GUILayout.HorizontalSlider((float)weights[i], i < 2 ? 0f : -2f, 2f);
                GUILayout.EndHorizontal();
                double rounded = System.Math.Round(value, 2);
                if (System.Math.Abs(rounded - weights[i]) > 0.00001) { weights[i] = rounded; changed = true; }
            }
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Cero")) { weights = new double[4]; changed = true; }
            if (GUILayout.Button("G + Q")) { weights = new double[] { 1, 1, 0, 0 }; changed = true; }
            if (GUILayout.Button("1.2 / 1 / 1.4 / 1.4")) { weights = new double[] { 1.2, 1, 1.4, 1.4 }; changed = true; }
            GUILayout.EndHorizontal();
            if (changed && AnalysisMap.TryCombine(weights)) SetCaso("COMBO");
            if (AnalysisMap.CombinationError != null) ElementInfoStyle.Note(AnalysisMap.CombinationError);
            ElementInfoStyle.Note("λ cambia la combinación al instante, sin reanálisis.\nSección o apoyo: reanalizar los cuatro casos y reiniciar Play.");
        }

        ElementInfoStyle.Section("VISTA DEL MODELO");
        GUILayout.BeginHorizontal();
        for (int i = 0; i < vistas.Length; i++)
        {
            bool sel = vistaIdx == i;
            bool click = ElementInfoStyle.Choice(sel,
                vistas[i] == "deformada" ? "DEF" : vistas[i].ToUpper());
            if (click != sel) SetVista(i);
        }
        GUILayout.EndHorizontal();

        if (vistaIdx == 0)
        {
            GUILayout.Label("Escala deformada: x" + factor);
            factor = (int)GUILayout.HorizontalSlider(factor, 10, 600);
            if (Event.current.type == EventType.Repaint && !Mathf.Approximately(0f, 0f))
            {
                // slider cambio -> reconstruir (solo si el valor cambio y OCURRIO)
            }
            if (factor != previousFactor)
            {
                previousFactor = factor;
                Rebuild();
            }
        }
        bool reacPrev = pintarReac;
        pintarReac = ElementInfoStyle.Choice(pintarReac, "Reacciones 3D · " + (pintarReac ? "visibles" : "ocultas"));
        if (pintarReac != reacPrev) Rebuild();

        GUILayout.Space(6);
        ElementInfoStyle.Note("1–5: caso · M/N/V/DEF: vista\nR: reacciones · +/−: escala · TAB: modo");
        ElementInfoStyle.Note("Doble clic: reporte de viga o curva P-M de columna / muro.");
        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);

        // Barra de colores (abajo derecha, fuera de la ficha abierta).
        DrawLegend();
    }

    int previousFactor = -1;

    void DrawLegend()
    {
        bool isDef = vistaIdx == 0;
        string unid = isDef ? "mm" : (vistaIdx == 1 ? "kN-m" : "kN");
        float mx = isDef ? scaleDmax : scaleVmax;
        if (mx <= 0) return;
        string title;
        if (vistaIdx == 1) title = "Momento M (caso " + caso + ", p90)";
        else if (vistaIdx == 2) title = "Axial N (caso " + caso + ", p90)";
        else if (vistaIdx == 3) title = "Corte V (caso " + caso + ", p90)";
        else title = "Desplazamiento max " + (scaleDmax * 1000f).ToString("F1") + " mm (x" + factor + ")";
        float lim = isDef ? mx * 1000f : mx;
        const int N = 6;
        float boxW = 60f, boxH = 24f;
        // Abajo-derecha (la leyenda de capas del ViewerHud ocupa abajo-izquierda).
        float x0 = Screen.width - 8f - boxW - 8f - 200f, y0 = Screen.height - (N * boxH + 30f);
        Rect report = ElementInfoStyle.DataArea.width > 0 ? ElementInfoStyle.DataArea : ElementInfoStyle.AnalysisArea;
        bool reportOpen = report.width > 0;
        if (reportOpen)
        {
            // Reserve the report's full width, including a gap to the legend.
            x0 = ElementInfoStyle.PanelRect().xMin - 16f - (boxW + 4f + 200f);
            // In a narrow Game view, avoid covering either the report or layer list.
            if (x0 < Mathf.Max(280f, ElementInfoStyle.LayerArea.xMax + 16f)) return;
        }
        Color previousColor = GUI.color;
        GUI.color = new Color(0.075f, 0.10f, 0.14f, 1f);
        GUI.DrawTexture(new Rect(x0 - 12, y0 - 56, boxW + 4 + 200 + 24, N * boxH + 68), WhiteTex());
        GUI.color = previousColor;
        var ts = new GUIStyle(GUI.skin.label) { fontSize = 16, wordWrap = true, alignment = TextAnchor.LowerLeft };
        ts.normal.textColor = new Color(0.91f, 0.94f, 0.98f);
        GUI.Label(new Rect(x0, y0 - 48, boxW + 4f + 200f, 40f), title, ts);
        for (int i = N - 1; i >= 0; i--)
        {
            float t0 = i / (float)N, t1 = (i + 1) / (float)N;
            Color col = Heat(t0);
            // GUI.Box usaria la textura gris del skin: dibujamos una textura
            // blanca tintada para que el color del mapa calor se vea real.
            GUI.color = col;
            GUI.DrawTexture(new Rect(x0, y0 + (N - 1 - i) * boxH, boxW, boxH), WhiteTex());
            GUI.color = Color.white;
            string v0 = Fmt(lim * t0), v1 = Fmt(lim * t1);
            GUI.Label(new Rect(x0 + boxW + 4, y0 + (N - 1 - i) * boxH, 200, boxH),
                      v0 + " - " + v1 + " " + unid, ts);
        }
        GUI.color = Color.white;
    }

    static Texture2D whiteLegendTex;
    static Texture2D WhiteTex()
    {
        if (whiteLegendTex == null)
        {
            whiteLegendTex = new Texture2D(1, 1);
            whiteLegendTex.SetPixel(0, 0, Color.white);
            whiteLegendTex.filterMode = FilterMode.Point;
            whiteLegendTex.Apply();
        }
        return whiteLegendTex;
    }

    static string Fmt(float v)
    {
        if (v >= 100000f) return (v / 1000f).ToString("F0");
        if (v >= 100f) return v.ToString("F0");
        return v.ToString("F1");
    }
}
