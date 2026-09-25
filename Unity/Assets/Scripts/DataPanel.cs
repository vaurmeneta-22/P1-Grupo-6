using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

// Panel DATOS (tecla B / boton DATOS): 6 pestanas sobre la API REAL verificada
// de AnalysisMap. Replica 1:1 las pestanas del visor HTML (Sismo, Mom-Curv,
// P-M, Reacciones, Tributarias, Diagramas) en una ventana derecha como #datosPanel.
public class DataPanel : MonoBehaviour
{
    public bool activo;
    string caso = "COMBO";
    string[] casos = { "COMBO", "G", "Q", "EX", "EY" };
    string[] tabs = { "Sismo", "Mom-Curv", "P-M", "Reacciones", "Tributarias", "Diagramas" };
    int tab;
    Vector2 scroll;

    string sismoCaso = "EX";
    string pmSec = "";
    string diagElem = "viga";
    string tribuQ = "";

    Vector2 tableScroll = Vector2.zero;

    public bool Visible { get { return activo; } }
    public void Toggle() { activo = !activo; }
    public void SetVisible(bool value) { activo = value; }

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.B)) Toggle();
    }

    void OnGUI()
    {
        ElementInfoStyle.DataArea = new Rect();
        if (!activo) return;
        int previousDepth = GUI.depth;
        GUI.depth = -10;
        Rect area = ElementInfoStyle.PanelRect();
        ElementInfoStyle.DataArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        bool close = ElementInfoStyle.Header("Datos del análisis", "RESULTADOS  /  CONSULTA POR CATEGORÍA");
        GUILayout.Space(10);
        for (int row = 0; row < tabs.Length; row += 3)
        {
            GUILayout.BeginHorizontal();
            for (int i = row; i < Mathf.Min(row + 3, tabs.Length); i++)
                if (ElementInfoStyle.Choice(tab == i, tabs[i]) && tab != i)
                { tab = i; scroll = Vector2.zero; tableScroll = Vector2.zero; }
            GUILayout.EndHorizontal();
        }
        scroll = GUILayout.BeginScrollView(scroll, false, false);
        if (!AnalysisMap.Loaded) ElementInfoStyle.Note("Sin datos (pulsa F6)");
        else
        switch (tab)
        {
            case 0: TabSismo(); break;
            case 1: TabMomCurv(); break;
            case 2: TabPM(); break;
            case 3: TabReacciones(); break;
            case 4: TabTributaria(); break;
            case 5: TabDiagramas(); break;
        }

        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);
        GUI.depth = previousDepth;
        if (close) { Toggle(); ElementInfoStyle.DataArea = new Rect(); }
    }

    // ----------------------- TAB 1: SISMO -----------------------
    // The HTML muestra Piso, z, G, Q, W, masa, F_X, F_Y, |F|, ux, uy y Rz.
    void TabSismo()
    {
        if (AnalysisMap.Sismo == null || AnalysisMap.Sismo.Count == 0)
        { GUILayout.Label("Sin datos de sismo en analysis_map."); return; }

        List<string> keys = AnalysisMap.Sismo.Keys.ToList();
        if (!keys.Contains(sismoCaso)) sismoCaso = keys[0];

        ElementInfoStyle.Section("SISMO POR PISO");
        GUILayout.BeginHorizontal();
        foreach (string k in keys)
        {
            bool b = ElementInfoStyle.Choice(sismoCaso == k, k);
            if (b) sismoCaso = k;
        }
        GUILayout.EndHorizontal();

        List<AnalysisMap.SismoRow> rows;
        if (!AnalysisMap.Sismo.TryGetValue(sismoCaso, out rows) || rows == null)
        { GUILayout.Label("Sin filas de sismo para " + sismoCaso); return; }

        float[] ws = { 46, 40, 48, 48, 48, 46, 50, 50, 44, 52, 52, 66 };
        string[] head = { "Piso", "z[m]", "G[kN]", "Q[kN]", "W[kN]", "masa[t]", "F_X[kN]", "F_Y[kN]", "|F|", "ux[mm]", "uy[mm]", "Rz[rad]" };
        List<string[]> cells = new List<string[]>();
        double sumF = 0;
        foreach (AnalysisMap.SismoRow r in rows)
        {
            double fabs = Math.Sqrt(r.FX * r.FX + r.FY * r.FY);
            sumF += fabs;
            cells.Add(new[]
            {
                r.piso.ToString(), Fmt(r.z, 2), Fmt(r.G, 0), Fmt(r.Q, 0), Fmt(r.W, 0),
                Fmt(r.masa / 1000.0, 1), Fmt(r.FX, 1), Fmt(r.FY, 1), Fmt(fabs, 1),
                Fmt(r.ux, 4), Fmt(r.uy, 4), FmtRz(r.Rz)
            });
        }
        DrawTableH(head, cells, ws);
        GUILayout.Label("Masa sismica W = G + 50% Q | Corte basal |F| = " + Fmt(sumF, 1) + " kN.");
    }

    // ------------------- TAB 2: MOMENTO-CURVATURA -------------------
    void TabMomCurv()
    {
        ElementInfoStyle.Section("MOM-CURV (columna 70x70, fiber, P = 0)");
        AnalysisMap.PmInfo p = AnalysisMap.MomCurv;
        if (p == null || p.M_fiber == null || p.M_fiber.Length == 0 ||
            p.phi_1m == null || p.phi_1m.Length == 0)
        { GUILayout.Label("Sin curva M-phi (genera figures con parte_d_fiber.py)."); return; }

        Rect rc = GUILayoutUtility.GetRect(488, 260);
        Plot2D.Draw(rc, p.phi_1m, p.M_fiber, "M vs phi (" + caso + ")", "M [kN-m]");

        int n = p.phi_1m.Length;
        double k0 = n > 1 ? (p.M_fiber[1] - p.M_fiber[0]) / (p.phi_1m[1] - p.phi_1m[0]) : 0;
        double Mfin = p.M_fiber[n - 1];
        double phimax = p.phi_1m[n - 1];
        GUILayout.Label("Rigidez inicial (EI~) = " + Fmt(k0 / 1000.0, 0) + " MN·m²  |  " +
                        "M_ultimo = " + Fmt(Mfin, 1) + " kN·m a phi = " + Fmt(phimax, 4) + " 1/m  |  " +
                        "convergencia " + (p.n_ok ? "OK" : "n/a"));
    }

    // ------------------- TAB 3: P-M FIBRA vs H.A. -------------------
    // Misma curva que el HTML: las dos curvas superpuestas en un solo canvas.
    void TabPM()
    {
        if (AnalysisMap.PmHa == null || AnalysisMap.PmHa.Count == 0)
        { GUILayout.Label("Sin P-M fibra/HA (genera figures/pm_*.json)."); return; }

        List<string> secs = AnalysisMap.PmHa.Keys.ToList();
        if (!secs.Contains(pmSec)) pmSec = secs[0];

        ElementInfoStyle.Section("P-M FIBRA vs H.A. (bloque ACI/NCh)");
        GUILayout.BeginHorizontal();
        foreach (string s in secs)
        {
            bool b = ElementInfoStyle.Choice(pmSec == s, s);
            if (b) pmSec = s;
        }
        GUILayout.EndHorizontal();

        AnalysisMap.PmInfo p = AnalysisMap.PmHa[pmSec];
        bool hasFib = p.M_fiber != null && p.M_fiber.Length > 0 &&
                      p.P_fiber != null && p.P_fiber.Length == p.M_fiber.Length;
        bool hasHa = p.M_HA != null && p.M_HA.Length > 0 &&
                     p.P_HA != null && p.P_HA.Length == p.M_HA.Length;
        if (!hasFib && !hasHa) { GUILayout.Label("Seccion sin curva P-M."); return; }

        var fib = new Plot2D.Series { x = p.M_fiber, y = p.P_fiber,
                                      color = new Color(0f, 1f, 1f, 1f) };
        var ha = new Plot2D.Series { x = p.M_HA, y = p.P_HA,
                                     color = new Color(1f, 0.85f, 0.2f, 1f) };
        Rect rc = GUILayoutUtility.GetRect(488, 320);
        Plot2D.DrawMulti(rc, "P-M " + pmSec + " (fibra vs H.A.)", "P [kN] / M [kN-m]", true, fib, ha);
        GUILayout.Label("Cian: fibra  ·  Naranja: bloque H.A. (alpha1 = " +
                        (p.alpha1.HasValue ? Fmt(p.alpha1.Value, 2) : "-") + " · beta1 = " +
                        (p.beta1.HasValue ? Fmt(p.beta1.Value, 2) : "-") + ")");

        if (hasFib)
        {
            double pT = double.MaxValue, pC = double.MinValue;
            for (int i = 0; i < p.P_fiber.Length; i++)
            {
                if (p.P_fiber[i] < pT) pT = p.P_fiber[i];
                if (p.P_fiber[i] > pC) pC = p.P_fiber[i];
            }
            GUILayout.Label("Puntas fibra: traccion = " + Fmt(pT, 0) + " kN · compresion = " + Fmt(pC, 0) + " kN");
        }
    }

    // ------------------- TAB 4: REACCIONES -------------------
    void TabReacciones()
    {
        if (AnalysisMap.Reacciones == null || AnalysisMap.Reacciones.Count == 0)
        { GUILayout.Label("Sin reacciones en analysis_map."); return; }

        ElementInfoStyle.Section("REACCIONES DE APOYO");
        GUILayout.BeginHorizontal();
        foreach (string c in casos)
        {
            if (!AnalysisMap.Reacciones.ContainsKey(c)) continue;
            bool b = ElementInfoStyle.Choice(caso == c, c);
            if (b) caso = c;
        }
        GUILayout.EndHorizontal();

        // Pintar en 3D: espejo del checkbox del visor (paintReactions/skin).
        bool pintar = AnalysisMode.Current != null && AnalysisMode.Current.PintarReac;
        bool np = ElementInfoStyle.Choice(pintar, "Reacciones 3D · " + (pintar ? "visibles" : "ocultas"));
        if (AnalysisMode.Current != null && np != pintar) AnalysisMode.Current.SetPintarReac(np);

        Dictionary<int, double[]> rmap;
        if (!AnalysisMap.Reacciones.TryGetValue(caso, out rmap) || rmap == null || rmap.Count == 0)
        { GUILayout.Label("Sin reacciones para el caso " + caso); return; }

        List<double[]> rows = new List<double[]>();
        double sum = 0;
        foreach (KeyValuePair<int, double[]> kv in rmap)
        {
            double[] r = kv.Value;
            double Rz = r != null && r.Length >= 3 ? r[2] : 0;
            double absR = r != null && r.Length >= 3 ? Math.Sqrt(r[0] * r[0] + r[1] * r[1] + r[2] * r[2]) : 0;
            rows.Add(new[] { kv.Key, Rz, absR });
            sum += Rz;
        }
        rows.Sort((a, b) => Math.Abs(b[1]).CompareTo(Math.Abs(a[1])));

        float[] ws = { 70, 110, 110 };
        List<string[]> cells = new List<string[]>();
        foreach (double[] t in rows)
            cells.Add(new[] { t[0].ToString("F0"), Fmt(t[1], 1), Fmt(t[2], 1) });
        DrawTableH(new[] { "Apoyo", "R_vert [kN]", "|R| [kN]" }, cells, ws);
        GUILayout.Label(rows.Count + " apoyos en el suelo (z=0) · Σ R_vert(" + caso + ") = " + Fmt(sum, 1) + " kN.");
    }

    // ------------------- TAB 5: TRIBUTARIAS -------------------
    void TabTributaria()
    {
        if (AnalysisMap.Tribu == null || AnalysisMap.Tribu.Count == 0)
        { GUILayout.Label("Sin tributarias en analysis_map."); return; }

        ElementInfoStyle.Section("TRIBUTARIAS POR VIGA (metodo 45°)");
        GUILayout.BeginHorizontal();
        GUILayout.Label("Buscar viga id:");
        tribuQ = GUILayout.TextField(tribuQ, GUILayout.Width(120));
        GUILayout.EndHorizontal();

        List<int> ids = new List<int>(AnalysisMap.Tribu.Keys);
        if (tribuQ.Length > 0)
            ids = ids.Where(id => id.ToString().Contains(tribuQ)).ToList();
        ids.Sort((a, b) => AnalysisMap.Tribu[b].area.CompareTo(AnalysisMap.Tribu[a].area));

        float[] ws = { 70, 60, 90, 90, 90, 90, 90 };
        List<string[]> cells = new List<string[]>();
        foreach (int id in ids)
        {
            AnalysisMap.TribuInfo t = AnalysisMap.Tribu[id];
            cells.Add(new[]
            {
                id.ToString(), t.section ?? "", Fmt(t.area, 1), Fmt(t.Wg, 0), Fmt(t.Wq, 0),
                Fmt(t.pG, 2), Fmt(t.pQ, 2)
            });
        }
        DrawTableH(new[] { "Viga", "Sec.", "A_trib[m2]", "W_G[kN]", "W_Q[kN]", "p_G[kN/m]", "p_Q[kN/m]" },
                   cells, ws);
        GUILayout.Label(ids.Count + " vigas con carga de losa (G y Q) sobre " + AnalysisMap.Tribu.Count + " totales.");
    }

    // ------------------- TAB 6: DIAGRAMAS 2D -------------------
    // Mismo dibujo que el visor HTML (drawDiagramPanels): N/V/M apilados.
    void TabDiagramas()
    {
        if (AnalysisMap.Diagramas == null || AnalysisMap.Diagramas.Count == 0)
        { GUILayout.Label("Sin diagramas en analysis_map."); return; }

        ElementInfoStyle.Section("DIAGRAMAS 2D (N / V / M apilados)");

        // selector de caso (los disponibles en el mapa)
        List<string> casosDisp = AnalysisMap.Diagramas.Keys.ToList();
        if (!casosDisp.Contains(caso)) caso = casosDisp[0];
        GUILayout.BeginHorizontal();
        GUILayout.Label("Caso:");
        foreach (string c in casosDisp)
        {
            bool b = ElementInfoStyle.Choice(caso == c, c);
            if (b) caso = c;
        }
        GUILayout.EndHorizontal();

        GUILayout.BeginHorizontal();
        GUILayout.Label("Elem:");
        foreach (string e in new[] { "viga", "columna", "muro" })
        {
            bool b = ElementInfoStyle.Choice(diagElem == e, e);
            if (b) diagElem = e;
        }
        GUILayout.EndHorizontal();

        AnalysisMap.DiagInfo d = AnalysisMap.Diagrama(caso, diagElem);
        if (d == null || d.x == null || d.x.Length == 0)
        { GUILayout.Label("Sin diagrama " + diagElem + " para el caso " + caso + "."); return; }

        Rect rc = GUILayoutUtility.GetRect(488, 360);
        Plot2D.DrawDiag(rc, d);

        string info = diagElem + " " + d.tag + " · " + d.seccion + " · L " + d.L.ToString("F2") + " m";
        if (!string.IsNullOrEmpty(d.piso)) info += " · " + d.piso;
        if (d.hasQ) info += " · q = " + Fmt(d.q, 3) + " kN/m · resid V = " + Fmt(d.resid, 2) +
                            " · resid Mj = " + Fmt(d.resMJ, 2);
        GUILayout.Label(info);
        GUILayout.Label("x sobre el elemento [m]. N verde, V naranja, M cian (maximos marcados).");
    }

    // ------------------- helpers de tabla y numeros -------------------
    // Tabla con scroll horizontal y vertical (columnas anchas en panel angosto).
    void DrawTableH(string[] headers, List<string[]> cells, float[] widths)
    {
        // Keep wide datasets scrollable; never squeeze or truncate numerical values.
        float[] readableWidths = new float[widths.Length];
        for (int i = 0; i < widths.Length; i++) readableWidths[i] = Mathf.Max(widths[i], 112);
        tableScroll = GUILayout.BeginScrollView(tableScroll, false, true,
            GUILayout.Height(280), GUILayout.ExpandWidth(true));
        ElementInfoStyle.FixedRow(headers, readableWidths, true);
        foreach (string[] row in cells) ElementInfoStyle.FixedRow(row, readableWidths, false);
        GUILayout.EndScrollView();
    }

    static string Fmt(double v)
    {
        if (double.IsNaN(v) || double.IsInfinity(v)) return "-";
        double a = Math.Abs(v);
        if (a >= 100000d) return (v / 1000d).ToString("F0") + "k";
        if (a >= 100d) return v.ToString("F0");
        return v.ToString("F1");
    }

    static string Fmt(double v, int dec)
    {
        if (double.IsNaN(v) || double.IsInfinity(v)) return "-";
        return v.ToString("F" + Mathf.Clamp(dec, 0, 6));
    }

    // Rz suele ser muy pequeno: notacion exponencial cuando |v| < 1e-3.
    static string FmtRz(double v)
    {
        if (double.IsNaN(v) || double.IsInfinity(v)) return "-";
        return Math.Abs(v) < 1e-3 ? v.ToString("E2") : v.ToString("F4");
    }
}
