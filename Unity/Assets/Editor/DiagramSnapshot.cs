using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

// Renderiza los diagramas N/V/M a PNG sin necesidad de GPU ni de Play Mode.
//
// Unity en -batchmode -nographics no tiene swap chain, asi que
// ScreenCapture.CaptureScreenshot no produce nada. Lo que interesa comprobar de
// verdad es que las curvas son las correctas, y eso se puede rasterizar sobre
// una Texture2D y escribir con EncodeToPNG.
//
// Usa la MISMA formula y los MISMOS datos que la ficha, y dibuja el mismo
// apilado de tres bandas que Plot2D.DrawDiag, de modo que la imagen sirve como
// revision visual de la ficha.
public static class DiagramSnapshot
{
    // Fuera de Unity/Temp: esa carpeta se borra al cerrar el editor.
    const string OutDir = "Builds/DiagramShots";
    const int W = 620, H = 250;
    const int PX_L = 52, PX_R = 16, PT = 26, PB = 26;

    [MenuItem("Lab/Volcar diagramas a PNG")]
    public static void Run()
    {
        int rc = Build();
        if (Application.isBatchMode) EditorApplication.Exit(rc);
    }

    static int Build()
    {
        string dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", OutDir));
        Directory.CreateDirectory(dir);

        if (!AnalysisMap.Loaded)
        {
            string am = Path.Combine(Application.streamingAssetsPath, "analysis_map.json");
            if (!AnalysisMap.Load(am))
            {
                Debug.LogError("[Snapshot] no se cargo el mapa: " + AnalysisMap.LoadError);
                return 1;
            }
        }

        // Un elemento por familia, y dentro de cada una el que mas tramos FE
        // tenga (las vigas subdivididas concentran el riesgo) y el primero.
        var tags = AnalysisMap.ElementsByTag.Values
            .Where(v => v.type != "loza")
            .GroupBy(v => v.type)
            .ToDictionary(g => g.Key, g => g.OrderBy(v => v.id).ToList());

        string[] quiere = { "G", "Q", "EX", "EY", "COMBO" };
        int n = 0;
        foreach (string tipo in new[] { "beam_x", "beam_y", "column", "wall", "steel_beam", "steel_column" })
        {
            if (!tags.ContainsKey(tipo)) continue;
            int primero = tags[tipo].Select(v => v.id).OrderBy(k => k).First();
            int conFracciones = tags[tipo]
                .Where(v => AnalysisMap.BeamFractionElems != null &&
                            AnalysisMap.BeamFractionElems.ContainsKey(v.id) &&
                            AnalysisMap.BeamFractionElems[v.id].Count > 1)
                .OrderByDescending(v => AnalysisMap.BeamFractionElems[v.id].Count)
                .Select(v => v.id).DefaultIfEmpty(primero).First();

            foreach (int tag in new[] { primero, conFracciones }.Distinct())
                for (int plano = 0; plano < 2; plano++)
                {
                    var r = ElementDiagrams.Construir(tag, "COMBO", plano);
                    if (r.error != null) continue;
                    string comp = plano == 0 ? "Vz_My" : "Vy_Mz";
                    foreach (string caso in quiere)
                    {
                        var rc2 = ElementDiagrams.Construir(tag, caso, plano);
                        if (rc2.error != null) continue;
                        string ruta = Path.Combine(dir,
                            string.Format("{0}_{1}_{2}_{3}.png", tipo, tag, caso, comp));
                        File.WriteAllBytes(ruta, Png(rc2.diag, plano));
                        n++;
                    }
                }
        }
        Debug.Log("[Snapshot] " + n + " PNG escritos en " + dir);
        return n > 0 ? 0 : 1;
    }

