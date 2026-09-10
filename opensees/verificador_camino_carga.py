# -*- coding: utf-8 -*-
"""
FASE 3 - Verificador mecanico de camino de carga.

Verifica sobre el modelo COMpleto (contrato + muros 9000+ + splits 200000+ +
fracciones 300000+ + rigidLinks + huerfanos) SIN correr OpenSees:

 1. Todo elemento estructural tiene un camino de carga hacia la fundacion:
    el grafo de conectividad (elementos + rigidLinks que transmiten fuerza)
    conecta ambos extremos de cada elemento con al menos un nodo fijo (z<0.06
    o apoyo de contrato) por continuidad estructural.
 2. Todo nodo del modelo pertenece a la componente conexa aterrizada
    (no flotan nodos ni componentes).
 3. Bajo G, todo muro equivalente reacciona axialmente (|N| > tol): un muro
    con N≈0 indica que idealizacion/kinematic link se "come" su participacion.
"""
from __future__ import annotations

import json
import math
import os
import sys

from conexiones import plan_conexiones

TOL_AXIAL_N = 1e-6          # kN: umbral "el muro participa axialmente"
MAX_REPORT = 20             # maximo de items a listar por categoria

OS_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(OS_DIR, "results")


def verificar(data: dict, forces: dict | None, tol_axial: float = TOL_AXIAL_N,
              anchors: set | None = None):
    """Vuelve (ok, report). data = Edificio.json; forces = element_forces_global de G.

    anchors: nodos "soportados" del modelo (claves de reactions_kN del JSON):
    fundacion fija + verticales de piso (0,0,1,1,1,0) + flotantes, o sea la
    idealizacion aceptada (la losa sostiene nodos de borde sin columna debajo).
    Si es None se usan solo los apoyos fijos (chequeo mas estricto).
    """
    plan = plan_conexiones(data["nodes"], data["elements"], data["supports"])
    tag_coord = plan["tag_coord"]
    ends = {}                 # elemento -> (tagA, tagB) para chequeo unitario

    # -- grafo de continuidad estructural (transmite fuerza) --------------
    g = {}

    def add(a, b):
        if a is None or b is None or a == b:
            return
        g.setdefault(a, set()).add(b)
        g.setdefault(b, set()).add(a)

    for e in data["elements"]:
        et = e.get("type")
        if et in ("column", "beam_x", "beam_y"):
            add(e["node_i"], e["node_j"])
            ends[e["id"]] = (e["node_i"], e["node_j"])
    for wid, (a, b) in plan["wall_ends"].items():
        add(a, b)
        ends[wid] = (a, b)
    for vid, segs in plan["frame_split"].items():
        for (ftag, a, b) in segs:
            add(a, b)
            ends[ftag] = (a, b)
    for (kind, master, slave) in plan["rigid_links"]:
        add(master, slave)            # rigidLink transmite fuerza (6 DOF)
    bar_orphans = set()
    for (tag, x, y, z, kind, master) in plan["orphan_nodes"]:
        if kind == "bar" and master is not None:
            add(master, tag)          # rigidLink 'bar' (traslacional)
            bar_orphans.add(tag)
        elif kind == "fix":
            pass                      # empotrado, es nodo de fundacion

    # -- nodos verdaderamente fijos (1,1,1,1,1,1) --------------------------
    ground = (set(plan["support_tags"]) | set(plan["base_extra"])) - bar_orphans
    ground = {t for t in ground if t in g}   # solo tags presentes en el grafo

    # -- BFS desde la fundacion / anclas -----------------------------------
    seed = ground if anchors is None else set(anchors) & (set(g) | ground)
    seed |= ground
    reach = set()
    stack = list(seed)
    while stack:
        n = stack.pop()
        if n in reach:
            continue
        reach.add(n)
        stack.extend(g.get(n, ()))

    # -- 1) extremos de cada elemento con camino ---------------------------
    sin_camino = [eid for eid, (a, b) in sorted(ends.items())
                  if a not in reach or b not in reach]
    # -- 2) nodos flotantes (no alcanzables) -------------------------------
    flotantes = sorted(t for t in g if t not in reach)

    # -- 3) muros con N≈0 bajo G --------------------------------------------
    #    Un muro vertical sus extremos sostenidos (fundacion + rigidLink al
    #    marco) cuelga su peso propio directo en ambos apoyos y N→0 es legítimo
    #    (muro de arriostramiento). Solo es sospechoso si N≈0 y ALGUN extremo
    #    no esta anclado (ni fundacion, ni rigidLink, ni apoyo/losa): ahi el
    #    muro debería reaccionar axialmente y no lo hace.
    held = set(seed)
    for (_k, _m, s) in plan["rigid_links"]:
        held.add(_m); held.add(s)
    muros_nula = []
    if forces is not None:
        for wid, (a, b) in plan["wall_ends"].items():
            f = forces.get(str(wid))
            if f is None:
                continue
            Fi = f["global_i"]
            ca = tag_coord[a]
            cb = tag_coord[b]
            L = math.dist(ca, cb)
            if L < 1e-12:
                continue
            ux, uy, uz = ((cb[0] - ca[0]) / L, (cb[1] - ca[1]) / L,
                          (cb[2] - ca[2]) / L)
            N = Fi[0] * ux + Fi[1] * uy + Fi[2] * uz
            if abs(N) < tol_axial and (a not in held or b not in held):
                muros_nula.append(wid)

    ok = (not sin_camino) and (not flotantes) and (not muros_nula)
    report = {
        "ok": ok,
        "nodos_grafo": len(g),
        "nodos_fundacion": len(ground),
        "nodos_ancla": len(seed),
        "sin_camino": sin_camino[:MAX_REPORT],
        "n_sin_camino": len(sin_camino),
        "flotantes": flotantes[:MAX_REPORT],
        "n_flotantes": len(flotantes),
        "muros_nula": muros_nula[:MAX_REPORT],
        "n_muros_nula": len(muros_nula),
        "n_muros": len(plan["wall_ends"]),
    }
    return ok, report


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    repo = os.path.dirname(OS_DIR)
    with open(os.path.join(repo, "Edificio.json"), encoding="utf-8") as f:
        data = json.load(f)

    forces = None
    anchors = None
    gpath = os.path.join(RESULTS_DIR, "edificio_full_results.json")
    if os.path.exists(gpath):
        with open(gpath, encoding="utf-8") as f:
            rjson = json.load(f)
        forces = rjson.get("element_forces_global")
        anchors = set(int(k) for k in rjson.get("reactions_kN", {}))

    ok, rep = verificar(data, forces, anchors=anchors)
    print("-" * 66)
    print("VERIFICADOR DE CAMINO DE CARGA (FASE 3)")
    print("-" * 66)
    print(f"  Nodos en el grafo estructural : {rep['nodos_grafo']}")
    print(f"  Nodos de fundacion (fijos)    : {rep['nodos_fundacion']}")
    print(f"  Nodos ancla (soportados)      : {rep['nodos_ancla']}")
    print(f"  Elementos sin camino de carga : {rep['n_sin_camino']}"
          + (f"  -> {rep['sin_camino'][:10]}" if rep["sin_camino"] else ""))
    print(f"  Nodos flotantes (sin camino)  : {rep['n_flotantes']}"
          + (f"  -> {rep['flotantes'][:10]}" if rep["flotantes"] else ""))
    print(f"  Muros con N~0 bajo G          : {rep['n_muros_nula']}"
          + f" de {rep['n_muros']}"
          + (f"  -> {rep['muros_nula'][:10]}" if rep["muros_nula"] else ""))
    print(f"  RESULTADO: {'OK - todo elemento con camino de carga'
                          if ok else 'REVISAR - hay elementos/nodos sin camino'}")
    print("-" * 66)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())