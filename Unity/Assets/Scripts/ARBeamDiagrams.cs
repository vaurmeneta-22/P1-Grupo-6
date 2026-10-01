using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;

// Same signed My/Vz reconstruction as desktop. Abscissas remain physical metres.
public class ARBeamDiagrams : MonoBehaviour
{
    public Camera arCamera;
    public Material positiveMaterial, negativeMaterial, zeroMaterial;
    readonly string[] cases = { "G", "Q", "EX", "EY", "COMBO" };
    readonly Dictionary<string, AnalysisMap.DiagInfo> data = new Dictionary<string, AnalysisMap.DiagInfo>();
    Transform beam;
    GameObject drawing;
    int mode, caseIndex;
    float amplitude = 1f, displacementGain = 120f;
    Renderer[] bodyRenderers;
    readonly int[] nodes = { 60, 63, 67, 70 };
    Vector3[] nodePoints, displacements;
    double[] nodeMagnitudes;
    double distributedLoad;
    double[] nodalWeight;
    string loadError;
    bool ready;
    readonly List<int> labels = new List<int>();
    double peak;
    int minIndex, maxIndex;
    GUIStyle worldLabel;

    IEnumerator Start()
    {
        string path = Path.Combine(Application.streamingAssetsPath, "analysis_map.json");
        if (path.Contains("://"))
        {
            using (var request = UnityWebRequest.Get(path))
            {
                yield return request.SendWebRequest();
                if (request.result != UnityWebRequest.Result.Success)
                { loadError = "No se pudieron cargar los diagramas: " + request.error; yield break; }
                path = Path.Combine(Application.temporaryCachePath, "ar185_diagrams.json");
                try { File.WriteAllBytes(path, request.downloadHandler.data); }
                catch (Exception ex) { loadError = ex.Message; yield break; }
            }
        }
        if (!AnalysisMap.Load(path)) { loadError = AnalysisMap.LoadError; yield break; }
        try
        {
            foreach (string name in cases) data.Add(name, ValidatedDiagram(name));
            ready = true;
            Refresh();
        }
        catch (Exception ex) { loadError = "Diagramas no disponibles: " + ex.Message; Debug.LogException(ex); }
    }

    public static AnalysisMap.DiagInfo ValidatedDiagram(string name)
    {
        var meta = AnalysisMap.Element(185);
        if (meta == null || meta.ni != 60 || meta.nj != 70 || meta.section != "60x80")
            throw new InvalidOperationException("Identidad de viga 185 incompatible.");
        var r = ElementDiagrams.Construir(185, name, ElementDiagrams.PlanoVertical);
        var d = r.diag;
        if (r.error != null || d == null || Math.Abs(d.L - ARBeamPlacementMath.Length) > 1e-5)
            throw new InvalidOperationException(name + ": faltan resultados o longitud incompatible.");
        if (r.errN > 1e-4 || r.errV > 1e-4 || r.errM > 1e-4)
            throw new InvalidOperationException(name + ": las fuerzas no cierran el diagrama.");
        if (d.x.Length < 2 || d.x.Length != d.M.Length || d.x.Length != d.V.Length || d.x.Length != d.N.Length)
            throw new InvalidOperationException(name + ": muestras incompatibles.");
        for (int i = 0; i < d.x.Length; i++)
            if (double.IsNaN(d.x[i]) || double.IsInfinity(d.x[i]) || double.IsNaN(d.M[i]) || double.IsInfinity(d.M[i]) ||
                double.IsNaN(d.N[i]) || double.IsInfinity(d.N[i]) || double.IsNaN(d.V[i]) || double.IsInfinity(d.V[i]) || (i > 0 && d.x[i] < d.x[i - 1]))
                throw new InvalidOperationException(name + ": muestras invalidas.");
                foreach (int node in new[] { 60, 63, 67, 70 })
        {
            var u = AnalysisMap.Desp(name, node);
            if (u == null || u.Length != 6 || !AnalysisMap.StructCoords.ContainsKey(node.ToString()))
                throw new InvalidOperationException(name + ": faltan desplazamientos nodales.");
            foreach (double value in u)
                if (double.IsNaN(value) || double.IsInfinity(value))
                    throw new InvalidOperationException(name + ": desplazamiento invalido.");
        }
        var fractions = AnalysisMap.BeamFractionElems[185];
        int[] expectedNodes = { 60, 63, 67, 70 };
        if (fractions.Count != 3) throw new InvalidOperationException("Subdivisiones incompatibles.");
        for (int i=0; i<3; i++)
            if (fractions[i].ni != expectedNodes[i] || fractions[i].nj != expectedNodes[i+1])
                throw new InvalidOperationException("Orden nodal incompatible.");
        var start = AnalysisMap.StructCoords["60"];
        var end = AnalysisMap.StructCoords["70"];
        if (Math.Abs(start[2]-end[2]) > 1e-8)
            throw new InvalidOperationException("Se requiere viga horizontal.");
        for(int i=1;i<3;i++)
        {
            var c = AnalysisMap.StructCoords[expectedNodes[i].ToString()];
            double t = (c[0]-start[0])/(end[0]-start[0]);
            if (t<=0 || t>=1 || Math.Abs(c[1]-start[1])>1e-8 || Math.Abs(c[2]-start[2])>1e-8)
                throw new InvalidOperationException("Nodos interiores incompatibles.");
        }
        var trib = AnalysisMap.Tributaria(185);
        if (trib == null || trib.area <= 0 || double.IsNaN(trib.area))
            throw new InvalidOperationException("Area tributaria no disponible.");
        return d;
    }

