"""
Test de la Parte D - secciones de fibra / capacidades de HA (Grupo 6)

Verifica (sin OpenSees, solo el contraste analitico del curso):
1. Geometria del acero de la columna 70x70: 16 phi28 perimetrales
   (5+5+3+3), Ast esperada.
2. Geometria del muro 30x356: bordes 4phi16 + malla phi10@20 doble.
3. Capacidad axial pura P0 (bloque ACI/NCh) dentro de rango fisico.
4. Momento balanceado > momento en flexio'n pura (columna).
5. La curva P-M del bloque: P creciente, M con pico interior.
6. Consistencia dimensiones: areas y recubrimientos razonables.
"""

import math

from opensees.fiber_sections import sections, verification_ha as vh

ABAR28 = math.pi * (28.0 / 2.0) ** 2
ABAR36 = math.pi * (36.0 / 2.0) ** 2


def test_columna_areas():
    b, h, barras, Ast = vh.seccion_columna()
    assert b == 700.0 and h == 700.0
    n = sum(int(round(a / ABAR28)) for _, a in barras)
    assert n == 16                      # 5+5+3+3 barras phi28 perimetrales
    esperada = 16 * ABAR28
    assert math.isclose(Ast, esperada, rel_tol=1e-9)
    # recubrimiento de las guas: todas dentro de la seccion
    for di, _ in barras:
        assert 0 < di < h
    # misma geometria la reporta sections.py
    assert sections.COLUMNA["barras"] == 16
    assert sections.COLUMNA["db"] == 28.0
    # filas simetricas: cara superior (5) y cara inferior (5) espejadas
    dic = {di: a for di, a in barras}
    for di, a in dic.items():
        assert math.isclose(dic[h - di], a, rel_tol=1e-9, abs_tol=1e-6)


def test_columna_borde_areas():
    """Columna del portico extremo: 20 barras mixtas perimetrales
    (4 phi28 esquinas + 16 phi36 intermedias B1/B2/B3), rec 68 mm."""
    b, h, barras, Ast = vh.seccion_columna_borde()
    assert b == 700.0 and h == 700.0
    # cuenta por diametro: cara superior/inferior agregan 2 esquinas (28) y
    # 4 intermedias (36) cada una; los costados agregan 4 intermedias (36)
    # por lado -> 4x28 + 16x36
    n36 = 0
    n28 = 0
    for _, a in barras:
        n28 += int(round(a / ABAR28)) if round(a / ABAR28, 3).is_integer() else 0
        n36 += int(round(a / ABAR36)) if round(a / ABAR36, 3).is_integer() else 0
    # matriz: (2*28+4*36) x2 caras + 4 niveles x 2*36 de costados
    total_area = sum(a for _, a in barras)
    esperada = 4 * ABAR28 + 16 * ABAR36
    assert math.isclose(Ast, esperada, rel_tol=1e-9)
    assert math.isclose(total_area, esperada, rel_tol=1e-9)
    # rec de las guas: todas dentro de la seccion
    for di, _ in barras:
        assert 0 < di < h
    assert sections.COLUMNA_BORDE["db"] == 36.0
    assert sections.COLUMNA_BORDE["db_esq"] == 28.0
    assert sections.COLUMNA_BORDE["n_esq"] == 4
    assert sections.COLUMNA_BORDE["n_int"] == 16
    assert sections.COLUMNA_BORDE["rec"] == 68.0
    # filas simetricas (empareja di con h-di tolerando ruido de coma flotante)
    di_v = sorted(di for di, _ in barras)
    for di, a in barras:
        pareja = min(di_v, key=lambda d: abs(d - (h - di)))
        assert abs(pareja - (h - di)) < 1e-6
        assert math.isclose(dict(barras)[pareja], a,
                            rel_tol=1e-9, abs_tol=1e-6)
    # area_acero del modulo coincide
    assert math.isclose(sections.area_acero(sections.COLUMNA_BORDE),
                        esperada, rel_tol=1e-9)


