using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
#if USE_AR_FOUNDATION
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
#endif

// One Unity unit = one metre. Marker +X points from node 60 to node 70.
public class ARViga185Demo : MonoBehaviour
{
    const string MarkerName = "Grupo6_Viga185_AR";
    string status = "Iniciando AR";
    string results = "Cargando resultados G...";
    bool showResults = true;
    bool busy;
    bool failed;
    bool dataReady;
    Material material;
    GameObject content;
#if USE_AR_FOUNDATION
    ARTrackedImageManager images;
    ARAnchorManager anchors;
    ARAnchor anchor;
    ARTrackedImage candidate;
    Pose stablePose;
    float stableSince;

    void Awake()
    {
        images = GetComponent<ARTrackedImageManager>();
        anchors = GetComponent<ARAnchorManager>();
    }

    void Update()
    {
        if (busy || failed) return;
        if (anchor != null)
        {
            bool tracking = ARSession.state == ARSessionState.SessionTracking && anchor.trackingState == TrackingState.Tracking;
            content.SetActive(tracking);
            status = tracking ? "Viga colocada - escala real 1:1" : "Seguimiento limitado: mueve lentamente el telefono";
            return;
        }
        if (!dataReady) return;
        if (ARSession.state != ARSessionState.SessionTracking)
        {
            candidate = null;
            status = "Iniciando AR: " + ARSession.state;
            return;
        }
        ARTrackedImage found = null;
        foreach (var image in images.trackables)
            if (image.referenceImage.name == MarkerName && image.trackingState == TrackingState.Tracking) { found = image; break; }
        if (found == null)
        {
            candidate = null;
            status = "Apunta al marker horizontal de 20 x 20 cm";
            return;
        }
        if (Vector3.Dot(found.transform.up, Vector3.up) < 0.95f)
        {
            candidate = null;
            status = "Coloca el marker horizontal y mirando hacia arriba";
            return;
        }
        Pose pose = new Pose(found.transform.position, found.transform.rotation);
        if (candidate != found || Vector3.Distance(pose.position, stablePose.position) > 0.02f || Quaternion.Angle(pose.rotation, stablePose.rotation) > 3f)
        {
            candidate = found;
            stablePose = pose;
            stableSince = Time.unscaledTime;
        }
        status = "Referencia detectada: manten estable el telefono";
        if (Time.unscaledTime - stableSince >= 1.5f) Place(pose);
    }

    async void Place(Pose pose)
    {
        busy = true;
        status = "Creando anchor AR...";
        try
        {
            var result = await anchors.TryAddAnchorAsync(pose);
            if (this == null) return;
            if (!result.status.IsSuccess() || result.value == null)
                throw new System.InvalidOperationException("ARCore no pudo crear el anchor: " + result.status);
            anchor = result.value;
            CreateBeam(anchor.transform);
            Debug.Log("AR185 RealScale v1: anchor creado; dimensiones 10 x 0.8 x 0.6 m; nodo 60 en origen.");
        }
        catch (System.Exception ex)
        {
            failed = true;
            status = "No se pudo colocar. Pulsa Volver a ubicar.";
            Debug.LogException(ex);
        }
        finally { busy = false; }
    }
#endif

    IEnumerator Start()
    {
        // Android StreamingAssets lives inside the APK, not a filesystem directory.
        string source = Path.Combine(Application.streamingAssetsPath, "analysis_map.json");
        if (source.Contains("://"))
        {
            using (var request = UnityWebRequest.Get(source))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success)
                {
                    results = "Error leyendo resultados: " + request.error;
                    status = results;
                    yield break;
                }
                source = Path.Combine(Application.temporaryCachePath, "ar185_analysis_map.json");
                try { File.WriteAllBytes(source, request.downloadHandler.data); }
                catch (System.Exception ex) { results = status = ex.Message; yield break; }
            }
        }
        if (!AnalysisMap.Load(source)) { results = status = AnalysisMap.LoadError; yield break; }
        var meta = AnalysisMap.Element(185);
        if (meta == null || meta.ni != 60 || meta.nj != 70 || meta.section != "60x80")
        {
            results = status = "Datos de Viga 185 incompatibles con geometria 1:1";
            yield break;
        }
        if (AnalysisMap.Forces.TryGetValue("G", out var forces) && forces.TryGetValue(185, out var f) && f.li != null && f.lj != null && f.li.Length >= 6 && f.lj.Length >= 6)
            results = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "OpenSees - caso G\ni: Vz={0:F2} kN | My={1:F2} kN-m\nj: Vz={2:F2} kN | My={3:F2} kN-m", f.li[2], f.li[4], f.lj[2], f.lj[4]);
        else results = "Caso G: fuerzas no disponibles";
        dataReady = true;
    }

    void CreateBeam(Transform parent)
    {
        content = new GameObject("Viga185_RealScale");
        content.transform.SetParent(parent, false);
        material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
        material.SetColor("_BaseColor", new Color(0.05f, 0.82f, 1f));
        GameObject beam = GameObject.CreatePrimitive(PrimitiveType.Cube);
        beam.name = "Viga185_10m_60x80cm";
        beam.transform.SetParent(content.transform, false);
        beam.transform.localPosition = new Vector3(5f, 0f, 0f);
        beam.transform.localScale = new Vector3(10f, 0.8f, 0.6f);
        beam.GetComponent<Renderer>().sharedMaterial = material;
        var tag = beam.AddComponent<ElementTag>();
        tag.elementId = 185; tag.type = "beam_x"; tag.section = "60x80";
        tag.material = AnalysisMap.Element(185).material;
        tag.niNode = 60; tag.njNode = 70; tag.piso = "Piso 3";
    }

    void ResetPlacement()
    {
        if (busy) return;
        if (content != null) Destroy(content);
        if (material != null) Destroy(material);
#if USE_AR_FOUNDATION
        if (anchor != null && !anchors.TryRemoveAnchor(anchor)) Destroy(anchor.gameObject);
        anchor = null;
        candidate = null;
#endif
        failed = false;
        status = "Buscando referencia";
    }

    void OnGUI()
    {
        Matrix4x4 previous = GUI.matrix;
        float scale = Mathf.Max(1f, Screen.width / 480f);
        GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1));
        GUILayout.BeginArea(new Rect(8, 8, Screen.width / scale - 16, 260), GUI.skin.box);
        GUILayout.Label("Viga 185 | RealScale v1 | 1:1");
        GUILayout.Label("10 m - seccion 0.60 x 0.80 m");
        GUILayout.Label(status);
        if (showResults) GUILayout.Label(results);
        if (GUILayout.Button(showResults ? "Ocultar resultados" : "Mostrar resultados", GUILayout.Height(40))) showResults = !showResults;
        GUI.enabled = !busy;
        if (GUILayout.Button("Volver a ubicar", GUILayout.Height(40))) ResetPlacement();
        GUI.enabled = true;
        GUILayout.EndArea();
        GUI.matrix = previous;
    }

    void OnDestroy()
    {
        if (content != null) Destroy(content);
        if (material != null) Destroy(material);
    }
}
