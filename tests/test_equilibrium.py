"""
Test de validación del Benchmark 3D (marco con viga central, 2 paños de losa)
Grupo 6

Verifica:
1. Equilibrio global:  ΣR = ΣF_aplicadas
2. Conservación de carga de las losas:  Σ(cargas sobre vigas) = q_G * A
3. Suma de áreas tributarias = área de losa (A = Lx * Ly)
4. Compatibilidad del diafragma rígido (nodos del piso se mueven como disco rígido)

El modelo se reconstruye explícitamente aquí (no se importa benchmark_3d.py,
que es un script de ejecución, no un módulo).
"""

import math


# ---------------------------------------------------------------------------
# Modelo (idéntico a benchmark_3d.py)
# ---------------------------------------------------------------------------
def create_model():
    import openseespy.opensees as ops

    # Geometría / materiales
    Lx = 10.0
    Ly = 8.9
    H_eje = 3.56
    Lx_mid = Lx / 2.0

    b_col, h_col = 0.70, 0.70
    b_vig, h_vig = 0.60, 0.80
    E = 27.8e6
    nu = 0.2
    G = E / (2.0 * (1.0 + nu))

    A_col = b_col * h_col
    Iy_col = b_col * h_col**3 / 12.0
    Iz_col = h_col * b_col**3 / 12.0
    J_col = 0.208 * b_col * h_col**3
    A_vig = b_vig * h_vig
    Iy_vig = b_vig * h_vig**3 / 12.0
    Iz_vig = h_vig * b_vig**3 / 12.0
    J_vig = 0.208 * b_vig * h_vig**3

    q_pp = 375 * 9.81 / 1000.0
    q_pmad = 260 * 9.81 / 1000.0
    q_sc = 300 * 9.81 / 1000.0
    q_G = q_pp + q_pmad + q_sc

    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)

    # Nodos
    ops.node(1, 0.0, 0.0, 0.0)
    ops.node(2, Lx, 0.0, 0.0)
    ops.node(3, 0.0, Ly, 0.0)
    ops.node(4, Lx, Ly, 0.0)
    ops.node(5, 0.0, 0.0, H_eje)
    ops.node(6, Lx, 0.0, H_eje)
    ops.node(7, 0.0, Ly, H_eje)
    ops.node(8, Lx, Ly, H_eje)
    ops.node(9, Lx_mid, 0.0, H_eje)
    ops.node(10, Lx_mid, Ly, H_eje)

    # Apoyos
    for i in [1, 2, 3, 4]:
        ops.fix(i, 1, 1, 1, 1, 1, 1)

    # Transformaciones
    ops.geomTransf('Linear', 1, 1, 0, 0)
    ops.geomTransf('Linear', 2, 0, 0, 1)

    # Secciones
    ops.section('Elastic', 1, E, A_col, Iy_col, Iz_col, G, J_col)
    ops.section('Elastic', 2, E, A_vig, Iy_vig, Iz_vig, G, J_vig)

    # Elementos: columnas 1-4, vigas 5-11
    for tag, (ni, nj) in [(1, (1, 5)), (2, (2, 6)), (3, (3, 7)), (4, (4, 8))]:
        ops.element('elasticBeamColumn', tag, ni, nj, A_col, E, G, J_col, Iy_col, Iz_col, 1)
    for tag, (ni, nj) in [(5, (5, 9)), (6, (9, 6)), (7, (7, 10)), (8, (10, 8)),
                          (9, (5, 7)), (10, (6, 8)), (11, (9, 10))]:
        ops.element('elasticBeamColumn', tag, ni, nj, A_vig, E, G, J_vig, Iy_vig, Iz_vig, 2)

    # Diafragma rígido (master = nodo estructural 9)
    ops.rigidDiaphragm(3, 9, 5, 6, 7, 8, 10)

    # Cargas: reparto 45°, 2 paños
    Sx = Lx / 2.0
    Sy = Ly
    h_trib = Sx / 2.0
    tri_area_x = Sx * h_trib / 2.0
    trap_area_y_lat = (Sy + (Sy - 2 * h_trib)) / 2.0 * h_trib
    trap_area_y_cen = 2.0 * trap_area_y_lat

    tributary_area = {
        5: tri_area_x, 6: tri_area_x, 7: tri_area_x, 8: tri_area_x,
        9: trap_area_y_lat, 10: trap_area_y_lat, 11: trap_area_y_cen,
    }
    w_loads = {eid: q_G * a / (5.0 if eid <= 8 else Sy) for eid, a in tributary_area.items()}

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    for eid, w in w_loads.items():
        ops.eleLoad('-ele', eid, '-type', '-beamUniform', 0.0, -w)

    # Análisis
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Transformation')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ok = ops.analyze(1)
    if ok != 0:
        raise RuntimeError(f"Análisis falló (código {ok})")
    ops.reactions()

    return ops, q_G, Lx, Ly, Sy


