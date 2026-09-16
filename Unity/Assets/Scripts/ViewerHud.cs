using System.Collections.Generic;
using UnityEngine;

// Replica el HUD del visor HTML:
// - #modebar (arriba centro): "Modo:" + boton VISUALIZACION/ANALISIS [TAB] +
//   boton DATOS.
// - #info (arriba izquierda): titulo + ayuda + contadores Nodos/Elementos.
// - #legend (abajo izquierda): leyenda de colores + checkboxes de capas.
public class ViewerHud : MonoBehaviour
{
    EdificioLoader loader;
    DataPanel dataPanel;

    string[] layers = { "columnas", "vigasX", "vigasY", "muros", "losas", "metálicas", "nodos", "ejes", "diafragmas" };
    string[] layerLabels = { "Columnas", "Vigas X", "Vigas Y", "Muros", "Losas", "Metálicas", "Nodos", "Ejes (palitos)", "Diafragmas" };

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

    public void Setup(EdificioLoader l, DataPanel dp)
    {
        loader = l;
        dataPanel = dp;
    }

    void OnGUI()
    {
        if (loader == null) return;
        DrawModeBar();
        DrawInfoHud();
        DrawLayerLegend();
    }

    // #modebar: Modo: [VISUALIZACION|ANALISIS] [TAB] [DATOS]
    void DrawModeBar()
    {
        GUILayout.BeginArea(new Rect(Screen.width / 2f - 250f, 8, 500, 34));
        GUILayout.BeginHorizontal();
        GUILayout.Label("Modo:", new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold });
        bool anal = AnalysisMode.Current != null && AnalysisMode.Current.Active;
        if (GUILayout.Button(anal ? "ANALISIS" : "VISUALIZACION", GUILayout.Width(150), GUILayout.Height(28)))
        {
            if (AnalysisMode.Current != null) AnalysisMode.Current.ToggleMode();
        }
        GUILayout.Label("[TAB]", new GUIStyle(GUI.skin.label) { fontSize = 11 },
                        GUILayout.Width(42));
        if (GUILayout.Button("DATOS", GUILayout.Width(84), GUILayout.Height(28)))
        {
            if (dataPanel != null) dataPanel.Toggle();
        }
        GUILayout.EndHorizontal();
        GUILayout.EndArea();
    }

    // #info: titulo, ayuda de camara y contadores.
    void DrawInfoHud()
    {
        int n = loader.NodeCount, e = loader.ElementCount;
        GUILayout.BeginArea(new Rect(8, 8, 400, 72));
        var title = new GUIStyle(GUI.skin.label) { fontSize = 14, fontStyle = FontStyle.Bold };
        GUILayout.Label("Edificio 3D - Grupo 6", title);
        GUILayout.Label("Click izq: Rotar | Click der: Mover | Scroll: Zoom | N: Nodos | E: Ejes");
        GUILayout.Label("Inspeccionar: clic en una viga o diafragma | Nodos: " + n + " | Elementos: " + e);
        GUILayout.EndArea();
    }

    // #legend: swatches de color + checkboxes "Mostrar".
    void DrawLayerLegend()
    {
        // La altura deja espacio al panel de analisis (arriba-izquierda).
        GUILayout.BeginArea(new Rect(8, Screen.height - 388f, 258, 380), GUI.skin.box);
        LegendRow(new Color(0.906f, 0.298f, 0.235f), "Columna 70x70");     // #e74c3c
        LegendRow(new Color(0.204f, 0.596f, 0.859f), "Viga X 60x80");      // #3498db
        LegendRow(new Color(0.180f, 0.800f, 0.443f), "Viga Y 60x80");      // #2ecc71
        LegendRow(new Color(0.608f, 0.349f, 0.714f), "Muro / pantalla");   // #9b59b6
        LegendRow(new Color(0.902f, 0.404f, 0.133f), "Losa");              // #e67e22
        LegendRow(new Color(0.102f, 0.737f, 0.612f), "Nodo");              // #1abc9c
        LegendRow(new Color(0.608f, 0.349f, 0.714f), "Apoyo empotrado");   // #9b59b6
        LegendRow(new Color(0.945f, 0.769f, 0.059f), "Refuerzo metalico"); // #f1c40f

        GUILayout.Space(4);
        GUILayout.Box("", GUILayout.Height(1));
        GUILayout.Label("Mostrar:");
        bool all = true;
        foreach (string l in layers)
            if (!loader.IsLayerVisible(l)) { all = false; break; }
        bool na = GUILayout.Toggle(all, " Todo");
        if (na != all) loader.SetAllLayers(na);

        // Capas en dos columnas para que no se corten abajo.
        for (int i = 0; i < layers.Length; i += 2)
        {
            GUILayout.BeginHorizontal();
            ToggleLayer(i);
            if (i + 1 < layers.Length) ToggleLayer(i + 1);
            GUILayout.EndHorizontal();
        }
        GUILayout.EndArea();
    }

    void ToggleLayer(int i)
    {
        bool on = loader.IsLayerVisible(layers[i]);
        bool no = GUILayout.Toggle(on, " " + layerLabels[i], GUILayout.Width(116));
        if (no != on) loader.SetLayerVisible(layers[i], no);
    }

    void LegendRow(Color c, string txt)
    {
        GUILayout.BeginHorizontal();
        // Cuadradito de color fijo (14x14) como el swatch del visor HTML.
        var sq = new GUIStyle();
        sq.normal.background = GetWhiteTex();
        sq.border = new RectOffset(0, 0, 0, 0);
        sq.margin = new RectOffset(0, 6, 0, 0);
        GUI.color = c;
        GUILayout.Box("", sq, GUILayout.Width(14), GUILayout.Height(14));
        GUI.color = Color.white;
        GUILayout.Label(txt, new GUIStyle(GUI.skin.label) { fontSize = 12 });
        GUILayout.EndHorizontal();
    }
}