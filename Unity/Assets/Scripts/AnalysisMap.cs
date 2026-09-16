using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

// Carga resultados/11_mapa_visor (analysis_map.json -> StreamingAssets) y
// expone los mismos datos que el `ANALYSIS_MAP` del visor HTML (analisis 1:1).
public static class AnalysisMap
{
    // ---------- Tipos de datos ----------

    public class ElementInfo
    {
        public int id;
        public string type;
        public string section;
        public string material = "";
        public int ni = -1;
        public int nj = -1;
        public bool supI;
        public bool supJ;
        public bool borde;
    }

    public class EndForces
    {
        public double[] gi; // fuerza/momento global en extremo i (6)
        public double[] gj; // extremo j (6)
        public double[] li; // fuerzas locales i: [N, Vy, Vz, T, My, Mz]
        public double[] lj; // locales j: [N, Vy, Vz, T, My, Mz]
    }

    public class TribuInfo
    {
        public string type;
        public string section;
        public double area;
        public double Wg;
        public double Wq;
        public double pG;
        public double pQ;
        public List<object> aportes = new List<object>();
    }

    public class PmInfo
    {
        public double[] P_fiber;
        public double[] M_fiber;
        public double[] phi_1m;
        public double[] P_HA = new double[0];
        public double[] M_HA = new double[0];
        public double? alpha1;
        public double? beta1;
        public double M_ult;
        public bool n_ok;
    }

    public class DiagInfo
    {
        public int tag;
        public string tipo;
        public string seccion;
        public double L;
        public string piso = "";
        public double[] x = new double[0];
        public double[] N = new double[0];
        public double[] V = new double[0];
        public double[] M = new double[0];
        public bool hasQ;
        public double q;
        public double resid;
        public double resMJ;
    }

    public class SismoRow
    {
        public string piso;
        public double z;
        public double G, Q, W, masa, FX, FY, CMx, CMy, ux, uy, Rz;
    }

    // ---------- Estado ----------

    public static bool Loaded { get; private set; }
    public static string LoadError { get; private set; }

    public static readonly List<string> Casos = new List<string> { "COMBO", "G", "Q", "EX", "EY" };
    public static Dictionary<int, ElementInfo> ElementsByTag = new Dictionary<int, ElementInfo>();
    public static Dictionary<string, Dictionary<int, EndForces>> Forces;
    public static Dictionary<string, Dictionary<int, double[]>> Disp;
    public static Dictionary<string, Dictionary<int, double[]>> Reacciones;
    public static Dictionary<string, List<SismoRow>> Sismo;
    public static Dictionary<int, TribuInfo> Tribu;
    public static PmInfo MomCurv;
    public static Dictionary<string, PmInfo> PmHa;
    public static Dictionary<string, Dictionary<string, DiagInfo>> Diagramas;
    public static Dictionary<int, List<KeyValuePair<int, int>>> BeamFractions;
    public static Dictionary<string, Vector3> NodeCoords;
    public static Dictionary<string, double[]> StructCoords; // tag -> [x, y, h] estructural
    public static Dictionary<string, double[]> LocalAxes;
    public static Dictionary<string, object> Meta;
    public static Dictionary<string, object> Capacidad;

    // ---------- Carga ----------