def test_equilibrium():
    ops, q_G, Lx, Ly, Sy = create_model()

    F_total = q_G * Lx * Ly
    R_total = sum(ops.nodeReaction(i)[2] for i in [1, 2, 3, 4])
    error = abs(R_total - F_total) / F_total
    assert error < 1e-6, f"Equilibrio falló: ΣR={R_total:.2f}, ΣF={F_total:.2f}"
    print(f"✓ Equilibrio: ΣR={R_total:.2f} kN, ΣF={F_total:.2f} kN, error={error:.2e}")


def test_load_conservation():
    ops, q_G, Lx, Ly, Sy = create_model()

    Sx = Lx / 2.0
    h_trib = Sx / 2.0
    tri_area_x = Sx * h_trib / 2.0
    trap_area_y_lat = (Sy + (Sy - 2 * h_trib)) / 2.0 * h_trib
    trap_area_y_cen = 2.0 * trap_area_y_lat

    areas = {i: tri_area_x for i in [5, 6, 7, 8]}
    areas.update({9: trap_area_y_lat, 10: trap_area_y_lat, 11: trap_area_y_cen})
    W_vigas = sum(q_G * a for a in areas.values())
    W_losas = q_G * Lx * Ly
    rel = abs(W_vigas - W_losas) / W_losas
    assert rel < 1e-9, f"Conservación falló: W_vigas={W_vigas:.4f}, W_losas={W_losas:.4f}"
    print(f"✓ Conservación de carga: W_vigas={W_vigas:.4f} kN = q_G·A={W_losas:.4f} kN")


def test_tributary_area_sum():
    ops, q_G, Lx, Ly, Sy = create_model()

    Sx = Lx / 2.0
    h_trib = Sx / 2.0
    tri_area_x = Sx * h_trib / 2.0
    trap_area_y_lat = (Sy + (Sy - 2 * h_trib)) / 2.0 * h_trib
    trap_area_y_cen = 2.0 * trap_area_y_lat

    areas = {i: tri_area_x for i in [5, 6, 7, 8]}
    areas.update({9: trap_area_y_lat, 10: trap_area_y_lat, 11: trap_area_y_cen})
    sum_area = sum(areas.values())
    A_floor = Lx * Ly
    assert abs(sum_area - A_floor) < 1e-9, f"Áreas no cuadran: Σ={sum_area:.6f}, A={A_floor:.6f}"
    print(f"✓ Suma áreas tributarias: Σ={sum_area:.4f} m² = A_floor={A_floor:.4f} m²")


def test_diaphragm_compatibility():
    ops, q_G, Lx, Ly, Sy = create_model()

    d_m = ops.nodeDisp(9)
    ux_m, uy_m, rz_m = d_m[0], d_m[1], d_m[5]
    xm, ym, _ = ops.nodeCoord(9)

    max_err = 0.0
    for n in [5, 6, 7, 8, 10]:
        x, y, _ = ops.nodeCoord(n)
        d = ops.nodeDisp(n)
        ux_pred = ux_m - rz_m * (y - ym)
        uy_pred = uy_m + rz_m * (x - xm)
        max_err = max(max_err, abs(d[0] - ux_pred), abs(d[1] - uy_pred))
    assert max_err < 1e-9, f"Diafragma incompatible, err máx={max_err:.3e} m"
    print(f"✓ Compatibilidad diafragma: error máx = {max_err:.3e} m (nodos 5-8,10 como disco rígido)")


if __name__ == "__main__":
    test_equilibrium()
    test_load_conservation()
    test_tributary_area_sum()
    test_diaphragm_compatibility()
    print("Todos los tests PASARON.")
