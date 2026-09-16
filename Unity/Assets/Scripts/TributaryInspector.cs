using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;

// Inspector por clic, replica el comportamiento del visor HTML: al hacer clic en
// un elemento se muestran sus propiedades estructurales, fuerzas por caso de
// analisis (G/Q/EX/EY/COMBO) y cargas tributarias. Tambien columna/muro/losa y
// la triada de ejes locales en 3D.
public class TributaryInspector : MonoBehaviour
{
    public class TribEntry
    {
        public int id;
        public string sec;
        public float A;    // area tributaria (m2)
        public float Wg;   // carga total de losa G (kN)
        public float Wq;   // carga de sobrecarga Q (kN)
        public float pG;   // equivalente lineal G (kN/m)
        public float pQ;   // equivalente lineal Q (kN/m)
    }

    const float GAMMA_CONC = 23.544f;    // kN/m3
    const float TERMINACIONES_KNM2 = 2.0f;
    const float SOBRECARGA_KNM2 = 2.0f;

    private Dictionary<int, TribEntry> tributaryById = new Dictionary<int, TribEntry>();
    private Canvas canvas;
    private Text text;
    private GameObject panel;
    private GameObject highlight;
    private Material highlightMat;
    private ElementTag selected;
    private string currentCase = "COMBO";

    // Triada de ejes locales (x' rojo, y' verde, z' azul) como flechas.
    private GameObject axesGroup;
    private Material axisXMat, axisYMat, axisZMat;

    public string CurrentCase { get { return currentCase; } }

    public void Setup(string tributaryJsPath, Transform parent)
    {
        LoadTributaryMap(tributaryJsPath);

        try
        {
            BuildUI(parent);

            Shader hs = Shader.Find("Universal Render Pipeline/Lit");
            if (hs == null) hs = Shader.Find("Standard");
            if (hs != null)
            {
                highlightMat = new Material(hs);
                highlightMat.color = new Color(1f, 1f, 0f, 0.4f);
                Color c2 = highlightMat.color;
                if (highlightMat.HasProperty("_BaseColor")) highlightMat.SetColor("_BaseColor", c2);
                if (highlightMat.HasProperty("_Surface")) highlightMat.SetFloat("_Surface", 1f);
                if (highlightMat.HasProperty("_Blend")) highlightMat.SetFloat("_Blend", 0f);
                highlightMat.renderQueue = 3100;
            }

            Shader liner = Shader.Find("Sprites/Default");
            if (liner == null) liner = Shader.Find("Unlit/Color");
            axisXMat = NewLineMat(liner, new Color(1f, 0.31f, 0.31f, 1f)); // #ff5050
            axisYMat = NewLineMat(liner, new Color(0.31f, 1f, 0.31f, 1f)); // #50ff50
            axisZMat = NewLineMat(liner, new Color(0.31f, 0.56f, 1f, 1f)); // #5090ff

            axesGroup = new GameObject("EjesLocalesInspector");
            axesGroup.transform.SetParent(parent, false);
            axesGroup.SetActive(false);
        }
        catch (System.Exception ex)
        {
            Debug.LogError("Inspector UI fallo: " + ex.Message + "\n" + ex.StackTrace);
        }
    }

    public bool HasAnyData { get { return tributaryById.Count > 0; } }

    void Update()
    {
        // El visor HTML ignora el clic en modo analisis (ahi el clic lo usa el
        // doble-clic para reportes/P-M). Solo el modo visualizacion abre el panel.
        if (AnalysisMode.Current != null && AnalysisMode.Current.Active) return;
        if (Input.GetMouseButtonDown(0))
        {
            DoPick();
        }
    }

    // Lee tributary_map.js (const TRIBUTARY = {...};) y lo indexa por id de elemento.
    // Los resultados del analisis (analysis_map.json) tambien traen tributarias;
    // si estan disponibles se priorizan sobre este archivo clasico.
    void LoadTributaryMap(string path)
    {
        tributaryById.Clear();
        if (!File.Exists(path)) return;
        string raw = File.ReadAllText(path);
        int start = raw.IndexOf('{');
        int end = raw.LastIndexOf('}');
        if (start < 0 || end < 0 || end <= start) return;
        string body = raw.Substring(start, end - start + 1);

        Regex entryRe = new Regex("\"([^\"]+)\"\\s*:\\s*\\{([^}]*)\\}");
        foreach (Match m in entryRe.Matches(body))
        {
            string fields = m.Groups[2].Value;
            TribEntry t = new TribEntry();
            t.sec = GrabStr(fields, "sec");
            t.id = (int)GrabFloat(fields, "id");
            t.A = GrabFloat(fields, "A");
            t.Wg = GrabFloat(fields, "Wg");
            t.Wq = GrabFloat(fields, "Wq");
            t.pG = GrabFloat(fields, "pG");
            t.pQ = GrabFloat(fields, "pQ");
            if (!tributaryById.ContainsKey(t.id)) tributaryById[t.id] = t;
        }
    }

