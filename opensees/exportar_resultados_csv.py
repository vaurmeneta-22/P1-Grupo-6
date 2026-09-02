# -*- coding: utf-8 -*-
"""
Exporta los resultados del edificio completo a 3 CSV ordenados por columnas,
aptos para revision y correccion detallada en Excel/Sheets.

Enriquece cada fila con contexto geometrico/estructural derivado del
contrato Edificio.json:
  - coordenadas (cm) y piso  -> para ubicar nodos / elementos por posicion
  - tipo y seccion           -> para agrupar columnas, vigas, muros
  - nodos i/j y longitud     -> para revisar elementos

Salida (en results/):
  1. desplazamientos.csv  por nodo (mm y rad)
  2. reacciones.csv       por nodo de apoyo (kN y kN.m)
  3. fuerzas_elementos.csv por elemento en nodo i (kN y kN.m)
"""

import json
import os
import csv
import math

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results")
IN_JSON = os.path.join(RESULTS, "edificio_full_results.json")
# Contrato en el repo (fuente de geometria / piso / secciones)
REPO = os.path.dirname(HERE)
CONTRACT = os.path.join(REPO, "Edificio.json")

CM_TO_M = 0.01


def numeric_sort_keys(keys):
    def key(k):
        try:
            return int(k)
        except ValueError:
            return float("inf")
    return sorted(keys, key=key)


def build_node_geo(data):
    """Devuelve {tag: {x,y,z (cm), floor}} para todos los nodos del modelo:
    contrato estructural + nodos de muro (creados por el script de analisis)."""
    nodes_json = data["nodes"]
    elems = data["elements"]
    supports = data["supports"]

    support_tags = set(s["node"] for s in supports)
    structural_refs = set()
    for e in elems:
        if e["type"] == "loza":
            continue
        if "node_i" in e:
            structural_refs.add(e["node_i"])
            structural_refs.add(e["node_j"])

    geo = {}
    for n in nodes_json:
        nid = n["id"]
        if nid in structural_refs or nid in support_tags:
            geo[str(nid)] = {"x": n["x"], "y": n["y"], "z": n["z"],
                             "floor": n.get("floor", "")}

    # Nodos de muro (misma convencion que el script de analisis):
    # extremo wall (xi, yi=ALTURA, zi) -> nodo (x=xi, y=zi, z=yi)
    pos_key = {(round(g["x"], 4), round(g["y"], 4), round(g["z"], 4)): tag
               for tag, g in geo.items()}
    for e in elems:
        if e["type"] != "wall":
            continue
        for end in ("i", "j"):
            xcm = e["x" + end]
            zcm = e["z" + end]
            ycm = e["y" + end]
            key = (round(xcm, 4), round(zcm, 4), round(ycm, 4))
            if key in pos_key:
                tag = pos_key[key]
            else:
                tag = str(len(geo) + 9000)
                pos_key[key] = tag
            if tag not in geo:
                geo[tag] = {"x": xcm, "y": zcm, "z": ycm, "floor": ""}
    return geo


def floor_from_z(z_cm):
    if z_cm < 356:
        return "Subterraneo"
    if 356 <= z_cm < 712:
        return "Piso 1"
    if 712 <= z_cm < 1068:
        return "Piso 2"
    if 1068 <= z_cm < 1424:
        return "Piso 3"
    return "Piso 4"


