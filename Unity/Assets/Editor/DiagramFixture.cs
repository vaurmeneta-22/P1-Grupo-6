using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Verificacion automatica de la ficha de Visualizacion con los diagramas N/V/M.
// No es un test de Play Mode: se ejecuta en modo editor sobre la escena real,
// invoca el mismo codigo que dibuja el panel y comprueba que el resultado es
// utilizable. Sirve para detectar regresiones sin depender de una pantalla.
public static class DiagramFixture
{
    public const string Tag = "DiagramFixture";

    [MenuItem("Lab/Verificar diagramas N/V/M")]
    public static void Run()
    {
        int rc = RunBatch();
        if (Application.isBatchMode) EditorApplication.Exit(rc);
    }

    public static int RunBatch()
    {
        int errores = 0;
        Log("[" + Tag + "] proyecto: " + Application.dataPath);

        // 1) El modulo debe compilar y tener la API esperada.
        Type ed = typeof(ElementDiagrams);
        Log("[" + Tag + "] ElementDiagrams en " + ed.Assembly.GetName().Name);
        MethodInfo construir = ed.GetMethod("Construir",
            BindingFlags.Public | BindingFlags.Static,
            null,
            new[] { typeof(int), typeof(string), typeof(int) }, null);
        if (construir == null)
        {
            Log("[ERROR] no existe ElementDiagrams.Construir(int,string,int)");
            return 1;
        }

        // 2) El mapa se carga como en EdificioLoader.LoadAnalysisMap: en modo
        //    editor la escena no se ha ejecutado todavia, asi que se carga aqui.
        if (!AnalysisMap.Loaded)
        {
            string amPath = Path.Combine(Application.streamingAssetsPath, "analysis_map.json");
            if (!AnalysisMap.Load(amPath))
            {
                Log("[ERROR] no se pudo cargar " + amPath + ": " + AnalysisMap.LoadError);
                return 1;
            }
        }
        if (AnalysisMap.ElementsByTag == null || AnalysisMap.ElementsByTag.Count == 0)
        {
            Log("[ERROR] AnalysisMap vacio: la ficha no tendria nada que dibujar");
            return 1;
        }
        Log("[" + Tag + "] elementos en el mapa: " + AnalysisMap.ElementsByTag.Count);

        // 3) Un elemento representativo de cada tipo con diagrama, en los 5 casos
        //    y los 2 planos. Se recorren los mismos campos que usa la ficha.
        string[] casos = { "G", "Q", "EX", "EY", "COMBO" };
        string[] tipos = { "beam_x", "beam_y", "column", "wall", "steel_beam", "steel_column" };

        foreach (string tipo in tipos)
        {
            int[] tag = AnalysisMap.ElementsByTag
                .Where(kv => kv.Value.type == tipo)
                .Select(kv => kv.Key).OrderBy(k => k).ToArray();
            if (tag.Length == 0)
            {
                Log("[ERROR] sin elementos de tipo " + tipo);
                errores++;
                continue;
            }
            // Se toma el primero y tambien el ultimo, para no depender de uno solo.
            foreach (int t in new[] { tag[0], tag[tag.Length - 1] })
                for (int c = 0; c < casos.Length; c++)
                    for (int plano = 0; plano < 2; plano++)
                        errores += Revisar(ed, construir, t, casos[c], plano, tipo);
        }

        // 4) Elemento inexistente: debe aparecer el mensaje explicito, no un null.
        {
            object res = construir.Invoke(null, new object[] { 987654321, "COMBO", 0 });
            string err = (string)res.GetType().GetField("error").GetValue(res);
            if (err != ElementDiagrams.SinResultados)
            {
                Log("[ERROR] elemento inexistente devolvio '" + err + "'");
                errores++;
            }
            else Log("[" + Tag + "] elemento inexistente -> " + err);
        }

        // 5) Lacache de la ficha: dos llamadas seguidas deben devolver la misma
        //    instancia (no reconstruir en cada OnGUI) y cambiar de plano debe
        //    dar una instancia distinta.
        {
            var r1 = (object)construir.Invoke(null, new object[] { PrimerTag("beam_x"), "COMBO", 0 });
            var r2 = (object)construir.Invoke(null, new object[] { PrimerTag("beam_x"), "COMBO", 0 });
            var r3 = (object)construir.Invoke(null, new object[] { PrimerTag("beam_x"), "COMBO", 1 });
            if (!ReferenceEquals(r1, r2))
            {
                Log("[AVISO] Construir no memoiza: la ficha cachea por su cuenta");
            }
            if (ReferenceEquals(r1, r3))
            {
                Log("[ERROR] los dos planos devolvieron la misma instancia");
                errores++;
            }
        }

        // 6) La escena del proyecto debe abrir y contener el inspector, que es
        //    quien dibuja el panel. En -batchmode el editor no carga ninguna
        //    escena, asi que se abre explicitamente.
        {
            string[] candidatas = { "Assets/Scenes/SampleScene.unity" };
            string ruta = candidatas.FirstOrDefault(
                p => !string.IsNullOrEmpty(p) && File.Exists(Path.Combine(
                    Path.GetDirectoryName(Application.dataPath), p)));
            if (ruta == null)
            {
                Log("[AVISO] no se encontro la escena del proyecto; se omite la comprobacion");
            }
            else
            {
                var scene = EditorSceneManager.OpenScene(ruta, OpenSceneMode.Single);
                Log("[" + Tag + "] escena '" + scene.name + "' · raices=" + scene.rootCount);
                if (scene.rootCount == 0)
                {
                    Log("[ERROR] la escena abio vacia");
                    errores++;
                }
                var insp = UnityEngine.Object.FindObjectsByType<TributaryInspector>(
                    FindObjectsInactive.Include, FindObjectsSortMode.None);
                Log("[" + Tag + "] TributaryInspector en escena: " + insp.Length);
                if (insp.Length == 0)
                {
                    Log("[AVISO] la escena no tiene TributaryInspector todavia (se crea al cargar el edificio)");
                }
                // El panel de datos ya no debe exponer la pestaña Diagramas.
                var paneles = UnityEngine.Object.FindObjectsByType<DataPanel>(
                    FindObjectsInactive.Include, FindObjectsSortMode.None);
                foreach (var dp in paneles)
                {
                    FieldInfo t = typeof(DataPanel).GetField("tabs",
                        BindingFlags.NonPublic | BindingFlags.Instance);
                    string[] arr = t != null ? (string[])t.GetValue(dp) : null;
                    if (arr != null && Array.IndexOf(arr, "Diagramas") >= 0)
                    {
                        Log("[ERROR] DataPanel todavia lista la pestaña Diagramas");
                        errores++;
                    }
                }
                Log("[" + Tag + "] DataPanel en escena: " + paneles.Length + " (pestañas sin Diagramas)");
            }
        }

        Log(errores == 0
            ? "[DIAGRAMAS] VERIFICACION OK"
            : "[DIAGRAMAS] " + errores + " FALLO(S)");
        return errores == 0 ? 0 : 1;
    }