    static float GrabFloat(string fields, string key)
    {
        Match m = Regex.Match(fields, "\"" + key + "\"\\s*:\\s*(-?[0-9]+\\.?[0-9]*)");
        return m.Success ? float.Parse(m.Groups[1].Value, System.Globalization.CultureInfo.InvariantCulture) : 0f;
    }

    static string GrabStr(string fields, string key)
    {
        Match m = Regex.Match(fields, "\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
        return m.Success ? m.Groups[1].Value : "";
    }

    // Fuente valida para el Text de UI. Se obtiene del TextMesh integrado de Unity
    // (que el resto del proyecto ya usa sin problema), sin depender de nombres de
    // recurso que en algunas versiones lanzan excepcion.
    static Font GetUIFont()
    {
        try
        {
            Font f = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (f != null) return f;
        }
        catch { }
        try
        {
            Font f = Resources.GetBuiltinResource<Font>("Arial.ttf");
            if (f != null) return f;
        }
        catch { }
        GameObject probe = new GameObject("_fontProbe");
        TextMesh tm = probe.AddComponent<TextMesh>();
        Font rf = tm.font;
        Object.Destroy(probe);
        return rf;
    }

    Material NewLineMat(Shader s, Color c)
    {
        Material m = new Material(s);
        m.color = c;
        return m;
    }

    void BuildUI(Transform parent)
    {
        GameObject canvasGO = new GameObject("InspectorCanvas");
        canvasGO.transform.SetParent(parent, false);
        canvas = canvasGO.AddComponent<Canvas>();
        canvas.renderMode = RenderMode.ScreenSpaceOverlay;
        CanvasScaler scaler = canvasGO.AddComponent<CanvasScaler>();
        scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
        scaler.referenceResolution = new Vector2(1920, 1080);
        canvasGO.AddComponent<GraphicRaycaster>();

        // Panel fondo
        panel = new GameObject("Panel");
        RectTransform pr = panel.AddComponent<RectTransform>();
        panel.transform.SetParent(canvasGO.transform, false);
        pr.anchorMin = new Vector2(1, 1);
        pr.anchorMax = new Vector2(1, 1);
        pr.pivot = new Vector2(1, 1);
        pr.anchoredPosition = new Vector2(-20, -20);
        pr.sizeDelta = new Vector2(560, 640);
        Image img = panel.AddComponent<Image>();
        img.color = new Color(0.1f, 0.1f, 0.12f, 0.9f);

        Button btn = panel.AddComponent<Button>();
        btn.targetGraphic = img;

        GameObject headerGO = new GameObject("Header");
        RectTransform hr = headerGO.AddComponent<RectTransform>();
        headerGO.transform.SetParent(panel.transform, false);
        Image header = headerGO.AddComponent<Image>();
        hr.anchorMin = new Vector2(0, 1);
        hr.anchorMax = new Vector2(1, 1);
        hr.pivot = new Vector2(0.5f, 1);
        hr.sizeDelta = new Vector2(0, 8);
        hr.anchoredPosition = new Vector2(0, -4);
        header.color = new Color(0.2f, 0.6f, 1f, 0.9f);

        // Franja de casos de analisis (G/Q/EX/EY/COMBO) como la del panel del visor.
        BuildCaseButtons(panel.transform, new Vector2(0.5f, 1f), new Vector2(0.5f, 1f), new Vector2(0f, -12f));

        // Texto de contenido
        Font font = GetUIFont();
        GameObject textGO = new GameObject("Texto");
        RectTransform tr = textGO.AddComponent<RectTransform>();
        textGO.transform.SetParent(panel.transform, false);
        text = textGO.AddComponent<Text>();
        if (font != null) text.font = font;
        tr.anchorMin = new Vector2(0, 0);
        tr.anchorMax = new Vector2(1, 1);
        tr.offsetMin = new Vector2(12, 12);
        tr.offsetMax = new Vector2(-12, -38);
        text.fontSize = 16;
        text.color = Color.white;
        text.alignment = TextAnchor.UpperLeft;
        text.horizontalOverflow = HorizontalWrapMode.Wrap;
        text.verticalOverflow = VerticalWrapMode.Overflow;

        // Boton cerrar (X): fondo + el texto "x" en un hijo separado (mismo patron que
        // el texto de contenido; apilar Image+Button+Text en un GO unico falla al crear
        // UI en codigo con Unity 6).
        GameObject closeBtnGO = new GameObject("Cerrar");
        RectTransform cr = closeBtnGO.AddComponent<RectTransform>();
        closeBtnGO.transform.SetParent(panel.transform, false);
        cr.anchorMin = new Vector2(1, 1);
        cr.anchorMax = new Vector2(1, 1);
        cr.pivot = new Vector2(1, 1);
        cr.anchoredPosition = new Vector2(0, -2);
        cr.sizeDelta = new Vector2(30, 30);
        Image ci = closeBtnGO.AddComponent<Image>();
        ci.color = new Color(0.8f, 0.2f, 0.2f, 0.9f);
        Button cb = closeBtnGO.AddComponent<Button>();
        cb.onClick.AddListener(() => panel.SetActive(false));

        GameObject closeLblGO = new GameObject("Cruz");
        RectTransform clr = closeLblGO.AddComponent<RectTransform>();
        closeLblGO.transform.SetParent(closeBtnGO.transform, false);
        clr.anchorMin = new Vector2(0, 0);
        clr.anchorMax = new Vector2(1, 1);
        clr.offsetMin = Vector2.zero;
        clr.offsetMax = Vector2.zero;
        Text ct = closeLblGO.AddComponent<Text>();
        if (font != null) ct.font = font;
        ct.fontSize = 18;
        ct.alignment = TextAnchor.MiddleCenter;
        ct.color = Color.white;
        ct.text = "x";

        panel.SetActive(false);
    }

    // Botones de caso: G | Q | EX | EY | COMBO (misma logica que el visor HTML,
    // que selecciona el caso de fuerzas/deformada con un boton por combinacion).
    void BuildCaseButtons(Transform parent, Vector2 anchorMin, Vector2 anchorMax, Vector2 pos)
    {
        Font font = GetUIFont();
        string[] cases = { "G", "Q", "EX", "EY", "COMBO" };
        float w = 62f, h = 26f, gap = 4f;
        GameObject rowGO = new GameObject("Casos");
        RectTransform rr = rowGO.AddComponent<RectTransform>();
        rowGO.transform.SetParent(parent, false);
        rr.anchorMin = anchorMin;
        rr.anchorMax = anchorMax;
        rr.pivot = new Vector2(0.5f, 1f);
        rr.anchoredPosition = pos;
        rr.sizeDelta = new Vector2(cases.Length * (w + gap) - gap, h);

        HorizontalLayoutGroup hlg = rowGO.AddComponent<HorizontalLayoutGroup>();
        hlg.spacing = gap;
        hlg.childControlWidth = true;
        hlg.childControlHeight = true;
        hlg.childForceExpandWidth = false;
        hlg.padding = new RectOffset(0, 0, 0, 0);

        foreach (string cs in cases)
        {
            GameObject bGO = new GameObject("Caso_" + cs);
            RectTransform br = bGO.AddComponent<RectTransform>();
            bGO.transform.SetParent(rowGO.transform, false);
            br.sizeDelta = new Vector2(w, h);
            Image bi = bGO.AddComponent<Image>();
            bi.color = (cs == currentCase)
                ? new Color(0.2f, 0.7f, 0.9f, 0.9f)
                : new Color(0.25f, 0.25f, 0.3f, 0.9f);
            Button bb = bGO.AddComponent<Button>();
            bb.targetGraphic = bi;
            string caso = cs;
            bb.onClick.AddListener(() =>
            {
                currentCase = caso;
                RefreshSelectedColors();
                UpdatePanel();
            });

            GameObject lGO = new GameObject("Lbl");
            RectTransform lr = lGO.AddComponent<RectTransform>();
            lGO.transform.SetParent(bGO.transform, false);
            lr.anchorMin = Vector2.zero;
            lr.anchorMax = Vector2.one;
            lr.offsetMin = Vector2.zero;
            lr.offsetMax = Vector2.zero;
            Text lt = lGO.AddComponent<Text>();
            if (font != null) lt.font = font;
            lt.fontSize = 13;
            lt.alignment = TextAnchor.MiddleCenter;
            lt.color = Color.white;
            lt.text = cs;
        }
    }

    void RefreshSelectedColors()
    {
        Transform row = panel.transform.Find("Casos");
        if (row == null) return;
        foreach (Transform child in row)
        {
            Text lt = child.GetComponentInChildren<Text>();
            Image bi = child.GetComponent<Image>();
            if (bi == null) continue;
            string name = child.name;
            string caso = name.StartsWith("Caso_") ? name.Substring(5) : name;
            bi.color = (caso == currentCase)
                ? new Color(0.2f, 0.7f, 0.9f, 0.9f)
                : new Color(0.25f, 0.25f, 0.3f, 0.9f);
        }
    }

    void UpdatePanel()
    {
        if (selected != null) text.text = BuildInfo(selected);
    }

    void DoPick()
    {
        Camera cam = Camera.main;
        if (cam == null) return;
        Ray ray = cam.ScreenPointToRay(Input.mousePosition);

        RaycastHit[] hits = Physics.RaycastAll(ray, 1000f);
        ElementTag best = null;
        float bestPri = -1f;
        float bestDist = float.MaxValue;
        foreach (RaycastHit h in hits)
        {
            ElementTag t = h.collider.GetComponentInParent<ElementTag>();
            if (t == null) continue;
            float pri = Priority(t);
            if (pri > bestPri || (pri == bestPri && h.distance < bestDist))
            {
                bestPri = pri;
                bestDist = h.distance;
                best = t;
            }
        }

        if (best == null)
        {
            panel.SetActive(false);
            ClearHighlight();
            ClearAxes();
            return;
        }

        panel.SetActive(true);
        selected = best;
        text.text = BuildInfo(best);
        Highlight(best);
        UpdateAxes(best);
    }

    static float Priority(ElementTag t)
    {
        if (t.type == "beam_x" || t.type == "beam_y") return 3;
        if (t.type == "column" || t.type == "wall") return 2;
        return 1; // losa
    }

    // Cabecera comun del inspector: ID, nodos (tag + coords), seccion, material,
    // restricciones. Igual que elemHeader() en el visor HTML.
    string BuildHeader(ElementTag e)
    {
        AnalysisMap.ElementInfo meta = AnalysisMap.Element(e.elementId);
        string tipo = TipoNombre(e.type);
        string mat = meta != null ? MaterialNombre(meta.material)
            : MaterialNombre(e.type.StartsWith("steel") ? "A240ES" : "HA35");
        string seccion = meta != null ? meta.section : e.section;
        if (string.IsNullOrEmpty(seccion) && e.type == "column")
            seccion = Mathf.RoundToInt(e.bCm) + "x" + Mathf.RoundToInt(e.bCm) + " cm";

        int ni = meta != null ? meta.ni : e.niNode;
        int nj = meta != null ? meta.nj : e.njNode;
        StringBuilder sb = new StringBuilder();
        sb.Append(tipo).Append("  id ").Append(e.elementId).AppendLine();
        sb.Append("Material: ").Append(mat).AppendLine();
        sb.Append("Seccion: ").Append(seccion).AppendLine();
        sb.Append("Nodo i: ").Append(ni).Append(' ').Append(PuntoEstructural(ni)).AppendLine();
        sb.Append("Nodo j: ").Append(nj).Append(' ').Append(PuntoEstructural(nj)).AppendLine();
        sb.Append("Restricciones: ").Append(Restricciones(e, meta)).AppendLine();
        return sb.ToString();
    }

    string PuntoEstructural(int tag)
    {
        string key = tag.ToString();
        double[] c;
        if (AnalysisMap.StructCoords.TryGetValue(key, out c) && c.Length >= 3)
            return "(" + c[0].ToString("F2") + ", " + c[1].ToString("F2") + ", h=" + c[2].ToString("F2") + " m)";
        return "(?)";
    }

    string Restricciones(ElementTag e, AnalysisMap.ElementInfo meta)
    {
        List<string> r = new List<string>();
        if (meta != null)
        {
            if (meta.supI) r.Add("extremo i (nodo " + meta.ni + ") empotrado/apoyado");
            if (meta.supJ) r.Add("extremo j (nodo " + meta.nj + ") empotrado/apoyado");
            if (meta.type == "wall")
            {
                double[] ci, cj;
                AnalysisMap.StructCoords.TryGetValue(meta.ni.ToString(), out ci);
                AnalysisMap.StructCoords.TryGetValue(meta.nj.ToString(), out cj);
                if (ci != null && cj != null && ci.Length >= 3 && cj.Length >= 3)
                {
                    double hi = ci[2], hj = cj[2];
                    double hBase = Mathf.Min((float)hi, (float)hj);
                    if (hBase < 0.01 || meta.id == 452 || meta.id == 453)
                        r.Add("empotrado en fundacion (base del muro)");
                    else
                        r.Add("arranca en " + NombrePiso((float)hBase) + " (h=" + hBase.ToString("F2") + " m), apoyado en estructura del piso inferior");
                }
            }
        }
        if (r.Count == 0) r.Add("continua (extremos sin apoyo directo)");
        return string.Join(" · ", r.ToArray());
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

    // Tabla de fuerzas del caso activo (N, Vy, Vz, T, My, Mz) en extremos i y j,
    // igual que fuerzasViga()/fuerzasCol() del visor: ANALYSIS.forces[caso][id].
    string FuerzasDelElemento(ElementTag e)
    {
        if (!AnalysisMap.Loaded) return "";
        AnalysisMap.EndForces f = AnalysisMap.Fuerzas(currentCase, e.elementId);
        if (f == null) return "";
        StringBuilder sb = new StringBuilder();
        sb.AppendLine();
        sb.Append("FUERZAS [").Append(currentCase).Append("]  (kN / kN-m):").AppendLine();
        sb.Append(FuerzasFila("i", f.li));
        sb.Append(FuerzasFila("j", f.lj));
        return sb.ToString();
    }

    string FuerzasFila(string extremo, double[] r)
    {
        if (r == null || r.Length < 6)
            return "  [" + extremo + "] (sin datos)" + System.Environment.NewLine;
        string[] nm = { "N", "Vy", "Vz", "T", "My", "Mz" };
        string[] val = new string[6];
        for (int k = 0; k < 6; k++)
            val[k] = nm[k] + "=" + Mathf.Abs((float)r[k]).ToString("F1") + (k >= 3 ? "kN-m" : "kN");
        return "  [" + extremo + "] " + string.Join("  ", val) + System.Environment.NewLine;
    }

    string BuildInfo(ElementTag e)
    {
        float L = (e.end - e.start).magnitude;
        string piso = e.piso;
        if (string.IsNullOrEmpty(piso)) piso = NombrePiso(e.start.y);

        StringBuilder sb = new StringBuilder();
        sb.Append(BuildHeader(e));
        sb.Append("Piso: ").Append(piso).Append("  [z=").Append(e.start.y.ToString("F2")).Append(" m]").AppendLine();

        if (e.type == "beam_x" || e.type == "beam_y")
        {
            string direction = (e.type == "beam_x") ? "X (plano) y fija" : "Y (plano) x fija";
            sb.Append("Direccion: ").Append(direction).AppendLine();
            sb.Append("Longitud: ").Append(L.ToString("F2")).Append(" m").AppendLine();

            // Tributarias: primero analysis_map.json, despues el archivo clasico.
            bool added = false;
            AnalysisMap.TribuInfo ti = AnalysisMap.Tributaria(e.elementId);
            if (ti != null)
            {
                BuildTribuAnalysis(sb, e, ti);
                added = true;
            }
            else
            {
                TribEntry t;
                if (tributaryById.TryGetValue(e.elementId, out t))
                {
                    BuildTribuClassic(sb, e, t, L);
                    added = true;
                }
            }
            if (!added)
                sb.AppendLine("Sin area tributaria indexada en el analisis.");
        }
        else if (e.type == "column")
        {
            sb.Append("Altura: ").Append(L.ToString("F2")).Append(" m").AppendLine();
            if (e.start.y < 0.01f)
                sb.Append("Material/sujecion: ").Append(MaterialNombre(
                    !string.IsNullOrEmpty(e.material) ? e.material : "HA35")).AppendLine();
        }
        else if (e.type == "wall")
        {
            sb.Append("Largo: ").Append(L.ToString("F2")).Append(" m").AppendLine();
            string secc = e.section;
            if (string.IsNullOrEmpty(secc)) secc = "espesor " + (e.bCm * 0.01f).ToString("F3") + " m x largo " + e.hCm.ToString("F1") + " cm";
            sb.Append("Muro equivalente (elementos ").Append(secc).Append("): material ").Append(MaterialNombre(
                !string.IsNullOrEmpty(e.material) ? e.material : "HA35")).AppendLine();
        }
        else
        {
            sb.Append("LOSA (panel): Altura placa ").Append(e.start.y.ToString("F2")).Append(" m").AppendLine();
        }

        // Cargas del sistema (COMBO) si el mapa las trae.
        if (AnalysisMap.Loaded && AnalysisMap.Meta != null)
        {
            object combo = MiniJson.Get(AnalysisMap.Meta, "COMBO");
            if (combo != null)
            {
                string desc = MiniJson.St(combo, "descripcion");
                double tot = MiniJson.Db(combo, "Carga_COMBO_total_kN");
                if (tot != 0 || !string.IsNullOrEmpty(desc))
                    sb.AppendLine().Append("Cargas del sistema (COMBO): G+Q gravitacional · EX/EY sismo · W total = ").
                      Append(Mathf.RoundToInt((float)tot)).Append(" kN (peso propio + losa residual por vigas)");
            }
        }

        sb.Append(FuerzasDelElemento(e));
        return sb.ToString();
    }

    // Mismo desglose que buildBeamRows() del visor, usando analysis_map.json.
    void BuildTribuAnalysis(StringBuilder sb, ElementTag e, AnalysisMap.TribuInfo t)
    {
        float L = (e.end - e.start).magnitude;
        float b = e.bCm * 0.01f, h = e.hCm * 0.01f;
        float At = (float)t.area;
        float W_G = (float)t.Wg;
        float W_Q = (float)t.Wq;
        float p_Q = (float)t.pQ;
        float W_PP = GAMMA_CONC * b * h * L;
        float W_G_total = W_G + W_PP;
        float p_G_total = L > 0 ? (W_G_total / L) : 0f;

        sb.AppendLine();
        sb.Append("CARGA PERMANENTE G:").AppendLine();
        sb.Append("  Tributario: At = ").Append(At.ToString("F2")).Append(" m2  (ancho = ")
          .Append((L > 0 ? At / L : 0).ToString("F2")).Append(" m)").AppendLine();
        sb.Append("  Losa + terminaciones = ").Append(W_G.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  Peso propio viga = ").Append(W_PP.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  G total (W_G + W_PP) = ").Append(W_G_total.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  p_G total = ").Append(p_G_total.ToString("F2")).Append(" kN/m").AppendLine();
        sb.AppendLine();
        sb.Append("CARGA VARIABLE Q:").AppendLine();
        sb.Append("  q_Q = ").Append(SOBRECARGA_KNM2.ToString("F2")).Append(" kN/m2").AppendLine();
        sb.Append("  W_Q tributario = ").Append(W_Q.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  p_Q = ").Append(p_Q.ToString("F2")).Append(" kN/m");
    }

    // Desglose equivalente usando el tributary_map.js clasico (sin results nuevos).
    void BuildTribuClassic(StringBuilder sb, ElementTag e, TribEntry t, float L)
    {
        float b = e.bCm, h = e.hCm;
        float At = t.A;
        float qG_total_m2 = At > 0 ? (t.Wg / At) : 0f;
        float losa_estructural_m2 = Mathf.Max(0f, qG_total_m2 - TERMINACIONES_KNM2);
        float W_PP = GAMMA_CONC * (b / 100f) * (h / 100f) * L;
        float p_PP = L > 0 ? (W_PP / L) : 0f;
        float W_G_total = t.Wg + W_PP;
        float p_G_total = L > 0 ? (W_G_total / L) : 0f;

        sb.AppendLine();
        sb.Append("CARGA PERMANENTE G:").AppendLine();
        sb.Append("  Losa estructural (").Append(Mathf.RoundToInt(losa_estructural_m2 / (GAMMA_CONC / 1000f)))
          .Append(" cm): ").Append(losa_estructural_m2.ToString("F2")).Append(" kN/m2").AppendLine();
        sb.Append("  Terminaciones: ").Append(TERMINACIONES_KNM2.ToString("F2")).Append(" kN/m2").AppendLine();
        sb.Append("  q_G superficial total: ").Append(qG_total_m2.ToString("F2")).Append(" kN/m2").AppendLine();
        sb.Append("  W_G tributario (q_G x At): ").Append(t.Wg.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  p_G equivalente (W_G / L): ").Append(t.pG.ToString("F2")).Append(" kN/m").AppendLine();
        sb.Append("  W_PP: ").Append(W_PP.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  total G: ").Append(W_G_total.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("CARGA VARIABLE Q:").AppendLine();
        sb.Append("  q_Q: ").Append(SOBRECARGA_KNM2.ToString("F2")).Append(" kN/m2").AppendLine();
        sb.Append("  W_Q tributario (q_Q x At): ").Append(t.Wq.ToString("F2")).Append(" kN").AppendLine();
        sb.Append("  p_Q equivalente (W_Q / L): ").Append(t.pQ.ToString("F2")).Append(" kN/m");
    }

    static string NombrePiso(float yi)
    {
        int n = Mathf.RoundToInt(yi / 3.56f);
        if (n <= 0) return "Subterraneo";
        if (n >= 5) return "Techo";
        return "Piso " + n;
    }

    // Triada de ejes locales en 3D (x' rojo, y' verde, z' azul) centrada en el
    // elemento, como showLocalAxes() del visor. Los ejes vienen en coordenadas
    // OpenSees (x, y-plan, z-altura) y se convierten a Unity (x, z-altura, y-plan).
    void UpdateAxes(ElementTag e)
    {
        if (axesGroup == null) return;
        ClearAxes();
        double[] rot;
        if (!AnalysisMap.LocalAxes.TryGetValue(e.elementId.ToString(), out rot) || rot.Length < 9)
            return;

        Vector3 mid = (e.start + e.end) * 0.5f;
        float len = Mathf.Max((e.end - e.start).magnitude * 0.3f, 0.5f);
        Vector3[] dirs = new Vector3[3];
        for (int k = 0; k < 3; k++)
        {
            Vector3 v = new Vector3((float)rot[k * 3], (float)rot[k * 3 + 2], (float)rot[k * 3 + 1]);
            if (v.magnitude < 1e-6f) continue;
            dirs[k] = v.normalized;
        }
        Material[] mats = { axisXMat, axisYMat, axisZMat };
        for (int k = 0; k < 3; k++)
        {
            if (dirs[k].magnitude < 1e-6f) continue;
            Vector3 tip = mid + dirs[k] * len;
            AddAxisLine(axesGroup.transform, mats[k], mid, tip, "locAxis_" + k);
        }
        axesGroup.SetActive(true);
    }

    void AddAxisLine(Transform parent, Material mat, Vector3 start, Vector3 end, string name)
    {
        GameObject lineGO = new GameObject(name);
        lineGO.transform.SetParent(parent, false);
        LineRenderer lr = lineGO.AddComponent<LineRenderer>();
        lr.material = mat;
        lr.startWidth = 0.06f;
        lr.endWidth = 0.06f;
        lr.positionCount = 2;
        lr.SetPosition(0, start);
        lr.SetPosition(1, end);
    }

    void ClearAxes()
    {
        if (axesGroup == null) return;
        while (axesGroup.transform.childCount > 0)
        {
            Transform c = axesGroup.transform.GetChild(0);
            c.SetParent(null);
            Destroy(c.gameObject);
        }
        axesGroup.SetActive(false);
    }

    // Resalta el elemento seleccionado con una caja semitransparente.
    void Highlight(ElementTag e)
    {
        ClearHighlight();
        Renderer r = e.GetComponentInParent<Renderer>();
        if (r == null) return;
        Bounds b = r.bounds;
        GameObject hl = GameObject.CreatePrimitive(PrimitiveType.Cube);
        hl.name = "HIGHLIGHT";
        Destroy(hl.GetComponent<BoxCollider>());
        hl.transform.position = b.center;
        hl.transform.localScale = b.size;
        hl.GetComponent<Renderer>().sharedMaterial = highlightMat;
        highlight = hl;
        if (axesGroup != null) axesGroup.SetActive(true);
    }

    void ClearHighlight()
    {
        if (highlight != null)
        {
            Destroy(highlight);
            highlight = null;
        }
    }

    void OnDestroy()
    {
        ClearHighlight();
        ClearAxes();
        if (highlightMat != null) Destroy(highlightMat);
    }
}