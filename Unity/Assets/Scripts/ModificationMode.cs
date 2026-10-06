using UnityEngine;
using UnityEngine.SceneManagement;
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Collections;
using System.Collections.Generic;
using UnityEngine.Networking;

[Serializable]
public class H4ReportData
{
    public string case_id;
    public string case_name;
    public H4CheckRow[] check_rows;
    public H4ComparisonRow[] comparison_rows;
}

[Serializable]
public class H4CheckRow
{
    public string name;
    public bool pass;
    public string detail;
}

[Serializable]
public class H4MetricSet
{
    public double load_kN;
    public double n_kN;
    public double my_kNm;
    public double mz_kNm;
    public double disp_mm;
}

[Serializable]
public class H4ComparisonRow
{
    public string case_name;
    public string node;
    public H4MetricSet unity;
    public H4MetricSet direct;
    public H4MetricSet delta;
    public bool pass;
}


[Serializable]
public class H4BackendRequest
{
    public string case_id = "C";
    public int element_id = 66;
    public float width_cm = 40f;
    public float height_cm = 40f;
    public int node_id = 1;
    public string support_type = "pinned";
}

[Serializable]
public class H4BackendResponse
{
    public bool ok;
    public string error;
    public string detail;
    public string model_json;
    public string analysis_map_json;
    public string report_json;
    public string report_text;
    public string solver_log;
}

// Panel de modificaciones reproducibles; Honor Track 4 inicia su backend local al solicitar el análisis.
public class ModificationMode : MonoBehaviour
{
    static string sessionH4ReportJson;
    static string sessionH4ReportText;
    static Process h4BackendProcess;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
    static void ResetH4SessionState()
    {
        sessionH4ReportJson = null;
        sessionH4ReportText = null;
    }

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
    string h4Report = "Aún no se ejecutó Honor Track 4 en esta sesión de Unity.";
    H4ReportData h4Data;
    bool h4ReportPending;
    bool backendStarting;
    bool backendReady;
    string selectedH4Case = "C";
    int panelTab;
    string pendingHistoryLine = "";
    string pendingModel = "";
    Vector2 scroll;
    Thread worker;

    const string CurrentModelKey = "P1.CurrentModel";
    const string HistoryKey = "P1.ModificationHistory";

    void Start()
    {
        activeModel = PlayerPrefs.GetString(CurrentModelKey, "Base");
        if (activeModel == "H4" || activeModel == "Caso C (H4)") activeModel = "Caso C";
        history = PlayerPrefs.GetString(HistoryKey, "");
        panelTab = PlayerPrefs.GetInt("P1.ModificationPanelTab", 0);
        selectedH4Case = PlayerPrefs.GetString("P1.H4Case", "C");
        RestoreSessionH4Report();
    }

    public void SetActive(bool value)
    {
        active = value;
    }

