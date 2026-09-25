using UnityEngine;
using System.Collections.Generic;

// Buscador del modo Visualizacion: localiza un elemento por tipo/id, enfoca la
// camara y aplica un resaltado temporal reversible.
public class ElementSearchPanel : MonoBehaviour
{
    EdificioLoader loader;
    CameraController cameraController;
    CameraController.ViewState savedView;
    bool hasSavedView;
    bool visible;

    readonly string[] labels = { "Viga", "Columna", "Losa", "Muro", "Metalica" };
    readonly string[][] types = {
        new [] { "beam_x", "beam_y", "steel_beam" },
        new [] { "column", "steel_column" },
        new [] { "loza" },
        new [] { "wall" },
        new [] { "steel_beam", "steel_column" }
    };
    int typeIdx;
    string idText = "";
    string status = "Ingresa tipo e ID.";
    Vector2 scroll;

    readonly Dictionary<Renderer, Material[]> savedMaterials = new Dictionary<Renderer, Material[]>();
    Material highlightMat;

    public bool Visible { get { return visible; } }

    public void Setup(EdificioLoader l)
    {
        loader = l;
        Camera cam = Camera.main;
        if (cam != null) cameraController = cam.GetComponent<CameraController>();
    }

    public void Toggle()
    {
        SetVisible(!visible);
    }

    public void SetVisible(bool value)
    {
        if (visible == value) return;
        visible = value;
        if (!visible) ClearSearch(true);
    }

    void OnGUI()
    {
        if (!visible)
        {
            ElementInfoStyle.SearchArea = new Rect();
            return;
        }

        Rect area = new Rect(Screen.width - Mathf.Min(430, Screen.width - 24) - 12, 88,
                             Mathf.Min(430, Screen.width - 24), 330);
        ElementInfoStyle.SearchArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        bool close = ElementInfoStyle.Header("Buscar elemento", "VISUALIZACION / LOCALIZADOR");
        scroll = GUILayout.BeginScrollView(scroll, false, false);

        ElementInfoStyle.Section("TIPO");
        GUILayout.BeginHorizontal();
        for (int i = 0; i < labels.Length; i++)
        {
            if (ElementInfoStyle.Choice(typeIdx == i, labels[i])) typeIdx = i;
        }
        GUILayout.EndHorizontal();

        ElementInfoStyle.Section("ID");
        idText = GUILayout.TextField(idText);
        GUILayout.BeginHorizontal();
        if (GUILayout.Button("Buscar")) Search();
        if (GUILayout.Button("Limpiar")) ClearSearch(true);
        GUILayout.EndHorizontal();

        ElementInfoStyle.Section("ESTADO");
        ElementInfoStyle.Note(status);

        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);
        if (close) SetVisible(false);
    }

    void Search()
    {
        int id;
        if (!int.TryParse(idText.Trim(), out id))
        {
            status = "ID invalido.";
            return;
        }
        if (loader == null || loader.ElementsGroup == null)
        {
            status = "Modelo no disponible.";
            return;
        }

        ElementTag found = null;
        foreach (ElementTag tag in loader.ElementsGroup.GetComponentsInChildren<ElementTag>(true))
        {
            if (tag.elementId != id) continue;
            if (!MatchesSelectedType(tag.type)) continue;
            found = tag;
            break;
        }

        if (found == null)
        {
            ClearSearch(false);
            status = "No se encontro " + labels[typeIdx] + " id " + id + ".";
            return;
        }

        if (!hasSavedView && cameraController != null)
        {
            savedView = cameraController.CaptureView();
            hasSavedView = savedView.valid;
        }

        EnsureLayerVisible(found.type);
        ClearHighlightOnly();
        Highlight(found.gameObject);
        Frame(found.gameObject);
        status = "Encontrado: " + labels[typeIdx] + " " + id + " (tipo " + found.type + ").";
    }

    bool MatchesSelectedType(string type)
    {
        string[] allowed = types[typeIdx];
        for (int i = 0; i < allowed.Length; i++)
            if (type == allowed[i]) return true;
        return false;
    }

    void Highlight(GameObject root)
    {
        Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
        Material mat = HighlightMat();
        foreach (Renderer r in renderers)
        {
            if (r == null || savedMaterials.ContainsKey(r)) continue;
            savedMaterials[r] = r.sharedMaterials;
            Material[] mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = mat;
            r.sharedMaterials = mats;
        }
    }

    void Frame(GameObject root)
    {
        Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0 || cameraController == null) return;
        Bounds b = renderers[0].bounds;
        for (int i = 1; i < renderers.Length; i++) b.Encapsulate(renderers[i].bounds);
        b.Expand(1.2f);
        cameraController.FrameBounds(b);
    }

    void EnsureLayerVisible(string type)
    {
        if (loader == null) return;
        if (type == "column") loader.SetLayerVisible("columnas", true);
        else if (type == "beam_x") loader.SetLayerVisible("vigasX", true);
        else if (type == "beam_y") loader.SetLayerVisible("vigasY", true);
        else if (type == "wall") loader.SetLayerVisible("muros", true);
        else if (type == "loza") loader.SetLayerVisible("losas", true);
        else if (type == "steel_beam" || type == "steel_column") loader.SetLayerVisible("metálicas", true);
    }

    void ClearSearch(bool restoreView)
    {
        ClearHighlightOnly();
        if (restoreView && hasSavedView && cameraController != null)
        {
            cameraController.RestoreView(savedView);
            hasSavedView = false;
        }
        status = "Busqueda limpia.";
    }

    void ClearHighlightOnly()
    {
        foreach (KeyValuePair<Renderer, Material[]> kv in savedMaterials)
            if (kv.Key != null) kv.Key.sharedMaterials = kv.Value;
        savedMaterials.Clear();
    }

    Material HighlightMat()
    {
        if (highlightMat != null) return highlightMat;
        Shader s = Shader.Find("Universal Render Pipeline/Lit");
        if (s == null) s = Shader.Find("Standard");
        highlightMat = new Material(s);
        highlightMat.color = new Color(1f, 0.92f, 0.12f, 1f);
        if (highlightMat.HasProperty("_BaseColor")) highlightMat.SetColor("_BaseColor", highlightMat.color);
        if (highlightMat.HasProperty("_EmissionColor"))
        {
            highlightMat.EnableKeyword("_EMISSION");
            highlightMat.SetColor("_EmissionColor", new Color(1f, 0.7f, 0f) * 0.35f);
        }
        return highlightMat;
    }

    void OnDestroy()
    {
        ClearHighlightOnly();
        if (highlightMat != null) Destroy(highlightMat);
    }
}
