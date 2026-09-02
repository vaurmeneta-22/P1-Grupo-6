# -*- coding: utf-8 -*-
"""
EDIFICIO COMPLETO - OpenSeesPy (v1 - version de PRUEBA)
Grupo 6 - P1 Laboratorio Estructural Digital
====================================================

Lee el contrato Edificio.json (cm) y arma el modelo global del edificio real:
  - 536 nodos contractuales
  - Columnas 70x70, vigas (beam_x / beam_y) y muros equivalentes
  - 64 apoyos fijos
  - Diafragma rigido por piso (AGENTS.md)
  - Carga G inicial = PESO PROPIO propio de los elementos estructurales

IMPORTANTE (v1):
  * La carga de LOSA + TERMINACIONES (q_G) via areas tributarias NO esta
    implementada aun; eso es el paso siguiente (Semana 2/3).
  * La orientacion del eje fuerte de los muros es una SUPOSICION (misma
    convencion de columnas) que debe validarse con la convencion del curso
    (AGENTS.md: no delegar ejes locales). Se imprime un WARNING.
  * Las losas NO se modelan con elementos finitos (AGENTS.md).

Unidades internas (SI): metros, kN, kN·m. El contrato viene en centimetros.

Como correr:
    python opensees_edificio_v1.py

Salida: resultados en opensees/results/edificio_full_results.json
"""

import json
import os
import math

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
REPO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "P1-Grupo-6",
)
JSON_PATH = os.path.join(REPO, "Edificio.json")
# Los resultados quedan en la carpeta personal/ (fuera del repo), hasta decidir
# que hacer con ellos. El JSON de entrada se lee del repo (contrato).
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
OUT_JSON = os.path.join(BASE, "edificio_full_results.json")

USE_DIAPHRAGM = True       # diafragma rigido por piso (AGENTS.md)
CM_TO_M = 0.01

# Material (materials.json): f'c = 25 MPa, E = 25000 MPa, densidad = 2400 kg/m3
E_CONC = 25.0e6            # kN/m2 (25 GPa)
NU = 0.2
G_CONC = E_CONC / (2.0 * (1.0 + NU))
GAMMA_CONC = 2400.0 * 9.81 / 1000.0   # kN/m3 = 23.544


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def floor_of(z_cm):
    """Asigna piso por altura, igual convencion que html_to_json.py."""
    if 0 <= z_cm < 356:
        return "Subterraneo"
    if 356 <= z_cm < 712:
        return "Piso 1"
    if 712 <= z_cm < 1068:
        return "Piso 2"
    if 1068 <= z_cm < 1424:
        return "Piso 3"
    if 1424 <= z_cm < 1780:
        return "Piso 4"
    return "Piso 4" if z_cm >= 1780 else "Subterraneo"


def sec_wall_from_name(name, b, h):
    """Para muros: (b=espesor, h=largo en planta). Retorna (A, Iy, Iz, J).
    SUPOSICION: eje fuerte = flexión en el plano del muro (Iy sobre largo),
    Igual que la convención 'equivalent wall' del benchmark. PENDIENTE validar.
    """
    t = min(b, h)   # espesor
    L = max(b, h)   # largo en planta
    A = t * L
    Iy = t * L**3 / 12.0   # fuerte (en el plano del muro)
    Iz = L * t**3 / 12.0   # debil (fuera del plano)
    J = 0.208 * t * L**3
    return A, Iy, Iz, J


def sec_rect(b, h):
    """Seccion rectangular estandar (vigas/columnas). b,h en metros."""
    A = b * h
    Iy = b * h**3 / 12.0
    Iz = h * b**3 / 12.0
    J = 0.208 * b * h**3
    return A, Iy, Iz, J