    void Update()
    {
        if (h4ReportPending)
        {
            h4ReportPending = false;
            RestoreSessionH4Report();
        }
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
        GUILayout.BeginHorizontal();
        if (ElementInfoStyle.Choice(panelTab == 0, "Modificaciones")) SetPanelTab(0);
        if (ElementInfoStyle.Choice(panelTab == 1, "Honor Track 4")) SetPanelTab(1);
        GUILayout.EndHorizontal();
        scroll = GUILayout.BeginScrollView(scroll, false, false);

        if (panelTab == 1)
        {
            DrawH4Panel();
            GUILayout.EndScrollView();
            ElementInfoStyle.End(previous);
            if (close) SetActive(false);
            return;
        }

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
        DrawAction("Aplicar Caso C", "Columna 66: seccion 70x70 -> 40x40 cm.",
                   "Recalcula los cinco casos y la curva P-M de la columna 66.", RunModC);

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

    void SetPanelTab(int value)
    {
        panelTab = value;
        PlayerPrefs.SetInt("P1.ModificationPanelTab", panelTab);
        PlayerPrefs.Save();
    }

    void SelectH4Case(string value)
    {
        selectedH4Case = value;
        PlayerPrefs.SetString("P1.H4Case", value);
        PlayerPrefs.Save();
    }

    static string H4CaseDescription(string value)
    {
        if (value == "A") return "Viga 147: cambia de 60×80 a 50×75 cm; se reanaliza la rigidez del marco.";
        if (value == "B") return "Apoyo del nodo 1: cambia de empotrado a articulado; se reanalizan las condiciones de borde.";
        return "Columna 66: cambia de 70×70 a 40×40 cm; se reanaliza y actualiza su curva P-M.";
    }

    static string H4CaseTarget(string value)
    {
        if (value == "A") return "VIGA 147";
        if (value == "B") return "APOYO NODO 1";
        return "COLUMNA 66";
    }

    void DrawH4Panel()
    {
        ElementInfoStyle.Section("HONOR TRACK 4 · COMPROBAR EL REANÁLISIS");
        GUILayout.Label("Elige qué cambio quieres analizar. Unity lo envía al backend Python/OpenSees; el backend lo valida, recalcula los cinco escenarios y devuelve los resultados para compararlos con una corrida directa y una repetición.",
            new GUIStyle(GUI.skin.label) { wordWrap = true });
        GUILayout.Space(6);
        GUILayout.BeginHorizontal();
        if (ElementInfoStyle.Choice(selectedH4Case == "A", "Caso A")) SelectH4Case("A");
        if (ElementInfoStyle.Choice(selectedH4Case == "B", "Caso B")) SelectH4Case("B");
        if (ElementInfoStyle.Choice(selectedH4Case == "C", "Caso C")) SelectH4Case("C");
        GUILayout.EndHorizontal();
        GUILayout.Label(H4CaseDescription(selectedH4Case), new GUIStyle(GUI.skin.label) { wordWrap = true });
        bool supported = Application.isEditor;
        if (!supported) ElementInfoStyle.Note("Honor Track 4 requiere Unity Editor en PC con Python y OpenSees instalados.");
        ElementInfoStyle.Note(backendReady ? "Conectado al backend local." : (backendStarting ? "Conectando con el backend…" : "Desconectado. Conéctate para habilitar el reanálisis."));
        GUI.enabled = !running && !backendStarting && supported;
        if (GUILayout.Button(backendReady ? "Desconectar backend" : (backendStarting ? "Conectando…" : "Conectar backend"), GUILayout.Height(36)))
        {
            if (backendReady) DisconnectH4Backend();
            else StartCoroutine(StartBackendOnDemand());
        }
        GUI.enabled = !running && backendReady && supported;
        if (GUILayout.Button(running ? "Ejecutando verificación…" : "Ejecutar verificación", GUILayout.Height(38))) RunH4();
        GUI.enabled = true;
        GUILayout.Space(8);
        if (h4Data != null && h4Data.check_rows != null)
        {
            ElementInfoStyle.Section("ESTADO DE LAS PRUEBAS");
            int passedChecks = 0;
            foreach (H4CheckRow check in h4Data.check_rows)
            {
                if (check.pass) passedChecks++;
                GUILayout.Label((check.pass ? "✓  " : "✕  ") + check.name + (string.IsNullOrEmpty(check.detail) ? "" : " — " + check.detail));
            }
            ElementInfoStyle.Note(passedChecks == h4Data.check_rows.Length
                ? "Resultado general: todas las pruebas pasaron."
                : "Resultado general: hay pruebas pendientes de corregir; revisa las que tienen una X.");
            ElementInfoStyle.Section("VALORES PARA COMPARAR · " + H4CaseTarget(h4Data.case_id));
            GUILayout.Label("En cada fila: resultado que devolvió el backend a Unity, corrida directa de OpenSees y diferencia entre ambos. Una diferencia cercana a cero significa que coinciden.");
            foreach (H4ComparisonRow row in h4Data.comparison_rows ?? new H4ComparisonRow[0]) DrawH4Case(row);
            GUILayout.Label("El desplazamiento corresponde al nodo indicado en cada fila y se expresa en milímetros.");
        }
        else
        {
            ElementInfoStyle.Section("RESULTADOS DE LA VERIFICACIÓN");
            GUILayout.TextArea(h4Report, new GUIStyle(GUI.skin.textArea) { wordWrap = true }, GUILayout.MinHeight(150));
        }
        GUILayout.Label("Prueba las dimensiones imposibles y el archivo faltante a propósito. Si aparece código 1 en esa prueba, significa que el programa detectó el error correctamente.");
        GUILayout.Label("Reporte detallado: resultados/12_h4/verificacion_h4.json.");
        if (!string.IsNullOrEmpty(log))
        {
            ElementInfoStyle.Section("LOG DE EJECUCIÓN");
            GUILayout.TextArea(log, GUILayout.MinHeight(120));
        }
    }

    void RestoreSessionH4Report()
    {
        h4Report = string.IsNullOrEmpty(sessionH4ReportText)
            ? "Aún no se ejecutó Honor Track 4 en esta sesión de Unity. Pulsa el botón para comenzar la verificación."
            : sessionH4ReportText;
        h4Data = string.IsNullOrEmpty(sessionH4ReportJson)
            ? null : JsonUtility.FromJson<H4ReportData>(sessionH4ReportJson);
    }

    static void DrawH4Case(H4ComparisonRow row)
    {
        if (row == null || row.unity == null || row.direct == null || row.delta == null) return;
        GUILayout.BeginVertical(GUI.skin.box);
        GUILayout.Label(row.case_name + (row.pass ? "  ✓" : "  ✕"), new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold, fontSize = 18 });
        GUILayout.BeginHorizontal();
        GUILayout.Label("Magnitud", GUILayout.Width(150));
        GUILayout.Label("Unity", GUILayout.Width(125));
        GUILayout.Label("Directo", GUILayout.Width(125));
        GUILayout.Label("Diferencia", GUILayout.ExpandWidth(true));
        GUILayout.EndHorizontal();
        DrawH4Metric("Carga [kN]", row.unity.load_kN, row.direct.load_kN, row.delta.load_kN);
        DrawH4Metric("Axial [kN]", row.unity.n_kN, row.direct.n_kN, row.delta.n_kN);
        DrawH4Metric("Momento Y [kN·m]", row.unity.my_kNm, row.direct.my_kNm, row.delta.my_kNm);
        DrawH4Metric("Momento Z [kN·m]", row.unity.mz_kNm, row.direct.mz_kNm, row.delta.mz_kNm);
        DrawH4Metric("Desplazamiento [mm]", row.unity.disp_mm, row.direct.disp_mm, row.delta.disp_mm);
        GUILayout.EndVertical();
    }

