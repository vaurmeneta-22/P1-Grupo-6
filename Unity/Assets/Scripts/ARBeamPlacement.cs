using System.Collections.Generic;
using UnityEngine;
#if USE_AR_FOUNDATION
using UnityEngine.XR.ARFoundation;
using UnityEngine.XR.ARSubsystems;
#endif

// Placement v2: only the preview follows the aiming ray. Placed content belongs
// to an ARAnchor, never to the camera. Camera motion never writes its transform.
public class ARBeamPlacement : MonoBehaviour
{
    public Camera arCamera;
    public Material beamMaterial;
    public Material guideMaterial;
    public const string VersionLabel = "Viga 185 | Resultados v4";
    ARBeamDiagrams diagrams;
    GameObject preview;
    Transform beamRoot;
    bool busy;
    bool editing;
    bool confirmReset;
    bool candidateValid;
    bool diagnostics;
    bool tracking;
    Pose candidatePose;
    Vector3 initialPosition;
    string message = "Mueve lentamente el telefono mirando al suelo.";
    string error;
    int stepIndex = 1;
    readonly float[] steps = { 0.05f, 0.25f, 1f };
    readonly float[] angles = { 1f, 5f, 15f };
    Vector2 scroll;
    GUIStyle labelStyle, titleStyle, buttonStyle;
#if USE_AR_FOUNDATION
    ARRaycastManager raycasts;
    ARPlaneManager planes;
    ARAnchorManager anchors;
    ARAnchor anchor;
    readonly List<ARRaycastHit> hits = new List<ARRaycastHit>();

    void Awake()
    {
        raycasts = GetComponent<ARRaycastManager>();
        planes = GetComponent<ARPlaneManager>();
        anchors = GetComponent<ARAnchorManager>();
        diagrams = GetComponent<ARBeamDiagrams>();
        Screen.sleepTimeout = SleepTimeout.NeverSleep;
        Application.targetFrameRate = 60;
        if (arCamera == null || raycasts == null || planes == null || anchors == null || beamMaterial == null || guideMaterial == null)
        {
            error = "La escena AR esta incompleta. Instala el APK Resultados v4.";
            enabled = false;
            return;
        }
        CreatePreview();
        Debug.Log("AR185 Placement v2: starting; 1 Unity unit = 1 metre.");
    }

    void Update()
    {
        tracking = ARSession.state == ARSessionState.SessionTracking;
        candidateValid = false;
        if (beamRoot != null)
        {
            tracking = tracking && anchor != null && anchor.trackingState == TrackingState.Tracking;
            beamRoot.gameObject.SetActive(tracking);
            preview.SetActive(false);
            message = tracking ? (editing ? "Ajusta con los botones y pulsa Fijar." : "Viga fija. Puedes moverte alrededor.")
                               : "Seguimiento limitado. Mira lentamente una zona con detalles para recuperarlo.";
            return;
        }
        if (busy) { preview.SetActive(false); return; }
        if (!tracking)
        {
            preview.SetActive(false);
            message = ARSession.state == ARSessionState.Unsupported
                ? "Este dispositivo no tiene soporte AR disponible."
                : "Buscando seguimiento: " + ARSession.state + " / " + ARSession.notTrackingReason;
            return;
        }
        // Aim at the centre of the camera image. The button is below this ray.
        if (raycasts.Raycast(new Vector2(Screen.width * 0.5f, Screen.height * 0.5f), hits, TrackableType.PlaneWithinPolygon))
        {
            foreach (var hit in hits)
            {
                ARPlane plane = planes.GetPlane(hit.trackableId);
                if (plane == null || plane.alignment != PlaneAlignment.HorizontalUp || plane.trackingState != TrackingState.Tracking)
                    continue;
                if (hit.distance < 0.3f || hit.distance > 8f) continue;
                candidatePose = new Pose(hit.pose.position, ARBeamPlacementMath.BeamRotation(arCamera.transform.forward, arCamera.transform.right));
                candidateValid = true;
                preview.transform.SetPositionAndRotation(candidatePose.position, candidatePose.rotation);
                break;
            }
        }
        preview.SetActive(candidateValid);
        message = candidateValid ? "Suelo detectado. La flecha indica hacia donde saldran los 10 m."
                                 : "Apunta al suelo a 0.3-8 m y mueve lentamente el telefono. Busca una zona iluminada con textura.";
    }

