using System.Collections.Generic;
using UnityEngine;

// Replica el HUD del visor HTML:
// - #modebar (arriba centro): VISUALIZACION / MODIFICACIONES / ANALISIS / DATOS.
// - #info (arriba izquierda): titulo + ayuda + contadores Nodos/Elementos.
// - #legend (abajo izquierda): leyenda de colores + checkboxes de capas.
public class ViewerHud : MonoBehaviour
{
    EdificioLoader loader;
    DataPanel dataPanel;
    ModificationMode modificationMode;
    ElementSearchPanel elementSearchPanel;
    int tab = 0; // 0 visualizacion, 1 modificaciones, 2 analisis, 3 datos

    string[] layers = { "columnas", "vigasX", "vigasY", "muros", "losas", "metálicas", "nodos", "ejes", "diafragmas" };
    string[] layerLabels = { "Columnas", "Vigas X", "Vigas Y", "Muros", "Losas", "Metálicas", "Nodos", "Ejes (palitos)", "Diafragmas" };

    Vector2 layerScroll;
    static Texture2D whiteTex;
    static Texture2D GetWhiteTex()
    {
        if (whiteTex == null)
        {
            whiteTex = new Texture2D(1, 1);
            whiteTex.SetPixel(0, 0, Color.white);
            whiteTex.filterMode = FilterMode.Point;
            whiteTex.Apply();
        }
        return whiteTex;
    }

    public void Setup(EdificioLoader l, DataPanel dp, ModificationMode mm, ElementSearchPanel sp)
    {
        loader = l;
        dataPanel = dp;
        modificationMode = mm;
        elementSearchPanel = sp;
    }

    void OnGUI()
    {
        if (loader == null) return;
        DrawModeBar();
        DrawInfoHud();
        DrawLayerLegend();
    }

    // #modebar: [VISUALIZACION] [MODIFICACIONES] [ANALISIS] [DATOS]
    void DrawModeBar()
    {
        float toolbarWidth = Mathf.Clamp(Screen.width - 432f, 520f, 900f);
        Rect toolbar = new Rect(Mathf.Max(420, Screen.width / 2f - toolbarWidth * 0.5f), 8, toolbarWidth, 72);
        ElementInfoStyle.ToolbarArea = toolbar;
        GUISkin previous = ElementInfoStyle.Begin(toolbar);
        GUILayout.BeginHorizontal();

        if (ElementInfoStyle.Choice(tab == 0, "Visualización")) SelectTab(0);
        if (ElementInfoStyle.Choice(tab == 1, "Modificaciones")) SelectTab(1);
        if (ElementInfoStyle.Choice(tab == 2, "Análisis")) SelectTab(2);
        if (ElementInfoStyle.Choice(tab == 3, "Datos")) SelectTab(3);
        GUILayout.EndHorizontal();
        ElementInfoStyle.End(previous);
    }

    void SelectTab(int next)
    {
        tab = next;
        if (AnalysisMode.Current != null) AnalysisMode.Current.SetActive(tab == 2);
        if (modificationMode != null) modificationMode.SetActive(tab == 1);
        if (dataPanel != null) dataPanel.SetVisible(tab == 3);
        if (elementSearchPanel != null && tab != 0) elementSearchPanel.SetVisible(false);
    }

    // #info: titulo, ayuda de camara y contadores.
    void DrawInfoHud()
    {
        int n = loader.NodeCount, e = loader.ElementCount;
        GUISkin previous = ElementInfoStyle.Begin(new Rect(12, 8, 396, 72));
        GUILayout.Label("Edificio 3D · Grupo 6", new GUIStyle(GUI.skin.label) { fontSize = 20, fontStyle = FontStyle.Bold, padding = new RectOffset() });
        ElementInfoStyle.Note(n + " nodos · " + e + " elementos");
        ElementInfoStyle.End(previous);
    }

