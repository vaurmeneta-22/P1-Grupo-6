"""
FASE 3 - Test del verificador mecanico de camino de carga.

Usa unicamente Edificio.json y el JSON G ya exportado (no corre OpenSees),
igual que test_superposicion.py.
"""

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENSEES = os.path.join(REPO, "opensees")
RESULTS = os.path.join(REPO, "resultados", "01_casos_base")
if OPENSEES not in sys.path:
    sys.path.insert(0, OPENSEES)

import pytest  # noqa: E402

import verificador_camino_carga as vf  # noqa: E402


@pytest.fixture(scope="module")
def guess():
    with open(os.path.join(REPO, "Edificio.json"), encoding="utf-8") as f:
        data = json.load(f)
    gpath = os.path.join(RESULTS, "edificio_full_results.json")
    forces = None
    anchors = None
    if os.path.exists(gpath):
        with open(gpath, encoding="utf-8") as f:
            rjson = json.load(f)
        forces = rjson.get("element_forces_global")
        anchors = {int(k) for k in rjson.get("reactions_kN", {})}
    if forces is None:
        pytest.skip("no hay edificio_full_results.json (correr opensees_edificio_v2.py)")
    ok, rep = vf.verificar(data, forces, anchors=anchors)
    return data, ok, rep


def test_fases_completas(guess):
    data, ok, rep = guess
    assert rep["n_sin_camino"] == 0
    assert rep["n_flotantes"] == 0
    assert ok


def test_grafo_aterrizado(guess):
    data, ok, rep = guess
    assert rep["nodos_grafo"] > 400
    assert rep["nodos_fundacion"] >= 50          # apoyos de contrato fijos en el grafo
    # anclas = fundacion + piso_vertical/flotantes en el grafo. Tras liberar los
    # suelos artificiales de la regla 7b (BFS v2 + Regla G) el valor real es ~79;
    # se fija un piso amplio (>= 60) que solo garantiza "muchos apoyos" sin ser
    # fragil ante futuras idealizaciones del apoyo vertical.
    assert rep["nodos_ancla"] >= 60


def test_muros_participan_axialmente(guess):
    data, ok, rep = guess
    assert rep["n_muros_nula"] == 0
    assert rep["n_muros"] >= 70