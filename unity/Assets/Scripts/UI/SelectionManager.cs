using UnityEngine;

/// <summary>
/// Controla la selección de elementos del modelo.
/// </summary>
public class SelectionManager : MonoBehaviour
{
    public static SelectionManager Instance;

    public GameObject selectedObject;
    public string selectedTag;

    void Awake()
    {
        if (Instance == null) Instance = this;
    }

    void Update()
    {
        if (Input.GetMouseButtonDown(0))
        {
            Ray ray = Camera.main.ScreenPointToRay(Input.mousePosition);
            if (Physics.Raycast(ray, out RaycastHit hit))
            {
                SelectObject(hit.collider.gameObject);
            }
        }
    }

    void SelectObject(GameObject obj)
    {
        if (selectedObject != null)
        {
            // Deseleccionar anterior
            Renderer rend = selectedObject.GetComponent<Renderer>();
            if (rend != null) rend.material.color = Color.white;
        }

        selectedObject = obj;
        selectedTag = obj.tag;

        // Resaltar selección
        Renderer renderer = obj.GetComponent<Renderer>();
        if (renderer != null)
        {
            renderer.material.color = Color.yellow;
        }

        Debug.Log($"Seleccionado: {obj.name} (Tag: {obj.tag})");
    }
}