def main():
    data = load_json(JSON_PATH)

    nodes_json = data["nodes"]
    elements = [e for e in data["elements"]]
    supports = data["supports"]

    # ------------------------------------------------------------------
    # 0. Chequeos de integridad
    # ------------------------------------------------------------------
    n_column = sum(1 for e in elements if e["type"] == "column")
    n_bx = sum(1 for e in elements if e["type"] == "beam_x")
    n_by = sum(1 for e in elements if e["type"] == "beam_y")
    n_wall = sum(1 for e in elements if e["type"] == "wall")
    n_loza = sum(1 for e in elements if e["type"] == "loza")
    print("=" * 70)
    print("EDIFICIO COMPLETO - OpenSeesPy (v1 - prueba)")
    print("=" * 70)
    print(f"  Nodos contrato : {len(nodes_json)}")
    print(f"  Elementos      : {len(elements)} (col={n_column}, bx={n_bx}, "
          f"by={n_by}, wall={n_wall}, loza={n_loza})")
    print(f"  Apoyos          : {len(supports)}")

    import openseespy.opensees as ops

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    # ------------------------------------------------------------------
    # 1. SOPORTES
    # ------------------------------------------------------------------
    support_tags = set(s["node"] for s in supports)
    print(f"  Soportes (fijos): {len(support_tags)}")

    # Nodos referenciados por elementos estructurales (col/viga).
    structural_refs = set()
    for e in elements:
        if e["type"] == "loza":
            continue
        if "node_i" in e:
            structural_refs.add(e["node_i"])
            structural_refs.add(e["node_j"])

    # ------------------------------------------------------------------
    # 2. NODOS del contrato (x,y,z en cm; z = altura). A metros.
    #    Solo se crean los nodos "estructurales": los que usan columnas/
    #    vigas o son apoyos. El resto (esquinas auxiliares de la retícula
    #    de losas) NO se modela: no tiene elemento ni rigidez (serian DOF
    #    singulares). Unity lee el contrato, no necesita esos nodos en el
    #    JSON de resultados.
    # ------------------------------------------------------------------
    nid_map = {}          # id JSON -> tag OpenSees
    pos_key = {}          # (x,y,z redon.) -> tag   (para muros reutilizar)
    for n in nodes_json:
        nid = n["id"]
        if nid in structural_refs or nid in support_tags:
            tag = nid
            x = n["x"] * CM_TO_M
            y = n["y"] * CM_TO_M
            z = n["z"] * CM_TO_M
            ops.node(tag, x, y, z)
            nid_map[nid] = tag
            pos_key[(round(x, 4), round(y, 4), round(z, 4))] = tag

    n_skipped = len(nodes_json) - len(nid_map)
    if n_skipped:
        print(f"  Nodos auxiliares omitidos      : {n_skipped} "
              f"(solo retícula de losas, sin elemento)")

    # ------------------------------------------------------------------
    # 3. NODOS de MUROS (no existen en el contrato; crear en extremos)
    #    Muro JSON: (xi, yi=ALTURA, zi) -> nodo (x=xi, y=zi, z=yi) en metros.
    # ------------------------------------------------------------------
    wall_elems = [e for e in elements if e["type"] == "wall"]
    WALL_TAG_START = 9000
    next_wall_node = WALL_TAG_START

    def get_or_create_wall_node(cx_cm, cz_cm, cy_cm):
        """cx_cm, cz_cm = plan (x, z del JSON wall); cy_cm = altura."""
        nonlocal next_wall_node
        x = cx_cm * CM_TO_M
        y = cz_cm * CM_TO_M
        z = cy_cm * CM_TO_M
        key = (round(x, 4), round(y, 4), round(z, 4))
        if key in pos_key:
            return pos_key[key]
        tag = next_wall_node
        next_wall_node += 1
        ops.node(tag, x, y, z)
        pos_key[key] = tag
        return tag

    wall_ends = {}        # elem id -> (tagA, tagB)
    for e in wall_elems:
        tagA = get_or_create_wall_node(e["xi"], e["zi"], e["yi"])
        tagB = get_or_create_wall_node(e["xj"], e["zj"], e["yj"])
        wall_ends[e["id"]] = (tagA, tagB)

    n_nodes_total = len(nodes_json) + (next_wall_node - WALL_TAG_START)
    print(f"  Nodos totales (contrato + muros): {n_nodes_total}")

    # FUNDACION: todo nodo (contrato o muro) en z=0 que no este en la lista
    # de apoyos queda empotrado; si no, el modelo tiene nodos flotantes
    # (U(i,i)=0 -> matriz singular).
    base_extra = []
    for (ax, ay, az), tag in pos_key.items():
        if az < 0.06 and tag not in support_tags:
            ops.fix(tag, 1, 1, 1, 1, 1, 1)
            base_extra.append(tag)
    if base_extra:
        support_tags |= set(base_extra)
        print(f"  Nodos de fundacion anadidos (empotrados): {len(base_extra)}")

    # ------------------------------------------------------------------
    # 4. TRANSFORMACIONES GEOMETRICAS
    #    T1: columnas y muros (vecxz = (1,0,0): local z = +X global)
    #    T2: vigas           (vecxz = (0,0,1): local z = +Z global)
    # ------------------------------------------------------------------
    ops.geomTransf("Linear", 1, 1, 0, 0)
    ops.geomTransf("Linear", 2, 0, 0, 1)

    # ------------------------------------------------------------------
    # 5. ELEMENTOS elasticBeamColumn (secciones calculadas inline)
    #    Columnas / vigas / muros. Las lozas NO se modelan (FE off).
    # ------------------------------------------------------------------
    elem_meta = {}        # tag -> dict con nodos, tipo, seccion
    incidence = {}        # node tag -> grado (para elegir maestro de diafragma)
    n_created = 0

    for e in elements:
        t = e["type"]
        if t == "loza":
            continue
        tag = e["id"]

        if t in ("column", "beam_x", "beam_y"):
            i = nid_map[e["node_i"]]
            j = nid_map[e["node_j"]]
        elif t == "wall":
            i, j = wall_ends[tag]
        else:
            continue

        transf = 1 if t in ("column", "wall") else 2
        b = e["b"] * CM_TO_M
        h = e["h"] * CM_TO_M
        if t == "wall":
            A, Iy, Iz, J = sec_wall_from_name(e.get("section", ""), b, h)
        else:
            A, Iy, Iz, J = sec_rect(b, h)

        ops.element(
            "elasticBeamColumn", tag, i, j,
            A, E_CONC, G_CONC, J, Iy, Iz, transf,
        )
        elem_meta[tag] = {"type": t, "nodes": (i, j), "section": e.get("section", ""),
                          "A": A, "Iy": Iy, "Iz": Iz, "J": J}
        incidence[i] = incidence.get(i, 0) + 1
        incidence[j] = incidence.get(j, 0) + 1
        n_created += 1

    print(f"  Elementos estructurales creados: {n_created} "
          f"(se omitieron {n_loza} lozas)")

    # ------------------------------------------------------------------
    # 7. COMPONENTES FLOTANTES
    #    Vigas de borde / tramos que en el edificio real descansan sobre la
    #    losa (que NO se modela con FE). Sin el apoyo vertical de la losa
    #    esos nodos quedan sin rigidez en uz -> modo de cuerpo rigido ->
    #    matriz singular. Solucion v1: apoyar verticalmente el nodo mas
    #    incidente de cada componente sin fundacion (el diafragma ya fija
    #    ux, uy, rz en el plano del piso).
    # ------------------------------------------------------------------
    adj = {}
    def add_edge(a, b):
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    for tag, meta in elem_meta.items():
        i, j = meta["nodes"]
        add_edge(i, j)

    # BFS: componentes conexos
    seen = set()
    components = []
    for start in sorted(adj):
        if start in seen:
            continue
        comp = []
        stack = [start]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            comp.append(n)
            stack.extend(adj[n])
        components.append(comp)

    fixed_nodes = set()
    n_float = 0
    for comp in components:
        if any(t in support_tags for t in comp):
            continue            # ya tiene camino a la fundacion
        master = max(comp, key=lambda t: incidence.get(t, 0))
        ops.fix(master, 0, 0, 1, 1, 1, 0)     # support vertical en el plano
        fixed_nodes.add(master)
        n_float += 1
    if n_float:
        print(f"  Componentes flotantes (apoyo vertical por losa): {n_float}")
        for master in sorted(fixed_nodes):
            z = ops.nodeCoord(master)[2]
            print(f"    master={master} z={z:.2f} m")

    # El apoyo "de losa" NO es fundacion, pero debe sumar en el equilibrio y
    # en el JSON. No se agrega a support_tags para no excluirlo del diafragma.
    floating_supports = sorted(fixed_nodes)

    # ------------------------------------------------------------------
    # 7. APOYOS FIJOS
    # ------------------------------------------------------------------
    for nid, dof in [(s["node"], s["DOF"]) for s in supports]:
        if nid in nid_map:
            tag = nid_map[nid]
            if dof and len(dof) == 6:
                ops.fix(tag, *dof)
            else:
                ops.fix(tag, 1, 1, 1, 1, 1, 1)

    # ------------------------------------------------------------------
    # 8. DIAFRAGMA RIGIDO POR PISO
    #    Maestro = nodo no-soporte con mayor grado de conexion en el piso.
    #    Esclavos = resto de nodos del piso (excepto soportes y maestro).
    # ------------------------------------------------------------------
    if USE_DIAPHRAGM:
        # agrupar por NIVEL EXACTO (misma z) -> el rigidDiaphragm exige
        # que maestro y esclavos esten en el mismo plano xy.
        levels = {}
        for tag in pos_key.values():
            z = ops.nodeCoord(tag)[2]          # metros (altura)
            levels.setdefault(round(z, 6), []).append(tag)

        for z, tags in sorted(levels.items()):
            fl = floor_of(z / CM_TO_M)
            candidates = [t for t in tags if t not in support_tags]
            if not candidates:
                print(f"  [DIAFRAGMA] {fl:12s} z={z:6.2f} m: sin candidatos")
                continue
            master = max(candidates, key=lambda t: incidence.get(t, 0))
            slaves = [t for t in tags if t != master and t not in support_tags]
            if not slaves:
                continue
            # dirn=3 => plano 1-2 (ux, uy, rz) constrenido al maestro
            ops.rigidDiaphragm(3, master, *slaves)
            print(f"  [DIAFRAGMA] {fl:12s} z={z:6.2f} m: master={master} "
                  f"esclavos={len(slaves)}")
    else:
        print("  [DIAFRAGMA] desactivado (USE_DIAPHRAGM=False)")

    # ------------------------------------------------------------------
    # 9. CARGA G (v1) = PESO PROPIO DE ELEMENTOS (nodal, W/2 en cada extremo)
    #    W = gamma * A * L. Para probar armado y equilibrio del modelo.
    #    (La carga de losa+terminaciones se agrega en la proxima version.)
    # ------------------------------------------------------------------
    nodal = {}            # node tag -> (fx, fy, fz)
    total_W = 0.0

    def node_xyz(tag):
        return ops.nodeCoord(tag)[:3]

    for tag, meta in elem_meta.items():
        A = meta["A"]
        i, j = meta["nodes"]
        xi, yi, zi = node_xyz(i)
        xj, yj, zj = node_xyz(j)
        L = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2 + (zj - zi) ** 2)
        W = GAMMA_CONC * A * L
        total_W += W
        half = W / 2.0
        k = (round(xi, 6), round(yi, 6), round(zi, 6))
        nodal.setdefault(i, [0.0, 0.0, 0.0])[2] -= half
        nodal.setdefault(j, [0.0, 0.0, 0.0])[2] -= half

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for tag, (fx, fy, fz) in nodal.items():
        ops.load(tag, fx, fy, fz, 0.0, 0.0, 0.0)

    print(f"  Peso propio total: {total_W:.2f} kN  (sobre {len(nodal)} nodos)")

    # ------------------------------------------------------------------
    # 10. ANALISIS ESTATICO LINEAL
    # ------------------------------------------------------------------
    ops.system("BandSPD")
    ops.numberer("RCM")
    ops.constraints("Transformation")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")

    ok = ops.analyze(1)
    print(f"\n  analyze() -> {ok}")
    if ok != 0:
        print("  [ERROR] El analisis fallo. Revisar modelo (diafragma, "
              "muros, secciones).")
        return

    ops.reactions()

    # ------------------------------------------------------------------
    # 11. VERIFICACION DE EQUILIBRIO  (Sigma F + Sigma R = 0)
    # ------------------------------------------------------------------
    Rx = Ry = Rz = 0.0
    all_support_tags = sorted(set(support_tags) | set(floating_supports))
    for tag in all_support_tags:
        r = ops.nodeReaction(tag)
        Rx += r[0]; Ry += r[1]; Rz += r[2]

    err = abs((total_W - Rz) / total_W) if total_W else 0.0
    print("-" * 70)
    print("VERIFICACION DE EQUILIBRIO")
    print(f"  Carga aplicada (peso propio total) : {total_W:12.3f} kN")
    print(f"  Suma reacciones Rx / Ry / Rz       : {Rx:9.3f} / {Ry:9.3f} / {Rz:12.3f} kN")
    print(f"  |W - Rz| / W = {err:.3e}")
    ok_eq = err < 1e-6
    print(f"  {'[OK] EQUILIBRIO VERIFICADO' if ok_eq else '[ERROR] EQUILIBRIO NO VERIFICADO'}")

    # ------------------------------------------------------------------
    # 12. RESULTADOS -> JSON
    # ------------------------------------------------------------------
    disp = {}
    for tag in pos_key.values():        # contrato estructurales + nodos muro
        d = ops.nodeDisp(tag)
        disp[str(tag)] = [round(v, 10) for v in d]

    reactions = {}
    for tag in all_support_tags:
        r = ops.nodeReaction(tag)
        reactions[str(tag)] = [round(v, 10) for v in r]

    forces = {}
    for tag, meta in elem_meta.items():
        # eleForce global (primeros 6 = nodo i en global)
        fg = list(ops.eleForce(tag))[:6]
        forces[str(tag)] = {
            "type": meta["type"],
            "global_i": [round(v, 8) for v in fg],
            "section": meta["section"],
        }

    result = {
        "model": data["model"],
        "units_internal": {"length": "m", "force": "kN"},
        "summary": {
            "nodes_total": n_nodes_total,
            "elements_structural": n_created,
            "loads": {"self_weight_kN": round(total_W, 4)},
            "equilibrium_ok": bool(ok_eq),
            "equilibrium_error": round(err, 12),
        },
        "displacements_m": disp,
        "reactions_kN": reactions,
        "element_forces_global": forces,
    }

    os.makedirs(BASE, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Resultados exportados a: {OUT_JSON}")

    print("\n  NOTA: resultados internos en m y kN (no cm).")
    print("  Pendiente: cargas de losa+terminaciones por areas tributarias,")
    print("  casos Q / EX / EY, superposicion, y validar eje fuerte de muros.")


if __name__ == "__main__":
    main()