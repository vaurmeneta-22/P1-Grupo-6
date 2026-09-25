using UnityEngine;
using UnityEngine.SceneManagement;
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

// Panel de modificaciones reproducibles del modelo. En PC/Editor ejecuta los
// mismos scripts que se usaban desde terminal y recarga la escena al terminar.
public class ModificationMode : MonoBehaviour
{
    public bool Active { get { return active; } }

    bool active;
    bool running;
    bool success;
    bool requestReload;
    bool reloadPending;
    bool historyPending;
    bool modelPending;
    float reloadAt;
    string status = "Listo";
    string activeModel = "Base";
    string log = "";
    string history = "";
    string pendingHistoryLine = "";
    string pendingModel = "";
    Vector2 scroll;
    Thread worker;

    const string CurrentModelKey = "P1.CurrentModel";
    const string HistoryKey = "P1.ModificationHistory";

    void Start()
    {
        activeModel = PlayerPrefs.GetString(CurrentModelKey, "Base");
        history = PlayerPrefs.GetString(HistoryKey, "");
    }

    public void SetActive(bool value)
    {
        active = value;
    }

    void Update()
    {
        if (requestReload)
        {
            requestReload = false;
            reloadPending = true;
            reloadAt = Time.realtimeSinceStartup + 1.0f;
        }
        if (historyPending)
        {
            historyPending = false;
            AddHistoryLine(pendingHistoryLine);
            pendingHistoryLine = "";
        }
        if (modelPending)
        {
            modelPending = false;
            activeModel = pendingModel;
            PlayerPrefs.SetString(CurrentModelKey, activeModel);
            PlayerPrefs.Save();
            pendingModel = "";
        }
        if (reloadPending && Time.realtimeSinceStartup >= reloadAt)
        {
            reloadPending = false;
            SceneManager.LoadScene(SceneManager.GetActiveScene().buildIndex);
        }
    }

    void OnGUI()
    {
        if (!active)
        {
            ElementInfoStyle.ModificationArea = new Rect();
            return;
        }
        Rect area = ElementInfoStyle.PanelRect();
        ElementInfoStyle.ModificationArea = area;
        GUISkin previous = ElementInfoStyle.Begin(area);
        bool close = ElementInfoStyle.Header("Modificaciones", "CAMBIOS REPRODUCIBLES + REANALISIS");
        GUILayout.Space(8);
        scroll = GUILayout.BeginScrollView(scroll, false, false);

        ElementInfoStyle.Section("ESTADO");
        GUILayout.Label("Modelo activo: " + activeModel);
        ElementInfoStyle.Note(status);
        if (!Application.isEditor && !Application.platform.ToString().Contains("Windows"))
            ElementInfoStyle.Note("Reanalisis local disponible solo en PC/Editor con Python y OpenSees.");

        ElementInfoStyle.Section("ACCIONES");
        DrawAction("Restaurar Base", "Vuelve a Edificio.json y analysis_map.json originales.",
                   "No modifica el modelo base; solo restaura StreamingAssets.", RunBase);
        DrawAction("Aplicar Mod A", "Viga 147: seccion 60x80 -> 50x75.",
                   "Requiere reanalisis porque cambia rigidez y fuerzas internas.", RunModA);
        DrawAction("Aplicar Mod B", "Nodo 1: empotrado -> articulado DOF=[1,1,1,0,0,0].",
                   "Requiere reanalisis porque cambia condicion de borde.", RunModB);

        ElementInfoStyle.Section("MODIFICACIONES REALIZADAS");
        GUILayout.TextArea(string.IsNullOrEmpty(history) ? "Aun no hay modificaciones registradas desde Unity." : history,
                           GUILayout.MinHeight(120));
        GUI.enabled = !running && !string.IsNullOrEmpty(history);
        if (GUILayout.Button("Limpiar historial"))
        {
            history = "";
            PlayerPrefs.DeleteKey(HistoryKey);
            PlayerPrefs.Save();
        }
        GUI.enabled = true;

        ElementInfoStyle.Section("LOG");
        GUILayout.TextArea(string.IsNullOrEmpty(log) ? "Sin ejecuciones aun." : log, GUILayout.MinHeight(180));

        GUILayout.EndScrollView();
        ElementInfoStyle.End(previous);
        if (close) SetActive(false);
    }

