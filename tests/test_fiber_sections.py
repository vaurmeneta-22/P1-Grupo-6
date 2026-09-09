"""
Test de la Parte D - secciones de fibra / capacidades de HA (Grupo 6)

Verifica (sin OpenSees, solo el contraste analitico del curso):
1. Geometria del acero de la columna 70x70: 8 phi25, Ast esperada.
2. Geometria del muro 30x356: bordes 4phi16 + malla phi10@20 doble.
3. Capacidad axial pura P0 (bloque ACI/NCh) dentro de rango fisico.
4. Momento balanceado > momento en flexio'n pura (columna).
5. La curva P-M del bloque: P creciente, M con pico interior.
6. Consistencia dimensiones: areas y recubrimientos razonables.
"""

import math

from opensees.fiber_sections import sections, verification_ha as vh

ABAR25 = math.pi * (25.0 / 2.0) ** 2


def test_columna_areas():
    b, h, barras, Ast = vh.seccion_columna()
    assert b == 700.0 and h == 700.0
    n = sum(int(round(a / ABAR25)) for _, a in barras)
    assert n == 8                       # 3+2+3 barras phi25
    esperada = 8 * ABAR25
    assert math.isclose(Ast, esperada, rel_tol=1e-9)
    # recubrimiento de las guas: todas dentro de la seccion
    for di, _ in barras:
        assert 0 < di < h
    # misma geometria la reporta sections.py
    assert sections.COLUMNA["barras"] == 8
    assert sections.COLUMNA["db"] == 25.0


def test_muro_areas():
    bw, Lw, bars, Ast = vh.seccion_muro()
    assert bw == 300.0 and Lw == 3560.0
    # bordes: 4 phi16 por borde
    As_borde = 4 * math.pi * (16.0 / 2.0) ** 2
    As_malla_esperada = 0.0
    for di, a in bars:
        if di in (50.0, Lw - 50.0):
            continue
        As_malla_esperada += a
    assert math.isclose(Ast, 2 * As_borde + As_malla_esperada, rel_tol=1e-9)
    # refuerzo distribuido de malla: varias posiciones entre los bordes
    interiores = [di for di, _ in bars if 50.0 < di < Lw - 50.0]
    assert len(interiores) >= 10
    # la configuracion del module sections coincide con la del enunciado
    assert sections.MURO["db_borde"] == 16.0
    assert sections.MURO["nb_borde"] == 4


def test_capacidad_axial_pura():
    P0_col = vh.capacidad_pura_axial(True)
    P0_mur = vh.capacidad_pura_axial(False)
    # rango fisico: ~0.85 f'c Ag (con aporte de acero)
    fcc = 0.85 * 35.0
    ag_col = sections.area_concreto(sections.COLUMNA)
    ag_mur = sections.area_concreto(sections.MURO)
    assert P0_col * 1e3 / (fcc * ag_col) > 1.0     # incluye As.fy
    assert P0_mur * 1e3 / (fcc * ag_mur) > 1.0
    # el muro tiene mucho mas capacidad axial que la columna
    assert P0_mur > P0_col


def test_momento_balanceado_supera_flexion_pura():
    P, M = vh.interaccion(True)
    # momento en flexion pura (P mas cercano a 0)
    ip = min(range(len(P)), key=lambda k: abs(P[k]))
    M_pura = M[ip]
    Pb, Mb = vh.punto_momento_balanceado(True)
    assert Mb > M_pura             # el pico de la curva esta hacia la compresion
    assert Pb > 4000 and Pb < 10000   # orden de los 6331 kN esperados


def test_curva_pm_bloque():
    P, M = vh.interaccion(True)
    assert len(P) == len(M) >= 100
    # P monotona creciente y positiva
    assert all(b > a for a, b in zip(P, P[1:]))
    assert P[0] > -2000 and P[-1] > 1e4
    # M > 0 en el interior y pico unico (sube y luego baja)
    ip = int(max(range(len(M)), key=lambda k: M[k]))
    assert all(M[k] <= M[k + 1] for k in range(ip))
    assert all(M[k] >= M[k + 1] for k in range(ip, len(M) - 1))
    # la curva es util: en el tramo medio M sustancial
    assert max(M) > 1000


def test_mom_curv_p0_resultado():
    """Compare con la salida guardada (rapida, sin opensees)."""
    import json
    import os
    ruta = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "figures", "mom_curv_columna_70x70.json")
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    assert len(datos["phi_1m"]) == len(datos["M_kNm"]) > 100
    assert datos["M_ult_kNm"] > 300 and datos["M_ult_kNm"] < 900
    Mmax = max(datos["M_kNm"])
    # orden tipico de capacidad de flexion de la columna 70x70 (kN*m)
    assert 400 < Mmax < 900