    public void SetBeam(Transform root) { beam = root; bodyRenderers = root.GetComponentsInChildren<Renderer>(); Refresh(); }
    public void ClearBeam() { if (drawing != null) Destroy(drawing); drawing = null; RestoreBody(true); beam = null; bodyRenderers = null; labels.Clear(); }
    double[] Values(AnalysisMap.DiagInfo d) { return mode == 1 ? d.M : mode == 2 ? d.V : d.N; }
    string Unit { get { return mode == 1 ? "kN·m" : "kN"; } }
    Vector3 Point(double x, double value)
    { return new Vector3((float)x, amplitude + 0.65f + (peak > 1e-10 ? (float)(value / peak) * amplitude : 0f), -0.45f); }

    void Refresh()
    {
        if (drawing != null) Destroy(drawing);
        drawing = null; labels.Clear(); RestoreBody(mode != 4);
        if (!ready || beam == null || mode == 0) return;
        var d = data[cases[caseIndex]];
        drawing = new GameObject("Resultados_" + cases[caseIndex]);
        drawing.transform.SetParent(beam, false);
        if (mode == 4) { DrawDisplacement(); return; }
        if (mode == 5) { DrawLoads(); return; }
        var values = Values(d);
        peak = 0; minIndex = maxIndex = 0;
        for (int i = 0; i < values.Length; i++)
        {
            peak = Math.Max(peak, Math.Abs(values[i]));
            if (values[i] < values[minIndex]) minIndex = i;
            if (values[i] > values[maxIndex]) maxIndex = i;
        }
        
        Line("Eje_cero", Point(0, 0), Point(d.L, 0), zeroMaterial, 0.016f);
        for (int i = 1; i < d.x.Length; i++)
        {
            Vector3 a = Point(d.x[i - 1], values[i - 1]), b = Point(d.x[i], values[i]);
            if (values[i - 1] * values[i] < 0)
            {
                float t = (float)(Math.Abs(values[i - 1]) / (Math.Abs(values[i - 1]) + Math.Abs(values[i])));
                Vector3 zero = Vector3.Lerp(a, b, t);
                Line("Curva", a, zero, values[i - 1] >= 0 ? positiveMaterial : negativeMaterial, 0.035f);
                Line("Curva", zero, b, values[i] >= 0 ? positiveMaterial : negativeMaterial, 0.035f);
            }
            else Line("Curva", a, b, (values[i - 1] + values[i]) >= 0 ? positiveMaterial : negativeMaterial, 0.035f);
            if (i % 3 == 0) Line("Ordenada", Point(d.x[i], 0), b, values[i] >= 0 ? positiveMaterial : negativeMaterial, 0.008f);
        }
        labels.Add(0);
        if (minIndex != 0 && minIndex != values.Length - 1) labels.Add(minIndex);
        if (maxIndex != 0 && maxIndex != values.Length - 1 && maxIndex != minIndex) labels.Add(maxIndex);
        labels.Add(values.Length - 1);
        foreach (int i in labels) Line("Valor", Point(d.x[i], 0), Point(d.x[i], values[i]), values[i] >= 0 ? positiveMaterial : negativeMaterial, 0.018f);
    }

