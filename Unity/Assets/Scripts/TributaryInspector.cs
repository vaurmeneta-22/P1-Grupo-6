using UnityEngine;
using UnityEngine.UI;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

// Inspector por clic, replica el comportamiento del visor HTML: al hacer clic en
// una viga se muestran sus propiedades estructurales y las cargas tributarias
// (G / Q) calculadas en el analisis. Tambien columna/muro y losas.
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
        }
        catch (System.Exception ex)
        {
            Debug.LogError("Inspector UI fallo: " + ex.Message + "\n" + ex.StackTrace);
        }
    }

    public bool HasAnyData { get { return tributaryById.Count > 0; } }

    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            DoPick();
        }
    }

    // Lee tributary_map.js (const TRIBUTARY = {...};) y lo indexa por id de elemento.
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
        // Respaldo: extraer el font que un TextMesh resuelve por defecto.
        GameObject probe = new GameObject("_fontProbe");
        TextMesh tm = probe.AddComponent<TextMesh>();
        Font rf = tm.font;
        Object.Destroy(probe);
        return rf;
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
        pr.sizeDelta = new Vector2(470, 560);
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
        tr.offsetMax = new Vector2(-12, -12);
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
            return;
        }

        panel.SetActive(true);
        text.text = BuildInfo(best);
        Highlight(best);
    }

    static float Priority(ElementTag t)
    {
        if (t.type == "beam_x" || t.type == "beam_y") return 3;
        if (t.type == "column" || t.type == "wall") return 2;
        return 1; // losa
    }

    string BuildInfo(ElementTag e)
    {
        float L = (e.end - e.start).magnitude;
        string piso = NombrePiso(e.start.y);
        if (e.type == "beam_x" || e.type == "beam_y")
        {
            TribEntry t;
            tributaryById.TryGetValue(e.elementId, out t);
            if (t == null)
            {
                return "Viga " + e.type + " (id " + e.elementId + ")\n" +
                       "Sin area tributaria indexada en el analisis.";
            }
            return BuildBeamInfo(e, t, L, piso);
        }
        if (e.type == "column")
        {
            string secStr = e.section;
            if (string.IsNullOrEmpty(secStr)) secStr = (e.bCm) + "x" + (e.bCm) + " cm";
            return "COLUMNA (id " + e.elementId + ")\n" +
                   "Piso: " + piso + "  [z=" + e.start.y.ToString("F2") + " m]\n" +
                   "Nodos: (" + e.start.x.ToString("F2") + "," + e.start.z.ToString("F2") +
                   ") -> (" + e.end.x.ToString("F2") + "," + e.end.z.ToString("F2") + ")\n" +
                   "Altura: " + L.ToString("F2") + " m\n" +
                   "Seccion: " + secStr;
        }
        if (e.type == "wall")
        {
            float espesor = e.bCm * 0.01f; // m
            return "MURO (id " + e.elementId + ")\n" +
                   "Piso: " + piso + "  [z=" + e.start.y.ToString("F2") + " m]\n" +
                   "Altura: " + L.ToString("F2") + " m\n" +
                   "Seccion: espesor " + espesor.ToString("F3") + " m x largo " + e.hCm.ToString("F1") + " cm (muro)";
        }
        // losa
        return "LOSA (panel id " + e.elementId + ")\n" +
               "Altura placa: " + e.start.y.ToString("F2") + " m\n" +
               "Aspecto: " + Mathf.Abs(e.end.x - e.start.x).ToString("F2") + " x " +
               Mathf.Abs(e.end.z - e.start.z).ToString("F2") + " m";
    }

    string BuildBeamInfo(ElementTag e, TribEntry t, float L, string piso)
    {
        string direction = (e.type == "beam_x") ? "X (plano) y fija" : "Y (plano) x fija";
        float b = e.bCm, h = e.hCm;
        float At = t.A;
        float qG_total_m2 = At > 0 ? (t.Wg / At) : 0f;
        float losa_estructural_m2 = Mathf.Max(0f, qG_total_m2 - TERMINACIONES_KNM2);
        float W_PP = GAMMA_CONC * (b / 100f) * (h / 100f) * L;
        float p_PP = L > 0 ? (W_PP / L) : 0f;
        float W_G_total = t.Wg + W_PP;
        float p_G_total = L > 0 ? (W_G_total / L) : 0f;
        float W_Q_total = t.Wq;

        return "Viga " + e.type + "  (id " + t.id + ")\n" +
               "Piso: " + piso + "   [z=" + e.start.y.ToString("F2") + " m]\n" +
               "Nodos: (" + e.start.x.ToString("F2") + "," + e.start.z.ToString("F2") +
               ") -> (" + e.end.x.ToString("F2") + "," + e.end.z.ToString("F2") + ")\n" +
               "Direccion: " + direction + "\n" +
               "Longitud: " + L.ToString("F2") + " m\n" +
               "Seccion: " + t.sec + " (" + (b).ToString("F0") + "x" + (h).ToString("F0") + " cm)\n" +
               "Area tributaria At: " + At.ToString("F2") + " m2\n" +
               "Ancho tributario (At/L): " + (L > 0 ? (At / L).ToString("F2") : "0") + " m\n\n" +
               "CARGA PERMANENTE G (sobre losa):\n" +
               "  Losa estructural (" + Mathf.RoundToInt(losa_estructural_m2 / (GAMMA_CONC / 1000f)) + " cm): " + losa_estructural_m2.ToString("F2") + " kN/m2\n" +
               "  Terminaciones: " + TERMINACIONES_KNM2.ToString("F2") + " kN/m2\n" +
               "  q_G superficial total: " + qG_total_m2.ToString("F2") + " kN/m2\n" +
               "  W_G tributario (q_G x At): " + t.Wg.ToString("F2") + " kN\n" +
               "  p_G equivalente (W_G / L): " + t.pG.ToString("F2") + " kN/m\n\n" +
               "PESO PROPIO DE LA VIGA:\n" +
               "  W_PP (gamma x b x h x L): " + W_PP.ToString("F2") + " kN\n" +
               "  p_PP equivalente: " + p_PP.ToString("F2") + " kN/m\n\n" +
               "TOTAL G (aplicado a la viga):\n" +
               "  W_G,total = W_G + W_PP = " + W_G_total.ToString("F2") + " kN\n" +
               "  p_G,total = " + p_G_total.ToString("F2") + " kN/m\n\n" +
               "SOBRECARGA Q (sobre losa, sin peso propio):\n" +
               "  q_Q: " + SOBRECARGA_KNM2.ToString("F2") + " kN/m2\n" +
               "  W_Q tributario (q_Q x At): " + W_Q_total.ToString("F2") + " kN\n" +
               "  p_Q equivalente (W_Q / L): " + t.pQ.ToString("F2") + " kN/m";
    }

    static string NombrePiso(float yi)
    {
        if (yi < 3.56f) return "Subterraneo";
        if (yi < 7.12f) return "Piso 1";
        if (yi < 10.68f) return "Piso 2";
        if (yi < 14.24f) return "Piso 3";
        if (yi < 17.8f) return "Piso 4";
        return "Techo";
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
        if (highlightMat != null) Destroy(highlightMat);
    }
}