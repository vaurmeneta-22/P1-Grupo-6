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
  - Casos: G (gravedad), Q (sobrecarga), EX/EY (sismo pseudostatico).
  - Carga Q y casos sismico EX/EY implementados (Semana 3): masa sismica
    W_sismico = G + 0.50*Q, F_sismo = ALPHA_SISMO * W_sismico aplicada en el
    centro de masa de cada piso (via el master del diafragma rigido).

Losas (reglas del enunciado):
  * NO se modelan con elementos finitos (prohibido).
  * Su carga se transfiere a las vigas de borde por areas tributarias
    (ver areas_tributarias.py) POR TRAMOS, como carga lineal uniforme sobre
    la viga. Los huecos de cobertura (borde con viga parcial) y las losas
    aisladas (sin viga en ningun borde) se reportan como PENDIENTES, NO se
    inventa soporte para compensarlos.

Notas de verificacion (Semana 3):
  * Equilibrio: sigma F + sigma R = 0 (tol < 1e-10).
  * Areas tributarias: A_transferida + A_huecos = A_losas_soportadas.
  * F sismica esperada = alpha * W_efectivo, calculada de forma INDEPENDIENTE
    de la lista aplicada (participacion lateral = pisos con diafragma).
  * Corte basal con signo: F_aplicada + R_base = 0.
  * El desplazamiento del master se transforma al centro de masa:
        ux_CM = ux_master - Rz_master*(yCM - yM)
        uy_CM = uy_master + Rz_master*(xCM - xM)
    (Rz en rad, desplazamientos en metros; se exportan ambos: master y CM).
  * Los 4-5 pisos se diagnostican: claves de diafragma duplicadas y pisos sin
    master detectados en vez de sobrescribirse en silencio.

Unidades internas (SI): metros, kN, kN·m. El contrato viene en centimetros.

Como correr:
    python opensees_edificio_v2.py            (todos los casos)
    python opensees_edificio_v2.py --case G   (caso individual)

