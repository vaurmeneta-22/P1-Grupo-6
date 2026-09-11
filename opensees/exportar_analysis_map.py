# -*- coding: utf-8 -*-
"""
Exporta a resultados/11_mapa_visor/analysis_map.js un mapa compacto para el
modo ANALISIS del visor edificio_3d.html.

Contiene (unidades internas del modelo: m, kN):
  * por cada caso (G, Q, EX, EY, COMBO): fuerzas globales por elemento y
    desplazamientos por nodo, tomados de resultados/01_casos_base/edificio_full_results*.json
  * el tag OpenSees de cada elemento (mismo orden que el array `elements`
    embebido en edificio_3d.html, ya verificado 1:1 con Edificio.json)
  * los tags de nodos extremo i/j de cada elemento (columnas/vigas: id del
    contrato; muros: tags 9000+ generados igual que en opensees_edificio_v2.py)
  * curvas P-M de capacidad (fiber) para columna 70x70 y muro 30x356

Genera un <script> JS plano (sin fetch) para que funcione abriendo el HTML
directamente desde el disco (file://).
"""
import json
import csv
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(REPO, "resultados", "01_casos_base")
CAPACIDAD = os.path.join(REPO, "resultados", "07_capacidad")
MOM_CURV_DIR = os.path.join(CAPACIDAD, "mom_curv")
PM_COLUMNAS = os.path.join(CAPACIDAD, "pm_columnas")
PM_MUROS = os.path.join(CAPACIDAD, "pm_muros")
SISMO_OUT = os.path.join(REPO, "resultados", "05_sismo")
OUT = os.path.join(REPO, "resultados", "11_mapa_visor", "analysis_map.js")

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


def exportar_sismo_csv(sismo):
    """Plano resultados/05_sismo/sismo_por_piso.csv (EX y EY por piso).
    Sobrescribe: solo queda la ultima corrida."""
    os.makedirs(SISMO_OUT, exist_ok=True)
    path = os.path.join(SISMO_OUT, "sismo_por_piso.csv")
    keys = ["piso", "z_m", "G_kN", "Q_kN", "W_kN", "masa_kg",
            "F_X_kN", "F_Y_kN", "CM_x_m", "CM_y_m",
            "ux_mm", "uy_mm", "Rz_rad"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["caso"] + keys)
        for c in ("EX", "EY"):
            for row in sismo.get(c, []):
                w.writerow([c] + [row.get(k, "") for k in keys])
    print(f"[CSV] {os.path.relpath(path, REPO)}")
    return path