    static void DrawH4Metric(string label, double unity, double direct, double delta)
    {
        GUILayout.BeginHorizontal();
        GUILayout.Label(label, GUILayout.Width(150));
        GUILayout.Label(unity.ToString("G6"), GUILayout.Width(125));
        GUILayout.Label(direct.ToString("G6"), GUILayout.Width(125));
        GUILayout.Label(delta.ToString("G3"), GUILayout.ExpandWidth(true));
        GUILayout.EndHorizontal();
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

    void RunModC()
    {
        RunCommands("Caso C", new string[][]
        {
            new [] { "scripts/generar_modificaciones.py" },
            new [] { "scripts/generar_pm_caso_c.py" },
            new [] { "scripts/ejecutar_modificacion.py", "--tag", "modC", "--json", "Edificio_mod_C.json", "--element", "66", "--all-cases", "--unity", "--capacity-json", "resultados/07_capacidad/pm_columnas/pm_columna_id66_40x40.json" }
        });
    }

    void RunH4()
    {
        if (running) return;
        if (!backendReady)
        {
            SetH4Failure("Conecta el backend antes de ejecutar la verificación.", "Pulsa Conectar backend.");
            return;
        }
        running = true;
        sessionH4ReportJson = null;
        sessionH4ReportText = null;
        h4Data = null;
        h4Report = "Enviando el Caso " + selectedH4Case + " al backend y esperando los resultados.";
        log = "Unity está enviando la solicitud al backend conectado…";
        status = "Ejecutando reanálisis OpenSees...";
        StartCoroutine(RunH4Request());
    }

    IEnumerator RunH4Request()
    {
        string baseUrl = "http://127.0.0.1:8765";
        status = "Enviando modificación y esperando el reanálisis...";
        H4BackendRequest payload = new H4BackendRequest();
        payload.case_id = selectedH4Case;
        if (selectedH4Case == "A")
        {
            payload.element_id = 147;
            payload.width_cm = 50f;
            payload.height_cm = 75f;
        }
        else if (selectedH4Case == "B")
        {
            payload.element_id = 0;
            payload.width_cm = 0f;
            payload.height_cm = 0f;
            payload.node_id = 1;
            payload.support_type = "pinned";
        }
        byte[] body = Encoding.UTF8.GetBytes(JsonUtility.ToJson(payload));
        using (UnityWebRequest request = new UnityWebRequest(baseUrl + "/reanalyze", "POST"))
        {
            request.uploadHandler = new UploadHandlerRaw(body);
            request.downloadHandler = new DownloadHandlerBuffer();
            request.SetRequestHeader("Content-Type", "application/json; charset=utf-8");
            request.timeout = 3600;
            yield return request.SendWebRequest();
            if (request.result != UnityWebRequest.Result.Success)
            {
                backendReady = false;
                string message = "El backend no pudo completar el análisis: " + request.error;
                string detail = request.downloadHandler != null ? request.downloadHandler.text : "";
                try
                {
                    H4BackendResponse error = JsonUtility.FromJson<H4BackendResponse>(detail);
                    if (error != null && !string.IsNullOrEmpty(error.error))
                    {
                        message = error.error;
                        detail = error.detail;
                    }
                }
                catch { }
                SetH4Failure(message, detail);
                yield break;
            }
            H4BackendResponse response = null;
            string responseParseError = null;
            try { response = JsonUtility.FromJson<H4BackendResponse>(request.downloadHandler.text); }
            catch (Exception ex) { responseParseError = ex.Message; }
            if (responseParseError != null)
            {
                SetH4Failure("Unity no pudo leer la respuesta del backend.", responseParseError);
                yield break;
            }
            if (response == null || !response.ok || string.IsNullOrEmpty(response.model_json) ||
                string.IsNullOrEmpty(response.analysis_map_json) || string.IsNullOrEmpty(response.report_json))
            {
                SetH4Failure(response != null && !string.IsNullOrEmpty(response.error) ? response.error : "La respuesta del backend está incompleta.", response != null ? response.detail : "");
                yield break;
            }
            try
            {
                EdificioData model = JsonUtility.FromJson<EdificioData>(response.model_json);
                bool targetValid = false;
                if (selectedH4Case == "A")
                {
                    ElementData beam = model != null && model.elements != null ? model.elements.Find(e => e.id == 147) : null;
                    targetValid = beam != null && beam.type == "beam_y" && beam.b == 50f && beam.h == 75f;
                }
                else if (selectedH4Case == "B")
                {
                    SupportInfo support = model != null && model.supports != null
                        ? Array.Find(model.supports, s => s.node == 1) : null;
                    targetValid = support != null && support.type == "pinned" && support.DOF != null &&
                        support.DOF.Length == 6 && support.DOF[0] == 1 && support.DOF[1] == 1 &&
                        support.DOF[2] == 1 && support.DOF[3] == 0 && support.DOF[4] == 0 && support.DOF[5] == 0;
                }
                else
                {
                    ElementData column = model != null && model.elements != null ? model.elements.Find(e => e.id == 66) : null;
                    targetValid = column != null && column.type == "column" && column.b == 40f && column.h == 40f;
                }
                if (!targetValid)
                    throw new InvalidDataException("El modelo recibido no corresponde al cambio seleccionado para el Caso " + selectedH4Case + ".");
                object mapRoot;
                if (!MiniJson.TryParse(response.analysis_map_json, out mapRoot) || MiniJson.AsDict(mapRoot) == null)
                    throw new InvalidDataException("El mapa de análisis recibido no es JSON válido.");
                H4ReportData report = JsonUtility.FromJson<H4ReportData>(response.report_json);
                if (report == null || report.case_id != selectedH4Case || report.check_rows == null || report.comparison_rows == null || report.comparison_rows.Length != 5)
                    throw new InvalidDataException("El reporte no contiene los cinco escenarios de comparación.");
                var checks = new List<H4CheckRow>(report.check_rows);
                checks.Add(new H4CheckRow { name = "Unity recibió resultados del backend", pass = true,
                    detail = "Unity recibió y validó el modelo, el mapa y la comparación de los cinco escenarios." });
                report.check_rows = checks.ToArray();
                Directory.CreateDirectory(Application.persistentDataPath);
                WriteRuntimeFile(Path.Combine(Application.persistentDataPath, "Edificio.json"), response.model_json);
                WriteRuntimeFile(Path.Combine(Application.persistentDataPath, "analysis_map.json"), response.analysis_map_json);
                sessionH4ReportJson = JsonUtility.ToJson(report);
                sessionH4ReportText = response.report_text ?? "El backend completó el reanálisis.";
                h4ReportPending = true;
                log = "Backend respondió correctamente. Unity recibió el modelo y los resultados.\n" + (response.solver_log ?? "");
                activeModel = "Caso " + selectedH4Case;
                pendingModel = activeModel;
                modelPending = true;
                pendingHistoryLine = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " | H4 " + selectedH4Case + " | " + H4CaseDescription(selectedH4Case);
                historyPending = true;
                status = "Reanálisis recibido. Actualizando el visor…";
                running = false;
                requestReload = true;
            }
            catch (Exception ex) { SetH4Failure("Unity no pudo validar o guardar los resultados recibidos.", ex.Message); }
        }
    }

    IEnumerator StartBackendOnDemand()
    {
        if (backendStarting || backendReady) yield break;
        backendStarting = true;
        string baseUrl = "http://127.0.0.1:8765";
        bool ready = false;
        using (UnityWebRequest health = UnityWebRequest.Get(baseUrl + "/health"))
        {
            health.timeout = 3;
            yield return health.SendWebRequest();
            ready = health.result == UnityWebRequest.Result.Success && health.responseCode == 200;
        }
        if (!ready && !StartH4Backend())
        {
            backendStarting = false;
            SetH4Failure("No se pudo iniciar el backend local.", "Comprueba que Python esté instalado y disponible en PATH.");
            yield break;
        }
        for (int attempt = 0; attempt < 40 && !ready; attempt++)
        {
            yield return new WaitForSecondsRealtime(0.5f);
            using (UnityWebRequest health = UnityWebRequest.Get(baseUrl + "/health"))
            {
                health.timeout = 2;
                yield return health.SendWebRequest();
                ready = health.result == UnityWebRequest.Result.Success && health.responseCode == 200;
            }
            if (h4BackendProcess != null && h4BackendProcess.HasExited)
            {
                backendStarting = false;
                SetH4Failure("El backend se cerró durante el inicio.", "Revisa que el puerto 8765 esté disponible y que Python pueda iniciar el servidor.");
                yield break;
            }
        }
        backendStarting = false;
        backendReady = ready;
        if (!ready) log = "Unity esperó 20 segundos, pero el backend no respondió.";
        else log = "Backend local iniciado y listo.";
    }

    void DisconnectH4Backend()
    {
        backendReady = false;
        if (h4BackendProcess != null)
        {
            try
            {
                if (!h4BackendProcess.HasExited) h4BackendProcess.Kill();
                h4BackendProcess.Dispose();
            }
            catch (Exception ex) { UnityEngine.Debug.LogWarning("No se pudo detener el backend H4: " + ex.Message); }
            h4BackendProcess = null;
        }
        status = "Backend desconectado.";
        log = "La conexión del visor se cerró.";
    }

    bool StartH4Backend()
    {
        if (h4BackendProcess != null)
        {
            try { if (!h4BackendProcess.HasExited) return true; }
            catch { }
            h4BackendProcess = null;
        }
        try
        {
            string repo = RepoRoot();
            ProcessStartInfo info = new ProcessStartInfo();
            info.FileName = "python";
            info.WorkingDirectory = repo;
            info.Arguments = "scripts/backend_opensees.py";
            info.UseShellExecute = false;
            info.CreateNoWindow = true;
            info.WindowStyle = ProcessWindowStyle.Hidden;
            h4BackendProcess = Process.Start(info);
            return h4BackendProcess != null;
        }
        catch (Exception ex)
        {
            log = "No se pudo iniciar Python: " + ex.Message;
            return false;
        }
    }

    static void WriteRuntimeFile(string path, string contents)
    {
        string temp = path + ".tmp";
        File.WriteAllText(temp, contents, new UTF8Encoding(false));
        if (File.Exists(path)) File.Delete(path);
        File.Move(temp, path);
    }

    void SetH4Failure(string message, string detail)
    {
        running = false;
        status = "Honor Track 4 no se completó.";
        h4Report = message;
        log = string.IsNullOrEmpty(detail) ? message : message + "\n" + detail;
    }

    void OnApplicationQuit()
    {
        try
        {
            if (h4BackendProcess != null && !h4BackendProcess.HasExited)
            {
                h4BackendProcess.Kill();
                h4BackendProcess.Dispose();
                h4BackendProcess = null;
            }
        }
        catch (Exception ex) { UnityEngine.Debug.LogWarning("No se pudo cerrar el backend H4: " + ex.Message); }
    }

    void RunCommands(string label, string[][] commands)
    {
        if (running) return;
        ClearRuntimeOverrides();
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
        if (label == "H4")
        {
            string reportPath = Path.Combine(repo, "resultados", "12_h4", "verificacion_h4.json");
            string textPath = Path.Combine(repo, "resultados", "12_h4", "verificacion_h4.txt");
            if (File.Exists(reportPath)) sessionH4ReportJson = File.ReadAllText(reportPath, Encoding.UTF8);
            if (File.Exists(textPath)) sessionH4ReportText = File.ReadAllText(textPath, Encoding.UTF8);
            h4ReportPending = true;
        }
        activeModel = ok ? (label == "H4" ? "Caso " + selectedH4Case + " (H4)" : label) : activeModel;
        status = ok ? (label == "H4" ? "H4 terminado para Caso " + selectedH4Case + ". Revisa los veredictos; recargando Unity..." : label + " aplicado. Recargando Unity...") : "Fallo la modificacion. Revisa el log y el reporte.";
        running = false;
        if (ok)
        {
            pendingModel = label == "H4" ? "Caso " + selectedH4Case : label;
            modelPending = true;
            pendingHistoryLine = HistoryLine(label, selectedH4Case);
            historyPending = true;
            requestReload = true;
        }
    }

    static void ClearRuntimeOverrides()
    {
        string dir = Application.persistentDataPath;
        string model = Path.Combine(dir, "Edificio.json");
        string map = Path.Combine(dir, "analysis_map.json");
        if (File.Exists(model)) File.Delete(model);
        if (File.Exists(map)) File.Delete(map);
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

    static string HistoryLine(string label, string h4Case = "C")
    {
        string detalle;
        if (label == "H4") detalle = "Honor Track 4: Caso " + h4Case + " reanalizado, comparado con corrida directa y repetido.";
        else if (label == "Mod A") detalle = "Viga 147: seccion 60x80 -> 50x75; reanalisis OpenSees completado.";
        else if (label == "Mod B") detalle = "Nodo 1: empotrado -> articulado DOF=[1,1,1,0,0,0]; reanalisis OpenSees completado.";
        else if (label == "Caso C") detalle = "Columna 66: sección 70x70 -> 40x40 cm; cinco casos y capacidad P-M recalculados.";
        else detalle = "StreamingAssets restaurado al modelo base.";
        return DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss") + " | " + label + " | " + detalle;
    }
}