    void RestoreBody(bool visible)
    {
        if (bodyRenderers != null)
            foreach (var renderer in bodyRenderers) if (renderer != null) renderer.enabled = visible;
    }

    Vector3 Coordinate(int node)
    {
        var c = AnalysisMap.StructCoords[node.ToString()];
        return new Vector3((float)c[0], (float)c[1], (float)c[2]);
    }

    void DrawDisplacement()
    {
        nodePoints = new Vector3[nodes.Length];
        displacements = new Vector3[nodes.Length];
        nodeMagnitudes = new double[nodes.Length];
        Vector3 origin = Coordinate(nodes[0]);
        Vector3 longitudinal = (Coordinate(nodes[3]) - origin).normalized;
        Vector3 transverse = Vector3.Cross(longitudinal, Vector3.forward).normalized;
        maxIndex = 0;
        for (int i = 0; i < nodes.Length; i++)
        {
            var u = AnalysisMap.Desp(cases[caseIndex], nodes[i]);
            Vector3 global = new Vector3((float)u[0], (float)u[1], (float)u[2]);
            nodePoints[i] = new Vector3(Vector3.Dot(Coordinate(nodes[i]) - origin, longitudinal), 0, 0);
            displacements[i] = new Vector3(Vector3.Dot(global, longitudinal), global.z, Vector3.Dot(global, transverse));
            nodeMagnitudes[i] = Math.Sqrt(u[0]*u[0]+u[1]*u[1]+u[2]*u[2])*1000;
            if (nodeMagnitudes[i] > nodeMagnitudes[maxIndex]) maxIndex = i;
            Line("Vector_desplazamiento", nodePoints[i], DeformedPoint(i), negativeMaterial, .02f);
            if (i > 0) Line("Desplazamiento_nodal", DeformedPoint(i-1), DeformedPoint(i), positiveMaterial, .05f);
        }
        // Original section: 0.8 m vertically and 0.6 m transversely.
        foreach (float y in new[] { -.4f, .4f })
            foreach (float z in new[] { -.3f, .3f })
                Line("Arista_original", new Vector3(0,y,z), new Vector3(10,y,z), zeroMaterial, .012f);
        foreach (float x in new[] { 0f, 10f })
        {
            Line("Seccion", new Vector3(x,-.4f,-.3f), new Vector3(x,.4f,-.3f), zeroMaterial,.012f);
            Line("Seccion", new Vector3(x,-.4f,.3f), new Vector3(x,.4f,.3f), zeroMaterial,.012f);
            Line("Seccion", new Vector3(x,-.4f,-.3f), new Vector3(x,-.4f,.3f), zeroMaterial,.012f);
            Line("Seccion", new Vector3(x,.4f,-.3f), new Vector3(x,.4f,.3f), zeroMaterial,.012f);
        }
        Line("Eje_original", Vector3.zero, new Vector3(10,0,0), zeroMaterial,.016f);
        labels.Add(0); if (maxIndex != 0 && maxIndex != 3) labels.Add(maxIndex); labels.Add(3);
    }

    Vector3 DeformedPoint(int i) { return nodePoints[i] + displacementGain * displacements[i]; }

    double GravityFactor()
    {
        return cases[caseIndex] == "G" ? 1 : cases[caseIndex] == "COMBO" ? AnalysisMap.Lambdas[0] : 0;
    }

    void Arrow(float x, float z, double force, float length, string name)
    {
        if (Math.Abs(force) < 1e-10) return;
        float tip = .5f, tail = tip + (force > 0 ? length : -length);
        Vector3 a = new Vector3(x,tail,z), b = new Vector3(x,tip,z);
        Material mat = z < 0 ? positiveMaterial : negativeMaterial;
        Line(name,a,b,mat,.025f);
        float direction = force > 0 ? 1 : -1;
        Line(name,b,b+new Vector3(-.13f,direction*.2f,0),mat,.025f);
        Line(name,b,b+new Vector3(.13f,direction*.2f,0),mat,.025f);
    }

