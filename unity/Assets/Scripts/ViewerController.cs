using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Controla la visibilidad de diferentes capas del modelo.
/// </summary>
public class ViewerController : MonoBehaviour
{
    [Header("Capas")]
    public bool showNodes = true;
    public bool showBeams = true;
    public bool showColumns = true;
    public bool showWalls = false;
    public bool showDiaphragms = false;
    public bool showSupports = true;
    public bool showAxes = false;
    public bool showIds = false;
    public bool showTributaryAreas = false;
    public bool showLoads = false;
    public bool showDeformation = false;
    public bool showDiagrams = false;
    public bool showPMDemand = false;
    public bool showPMCurves = false;

    void Update()
    {
        ToggleVisibility("Node", showNodes);
        ToggleVisibility("Beam", showBeams);
        ToggleVisibility("Column", showColumns);
        ToggleVisibility("Wall", showWalls);
        ToggleVisibility("Diaphragm", showDiaphragms);
        ToggleVisibility("Support", showSupports);
    }

    void ToggleVisibility(string tag, bool visible)
    {
        GameObject[] objects = GameObject.FindGameObjectsWithTag(tag);
        foreach (GameObject obj in objects)
        {
            obj.SetActive(visible);
        }
    }

    public void ToggleNodes() { showNodes = !showNodes; }
    public void ToggleBeams() { showBeams = !showBeams; }
    public void ToggleColumns() { showColumns = !showColumns; }
    public void ToggleWalls() { showWalls = !showWalls; }
    public void ToggleDiaphragms() { showDiaphragms = !showDiaphragms; }
    public void ToggleSupports() { showSupports = !showSupports; }
    public void ToggleAxes() { showAxes = !showAxes; }
    public void ToggleIds() { showIds = !showIds; }
    public void ToggleTributaryAreas() { showTributaryAreas = !showTributaryAreas; }
    public void ToggleLoads() { showLoads = !showLoads; }
    public void ToggleDeformation() { showDeformation = !showDeformation; }
    public void ToggleDiagrams() { showDiagrams = !showDiagrams; }
    public void TogglePMDemand() { showPMDemand = !showPMDemand; }
    public void TogglePMCurves() { showPMCurves = !showPMCurves; }
}
