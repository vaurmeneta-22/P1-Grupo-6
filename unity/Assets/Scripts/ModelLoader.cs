using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// Carga y muestra el modelo estructural desde JSON.
/// </summary>
public class ModelLoader : MonoBehaviour
{
    [Header("Ruta al JSON del modelo")]
    public string modelJsonPath = "model.json";

    [Header("Prefabs")]
    public GameObject nodePrefab;
    public GameObject beamPrefab;
    public GameObject columnPrefab;

    private ModelData modelData;

    [System.Serializable]
    public class NodeData
    {
        public float x, y, z;
        public int[] fixity;
    }

    [System.Serializable]
    public class ElementData
    {
        public string type;
        public int[] nodes;
        public int section;
    }

    [System.Serializable]
    public class ModelData
    {
        public Dictionary<string, NodeData> nodes;
        public Dictionary<string, ElementData> elements;
    }

    void Start()
    {
        LoadModel();
    }

    void LoadModel()
    {
        string json = System.IO.File.ReadAllText(modelJsonPath);
        modelData = JsonUtility.FromJson<ModelData>(json);
        Debug.Log("Modelo cargado desde JSON");
    }

    public void CreateNodeObjects()
    {
        foreach (var kvp in modelData.nodes)
        {
            int id = int.Parse(kvp.Key);
            NodeData node = kvp.Value;
            Vector3 pos = new Vector3(node.x, node.y, node.z);

            GameObject obj = Instantiate(nodePrefab, pos, Quaternion.identity);
            obj.name = $"Node_{id}";
            obj.tag = "Node";
        }
    }

    public void CreateElementObjects()
    {
        foreach (var kvp in modelData.elements)
        {
            int id = int.Parse(kvp.Key);
            ElementData elem = kvp.Value;

            if (modelData.nodes.TryGetValue(elem.nodes[0].ToString(), out NodeData n1) &&
                modelData.nodes.TryGetValue(elem.nodes[1].ToString(), out NodeData n2))
            {
                Vector3 start = new Vector3(n1.x, n1.y, n1.z);
                Vector3 end = new Vector3(n2.x, n2.y, n2.z);

                GameObject prefab = elem.type == "beam" ? beamPrefab : columnPrefab;
                GameObject obj = Instantiate(prefab, start, Quaternion.identity);
                obj.name = $"Element_{id}";
                obj.tag = elem.type == "beam" ? "Beam" : "Column";

                // Orientar elemento
                Vector3 dir = end - start;
                obj.transform.rotation = Quaternion.LookRotation(dir);
                obj.transform.localScale = new Vector3(1, 1, dir.magnitude);
            }
        }
    }
}