    void DrawLoads()
    {
        distributedLoad = ElementDiagrams.Construir(185,cases[caseIndex],ElementDiagrams.PlanoVertical).q;
        for (int i=0;i<=10;i++) Arrow(i,-.45f,distributedLoad,.9f,"Carga_losa");
        nodalWeight = new double[4];
        // Beam-only self weight from OpenSees: gamma=2400*9.81/1000, A=0.6*0.8.
        // Complete nodal loads also contain contributions from adjoining elements.
        for (int i=1;i<4;i++)
        {
            double half = Vector3.Distance(Coordinate(nodes[i-1]),Coordinate(nodes[i]))*.6*.8*23.544*.5*GravityFactor();
            nodalWeight[i-1]+=half; nodalWeight[i]+=half;
        }
        double largest=0; foreach(double w in nodalWeight) largest=Math.Max(largest,Math.Abs(w));
        Vector3 origin=Coordinate(60), direction=(Coordinate(70)-origin).normalized;
        for(int i=0;i<4;i++)
            Arrow(Vector3.Dot(Coordinate(nodes[i])-origin,direction),.45f,nodalWeight[i],
                largest>0 ? .4f+.8f*(float)(Math.Abs(nodalWeight[i])/largest) : .4f,"Peso_propio_viga");
    }
    void Line(string name, Vector3 a, Vector3 b, Material mat, float width)
    {
        var go = new GameObject(name);
        go.transform.SetParent(drawing.transform, false);
        var line = go.AddComponent<LineRenderer>();
        line.useWorldSpace = false; line.positionCount = 2;
        line.SetPosition(0, a); line.SetPosition(1, b);
        line.widthMultiplier = width; line.numCapVertices = 3;
        line.sharedMaterial = mat;
    }