    static byte[] Png(AnalysisMap.DiagInfo d, int plano)
    {
        var tx = new Texture2D(W, H, TextureFormat.RGBA32, false);
        var bg = new Color(0.10f, 0.12f, 0.14f, 1f);
        var gr = new Color(0.25f, 0.30f, 0.35f, 1f);
        var mid = new Color(0.30f, 0.30f, 0.45f, 1f);
        Fill(tx, bg);

        int NW = W - PX_L - PX_R;
        int NH = (H - PT - PB - 6) / 3;
        Color[] col = { new Color(0.18f, 0.80f, 0.44f), new Color(1f, 0.70f, 0.28f), new Color(0f, 1f, 1f) };
        double[][] series = { d.N, d.V, d.M };
        string[] nombre = { "N [kN]", plano == 0 ? "Vz [kN]" : "Vy [kN]", plano == 0 ? "My [kN-m]" : "Mz [kN-m]" };
        bool[] relleno = { false, true, true };

        for (int s = 0; s < 3; s++)
        {
            int top = PT + s * (NH + 3), bot = top + NH, midS = top + NH / 2;
            int eT = H - top, eB = H - bot, eM = H - midS;
            Line(tx, PX_L, eT, PX_L + NW, eT, gr);
            Line(tx, PX_L, eB, PX_L + NW, eB, gr);
            for (int gx = PX_L; gx <= PX_L + NW; gx++)
            { Put(tx, gx, eM, mid); Put(tx, gx, eM - 1, mid); }

            double[] v = series[s];
            if (v == null || v.Length == 0 || d.L <= 0) continue;
            double maxA = Math.Max(1e-9, v.Max(Math.Abs));
            maxA *= 1.15;

            int[] px = new int[v.Length], py = new int[v.Length];
            for (int i = 0; i < v.Length; i++)
            {
                px[i] = PX_L + (int)Math.Round(NW * (d.x[i] / d.L));
                py[i] = eM - (int)Math.Round((NH / 2.0) * (v[i] / maxA));
            }
            if (relleno[s])
                for (int i = 0; i < v.Length - 1; i++)
                    Band(tx, px[i], py[i], px[i + 1], py[i + 1], eM, col[s]);
            for (int i = 0; i < v.Length - 1; i++)
                Seg(tx, px[i], py[i], px[i + 1], py[i + 1], col[s]);

            int imax = 0;
            for (int i = 1; i < v.Length; i++) if (Math.Abs(v[i]) > Math.Abs(v[imax])) imax = i;
            for (int dx = -3; dx <= 3; dx++)
                for (int dy = -3; dy <= 3; dy++)
                    if (dx * dx + dy * dy <= 9) Put(tx, px[imax] + dx, py[imax] + dy, col[s]);
        }

        string txt = d.tipo + " " + d.tag + "  " + d.seccion + "  L=" + d.L.ToString("F2") +
                     " m   x-z: " + nombre[1] + " / " + nombre[2] +
                     (d.hasQ ? "   q=" + d.q.ToString("F2") + " kN/m" : "");
        Barcode(tx, txt);
        return tx.EncodeToPNG();
    }

    static void Fill(Texture2D t, Color c) { for (int y = 0; y < t.height; y++) for (int x = 0; x < t.width; x++) t.SetPixel(x, y, c); }
    static void Put(Texture2D t, int x, int y, Color c) { if (x >= 0 && y >= 0 && x < t.width && y < t.height) t.SetPixel(x, y, c); }
    static void Line(Texture2D t, int x0, int y0, int x1, int y1, Color c)
    {
        int n = Mathf.Max(Math.Abs(x1 - x0), Math.Abs(y1 - y0));
        if (n == 0) { Put(t, x0, y0, c); return; }
        for (int i = 0; i <= n; i++) Put(t, x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, c);
    }
    static void Seg(Texture2D t, int x0, int y0, int x1, int y1, Color c) { Line(t, x0, y0, x1, y1, c); }
    static void Band(Texture2D t, int x0, int y0, int x1, int y1, int eM, Color c)
    {
        int n = Math.Abs(x1 - x0);
        if (n == 0) n = 1;
        for (int i = 0; i <= n; i++)
        {
            int x = x1 == x0 ? x0 : x0 + (x1 - x0) * i / n;
            int a = Math.Min(y0, y1), b = Math.Max(y0, y1);
            for (int y = a; y <= b; y++) Put(t, x, y, new Color(c.r, c.g, c.b, 0.35f));
        }
    }
    // Codigo de barras 3x5 como "texto", suficiente para leer el encabezado.
    static readonly Dictionary<char, int> GLIF = new Dictionary<char, int>
    {
        {'0',0x1F},{'1',0x00},{'2',0x1D},{'3',0x15},{'4',0x07},{'5',0x25},
        {'6',0x27},{'7',0x05},{'8',0x2F},{'9',0x17},{'A',0x3F},{'B',0x3D},
        {'C',0x29},{'D',0x39},{'E',0x2D},{'F',0x2B},{'G',0x21},{'H',0x33},
        {'I',0x11},{'J',0x19},{'K',0x37},{'L',0x31},{'M',0x35},{'N',0x18},
        {'O',0x3E},{'P',0x3C},{'Q',0x1A},{'R',0x3B},{'S',0x24},{'T',0x04},
        {'U',0x3A},{'V',0x32},{'W',0x36},{'X',0x1A},{'Y',0x12},{'Z',0x02},
        {' ',0x00},{'.',0x20},{',',0x20},{':',0x22},{'-',0x2A},{'[',0x2E},
        {']',0x2A},{'/',0x12},{'x',0x16},{'z',0x0E},{'+',0x1A},{'*',0x1A},
        {'=',0x14},{'_',0x00},{'%',0x12}
    };
    static void Barcode(Texture2D t, string s)
    {
        var c = new Color(0.85f, 0.85f, 0.85f);
        int x0 = 6, y0 = 8;
        s = s.ToUpperInvariant().Replace('_', ' ');
        for (int i = 0; i < s.Length && x0 + i * 4 < t.width; i++)
        {
            int g;
            if (!GLIF.TryGetValue(s[i], out g)) continue;
            for (int col = 0; col < 3; col++)
                for (int row = 0; row < 5; row++)
                    if ((g & (1 << (col * 5 + row))) != 0)
                        for (int dy = 0; dy < 2; dy++)
                            Put(t, x0 + i * 4 + col, y0 + (4 - row) * 2 + dy, c);
        }
    }
}
