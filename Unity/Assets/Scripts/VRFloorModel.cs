using System;
using System.Collections.Generic;
using UnityEngine;

// Same centimetres -> metres and X reflection as EdificioLoader. Navigation
// support comes from the union of existing floor slabs, never an invented plane.
public class VRFloorModel
{
    public const float BodyRadius = .22f;
    public EdificioData Data { get; private set; }
    public readonly List<Rect> Walkable = new List<Rect>();
    // Viewer-only covers for the audited joint at world X=-0.60/-0.45 to 0.
    public readonly List<Rect> JointPassages = new List<Rect>();
    public readonly HashSet<int> CeilingIds = new HashSet<int>();
    public float Ground { get; private set; }
    public float Base { get; private set; }
    public float Top { get; private set; }
    public int Number { get; private set; }
    public string Name { get { return "Piso " + Number; } }

    public VRFloorModel(EdificioData source, int number = 3)
    {
        if (source == null || source.nodes == null || source.elements == null || source.model == null || source.model.units == null || source.model.units.length != "cm")
            throw new InvalidOperationException("Contrato del edificio ausente o unidades distintas de cm.");
        if(number<1 || number>4) throw new ArgumentOutOfRangeException(nameof(number));
        Number=number;
        var floor = Array.Find(source.floors ?? new FloorInfo[0], f => f.name == Name);
        if (floor == null) throw new InvalidOperationException("El contrato no define " + Name + ".");
        Base = floor.elevation_base*.01f; Top = floor.elevation_top*.01f;
        foreach(var e in source.elements)
            if(e.type=="loza" && e.yi*.01f>=Top && e.yi*.01f<Top+1f)
                CeilingIds.Add(e.id);
        if(CeilingIds.Count==0) throw new InvalidOperationException(Name + " no tiene losas superiores para el techo.");
        var levels = new List<float>();
        foreach (var e in source.elements)
            if (e.type == "loza" && e.yi*.01f >= Base && e.yi*.01f < Base+1f)
            {
                levels.Add(e.yi*.01f + .08f + .045f*.5f);
                Walkable.Add(Rect.MinMaxRect(Mathf.Min(-e.xi, -e.xj)*.01f, Mathf.Min(e.zi,e.zj)*.01f,
                    Mathf.Max(-e.xi,-e.xj)*.01f, Mathf.Max(e.zi,e.zj)*.01f));
            }
        if (levels.Count == 0) throw new InvalidOperationException(Name + " no tiene losas para recorrer.");
        // Piso 4 has a 1.5 cm difference between slab groups. Keep the capsule
        // above the highest surface, without altering any slab's geometry.
        levels.Sort(); Ground = levels[levels.Count-1];
        foreach (float level in levels)
            if (Mathf.Abs(level-Ground) > .05f) throw new InvalidOperationException(Name + " tiene losas a distinto nivel: requiere un recorrido con desniveles.");
        foreach(var left in Walkable)
        {
            if(left.xMax < -.61f || left.xMax > -.44f || left.width < BodyRadius*2) continue;
            foreach(var right in Walkable)
            {
                if(Mathf.Abs(right.xMin)>.001f || right.width<BodyRadius*2) continue;
                float start=Mathf.Max(left.yMin,right.yMin), end=Mathf.Min(left.yMax,right.yMax);
                // Only where both sides have usable floor. The narrow strip
                // next to the stairs is deliberately excluded.
                if(end-start>BodyRadius*2)
                    JointPassages.Add(Rect.MinMaxRect(left.xMax,start,right.xMin,end));
            }
        }
        var nodes = new Dictionary<int,NodeData>();
        foreach (var n in source.nodes) nodes.Add(n.id,n);
        var elements = new List<ElementData>();
        var ids = new HashSet<int>();
        foreach (var e in source.elements)
        {
            float low, high;
            if (e.type == "loza" || e.type == "wall" || e.type.StartsWith("steel_"))
            { low = Mathf.Min(e.yi,e.yj)*.01f; high = Mathf.Max(e.yi,e.yj)*.01f; }
            else
            {
                NodeData a,b;
                if (!nodes.TryGetValue(e.node_i,out a) || !nodes.TryGetValue(e.node_j,out b)) continue;
                low = Mathf.Min(a.z,b.z)*.01f; high = Mathf.Max(a.z,b.z)*.01f;
            }
            bool horizontal = Mathf.Abs(high-low)<.01f;
            bool include = horizontal ? low >= Base-.01f && low <= Top+.5f : low >= Base-.01f && low < Top-.01f && high <= Top+.5f;
            // The next level's floor is this room's ceiling. Use actual slabs,
            // preserving their footprint and holes instead of filling a plane.
            if(e.type=="loza") include=(low>=Base && low<Base+1f) || CeilingIds.Contains(e.id);
            if (!include) continue;
            if (!ids.Add(e.id)) throw new InvalidOperationException("ID duplicado en VR: " + e.id);
            elements.Add(e);
        }
        Data = new EdificioData { model=source.model, floors=source.floors, sections=source.sections,
            nodes=source.nodes, elements=elements, supports=new SupportInfo[0] };
    }

    bool Contains(Vector2 p)
    {
        foreach (var r in Walkable) if (r.Contains(p)) return true;
        foreach (var r in JointPassages) if (r.Contains(p)) return true;
        return false;
    }

    public void RestrictJointPassagesToClearSpace(IEnumerable<Bounds> obstacles)
    {
        // Use the actual viewer colliders, including wall visual corrections.
        // Slabs and overhead beams do not obstruct the visitor's body height.
        foreach(var obstacle in obstacles)
        {
            if(obstacle.max.y<=Ground+.04f || obstacle.min.y>=Ground+1.72f) continue;
            for(int i=JointPassages.Count-1;i>=0;i--)
            {
                var part=JointPassages[i];
                if(obstacle.max.x+BodyRadius<=part.xMin || obstacle.min.x-BodyRadius>=part.xMax
                    || obstacle.max.z<=part.yMin || obstacle.min.z>=part.yMax) continue;
                JointPassages.RemoveAt(i);
                if(obstacle.min.z-part.yMin>BodyRadius*2)
                    JointPassages.Add(Rect.MinMaxRect(part.xMin,part.yMin,part.xMax,obstacle.min.z));
                if(part.yMax-obstacle.max.z>BodyRadius*2)
                    JointPassages.Add(Rect.MinMaxRect(part.xMin,obstacle.max.z,part.xMax,part.yMax));
            }
        }
    }

    public bool CanStand(Vector3 p)
    {
        var v = new Vector2(p.x,p.z);
        float r = BodyRadius;
        return Contains(v) && Contains(v+new Vector2(r,r)) && Contains(v+new Vector2(r,-r))
            && Contains(v+new Vector2(-r,r)) && Contains(v+new Vector2(-r,-r));
    }

    public static Vector3 Direction(Vector3 headForward, int arrow)
    {
        var forward = Vector3.ProjectOnPlane(headForward,Vector3.up);
        if (forward.sqrMagnitude < .01f) forward = Vector3.forward;
        forward.Normalize();
        var right = Vector3.Cross(Vector3.up,forward);
        return arrow == 0 ? forward : arrow == 1 ? -forward : arrow == 2 ? -right : right;
    }
}
