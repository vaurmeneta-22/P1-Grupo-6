using UnityEngine;

// Presentation only: no structural data, conversions or analysis live here.
public static class ElementInfoStyle
{
    static GUISkin skin;
    static GUIStyle title, section, muted, key, value, cell, heading;
    static Texture2D surface, stripe, button;
    public static Rect VisualizationArea, AnalysisArea, LayerArea, DataArea, ControlsArea, ToolbarArea, VerificationArea, SQ4Area, ModificationArea, SearchArea;
    public static bool SQ4Dragging;

    public static bool PointerOverPanel
    {
        get
        {
            Vector2 p = new Vector2(Input.mousePosition.x, Screen.height - Input.mousePosition.y);
            bool analysis = AnalysisMode.Current != null && AnalysisMode.Current.Active;
            return SQ4Dragging || DataArea.Contains(p) || ModificationArea.Contains(p) || SearchArea.Contains(p) || ControlsArea.Contains(p) || ToolbarArea.Contains(p) || VerificationArea.Contains(p) || SQ4Area.Contains(p) || LayerArea.Contains(p) || (analysis ? AnalysisArea : VisualizationArea).Contains(p);
        }
    }

    public static Rect PanelRect()
    {
        float w = Mathf.Min(610, Screen.width - 24);
        return new Rect(Screen.width - w - 12, 88, w, Mathf.Max(100, Screen.height - 106));
    }

    static Texture2D Solid(Color color)
    {
        var texture = new Texture2D(1, 1) { hideFlags = HideFlags.HideAndDontSave };
        texture.SetPixel(0, 0, color);
        texture.Apply();
        return texture;
    }

    static GUIStyle TextStyle(int size, Color color, FontStyle weight = FontStyle.Normal)
    {
        var s = new GUIStyle(skin.label) { fontSize = size, fontStyle = weight, wordWrap = true };
        s.normal.textColor = color;
        return s;
    }

    static void Ensure()
    {
        if (skin != null) return;
        skin = Object.Instantiate(GUI.skin);
        skin.hideFlags = HideFlags.HideAndDontSave;
        surface = Solid(new Color(0.075f, 0.10f, 0.14f, 1));
        stripe = Solid(new Color(0.11f, 0.15f, 0.20f, 1));
        button = Solid(new Color(0.17f, 0.24f, 0.32f, 1));
        skin.label.fontSize = 18;
        skin.label.wordWrap = true;
        skin.label.normal.textColor = new Color(0.91f, 0.94f, 0.98f);
        skin.label.padding = new RectOffset(4, 4, 5, 5);
        skin.box.normal.background = surface;
        skin.box.border = new RectOffset();
        skin.box.padding = new RectOffset(18, 18, 14, 14);
        skin.toggle.fontSize = 17;
        skin.toggle.normal.textColor = skin.label.normal.textColor;
        skin.textField.fontSize = 18;
        skin.textField.normal.background = stripe;
        skin.textField.normal.textColor = Color.white;
        skin.textField.padding = new RectOffset(8, 8, 6, 6);
        skin.textArea = new GUIStyle(skin.textField) { wordWrap = false };
        skin.button.fontSize = 17;
        skin.button.fixedHeight = 40;
        skin.button.normal.background = button;
        skin.button.normal.textColor = Color.white;
        title = TextStyle(24, Color.white, FontStyle.Bold);
        section = TextStyle(16, new Color(0.39f, 0.77f, 1), FontStyle.Bold);
        muted = TextStyle(16, new Color(0.65f, 0.73f, 0.82f));
        key = TextStyle(17, new Color(0.65f, 0.73f, 0.82f));
        value = TextStyle(18, new Color(0.93f, 0.96f, 1));
        cell = new GUIStyle(value) { alignment = TextAnchor.MiddleRight, stretchWidth = true };
        heading = new GUIStyle(key) { fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleRight };
    }

    public static GUISkin Begin(Rect area)
    {
        Ensure();
        var previous = GUI.skin;
        GUI.skin = skin;
        GUILayout.BeginArea(area, skin.box);
        return previous;
    }

    public static void End(GUISkin previous)
    {
        GUILayout.EndArea();
        GUI.skin = previous;
    }

    public static bool Header(string name, string context)
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label(name, title, GUILayout.ExpandWidth(true));
        bool close = GUILayout.Button("×", GUILayout.Width(40));
        GUILayout.EndHorizontal();
        GUILayout.Label(context, muted);
        return close;
    }

    public static void Section(string label)
    {
        GUILayout.Space(14);
        GUILayout.Label(label, section);
        Rect line = GUILayoutUtility.GetRect(0, 1, GUILayout.ExpandWidth(true));
        if (Event.current.type == EventType.Repaint) GUI.DrawTexture(line, button);
        GUILayout.Space(5);
    }

    public static void Pair(string label, string text)
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label(label, key, GUILayout.Width(Mathf.Min(190, PanelRect().width * 0.34f)));
        GUILayout.Label(text, value, GUILayout.MinWidth(0), GUILayout.ExpandWidth(true));
        GUILayout.EndHorizontal();
    }

    public static bool Choice(bool selected, string text)
    {
        Color old = GUI.backgroundColor;
        GUI.backgroundColor = selected ? new Color(0.38f, 0.80f, 1f) : Color.white;
        var style = new GUIStyle(skin.button) { fontSize = 17 };
        style.onNormal.background = button;
        style.onNormal.textColor = Color.white;
        bool result = GUILayout.Toggle(selected, text, style, GUILayout.MinWidth(0), GUILayout.ExpandWidth(true));
        GUI.backgroundColor = old;
        return result;
    }

    public static void FixedRow(string[] cells, float[] widths, bool header)
    {
        GUILayout.BeginHorizontal();
        for (int i = 0; i < cells.Length && i < widths.Length; i++)
        {
            var style = new GUIStyle(header ? heading : cell);
            style.normal.background = stripe;
            if (i == 0) style.alignment = TextAnchor.MiddleLeft;
            GUILayout.Label(cells[i], style, GUILayout.Width(widths[i]), GUILayout.MinHeight(38));
        }
        GUILayout.EndHorizontal();
    }

    public static void Note(string text) { GUILayout.Label(text, muted); }

    public static void Row(string[] cells, float[] weights, bool header = false)
    {
        float width = Mathf.Max(80, PanelRect().width - 62);
        float total = 0;
        for (int i = 0; i < cells.Length; i++) total += weights[i];
        var row = new GUIStyle { padding = new RectOffset(), margin = new RectOffset(0, 0, 1, 1) };
        row.normal.background = stripe;
        GUILayout.BeginHorizontal(row);
        for (int i = 0; i < cells.Length; i++)
        {
            var style = new GUIStyle(header ? heading : cell);
            if (i == 0) style.alignment = TextAnchor.MiddleLeft;
            GUILayout.Label(cells[i], style, GUILayout.Width(width * weights[i] / total));
        }
        GUILayout.EndHorizontal();
    }
}
