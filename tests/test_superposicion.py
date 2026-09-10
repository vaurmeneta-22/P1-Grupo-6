"""
Tests de la Parte C — SUPERPOSICION  R = lambda_G*G + lambda_Q*Q
                                        + lambda_EX*EX + lambda_EY*EY

Verifica la combinacion DIRECTA de los JSON de casos base contra la corrida
EXPLICITA OpenSees del caso COMBO (sin depender de pytest-Graphics):

 1. combine() == suma ponderada componente a componente de los resultados.
 2. compare_maps(): errores por norma por debajo de TOL = 1e-6 en
    desplazamientos, reacciones y fuerzas internas, usando el COMBO explícito
    ya exportado por `superposicion.py` en `results/`.
 3. combine() coincide con los resultados individuales cuando se toma una
    sola lambda = 1.0 (reproducibilidad del caso base con λ isolectivas).
 4. Simetria lineal: lam(EX)=1, lam(EY)=0 reproduce el caso EX (hasta
    redondeo de la exportación a 1e-10/1e-8).

Los test 2-4 usan los JSON de resultados ya corridos localmente; si el COMBO
explícito no existe se omite (skipped) excepto el test 1 que es puramente
composicional.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENSEES = os.path.join(REPO, "opensees")
RESULTS = os.path.join(OPENSEES, "results")
if OPENSEES not in sys.path:
    sys.path.insert(0, OPENSEES)

import superposicion as sp

TOL = 1e-6

CASES = ["G", "Q", "EX", "EY"]
LAM = {"G": 1.0, "Q": 1.0, "EX": 1.0, "EY": 1.0}

_FILES = {"G": "edificio_full_results.json",
          "Q": "edificio_full_results_Q.json",
          "EX": "edificio_full_results_EX.json",
          "EY": "edificio_full_results_EY.json"}


def _load(case):
    import json
    with open(os.path.join(RESULTS, _FILES[case]), encoding="utf-8") as f:
        return json.load(f)


def _loads():
    return {c: _load(c) for c in CASES}


# ---------------------------------------------------------------------------
# 1) combine(): suma ponderada componente a componente (algebraica)
# ---------------------------------------------------------------------------
def test_combine_es_suma_ponderada():
    import pytest
    reps = {c: {"displacements_m": {10: [g * (i + 1) / 1e3 for i in range(6)],
                                    20: [2 * g * (i + 1) / 1e3 for i in range(6)]},
                "reactions_kN": {1: [3 * g * (i + 1) for i in range(6)]},
                "element_forces_global": {100: {"global_i": [4 * g * (i + 1)
                                                             for i in range(6)]}}}
            for g_idx, (c, g) in enumerate(zip(CASES, [1, 2, 3, 4]))}
    lams = {"G": 1.2, "Q": 0.5, "EX": 0.3, "EY": 0.0}
    combo = sp.combine(lams, CASES, data=reps)
    # nodo 10, gdl 0: 1.2*1e-3 + 0.5*2e-3 + 0.3*3e-3 + 0.0*4e-3 = 3.1e-3
    assert combo["displacements_m"][10][0] == pytest.approx(3.1e-3, abs=1e-12)
    # apoyo 1, gdl 5: 1.2*18 + 0.5*36 + 0.3*54 + 0.0*72 = 55.8
    assert combo["reactions_kN"][1][5] == pytest.approx(55.8, abs=1e-12)

    assert combo["_lambdas"] == lams
    assert combo["_load_cases"] == CASES
    # conserva los tags completos (misma clave -> misma suma, no merge parcial)
    assert set(combo["displacements_m"]) == {10, 20}


# ---------------------------------------------------------------------------
# 2) compare_maps: norma relativa < TOL en los tres campos (COMBO explícito)
# ---------------------------------------------------------------------------
def test_comparacion_explicita_directa_tolerancias():
    import pytest
    expl_path = os.path.join(RESULTS, "edificio_full_results_COMBO.json")
    if not os.path.exists(expl_path):
        pytest.skip("COMBO explicito no corrido aun: ejecutar superposicion.py")

    import json
    with open(expl_path, encoding="utf-8") as f:
        expl = json.load(f)

    # usa las lambdas con que se corrio el EXPLICITO (guardadas en el JSON):
    # el test es robusto a cualquier combinacion guardada en disco.
    lams = expl["superposition"]["lambdas"]
    combo = sp.combine(lams, CASES, data=_loads())

    maps = [
        ("desplazamiento",
         combo["displacements_m"], expl["displacements_m"]),
        ("reaccion",
         combo["reactions_kN"], expl["reactions_kN"]),
        ("fuerza", sp.forces_map(combo), sp.forces_map(expl)),
    ]
    for label, a, b in maps:
        me, n, _, _ = sp.compare_maps(a, b, None, 6)
        assert me < TOL, f"{label}: err={me:.3e} >= TOL"
        # se comparan TODAS las claves del resultado explicito (los sets de
        # tags deben coincidir 1:1; el umbral fijo >100 quedo obsoleto cuando
        # los suelos artificiales se liberaron y reactions_kN bajo a ~99).
        assert n == len(b), f"{label}: solo {n}/{len(b)} claves comparadas"


# ---------------------------------------------------------------------------
# 3) una sola lambda = 1 reproduce el caso base individual
# ---------------------------------------------------------------------------
def test_combinacion_solo_G_reproduce_caso_G():
    import pytest
    g = _load("G")
    only = {"G": 1.0, "Q": 0.0, "EX": 0.0, "EY": 0.0}
    combo = sp.combine(only, CASES, data=_loads())
    me, n, _, _ = sp.compare_maps(combo["displacements_m"],
                                  g["displacements_m"], None, 6)
    assert me < 1e-8, f"G solo: disp err={me:.3e}"
    assert n == len(g["displacements_m"])


# ---------------------------------------------------------------------------
# 4) solo EX reproduce el caso EX (isoleccion del sismo X)
# ---------------------------------------------------------------------------
def test_combinacion_solo_EX_reproduce_caso_EX():
    import pytest
    ex = _load("EX")
    only = {"G": 0.0, "Q": 0.0, "EX": 1.0, "EY": 0.0}
    combo = sp.combine(only, CASES, data=_loads())
    for label, a, b in [("disp", combo["displacements_m"], ex["displacements_m"]),
                        ("react", combo["reactions_kN"], ex["reactions_kN"])]:
        me, n, _, _ = sp.compare_maps(a, b, None, 6)
        assert me < 1e-8, f"EX solo: {label} err={me:.3e}"
        assert n == len(b), f"EX solo: {label}: solo {n}/{len(b)} claves comparadas"


if __name__ == "__main__":
    for name in sorted(k for k in globals() if k.startswith("test_")):
        try:
            globals()[name]()
            print(f"[OK] {name}")
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {name}: {e}")