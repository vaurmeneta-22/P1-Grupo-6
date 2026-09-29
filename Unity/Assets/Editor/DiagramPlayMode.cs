using System;
using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Entra en Play Mode, espera a que el edificio este cargado, selecciona un
// elemento de cada tipo y recorre los 5 casos y los 2 planos.
//
// Aqui NO se invoca OnGUI a mano: el inspector ya dibuja su panel en cada frame
// de juego. El fixture solo cambia el estado (elemento, caso, plano), deja que
// Unity dibuje de verdad, comprueba que no aparecio ningun error en el log y
// guarda una captura por caso.
//
//   Unity.exe -batchmode -projectPath Unity -executeMethod DiagramPlayMode.Run
public static class DiagramPlayMode
{
    const string ScenePath = "Assets/Scenes/SampleScene.unity";
    const string OutDir = "Builds/DiagramShots";
    static string dir;
    static int pasos;
    static int fallos;
    static readonly string[] Casos = { "G", "Q", "EX", "EY", "COMBO" };

    public static void Run()
    {
        dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", OutDir));
        Directory.CreateDirectory(dir);

        // Sin recarga de dominio: si Unity recarga los ensamblados al entrar en
        // Play Mode, esta clase se recrea y se pierde el handler de update.
        EditorSettings.enterPlayModeOptionsEnabled = true;
        EditorSettings.enterPlayModeOptions = EnterPlayModeOptions.DisableDomainReload;

        EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
        EditorApplication.update += Tick;
        EditorApplication.EnterPlaymode();
    }

    // El avance se hace a mano desde update: un paso de la corrutina por tick
    // del editor, de modo que Play Mode sigue vivo (y OnGUI sigue dibujando)
    // entre pasos. -quit cerraria el editor al volver de Run(), asi que la
    // salida la hace Terminar con EditorApplication.Exit.
    static IEnumerator rutina;

    static void Tick()
    {
        if (rutina == null)
        {
            pasos++;
            if (pasos > 900)
            { Terminar(1, "timeout: el edificio no se cargo en " + pasos + " ticks"); return; }
            if (EditorApplication.isPlaying && Ready())
            {
                rutina = Routine();
                Debug.Log("[PlayDiag] escena lista, plumbing del edificio correcto");
            }
            return;
        }
        try
        {
            if (!rutina.MoveNext()) Terminar(fallos == 0 ? 0 : 1);
        }
        catch (Exception e) { Terminar(1, e.ToString()); }
    }