    public static bool Load(string jsonPath)
    {
        Loaded = false;
        LoadError = null;
        if (!File.Exists(jsonPath))
        {
            LoadError = "No existe analysis_map.json en StreamingAssets.";
            return false;
        }
        string raw;
        try { raw = File.ReadAllText(jsonPath); }
        catch (Exception ex) { LoadError = "Leyendo JSON: " + ex.Message; return false; }
        object root;
        if (!MiniJson.TryParse(raw, out root))
        {
            LoadError = "analysis_map.json no es JSON valido.";
            return false;
        }
        try
        {
            Dictionary<string, object> r = MiniJson.AsDict(root);
            if (r == null) { LoadError = "Raiz no es objeto."; return false; }

            Meta = MiniJson.Dict(r, "meta");
            Capacidad = MiniJson.Dict(r, "capacidad");

            // elements
            ElementsByTag.Clear();
            List<object> els = MiniJson.Lis(r, "elements");
            if (els != null)
                foreach (object o in els)
                {
                    ElementInfo e = new ElementInfo();
                    e.id = (int)MiniJson.Db(o, "id");
                    e.type = MiniJson.St(o, "type") ?? "";
                    e.section = MiniJson.St(o, "section") ?? "";
                    e.material = MiniJson.St(o, "material") ?? "";
                    e.ni = (int)MiniJson.Db(o, "ni");
                    e.nj = (int)MiniJson.Db(o, "nj");
                    e.supI = MiniJson.Bt(o, "sup_i");
                    e.supJ = MiniJson.Bt(o, "sup_j");
                    e.borde = MiniJson.Bt(o, "borde");
                    if (!ElementsByTag.ContainsKey(e.id))
                        ElementsByTag[e.id] = e;
                }

            // forces: case -> "tag" -> {i,j,li,lj}
            Forces = new Dictionary<string, Dictionary<int, EndForces>>();
            Dictionary<string, object> frc = MiniJson.Dict(r, "forces");
            if (frc != null)
                foreach (KeyValuePair<string, object> kv in frc)
                {
                    Dictionary<int, EndForces> m = new Dictionary<int, EndForces>();
                    Dictionary<string, object> byTag = MiniJson.AsDict(kv.Value);
                    if (byTag != null)
                        foreach (KeyValuePair<string, object> t in byTag)
                        {
                            int tag;
                            if (!int.TryParse(t.Key, out tag)) continue;
                            EndForces f = new EndForces();
                            f.gi = MiniJson.NumArrayValue(MiniJson.Get(t.Value, "i"));
                            f.gj = MiniJson.NumArrayValue(MiniJson.Get(t.Value, "j"));
                            f.li = MiniJson.NumArrayValue(MiniJson.Get(t.Value, "li"));
                            f.lj = MiniJson.NumArrayValue(MiniJson.Get(t.Value, "lj"));
                            m[tag] = f;
                        }
                    Forces[kv.Key] = m;
                }

            // disp: case -> "tag" -> [6]
            Disp = new Dictionary<string, Dictionary<int, double[]>>();
            Dictionary<string, object> dsp = MiniJson.Dict(r, "disp");
            if (dsp != null)
                foreach (KeyValuePair<string, object> kv in dsp)
                {
                    Dictionary<int, double[]> m = new Dictionary<int, double[]>();
                    Dictionary<string, object> byTag = MiniJson.AsDict(kv.Value);
                    if (byTag != null)
                        foreach (KeyValuePair<string, object> t in byTag)
                        {
                            int tag;
                            if (int.TryParse(t.Key, out tag))
                                m[tag] = MiniJson.NumArrayValue(t.Value);
                        }
                    Disp[kv.Key] = m;
                }

            // reacciones: case -> "tag" -> [6]
            Reacciones = new Dictionary<string, Dictionary<int, double[]>>();
            Dictionary<string, object> rct = MiniJson.Dict(r, "reacciones");
            if (rct != null)
                foreach (KeyValuePair<string, object> kv in rct)
                {
                    Dictionary<int, double[]> m = new Dictionary<int, double[]>();
                    Dictionary<string, object> byTag = MiniJson.AsDict(kv.Value);
                    if (byTag != null)
                        foreach (KeyValuePair<string, object> t in byTag)
                        {
                            int tag;
                            if (int.TryParse(t.Key, out tag))
                                m[tag] = MiniJson.NumArrayValue(t.Value);
                        }
                    Reacciones[kv.Key] = m;
                }

            // sismo: case (EX/EY) -> [ {piso,z_m,...} ]
            Sismo = new Dictionary<string, List<SismoRow>>();
            Dictionary<string, object> ssm = MiniJson.Dict(r, "sismo");
            if (ssm != null)
                foreach (KeyValuePair<string, object> kv in ssm)
                {
                    List<SismoRow> rows = new List<SismoRow>();
                    List<object> arr = MiniJson.AsList(kv.Value);
                    if (arr != null)
                        foreach (object o in arr)
                        {
                            SismoRow s = new SismoRow();
                            s.piso = MiniJson.St(o, "piso") ?? "";
                            s.z = MiniJson.Db(o, "z_m");
                            s.G = MiniJson.Db(o, "G_kN");
                            s.Q = MiniJson.Db(o, "Q_kN");
                            s.W = MiniJson.Db(o, "W_kN");
                            s.masa = MiniJson.Db(o, "masa_kg");
                            s.FX = MiniJson.Db(o, "F_X_kN");
                            s.FY = MiniJson.Db(o, "F_Y_kN");
                            s.CMx = MiniJson.Db(o, "CM_x_m");
                            s.CMy = MiniJson.Db(o, "CM_y_m");
                            s.ux = MiniJson.Db(o, "ux_mm");
                            s.uy = MiniJson.Db(o, "uy_mm");
                            s.Rz = MiniJson.Db(o, "Rz_rad");
                            rows.Add(s);
                        }
                    Sismo[kv.Key] = rows;
                }

            // tributarias
            Tribu = new Dictionary<int, TribuInfo>();
            Dictionary<string, object> trb = MiniJson.Dict(r, "tributarias");
            if (trb != null)
                foreach (KeyValuePair<string, object> kv in trb)
                {
                    int vid;
                    if (!int.TryParse(kv.Key, out vid)) continue;
                    TribuInfo t = new TribuInfo();
                    t.type = MiniJson.St(kv.Value, "type") ?? "";
                    t.section = MiniJson.St(kv.Value, "section") ?? "";
                    t.area = MiniJson.Db(kv.Value, "area_tributaria_m2");
                    t.Wg = MiniJson.Db(kv.Value, "W_G_kN");
                    t.Wq = MiniJson.Db(kv.Value, "W_Q_kN");
                    t.pG = MiniJson.Db(kv.Value, "p_G_kN_m");
                    t.pQ = MiniJson.Db(kv.Value, "p_Q_kN_m");
                    List<object> ap = MiniJson.Lis(kv.Value, "aportes");
                    if (ap != null) t.aportes = ap;
                    Tribu[vid] = t;
                }

            // momcurv
            Dictionary<string, object> mc = MiniJson.Dict(r, "momcurv");
            if (mc != null)
            {
                MomCurv = new PmInfo();
                MomCurv.P_fiber = new[] { MiniJson.Db(mc, "P_kN") };
                MomCurv.M_fiber = MiniJson.NumArray(mc, "M_kNm");
                MomCurv.phi_1m = MiniJson.NumArray(mc, "phi_1m");
                MomCurv.M_ult = MiniJson.Db(mc, "M_ult_kNm");
                MomCurv.n_ok = MiniJson.Bt(mc, "n_ok");
                MomCurv.alpha1 = null;
                MomCurv.beta1 = null;
            }
            else MomCurv = null;

            // pm_ha
            PmHa = new Dictionary<string, PmInfo>();
            Dictionary<string, object> pm = MiniJson.Dict(r, "pm_ha");
            if (pm != null)
                foreach (KeyValuePair<string, object> kv in pm)
                {
                    PmInfo p = new PmInfo();
                    p.P_fiber = MiniJson.NumArray(kv.Value, "P_fiber");
                    p.M_fiber = MiniJson.NumArray(kv.Value, "M_fiber");
                    p.P_HA = MiniJson.NumArray(kv.Value, "P_HA");
                    p.M_HA = MiniJson.NumArray(kv.Value, "M_HA");
                    object a1 = MiniJson.Get(kv.Value, "alpha1");
                    if (a1 != null) p.alpha1 = MiniJson.Num(a1);
                    object b1 = MiniJson.Get(kv.Value, "beta1");
                    if (b1 != null) p.beta1 = MiniJson.Num(b1);
                    PmHa[kv.Key] = p;
                }

            // diagramas: case -> {viga/columna/muro -> {tag,...}}
            Diagramas = new Dictionary<string, Dictionary<string, DiagInfo>>();
            Dictionary<string, object> dg = MiniJson.Dict(r, "diagramas");
            if (dg != null)
                foreach (KeyValuePair<string, object> kv in dg)
                {
                    Dictionary<string, DiagInfo> dd = new Dictionary<string, DiagInfo>();
                    Dictionary<string, object> byType = MiniJson.AsDict(kv.Value);
                    if (byType != null)
                        foreach (KeyValuePair<string, object> t in byType)
                        {
                            DiagInfo d = new DiagInfo();
                            d.tag = (int)MiniJson.Db(t.Value, "tag");
                            d.tipo = MiniJson.St(t.Value, "tipo") ?? "";
                            d.seccion = MiniJson.St(t.Value, "seccion") ?? "";
                            d.L = MiniJson.Db(t.Value, "L");
                            d.piso = MiniJson.St(t.Value, "piso") ?? "";
                            d.x = MiniJson.NumArray(t.Value, "x");
                            d.N = MiniJson.NumArray(t.Value, "N");
                            d.V = MiniJson.NumArray(t.Value, "V");
                            d.M = MiniJson.NumArray(t.Value, "M");
                            object q = MiniJson.Get(t.Value, "q");
                            if (q != null)
                            {
                                d.hasQ = true;
                                d.q = MiniJson.Num(q);
                                d.resid = MiniJson.Db(t.Value, "resid");
                                d.resMJ = MiniJson.Db(t.Value, "resMJ");
                            }
                            dd[t.Key] = d;
                        }
                    Diagramas[kv.Key] = dd;
                }

            // beam_fractions: vid -> [{ni,nj}]
            BeamFractions = new Dictionary<int, List<KeyValuePair<int, int>>>();
            Dictionary<string, object> bf = MiniJson.Dict(r, "beam_fractions");
            if (bf != null)
                foreach (KeyValuePair<string, object> kv in bf)
                {
                    int vid;
                    if (!int.TryParse(kv.Key, out vid)) continue;
                    List<KeyValuePair<int, int>> segs = new List<KeyValuePair<int, int>>();
                    List<object> arr = MiniJson.AsList(kv.Value);
                    if (arr != null)
                        foreach (object o in arr)
                        {
                            int ni = (int)MiniJson.Db(o, "ni");
                            int nj = (int)MiniJson.Db(o, "nj");
                            segs.Add(new KeyValuePair<int, int>(ni, nj));
                        }
                    BeamFractions[vid] = segs;
                }

            // node_coords: tag -> [x,y,z] (metros, coordenadas FE)
            NodeCoords = new Dictionary<string, Vector3>();
            StructCoords = new Dictionary<string, double[]>();
            Dictionary<string, object> nc = MiniJson.Dict(r, "node_coords");
            if (nc != null)
                foreach (KeyValuePair<string, object> kv in nc)
                {
                    double[] c = MiniJson.NumArrayValue(kv.Value);
                    if (c.Length >= 3)
                    {
                        // Mundo Unity (mismo espejo en X que EdificioLoader.NodeToPos):
                        // Unity.x = -x estructural, Unity.y = altura (z), Unity.z = y.
                        NodeCoords[kv.Key] = new Vector3(-(float)c[0], (float)c[2], (float)c[1]);
                        StructCoords[kv.Key] = c;
                    }
                }

            // local_axes: tag -> cosenos directores [3x3] con el orden del FE
            LocalAxes = new Dictionary<string, double[]>();
            Dictionary<string, object> la = MiniJson.Dict(r, "local_axes");
            if (la != null)
                foreach (KeyValuePair<string, object> kv in la)
                    LocalAxes[kv.Key] = MiniJson.NumArrayValue(kv.Value);

            Loaded = true;
            return true;
        }
        catch (Exception ex)
        {
            LoadError = "Parseo de analysis_map.json: " + ex.Message;
            return false;
        }
    }