    async void Place()
    {
        if (busy || !candidateValid || beamRoot != null || !tracking) return;
        Pose pose = candidatePose; // Capture once; never follow the camera after this.
        busy = true;
        error = null;
        message = "Fijando la viga al entorno...";
        try
        {
            var result = await anchors.TryAddAnchorAsync(pose);
            if (this == null)
            {
                if (result.value != null && anchors != null) anchors.TryRemoveAnchor(result.value);
                return;
            }
            if (!result.status.IsSuccess() || result.value == null)
                throw new System.InvalidOperationException("No se pudo crear el anclaje: " + result.status);
            anchor = result.value;
            beamRoot = CreateBeam(anchor.transform, beamMaterial, guideMaterial);
            beamRoot.localPosition = new Vector3(0f, ARBeamPlacementMath.Height * 0.5f, 0f);
            initialPosition = beamRoot.position;
            if (diagrams != null) diagrams.SetBeam(beamRoot);
            editing = false;
            preview.SetActive(false);
            Debug.Log("AR185 Placement v2: placed at " + pose.position + "; dimensions 10 x 0.8 x 0.6 m.");
        }
        catch (System.Exception ex)
        {
            error = "No se pudo colocar. Apunta otra vez al suelo y reintenta.";
            Debug.LogException(ex);
        }
        finally { busy = false; }
    }

    // Re-anchor near the adjusted beam centre. Preserve the visible world pose;
    // never move the ARAnchor transform itself (the XR provider owns that pose).
    async void Fix()
    {
        if (busy || !editing || !tracking || beamRoot == null) return;
        busy = true;
        error = null;
        ARAnchor previous = anchor;
        Pose pose = new Pose(beamRoot.TransformPoint(new Vector3(ARBeamPlacementMath.Length * 0.5f, 0f, 0f)), beamRoot.rotation);
        try
        {
            var result = await anchors.TryAddAnchorAsync(pose);
            if (this == null)
            {
                if (result.value != null && anchors != null) anchors.TryRemoveAnchor(result.value);
                return;
            }
            if (!result.status.IsSuccess() || result.value == null)
                throw new System.InvalidOperationException("No se pudo actualizar el anclaje: " + result.status);
            anchor = result.value;
            beamRoot.SetParent(anchor.transform, true);
            if (previous != null) anchors.TryRemoveAnchor(previous);
            editing = false;
            Debug.Log("AR185 Placement v2: adjustment fixed, anchor near beam centre.");
        }
        catch (System.Exception ex)
        {
            error = "No se pudo fijar el ajuste. Se conserva la viga; recupera seguimiento y reintenta.";
            Debug.LogException(ex);
        }
        finally { busy = false; }
    }

    void ResetPlacement()
    {
        if (busy) return;
        if (diagrams != null) diagrams.ClearBeam();
        if (beamRoot != null) Destroy(beamRoot.gameObject);
        beamRoot = null;
        if (anchor != null) anchors.TryRemoveAnchor(anchor);
        anchor = null;
        editing = false;
        confirmReset = false;
        error = null;
    }
#else
    void Start() { error = "AR Foundation no esta habilitado en esta compilacion."; }
#endif

