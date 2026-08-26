"""
Test de equilibrio — Benchmark 3D
Grupo 6 — Semana 1

Verifica: ΣR = ΣF_aplicadas
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from benchmark_3d import *


def test_equilibrium():
    """Verificar que la suma de reacciones equals la carga total."""
    # Recrear modelo
    create_full_model()

    F_total = q_G * Lx * Ly
    R_total = sum(ops.nodeReaction(i)[2] for i in [1, 2, 3, 4])

    tolerance = 1e-6
    error = abs(R_total - F_total) / F_total

    assert error < tolerance, f"Equilibrio falló: ΣR={R_total:.2f}, ΣF={F_total:.2f}"
    print(f"✓ Test PASÓ: ΣR = {R_total:.2f} kN, ΣF = {F_total:.2f} kN, error = {error:.2e}")


def create_full_model():
    """Recrear el modelo completo para testing."""
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

    # Apoyos
    for i in [1, 2, 3, 4]:
        ops.fix(i, 1, 1, 1, 1, 1, 1)

    # Transformaciones
    ops.geomTransf('Linear', 1, 1, 0, 0)
    ops.geomTransf('Linear', 2, 0, 0, 1)

    # Elementos
    for i in range(1, 5):
        ops.element('elasticBeamColumn', i, i, i+4, E, A_col, Iy_col, Iz_col, G, J_col, 1)
    ops.element('elasticBeamColumn', 5, 5, 6, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)
    ops.element('elasticBeamColumn', 6, 7, 8, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)
    ops.element('elasticBeamColumn', 7, 5, 7, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)
    ops.element('elasticBeamColumn', 8, 6, 8, E, A_vig, Iy_vig, Iz_vig, G, J_vig, 2)

    # Cargas
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.eleLoad('-ele', 5, '-type', '-beamUniform', -w_G_x, 0, 0)
    ops.eleLoad('-ele', 6, '-type', '-beamUniform', -w_G_x, 0, 0)
    ops.eleLoad('-ele', 7, '-type', '-beamUniform', -w_G_y, 0, 0)
    ops.eleLoad('-ele', 8, '-type', '-beamUniform', -w_G_y, 0, 0)

    # Análisis
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)


if __name__ == "__main__":
    test_equilibrium()
