using System;
using UnityEngine;

// Grafica 2D estilo visor (textura polilinea con grid, ejes, titulo).
// Plot2D.Make(xs, ys, titulo, unidad, W, H) -> Texture2D;
// Plot2D.Draw(rect, xs, ys, titulo, unidad) lo pinta con GUI.DrawTexture.
// Ademas: DrawMulti (series multiples) y DrawDiag / DrawPMLab (canvas del visor).
public static class Plot2D
{
    public static Texture2D Make(double[] xs, double[] ys, string title, string unit, int W = 520, int H = 220)
    {
        var tx = new Texture2D(W, H, TextureFormat.RGBA32, false);
        var bg = new Color(0.10f, 0.12f, 0.14f, 1f);
        var gr = new Color(0.22f, 0.26f, 0.30f, 1f);
        var ax = new Color(0.9f, 0.9f, 0.9f, 1f);
        var ln = new Color(1f, 0.75f, 0.15f, 1f);
        var pk = new Color(1f, 0.3f, 0.2f, 1f);
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                tx.SetPixel(x, y, bg);

        int padL = 46, padR = 12, padT = 30, padB = 38;
        int x0 = padL, x1 = W - padR, y0 = padT, y1 = H - padB;
        int pw = x1 - x0, ph = y1 - y0;

        double xmin = 0, xmax = 1, ymin = 0, ymax = 1;
        int n = xs != null ? xs.Length : 0;
        if (n > 0) { xmin = xmax = xs[0]; for (int i = 1; i < n; i++) { if (xs[i] < xmin) xmin = xs[i]; if (xs[i] > xmax) xmax = xs[i]; } }
        if (ys != null && ys.Length > 0) { ymin = ymax = ys[0]; for (int i = 1; i < ys.Length; i++) { if (double.IsNaN(ys[i]) || double.IsInfinity(ys[i])) continue; if (ys[i] < ymin) ymin = ys[i]; if (ys[i] > ymax) ymax = ys[i]; } }
        if (xmax - xmin < 1e-9) { xmin -= 1; xmax += 1; }
        if (ymax - ymin < 1e-9) { ymin -= 1; ymax += 1; }
        double mx = (xmax - xmin) * 0.08, my = (ymax - ymin) * 0.14;
        xmin -= mx; xmax += mx; ymin -= my; ymax += my;

        for (int g = 0; g <= 4; g++)
        {
            int gx = x0 + (int)Math.Round(g * pw / 4.0);
            for (int y = y0; y <= y1; y++) tx.SetPixel(gx, y, gr);
            int gy = y0 + (int)Math.Round(g * ph / 4.0);
            for (int x = x0; x <= x1; x++) tx.SetPixel(x, gy, gr);
        }
        for (int x = x0; x <= x1; x++) { tx.SetPixel(x, y0, ax); tx.SetPixel(x, y1, ax); }
        for (int y = y0; y <= y1; y++) { tx.SetPixel(x0, y, ax); tx.SetPixel(x1, y, ax); }

        for (int i = 1; i < n; i++)
        {
            if (xs == null || ys == null || i >= xs.Length || i >= ys.Length) continue;
            double xa = xs[i - 1], xb = xs[i];
            double ya = ys[i - 1], yb = ys[i];
            if (double.IsNaN(ya) || double.IsNaN(yb) || double.IsInfinity(ya) || double.IsInfinity(yb)) continue;
            int X0 = x0 + (int)Math.Round((xa - xmin) / (xmax - xmin) * pw);
            int Y0 = y0 + (int)Math.Round((ya - ymin) / (ymax - ymin) * ph);
            int X1 = x0 + (int)Math.Round((xb - xmin) / (xmax - xmin) * pw);
            int Y1 = y0 + (int)Math.Round((yb - ymin) / (ymax - ymin) * ph);
            Line(tx, X0, Y0, X1, Y1, ln);
        }

        int imax = -1;
        if (ys != null)
        {
            for (int i = 0; i < ys.Length; i++)
                if (!double.IsNaN(ys[i]) && !double.IsInfinity(ys[i]) && (imax < 0 || ys[i] > ys[imax])) imax = i;
        }
        if (imax >= 0 && xs != null && imax < xs.Length)
        {
            int X = x0 + (int)Math.Round((xs[imax] - xmin) / (xmax - xmin) * pw);
            int Y = y0 + (int)Math.Round((ys[imax] - ymin) / (ymax - ymin) * ph);
            for (int a = 0; a <= 8; a++)
            {
                tx.SetPixel(Mathf.Clamp(X + a, 0, W - 1), Mathf.Clamp(Y, 0, H - 1), pk);
                tx.SetPixel(Mathf.Clamp(X - a, 0, W - 1), Mathf.Clamp(Y, 0, H - 1), pk);
                tx.SetPixel(Mathf.Clamp(X, 0, W - 1), Mathf.Clamp(Y + a, 0, H - 1), pk);
                tx.SetPixel(Mathf.Clamp(X, 0, W - 1), Mathf.Clamp(Y - a, 0, H - 1), pk);
            }
        }

        tx.Apply();
        return tx;
    }

