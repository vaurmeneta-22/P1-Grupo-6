# -*- coding: utf-8 -*-
"""
EDIFICIO COMPLETO - OpenSeesPy (v2 - carga de loza por areas tributarias)
Grupo 6 - P1 Laboratorio Estructural Digital
====================================================

Lee el contrato Edificio.json (cm) y arma el modelo global del edificio real:
  - Columnas, vigas (beam_x / beam_y) y muros equivalentes
  - Apoyos fijos + diafragma rigido por piso (AGENTS.md)
  - Carga G = PESO PROPIO de elementos estructurales (nodal) +
              PESO PROPIO DE LOSA transferido a las vigas por
              AREAS TRIBUTARIAS (metodo 45°).

Losas (reglas del enunciado):
  * NO se modelan con elementos finitos (prohibido).
  * Su carga se transfiere a las vigas de borde por areas tributarias
    (ver areas_tributarias.py), como carga lineal uniforme sobre la viga.

IMPORTANTE (v2):
  * La carga de TERMINACIONES (G) y SOBRECARGA (Q) y los casos
    EX/EY/superposicion quedan pendientes (proximas versiones).
  * La orientacion del eje fuerte de los muros es una SUPOSICION que debe
    validarse con la convencion del curso.
  * Las losas NO se modelan con elementos finitos (AGENTS.md).

Unidades internas (SI): metros, kN, kN·m. El contrato viene en centimetros.

Como correr:
    python opensees_edificio_v1.py

Salida: resultados en opensees/results/edificio_full_results.json
"""

import json
import os
import math

# Modulo local de areas tributarias (mismo directorio)
from areas_tributarias import cargas_para_vigas, cargar_contrato

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(REPO, "Edificio.json")
# Los resultados quedan en opensees/results/ (dentro del repo).
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
OUT_JSON = os.path.join(BASE, "edificio_full_results.json")

USE_DIAPHRAGM = True       # diafragma rigido por piso (AGENTS.md)
CM_TO_M = 0.01