    static int PrimerTag(string tipo)
    {
        return AnalysisMap.ElementsByTag
            .Where(kv => kv.Value.type == tipo)
            .Select(kv => kv.Key).OrderBy(k => k).First();
    }

    static int Revisar(Type ed, MethodInfo construir, int tag, string caso, int plano, string tipo)
    {
        int errores = 0;
        object r = construir.Invoke(null, new object[] { tag, caso, plano });
        Type rt = r.GetType();
        string error = (string)rt.GetField("error").GetValue(r);
        string etq = tag + "/" + caso + "/plano" + plano + " (" + tipo + ")";

        if (error != null)
        {
            Log("[ERROR] " + etq + " -> " + error);
            return 1;
        }

        object diag = rt.GetField("diag").GetValue(r);
        Type dt = diag.GetType();
        double[] x = (double[])dt.GetField("x").GetValue(diag);
        double[] N = (double[])dt.GetField("N").GetValue(diag);
        double[] V = (double[])dt.GetField("V").GetValue(diag);
        double[] M = (double[])dt.GetField("M").GetValue(diag);
        double L = (double)dt.GetField("L").GetValue(diag);

        if (x == null || x.Length < 2) { Log("[ERROR] " + etq + " sin puntos"); return 1; }
        if (x.Length != N.Length || x.Length != V.Length || x.Length != M.Length)
        { Log("[ERROR] " + etq + " series de distinta longitud"); return 1; }
        if (L <= 0) { Log("[ERROR] " + etq + " L=" + L); errores++; }
        if (x[0] > 1e-9 || Math.Abs(x[x.Length - 1] - L) > 1e-6)
        { Log("[ERROR] " + etq + " x no va de 0 a L (" + x[0] + ".." + x[x.Length - 1] + ")"); errores++; }
        for (int i = 1; i < x.Length; i++)
            if (x[i] < x[i - 1]) { Log("[ERROR] " + etq + " x no es monotono en " + i); errores++; break; }
        for (int i = 0; i < x.Length; i++)
            if (double.IsNaN(N[i]) || double.IsNaN(V[i]) || double.IsNaN(M[i]))
            { Log("[ERROR] " + etq + " NaN en la serie"); errores++; break; }

        double errN = (double)rt.GetField("errN").GetValue(r);
        double errV = (double)rt.GetField("errV").GetValue(r);
        double errM = (double)rt.GetField("errM").GetValue(r);
        if (errN > 1e-4 || errV > 1e-4 || errM > 1e-4)
        {
            Log("[ERROR] " + etq + " cierre N=" + errN + " V=" + errV + " M=" + errM);
            errores++;
        }
        if (errores == 0)
            Log("[" + Tag + "] " + etq + " ok · L=" + L.ToString("F2") +
                " · n=" + x.Length + " · cierre N=" + errN.ToString("E1") +
                " V=" + errV.ToString("E1") + " M=" + errM.ToString("E1"));
        return errores;
    }

    static void Log(string m)
    {
        // En batchmode el log va al -logFile; en editor, a la consola.
        if (Application.isBatchMode) Console.WriteLine(m);
        Debug.Log(m);
    }
}