    public static void Draw(Rect rc, double[] xs, double[] ys, string title, string unit)
    {
        var st = new GUIStyle();
        st.fontSize = 12;
        st.normal.textColor = new Color(0.95f, 0.95f, 0.95f, 1f);
        var st2 = new GUIStyle(st);
        st2.fontSize = 11;
        st2.normal.textColor = new Color(0.75f, 0.8f, 0.85f, 1f);
        Texture2D t = Make(xs, ys, title, unit, (int)rc.width, (int)rc.height);
        GUI.DrawTexture(rc, t);
        GUI.Label(new Rect(rc.x + 12, rc.y + 6, rc.width - 24, 20), title, st);
        GUI.Label(new Rect(rc.x + 12, rc.yMax - 22, rc.width - 24, 18), unit, st2);
        UnityEngine.Object.Destroy(t);
    }

    static void Line(Texture2D tx, int X0, int Y0, int X1, int Y1, Color c)
    {
        int dx = Math.Abs(X1 - X0), dy = Math.Abs(Y1 - Y0);
        int sx = X0 < X1 ? 1 : -1, sy = Y0 < Y1 ? 1 : -1;
        int err = dx - dy;
        while (true)
        {
            if (X0 >= 0 && X0 < tx.width && Y0 >= 0 && Y0 < tx.height) tx.SetPixel(X0, Y0, c);
            if (X0 == X1 && Y0 == Y1) break;
            int e2 = 2 * err;
            if (e2 > -dy) { err -= dy; X0 += sx; }
            if (e2 < dx) { err += dx; Y0 += sy; }
        }
    }

    // ---------------- Series multiples (P-M fibra + HA) ----------------

    public struct Series
    {
        public double[] x;
        public double[] y;
        public Color color;
    }

    public static void DrawMulti(Rect rc, string title, string unit, bool mirrorX, params Series[] series)
    {
        var st = new GUIStyle();
        st.fontSize = 12;
        st.normal.textColor = new Color(0.95f, 0.95f, 0.95f, 1f);
        var st2 = new GUIStyle(st);
        st2.fontSize = 11;
        st2.normal.textColor = new Color(0.75f, 0.8f, 0.85f, 1f);
        Texture2D t = MakeMultiTex((int)rc.width, (int)rc.height, mirrorX, series);
        GUI.DrawTexture(rc, t);
        GUI.Label(new Rect(rc.x + 12, rc.y + 6, rc.width - 24, 20), title, st);
        GUI.Label(new Rect(rc.x + 12, rc.yMax - 22, rc.width - 24, 18), unit, st2);
        UnityEngine.Object.Destroy(t);
    }