    public static Transform CreateBeam(Transform parent, Material body, Material guide)
    {
        Transform root = new GameObject("Viga185_Adjustment").transform;
        root.SetParent(parent, false);
        var cube = Primitive(root, "Viga185_10m_60x80cm", new Vector3(5f, 0f, 0f),
            new Vector3(ARBeamPlacementMath.Length, ARBeamPlacementMath.Height, ARBeamPlacementMath.Width), body);
        ElementTag tag = cube.AddComponent<ElementTag>();
        tag.elementId = 185; tag.type = "beam_x"; tag.section = "60x80";
        tag.niNode = 60; tag.njNode = 70; tag.piso = "Piso 3";
        // Thin bands at every metre let the user check scale with a physical tape.
        for (int i = 0; i <= 10; i++)
            Primitive(root, "Marca_" + i + "m", new Vector3(i, 0f, 0f), new Vector3(0.018f, 0.806f, 0.606f), guide);
        return root;
    }

    static GameObject Primitive(Transform parent, string name, Vector3 position, Vector3 scale, Material mat)
    {
        GameObject obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
        obj.name = name;
        obj.transform.SetParent(parent, false);
        obj.transform.localPosition = position;
        obj.transform.localScale = scale;
        obj.GetComponent<Renderer>().sharedMaterial = mat;
        // No physical interactions with the camera or AR raycast.
        obj.GetComponent<Collider>().enabled = false;
        return obj;
    }

    void CreatePreview()
    {
        preview = new GameObject("Inicio_y_direccion");
        Primitive(preview.transform, "Origen", new Vector3(0f, 0.012f, 0f), new Vector3(0.16f, 0.02f, 0.16f), guideMaterial);
        Primitive(preview.transform, "Flecha_1m", new Vector3(0.5f, 0.012f, 0f), new Vector3(1f, 0.018f, 0.025f), guideMaterial);
        var a = Primitive(preview.transform, "Flecha_A", new Vector3(0.90f, 0.012f, 0.08f), new Vector3(0.26f, 0.018f, 0.025f), guideMaterial);
        var b = Primitive(preview.transform, "Flecha_B", new Vector3(0.90f, 0.012f, -0.08f), new Vector3(0.26f, 0.018f, 0.025f), guideMaterial);
        a.transform.localRotation = Quaternion.Euler(0f, 40f, 0f);
        b.transform.localRotation = Quaternion.Euler(0f, -40f, 0f);
        preview.SetActive(false);
    }

    void Move(float sideways, float away, float up)
    {
        if (!editing || busy || !tracking || beamRoot == null) return;
        beamRoot.position += ARBeamPlacementMath.CameraRelativeDelta(arCamera.transform.forward, arCamera.transform.right,
            sideways * steps[stepIndex], away * steps[stepIndex], up * steps[stepIndex]);
    }

    void Rotate(float sign)
    {
        if (!editing || busy || !tracking || beamRoot == null) return;
        ARBeamPlacementMath.RotateAboutCentre(beamRoot, angles[stepIndex] * sign);
    }

