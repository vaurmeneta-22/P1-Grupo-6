using System;
using System.Collections.Generic;

public static class ViewerCombinationChecks
{
    static int checks;
    static void Check(bool ok, string message)
    {
        checks++;
        if (!ok) throw new Exception(message);
    }
    static void Vector(double[] actual, Func<int, double[]> source, double[] w)
    {
        for (int j = 0; j < actual.Length; j++)
        {
            double expected = 0;
            for (int c = 0; c < 4; c++) expected += source(c)[j] * w[c];
            Check(Math.Abs(expected - actual[j]) < 1e-10, "Vector incorrecto");
        }
    }
    public static void Run(string path)
    {
        Check(AnalysisMap.Load(path), AnalysisMap.LoadError);
        Check(AnalysisMap.CombinationError == null, AnalysisMap.CombinationError);
        var original = AnalysisMap.Disp["G"];
        var snapshots = new Dictionary<int, double[]>();
        foreach (var p in original) snapshots[p.Key] = (double[])p.Value.Clone();
        var combinations = new[] {
            new double[] {0,0,0,0}, new double[] {1,0,0,0},
            new double[] {0,1,0,0}, new double[] {0,0,1,0}, new double[] {0,0,0,1},
            new double[] {1.2,1,1.4,1.4}, new double[] {1,.5,-.3,.7}
        };
        foreach (var w in combinations)
        {
            Check(AnalysisMap.TryCombine(w), AnalysisMap.CombinationError);
            foreach (var p in AnalysisMap.Disp["COMBO"])
                Vector(p.Value, c => AnalysisMap.Disp[AnalysisMap.BaseCases[c]][p.Key], w);
            foreach (var p in AnalysisMap.Reacciones["COMBO"])
                Vector(p.Value, c => AnalysisMap.Reacciones[AnalysisMap.BaseCases[c]][p.Key], w);
            foreach (var p in AnalysisMap.Forces["COMBO"])
            {
                Vector(p.Value.gi, c => AnalysisMap.Forces[AnalysisMap.BaseCases[c]][p.Key].gi, w);
                Vector(p.Value.gj, c => AnalysisMap.Forces[AnalysisMap.BaseCases[c]][p.Key].gj, w);
                Vector(p.Value.li, c => AnalysisMap.Forces[AnalysisMap.BaseCases[c]][p.Key].li, w);
                Vector(p.Value.lj, c => AnalysisMap.Forces[AnalysisMap.BaseCases[c]][p.Key].lj, w);
            }
            foreach (var p in AnalysisMap.Diagramas["COMBO"])
            {
                Vector(p.Value.N, c => AnalysisMap.Diagramas[AnalysisMap.BaseCases[c]][p.Key].N, w);
                Vector(p.Value.V, c => AnalysisMap.Diagramas[AnalysisMap.BaseCases[c]][p.Key].V, w);
                Vector(p.Value.M, c => AnalysisMap.Diagramas[AnalysisMap.BaseCases[c]][p.Key].M, w);
            }
        }
        foreach (var p in original)
            for (int j=0; j<p.Value.Length; j++) Check(p.Value[j] == snapshots[p.Key][j], "Caso base mutado");
        var published = AnalysisMap.Disp["COMBO"];
        Check(!AnalysisMap.TryCombine(new double[] {double.NaN,0,0,0}), "NaN aceptado");
        var ex = AnalysisMap.Disp["EX"];
        AnalysisMap.Disp.Remove("EX");
        Check(!AnalysisMap.TryCombine(new double[4]), "Caso ausente aceptado");
        Check(Object.ReferenceEquals(published, AnalysisMap.Disp["COMBO"]), "Publicacion parcial");
        AnalysisMap.Disp["EX"] = ex;
        Console.WriteLine("PASS: " + checks + " comprobaciones C#, siete combinaciones, casos inmutables y rechazo atomico.");
    }
}
