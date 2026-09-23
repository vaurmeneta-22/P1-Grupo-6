using System;
using System.Collections.Generic;

// Linear combinations preserve the exported units and signed components.
// Resultants, extrema and P-M demand must be computed AFTER this sum.
public static partial class AnalysisMap
{
    static readonly double[] DefaultLambdas = { 1.2, 1, 1.4, 1.4 };
    static double[] lambdas = (double[])DefaultLambdas.Clone();
    public static readonly string[] BaseCases = { "G", "Q", "EX", "EY" };
    public static double[] Lambdas { get { return lambdas; } private set { lambdas = value; } }
    public static int CombinationRevision { get; private set; }
    public static string CombinationError { get; private set; }

    static void InitializeCombination()
    {
        double[] values = { 1.2, 1, 1.4, 1.4 };
        object combo = MiniJson.Get(Meta, "COMBO");
        object factors = MiniJson.Get(MiniJson.Get(combo, "superposicion"), "lambdas");
        for (int i = 0; i < 4; i++)
        {
            object value = MiniJson.Get(factors, BaseCases[i]);
            if (value != null) values[i] = MiniJson.Num(value);
        }
        TryCombine(values);
    }

    static double[] SumVectors(double[][] vectors, double[] weights)
    {
        if (vectors[0] == null) throw new InvalidOperationException("Vector ausente");
        var sum = new double[vectors[0].Length];
        for (int c = 0; c < 4; c++)
        {
            if (vectors[c] == null || vectors[c].Length != sum.Length)
                throw new InvalidOperationException("Componentes incompatibles");
            for (int j = 0; j < sum.Length; j++)
            {
                if (double.IsNaN(vectors[c][j]) || double.IsInfinity(vectors[c][j]))
                    throw new InvalidOperationException("Resultado no finito");
                sum[j] += weights[c] * vectors[c][j];
            }
        }
        return sum;
    }

    static Dictionary<K, T>[] Cases<K, T>(Dictionary<string, Dictionary<K, T>> source)
    {
        var result = new Dictionary<K, T>[4];
        for (int c = 0; c < 4; c++)
        {
            if (source == null || !source.TryGetValue(BaseCases[c], out result[c]))
                throw new InvalidOperationException("Falta caso " + BaseCases[c]);
            if (result[c].Count != result[0].Count)
                throw new InvalidOperationException("IDs incompatibles: " + BaseCases[c]);
            foreach (K key in result[0].Keys)
                if (!result[c].ContainsKey(key)) throw new InvalidOperationException("Falta ID " + key);
        }
        return result;
    }

    static Dictionary<int, double[]> CombineVectors(Dictionary<string, Dictionary<int, double[]>> source, double[] w)
    {
        var cases = Cases(source);
        var result = new Dictionary<int, double[]>();
        foreach (int id in cases[0].Keys)
            result[id] = SumVectors(new[] { cases[0][id], cases[1][id], cases[2][id], cases[3][id] }, w);
        return result;
    }

    public static bool TryCombine(double[] weights)
    {
        try
        {
            if (weights == null || weights.Length != 4) throw new InvalidOperationException("Se requieren cuatro factores");
            foreach (double w in weights)
                if (double.IsNaN(w) || double.IsInfinity(w) || Math.Abs(w) > 10)
                    throw new InvalidOperationException("Factor fuera de rango [-10,10]");
            var fc = Cases(Forces);
            var forces = new Dictionary<int, EndForces>();
            foreach (int id in fc[0].Keys)
            {
                var f = new EndForces();
                f.gi = SumVectors(new[] { fc[0][id].gi, fc[1][id].gi, fc[2][id].gi, fc[3][id].gi }, weights);
                f.gj = SumVectors(new[] { fc[0][id].gj, fc[1][id].gj, fc[2][id].gj, fc[3][id].gj }, weights);
                f.li = SumVectors(new[] { fc[0][id].li, fc[1][id].li, fc[2][id].li, fc[3][id].li }, weights);
                f.lj = SumVectors(new[] { fc[0][id].lj, fc[1][id].lj, fc[2][id].lj, fc[3][id].lj }, weights);
                forces[id] = f;
            }
            var disp = CombineVectors(Disp, weights);
            var reactions = CombineVectors(Reacciones, weights);
            var dc = Cases(Diagramas);
            var diagrams = new Dictionary<string, DiagInfo>();
            foreach (string key in dc[0].Keys)
            {
                DiagInfo a = dc[0][key];
                for (int c = 1; c < 4; c++)
                {
                    DiagInfo b = dc[c][key];
                    if (a.tag != b.tag || a.x.Length != b.x.Length)
                        throw new InvalidOperationException("Diagrama incompatible: " + key);
                    for (int j = 0; j < a.x.Length; j++)
                        if (Math.Abs(a.x[j] - b.x[j]) > 1e-10)
                            throw new InvalidOperationException("Malla de diagrama incompatible: " + key);
                }
                var d = new DiagInfo { tag = a.tag, tipo = a.tipo, seccion = a.seccion,
                    L = a.L, piso = a.piso, x = (double[])a.x.Clone() };
                d.N = SumVectors(new[] { a.N, dc[1][key].N, dc[2][key].N, dc[3][key].N }, weights);
                d.V = SumVectors(new[] { a.V, dc[1][key].V, dc[2][key].V, dc[3][key].V }, weights);
                d.M = SumVectors(new[] { a.M, dc[1][key].M, dc[2][key].M, dc[3][key].M }, weights);
                for (int c = 0; c < 4; c++)
                {
                    DiagInfo b = dc[c][key];
                    d.hasQ |= b.hasQ;
                    d.q += weights[c] * b.q;
                    d.resid += weights[c] * b.resid;
                    d.resMJ += weights[c] * b.resMJ;
                }
                diagrams[key] = d;
            }
            // Publish together only after validating every channel. Base cases stay immutable.
            Forces["COMBO"] = forces;
            Disp["COMBO"] = disp;
            Reacciones["COMBO"] = reactions;
            Diagramas["COMBO"] = diagrams;
            Lambdas = (double[])weights.Clone();
            CombinationRevision++;
            CombinationError = null;
            return true;
        }
        catch (Exception ex)
        {
            CombinationError = "No se puede combinar: " + ex.Message;
            return false;
        }
    }
}
