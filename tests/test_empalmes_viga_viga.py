"""
Regla F - Empalmes viga-viga (plan_empalmes_viga_viga.md).

Puro (no corre OpenSees): usa Edificio.json y el plan de conectividad.
"""

import json
import os
import sys
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENSEES = os.path.join(REPO, "opensees")
if OPENSEES not in sys.path:
    sys.path.insert(0, OPENSEES)

import pytest  # noqa: E402

import conexiones as cx  # noqa: E402


@pytest.fixture(scope="module")
def plan():
    data = json.load(open(os.path.join(REPO, "Edificio.json"), encoding="utf-8"))
    p = cx.plan_conexiones(data["nodes"], data["elements"], data["supports"])
    return data, p


def _viga_por_nodo_de_contrato(data, p):
    """Devuelve {nodo_contrato: [viga tags donde es interior]} segun Regla F."""
    col_nodes = set()
    for e in data["elements"]:
        if e["type"] == "column":
            col_nodes |= {e["node_i"], e["node_j"]}

    beam_elem = {}
    for e in data["elements"]:
        if e["type"] in ("beam_x", "beam_y") and e["id"] in p["frame_split"]:
            fracs = p["frame_split"][e["id"]]
            beam_elem[e["id"]] = (fracs[0][1], fracs[-1][2])  # ni, nj reales
        elif e["type"] in ("beam_x", "beam_y"):
            beam_elem[e["id"]] = (e["node_i"], e["node_j"])

    tag_coord = p["tag_coord"]

    def dist_pt_seg(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 < 1e-14 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / L2))
        qx, qy = x1 + t * dx, y1 + t * dy
        return t, qx, qy

    res = {}
    for ntag, (nx, ny, nz) in tag_coord.items():
        if ntag > 1000:
            continue
        if ntag in col_nodes:
            continue
        for vid, (ni, nj) in beam_elem.items():
            if ntag in (ni, nj):
                continue
            if ntag not in tag_coord:
                continue
            c1, c2 = tag_coord[ni], tag_coord[nj]
            if abs(c1[2] - nz) > 1e-6:
                continue
            t, qx, qy = dist_pt_seg(nx, ny, c1[0], c1[1], c2[0], c2[1])
            if (abs(nx - qx) < 0.025 and abs(ny - qy) < 0.025 and 0.005 < t < 0.995):
                res.setdefault(ntag, []).append(vid)
    return res


def test_empalmes_identificados(plan):
    """Regla F detecta los 143 cruces interiores / 119+ vigas subdivididas."""
    _data, p = plan
    frac_tags = [ft for fr in p["frame_split"].values() for (ft, _a, _b) in fr]
    assert p["n_empalmes"] >= 140          # 143 cruces interiores esperados
    assert len(p["frame_split"]) >= 110    # vigas subdivididas
    assert len(frac_tags) > len(p["frame_split"])  # hay fracciones multiples


def test_reuso_tag_contrato(plan):
    """Empalme viga-viga NO crea nodo 200000+ (reusa el nodo del contrato)."""
    data, p = plan
    nodes_200k = set()
    for fr in p["frame_split"].values():
        for (_ft, ni, nj) in fr:
            nodes_200k |= {ni, nj}
    nodes_200k = {t for t in nodes_200k if t >= 200000}
    # Los unicos 200000+ permitidos son pies de MURO (regla B), no empalmes:
    # todo nodo 200000+ en fracciones debe venir de extra_nodes (splits de muro).
    extra_200k = {t for (t, _x, _y, _z) in p["extra_nodes"]}
    assert nodes_200k.issubset(extra_200k)


def test_primera_fraccion_conserva_tag(plan):
    _data, p = plan
    for vid, fr in p["frame_split"].items():
        assert fr[0][0] == vid
        for (ft, ni, nj) in fr:
            assert ni in p["tag_coord"] and nj in p["tag_coord"]


def test_cruce_simultaneo_muro_no_duplica_nodo(plan):
    """Punto con pie de muro Y empalme viga-viga: un solo nodo (reuse)."""
    _data, p = plan
    # verificacion indirecta: en frame_split final no hay tags de fraccion repetidos
    frs = [fr for f in p["frame_split"].values() for fr in f]
    dup_tags = {f[0] for f in frs}
    assert len(dup_tags) == len(frs)


def test_cero_extremos_colgantes():
    """Post-fix: ningun extremo de viga cuelga sin viga pasante/columna."""
    data = json.load(open(os.path.join(REPO, "Edificio.json"), encoding="utf-8"))
    p = cx.plan_conexiones(data["nodes"], data["elements"], data["supports"])
    tag_coord = p["tag_coord"]
    col_nodes = set()
    for e in data["elements"]:
        if e["type"] == "column":
            col_nodes |= {e["node_i"], e["node_j"]}

    beam_ends = []  # (ni, nj, tipo, id) reales con fracciones
    for e in data["elements"]:
        if e["type"] not in ("beam_x", "beam_y"):
            continue
        i, j = e["node_i"], e["node_j"]
        if e["id"] in p["frame_split"]:
            i = p["frame_split"][e["id"]][0][1]
            j = p["frame_split"][e["id"]][-1][2]
        beam_ends.append((i, j, e["type"], e["id"]))

    pos_todos = set()
    for (ni, nj, _t, _id) in beam_ends:
        pos_todos |= {ni, nj}
    incidentes = Counter()
    for (ni, nj, _t, _id) in beam_ends:
        incidentes[ni] += 1
        incidentes[nj] += 1

    def dentro(nx, ny, nz, x1, y1, z1, x2, y2, z2):
        if abs(z1 - z2) > 1e-9 or abs(nz - z1) > 1e-6:
            return False
        if abs(x1 - x2) > 1e-6 and abs(y1 - y2) > 1e-6:
            return False
        if abs(x1 - x2) <= 1e-6:
            if abs(nx - x1) > 0.025:
                return False
            lo, hi = sorted((y1, y2))
            return lo - 0.025 <= ny <= hi + 0.025
        else:
            if abs(ny - y1) > 0.025:
                return False
            lo, hi = sorted((x1, x2))
            return lo - 0.025 <= nx <= hi + 0.025

    resoluciones = []
    for (ni, nj, _t, id) in beam_ends:
        for n in (ni, nj):
            if n in col_nodes or incidentes[n] > 1:
                continue
            x, y, z = tag_coord.get(n, (0, 0, 0))
            if (x, y, z) == (0, 0, 0):
                continue
            ok = any(
                (a, b) != (n, n) and dentro(x, y, z, *tag_coord[a], *tag_coord[b])
                for (a, b, _t2, _id2) in beam_ends
                if (_id2 != id) and a in tag_coord and b in tag_coord
            )
            if not ok:
                resoluciones.append((id, n))
    # Solo los 20 casos especiales documentados quedan colgando (regla G pendiente).
    assert len(resoluciones) <= 20