# -*- coding: utf-8 -*-
"""
Exporta a opensees/results/analysis_map.js un mapa compacto para el
modo ANALISIS del visor edificio_3d.html.

Contiene (unidades internas del modelo: m, kN):
  * por cada caso (G, Q, EX, EY, COMBO): fuerzas globales por elemento y
    desplazamientos por nodo, tomados de opensees/results/edificio_full_results*.json
  * el tag OpenSees de cada elemento (mismo orden que el array `elements`
    embebido en edificio_3d.html, ya verificado 1:1 con Edificio.json)
  * los tags de nodos extremo i/j de cada elemento (columnas/vigas: id del
    contrato; muros: tags 9000+ generados igual que en opensees_edificio_v2.py)
  * curvas P-M de capacidad (fiber) para columna 70x70 y muro 30x356

Genera un <script> JS plano (sin fetch) para que funcione abriendo el HTML
directamente desde el disco (file://).
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "opensees", "results")
FIGURES = os.path.join(REPO, "figures")
OUT = os.path.join(RESULTS, "analysis_map.js")

CM_TO_M = 0.01
CASES = ["G", "Q", "EX", "EY", "COMBO"]


def load_result(case):
    fname = {
        "G": "edificio_full_results.json",
        "Q": "edificio_full_results_Q.json",
        "EX": "edificio_full_results_EX.json",
        "EY": "edificio_full_results_EY.json",
        "COMBO": "edificio_full_results_COMBO.json",
    }[case]
    with open(os.path.join(RESULTS, fname), encoding="utf-8") as f:
        return json.load(f)


def main():
    with open(os.path.join(REPO, "Edificio.json"), encoding="utf-8") as f:
        data = json.load(f)

    nodes_json = data["nodes"]
    elements_json = data["elements"]
    json_nodes_by_id = {n["id"]: n for n in nodes_json}

    # ------------------------------------------------------------------
    # Replicar exactamente los tags OpenSees de los extremos de cada
    # elemento (misma logica que opensees_edificio_v2.py, sin ejecutar FI).
    # ------------------------------------------------------------------
    structural_refs = set()
    for e in elements_json:
        if e["type"] == "loza":
            continue
        if "node_i" in e:
            structural_refs.add(e["node_i"])
            structural_refs.add(e["node_j"])

    pos_key = {}          # (x,y,z redon.) -> tag
    for n in nodes_json:
        if n["id"] in structural_refs:
            x = n["x"] * CM_TO_M
            y = n["y"] * CM_TO_M
            z = n["z"] * CM_TO_M
            pos_key[(round(x, 4), round(y, 4), round(z, 4))] = n["id"]

    wall_elems = [e for e in elements_json if e["type"] == "wall"]
    next_wall_node = 9000

    def get_or_create_wall_node(cx_cm, cz_cm, cy_cm):
        nonlocal next_wall_node
        x = cx_cm * CM_TO_M
        y = cz_cm * CM_TO_M
        z = cy_cm * CM_TO_M
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key in pos_key:
            return pos_key[key]
        tag = next_wall_node
        next_wall_node += 1
        pos_key[key] = tag
        return tag

    wall_ends = {}
    for e in wall_elems:
        tagA = get_or_create_wall_node(e["xi"], e["zi"], e["yi"])
        tagB = get_or_create_wall_node(e["xj"], e["zj"], e["yj"])
        wall_ends[e["id"]] = (tagA, tagB)

    # ------------------------------------------------------------------
    # Por cada elemento: id, tipo, seccion y tags i/j en el MISMO ORDEN
    # que el array `elements` del viewer (Edificio.json y viewer 1:1).
    # ------------------------------------------------------------------
    elements_out = []
    node_uses = {}
    for e in elements_json:
        t = e["type"]
        if t == "loza":
            elements_out.append({"id": e["id"], "type": t,
                                 "section": e["section"], "ni": None, "nj": None})
            continue
        if t == "wall":
            ni, nj = wall_ends[e["id"]]
        else:
            ni, nj = e["node_i"], e["node_j"]
        elements_out.append({"id": e["id"], "type": t,
                             "section": e["section"], "ni": ni, "nj": nj})
        node_uses.setdefault(ni, 0)
        node_uses.setdefault(nj, 0)

    # ------------------------------------------------------------------
    # Cargar resultados por caso (fuerzas globales por tag y disp por nodo)
    # ------------------------------------------------------------------
    forces = {}    # case -> {tag: [6]}
    disp = {}      # case -> {tag: [6]}
    meta_by_case = {}
    for c in CASES:
        r = load_result(c)
        meta_by_case[c] = {
            "descripcion": r["summary"],
            "superposicion": r.get("superposition", None),
        }
        forces[c] = {int(tag): {"i": el.get("global_i"), "j": el.get("global_j")}
                     for tag, el in r["element_forces_global"].items()}
        disp[c] = {int(tag): d
                   for tag, d in r.get("displacements_m", {}).items()}

    # ------------------------------------------------------------------
    # Curvas P-M de capacidad (fiber) para el overlay
    # ------------------------------------------------------------------
    def load_pm(fname):
        with open(os.path.join(FIGURES, fname), encoding="utf-8") as f:
            pm = json.load(f)
        return {"P": pm["P_kN_fiber"], "M": pm["M_kNm_fiber"],
                "seccion": pm["seccion"]}

    # Todos los muros del contrato con curva P-M: se mapea por el `seccion`
    # del JSON (que coincide con el nombre de seccion del viewer). La clave
    # del archivo pm_muro_30x356.json es "muro_30x356" -> se expone como
    # "30x356" para que el viewer la encuentre.
    muros_capacidad = {}
    for fn in sorted(os.listdir(FIGURES)):
        if not fn.startswith("pm_") or not fn.endswith(".json"):
            continue
        if fn == "pm_columna_70x70.json":
            continue
        pm = load_pm(fn)
        clave = pm["seccion"]
        if clave == "muro_30x356":
            clave = "30x356"
        muros_capacidad[clave] = pm

    capacidad = {
        "columna": load_pm("pm_columna_70x70.json"),
        "muro": load_pm("pm_muro_30x356.json"),
        "muros": muros_capacidad,
    }

    out = {
        "generado": "opensees/exportar_analysis_map.py",
        "casos": CASES,
        "meta": meta_by_case,
        "elements": elements_out,
        "forces": forces,
        "disp": disp,
        "capacidad": capacidad,
        "nota": "Fuerzas globales en extremos i y j (kN, kN*m); disp en m. "
                "Orden de `elements` == edificio_3d.html.",
    }

    def js(py, indent="  "):
        return json.dumps(py, ensure_ascii=False, separators=(",", ":"))

    body = "const ANALYSIS_MAP = " + js(out) + ";\n"
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(body)

    n_forces = len(forces["COMBO"])
    print(f"OK: analysis_map.js ({len(body)/1024:.0f} KB)")
    print(f"  elements: {len(elements_out)} | fuerzas COMBO: {n_forces} "
          f"| disp EX nodos: {len(disp['EX'])}")
    # sanity: desalineaciones con el viewer
    if len(elements_out) != len(data["elements"]):
        print("  [WARN] tamano no coincide con Edificio.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())