    public static void DrawMulti(Rect rc, string title, string unit, params Series[] series)
    {
        DrawMulti(rc, title, unit, false, series);
    }

    static Texture2D MakeMultiTex(int W, int H, bool mirrorX, params Series[] series)
    {
        var tx = new Texture2D(W, H, TextureFormat.RGBA32, false);
        var bg = new Color(0.10f, 0.12f, 0.14f, 1f);
        var gr = new Color(0.22f, 0.26f, 0.30f, 1f);
        var ax = new Color(0.9f, 0.9f, 0.9f, 1f);
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                tx.SetPixel(x, y, bg);

        int padL = 46, padR = 12, padT = 30, padB = 38;
        int x0 = padL, x1 = W - padR, y0 = padT, y1 = H - padB;
        int pw = x1 - x0, ph = y1 - y0;

        double xmin = 0, xmax = 1, ymin = 0, ymax = 1;
        bool any = false;
        for (int s = 0; s < (series != null ? series.Length : 0); s++)
        {
            double[] xs = series[s].x, ys = series[s].y;
            if (xs == null || ys == null || xs.Length == 0) continue;
            for (int i = 0; i < xs.Length; i++)
            {
                if (double.IsNaN(ys[i]) || double.IsInfinity(ys[i])) continue;
                if (!any) { xmin = xmax = xs[i]; ymin = ymax = ys[i]; any = true; }
                else
                {
                    if (xs[i] < xmin) xmin = xs[i];
                    if (xs[i] > xmax) xmax = xs[i];
                    if (ys[i] < ymin) ymin = ys[i];
                    if (ys[i] > ymax) ymax = ys[i];
                }
            }
        }
        if (!any) return tx;
        if (xmax - xmin < 1e-9) { xmin -= 1; xmax += 1; }
        if (ymax - ymin < 1e-9) { ymin -= 1; ymax += 1; }
        double mx = (xmax - xmin) * 0.08, my = (ymax - ymin) * 0.14;
        xmin -= mx; xmax += mx; ymin -= my; ymax += my;

        // Con espejo: forzar el eje horizontal simetrico respecto a 0 para
        // que el diamante (+M derecha / -M izquierda) quede centrado completo.
        if (mirrorX) { xmax = Math.Max(xmax, -xmin); xmin = -xmax; }

        for (int g = 0; g <= 4; g++)
        {
            int gx = x0 + (int)Math.Round(g * pw / 4.0);
            for (int y = y0; y <= y1; y++) tx.SetPixel(gx, y, gr);
            int gy = y0 + (int)Math.Round(g * ph / 4.0);
            for (int x = x0; x <= x1; x++) tx.SetPixel(x, gy, gr);
        }
        for (int x = x0; x <= x1; x++) { tx.SetPixel(x, y0, ax); tx.SetPixel(x, y1, ax); }
        for (int y = y0; y <= y1; y++) { tx.SetPixel(x0, y, ax); tx.SetPixel(x1, y, ax); }

        for (int s = 0; s < (series != null ? series.Length : 0); s++)
        {
            double[] xs = series[s].x, ys = series[s].y;
            if (xs == null || ys == null || xs.Length == 0) continue;
            for (int i = 1; i < xs.Length && i < ys.Length; i++)
            {
                double xa = xs[i - 1], xb = xs[i];
                double ya = ys[i - 1], yb = ys[i];
                if (double.IsNaN(ya) || double.IsNaN(yb) || double.IsInfinity(ya) || double.IsInfinity(yb)) continue;
                int X0 = x0 + (int)Math.Round((xa - xmin) / (xmax - xmin) * pw);
                int Y0 = y0 + (int)Math.Round((ya - ymin) / (ymax - ymin) * ph);
                int X1 = x0 + (int)Math.Round((xb - xmin) / (xmax - xmin) * pw);
                int Y1 = y0 + (int)Math.Round((yb - ymin) / (ymax - ymin) * ph);
                Line(tx, X0, Y0, X1, Y1, series[s].color);
                Line(tx, X0, Y0 - 1, X1, Y1 - 1, series[s].color);
                if (mirrorX)
                {
                    double xma = -xa, xmb = -xb;
                    int XM0 = x0 + (int)Math.Round((xma - xmin) / (xmax - xmin) * pw);
                    int XM1 = x0 + (int)Math.Round((xmb - xmin) / (xmax - xmin) * pw);
                    Line(tx, XM0, Y0, XM1, Y1, series[s].color);
                    Line(tx, XM0, Y0 - 1, XM1, Y1 - 1, series[s].color);
                }
            }
        }

        tx.Apply();
        return tx;
    }