def main():
    with open(IN_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(CONTRACT, "r", encoding="utf-8") as f:
        contract = json.load(f)

    geo = build_node_geo(contract)

    # ---------- 1. Desplazamientos ----------
    disp = data["displacements_m"]
    out1 = os.path.join(RESULTS, "desplazamientos.csv")
    with open(out1, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "piso", "x_cm", "y_cm", "z_cm",
                    "ux_mm", "uy_mm", "uz_mm", "u_planta_mm",
                    "rx_rad", "ry_rad", "rz_rad"])
        for nid in numeric_sort_keys(disp):
            v = disp[nid]
            g = geo.get(str(nid), {})
            fl = g.get("floor") or floor_from_z(g.get("z", 0))
            ux, uy, uz = v[0] * 1000, v[1] * 1000, v[2] * 1000
            uplanta = math.hypot(v[0], v[1]) * 1000
            w.writerow([
                nid, fl,
                round(g.get("x", ""), 2) if "x" in g else "",
                round(g.get("y", ""), 2) if "y" in g else "",
                round(g.get("z", ""), 2) if "z" in g else "",
                round(ux, 6), round(uy, 6), round(uz, 6), round(uplanta, 6),
                round(v[3], 12), round(v[4], 12), round(v[5], 12),
            ])
    print(f"[OK] {out1}  ({len(disp)} filas)")

    # ---------- 2. Reacciones ----------
    reac = data["reactions_kN"]
    out2 = os.path.join(RESULTS, "reacciones.csv")
    with open(out2, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "piso", "x_cm", "y_cm", "z_cm",
                    "Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"])
        for nid in numeric_sort_keys(reac):
            v = reac[nid]
            g = geo.get(str(nid), {})
            fl = g.get("floor") or floor_from_z(g.get("z", 0))
            w.writerow([
                nid, fl,
                round(g.get("x", ""), 2) if "x" in g else "",
                round(g.get("y", ""), 2) if "y" in g else "",
                round(g.get("z", ""), 2) if "z" in g else "",
                round(v[0], 6), round(v[1], 6), round(v[2], 6),
                round(v[3], 6), round(v[4], 6), round(v[5], 6),
            ])
    print(f"[OK] {out2}  ({len(reac)} filas)")

    # ---------- 3. Fuerzas en elementos (nodo i, global) ----------
    # Mapa id-elemento -> (tipo, nodos i/j, seccion, b, h reales del contrato)
    elem_map = {}
    for e in contract["elements"]:
        if e["type"] == "loza":
            continue
        nid = str(e["id"])
        dims = {"b": e.get("b"), "h": e.get("h")}
        if "node_i" in e:
            elem_map[nid] = {"type": e["type"], "i": e["node_i"], "j": e["node_j"],
                             "section": e.get("section", ""), **dims}
        else:  # wall: nodos creados por el script (misma convencion)
            def tag_at(pos):
                for t, g in geo.items():
                    if (round(g["x"], 4), round(g["y"], 4), round(g["z"], 4)) == pos:
                        return t
                return None
            pi = (round(e["xi"], 4), round(e["zi"], 4), round(e["yi"], 4))
            pj = (round(e["xj"], 4), round(e["zj"], 4), round(e["yj"], 4))
            elem_map[nid] = {"type": "wall",
                             "i": tag_at(pi), "j": tag_at(pj),
                             "section": e.get("section", ""), **dims}

    forces = data["element_forces_global"]
    out3 = os.path.join(RESULTS, "fuerzas_elementos.csv")
    with open(out3, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "tipo", "seccion", "b_cm", "h_cm", "A_m2",
                    "nodo_i", "nodo_j",
                    "xi_cm", "yi_cm", "zi_cm", "xj_cm", "yj_cm", "zj_cm", "L_m",
                    "Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"])
        for eid in numeric_sort_keys(forces):
            e = forces[eid]
            em = elem_map.get(str(eid), {})
            gi = geo.get(str(em.get("i")), {})
            gj = geo.get(str(em.get("j")), {})
            L = None
            if gi and gj:
                dx = (gj.get("x", 0) - gi.get("x", 0)) * CM_TO_M
                dy = (gj.get("y", 0) - gi.get("y", 0)) * CM_TO_M
                dz = (gj.get("z", 0) - gi.get("z", 0)) * CM_TO_M
                L = math.sqrt(dx * dx + dy * dy + dz * dz)
            b = em.get("b"); h = em.get("h")
            area = None
            if b is not None and h is not None:
                area = float(b) * float(h) * CM_TO_M * CM_TO_M
            fg = e["global_i"]
            w.writerow([
                eid, em.get("type", e["type"]), em.get("section", e.get("section", "")),
                b if b is not None else "", h if h is not None else "",
                round(area, 6) if area is not None else "",
                em.get("i", ""), em.get("j", ""),
                round(gi.get("x", ""), 2) if gi else "",
                round(gi.get("y", ""), 2) if gi else "",
                round(gi.get("z", ""), 2) if gi else "",
                round(gj.get("x", ""), 2) if gj else "",
                round(gj.get("y", ""), 2) if gj else "",
                round(gj.get("z", ""), 2) if gj else "",
                round(L, 4) if L else "",
                round(fg[0], 6), round(fg[1], 6), round(fg[2], 6),
                round(fg[3], 6), round(fg[4], 6), round(fg[5], 6),
            ])
    print(f"[OK] {out3}  ({len(forces)} filas)")

    print("\ndone.")


if __name__ == "__main__":
    main()