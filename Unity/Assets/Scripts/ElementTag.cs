using UnityEngine;

// Identifica un elemento estructural en la escena para el inspector por clic.
// Se anexa al collider del elemento (viga, columna, muro o losa).
public class ElementTag : MonoBehaviour
{
    public int elementId;
    public string type;
    public string section;
    public float bCm;
    public float hCm;
    public Vector3 start;
    public Vector3 end;
    public bool isDiaphragm;
    public string diaphName;
}