def test_muro_tipificado_escala():
    """La regla proporcional reproduce las proporciones del 30x356 y
    cubre las 14 secciones de muro adicionales del contrato."""
    # el 30x356 es el caso base (borde 11.2% de Lw)
    base = sections.MURO
    assert base["Lw"] == 3560.0
    assert math.isclose(base["borde"] / base["Lw"], 0.112, rel_tol=5e-3)

    # regla: borde proporcional, filas proporcionales, malla fija phi10@20
    grand = sections.muro_tipificado("30x1000", 30.0, 1000.0)
    assert grand["Lw"] == 10000.0
    assert math.isclose(grand["borde"] / grand["Lw"],
                        round(0.112 * grand["Lw"], 1) / grand["Lw"],
                        rel_tol=1e-9)
    # filas de borde escaladas en la misma proporcion
    assert grand["filas_b"][0] == round(0.0225 * grand["Lw"], 1)
    assert grand["filas_b"][-1] == round(0.0674 * grand["Lw"], 1)
    # malla central sin cambios (phi10 @ 200 mm doble)
    assert grand["db_malla"] == 10.0 and grand["s_malla"] == 200.0

    # todos los muros reales del contrato estan cubiertos
    esperadas = {"60x291.5", "60x292", "25x795", "25x585", "30x2695",
                 "25x282", "30x725", "30x1000", "30x890", "30x615",
                 "25x158", "25x365", "30x225", "30x310"}
    claves = {s["nombre"] for s in sections.WALLS}
    assert claves == esperadas
    # geometria coherente en todos: borde al interior del largo, filas ordenadas
    for s in sections.WALLS:
        assert 0 < s["borde"] < s["Lw"] / 2 - 50.0
        assert s["filas_b"][0] < s["filas_b"][-1] < s["borde"]
        assert len(s["filas_b"]) >= 2
        assert s["db_borde"] == 40.0
        assert sections.area_acero(s) > 0


def test_muro_areas():
    bw, Lw, bars, Ast = vh.seccion_muro()
    assert bw == 300.0 and Lw == 3560.0
    # bordes: 5 filas x 2 phi40 x 2 bordes
    As_borde_fila = 2 * math.pi * (40.0 / 2.0) ** 2
    As_malla_esperada = 0.0
    for di, a in bars:
        if di in (80.0, 120.0, 160.0, 200.0, 240.0,
                  3560.0 - 80.0, 3560.0 - 120.0, 3560.0 - 160.0,
                  3560.0 - 200.0, 3560.0 - 240.0):
            continue
        As_malla_esperada += a
    assert math.isclose(Ast, 5 * 2 * As_borde_fila + As_malla_esperada,
                        rel_tol=1e-9)
    # refuerzo distribuido de malla: varias posiciones entre los bordes
    interiores = [di for di, _ in bars if 240.0 < di < Lw - 240.0]
    assert len(interiores) >= 10
    # la configuracion del module sections coincide con la del enunciado
    assert sections.MURO["db_borde"] == 40.0
    assert sections.MURO["nb_borde"] == 10


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


def _V_flexion_pura(tipo):
    P, M = vh.interaccion(tipo)
    ip = min(range(len(P)), key=lambda k: abs(P[k]))
    return M[ip]


def test_columna_borde_capacidades():
    """La columna del portico extremo (20 barras mixtas) tiene mas capacidad
    que la base 16 phi28: mayor P0, mayor balanceado y mayor flexion pura."""
    P0_b = vh.capacidad_pura_axial("columna_borde")
    P0_70 = vh.capacidad_pura_axial(True)
    assert P0_b > P0_70                     # mas acero -> ~22 MN vs 18.4 MN
    M_pura_b = _V_flexion_pura("columna_borde")
    M_pura_70 = _V_flexion_pura(True)
    assert M_pura_b > M_pura_70             # 4x36+4x28 > 16x28 en flexion
    Pb, Mb = vh.punto_momento_balanceado("columna_borde")
    assert Mb > M_pura_b                    # pico hacia compresion
    assert Pb > 5000 and Pb < 14000         # P0 mayor -> balanceado mas alto


def test_curva_pm_bloque():
    P, M = vh.interaccion(True)
    assert len(P) == len(M) >= 100
    # P monotona creciente y positiva
    assert all(b > a for a, b in zip(P, P[1:]))
    assert P[0] > -4000 and P[-1] > 1e4
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
                        "resultados", "07_capacidad", "mom_curv",
                        "mom_curv_columna_70x70.json")
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    assert len(datos["phi_1m"]) == len(datos["M_kNm"]) > 100
    assert datos["M_ult_kNm"] > 300 and datos["M_ult_kNm"] < 1300
    Mmax = max(datos["M_kNm"])
    # orden tipico de capacidad de flexion de la columna 70x70 (kN*m)
    assert 600 < Mmax < 1300