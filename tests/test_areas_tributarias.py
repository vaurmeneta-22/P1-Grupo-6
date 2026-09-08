"""
Tests de areas tributarias por TRAMOS (Semana 3) — Grupo 6

Verifica (sin abrir OpenSees; solo geometria del reparto):
 1. Integral exacta del perfil 45° sobre el borde completo == area del borde.
 2. Re-baseline del perfil ante coordenadas NEGATIVAS (bug corregido: antes los
    tramos con coord. < 0 daban At = 0).
 3. Particion sin solapes ni dobles conteos (sweep): vigas contiguas y vigas
    solapadas -> tramos disjuntos y huecos solo donde no hay viga.
 4. Contrato real: conservacion global de areas y de carga W (< 1e-10).
 5. Contrato real: losa 698 repartida entre las vigas 411/412 SIN hueco y con
    sum(At_tramos) == area del borde (regresion del borde multi-viga).
 6. Contrato real: reporte de las 4 losas aisladas y los 9 huecos pendientes.
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENSEES = os.path.join(REPO, "opensees")
JSON_PATH = os.path.join(REPO, "Edificio.json")
if OPENSEES not in sys.path:
    sys.path.insert(0, OPENSEES)

import areas_tributarias as at


# ---------------------------------------------------------------------------
# 1) Perfil 45°: integral sobre [0, Lm] == A_total (conservacion por borde)
# ---------------------------------------------------------------------------
def test_perfil45_integral_igual_area_total():
    import pytest
    casos = [(4.0, 2.0, 4.0),      # losa 4x4, borde corto (meseta degenerada)
             (8.0, 2.0, 16.0),     # losa 4x8, borde larga
             (4.0, 2.0, 16.0),     # losa 8x4, borde corta pero area distinta
             (7.12, 3.56, 25.35),  # caso generico
             ]
    for Lm, h, A_total in casos:
        At, a45 = at._perfil_45(Lm, h, A_total, 0.0, Lm)
        assert At == pytest.approx(A_total, abs=1e-9), \
            f"Lm={Lm}: At={At:.10f} != A_total={A_total}"
        # el area analitica del 45 grados es h*(Lm - h)
        assert abs(a45 - h * (Lm - h)) < 1e-12


def test_perfil45_monotona_y_escalada():
    # perfil con meseta: w(h)=h, w(Lm-h)=h
    Lm, h, A = 8.0, 2.0, 16.0
    a = at._perfil_45(Lm, h, A, 0.0, 2.0)[0]      # rampa: integral s^2/2 -> 2
    b = at._perfil_45(Lm, h, A, 6.0, 8.0)[0]      # rampa final: (8-6)^2/2 -> 2
    m = at._perfil_45(Lm, h, A, 2.0, 6.0)[0]      # meseta: h*(6-2)=8
    escala = A / (h * (Lm - h))
    assert abs(a - escala * 2.0) < 1e-12
    assert abs(b - escala * 2.0) < 1e-12
    assert abs(m - escala * 8.0) < 1e-12


# ---------------------------------------------------------------------------
# 2) Re-baseline con coordenadas negativas (bug corregido en Semana 3)
# ---------------------------------------------------------------------------
def test_area_por_tramo_negativas():
    # losa con x0 = -3000 cm, borde x_min en X=-3000 cte, extendido en Y:
    # ymin = -4000 .. ymax = -3200 (Ly=800 cm), Lx=400 cm -> borde largo.
    loza = {'Lx': 400, 'Ly': 800, 'ymin': -4000.0, 'xi': -3000.0}
    # el tramo abarca el borde completo [ymin, ymax]; A_total del borde x_min
    # (borde largo) = (Lx*Ly - 2*triangulo)/2 = (32 - 8)/2 = 12 m2
    At = at.area_por_tramo_45(loza, 'x_min', -4000.0, -3200.0, 12.0)
    assert At > 0.0, "coord. negativas: el tramo completo dio area 0"
    assert abs(At - 12.0) < 1e-12, f"conservacion por borde: {At:.6f} != 12.0"


# ---------------------------------------------------------------------------
# 3) Particion por tramos: sweep sin solapes ni huecos indebidos
# ---------------------------------------------------------------------------
def _seg(eje_x_segs=None, eje_y_segs=None):
    """Construye (seg_x, seg_y) con la forma de vigas_por_nivel:
    seg_x[(z,x)] = [(y1,y2,id,sec)] para beam_x; seg_y[(z,y)] = [(x1,x2,id,sec)]."""
    return (eje_x_segs or {}), (eje_y_segs or {})


def test_tramos_receptores_vigas_contiguas_no_dejan_hueco():
    z = 356.0
    seg_x, seg_y = _seg(eje_x_segs=None,
                        eje_y_segs={(z, 100.0): [(0.0, 725.0, 411, '0.30x0.60'),
                                                 (725.0, 1615.0, 412, '0.30x0.60')]})
    tramos, huecos = at.tramos_receptores(seg_x, seg_y, z, 'x', 100.0, 0.0, 1615.0)
    assert [t['s'] for t in tramos] == [0.0, 725.0]
    assert [t['e'] for t in tramos] == [725.0, 1615.0]
    assert [t['vid'] for t in tramos] == [411, 412]
    assert huecos == [], f"vigas contiguas no deben dejar hueco: {huecos}"


def test_tramos_receptores_solape_se_recorta():
    z = 356.0
    seg_x, seg_y = _seg(eje_x_segs=None,
                        eje_y_segs={(z, 100.0): [(0.0, 800.0, 5, 'x'),
                                                 (600.0, 1600.0, 6, 'x')]})
    tramos, huecos = at.tramos_receptores(seg_x, seg_y, z, 'x', 100.0, 0.0, 1600.0)
    assert [(t['s'], t['e'], t['vid']) for t in tramos] == \
        [(0.0, 800.0, 5), (800.0, 1600.0, 6)], "solape debe recortarse (sin doble conteo)"
    assert huecos == []


def test_tramos_receptores_viga_parcial_deja_hueco():
    z = 356.0
    seg_x, seg_y = _seg(eje_x_segs=None,
                        eje_y_segs={(z, 100.0): [(0.0, 800.0, 7, 'x')]})
    tramos, huecos = at.tramos_receptores(seg_x, seg_y, z, 'x', 100.0, 0.0, 1000.0)
    assert [(t['s'], t['e']) for t in tramos] == [(0.0, 800.0)]
    assert huecos == [(800.0, 1000.0)], f"la banda suelta debe reportarse como hueco: {huecos}"


def test_tramos_receptores_sin_viga_todo_hueco():
    z = 356.0
    seg_x, seg_y = _seg(eje_x_segs=None, eje_y_segs={})
    tramos, huecos = at.tramos_receptores(seg_x, seg_y, z, 'x', 100.0, 0.0, 800.0)
    assert tramos == [] and huecos == [(0.0, 800.0)]


# ---------------------------------------------------------------------------
# 4) Contrato real: conservacion global (areas y carga W)
# ---------------------------------------------------------------------------
def _nodos():
    import json
    d = json.load(open(JSON_PATH, encoding='utf-8'))
    return {n['id']: n for n in d['nodes']}


def test_verificador_conservacion_global():
    ok, res = at.verificar_areas_tributarias(JSON_PATH, _nodos(),
                                             extra_kn_m2=2.0,
                                             include_self_weight=True)
    assert ok
    assert res['conservacion_rel_A'] < 1e-10
    assert res['conservacion_rel_W'] < 1e-10
    assert abs((res['A_trib_total_m2'] + res['A_huecos_m2']) -
               res['A_lozas_total_m2']) / res['A_lozas_total_m2'] < 1e-10


# ---------------------------------------------------------------------------
# 5) Borde multi-viga real (losa 698 -> vigas 411/412) sin hueco
# ---------------------------------------------------------------------------
def test_losa698_repartida_en_dos_vigas_contiguas():
    import pytest
    cargas, huecos, aisladas = at._transferir(JSON_PATH, _nodos(),
                                              extra_kn_m2=2.0,
                                              include_self_weight=True)
    # losa 698 sobre el borde x_min debe repartirse entre las vigas 411 y 412
    aportes = [ap for vid in (411, 412) for ap in cargas.get(vid, {}).get('aportes', [])
               if ap['loza'] == 698 and ap['borde'] == 'x_min']
    assert len(aportes) == 2, f"esperaba 2 tramos en x_min de losa 698: {aportes}"
    tramos = sorted(ap['tramo'] for ap in aportes)
    # contiguos: el fin del primero == el inicio del segundo (particion en 725 cm)
    assert tramos[0][1] == pytest.approx(tramos[1][0], abs=1e-6), \
        f"tramos deben compartir el borde en 725.0 cm: {tramos}"
    # la SUMA de tramos conserva el area del borde (regresion multi-viga)
    At = sum(ap['area_m2'] for ap in aportes)
    assert At == pytest.approx(12.385750, abs=1e-6), \
        f"suma tramos {At:.6f} != A_borde 12.385750"
    # ningun hueco pendiente para este borde
    assert not any(h['loza'] == 698 and h['borde'] == 'x_min' for h in huecos), \
        "el borde con viga completa no debe reportar hueco"


# ---------------------------------------------------------------------------
# 6) Reporte: aisladas y huecos pendientes del contrato real
# ---------------------------------------------------------------------------
def test_aisladas_y_huecos_reales():
    _, res = at.verificar_areas_tributarias(JSON_PATH, _nodos(),
                                            extra_kn_m2=2.0,
                                            include_self_weight=True)
    ids = sorted(a['id'] for a in res['aisladas'])
    assert ids == [649, 653, 657, 661], f"losas aisladas: {ids}"
    assert abs(res['A_lozas_aisladas_m2'] - 2.256) < 1e-9
    assert len(res['huecos_pendientes']) == 9, \
        f"se esperaban 9 huecos: {res['huecos_pendientes']}"
    # todo hueco tiene su area (trazabilidad de la banda no transferida)
    for h in res['huecos_pendientes']:
        assert h['area_m2'] > 0.0


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK   {name}")
            except Exception as e:
                failed += 1
                print(f"FAIL {name}: {e}")
                traceback.print_exc()
    print("PASARON" if failed == 0 else f"{failed} tests fallaron")
    sys.exit(1 if failed else 0)