    void OnGUI()
    {
        if (labelStyle == null)
        {
            labelStyle = new GUIStyle(GUI.skin.label) { fontSize = 16, wordWrap = true };
            titleStyle = new GUIStyle(labelStyle) { fontSize = 21, fontStyle = FontStyle.Bold };
            buttonStyle = new GUIStyle(GUI.skin.button) { fontSize = 17, wordWrap = true };
        }
        Rect safe = Screen.safeArea;
        float scale = safe.width / 420f;
        float height = safe.height / scale;
        Matrix4x4 old = GUI.matrix;
        GUI.matrix = Matrix4x4.TRS(new Vector3(safe.x, Screen.height - safe.yMax, 0f), Quaternion.identity, new Vector3(scale, scale, 1f));
        GUILayout.BeginArea(new Rect(8f, 6f, 404f, 155f), GUI.skin.box);
        GUILayout.Label(VersionLabel, titleStyle);
        GUILayout.Label("Escala 1:1 | 10 m | seccion 60 x 80 cm", labelStyle);
        GUILayout.Label(error ?? message, labelStyle);
        GUILayout.EndArea();

        if (beamRoot == null)
        {
            // Same screen centre used by the AR raycast, independent of safe area.
            float cx = (Screen.width * 0.5f - safe.x) / scale;
            float cy = (Screen.height * 0.5f - (Screen.height - safe.yMax)) / scale;
            GUI.color = candidateValid ? Color.green : Color.white;
            GUI.Label(new Rect(cx - 12f, cy - 18f, 36f, 36f), "+", titleStyle);
            GUI.color = Color.white;
        }
        float panelHeight = Mathf.Min(beamRoot != null ? 360f : 180f, height * 0.47f);
        GUILayout.BeginArea(new Rect(8f, height - panelHeight - 8f, 404f, panelHeight), GUI.skin.box);
        scroll = GUILayout.BeginScrollView(scroll);
        GUI.enabled = !busy;
#if USE_AR_FOUNDATION
        if (confirmReset)
        {
            GUILayout.Label("¿Quitar la viga y elegir otro punto?", labelStyle);
            if (Button("Si, volver a colocar")) ResetPlacement();
            if (Button("Cancelar")) confirmReset = false;
        }
        else if (beamRoot == null)
        {
            GUILayout.Label("Centra la mira en el suelo. La base de la viga quedara sobre esa superficie.", labelStyle);
            GUI.enabled = !busy && candidateValid && tracking;
            if (Button(busy ? "Colocando..." : "Colocar viga aqui")) Place();
        }
        else if (editing)
        {
            GUI.enabled = !busy && tracking;
            GUILayout.Label("Mover respecto a tu vista (cada pulsacion):", labelStyle);
            stepIndex = GUILayout.Toolbar(stepIndex, new[] { "5 cm / 1°", "25 cm / 5°", "1 m / 15°" }, buttonStyle, GUILayout.Height(42));
            GUILayout.BeginHorizontal();
            if (Button("Izquierda")) Move(-1, 0, 0);
            if (Button("Derecha")) Move(1, 0, 0);
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            if (Button("Alejar")) Move(0, 1, 0);
            if (Button("Acercar")) Move(0, -1, 0);
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            if (Button("Subir")) Move(0, 0, 1);
            if (Button("Bajar")) Move(0, 0, -1);
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            if (Button("Girar -")) Rotate(-1);
            if (Button("Girar +")) Rotate(1);
            GUILayout.EndHorizontal();
            if (Button(busy ? "Fijando..." : "Fijar posicion")) Fix();
        }
        else
        {
            GUILayout.Label("Marcas cada 1 m. La ubicacion se conserva durante esta sesion.", labelStyle);
            GUI.enabled = !busy && tracking;
            if (Button("Ajustar posicion")) { editing = true; scroll = Vector2.zero; }
            GUI.enabled = !busy;
            if (Button("Volver a colocar")) confirmReset = true;
            if (diagrams != null) diagrams.DrawControls(labelStyle, buttonStyle);
        }
#endif
        GUI.enabled = true;
        diagnostics = GUILayout.Toggle(diagnostics, " Ver estado AR", labelStyle);
        if (diagnostics)
        {
#if USE_AR_FOUNDATION
            GUILayout.Label("Sesion: " + ARSession.state + " | " + ARSession.notTrackingReason + "\nAnclaje: " + (anchor == null ? "sin colocar" : anchor.trackingState.ToString()), labelStyle);
#endif
            if (arCamera != null) GUILayout.Label("Camara (m): " + arCamera.transform.position.ToString("F2"), labelStyle);
            if (beamRoot != null) GUILayout.Label("Desplazamiento desde inicio (m): " + (beamRoot.position - initialPosition).ToString("F2"), labelStyle);
        }
        GUILayout.EndScrollView();
        GUILayout.EndArea();
        GUI.matrix = old;
    }

    bool Button(string text) { return GUILayout.Button(text, buttonStyle, GUILayout.Height(44f)); }

    void OnDestroy()
    {
        if (preview != null) Destroy(preview);
        if (beamRoot != null) Destroy(beamRoot.gameObject);
    }
}