    static IEnumerator Routine()
    {
        var insp = UnityEngine.Object.FindObjectsByType<TributaryInspector>(
            FindObjectsInactive.Include, FindObjectsSortMode.None).FirstOrDefault();
        if (insp == null) throw new Exception("no hay TributaryInspector en escena");

        var tags = UnityEngine.Object.FindObjectsByType<ElementTag>(
            FindObjectsInactive.Include, FindObjectsSortMode.None);
        Debug.Log("[PlayDiag] ElementTag en escena: " + tags.Length);
        if (tags.Length == 0) throw new Exception("no hay ElementTag en escena");

        var porTipo = tags.GroupBy(t => t.type)
                           .ToDictionary(g => g.Key,
                                         g => g.OrderBy(t => t.elementId).ToList());

        // Un tipo representativo de cada familia, mas el ultimo del mismo tipo
        // para no depender de una sola viga.
        var objetivos = new System.Collections.Generic.List<ElementTag>();
        foreach (var kv in porTipo.OrderBy(k => k.Key))
        {
            if (kv.Key == "loza") continue;
            objetivos.Add(kv.Value[0]);
            if (kv.Value.Count > 1) objetivos.Add(kv.Value[kv.Value.Count - 1]);
        }
        Debug.Log("[PlayDiag] elementos a recorrer: " + objetivos.Count);

        foreach (ElementTag t in objetivos)
        {
            if (!Seleccionar(insp, t)) throw new Exception("no se pudo seleccionar " + t.type);

            foreach (string caso in Casos)
            {
                Set(insp, "currentCase", caso);
                for (int plano = 0; plano < 2; plano++)
                {
                    Set(insp, "diagramPlane", plano);
                    yield return null;                 // deja que Unity dibuje
                    yield return new WaitForEndOfFrame();

                    object res = typeof(ElementDiagrams).GetMethod("Construir")
                        .Invoke(null, new object[] { t.elementId, caso, plano });
                    Type rt = res.GetType();
                    string err = (string)rt.GetField("error").GetValue(res);
                    if (err != null)
                    {
                        Debug.LogError("[PlayDiag] " + t.type + " " + caso +
                                       " plano" + plano + " -> " + err);
                        fallos++;
                        continue;
                    }
                    object diag = rt.GetField("diag").GetValue(res);
                    double L = (double)diag.GetType().GetField("L").GetValue(diag);
                    double[] x = (double[])diag.GetType().GetField("x").GetValue(diag);
                    if (L <= 0 || x == null || x.Length < 2)
                    {
                        Debug.LogError("[PlayDiag] diagrama vacio en " + t.type + " " + caso);
                        fallos++;
                        continue;
                    }
                    if (plano == 0)
                    {
                        string ruta = Path.Combine(dir,
                            t.type + "_" + t.elementId + "_" + caso + ".png");
                        try
                        {
                            ScreenCapture.CaptureScreenshot(ruta);
                            Debug.Log("[PlayDiag] OK " + t.type + " " + t.elementId +
                                      " " + caso + " · L=" + L.ToString("F2") +
                                      " · n=" + x.Length + " -> " + Path.GetFileName(ruta));
                        }
                        catch (Exception e)
                        {
                            Debug.Log("[PlayDiag] sin captura (" + e.Message + ")");
                        }
                    }
                }
            }
        }

        // Un elemento sin diagrama (losa) debe mostrar el mensaje explicito.
        if (porTipo.ContainsKey("loza"))
        {
            var losa = porTipo["loza"][0];
            if (Seleccionar(insp, losa))
            {
                Set(insp, "currentCase", "COMBO");
                yield return null;
                Debug.Log("[PlayDiag] losa " + losa.elementId +
                          " -> la ficha debe mostrar el mensaje explicito");
            }
        }

        // Cambiar de caso y plano muchas veces: la ficha cachea, no debe leakear.
        var viga = porTipo.ContainsKey("beam_x") ? porTipo["beam_x"][0] : null;
        if (viga != null && Seleccionar(insp, viga))
        {
            long antes = GC.GetTotalMemory(true);
            for (int i = 0; i < 120; i++)
            {
                Set(insp, "currentCase", Casos[i % Casos.Length]);
                Set(insp, "diagramPlane", i % 2);
            }
            yield return null;
            long despues = GC.GetTotalMemory(true);
            Debug.Log("[PlayDiag] 120 cambios de caso/plano · memoria " +
                      (antes / 1024 / 1024) + " -> " + (despues / 1024 / 1024) + " MB");
        }

        Debug.Log("[PlayDiag] " + (fallos == 0
            ? "VERIFICACION OK (tipos: " + string.Join(", ",
                  objetivos.Select(o => o.type).Distinct().OrderBy(s => s)) + ")"
            : fallos + " FALLO(S)"));
        yield break;
    }

    static void Terminar(int rc, string err = null)
    {
        EditorApplication.update -= Tick;
        if (err != null) Debug.LogError("[PlayDiag] " + err);
        EditorApplication.Exit(rc);
    }

    static bool Ready()
    {
        return AnalysisMap.Loaded &&
               AnalysisMap.ElementsByTag != null && AnalysisMap.ElementsByTag.Count > 0 &&
               UnityEngine.Object.FindObjectsByType<ElementTag>(
                   FindObjectsInactive.Include, FindObjectsSortMode.None).Length > 0;
    }

    static bool Seleccionar(TributaryInspector insp, ElementTag t)
    {
        var mi = typeof(TributaryInspector).GetMethod("Select",
            BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
        if (mi != null && mi.GetParameters().Length == 1)
        {
            mi.Invoke(insp, new object[] { t });
            return true;
        }
        return Set(insp, "selected", t);
    }

    static bool Set(object obj, string name, object value)
    {
        var f = obj.GetType().GetField(name,
            BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Public);
        if (f == null) { Debug.LogWarning("[PlayDiag] no existe el campo " + name); return false; }
        f.SetValue(obj, value);
        return true;
    }
}
