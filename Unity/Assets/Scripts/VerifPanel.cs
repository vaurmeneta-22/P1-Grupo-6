using System.Collections.Generic;
using System.Text;
using UnityEngine;

// FASE 5 - TRAZABILIDAD (igual a la pestana VERIFICACION del visor):
// para los 3 elementos traza (147 viga, 261 columna, 446 muro)
// muestra la cadena completa:
//   id -> tipo/seccion/material -> demanda N,V,M (COMBO, extremo mayor)
//   -> capacidad P-M de la seccion (M_ult, n_ok, alpha1, beta1).
// Todo desde AnalysisMap (mismos datos del HTML). Tecla V.
public class VerifPanel : MonoBehaviour
{
    public bool activo;
    Vector2 scroll;
    static readonly int[] traceTags = { 147, 261, 446 };

    void Update()
    {
        if (Input.GetKeyDown(KeyCode.V)) activo = !activo;
    }

    void OnGUI()
    {
        ElementInfoStyle.VerificationArea = new Rect();
        if (!activo) return;
        float w = Mathf.Min(1100, Screen.width - 24), h = Screen.height - 100;
        float x0 = (Screen.width - w) / 2f, y0 = 88f;
        int previousDepth = GUI.depth;
        GUI.depth = -20;
        ElementInfoStyle.VerificationArea = new Rect(x0, y0, w, h);
        GUISkin previous = ElementInfoStyle.Begin(ElementInfoStyle.VerificationArea);
        bool close = ElementInfoStyle.Header("Verificación", "TRAZABILIDAD  /  DEMANDA Y CAPACIDAD");
        scroll = GUILayout.BeginScrollView(scroll, false, false);
        if (!AnalysisMap.Loaded) { GUILayout.Label("Sin datos."); }
        else
        {
            var sb = new StringBuilder();
            sb.AppendLine("TRAZABILIDAD 147 / 261 / 446  (COMBO, extremo mayor)");
            sb.AppendLine();
            foreach (int tag in traceTags)
            {
                AnalysisMap.ElementInfo e;
                if (!AnalysisMap.ElementsByTag.TryGetValue(tag, out e) || e == null)
                { sb.AppendLine(tag + "\\tSIN ELEMENTO"); continue; }
                AnalysisMap.EndForces f = AnalysisMap.Fuerzas("COMBO", tag);
                double N = 0, V = 0, M = 0;
                double[] may = ExtremoMayor(f);
                if (may != null && may.Length >= 6)
                {
                    N = may[0];
                    V = System.Math.Sqrt(may[1] * may[1] + may[2] * may[2]);
                    M = System.Math.Sqrt(may[3] * may[3] + may[4] * may[4] + may[5] * may[5]);
                }
                AnalysisMap.PmInfo cap = CapacidadDe(e.section);
                double M_ult = 0; bool n_ok = false;
                if (cap != null) { M_ult = cap.M_ult; n_ok = cap.n_ok; }
                sb.AppendLine(tag + "\\t" + e.type + "\\t" + e.section + "\\t" + e.material +
                    "\\tN=" + Fmt(N) + "\\tV=" + Fmt(V) + "\\tM=" + Fmt(M) +
                    "\\tM_ult=" + Fmt(M_ult) + "\\tn_ok=" + (n_ok ? "SI" : "NO"));
            }
            sb.AppendLine();
            sb.AppendLine("Detalle P-M por seccion:");
            if (AnalysisMap.PmHa != null && AnalysisMap.PmHa.Count > 0)
            {
                foreach (KeyValuePair<string, AnalysisMap.PmInfo> kv in AnalysisMap.PmHa)
                {
                    AnalysisMap.PmInfo p = kv.Value;
                    if (p == null) continue;
                    sb.AppendLine("  [" + kv.Key + "]  P_HA=" + (p.P_HA != null ? p.P_HA.Length.ToString() : "0") +
                        "  M_HA=" + (p.M_HA != null ? p.M_HA.Length.ToString() : "0") +
                        "  alpha1=" + (p.alpha1.HasValue ? Fmt(p.alpha1.Value) : "-") +
                        "  beta1=" + (p.beta1.HasValue ? Fmt(p.beta1.Value) : "-") +
                        "  M_ult=" + Fmt(p.M_ult) + "  n_ok=" + (p.n_ok ? "SI" : "NO"));
                }
            }
            sb.AppendLine();
            sb.AppendLine("Capacidad demanda->capacidad (fila por elemento):");
            sb.AppendLine("tag\\ttipo\\tseccion\\tmaterial\\tN(kN)\\tV(kN)\\tM(kNm)\\tM_ult(kNm)\\tn_ok");
            foreach (int tag in traceTags)
            {
                AnalysisMap.ElementInfo e;
                if (!AnalysisMap.ElementsByTag.TryGetValue(tag, out e) || e == null) continue;
                AnalysisMap.EndForces f = AnalysisMap.Fuerzas("COMBO", tag);
                double N = 0, V = 0, M = 0;
                double[] may = ExtremoMayor(f);
                if (may != null && may.Length >= 6)
                {
                    N = may[0];
                    V = System.Math.Sqrt(may[1] * may[1] + may[2] * may[2]);
                    M = System.Math.Sqrt(may[3] * may[3] + may[4] * may[4] + may[5] * may[5]);
                }
                AnalysisMap.PmInfo cap = CapacidadDe(e.section);
                double M_ult = 0; bool n_ok = false;
                if (cap != null) { M_ult = cap.M_ult; n_ok = cap.n_ok; }
                sb.AppendLine(tag + "\\t" + e.type + "\\t" + e.section + "\\t" + e.material +
                    "\\t" + Fmt(N) + "\\t" + Fmt(V) + "\\t" + Fmt(M) +
                    "\\t" + Fmt(M_ult) + "\\t" + (n_ok ? "SI" : "NO"));
            }
            foreach (string line in sb.ToString().Replace("\r", "").Split('\n'))
            {
                if (string.IsNullOrWhiteSpace(line)) { GUILayout.Space(8); continue; }
                if (line.Contains("\\t"))
                {
                    string[] cells = line.Split(new[] { "\\t" }, System.StringSplitOptions.None);
                    float[] widths = new float[cells.Length];
                    for (int i = 0; i < widths.Length; i++) widths[i] = 104;
                    ElementInfoStyle.FixedRow(cells, widths, cells[0] == "tag");
                }
                else if (line.StartsWith("  [")) GUILayout.Label(line);
                else ElementInfoStyle.Section(line);
            }
        }
        GUILayout.EndScrollView();
        ElementInfoStyle.Note("N y V: kN · M y M_ult: kN·m · V: cerrar");
        ElementInfoStyle.End(previous);
        GUI.depth = previousDepth;
        if (close) { activo = false; ElementInfoStyle.VerificationArea = new Rect(); }
    }

    static double[] ExtremoMayor(AnalysisMap.EndForces f)
    {
        if (f == null) return null;
        double[] gi = f.gi != null ? f.gi : new double[6];
        double[] gj = f.gj != null ? f.gj : gi;
        double mi = Mag(gi, 3), mj = Mag(gj, 3);
        return mi >= mj ? gi : gj;
    }
    static double Mag(double[] v, int o)
    {
        return System.Math.Sqrt(v[o] * v[o] + v[o + 1] * v[o + 1] + v[o + 2] * v[o + 2]);
    }
    static AnalysisMap.PmInfo CapacidadDe(string section)
    {
        if (AnalysisMap.PmHa != null && !string.IsNullOrEmpty(section))
        {
            AnalysisMap.PmInfo p;
            if (AnalysisMap.PmHa.TryGetValue(section, out p)) return p;
        }
        return AnalysisMap.MomCurv;
    }
    static string Fmt(double v)
    {
        if (double.IsNaN(v) || double.IsInfinity(v)) return "-";
        return System.Math.Abs(v) < 1e-9 ? "0" : v.ToString("0.####");
    }
}