    // ---------------- Diagramas 2D apilados (N / V / M) ----------------

    // Replica drawDiagramPanels() del visor HTML: 3 paneles apilados con eje
    // central, relleno bajo la curva y punto del maximo senalado.
    public static void DrawDiag(Rect rc, AnalysisMap.DiagInfo d)
    {
        double[] x = d.x, N = d.N, V = d.V, M = d.M;
        if (x == null || x.Length == 0 || d.L <= 0) return;

        int W = (int)rc.width, H = (int)rc.height;
        const int PXL = 48, PXR = 14, PT = 26, PB = 24;
        int NW = W - PXL - PXR;
        int NH = (H - PT - PB - 6) / 3;
        if (NW < 8 || NH < 8) return;

        var bg = new Color(0.10f, 0.12f, 0.14f, 1f);
        var gr = new Color(0.22f, 0.26f, 0.30f, 1f);
        var midc = new Color(0.23f, 0.23f, 0.35f, 1f);

        var tx = new Texture2D(W, H, TextureFormat.RGBA32, false);
        for (int y = 0; y < H; y++)
            for (int xx = 0; xx < W; xx++)
                tx.SetPixel(xx, y, bg);

        Color[] cols = { new Color(0.18f, 0.80f, 0.44f, 1f),  // N verde
                         new Color(1f, 0.70f, 0.28f, 1f),     // V naranja
                         new Color(0f, 1f, 1f, 1f) };         // M cian
        double[][] valsA = { N, V, M };

        // Convencion: S = offset desde el tope del rect (0=arriba, igual que la
        // GUI). e = H - S es la fila de la textura (las filas crecen hacia arriba).
        for (int s = 0; s < 3; s++)
        {
            double[] vals = valsA[s];
            if (vals == null || vals.Length == 0) continue;
            int topS = PT + s * (NH + 3);
            int botS = topS + NH;
            int midS = topS + NH / 2;
            int eT = H - topS, eB = H - botS, eM = H - midS;
            double maxA = 1e-9;
            for (int i = 0; i < vals.Length; i++)
            {
                double a = Math.Abs(vals[i]);
                if (a > maxA) maxA = a;
            }
            maxA *= 1.15;

            for (int gx = PXL; gx <= PXL + NW; gx++) { tx.SetPixel(gx, eT, gr); tx.SetPixel(gx, eB, gr); }
            for (int gx = PXL; gx <= PXL + NW; gx++) { tx.SetPixel(gx, eM, midc); tx.SetPixel(gx, eM - 1, midc); }

            int iMax = 0;
            for (int i = 1; i < vals.Length; i++)
                if (Math.Abs(vals[i]) > Math.Abs(vals[iMax])) iMax = i;

            Color c = cols[s];
            // curva (valor positivo -> fila grande -> mas arriba en la pantalla)
            for (int i = 1; i < x.Length && i < vals.Length; i++)
            {
                int X0 = PXL + (int)Math.Round(NW * (x[i - 1] / d.L));
                int X1 = PXL + (int)Math.Round(NW * (x[i] / d.L));
                int Y0 = eM + (int)Math.Round((vals[i - 1] / maxA) * (NH / 2.0));
                int Y1 = eM + (int)Math.Round((vals[i] / maxA) * (NH / 2.0));
                Line(tx, X0, Y0, X1, Y1, c);
                Line(tx, X0, Y0 + 1, X1, Y1 + 1, c);
            }
            // relleno hacia el eje 0 (barrido por columna)
            for (int gx = PXL; gx <= PXL + NW; gx++)
            {
                double fx = (double)(gx - PXL) / NW;
                double v = Interp(x, vals, fx * d.L);
                int yv = eM + (int)Math.Round((v / maxA) * (NH / 2.0));
                int lo = Math.Min(eM, yv), hi = Math.Max(eM, yv);
                for (int i = lo; i <= hi; i++)
                {
                    if (i < eB || i > eT) continue;
                    Color p = tx.GetPixel(gx, i);
                    tx.SetPixel(gx, i, Color.Lerp(p, c, 0.35f));
                }
            }
            // punto del maximo
            int xm = PXL + (int)Math.Round(NW * (x[Mathf.Min(iMax, x.Length - 1)] / d.L));
            int ym = eM + (int)Math.Round((vals[iMax] / maxA) * (NH / 2.0));
            for (int gx = xm - 3; gx <= xm + 3; gx++)
                for (int gy = ym - 3; gy <= ym + 3; gy++)
                    if ((gx - xm) * (gx - xm) + (gy - ym) * (gy - ym) <= 9)
                        tx.SetPixel(Mathf.Clamp(gx, 0, W - 1), Mathf.Clamp(gy, 0, H - 1), c);
        }

        for (int gx = PXL; gx <= PXL + NW; gx++)
            tx.SetPixel(gx, H - PB + 3, new Color(0.27f, 0.27f, 0.33f, 1f));

        var st = new GUIStyle();
        st.fontSize = 10;
        st.normal.textColor = new Color(0.55f, 0.6f, 0.68f, 1f);
        var st2 = new GUIStyle(st);
        st2.fontSize = 11;
        st2.fontStyle = FontStyle.Bold;
        st2.normal.textColor = new Color(1f, 0.8f, 0.4f, 1f);

        tx.Apply();
        GUI.DrawTexture(rc, tx);

        // Etiquetas numericas (overlay GUI, el texto no va en la textura)
        for (int s = 0; s < 3; s++)
        {
            double[] vals = valsA[s];
            if (vals == null || vals.Length == 0) continue;
            int py = PT + s * (NH + 3);
            int mid = py + NH / 2;
            double maxA = 1e-9;
            for (int i = 0; i < vals.Length; i++) maxA = Math.Max(maxA, Math.Abs(vals[i]));
            maxA *= 1.15;
            string[] sn = { "N [kN]", "V [kN]", "M [kN-m]" };
            GUI.Label(new Rect(rc.x + PXL + 3, rc.y + py + 5, 90, 14), sn[s], st2);
            GUI.Label(new Rect(rc.x + 6, rc.y + py + 6, PXL - 8, 14), "+" + maxA.ToString("F0"), st);
            GUI.Label(new Rect(rc.x + 6, rc.y + py + NH - 8, PXL - 8, 14), "-" + maxA.ToString("F0"), st);
            GUI.Label(new Rect(rc.x + 6, rc.y + mid - 3, PXL - 8, 14), "0", st);
            int iMax = 0;
            for (int i = 1; i < vals.Length; i++)
                if (Math.Abs(vals[i]) > Math.Abs(vals[iMax])) iMax = i;
            int xxm = PXL + (int)Math.Round(NW * (x[Mathf.Min(iMax, x.Length - 1)] / d.L));
            int yym = mid - (int)Math.Round((vals[iMax] / maxA) * (NH / 2.0));
            GUI.Label(new Rect(rc.x + xxm + 5, rc.y + yym - 8, 70, 14), vals[iMax].ToString("F0"),
                      new GUIStyle(st) { normal = { textColor = cols[s] } });
        }
        GUI.Label(new Rect(rc.x + PXL, rc.y + H - 16, 40, 14), "0", st);
        GUI.Label(new Rect(rc.x + rc.width - PXR - 60, rc.y + H - 16, 60, 14),
                  d.L.ToString("F2") + " m", new GUIStyle(st) { alignment = TextAnchor.MiddleRight });
    }

