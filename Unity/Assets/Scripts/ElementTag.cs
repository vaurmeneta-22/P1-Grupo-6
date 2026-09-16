using UnityEngine;

// Identifica un elemento estructural en la escena para el inspector por clic.
// Se anexa al collider del elemento (viga, columna, muro o losa).
public class ElementTag : MonoBehaviour
{
    public int elementId;
    public string type;
    public string section;
    public string material;
    public float bCm;
    public float hCm;
    public int niNode;
    public int njNode;
    public bool supI;
    public bool supJ;
    public Vector3 start;
    public Vector3 end;
    // Coordenadas estructurales (metros, sistema del analisis, antes del espejo X)
    public float structX_I, structY_I, structZ_I;
    public float structX_J, structY_J, structZ_J;
    public string piso;
    public bool isDiaphragm;
    public string diaphName;
}