    // #legend: swatches de color + checkboxes "Mostrar".
    void DrawLayerLegend()
    {
        bool analysis = AnalysisMode.Current != null && AnalysisMode.Current.Active;
        float height = Mathf.Min(510f, Mathf.Max(120f, Screen.height - (analysis ? 452f : 100f)));
        Rect area = new Rect(12, Screen.height - height - 12, Mathf.Min(360, Screen.width - 24), height);
        ElementInfoStyle.LayerArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        GUILayout.Label("Capas del modelo", new GUIStyle(GUI.skin.label) { fontSize = 22, fontStyle = FontStyle.Bold });
        ElementInfoStyle.Note("Controla qué elementos se muestran");
        layerScroll = GUILayout.BeginScrollView(layerScroll, false, false);
        ElementInfoStyle.Section("LEYENDA DE COLORES");
        LegendRow(new Color(0.906f, 0.298f, 0.235f), "Columna 70x70");     // #e74c3c
        LegendRow(new Color(0.204f, 0.596f, 0.859f), "Viga X 60x80");      // #3498db
        LegendRow(new Color(0.180f, 0.800f, 0.443f), "Viga Y 60x80");      // #2ecc71
        LegendRow(new Color(0.608f, 0.349f, 0.714f), "Muro / pantalla");   // #9b59b6
        LegendRow(new Color(0.902f, 0.404f, 0.133f), "Losa");              // #e67e22
        LegendRow(new Color(0.102f, 0.737f, 0.612f), "Nodo");              // #1abc9c
        LegendRow(new Color(0.608f, 0.349f, 0.714f), "Apoyo empotrado");   // #9b59b6
        LegendRow(new Color(0.945f, 0.769f, 0.059f), "Refuerzo metalico"); // #f1c40f

        if (tab == 0)
        {
            ElementInfoStyle.Section("BUSCAR ELEMENTO");
            ElementInfoStyle.Note("Localiza por tipo e ID, acerca la camara y resalta el elemento.");
            if (GUILayout.Button(elementSearchPanel != null && elementSearchPanel.Visible ? "Cerrar buscador" : "Abrir buscador"))
                if (elementSearchPanel != null) elementSearchPanel.Toggle();
        }

        ElementInfoStyle.Section("VISIBILIDAD");
        bool all = true;
        foreach (string l in layers)
            if (!loader.IsLayerVisible(l)) { all = false; break; }
        if (GUILayout.Button(all ? "Ocultar todas las capas" : "Mostrar todas las capas"))
            loader.SetAllLayers(!all);
        GUILayout.Space(6);

        // Capas en dos columnas para que no se corten abajo.
        for (int i = 0; i < layers.Length; i += 2)
        {
            GUILayout.BeginHorizontal();
            ToggleLayer(i);
            GUILayout.Space(4);
            if (i + 1 < layers.Length) ToggleLayer(i + 1);
            else GUILayout.Label("", GUILayout.MinWidth(0), GUILayout.ExpandWidth(true));
            GUILayout.EndHorizontal();
        }
        ElementInfoStyle.Section("NAVEGACIÓN");
        ElementInfoStyle.Note("Clic izq.: rotar · Clic der.: mover\nRueda: zoom · N: nodos · E: ejes\nMODIFICACIONES: Base/Mod A/Mod B\nANALISIS: doble clic losa = SQ4");
        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);
    }

    void ToggleLayer(int i)
    {
        bool on = loader.IsLayerVisible(layers[i]);
        Color previous = GUI.backgroundColor;
        GUI.backgroundColor = on ? new Color(0.38f, 0.80f, 1f) : new Color(0.65f, 0.70f, 0.78f);
        var style = new GUIStyle(GUI.skin.button) { alignment = TextAnchor.MiddleLeft, fontSize = 17 };
        string label = (on ? "●  " : "○  ") + layerLabels[i];
        bool no = GUILayout.Toggle(on, label, style, GUILayout.MinWidth(0), GUILayout.ExpandWidth(true));
        GUI.backgroundColor = previous;
        if (no != on) loader.SetLayerVisible(layers[i], no);
    }

    void LegendRow(Color c, string txt)
    {
        GUILayout.BeginHorizontal();
        // Cuadradito de color fijo (14x14) como el swatch del visor HTML.
        var sq = new GUIStyle();
        sq.normal.background = GetWhiteTex();
        sq.border = new RectOffset(0, 0, 0, 0);
        sq.margin = new RectOffset(4, 8, 5, 0);
        GUI.color = c;
        GUILayout.Box("", sq, GUILayout.Width(18), GUILayout.Height(18));
        GUI.color = Color.white;
        GUILayout.Label(txt, new GUIStyle(GUI.skin.label) { fontSize = 18, padding = new RectOffset(0, 0, 2, 2) });
        GUILayout.EndHorizontal();
    }
}