# v2: opcion para retirar el parche numerico de apoyos artificiales de losa.
# True  -> se quitan (los nodos de losa se empotran; pendiente estabilizar)
# False -> se mantienen los apoyos del v1 + se suma la carga de losa por
#          tributarias (recomendado: convergencia asegurada, resultado usable)
REMOVE_FLOATING_SUPPORTS = True

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
    json_nodes_by_id = {n["id"]: n for n in nodes_json}
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
    # NODOS AISLADOS: apoyos del contrato que no conectan a NINGUN elemento.
    # No aportan rigidez ni carga; si se modelan quedan como DOF colgados y
    # rompen el analisis. => no se crean (ningun nodo debe quedar aislado).
    isolated_ids = {s_id for s_id in support_tags if s_id not in structural_refs}
    for n in nodes_json:
        nid = n["id"]
        if nid in structural_refs or (nid in support_tags and nid not in isolated_ids):
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
              f"(reticula de losas y apoyos aislados sin elemento)")

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
    # 7. APOYO VERTICAL DE LOSA (nodos sin columna/muro bajo)
    #    La retícula de vigas sin losa queda con nodos de borde/voladizo sin
    #    rigidez vertical. En el edificio real la LOSA los sostiene (diafragma
    #    en el plano + rigidez de placa). El enunciado prohibe modelar la losa
    #    con FE. Solucion v2: dar apoyo vertical (uz) a los nodos de piso que
    #    NO esten directamente apoyados por una columna o muro bajo ellos,
    #    representando el sostén vertical que aporta la losa.
    # ------------------------------------------------------------------
    # ------------------------------------------------------------------
    # 7. SOPORTE DE LOS NODOS DE LOSA/RETICULA SIN COLUMNA
    #    Dos capas, igual que v1 (converge) pero tratando TODOS los pisos igual:
    #    a) 1 apoyo vertical (0,0,1,1,1,0) por componente conectado SIN fundacion
    #       (solo el maestro; los demas quedan como esclavos del diafragma).
    #    b) apoyo vertical uniforme (0,0,1,1,1,0) a TODOS los nodos de piso
    #       (z>356) sin columna directamente abajo ni dentro de un muro.
    #       Asi el nodo 76 (voladizo borde x=-2500) recibe EXACTAMENTE el mismo
    #       tratamiento que 43/109 (que pertenecen a micro-componentes sin
    #       fundacion). Resultado: 43=76=109 (Regla: ningun nodo aislado).
    # ------------------------------------------------------------------
    # (a) estabilizacion de componentes conectados SIN nodo de fundacion.
    #     Se aplica un SUELO VERTICAL MINIMO (uz + rx, ry) en el master de cada
    #     componente flotante. Se probo restringir SOLO uz (0,0,1,0,0,0): deja un
    #     mecanismo de giro fuera del plano y la matriz es singular (analyze -3),
    #     por lo que rx, ry son DOF estrictamente necesarios. rx/ry generan PAR
    #     (Mx, My), NO reaccion lateral (Fx, Fy); los dof laterales (ux, uy) y rz
    #     los condiciona el diafragma rigido del piso. Este es el conjunto minimo
    #     que converge sin aportar Fx/Fy en los apoyos auxiliares.
    adj = {}
    def add_edge(a, b):
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    for mt in elem_meta.values():
        ni, nj = mt["nodes"]
        add_edge(ni, nj)
    seen = set()
    components = []
    for start in sorted(adj):
        if start in seen:
            continue
        comp = []
        st = [start]
        while st:
            nn = st.pop()
            if nn in seen:
                continue
            seen.add(nn)
            comp.append(nn)
            st.extend(adj[nn])
        components.append(comp)
    incidence = {a: len(v) for a, v in adj.items()}

    floating_supports = []
    for comp in components:
        if any(t in support_tags for t in comp):
            continue
        master = max(comp, key=lambda t: incidence.get(t, 0))
        # Suelo vertical minimo: uz + rx, ry. Solo uz deja mecanismo de giro fuera
        # del plano (matriz singular -> analyze -3, verificado). rx/ry producen PAR,
        # NO reaccion lateral; los dof laterales (ux,uy) y rz los condiciona el
        # diafragma. Este es el conjunto minimo que converge y no aporta Fx/Fy.
        ops.fix(master, 0, 0, 1, 1, 1, 0)
        floating_supports.append(master)
    floating_supports = sorted(set(floating_supports))

    # (b) apoyo vertical uniforme a nodos de piso sin columna/muro
    col_tops = {}
    for e in elements:
        if e["type"] == "column":
            nn_i = json_nodes_by_id.get(e["node_i"])
            nn_j = json_nodes_by_id.get(e["node_j"])
            if nn_i and nn_j:
                if nn_i["z"] > nn_j["z"]:
                    top_n, bot_n = nn_i, nn_j
                else:
                    top_n, bot_n = nn_j, nn_i
                col_tops.setdefault(round(top_n["z"]), set()).add(
                    (round(top_n["x"], 1), round(top_n["y"], 1)))

    wall_rects = []
    for e in elements:
        if e["type"] == "wall":
            wall_rects.append((min(e["xi"], e["xj"]), max(e["xi"], e["xj"]),
                               min(e["zi"], e["zj"]), max(e["zi"], e["zj"]),
                               e["yi"], e["yj"]))
    def muro_cubre(x_cm, y_cm, z_cm):
        for (xmin, xmax, ymin, ymax, yi, yj) in wall_rects:
            if yi - 0.1 <= z_cm <= yj + 0.1 and \
               xmin - 0.1 <= x_cm <= xmax + 0.1 and \
               ymin - 0.1 <= y_cm <= ymax + 0.1:
                return True
        return False

    piso_vertical = []
    n_losa = 0
    for (rx, ry, rz), tag in pos_key.items():
        x_cm, y_cm, z_cm = rx / CM_TO_M, ry / CM_TO_M, rz / CM_TO_M
        if z_cm < 356.0:         # subterraneo: lo maneja (a)/columnas/muros
            continue
        if tag in support_tags:
            continue
        prev = [p for p in sorted(col_tops.keys()) if p < z_cm - 0.1]
        has_col = False
        if prev:
            p = max(prev)
            has_col = (round(x_cm, 1), round(y_cm, 1)) in col_tops.get(p, set())
        if has_col:
            continue               # tiene columna bajo
        if muro_cubre(x_cm, y_cm, z_cm):
            continue               # dentro de un muro
        try:
            # Suelo vertical: uz + minimo rx,ry. Verificado: solo uz deja el
            # mecanismo de giro fuera del plano (matriz singular, analyze -3);
            # rx/ry son los DOF que quitan ese modo y generan PAR, no reaccion
            # lateral. ux/uy/rz los condiciona el diafragma del piso.
            ops.fix(tag, 0, 0, 1, 1, 1, 0)
            piso_vertical.append(tag)
            n_losa += 1
        except Exception:
            pass                   # ya apoyado (master de (a), etc.)
    piso_vertical = sorted(set(piso_vertical))

    if floating_supports or piso_vertical:
        print(f"  Soporte vertical: {len(floating_supports)} masters de componentes "
              f"+ {n_losa} nodos de piso sin columna (43=76=109)")

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
            # excluir del diafragma: solo apoyos reales (fijos completos).
            # los nodos con apoyo vertical (0,0,1,1,1,0) quedan como esclavos,
            # uniendo ux/uy/rz al master (igual que v1).
            excl = set(support_tags)
            candidates = [t for t in tags if t not in excl]
            if not candidates:
                print(f"  [DIAFRAGMA] {fl:12s} z={z:6.2f} m: sin candidatos")
                continue
            master = max(candidates, key=lambda t: incidence.get(t, 0))
            slaves = [t for t in tags if t != master and t not in excl]
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

    print(f"  Peso propio (elementos estructurales): {total_W:.2f} kN")

    # ------------------------------------------------------------------
    # 9b. CARGA DE LOSA por AREAS TRIBUTARIAS (metodo 45°)
    #      La carga de cada loza (solo PESO PROPIO por ahora, gamma*t) se
    #      transfiere como carga uniforme sobre las vigas de borde.
    # ------------------------------------------------------------------
    cargas_losa = cargas_para_vigas(JSON_PATH, {n["id"]: n for n in nodes_json})
    total_losa = 0.0
    n_viga_cargada = 0
    for tag, meta in elem_meta.items():
        if meta["type"] not in ("beam_x", "beam_y"):
            continue
        p = cargas_losa.get(tag, {}).get("p", 0.0)
        if p <= 0:
            continue
        i, j = meta["nodes"]
        xi, yi, zi = node_xyz(i)
        xj, yj, zj = node_xyz(j)
        L = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2 + (zj - zi) ** 2)
        # carga lineal uniforme transversal en -z global (gravedad)
        ops.eleLoad("-ele", tag, "-type", "beamUniform", 0.0, -p)
        total_losa += p * L
        n_viga_cargada += 1

    total_W += total_losa
    print(f"  Carga de losa (areas tributarias)  : {total_losa:.2f} kN  "
          f"({n_viga_cargada} vigas)")
    print(f"  CARGA G TOTAL                    : {total_W:.2f} kN")

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
    in_model = set(ops.getNodeTags())
    all_support_tags = sorted(
        (set(support_tags) | set(floating_supports) | set(piso_vertical)) &
        in_model)
    for tag in all_support_tags:
        r = ops.nodeReaction(tag)
        Rx += r[0]; Ry += r[1]; Rz += r[2]

    err = abs((total_W - Rz) / total_W) if total_W else 0.0
    print("-" * 70)
    print("VERIFICACION DE EQUILIBRIO")
    print(f"  Carga aplicada (G = peso propio + losa) : {total_W:12.3f} kN")
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
            "loads": {
                "self_weight_kN": round(total_W - total_losa, 4),
                "losa_tributaria_kN": round(total_losa, 4),
                "Carga_G_total_kN": round(total_W, 4),
            },
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
    print("  Carga G = peso propio estructural + peso propio de losa (tributarias).")
    print("  Pendiente: terminaciones G, sobrecarga Q, casos EX/EY + superposicion,")
    print("  y validar eje fuerte de muros.")


if __name__ == "__main__":
    main()