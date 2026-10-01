using UnityEngine;

// All distances are metres. Beam local X is longitudinal, Y vertical, Z width.
public static class ARBeamPlacementMath
{
    public const float Length = 10f;
    public const float Height = 0.8f;
    public const float Width = 0.6f;

    public static Vector3 HorizontalForward(Vector3 forward, Vector3 right)
    {
        Vector3 direction = Vector3.ProjectOnPlane(forward, Vector3.up);
        if (direction.sqrMagnitude < 0.01f)
            direction = Vector3.Cross(Vector3.ProjectOnPlane(right, Vector3.up), Vector3.up);
        return direction.sqrMagnitude > 0.0001f ? direction.normalized : Vector3.forward;
    }

    public static Quaternion BeamRotation(Vector3 forward, Vector3 right)
    {
        return Quaternion.LookRotation(HorizontalForward(forward, right), Vector3.up)
               * Quaternion.Euler(0f, -90f, 0f);
    }

    public static Vector3 CameraRelativeDelta(Vector3 forward, Vector3 right, float sideways, float away, float up)
    {
        Vector3 horizontal = HorizontalForward(forward, right);
        return Vector3.Cross(Vector3.up, horizontal) * sideways + horizontal * away + Vector3.up * up;
    }

    public static void RotateAboutCentre(Transform beamRoot, float degrees)
    {
        beamRoot.RotateAround(beamRoot.TransformPoint(new Vector3(Length * 0.5f, 0f, 0f)), Vector3.up, degrees);
    }
}