    void DrawAction(string title, string desc, string note, Action action)
    {
        GUILayout.BeginVertical(GUI.skin.box);
        GUILayout.Label(title, new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold, fontSize = 18 });
        GUILayout.Label(desc);
        ElementInfoStyle.Note(note);
        GUI.enabled = !running;
        if (GUILayout.Button(running ? "Ejecutando..." : title)) action();
        GUI.enabled = true;
        GUILayout.EndVertical();
        GUILayout.Space(8);
    }

    void RunBase()
    {
        RunCommands("Base", new string[][]
        {
            new [] { "scripts/ejecutar_modificacion.py", "--restore" }
        });
    }

    void RunModA()
    {
        RunCommands("Mod A", new string[][]
        {
            new [] { "scripts/generar_modificaciones.py" },
            new [] { "scripts/ejecutar_modificacion.py", "--tag", "modA", "--json", "Edificio_mod_A.json", "--element", "147", "--unity" }
        });
    }

    void RunModB()
    {
        RunCommands("Mod B", new string[][]
        {
            new [] { "scripts/generar_modificaciones.py" },
            new [] { "scripts/ejecutar_modificacion.py", "--tag", "modB", "--json", "Edificio_mod_B.json", "--element", "76", "--unity" }
        });
    }

    void RunCommands(string label, string[][] commands)
    {
        if (running) return;
        running = true;
        success = false;
        reloadPending = false;
        status = "Ejecutando " + label + "...";
        log = "";

        worker = new Thread(() => Worker(label, commands));
        worker.IsBackground = true;
        worker.Start();
    }

    void Worker(string label, string[][] commands)
    {
        StringBuilder sb = new StringBuilder();
        bool ok = true;
        string repo = RepoRoot();
        try
        {
            foreach (string[] args in commands)
            {
                sb.AppendLine(">>> python " + string.Join(" ", args));
                int code = RunPython(repo, args, sb);
                if (code != 0)
                {
                    sb.AppendLine("[ERROR] codigo de salida: " + code);
                    ok = false;
                    break;
                }
            }
        }
        catch (Exception ex)
        {
            ok = false;
            sb.AppendLine("[ERROR] " + ex.Message);
        }

        log = sb.ToString();
        success = ok;
        activeModel = ok ? label : activeModel;
        status = ok ? label + " aplicado. Recargando Unity..." : "Fallo la modificacion. Revisa el log.";
        running = false;
        if (ok)
        {
            pendingModel = label;
            modelPending = true;
            pendingHistoryLine = HistoryLine(label);
            historyPending = true;
            requestReload = true;
        }
    }

    int RunPython(string repo, string[] scriptArgs, StringBuilder sb)
    {
        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = "python";
        psi.WorkingDirectory = repo;
        psi.UseShellExecute = false;
        psi.RedirectStandardOutput = true;
        psi.RedirectStandardError = true;
        psi.CreateNoWindow = true;
        psi.Arguments = QuoteArgs(scriptArgs);

        using (Process p = new Process())
        {
            p.StartInfo = psi;
            p.OutputDataReceived += (s, e) => { if (e.Data != null) sb.AppendLine(e.Data); };
            p.ErrorDataReceived += (s, e) => { if (e.Data != null) sb.AppendLine(e.Data); };
            p.Start();
            p.BeginOutputReadLine();
            p.BeginErrorReadLine();
            p.WaitForExit();
            return p.ExitCode;
        }
    }

    static string QuoteArgs(string[] args)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < args.Length; i++)
        {
            if (i > 0) sb.Append(' ');
            string a = args[i].Replace("\\", "/");
            if (a.Contains(" ")) sb.Append('"').Append(a.Replace("\"", "\\\"")).Append('"');
            else sb.Append(a);
        }
        return sb.ToString();
    }

    static string RepoRoot()
    {
        DirectoryInfo assets = new DirectoryInfo(Application.dataPath);
        DirectoryInfo unity = assets.Parent;
        return unity != null && unity.Parent != null ? unity.Parent.FullName : Application.dataPath;
    }

    void AddHistoryLine(string line)
    {
        if (string.IsNullOrEmpty(line)) return;
        history = string.IsNullOrEmpty(history) ? line : line + "\n" + history;
        PlayerPrefs.SetString(HistoryKey, history);
        PlayerPrefs.Save();
    }

    static string HistoryLine(string label)
    {
        string detalle;
        if (label == "Mod A") detalle = "Viga 147: seccion 60x80 -> 50x75; reanalisis OpenSees completado.";
        else if (label == "Mod B") detalle = "Nodo 1: empotrado -> articulado DOF=[1,1,1,0,0,0]; reanalisis OpenSees completado.";
        else detalle = "StreamingAssets restaurado al modelo base.";
        return DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " | " + label + " | " + detalle;
    }
}
