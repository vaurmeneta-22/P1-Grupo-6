using UnityEngine;

public class CameraController : MonoBehaviour
{
    public Transform target;
    public float distance = 20f;
    public float rotationSpeed = 3f;
    public float panSpeed = 0.02f;
    public float zoomSpeed = 1f;
    public float minDistance = 2f;
    public float maxDistance = 200f;

    [Header("Encuadre inicial al cargar el modelo")]
    public float initialDistance = 60f;
    public float initialRotX = 30f;
    public float initialRotY = -30f;

    private float rotX = 30f;
    private float rotY = -30f;
    private Vector3 panOffset = Vector3.zero;

    // La camara orbital apunta al centro real del modelo. La llama EdificioLoader
    // desde su propio Start(), de forma que el encuadre no depende del orden de
    // ejecucion de los Start() entre ambos scripts.
    public void TargetModelCenter(Vector3 center)
    {
        if (target == null)
        {
            target = new GameObject("CameraTarget").transform;
        }
        target.position = center;
        panOffset = Vector3.zero;
        rotX = initialRotX;
        rotY = initialRotY;
        distance = Mathf.Clamp(initialDistance, minDistance, maxDistance);
        UpdatePosition();
    }

    // Recuadra la camara sobre un volumen (por ejemplo la deformada), manteniendo
    // la orientacion actual del usuario (rotX/rotY) si ya navego.
    public void FrameBounds(Bounds b)
    {
        if (target == null)
        {
            target = new GameObject("CameraTarget").transform;
        }
        float r = b.extents.magnitude;
        if (r < 0.01f) r = 1f;
        target.position = b.center;
        panOffset = Vector3.zero;
        Camera cam = GetComponent<Camera>();
        float fov = cam != null ? cam.fieldOfView : 60f;
        float dist = r / Mathf.Tan(fov * 0.5f * Mathf.Deg2Rad) * 1.4f;
        distance = Mathf.Clamp(dist, minDistance, maxDistance);
        UpdatePosition();
    }

    void Start()
    {
        if (target == null)
        {
            target = new GameObject("CameraTarget").transform;
            target.position = new Vector3(25f, 9f, 8f);

            // Solo aqui (sin EdificioLoader) se sincroniza con la posicion inicial.
            Vector3 toTarget = target.position - transform.position;
            distance = Mathf.Clamp(toTarget.magnitude, minDistance, maxDistance);
            if (toTarget.sqrMagnitude > 0.0001f)
            {
                Vector3 dir = toTarget.normalized;
                rotX = Mathf.Asin(Mathf.Clamp(dir.y, -1f, 1f)) * Mathf.Rad2Deg;
                rotY = -Mathf.Atan2(dir.x, -dir.z) * Mathf.Rad2Deg;
            }
            UpdatePosition();
        }
    }

    // True mientras se rota/arrastra/zoom con el raton: el hover del visor se
    // desactiva para no resaltar elementos mientras se navega (como el HTML).
    public bool Busy
    {
        get { return Input.GetMouseButton(0) || Input.GetMouseButton(1) ||
                     Mathf.Abs(Input.GetAxis("Mouse ScrollWheel")) > 0.001f; }
    }

    void Update()
    {
        if (Input.GetMouseButton(0))
        {
            rotY += Input.GetAxis("Mouse X") * rotationSpeed;
            rotX -= Input.GetAxis("Mouse Y") * rotationSpeed;
            rotX = Mathf.Clamp(rotX, -89f, 89f);
            UpdatePosition();
        }

        if (Input.GetMouseButton(1))
        {
            Vector3 right = transform.right;
            Vector3 up = transform.up;
            panOffset -= right * Input.GetAxis("Mouse X") * panSpeed * distance;
            panOffset += up * Input.GetAxis("Mouse Y") * panSpeed * distance;
            UpdatePosition();
        }

        float scroll = Input.GetAxis("Mouse ScrollWheel");
        if (Mathf.Abs(scroll) > 0.001f)
        {
            distance -= scroll * zoomSpeed * distance;
            distance = Mathf.Clamp(distance, minDistance, maxDistance);
            UpdatePosition();
        }
    }

    void UpdatePosition()
    {
        Quaternion rotation = Quaternion.Euler(rotX, rotY, 0);
        Vector3 position = target.position + panOffset + rotation * new Vector3(0, 0, -distance);
        transform.position = position;
        transform.LookAt(target.position + panOffset);
    }
}