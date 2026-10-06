using UnityEngine;
using UnityEngine.UI;

public class VRAction : MonoBehaviour
{
    public System.Action activate;
    public int movement = -1;
    public Image background;
    public Color normal = new Color(.12f,.21f,.29f,1);
    public void Hover(bool value) { if (background != null) background.color = value ? new Color(.05f,.56f,.67f,1) : normal; }
}