    static double Interp(double[] xs, double[] ys, double t)
    {
        if (xs == null || ys == null || xs.Length == 0) return 0;
        if (t <= xs[0]) return ys[0];
        if (t >= xs[xs.Length - 1]) return ys[ys.Length - 1];
        for (int i = 1; i < xs.Length; i++)
        {
            if (t <= xs[i])
            {
                double f = (xs[i] - xs[i - 1]) < 1e-12 ? 0 : (t - xs[i - 1]) / (xs[i] - xs[i - 1]);
                return ys[i - 1] + f * (ys[i] - ys[i - 1]);
            }
        }
        return ys[ys.Length - 1];
    }

    // ---------------- P-M de capacidad + punto de demanda ----------------
    // Replica drawPM() del visor HTML: diamante simetrico en M, rama + cian,
    // rama - turquesa, punto de demanda amarillo/rojo segun este dentro/fuera.
    // Devuelve Mcap (capacidad a la carga axial Pd) por el parametro out.
    public static void DrawPMLab(Rect rc, double[] P, double[] Mc, double Pd, double Md, string caso, out double Mcap)
    {
        Mcap = 0;
        int W = (int)rc.width, H = (int)rc.height;
        const int px = 46, py = 16;
        int pw = W - px - 14, ph = H - py - 30;
        if (pw < 8 || ph < 8) return;

        double Pmax = 0, Pmin = 0, Mabs = 0;
        if (P != null) for (int i = 0; i < P.Length; i++) { if (P[i] > Pmax) Pmax = P[i]; if (P[i] < Pmin) Pmin = P[i]; }
        if (Mc != null) for (int i = 0; i < Mc.Length; i++) Mabs = Math.Max(Mabs, Mc[i]);
        Pmax = Math.Max(Pmax, Pd); Pmin = Math.Min(Pmin, Pd);
        Mabs = Math.Max(Mabs, Math.Abs(Md));
        if (Mabs <= 0) Mabs = 1;
        if (Pmax <= Pmin) Pmax = Pmin + 1;

        var tx = new Texture2D(W, H, TextureFormat.RGBA32, false);
        var bg = new Color(0.04f, 0.04f, 0.08f, 1f);
        var gr = new Color(0.16f, 0.16f, 0.27f, 1f);
        var zc = new Color(0.23f, 0.23f, 0.35f, 1f);
        var cian = new Color(0f, 1f, 1f, 1f);
        var turq = new Color(0f, 0.67f, 0.67f, 1f);
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                tx.SetPixel(x, y, bg);

        for (int i = 0; i <= 5; i++)
        {
            int x = px + pw * i / 5, y = py + ph - ph * i / 5;
            for (int yy = py; yy <= py + ph; yy++) tx.SetPixel(x, yy, gr);
            for (int xx = px; xx <= px + pw; xx++) tx.SetPixel(xx, y, gr);
        }

        Func<double, int> sx = m => px + pw / 2 + (int)Math.Round(pw * m / (2 * Mabs));
        // sP = offset desde el tope del rect (igual que la GUI); rP = fila textura.
        Func<double, int> sP = p => py + (int)Math.Round(ph * (Pmax - p) / (Pmax - Pmin));
        Func<double, int> rP = p => H - sP(p);

        for (int yy = py; yy <= py + ph; yy++) tx.SetPixel(px + pw / 2, yy, zc);
        int yP0 = rP(0);
        for (int xx = px; xx <= px + pw; xx++) { tx.SetPixel(xx, yP0, zc); tx.SetPixel(xx, yP0 - 1, zc); }

        // ramas + y -
        if (Mc != null && P != null && Mc.Length > 0 && Mc.Length == P.Length)
        {
            for (int i = 1; i < Mc.Length; i++)
            {
                Line(tx, sx(Mc[i - 1]), rP(P[i - 1]), sx(Mc[i]), rP(P[i]), cian);
                Line(tx, sx(Mc[i - 1]), rP(P[i - 1]) + 1, sx(Mc[i]), rP(P[i]) + 1, cian);
                Line(tx, sx(-Mc[i - 1]), rP(P[i - 1]), sx(-Mc[i]), rP(P[i]), turq);
                Line(tx, sx(-Mc[i - 1]), rP(P[i - 1]) + 1, sx(-Mc[i]), rP(P[i]) + 1, turq);
            }
        }

        // capacidad a esa carga axial (interpolada) y punto de demanda
        Mcap = McapAt(P, Mc, Pd);
        bool showDemand = Math.Abs(Md) > 0 || Math.Abs(Pd) > 0;
        if (showDemand && P != null && Mc != null)
        {
            bool dentro = Md <= Mcap;
            int cxs = sx(Md), cys = rP(Pd);
            Color col = dentro ? new Color(1f, 1f, 0.33f, 1f) : new Color(1f, 0.33f, 0.33f, 1f);
            for (int gx = cxs - 6; gx <= cxs + 6; gx++)
                for (int gy = cys - 6; gy <= cys + 6; gy++)
                    if ((gx - cxs) * (gx - cxs) + (gy - cys) * (gy - cys) <= 36)
                        tx.SetPixel(Mathf.Clamp(gx, 0, W - 1), Mathf.Clamp(gy, 0, H - 1), col);
            for (int a = -6; a <= 6; a++)
            {
                tx.SetPixel(Mathf.Clamp(cxs + a, 0, W - 1), Mathf.Clamp(cys, 0, H - 1), Color.black);
                tx.SetPixel(Mathf.Clamp(cxs, 0, W - 1), Mathf.Clamp(cys + a, 0, H - 1), Color.black);
            }
        }

        var st = new GUIStyle();
        st.fontSize = 11;
        st.normal.textColor = new Color(0.81f, 0.81f, 0.81f, 1f);

        tx.Apply();
        GUI.DrawTexture(rc, tx);

        GUI.Label(new Rect(rc.x + px, rc.y + H - 18, rc.width - 60, 16), "M [kN-m]", st);
        GUI.Label(new Rect(rc.x + 4, rc.y + 8, 42, 16), "P [kN]", st);
        GUI.Label(new Rect(rc.x + px + pw / 2 - 10, rc.y + py + ph + 4, 30, 14), "0", st);
        if (showDemand)
        {
            int cxs2 = sx(Md), cys2 = sP(Pd);
            GUI.Label(new Rect(rc.x + cxs2 + 10, rc.y + cys2 - 10, 120, 16),
                      caso + (Md <= Mcap ? "" : " (fuera)"),
                      new GUIStyle(st) { normal = { textColor = Md <= Mcap ? new Color(1f, 1f, 0.33f, 1f) : new Color(1f, 0.33f, 0.33f, 1f) } });
        }
    }

    static double McapAt(double[] P, double[] Mc, double p)
    {
        if (P == null || Mc == null || P.Length == 0) return 0;
        if (p <= P[0]) return Mc[0];
        if (p >= P[P.Length - 1]) return Mc[Mc.Length - 1];
        for (int i = 1; i < P.Length; i++)
        {
            if (p <= P[i])
            {
                double f = (P[i] - P[i - 1]) < 1e-12 ? 0 : (p - P[i - 1]) / (P[i] - P[i - 1]);
                return Mc[i - 1] + f * (Mc[i] - Mc[i - 1]);
            }
        }
        return Mc[Mc.Length - 1];
    }
}