    public void DrawControls(GUIStyle label, GUIStyle button)
    {
        if (loadError != null) { GUILayout.Label(loadError, label); return; }
        if (!ready) { GUILayout.Label("Cargando diagramas OpenSees...", label); return; }
        GUILayout.Label("Area tributaria: " + Number(AnalysisMap.Tributaria(185).area) + " m²", label);
        int row = mode <= 2 ? mode : -1;
        int choice = GUILayout.Toolbar(row, new[] { "Ocultar", "Momento", "Corte" }, button, GUILayout.Height(44));
        int nextMode = choice != row ? choice : mode;
        int other = mode >= 3 ? mode - 3 : -1;
        int extra = GUILayout.Toolbar(other, new[] { "Axial", "Desplaz.", "Cargas" }, button, GUILayout.Height(44));
        if (extra != other) nextMode = extra + 3;
        int nextCase = GUILayout.Toolbar(caseIndex, cases, button, GUILayout.Height(40));
        bool changed = nextMode != mode || nextCase != caseIndex;
        mode = nextMode; caseIndex = nextCase;
        if (mode >= 1 && mode <= 3)
        {
            GUILayout.Label("Altura visual: " + amplitude.ToString("F2") + " m", label);
            float nextAmplitude = GUILayout.HorizontalSlider(amplitude, 0.3f, 2f, GUILayout.Height(24));
            if (Mathf.Abs(nextAmplitude - amplitude) > 0.005f) { amplitude = nextAmplitude; changed = true; }
        }
        if (mode == 4)
        {
            GUILayout.Label("Amplificacion: x" + displacementGain.ToString("F0"), label);
            float gain = GUILayout.HorizontalSlider(displacementGain, 1f, 600f, GUILayout.Height(24));
            if (Mathf.Abs(gain-displacementGain) > .1f) { displacementGain=gain; changed=true; }
        }
        if (changed) Refresh();
        if (mode == 0) return;
        if (cases[caseIndex] == "COMBO")
            GUILayout.Label("Factores: G="+Number(AnalysisMap.Lambdas[0])+" Q="+Number(AnalysisMap.Lambdas[1])+" EX="+Number(AnalysisMap.Lambdas[2])+" EY="+Number(AnalysisMap.Lambdas[3]),label);
        if (mode == 4)
        {
            GUILayout.Label("Desplazamientos | " + cases[caseIndex] + " | mm", label);
            GUILayout.Label("Maximo nodal: " + Number(nodeMagnitudes[maxIndex]) + " mm (nodo " + nodes[maxIndex] + ")",label);
            foreach (int i in new[] { 0, 3 })
            {
                var u=AnalysisMap.Desp(cases[caseIndex],nodes[i]);
                GUILayout.Label("Nodo "+nodes[i]+": UX="+Number(u[0]*1000)+" UY="+Number(u[1]*1000)+" UZ="+Number(u[2]*1000)+" mm",label);
            }
            GUILayout.Label("Blanco: viga original. Cian: eje desplazado.\nDesplazamientos nodales unidos con lineas rectas.\nAmplificacion visual; valores reales en mm.",label);
            return;
        }
        if (mode == 5)
        {
            GUILayout.Label("Cargas | "+cases[caseIndex]+"\nLosa: q="+Number(distributedLoad)+" kN/m\nTotal distribuido: "+Number(distributedLoad*10)+" kN",label);
            for(int i=0;i<4;i++) GUILayout.Label("PP viga en nodo "+nodes[i]+": "+Number(nodalWeight[i])+" kN",label);
            GUILayout.Label("Cian: losa. Naranja: aporte nodal del peso propio de esta viga.\nFlechas amplificadas. Positivo hacia abajo.",label);
            if(cases[caseIndex]=="EX" || cases[caseIndex]=="EY")
                GUILayout.Label("Sismo aplicado en diafragmas; sin carga vertical directa en esta viga.",label);
            return;
        }
        var d = data[cases[caseIndex]];
        var values = Values(d);
        GUILayout.Label((mode == 1 ? "Momento My" : mode == 2 ? "Corte Vz" : "Axial N") + " | " + cases[caseIndex] + " | " + Unit, label);
        GUILayout.Label("Inicio: " + Number(values[0]) + " | Final: " + Number(values[values.Length - 1]), label);
        GUILayout.Label("Min: " + Number(values[minIndex]) + " (x=" + Number(d.x[minIndex]) + " m)\nMax: " + Number(values[maxIndex]) + " (x=" + Number(d.x[maxIndex]) + " m)", label);
        GUILayout.Label("Cian: positivo arriba. Naranja: negativo abajo.\nAltura amplificada; longitud real de 10 m.", label);
        if (cases[caseIndex] == "COMBO" && AnalysisMap.Lambdas != null && AnalysisMap.Lambdas.Length >= 4)
            GUILayout.Label("COMBO: G=" + Number(AnalysisMap.Lambdas[0]) + " Q=" + Number(AnalysisMap.Lambdas[1]) + " EX=" + Number(AnalysisMap.Lambdas[2]) + " EY=" + Number(AnalysisMap.Lambdas[3]), label);
    }

    static string Number(double value) { return value.ToString("F2", CultureInfo.InvariantCulture); }

    void OnGUI()
    {
        if (!ready || mode == 0 || mode == 5 || drawing == null || !drawing.activeInHierarchy || arCamera == null) return;
        if (worldLabel == null) worldLabel = new GUIStyle(GUI.skin.box) { alignment = TextAnchor.MiddleCenter };
        var d = data[cases[caseIndex]];
        var values = Values(d);
        float factor = Screen.safeArea.width / 420f;
        worldLabel.fontSize = Mathf.RoundToInt(14 * factor);
        foreach (int i in labels)
        {
            Vector3 screen = arCamera.WorldToScreenPoint(beam.TransformPoint(mode == 4 ? DeformedPoint(i) : Point(d.x[i], values[i])));
            if (screen.z <= 0 || screen.x < 0 || screen.x > Screen.width || screen.y < 0 || screen.y > Screen.height) continue;
            float w = 145 * factor, h = 43 * factor;
            Rect rc = new Rect(screen.x - w / 2, Screen.height - screen.y - h - 8 * factor, w, h);
            if (rc.y < 175 * factor || rc.yMax > Screen.height - 370 * factor) continue;
            GUI.Label(rc, mode == 4 ? "Nodo "+nodes[i]+"\n"+Number(nodeMagnitudes[i])+" mm" : "x=" + Number(d.x[i]) + " m\n" + Number(values[i]) + " " + Unit, worldLabel);
        }
    }
}