    // ---------- Accesos de conveniencia ----------

    public static ElementInfo Element(int tag)
    {
        ElementInfo e;
        return ElementsByTag.TryGetValue(tag, out e) ? e : null;
    }

    public static EndForces Fuerzas(string caso, int tag)
    {
        Dictionary<int, EndForces> m;
        EndForces f;
        if (Forces != null && Forces.TryGetValue(caso, out m) && m.TryGetValue(tag, out f))
            return f;
        return null;
    }

    public static double[] Desp(string caso, int nodeTag)
    {
        Dictionary<int, double[]> m;
        double[] d;
        if (Disp != null && Disp.TryGetValue(caso, out m) && m.TryGetValue(nodeTag, out d))
            return d;
        return null;
    }

    public static double[] Reaccion(string caso, int nodeTag)
    {
        Dictionary<int, double[]> m;
        double[] r;
        if (Reacciones != null && Reacciones.TryGetValue(caso, out m) && m.TryGetValue(nodeTag, out r))
            return r;
        return null;
    }

    public static TribuInfo Tributaria(int vid)
    {
        TribuInfo t;
        return Tribu != null && Tribu.TryGetValue(vid, out t) ? t : null;
    }

    public static DiagInfo Diagrama(string caso, string elemento)
    {
        Dictionary<string, DiagInfo> d;
        DiagInfo di;
        if (Diagramas != null && Diagramas.TryGetValue(caso, out d) && d.TryGetValue(elemento, out di))
            return di;
        return null;
    }

    // Proyeccion del vector fuerza (global) sobre el eje longitudinal (u) y el
    // transversal (B) definidos como en el visor HTML, para columnas y muros.
    public static void Proyectar(double[] fi, double[] fj, Vector3 u, Vector3 B,
                                 out double Ni, out double Nj,
                                 out double Vi, out double Vj,
                                 out double Mi, out double Mj)
    {
        Ni = Rayleigh(fi, 0, u) ; Nj = Rayleigh(fj, 0, u);
        Vi = Rayleigh(fi, 0, B) ; Vj = Rayleigh(fj, 0, B);
        Mi = Rayleigh(fi, 3, B); Mj = Rayleigh(fj, 3, B);
    }

    static double Rayleigh(double[] f, int o, Vector3 v)
    {
        double r = 0.0;
        for (int k = 0; k < 3; k++) r += f[o + k] * v[k];
        return r;
    }
}