def main():
    sys.stdout.reconfigure(encoding="utf-8")
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
    # Posiciones en planta del portico extremo (borde re-forzado 4x36+4x28):
    # x = {-45,-40,-30,-20} m x y = {0, 7.25, 16.15} m. El elemento columna se
    # marca con borde=True si su nodo inferior (ni) cae en esas coordenadas.
    def es_borde(ci, cj):
        for p in (ci, cj):
            if abs(p[0] - -45.0) < 1.0 or abs(p[0] - -40.0) < 1.0 or \
               abs(p[0] - -30.0) < 1.0 or abs(p[0] - -20.0) < 1.0:
                if abs(p[1] - 0.0) < 1.0 or abs(p[1] - 7.25) < 0.05 or \
                   abs(p[1] - 16.15) < 0.05:
                    return True
        return False

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
        ep = {"id": e["id"], "type": t, "section": e["section"],
              "ni": ni, "nj": nj}
        if t == "column" and e["section"] == "70x70":
            ci = conx["tag_coord"].get(ni)
            cj = conx["tag_coord"].get(nj)
            if ci is not None and cj is not None and es_borde(ci, cj):
                ep["borde"] = True
        if e["id"] == 70:
            ep["id70"] = True
        elements_out.append(ep)
        node_uses.setdefault(ni, 0)
        node_uses.setdefault(nj, 0)

    # ------------------------------------------------------------------
    # Cargar resultados por caso (fuerzas globales por tag y disp por nodo)
    # ------------------------------------------------------------------
    forces = {}    # case -> {tag: [6]}
    disp = {}      # case -> {tag: [6]}
    reacciones = {}     # case -> {tag: [6]}
    sismo = {}          # case (EX/EY) -> [por piso]
    meta_by_case = {}
    PISO_Z = {"Piso 1": 3.56, "Piso 2": 7.12, "Piso 3": 10.68,
              "Piso 4": 14.24, "Techo": 17.80}

    # Apoyos REALES del contrato (todos los definidos en Edificio.json):
    # unos estan a z=0 (subterraneo) y otros mas arriba en la zona X- donde el
    # terreno es mas alto (p.ej. 13-24 a z=356, apoyados via rigidLink 'bar').
    # Se excluyen las reacciones que NO son apoyos del contrato: nodos de
    # muros (tags 9000+), fundaciones enterradas y nodos auxiliares generados
    # por el FE (398+, etc.).
    # Ademas se descartan los apoyos del contrato que dan reaccion NULA en
    # todos los casos (manejados por rigidLink 'bar', toda la carga va al nodo
    # estructural): no soportan nada y ensucian la tabla.
    apoyos_suelo = sorted({t for t in (s["node"] for s in data["supports"])
                           if any(any(abs(x) > 1e-6 for x in rr)
                                  for c in CASES
                                  for rr in [load_result(c).get("reactions_kN", {})
                                             .get(str(t), [0.0] * 6)])})

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
        reacciones[c] = {tag: r["reactions_kN"].get(str(tag), [0.0] * 6)
                         for tag in apoyos_suelo}
        sfr = r.get("seismic_floor_results", {})
        if sfr:
            sismo[c] = []
            for piso, v in sfr.items():
                sigma = r.get("seismic_case", {}).get(piso, {})
                sismo[c].append({
                    "piso": piso,
                    "z_m": PISO_Z.get(piso, None),
                    "G_kN": round(sigma.get("G_floor", 0.0), 2),
                    "Q_kN": round(sigma.get("Q_floor", 0.0), 2),
                    "W_kN": round(v.get("W_sismico_kN", 0.0), 2),
                    "masa_kg": v.get("masa_kg", 0.0),
                    "F_X_kN": round(v.get("F_x_kN", 0.0), 2),
                    "F_Y_kN": round(v.get("F_y_kN", 0.0), 2),
                    "CM_x_m": v.get("CM_x_m", 0.0),
                    "CM_y_m": v.get("CM_y_m", 0.0),
                    "ux_mm": round((v.get("Ux_CM_m", 0.0) or 0.0) * 1000.0, 3),
                    "uy_mm": round((v.get("Uy_CM_m", 0.0) or 0.0) * 1000.0, 3),
                    "Rz_rad": v.get("Rz_rad", 0.0),
                })

    # ------------------------------------------------------------------
    # Curvas P-M de capacidad (fiber) para el overlay
    # ------------------------------------------------------------------
    def load_pm(fname):
        for d in (PM_COLUMNAS, PM_MUROS):
            p = os.path.join(d, fname)
            if os.path.exists(p):
                with open(p, encoding="utf-8") as f:
                    pm = json.load(f)
                return {"P": pm["P_kN_fiber"], "M": pm["M_kNm_fiber"],
                        "seccion": pm["seccion"]}
        raise FileNotFoundError(fname)

    # Todos los muros del contrato con curva P-M: se mapea por el `seccion`
    # del JSON (que coincide con el nombre de seccion del viewer). La clave
    # del archivo pm_muro_30x356.json es "muro_30x356" -> se expone como
    # "30x356" para que el viewer la encuentre.
    muros_capacidad = {}
    for fn in sorted(os.listdir(PM_MUROS)):
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
        "columna_borde": load_pm("pm_columna_borde_70x70.json"),
        "columna_id70": load_pm("pm_columna_id70.json"),
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

    # ------------------------------------------------------------------
    # Datos de consulta para el panel DATOS del visor
    # ------------------------------------------------------------------
    # Tributarias por viga (del caso G; iguales para todos los casos).
    tribu = {}
    rg = load_result("G")
    for vid, v in rg.get("tributary_by_viga", {}).items():
        tribu[int(vid)] = {
            "type": v.get("type"), "section": v.get("section"),
            "area_tributaria_m2": round(v.get("area_tributaria_m2", 0.0), 3),
            "W_G_kN": round(v.get("W_losa_G_kN", 0.0), 2),
            "p_G_kN_m": round(v.get("p_G_kN_m", 0.0), 3),
            "W_Q_kN": round(v.get("W_losa_Q_kN", 0.0), 2),
            "p_Q_kN_m": round(v.get("p_Q_kN_m", 0.0), 3),
            "aportes": v.get("aportes", []),
        }

    # Momento-curvatura de la columna 70x70.
    momcurv = None
    mc_path = os.path.join(MOM_CURV_DIR, "mom_curv_columna_70x70.json")
    if os.path.exists(mc_path):
        with open(mc_path, encoding="utf-8") as f:
            mc = json.load(f)
        momcurv = {"P_kN": mc.get("P_kN", 0.0),
                   "phi_1m": mc.get("phi_1m", []),
                   "M_kNm": mc.get("M_kNm", []),
                   "M_ult_kNm": mc.get("M_ult_kNm", None),
                   "n_ok": mc.get("n_ok", 0)}

    # P-M fibra + HA de columna y muro para superposicion.
    pm_ha = {}
    for sec, fn, d in (("70x70", "pm_columna_70x70.json", PM_COLUMNAS),
                        ("30x356", "pm_muro_30x356.json", PM_MUROS)):
        p_path = os.path.join(d, fn)
        if not os.path.exists(p_path):
            continue
        with open(p_path, encoding="utf-8") as f:
            p = json.load(f)
        pm_ha[sec] = {"P_fiber": p.get("P_kN_fiber", []),
                      "M_fiber": p.get("M_kNm_fiber", []),
                      "P_HA": p.get("P_kN_HA", []),
                      "M_HA": p.get("M_kNm_HA", []),
                      "alpha1": p.get("alpha1"), "beta1": p.get("beta1")}

    out = {
        "generado": "opensees/exportar_analysis_map.py",
        "casos": CASES,
        "units": {"length": "m", "force": "kN", "moment": "kN*m"},
        "meta": meta_by_case,
        "elements": elements_out,
        "forces": forces,
        "disp": disp,
        "reacciones": reacciones,
        "sismo": sismo,
        "tributarias": tribu,
        "momcurv": momcurv,
        "pm_ha": pm_ha,
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
    print(f"  reacciones: {len(reacciones.get('COMBO', {}))} | "
          f"sismo pisos: {len(sismo.get('EX', []))} | "
          f"tributarias: {len(tribu)} | periodico?: pm_ha={list(pm_ha)}")
    # sanity: desalineaciones con el viewer
    if len(elements_out) != len(data["elements"]):
        print("  [WARN] tamano no coincide con Edificio.json")
    exportar_sismo_csv(sismo)
    return 0


if __name__ == "__main__":
    sys.exit(main())