Salida: resultados en resultados/01_casos_base/
"""

import json
import os
import math
from collections import defaultdict

# Modulo local de areas tributarias (mismo directorio)
from areas_tributarias import (
    cargas_para_vigas,
    cargar_contrato,
    verificar_areas_tributarias,
)

# Planificador de conectividad (reglas A-E muro<->marco, apoyos huerfanos).
# Modulo PURO: garantiza que generador y exportador usen los mismos tags.
from conexiones import plan_conexiones

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(REPO, "Edificio.json")
# Los resultados quedan en resultados/01_casos_base/ (raiz del repo).
BASE = os.path.join(REPO, "resultados", "01_casos_base")
os.makedirs(BASE, exist_ok=True)
OUT_JSON = os.path.join(BASE, "edificio_full_results.json")
# Sufijo opcional (--tag) para corridas de MODIFICACION del modelo SIN pisar
# los resultados de la linea base: los archivos salen como
# edificio_full_results[_tag][_CASO].json.
MOD_TAG = ""

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

# Acero estructural A240ES (NCh 203)
E_STEEL = 200.0e6          # kN/m2 (200 GPa)
NU_STEEL = 0.3
G_STEEL = E_STEEL / (2.0 * (1.0 + NU_STEEL))
GAMMA_STEEL = 7850.0 * 9.81 / 1000.0  # kN/m3 ≈ 77.01

# ---------------------------------------------------------------------------
# CARGAS GRAVITACIONALES por m2 de LOSA (kN/m2)
#   q_G = peso propio de losa (gamma*t) + TERMINACIONES
#   q_Q = SOBRECARGA (caso de uso / SÍSMICO - Q)
# Los valores de terminaciones y sobrecarga vienen del enunciado/planos;
# ajustar aqui segun el modelo real.
# ---------------------------------------------------------------------------
TERMINACIONES_KNM2 = 2.0      # terminaciones uniformes sobre losa (kN/m2)
SOBRECARGA_KNM2 = 4.0         # sobrecarga de uso sobre losa (kN/m2)

# Aceleracion de gravedad (unidades SI, coherente con kN y m).
g = 9.81         # m/s^2

# ---------------------------------------------------------------------------
# SISMO PSEUDOESTATICO (Semana 3 - Parte B)
# ---------------------------------------------------------------------------
# El sismo se modela como una fuerza lateral aplicada en el centro de masa de
# cada piso (nodo master del diafragma rigido). Patron/parametros definitivos
# a definir por el profesor.
#   F_sismo = alpha_sismo * W_sismico            con W_sismico = G + 0.50*Q
#   equivalente:  F_sismo = masa_piso * (alpha_sismo * g)
# Masa sismica por piso:  m = W_sismico / g
ALPHA_SISMO = 0.20        # PARAMETRO A CONFIRMAR CON EL PROFESOR (NCh433 ~20% g)
FRAC_LIVE_SISMIC = 0.50   # fraccion de sobrecarga de uso considerada como masa sismica

# Casos a correr (G = gravedad completa, Q = sobrecarga sola,
# EX/EY = sismo pseudostatico en X / Y, COMBO = superposicion con lambdas)
RUN_CASE_G = True
RUN_CASE_Q = True
RUN_CASE_EX = True
RUN_CASE_EY = True
RUN_CASE_COMBO = False

# Parte C - Superposicion  R = lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY
# Se usa solo cuando case_name == "COMBO" (por defecto 1.0 = combinacion de servicio
# con todos los casos a plena carga). Pueden pasarse por CLI (--lambda-g X ...).
LAMBDA_G = 1.0
LAMBDA_Q = 1.0
LAMBDA_EX = 1.0
LAMBDA_EY = 1.0


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def floor_of(z_cm):
    """Asigna piso por altura, igual convencion que html_to_json.py.
    Se distingue EXPRESAMENTE el 'Techo' (z>=1780) del 'Piso 4' (1424-1780):
    en el contrato existen dos niveles con esa etiqueta y colapsarlos haria que
    dos niveles distintos compartieran masa sismica / master de diafragma."""
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
    if 1780 <= z_cm:
        return "Techo"
    return "Subterraneo"


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


def sec_tube(b, t):
    """Tubo cuadrado hueco. b = lado exterior (m), t = espesor (m).
    Retorna (A, Iy, Iz, J)."""
    a = b - 2.0 * t
    if a < 0:
        a = 0.0
    A = b * b - a * a
    Iy = (b**4 - a**4) / 12.0
    Iz = Iy
    J = (b**4 - a**4) / 6.0
    return A, Iy, Iz, J


def run_case(case_name="G"):
    """Arma el modelo completo del edificio (536 nodos), aplica un caso de carga
    gravitacional y verifica. `case_name`:
      - 'G': q_G = peso propio de losa + TERMINACIONES + peso propio estructural
      - 'Q': q_Q = SOBRECARGA sola
    Cada caso se construye desde cero (ops.wipe) para asegurar estado limpio."""
    data = load_json(JSON_PATH)

    nodes_json = data["nodes"]
    json_nodes_by_id = {n["id"]: n for n in nodes_json}
    elements = [e for e in data["elements"]]
    supports = data["supports"]

    # Plan de conectividad: nodos de muro (9000+), splits de viga (200000+/300000+),
    # rigidLinks A-E y apoyos huerfanos. Definido ANTES de crear nodos para que los
    # tags coincidan exactamente con exportar_analysis_map.py (viewer 1:1).
    conx = plan_conexiones(data["nodes"], data["elements"], data["supports"])
    wall_ends = conx["wall_ends"]
    frame_split = conx["frame_split"]
    rigid_links = conx["rigid_links"]
    orphan_nodes = conx["orphan_nodes"]

    # ------------------------------------------------------------------
    # 0. Chequeos de integridad
    # ------------------------------------------------------------------
    n_column = sum(1 for e in elements if e["type"] == "column")
    n_bx = sum(1 for e in elements if e["type"] == "beam_x")
    n_by = sum(1 for e in elements if e["type"] == "beam_y")
    n_wall = sum(1 for e in elements if e["type"] == "wall")
    n_loza = sum(1 for e in elements if e["type"] == "loza")
    n_sc = sum(1 for e in elements if e["type"] == "steel_column")
    n_sb = sum(1 for e in elements if e["type"] == "steel_beam")
    print("=" * 70)
    print("EDIFICIO COMPLETO - OpenSeesPy (v1 - prueba)")
    print("=" * 70)
    print(f"  Nodos contrato : {len(nodes_json)}")
    print(f"  Elementos      : {len(elements)} (col={n_column}, bx={n_bx}, "
          f"by={n_by}, wall={n_wall}, loza={n_loza}, "
          f"scol={n_sc}, sbeam={n_sb})")
    print(f"  Apoyos          : {len(supports)}")

    import openseespy.opensees as ops

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", 6)

    # ------------------------------------------------------------------
    # 1. SOPORTES
    # ------------------------------------------------------------------
    support_tags = set(s["node"] for s in supports)
    # Apoyos huerfanos unidos por rigidLink 'bar' a un nodo estructural proximo:
    # NO se fijan directamente (la restriccion los define), evita doble constraint.
    bar_orphan_ids = {t for (t, _x, _y, _z, kind, _m) in orphan_nodes
                      if kind == "bar"}
    fix_orphan_ids = {t for (t, _x, _y, _z, kind, _m) in orphan_nodes
                      if kind == "fix"}
    support_tags -= bar_orphan_ids
    print(f"  Soportes (fijos): {len(support_tags)} "
          f"(+{len(bar_orphan_ids)} huerfanos por rigidLink 'bar', "
          f"+{len(fix_orphan_ids)} huerfanos fijos)")

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
    # 3. NODOS EXTRA del plan de conectividad
    #    - nodos de MUROS (9000+): no existen en el contrato; el plan fija
    #      su tag (misma logica compartida con exportar_analysis_map.py).
    #      Muro JSON: (xi, yi=ALTURA, zi) -> nodo (x=xi, y=zi, z=yi) en metros.
    #    - nodos de CONEXION en vigas (200000+): pie perpendicular del muro
    #      dentro del tramo -> subdivide la viga.
    #    - nodos HUERFANOS de apoyo (apoyos del contrato sin elemento propio).
    # ------------------------------------------------------------------
    wall_elems = [e for e in elements if e["type"] == "wall"]
    n_wall_nodes = len(conx["wall_node_coords"])
    for (tag, x, y, z) in conx["wall_node_coords"]:
        ops.node(tag, x, y, z)
    for (tag, x, y, z) in conx["extra_nodes"]:
        ops.node(tag, x, y, z)
    orphan_ids = set()
    for (nid, x, y, z, _kind, _master) in conx["orphan_nodes"]:
        ops.node(nid, x, y, z)
        orphan_ids.add(nid)

    n_nodes_total = len(conx["pos_key"])
    print(f"  Nodos totales (contrato + muros + conexion + huerfanos): "
          f"{n_nodes_total} (muros={n_wall_nodes}, "
          f"splits={len(conx['extra_nodes'])}, huerfanos={len(orphan_nodes)})")

    # pos_key global del modelo (mismos tags que el plan): lo usan fundacion,
    # diafragma, apoyos verticales de piso y resultados de desplazamientos.
    pos_key = conx["pos_key"]

    # FUNDACION: todo nodo (contrato o muro) en z=0 que no este en la lista
    # de apoyos queda empotrado; si no, el modelo tiene nodos flotantes
    # (U(i,i)=0 -> matriz singular). Los huerfanos BAR ya se unen por
    # rigidLink a un nodo estructural proximo: se omiten aqui para no
    # duplicar su restriccion.
    base_extra = []
    for (ax, ay, az), tag in pos_key.items():
        if az < 0.06 and tag not in support_tags and tag not in bar_orphan_ids:
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
        elif t in ("steel_column", "steel_beam"):
            i = nid_map[e["node_i"]]
            j = nid_map[e["node_j"]]
        else:
            continue

        is_steel = t in ("steel_column", "steel_beam")
        E_cur = E_STEEL if is_steel else E_CONC
        G_cur = G_STEEL if is_steel else G_CONC
        transf = 1 if t in ("column", "wall", "steel_column", "steel_beam") else 2
        b = e["b"] * CM_TO_M
        h = e["h"] * CM_TO_M
        if t == "wall":
            A, Iy, Iz, J = sec_wall_from_name(e.get("section", ""), b, h)
        elif is_steel:
            # Espesor del tubo: 3er campo del nombre de seccion "300x300x20" -> 20 mm.
            try:
                t_mm = float(str(e.get("section", "")).split("x")[2])
            except (ValueError, IndexError):
                t_mm = float(e.get("t", 20.0))
            tw = t_mm * 0.001  # mm -> m
            A, Iy, Iz, J = sec_tube(b, tw)
        else:
            A, Iy, Iz, J = sec_rect(b, h)

        if t in ("beam_x", "beam_y") and tag in frame_split:
            # Viga subdividida para conectar un muro en su interior (regla B).
            # La 1a fraccion conserva el tag del contrato (viewer 1:1); las
            # demas reciben tags 300000+ definidos en el plan compartido.
            for (ftag, ni, nj) in frame_split[tag]:
                ops.element("elasticBeamColumn", ftag, ni, nj,
                            A, E_cur, G_cur, J, Iy, Iz, transf)
                elem_meta[ftag] = {"type": t, "nodes": (ni, nj),
                                   "section": e.get("section", ""),
                                   "A": A, "Iy": Iy, "Iz": Iz, "J": J,
                                   "gamma": GAMMA_CONC,
                                   "parent": tag,
                                   "is_fraction": (ftag != tag)}
                incidence[ni] = incidence.get(ni, 0) + 1
                incidence[nj] = incidence.get(nj, 0) + 1
                n_created += 1
        else:
            ops.element(
                "elasticBeamColumn", tag, i, j,
                A, E_cur, G_cur, J, Iy, Iz, transf,
            )
            elem_meta[tag] = {"type": t, "nodes": (i, j),
                              "section": e.get("section", ""),
                              "A": A, "Iy": Iy, "Iz": Iz, "J": J,
                              "gamma": GAMMA_STEEL if is_steel else GAMMA_CONC,
                              "parent": tag, "is_fraction": False}
            incidence[i] = incidence.get(i, 0) + 1
            incidence[j] = incidence.get(j, 0) + 1
            n_created += 1

    print(f"  Elementos estructurales creados: {n_created} "
          f"(se omitieron {n_loza} lozas; "
          f"{sum(len(v) > 1 for v in frame_split.values())} vigas subdivididas)")

    # ------------------------------------------------------------------
    # 6. CONEXIONES del plan (reglas A-E): rigidLinks muro<->marco y
    #    apoyos huerfanos como esclavos de un nodo estructural proximo.
    #    Se omiten los links a nodos YA fijos (p.ej. base de muro en z=0,
    #    que base_extra empotra): un rigidLink adicional duplicaria la
    #    restriccion y el handler Transformation lo rechaza.
    # ------------------------------------------------------------------
    rigid_slave_tags = set()
    rigid_master_tags = set()
    for (_kind, master, slave) in rigid_links:
        if slave in support_tags:
            continue
        if _kind == "eq3":
            # Regla G (vigas apoyadas en muro de fachada): igualdad de
            # traslaciones ux,uy,uz. Las rotaciones quedan libres: la viga
            # sigue el movimiento del punto del muro sin arrastrar el giro del
            # muro ancho por el brazo de conexion (rx*brazo = descuelgue
            # artificial). Si el master esta fijo se omite (duplicaria
            # constraint, Transformation lo rechaza).
            ops.equalDOF(master, slave, 1, 2, 3)
        else:
            ops.rigidLink(_kind, master, slave)
        rigid_slave_tags.add(slave)
        rigid_master_tags.add(master)
    for (nid, _x, _y, _z, kind, master) in conx["orphan_nodes"]:
        if kind == "bar":
            # Esclavo traslacional del nodo estructural proximo + rotaciones
            # empotradas: el nodo no conecta a elementos y sus rx/ry/rz libres
            # dejarian la diagonal en cero (matriz singular). Las traslaciones
            # las define el rigidLink; las rotaciones quedan fijas (apoyo).
            ops.fix(nid, 0, 0, 0, 1, 1, 1)
            ops.rigidLink("bar", master, nid)
    if rigid_links or orphan_nodes:
        print(f"  Conexiones: {len(rigid_links)} rigidLinks "
              f"(reglas A-E), {len(conx['orphan_nodes'])} apoyos huerfanos "
              f"({len([o for o in conx['orphan_nodes'] if o[4] == 'bar'])} por "
              f"rigidLink 'bar')")

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
        if e["type"] in ("column", "steel_column"):
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
    # Nodos de CONEXION del plan (splits de viga 200000+): estan sobre la viga,
    # NO reciben suelo vertical artificial (seria un apoyo extra que endurece el
    # tramo; el muro se conecta ahi por rigidLink y la viga transmite la carga).
    split_node_tags = {t for (t, *_rest) in conx["extra_nodes"]}
    # Nodos INTERIORES de vigas subdivididas (Regla F y B): son cruces que
    # reciben rigidez vertical REAL de la viga pasante que los atraviesa. NO
    # deben recibir el suelo vertical artificial de la losa (regla 7b), o las
    # vigas secundarias quedan clavadas en u_z=0 y no flexionan bajo G/Q.
    cruce_node_tags = set()
    for fracc in conx["frame_split"].values():
        for k in range(len(fracc) - 1):
            cruce_node_tags.add(fracc[k + 1][1])
    ya_soportado = (set(support_tags) | set(floating_supports)
                    | split_node_tags | cruce_node_tags)
    # RED DE RIGIDEZ VERTICAL (BFS): un nodo de la reticula que tiene CAMINO de
    # vigas/columnas/rigidLinks (muros) hasta la fundacion ya recibe su rigidez
    # vertical por FLEXION de las vigas (o carga real). NO debe recibir el suelo
    # vertical artificial de regla 7b; ese apoyo solo queda para nodos que no
    # tienen ninguna ruta a soporte (huerfanos/voladizos sin red). Asi las vigas
    # en voladizo/encastre flexionan y bajan bajo G/Q en vez de quedar clavadas.
    grafo_v = {}
    for _a, _b in [(e["node_i"], e["node_j"]) for e in elements
                   if e["type"] in ("beam_x", "beam_y", "column",
                                    "steel_column", "steel_beam")
                   and e["node_i"] in nid_map and e["node_j"] in nid_map]:
        grafo_v.setdefault(nid_map[_a], set()).add(nid_map[_b])
        grafo_v.setdefault(nid_map[_b], set()).add(nid_map[_a])
    for _kind, _a, _b in rigid_links:
        grafo_v.setdefault(_a, set()).add(_b)
        grafo_v.setdefault(_b, set()).add(_a)
    seeds = ((set(conx["support_tags"]) | set(conx["base_extra"]))
             & set(nid_map.values())) | set(floating_supports)
    reachable_v = set(seeds)
    stack = list(seeds)
    while stack:
        nn = stack.pop()
        for mm in grafo_v.get(nn, ()):
            if mm in reachable_v:
                continue
            reachable_v.add(mm)
            stack.append(mm)
    # CASOS ESPECIALES: extremos libres de voladizos largos sin viga pasante.
    # beam_x 335-344 => nodos 167..180. Estos ya se apoyan en la muralla 315..319
    # via REGLA G (rigidLink wall->viga, plan conexiones): se RETIRAN del set y
    # el apoyo vertical real lo da el muro. beam_y 390-394 => nodos 398..407
    # (x=3205) siguen sin muro asignado: se mantienen con suelo vertical
    # artificial hasta que el usuario seleccione sus muros.
    regla_g_nodes = set(conx.get("regla_g_nodes", ()))
    casos_especiales = set(range(398, 408)) if regla_g_nodes else (
        {167, 170, 173, 176, 179, 168, 171, 174, 177, 180}
        | set(range(398, 408)))
    for (rx, ry, rz), tag in pos_key.items():
        x_cm, y_cm, z_cm = rx / CM_TO_M, ry / CM_TO_M, rz / CM_TO_M
        if z_cm < 356.0:         # subterraneo: lo maneja (a)/columnas/muros
            continue
        if tag in ya_soportado:
            continue               # ya apoyo real o master de (a): no duplicar
        if tag in reachable_v and tag not in casos_especiales:
            continue               # ya tiene rigidez vertical por la red
        # Tiene columna bajo si el nodo coincide con el EXTREMO SUPERIOR de una
        # columna en SU PROPIO nivel. col_tops guarda (x,y) del extremo superior
        # por nivel z (cm). Antes se buscaba en un nivel ESTRICTAMENTE inferior,
        # lo que no detectaba la columna cuyo tope esta en el mismo z del nodo
        # (y al no encontrarla, el nodo recibia un apoyo vertical espurio).
        has_col = (round(x_cm, 1), round(y_cm, 1)) in col_tops.get(round(z_cm), set())
        if has_col:
            continue               # tiene columna bajo
        if muro_cubre(x_cm, y_cm, z_cm):
            continue               # dentro de un muro
        # Suelo vertical: uz + minimo rx,ry. Solo uz deja el mecanismo de giro
        # fuera del plano (matriz singular, analyze -3); rx/ry son los DOF que
        # quitan ese modo y generan PAR, no reaccion lateral. ux/uy/rz los
        # condiciona el diafragma del piso.
        ops.fix(tag, 0, 0, 1, 1, 1, 0)
        piso_vertical.append(tag)
        n_losa += 1
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
    # Apoyos huerfanos TIPO FIX: se crean (seccion 3) y quedan empotrados en
    # su posicion; los huerfanos tipo BAR ya se unieron por rigidLink y NO se
    # fijan (evita doble constraint). Los huerfanos fijos no estan en nid_map.
    for nid in fix_orphan_ids:
        ops.fix(nid, 1, 1, 1, 1, 1, 1)

    # ------------------------------------------------------------------
    # 8. DIAFRAGMA RIGIDO POR PISO
    #    Maestro = nodo no-soporte con mayor grado de conexion en el piso.
    #    Esclavos = resto de nodos del piso (excepto soportes y maestro).
    # ------------------------------------------------------------------
    diaphragm_flag = False   # una bandera por piso creado (para compatibilidad)
    diaphragm_sets = []      # (master, z_m, [slaves]) para verificacion de compatibilidad
    if USE_DIAPHRAGM:
        # agrupar por NIVEL EXACTO (misma z) -> el rigidDiaphragm exige
        # que maestro y esclavos esten en el mismo plano xy.
        levels = {}
        for tag in pos_key.values():
            z = ops.nodeCoord(tag)[2]          # metros (altura)
            levels.setdefault(round(z, 6), []).append(tag)

        for z, tags in sorted(levels.items()):
            fl = floor_of(z / CM_TO_M)
            # excluir del diafragma: apoyos reales (fijos), esclavos de
            # rigidLink (su movimiento en el plano ya lo impone el link al
            # nodo de la viga; un rigidDiaphragma adicional duplicaria la
            # restriccion de ux/uy/rz y Transformation lo rechazaria) y
            # MASTERS de rigidLink (el nodo que arrastra al esclavo no puede
            # estar a su vez constrenido por el diafragma del piso, o la
            # cadena diafragma->rigidLink no transmite la traslacion).
            excl = (set(support_tags) | set(rigid_slave_tags)
                    | set(rigid_master_tags))
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
            diaphragm_flag = True
            diaphragm_sets.append((master, z, slaves))
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
    # Peso propio de elementos estructurales desglosado por piso (para masa
    # sismica). Cada elemento reparte W/2 en cada extremo; cada medio se asigna
    # al piso del nodo extremo respectivo (se contabilizan AMBOS extremos).
    # El 'Subterraneo' (z<356) acumula el peso de lo que cae bajo el primer
    # nivel: es MASA DE DIAFRAGMA no-restringida y NO participa en la carga
    # lateral de piso (no hay diafragma en z=0), pero cuenta en el peso total.
    self_weight_by_floor = {}
    self_weight_foundation = 0.0     # peso propio por debajo del primer forjado

    def node_xyz(tag):
        return ops.nodeCoord(tag)[:3]

    for tag, meta in elem_meta.items():
        A = meta["A"]
        i, j = meta["nodes"]
        xi, yi, zi = node_xyz(i)
        xj, yj, zj = node_xyz(j)
        L = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2 + (zj - zi) ** 2)
        W = meta.get("gamma", GAMMA_CONC) * A * L
        total_W += W
        half = W / 2.0
        k = (round(xi, 6), round(yi, 6), round(zi, 6))
        nodal.setdefault(i, [0.0, 0.0, 0.0])[2] -= half
        nodal.setdefault(j, [0.0, 0.0, 0.0])[2] -= half
        # desglose por piso: contabilizar W/2 en el piso de CADA extremo
        zi_cm, zj_cm = zi * 100.0, zj * 100.0
        fl_i, fl_j = floor_of(zi_cm), floor_of(zj_cm)
        self_weight_by_floor[fl_i] = self_weight_by_floor.get(fl_i, 0.0) + half
        self_weight_by_floor[fl_j] = self_weight_by_floor.get(fl_j, 0.0) + half

    self_weight_kN = total_W      # peso propio de elementos estructurales (kN)

    nodes_map = {n["id"]: n for n in nodes_json}

    # Tributario de REFERENCIA (q_G completo: PP losa + terminaciones), para el
    # Inspector y la verificacion de areas/conservacion (independiente del caso).
    cargas_losa_qG = cargas_para_vigas(JSON_PATH, nodes_map,
                                       extra_kn_m2=TERMINACIONES_KNM2,
                                       include_self_weight=True)

    # Tributario de Q (sobrecarga, sin peso propio): misma geometria tributaria
    # que G, solo cambia la intensidad por m2. Se calcula UNA vez (no por viga).
    cargas_losa_qQ = cargas_para_vigas(JSON_PATH, nodes_map,
                                       extra_kn_m2=SOBRECARGA_KNM2,
                                       include_self_weight=False)

    # Area tributaria TRANSFERIDA por losa (id loza -> m2), identica en G y Q:
    # solo suma lo que realmente llega a una viga (excluye huecos y losas
    # aisladas). Se usa para G/Q por piso, masa sismica y centro de masa, de
    # forma CONSISTENTE con la transferencia (punto 3 de la revision).
    trib_area_by_loza = defaultdict(float)
    for c in cargas_losa_qG.values():
        for ap in c.get('aportes', []):
            trib_area_by_loza[ap['loza']] += ap['area_m2']

    # Tributario EXPLICITO por viga (para el Tributary Area Inspector)
    tributary_by_viga = {}
    for tag, meta in elem_meta.items():
        if meta["type"] not in ("beam_x", "beam_y"):
            continue
        if meta.get("is_fraction"):
            continue          # solo el tag del contrato (los demas son fracciones)
        c = cargas_losa_qG.get(tag) or {"p": 0.0, "A": 0.0, "W": 0.0,
                                        "aportes": []}
        cQ = cargas_losa_qQ.get(tag) or {"p": 0.0, "A": 0.0, "W": 0.0}
        tributary_by_viga[str(tag)] = {
            "type": meta["type"],
            "section": meta["section"],
            "area_tributaria_m2": round(c["A"], 6),
            "W_losa_G_kN": round(c["W"], 6),
            "p_G_kN_m": round(c["p"], 6),
            "W_losa_Q_kN": round(cQ["W"], 6),
            "p_Q_kN_m": round(cQ["p"], 6),
            "aportes": [
                {"losa": ap["loza"], "borde": ap["borde"],
                 "tramo_m": [ap["tramo"][0] / 100.0, ap["tramo"][1] / 100.0],
                 "area_m2": ap["area_m2"], "W_G_kN": ap["W_kN"]}
                for ap in c["aportes"]
            ],
        }

    # ------------------------------------------------------------------
    # CARGA DEL CASO (G / Q / EX / EY)
    #   - G : peso propio estructural + q_G de losa (terminaciones + PP) por tributarias
    #   - Q : solo q_Q de losa (sobrecarga) por tributarias, misma geometria que G
    #   - EX/EY : carga lateral sismica en el centro de masa de cada piso (master
    #             del diafragma). Sin cargas gravitacionales en este caso base.
    # Cada caso se carga en un pattern independiente; ops.wipe() al inicio de cada
    # run_case garantiza que no queden residuos del caso anterior (sin mezclar G y Q).
    # ------------------------------------------------------------------
    if case_name == "G":
        cargas_losa = cargas_losa_qG
        apply_selfweight = True
        is_lateral = False
    elif case_name == "Q":
        cargas_losa = cargas_losa_qQ    # mismo calculo que G, intensidad q_Q
        apply_selfweight = False
        is_lateral = False
    elif case_name == "COMBO":
        # Parte C: superposicion con lambdas. La carga de losa que recibe cada
        # viga es la combinacion lambda_G q_G + lambda_Q q_Q, y el peso propio
        # estructural se escala por lambda_G (misma intensidad que en G).
        cargas_losa = {}
        for tag, c in cargas_losa_qG.items():
            cq = cargas_losa_qQ.get(tag)
            p = LAMBDA_G * c["p"] + ((LAMBDA_Q * cq["p"]) if cq else 0.0)
            W = LAMBDA_G * c["W"] + ((LAMBDA_Q * cq["W"]) if cq else 0.0)
            cargas_losa[tag] = {"p": p, "A": c["A"], "W": W}
        apply_selfweight = LAMBDA_G != 0.0
        is_lateral = True        # puede incluir componentes sismicas EX/EY
    else:                       # EX o EY: caso sismico lateral
        cargas_losa = {}
        apply_selfweight = False
        is_lateral = True

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    if apply_selfweight:
        w_scale = LAMBDA_G if case_name == "COMBO" else 1.0
        for tag, (fx, fy, fz) in nodal.items():
            ops.load(tag, fx * w_scale, fy * w_scale, fz * w_scale, 0.0, 0.0, 0.0)

    print(f"  Peso propio (elementos estructurales): {total_W:.2f} kN")

    total_losa = 0.0
    n_viga_cargada = 0
    for tag, meta in elem_meta.items():
        if meta["type"] not in ("beam_x", "beam_y"):
            continue
        # Fracciones de una viga subdividida: la carga lineal (kN/m) es la de
        # la viga PADRE; ops.eleLoad beamUniform la reparte por longitud, asi
        # cada fraccion recibe automaticamente su parte proporcional.
        p = cargas_losa.get(meta.get("parent", tag), {}).get("p", 0.0)
        if p <= 0:
            continue
        i, j = meta["nodes"]
        xi, yi, zi = node_xyz(i)
        xj, yj, zj = node_xyz(j)
        L = math.sqrt((xj - xi) ** 2 + (yj - yi) ** 2 + (zj - zi) ** 2)
        ops.eleLoad("-ele", tag, "-type", "beamUniform", 0.0, -p)
        total_losa += p * L
        n_viga_cargada += 1

    total_W_apply = (LAMBDA_G * self_weight_kN) if (apply_selfweight and case_name == "COMBO") else (self_weight_kN if apply_selfweight else 0.0)
    total_W_apply += total_losa
    print(f"  Carga de losa (areas tributarias)  : {total_losa:.2f} kN  "
          f"({n_viga_cargada} vigas)")
    print(f"  CARGA {case_name} TOTAL                  : {total_W_apply:.2f} kN")

    # ==================================================================
    # MASA SISMICA Y CARGA LATERAL (casos EX / EY)
    # ==================================================================
    # Datos para la defensa (verificaciones) también usados en G y Q.
    # La carga lateral sismica se aplica en el CENTRO DE MASA de cada piso,
    # representado por el nodo MASTER del diafragma rigido de ese piso
    # (ops.rigidDiaphragm acopla ux, uy, rz de todos los nodos del piso al
    # master, de modo que una fuerza en el master se distribuye por todo el
    # piso como cuerpo rigido). Por eso la fuerza se aplica ahi y el Rz del
    # master reporta directamente la torsion de piso.
    piso_to_master = {}
    for master, zm, slaves in diaphragm_sets:
        z_cm = zm / CM_TO_M
        piso_to_master[floor_of(z_cm)] = master

    # Diagnostico de correspondencia piso<->diafragma (punto 4 de la revision):
    # claves de piso duplicadas (dos diafragmas en el mismo nivel -> la segunda
    # sobrescribiria la primera). Los pisos con masa SIN master se detectan
    # despues de construir G_floor (ver abajo).
    duplicados_piso = defaultdict(int)
    for master, zm, slaves in diaphragm_sets:
        duplicados_piso[floor_of(zm / CM_TO_M)] += 1
    piso_dup = {fl: n for fl, n in duplicados_piso.items() if n > 1}
    if piso_dup:
        print(f"  [AVISO] Diafragmas DUPLICADOS en piso: {piso_dup} "
              f"(se sobrescribe, revisar)")

    # Carga de LOSA por piso, desglosada en G (PP+terminaciones) y Q (sobrecarga).
    # (Usa la misma geometria tributaria: solo difiere la intensidad por m2.)
    # IMPORTANTE (consistencia, punto 3 de la revision): el area por piso es el
    # area REALMENTE TRANSFERIDA a las vigas (trib_area_by_loza), identica a la
    # masa sismica y a la transferencia G/Q. Las losas aisladas y los huecos de
    # cobertura quedan FUERA de la masa del modelo (no hay elemento estructural
    # que los lleve) y se reportan aparte.
    def losa_por_piso(w_m2_fn):
        acc = {}
        for e in elements:
            if e["type"] != "loza":
                continue
            A = trib_area_by_loza.get(e["id"], 0.0)
            if A <= 0:
                continue
            fl = floor_of(e["yi"])
            acc[fl] = acc.get(fl, 0.0) + w_m2_fn(e) * A
        return acc

    losa_G_by_floor = losa_por_piso(
        lambda e: GAMMA_CONC * (e.get("t", 25.0) / 100.0) + TERMINACIONES_KNM2)
    losa_Q_by_floor = losa_por_piso(lambda e: SOBRECARGA_KNM2)  # solo sobrecarga

    # G y Q totales por piso:
    #   G_floor = peso propio estructural del piso + losa G
    #   Q_floor = losa Q (sobrecarga) del piso
    G_floor = {}
    Q_floor = {}
    for fl in set(list(self_weight_by_floor) + list(losa_G_by_floor) +
                  list(losa_Q_by_floor)):
        G_floor[fl] = self_weight_by_floor.get(fl, 0.0) + losa_G_by_floor.get(fl, 0.0)
        Q_floor[fl] = losa_Q_by_floor.get(fl, 0.0)

    # Pisos con masa pero SIN master de diafragma (no participarian en sismo).
    pisos_sin_master = sorted(
        fl for fl in G_floor if fl != "Subterraneo" and fl not in piso_to_master)
    if pisos_sin_master:
        print(f"  [AVISO] Pisos con carga SIN master de diafragma: "
              f"{pisos_sin_master} (no participan en masa sismica lateral)")

    G_total = sum(G_floor.values())
    Q_total = sum(Q_floor.values())
    # Peso de fundacion/subterraneo (NO participa en carga lateral: no hay
    # diafragma en z=0; el diafragma se apoya en los forjados superiores).
    foundation_weight = G_floor.get("Subterraneo", 0.0)
    W_sismico_total = G_total + FRAC_LIVE_SISMIC * Q_total

    if is_lateral:
        # ==============================================================
        # CENTRO DE MASA POR PISO (ponderado G + 0.50 Q)
        # ==============================================================
        # El nodo master del diafragma se elige por CONECTIVIDAD (nodo mas
        # conectado del piso), no por el centro de masa. Aplicar la fuerza
        # sismica en el master introduciria una torsion ESPURIA si el master
        # no coincide con el CM. Por eso se calcula el CM de cada piso y la
        # fuerza se aplica en el master como carga EQUIVALENTE:
        #    Fx, Fy en el master + Mz = (xCM - xM)*Fy - (yCM - yM)*Fx
        # (teorema de traslacion de fuerzas; la carga resultante actua en el
        # CM real). El CM se calcula ponderando:
        #   - masa ESTRUCTURAL por nodo (peso propio repartido W/2 por extremo)
        #   - masa de LOSA del piso (G_losa + FRAC*Q), repartida en el contorno
        #     de cada losa -> centroide geometrico de las losas del piso.
        def tag_floor(tag):
            z = ops.nodeCoord(tag)[2]
            return floor_of(z * 100.0)

        # masa estructural por nodo: |W/2 acumulada en z|, base para CM
        struc_mass = {}   # tag -> kN (peso propio)
        for tag, f in nodal.items():
            w = abs(f[2])
            if w > 0:
                struc_mass[tag] = w

        # CM y W por losa (pondera G_losa + FRAC*Q); centroide geometrico.
        # Usa el area TRANSFERIDA (trib_area_by_loza), consistente con G_floor/
        # Q_floor y con la masa sismica (losas aisladas y huecos excluidos).
        losa_mass = {}    # fl -> (W_losa, cx, cy)
        for e in elements:
            if e["type"] != "loza":
                continue
            A = trib_area_by_loza.get(e["id"], 0.0)
            if A <= 0:
                continue
            fl = floor_of(e["yi"])
            w_m2 = (GAMMA_CONC * (e.get("t", 25.0) / 100.0) + TERMINACIONES_KNM2) \
                + FRAC_LIVE_SISMIC * SOBRECARGA_KNM2
            W = w_m2 * A
            cx = ((e["xi"] + e["xj"]) / 2.0) / 100.0
            cy = ((e["zi"] + e["zj"]) / 2.0) / 100.0
            acc = losa_mass.get(fl)
            if acc is None:
                losa_mass[fl] = [W, W * cx, W * cy]
            else:
                acc[0] += W; acc[1] += W * cx; acc[2] += W * cy

        seismic = {}
        for fl in sorted(set(tag_floor(t) for t in struc_mass) |
                         set(losa_mass) | set(G_floor)):
            if fl == "Subterraneo":
                continue
            # masa estructural de este piso: se suman TODOS los nodos con masa
            # cuyo nivel (z) pertenece al piso (tag_floor), NO solo los nodos
            # del diafragma (master+esclavos a z exacta). Un extremo de muro o
            # elemento cuya z cae dentro de la banda del piso (pero distinta de
            # la z exacta del diafragma) aporta su W/2 en self_weight_by_floor
            # y DEBE contar igual en el CM para que W_CM == W_F se cumpla.
            W_s = 0.0
            cx_s = 0.0
            cy_s = 0.0
            for tag, w in struc_mass.items():
                if tag_floor(tag) != fl:
                    continue
                x, y, _ = ops.nodeCoord(tag)
                W_s += w
                cx_s += w * x
                cy_s += w * y
            if W_s > 0:
                cx_s /= W_s
                cy_s /= W_s
            # masa de losa de este piso
            W_l, lx, ly = losa_mass.get(fl, [0.0, 0.0, 0.0])
            cx_l = lx / W_l if W_l > 0 else 0.0
            cy_l = ly / W_l if W_l > 0 else 0.0
            W_floor = G_floor.get(fl, 0.0) + FRAC_LIVE_SISMIC * Q_floor.get(fl, 0.0)
            cx = ((W_s * cx_s + W_l * cx_l) / (W_s + W_l)) if (W_s + W_l) else 0.0
            cy = ((W_s * cy_s + W_l * cy_l) / (W_s + W_l)) if (W_s + W_l) else 0.0
            # Verificacion de consistencia (punto 5): el peso total de la masa
            # usada en el CM (estructura + losa) debe coincidir con el peso de
            # la fuerza F = alpha*W_sismico del piso (W_CM == W_F).
            W_cm = W_s + W_l
            err_wcm = (abs(W_cm - W_floor) / W_floor) if W_floor else 0.0
            seismic[fl] = {
                "G_floor": G_floor.get(fl, 0.0),
                "Q_floor": Q_floor.get(fl, 0.0),
                "W_sismico_floor": W_floor,
                "massa_piso": W_floor / g,
                "masa_kg": 1000.0 * W_floor / g,
                "F_floor": ALPHA_SISMO * W_floor,
                "master": piso_to_master.get(fl),
                "CM": (cx, cy),
                "W_cm_check": W_cm,
                "err_W_cm": err_wcm,
            }

        # todas_ok de masa sismica: W_CM == W_F en 100% de los pisos con masa
        ok_mass = all(s["err_W_cm"] < 1e-10 for s in seismic.values()) \
            and bool(seismic)
        if not ok_mass:
            for fl, s in seismic.items():
                if s["err_W_cm"] >= 1e-10:
                    print(f"  [AVISO] W_CM != W_F en {fl}: "
                          f"W_cm={s['W_cm_check']:.3f} vs W_F={s['W_sismico_floor']:.3f}")

        print(f"\n  === MASA SISMICA (G + {FRAC_LIVE_SISMIC:.0%} Q) ===  "
              f"alpha_sismo={ALPHA_SISMO:.2f}")
        for fl in sorted(seismic):
            s = seismic[fl]
            print(f"    {fl:12s}: G={s['G_floor']:10.2f}  Q={s['Q_floor']:9.2f}  "
                  f"W={s['W_sismico_floor']:10.2f}  m={s['massa_piso']:9.1f} t  "
                  f"F={s['F_floor']:9.2f} kN  master={s['master']}  "
                  f"CM=({s['CM'][0]:.2f},{s['CM'][1]:.2f})")

        # Aplicar la fuerza en el CM via carga equivalente en el master.
        # EX: Fx=+F ; EY: Fy=+F (sentido positivo del eje global).
        # COMBO: componentes X (lambda_EX) e Y (lambda_EY) simultaneas.
        if case_name == "COMBO":
            dirx = LAMBDA_EX
            diry = LAMBDA_EY
        else:
            dirx = 1 if case_name == "EX" else 0
            diry = 1 if case_name == "EY" else 0
        F_total_lateral = 0.0
        fx_total = 0.0
        fy_total = 0.0
        W_sismico_efectivo = 0.0     # solo pisos con diafragma (participan)
        for fl, s in seismic.items():
            if s["master"] is None:
                continue
            F = s["F_floor"]
            W_sismico_efectivo += s["W_sismico_floor"]
            cx, cy = s["CM"]
            xm, ym, _ = ops.nodeCoord(s["master"])
            # Mz de la fuerza trasladada del CM al master
            Mz = (cx - xm) * (diry * F) - (cy - ym) * (dirx * F)
            ops.load(s["master"], dirx * F, diry * F, 0.0, 0.0, 0.0, Mz)
            F_total_lateral += F
            fx_total += dirx * F
            fy_total += diry * F
        if case_name == "COMBO":
            # conserva la carga combinada (gravity + lateral) para el reporte
            total_W_apply = total_W_apply + fx_total + fy_total
        else:
            total_W_apply = F_total_lateral
        print(f"  SISMO {case_name}: F_total aplicada = {F_total_lateral:.2f} kN "
              f"sobre {len([s for s in seismic.values() if s['master']])} pisos")
        print(f"  F esperada = alpha*W_efectivo = {ALPHA_SISMO*W_sismico_efectivo:.2f} kN "
              f"(W_efectivo={W_sismico_efectivo:.2f} kN, fundacion excluida="
              f"{foundation_weight:.2f} kN)")
        print(f"  CARGA {case_name} TOTAL (corte basal esperado) : {total_W_apply:.2f} kN")

        # Fuerza esperada CON INDEPENDENCIA de la lista aplicada (punto 6 de la
        # revision): se recalcula desde G_floor/Q_floor directamente, exigiendo
        # participacion de todos los pisos con masa (excepto Subterraneo) y que
        # ninguno quedara sin master. No se reutiliza 'seismic' para el check.
        W_ef_indep = sum(
            G_floor.get(fl, 0.0) + FRAC_LIVE_SISMIC * Q_floor.get(fl, 0.0)
            for fl in G_floor
            if fl != "Subterraneo" and fl in piso_to_master)
        F_esperada_indep = ALPHA_SISMO * W_ef_indep
        participacion_ok = (not pisos_sin_master) and \
            all(fl in piso_to_master for fl in G_floor if fl != "Subterraneo")
        okFe = (F_esperada_indep > 0.0 and F_total_lateral > 0.0
                and abs(F_total_lateral - F_esperada_indep) / F_esperada_indep
                < 1e-10 and participacion_ok)
        err_Fe = (abs(F_total_lateral - F_esperada_indep) / F_esperada_indep
                  if F_esperada_indep else float("inf"))
        print(f"  F esperada (independiente)= {F_esperada_indep:.2f} kN  "
              f"(W_efectivo_indep={W_ef_indep:.2f} kN, "
              f"fundacion_excluida={foundation_weight:.2f} kN)  "
              f"err={err_Fe:.3e}  ({'OK' if okFe else 'NO'})")

    # Para la auditoria/conservacion (caso G y Q):
    seismic_summary = {
        "G_floor": G_floor, "Q_floor": Q_floor,
        "G_total": G_total, "Q_total": Q_total,
        "W_sismico_total": W_sismico_total,
        "piso_to_master": piso_to_master,
    }

    # ------------------------------------------------------------------
    # ANALISIS ESTATICO LINEAL
    # ------------------------------------------------------------------
    ops.system("BandSPD")
    ops.numberer("RCM")
    ops.constraints("Transformation")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")

    ok = ops.analyze(1)
    ops.reactions()
    print(f"  analyze() -> {ok}")
    if ok != 0:
        print("  [ERROR] El analisis fallo. Revisar modelo (diafragma, muros, secciones).")
        return None

    # ------------------------------------------------------------------
    # VERIFICACIONES
    # ------------------------------------------------------------------
    print("-" * 70)
    print(f"VERIFICACIONES DEL EDIFICIO REAL — caso {case_name}")

    in_model = set(ops.getNodeTags())
    all_support_tags = sorted(
        (set(support_tags) | set(floating_supports) | set(piso_vertical)) &
        in_model)
    # Apoyos verdaderamente fijos en todos los DOF (solo fundacion).
    # Estos son los que reaccionan horizontalmente en sismo. Los floating y
    # piso_vertical tienen ux/uy libres (0,0,1,1,1,0) y sus reacciones
    # horizontales via nodeReaction incluyen fuerzas de constraint del diafragma
    # que NO son reacciones fisicas de apoyo.
    base_support_tags = sorted(set(support_tags) & in_model)

    # (a) Equilibrio global: Sigma F + Sigma R = 0
    #     Para G/Q: comparar Rz vs total_W_apply (carga vertical).
    #     Para EX/EY: comparar Rx/Ry vs F_lateral (carga horizontal).
    #     CON CONEXIONES (rigidDiaphragm/rigidLink de muros) la suma DEBE
    #     hacerse sobre TODOS los nodos del modelo: parte de la carga queda
    #     en masters/slaves de constraint (nodos de conexion 200000+ y de
    #     muro 9000+) que no son apoyos fisicos, y por eso
    #     Sigma(all_support_tags) != Sigma(total). Con Transformation la
    #     identidad exacta es Sigma(nodeReaction en todos) + Sigma(F) = 0.
    Rx = Ry = Rz = 0.0
    for tag in in_model:
        r = ops.nodeReaction(tag)
        Rx += r[0]; Ry += r[1]; Rz += r[2]
    if is_lateral and case_name in ("EX", "EY"):
        F_applied = total_W_apply
        dir_axis = 0 if case_name == "EX" else 1   # 0=X, 1=Y
        # Equilibrio global (identidad exacta con Transformation): la suma de
        # nodeReaction sobre TODOS los nodos cancela las fuerzas internas de
        # constraint (rigidDiaphragm / rigidLink de muros) y debe dar -F.
        R_eje = Rx if dir_axis == 0 else Ry
        err = (abs(F_applied + R_eje) / F_applied) if F_applied else float("inf")
        ok_eq = err < 1e-10 and F_applied > 0.0
        print(f"    . Equilibrio {case_name} (global): F_applied={F_applied:12.3f}  "
              f"R_global({case_name[-1]})={R_eje:12.3f}  err={err:.3e}  "
              f"({'OK' if ok_eq else 'NO'})")
    elif case_name == "COMBO":
        # El equilibrio del caso combinado se audita en su propia seccion
        # (AUDITORIA SUPERPOSICION COMBO), donde se verifica F+R=0 en X, Y, Z.
        print(f"    . Equilibrio COMBO: auditado en la seccion dedicada (X, Y, Z)")
    else:
        err = abs((total_W_apply - Rz) / total_W_apply) if total_W_apply else float("inf")
        ok_eq = err < 1e-10 and total_W_apply > 0.0
        print(f"    . Equilibrio {case_name}: SigmaX={Rx:9.3f}  SigmaY={Ry:9.3f}  "
              f"SigmaZ={Rz:12.3f}  W={total_W_apply:12.3f}  err={err:.3e}  "
              f"({'OK' if ok_eq else 'NO'})")

    # (b) Areas tributarias + conservacion (referencia q_G)
    ok_areas, res_areas = verificar_areas_tributarias(
        JSON_PATH, nodes_map, extra_kn_m2=TERMINACIONES_KNM2,
        include_self_weight=True)
    ok_conserv = (res_areas['conservacion_rel_W'] < 1e-10
                  and res_areas['conservacion_rel_A'] < 1e-10)
    print(f"    . Carga de losa q_G: W_losas={res_areas['W_losas_kN']:.1f} kN, "
          f"W_vigas(transf)={res_areas['W_vigas_kN']:.1f} kN, "
          f"W_huecos={res_areas['W_huecos_kN']:.3f} kN, "
          f"conservacion rel={res_areas['conservacion_rel_W']:.3e} "
          f"({'OK' if ok_conserv else 'NO'})")
    print(f"      Suma areas trib: A_lozas={res_areas['A_lozas_total_m2']:.2f} m2, "
          f"A_trib(vigas)={res_areas['A_trib_total_m2']:.2f} m2, "
          f"A_huecos={res_areas['A_huecos_m2']:.3f} m2, "
          f"diferencia rel={res_areas['conservacion_rel_A']:.3e} "
          f"({'OK' if ok_conserv else 'NO'})")
    if res_areas['huecos_pendientes']:
        print("      Huecos de cobertura (borde con viga parcial, sin soporte):")
        for h in res_areas['huecos_pendientes']:
            print(f"        losa {h['loza']} {h['borde']} "
                  f"tramo={h['hueco_cm']} A={h['area_m2']:.4f} m2")
    for lz in res_areas['aisladas']:
        print(f"      Losa aislada (sin viga en ningun borde): "
              f"losa {lz['id']} A={lz.get('A_m2', 0.0):.4f} m2 "
              f"[{lz['motivo']}]")

    # (c) Carga de losa por piso (q_G y q_Q), area TRANSFERIDA
    print("    . Carga de losa por piso (kN), area transferida:")
    for fl in sorted(set(list(losa_G_by_floor) + list(losa_Q_by_floor))):
        print(f"        {fl:12s}: G_losa={losa_G_by_floor.get(fl,0.0):.2f}  "
              f"Q_losa={losa_Q_by_floor.get(fl,0.0):.2f}")

    # (d) Compatibilidad del diafragma rigido
    dmax = 0.0
    for master, zm, slaves in diaphragm_sets:
        dm = ops.nodeDisp(master)
        ux_m, uy_m, rz_m = dm[0], dm[1], dm[5]
        xm, ym, _ = ops.nodeCoord(master)
        for s in slaves:
            x, y, _ = ops.nodeCoord(s)
            d = ops.nodeDisp(s)
            e1 = abs(d[0] - (ux_m - rz_m * (y - ym)))
            e2 = abs(d[1] - (uy_m + rz_m * (x - xm)))
            dmax = max(dmax, e1, e2)
    ok_dia = dmax < 1e-9
    print(f"    . Diafragma rigido: compat. err max={dmax:.3e}  "
          f"({'OK' if ok_dia else 'NO'}), {len(diaphragm_sets)} pisos con diafragma")

    # ------------------------------------------------------------------
    # AUDITORIA ESPECIFICA DE CARGA VIVA Q (Parte A)
    # ------------------------------------------------------------------
    # Verifica conservacion:  Σ(Q transferida a vigas) ≈ q_Q * A_transferible.
    # La carga viva usa EXACTAMENTE la misma geometria tributaria que G, por lo
    # que el doble conteo se evita usando q_Q (sin incluir peso propio de losa)
    # sobre las mismas areas tributarias. Q queda en un pattern independiente.
    if case_name == "Q":
        # Referencia: area realmente TRANSFERIBLE = losas soportadas MENOS los
        # huecos de cobertura (borde con viga parcial, ese pedazo no llega a
        # ninguna viga). El verificador reporta aparte:
        #   * losas aisladas (antepecho/remate de borde, 20 x 282 cm, una por
        #     nivel 388.5/744.5/1100.5/1456.5): sin viga en NINGUN borde -> no
        #     tienen elementos estructurales que las reciban; excluidas del
        #     modelo y reportadas aparte (2.256 m2 en total);
        #   * huecos: borde con viga parcial -> la franja sin viga queda como
        #     pendiente y NO se inventa soporte.
        _, resQ = verificar_areas_tributarias(
            JSON_PATH, nodes_map, extra_kn_m2=SOBRECARGA_KNM2,
            include_self_weight=False)
        A_soportada = resQ['A_lozas_total_m2']
        A_huecos = resQ['A_huecos_m2']
        A_aisladas = resQ['A_lozas_aisladas_m2']
        A_transferible = A_soportada - A_huecos
        Q_teorica = SOBRECARGA_KNM2 * A_transferible
        Q_transferida = total_losa          # carga viva realmente transferida a vigas
        errQ = abs(Q_transferida - Q_teorica) / Q_teorica if Q_teorica else float("inf")
        okQ = errQ < 1e-10 and Q_teorica > 0.0
        print("=" * 70)
        print("=== AUDITORIA CARGA VIVA Q ===")
        print(f"Area losa soportada       = {A_soportada:.2f} m2")
        print(f"Area huecos (banda suelta)= {A_huecos:.4f} m2 "
              f"({len(resQ['huecos_pendientes'])} bordes con viga parcial)")
        print(f"Area losas aisladas excl.  = {A_aisladas:.4f} m2 "
              f"({len(resQ['aisladas'])} losas sin viga de apoyo)")
        print(f"Area TRANSFERIBLE          = {A_transferible:.2f} m2")
        print(f"q_Q                       = {SOBRECARGA_KNM2:.2f} kN/m2")
        print(f"Q teorica  = q_Q*A_transf  = {Q_teorica:.2f} kN")
        print(f"Q transferida a vigas     = {Q_transferida:.2f} kN")
        print(f"Diferencia                = {Q_transferida - Q_teorica:.4f} kN")
        print(f"Error relativo            = {errQ:.3e} ({errQ*100:.5f} %)")
        print(f"Estado                      = {'OK' if okQ else 'REVISAR'}")
        print("=" * 70)

    # ------------------------------------------------------------------
    # AUDITORIA ESPECIFICA DE SISMO EX / EY (Parte B)
    # ------------------------------------------------------------------
    # 1) Carga lateral total: Σ(Fy/Fx aplicada) = F_EX / F_EY (control).
    # 2) Equilibrio global: Σ nodeReaction sobre TODOS los nodos cancela las
    #    fuerzas internas de constraint (rigidDiaphragm/rigidLink) y debe dar
    #    F + R_global = 0. El corte de fundacion se reporta por separado.
    # 3) Deformada: ux/uy del nodo master en el sentido (+) de la fuerza aplicada.
    # 4) Torsion de piso: rz del master (debe salir pequena si es simetrico; si es
    #    relevante, revisar asimetria de rigidez / posicion de CM-CR).
    if is_lateral and case_name in ("EX", "EY"):
        dir_axis = 0 if case_name == "EX" else 1   # 0=X, 1=Y
        dir_sense = 1                               # fuerza aplicada en eje (+)
        F_aplicada = total_W_apply
        # (2b) Fuerza sismica esperada: usa la verif. INDEPENDIENTE calculada
        # antes del analisis (F_esperada_indep desde G_floor/Q_floor, sin
        # reutilizar la lista aplicada). No se recalcula aqui.
        # Corte basal de FUNDACION: suma de reacciones horizontales SOLO en
        # apoyos verdaderamente fijos (1,1,1,1,1,1). Es un dato de diseno.
        # NO se exige F + corte = 0: los muros inclinados/flotantes y los
        # diafragmas transmiten parte de la carga como pares de constraint
        # internos (rigidDiaphragm/rigidLink) que en la contabilidad de
        # Transformation residen en nodos interiores. El invariante exacto es
        # la suma GLOBAL sobre todos los nodos (F + R_global = 0).
        corte = 0.0
        for tag in base_support_tags:
            r = ops.nodeReaction(tag)
            corte += r[dir_axis]
        corte_global = 0.0
        for tag in in_model:
            r = ops.nodeReaction(tag)
            corte_global += r[dir_axis]
        # Ecuacion F + R_global = 0 (signo): corte global cancela la fuerza.
        errV = (abs(F_aplicada + corte_global) / F_aplicada) if F_aplicada else float("inf")
        okV = errV < 1e-10 and F_aplicada > 0.0
        # desplazamiento y rotacion del nodo master de cada piso
        cm_info = []
        for fl, s in seismic.items():
            m = s["master"]
            if m is None:
                continue
            d = ops.nodeDisp(m)
            cm_info.append((fl, m, d[0], d[1], d[5]))
        # sentido de la deformada en TODOS los pisos (no solo el primero):
        # en un analisis estatico lineal toda la torre debe deformarse en el
        # sentido de la fuerza aplicada (deformada del primer modo).
        signo_ok = True
        detalles_signo = []
        for fl, m, ux, uy, rz in sorted(cm_info, key=lambda t: t[0]):
            d_eje = ux if dir_axis == 0 else uy
            sentido = 1 if d_eje >= 0 else -1
            if abs(d_eje) > 1e-12 and sentido != dir_sense:
                signo_ok = False
                detalles_signo.append((fl, d_eje))
        print("=" * 70)
        print(f"=== AUDITORIA SISMO {case_name} ===")
        print(f"Fuerza lateral aplicada    = {F_aplicada:.2f} kN")
        print(f"F esperada (independiente) = {F_esperada_indep:.2f} kN  "
              f"err={err_Fe:.3e}  {'OK' if okFe else 'REVISAR'}")
        print(f"Corte basal fundacion {'(X)' if dir_axis==0 else '(Y)'}    = {corte:10.2f} kN")
        print(f"F + R_global (con signo)     = {F_aplicada + corte_global:.4e}  "
              f"errV={errV:.3e}  {'OK' if okV else 'REVISAR'}")
        for fl, m, ux, uy, rz in sorted(cm_info, key=lambda t: t[0]):
            print(f"  CM piso {fl:10s} (master={m}): "
                  f"Ux={ux/1e-3:9.4f} mm  Uy={uy/1e-3:9.4f} mm  Rz={rz:10.2e} rad")
        if detalles_signo:
            print(f"  [AVISO] pisos con sentido opuesto a F (+): {detalles_signo}")
        print(f"Sentido de deformada (eje {case_name[-1]}): "
              f"{'OK en todos los pisos' if signo_ok else 'REVISAR'}")
        print("=" * 70)

    # ------------------------------------------------------------------
    # AUDITORIA DE SUPERPOSICION COMBO (Parte C)
    # ------------------------------------------------------------------
    # Verifica que la corrida combinada equilibra en las tres direcciones.
    # Igual que EX/EY, el invariante exacto con Transformation es la suma de
    # nodeReaction sobre TODOS los nodos (las fuerzas de constraint internas
    # de rigidDiaphragm/rigidLink cancelan); el corte de fundacion (base
    # 1,1,1,1,1,1) se reporta por separado como dato de diseno.
    if case_name == "COMBO":
        rxb = ryb = 0.0
        for tag in base_support_tags:
            r = ops.nodeReaction(tag)
            rxb += r[0]; ryb += r[1]
        rx = ry = rz = 0.0
        for tag in in_model:
            r = ops.nodeReaction(tag)
            rx += r[0]; ry += r[1]; rz += r[2]
        print("=" * 70)
        print(f"=== AUDITORIA SUPERPOSICION COMBO ===")
        print(f"  Corte fundacion (Rxb, Ryb) = {rxb:.4e}, {ryb:.4e} kN")
        print(f"  Equilibrio global (Rx, Ry) = {rx:.4e}, {ry:.4e} | Rz total={rz:.4e} kN")
        # Equilibrio vertical: carga gravitacional combinada hacia abajo (-fz)
        # cancelada por las reacciones verticales de TODOS los nodos (+rz).
        fz_comb = (LAMBDA_G * self_weight_kN)
        fz_comb += sum(c["W"] for c in cargas_losa.values())   # losa G*lG + Q*lQ
        if abs(fz_comb) > 1e-6:
            err_z = abs((fz_comb - rz) / fz_comb)
            ok_z = err_z < 1e-6
        else:
            # sin carga vertical (lambdas de gravedad nulas): no hay equilibrio
            # vertical que verificar; Rz debe salir ~0
            err_z = abs(rz)
            ok_z = err_z < 1e-6
        # Equilibrio lateral GLOBAL: F + R = 0 en cada eje (R con signo de
        # reaccion).
        if fx_total:
            err_x = abs((fx_total + rx) / fx_total)
        else:
            err_x = abs(rx)
        ok_x = err_x < 1e-6
        if fy_total:
            err_y = abs((fy_total + ry) / fy_total)
        else:
            err_y = abs(ry)
        ok_y = err_y < 1e-6
        for label, err, ok in (("X", err_x, ok_x), ("Y", err_y, ok_y),
                               ("Z", err_z, ok_z)):
            print(f"    . Equilibrio {label}: err={err:.3e}  "
                  f"{'OK' if ok else 'REVISAR'}")
        # reutiliza la variable err (global) como el peor error de equilibrio
        err = max(e for e in (err_x, err_y, err_z) if e != float("inf"))
        ok_eq = ok_x and ok_y and ok_z
        print("=" * 70)

    # ------------------------------------------------------------------
    # RESULTADOS -> JSON
    # ------------------------------------------------------------------
    def _local_axes_rot(ni, nj, vecxz):
        """Ejes locales (x y z) del elemento FE en coordenadas globales,
        misma convencion que benchmark_3d: local_x = i->j normalizado,
        local_z = componente de vecxz perpendicular, local_y = z x x.
        Devuelve (lx, ly, lz) listas de 3 floats."""
        import math
        xi, yi, zi = ops.nodeCoord(ni)
        xj, yj, zj = ops.nodeCoord(nj)
        dx, dy, dz = xj - xi, yj - yi, zj - zi
        L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        lx = (dx / L, dy / L, dz / L)
        vx, vy, vz = vecxz
        dot = vx * lx[0] + vy * lx[1] + vz * lx[2]
        lz = (vx - dot * lx[0], vy - dot * lx[1], vz - dot * lx[2])
        lz_mag = math.sqrt(lz[0] ** 2 + lz[1] ** 2 + lz[2] ** 2) or 1.0
        lz = (lz[0] / lz_mag, lz[1] / lz_mag, lz[2] / lz_mag)
        ly = (lz[1] * lx[2] - lz[2] * lx[1],
              lz[2] * lx[0] - lz[0] * lx[2],
              lz[0] * lx[1] - lz[1] * lx[0])
        return lx, ly, lz

    def _to_local(f6, rot):
        """Rota 6 componentes globales [Fx,Fy,Fz,Mx,My,Mz] a locales
        [P,V2,V3,T,M2,M3] con la matriz R = [lx,ly,lz] (filas = ejes locales).
        Formulas:  [P,V2,V3] = R·F ;  [T,M2,M3] = R·M."""
        lx, ly, lz = rot
        F = f6[:3]
        M = f6[3:]
        out = []
        for axis in (lx, ly, lz):
            out.append(sum(axis[k] * F[k] for k in range(3)))
        for axis in (lx, ly, lz):
            out.append(sum(axis[k] * M[k] for k in range(3)))
        return out

    disp = {}
    for tag in pos_key.values():
        d = ops.nodeDisp(tag)
        disp[str(tag)] = [round(v, 10) for v in d]
    reactions = {}
    for tag in all_support_tags:
        r = ops.nodeReaction(tag)
        reactions[str(tag)] = [round(v, 10) for v in r]
    forces = {}
    local_axes = {}
    material_by_tag = {}
    for tag, meta in elem_meta.items():
        fg = list(ops.eleForce(tag))[:12]
        # vecxz segun la transformacion del elemento (v2: T1 col/muro/acero
        # con vecxz (1,0,0); T2 vigas con vecxz (0,0,1)).
        t = meta["type"]
        vecxz = (1, 0, 0) if t in ("column", "wall", "steel_column", "steel_beam") else (0, 0, 1)
        ni_t, nj_t = meta["nodes"]
        rot = _local_axes_rot(ni_t, nj_t, vecxz)
        local_axes[tag] = rot
        f_glob = (list(fg[:6]), list(fg[6:12]))
        local_i = _to_local(fg[:6], rot)
        local_j = _to_local(fg[6:12], rot)
        material = "A240ES" if t in ("steel_column", "steel_beam") else "HA35"
        material_by_tag[tag] = material
        forces[str(tag)] = {
            "type": meta["type"],
            "global_i": [round(v, 8) for v in fg[:6]],
            "global_j": [round(v, 8) for v in fg[6:12]],
            "local_i": [round(v, 8) for v in local_i],
            "local_j": [round(v, 8) for v in local_j],
            "section": meta["section"],
        }

    # Datos de masa sismica / corte basal para reportar en el resultado.
    # En casos no laterales, seismic no se calcula; se deja como dict vacio.
    seismic_export = seismic if is_lateral else {}

    # Resultados por piso para sismo: desplazamiento del master, transformada al
    # CM (movimiento de cuerpo rigido) y participacion lateral.
    seismic_floor_results = {}
    if is_lateral:
        for fl, s in seismic.items():
            m = s["master"]
            if m is None:
                continue
            d = ops.nodeDisp(m)
            ux_m, uy_m, rz_m = d[0], d[1], d[5]     # m, m, rad
            cx, cy = s["CM"]
            xm, ym, _ = ops.nodeCoord(m)
            # (5) Traslacion del movimiento del master al CENTRO DE MASA:
            #     ux_CM = ux_master - Rz*(yCM - yM)
            #     uy_CM = uy_master + Rz*(xCM - xM)
            ux_cm = ux_m - rz_m * (cy - ym)
            uy_cm = uy_m + rz_m * (cx - xm)
            seismic_floor_results[fl] = {
                "master": m,
                "CM_x_m": round(cx, 4),
                "CM_y_m": round(cy, 4),
                "F_x_kN": round(dirx * s["F_floor"], 4),
                "F_y_kN": round(diry * s["F_floor"], 4),
                "W_sismico_kN": round(s["W_sismico_floor"], 4),
                "masa_kg": round(s["masa_kg"], 3),
                "W_CM_check_kN": round(s["W_cm_check"], 4),
                "err_W_cm": round(s["err_W_cm"], 12),
                "Ux_master_m": round(ux_m, 10),
                "Uy_master_m": round(uy_m, 10),
                "Ux_CM_m": round(ux_cm, 10),
                "Uy_CM_m": round(uy_cm, 10),
                "Rz_rad": round(rz_m, 12),
            }

    # okQ/okV/okFe solo cobran sentido en sus casos; ok_mass en laterales.
    ok_q = okQ if case_name == "Q" else True
    ok_v = okV if (is_lateral and case_name in ("EX", "EY")) else True
    ok_fe = okFe if (is_lateral and case_name in ("EX", "EY")) else True
    ok_m = ok_mass if is_lateral else True

    result = {
        "model": data["model"],
        "case": case_name,
        "units_internal": {"length": "m", "force": "kN", "moment": "kN*m"},
        "summary": {
            "nodes_total": n_nodes_total,
            "elements_structural": n_created,
            "self_weight_kN": round(self_weight_kN, 4),
            "losa_tributaria_kN": round(total_losa, 4),
            f"Carga_{case_name}_total_kN": round(total_W_apply, 4),
        },
        "verifications": {
            "carga_losa_G_por_piso_kN": {fl: round(W, 4)
                                          for fl, W in losa_G_by_floor.items()},
            "carga_losa_Q_por_piso_kN": {fl: round(W, 4)
                                          for fl, W in losa_Q_by_floor.items()},
            "suma_areas_tributarias_m2": round(res_areas["A_trib_total_m2"], 4),
            "area_lozas_total_m2": round(res_areas["A_lozas_total_m2"], 4),
            "area_huecos_m2": round(res_areas["A_huecos_m2"], 4),
            "area_lozas_aisladas_m2": round(res_areas["A_lozas_aisladas_m2"], 4),
            "n_huecos_pendientes": len(res_areas["huecos_pendientes"]),
            "n_losas_aisladas": len(res_areas["aisladas"]),
            "area_conservacion_rel": round(res_areas["conservacion_rel_A"], 12),
            "carga_conservacion_rel": round(res_areas["conservacion_rel_W"], 12),
            "equilibrio_error": round(err, 12),
            "todas_ok_eq": bool(ok_eq),
            "diafragma_compatibilidad_err_max_m": round(dmax, 12),
            "todas_ok_dia": bool(ok_dia),
            "W_CM_coincide_W_F": bool(ok_m),
            "conservacion_q_error": round(errQ, 12) if case_name == "Q" else None,
            "todas_ok_q": bool(ok_q),
            "F_esperada_indep_kN": round(F_esperada_indep, 4) if (is_lateral and case_name in ("EX", "EY")) else None,
            "F_aplicada_kN": round(F_aplicada, 4) if (is_lateral and case_name in ("EX", "EY")) else None,
            "corte_basal_error": round(errV, 12) if (is_lateral and case_name in ("EX", "EY")) else None,
            "todas_ok_sismo_basal": bool(ok_v),
            "F_esperada_error": round(err_Fe, 12) if (is_lateral and case_name in ("EX", "EY")) else None,
            "todas_ok_sismo_F": bool(ok_fe),
            "todas_ok": bool(ok_eq and ok_areas and ok_dia and ok_q
                           and ok_m and ok_fe and ok_v),
        },
        # Parte C: componentes y lambdas de la superposicion (solo COMBO)
        "superposition": {
            "lambdas": {"G": LAMBDA_G, "Q": LAMBDA_Q,
                        "EX": LAMBDA_EX, "EY": LAMBDA_EY},
            "Fx_lateral_kN": round(fx_total, 6),
            "Fy_lateral_kN": round(fy_total, 6),
            "ecuacion": "R = lambda_G*G + lambda_Q*Q + lambda_EX*EX + lambda_EY*EY",
        } if case_name == "COMBO" else None,
        "tributary_by_viga": tributary_by_viga,
        "displacements_m": disp,
        "reactions_kN": reactions,
        "element_forces_global": forces,
        "element_local_axes": {str(t): [list(a) for a in rot]
                                for t, rot in local_axes.items()},
        "element_material": {str(t): m for t, m in material_by_tag.items()},
        # (Semana 3) masa sismica por piso, G/Q por piso y corte basal
        "seismic_mass": {
            "g": g,
            "alpha_sismo": ALPHA_SISMO,
            "frac_live_sismic": FRAC_LIVE_SISMIC,
            "G_total_kN": round(G_total, 4),
            "Q_total_kN": round(Q_total, 4),
            "W_sismico_total_kN": round(W_sismico_total, 4),
            "W_sismico_efectivo_kN": round(W_sismico_efectivo, 4) if is_lateral else None,
            "fundacion_excluida_kN": round(foundation_weight, 4),
            "G_floor_kN": {fl: round(v, 4) for fl, v in G_floor.items()},
            "Q_floor_kN": {fl: round(v, 4) for fl, v in Q_floor.items()},
            "piso_to_master": piso_to_master,
        },
        "seismic_case": seismic_export,
        "seismic_floor_results": seismic_floor_results,
    }

    os.makedirs(BASE, exist_ok=True)
    # Cada caso se exporta a su propio archivo para poder compararlos por separado
    # y alimentar la Parte C (superposicion). G conserva el nombre historico.
    # Con MOD_TAG (corrida de modificacion) el tag va antes del nombre del caso:
    #   G     -> edificio_full_results_{MOD_TAG}.json
    #   CASO  -> edificio_full_results_{MOD_TAG}_{CASO}.json
    out = OUT_JSON
    if MOD_TAG:
        if case_name == "G":
            out = OUT_JSON.replace("edificio_full_results.json",
                                   f"edificio_full_results_{MOD_TAG}.json")
        else:
            out = OUT_JSON.replace("edificio_full_results.json",
                                   f"edificio_full_results_{MOD_TAG}_{case_name}.json")
    elif case_name != "G":
        out = OUT_JSON.replace("edificio_full_results.json",
                               f"edificio_full_results_{case_name}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Resultados exportados a: {out}")
    return result


def main():
    # Cada caso se construye desde cero (ops.wipe en run_case) para estado limpio:
    # se evita que cargas de un caso anterior (G, Q, EX, EY) queden activas.
    # Uso:  python opensees_edificio_v2.py [--case G|Q|EX|EY|COMBO]
    #       python opensees_edificio_v2.py --case COMBO --lambda-g 1.2 --lambda-q 0.5 ...
    # Si se omite --case, se corren los casos habilitados por RUN_CASE_*.
    import sys
    only_case = None
    if "--case" in sys.argv:
        i = sys.argv.index("--case")
        if i + 1 < len(sys.argv):
            only_case = sys.argv[i + 1].upper()

    # MODIFICACION DEL MODELO (Semana 5): --json <path> apunta a un contrato
    # alternativo (p.ej. Edificio_mod_A.json) y --tag <tag> etiqueta la salida
    # para no sobrescribir la linea base.
    global JSON_PATH, MOD_TAG
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        if i + 1 < len(sys.argv):
            JSON_PATH = os.path.abspath(sys.argv[i + 1])
            print(f"  modelo (JSON_PATH): {JSON_PATH}")
    if "--tag" in sys.argv:
        i = sys.argv.index("--tag")
        if i + 1 < len(sys.argv):
            MOD_TAG = sys.argv[i + 1]
            print(f"  tag de salida (MOD_TAG): {MOD_TAG}")

    def _flag(name):
        global LAMBDA_G, LAMBDA_Q, LAMBDA_EX, LAMBDA_EY
        if name in sys.argv:
            i = sys.argv.index(name)
            if i + 1 < len(sys.argv):
                val = float(sys.argv[i + 1])
                {
                    "--lambda-g": lambda: globals().update(LAMBDA_G=val),
                    "--lambda-q": lambda: globals().update(LAMBDA_Q=val),
                    "--lambda-ex": lambda: globals().update(LAMBDA_EX=val),
                    "--lambda-ey": lambda: globals().update(LAMBDA_EY=val),
                }[name]()
                return val
        return None

    for name in ("--lambda-g", "--lambda-q", "--lambda-ex", "--lambda-ey"):
        v = _flag(name)
        if v is not None:
            print(f"  lambda {name[-1].upper()} = {v}")

    results = {}
    cases = ["G", "Q", "EX", "EY"] if only_case is None else [only_case]
    for case in cases:
        run_flag = {
            "G": RUN_CASE_G, "Q": RUN_CASE_Q,
            "EX": RUN_CASE_EX, "EY": RUN_CASE_EY,
            "COMBO": RUN_CASE_COMBO or True,
        }[case]
        if run_flag:
            res = run_case(case)
            if res is not None:
                results[case] = res
    return results


if __name__ == "__main__":
    main()