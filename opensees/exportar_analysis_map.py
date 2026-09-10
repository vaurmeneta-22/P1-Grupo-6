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
    # Tags de los extremos de cada elemento en el MISMO orden que el array
    # `elements` del viewer (Edificio.json y viewer 1:1). Para muros usa el
    # plan de conectividad compartido (conexiones.py): garantiza que los tags
    # de extremo (9000+) coincidan EXACTAMENTE con los del FE.
    # ------------------------------------------------------------------
    from conexiones import plan_conexiones
    conx = plan_conexiones(nodes_json, elements_json, data["supports"])
    wall_ends = conx["wall_ends"]
    frame_split = conx["frame_split"]

    # Fracciones reales de cada viga del contrato (reglas B y F): el viewer
    # debe dibujar la deformada como polilinea usando los nodos reales del FE,
    # no la viga recta entre sus 2 extremos (si no, el doblez del empalme
    # viga-viga no se ve y la secundaria parece "flotar").
    beam_fractions = {vid: [{"ni": ni, "nj": nj} for (_ft, ni, nj) in fr]
                      for vid, fr in frame_split.items()}
    node_coords = {str(tag): [x, y, z] for tag, (x, y, z) in conx["tag_coord"].items()}

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

    # Capacidad P-M de acero A240ES para tubos huecos cuadrados.
    FY_STEEL_KPA = 240_000.0   # kPa
    steel_sections = {
        "300x300x20": {"b": 0.30, "t": 0.02},
        "300x300x50": {"b": 0.30, "t": 0.05},
    }
    steel_cap = {}
    for sec_name, dims in steel_sections.items():
        b, t = dims["b"], dims["t"]
        a = b - 2.0 * t
        A = b * b - a * a
        Zp = (b ** 3 - a ** 3) / 6.0
        Py = FY_STEEL_KPA * A
        Mp = FY_STEEL_KPA * Zp
        npts = 21
        P_list, M_list = [], []
        for i in range(npts):
            frac = i / (npts - 1)
            P = -Py + 2.0 * Py * frac
            ratio = abs(P) / Py if Py > 0 else 0
            M = Mp * max(0.0, 1.0 - ratio ** 1.4)
            P_list.append(round(P, 2))
            M_list.append(round(M, 2))
        steel_cap[sec_name] = {
            "P": P_list, "M": M_list,
            "seccion": sec_name,
            "fy_MPa": 240, "A_m2": round(A, 6), "Zp_m3": round(Zp, 6),
        }
    capacidad["steel"] = steel_cap

    out = {
        "generado": "opensees/exportar_analysis_map.py",
        "casos": CASES,
        "units": {"length": "m", "force": "kN", "moment": "kN*m"},
        "meta": meta_by_case,
        "elements": elements_out,
        "forces": forces,
        "disp": disp,
        "beam_fractions": beam_fractions,
        "node_coords": node_coords,
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
    print(f"OK: analysis_map.js ({len(body)/1020:.0f} KB)")
    print(f"  elements: {len(elements_out)} | fuerzas COMBO: {n_forces} "
          f"| disp EX nodos: {len(disp['EX'])} "
          f"| vigas con fracciones: {len(beam_fractions)}")
    # sanity: desalineaciones con el viewer
    if len(elements_out) != len(data["elements"]):
        print("  [WARN] tamano no coincide con Edificio.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())