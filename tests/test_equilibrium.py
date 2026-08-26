"""
Test de equilibrio — Verificación invariante
Grupo 6 — Métodos Computacionales

Verifica: ΣF_aplicadas + ΣR = 0
Tolerancia: 1e-10
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opensees'))

from benchmark_3d import *
import json


def test_equilibrium():
    """Ejecutar benchmark y verificar equilibrio."""
    print("=== TEST DE EQUILIBRIO ===")

    create_model()
    define_nodes()
    define_materials()
    define_sections()
    define_transformations()
    define_elements()
    define_supports()
    define_loads()
    run_analysis()

    results = get_results()

    # Verificar
    Fy_applied = -10.0
    R1 = results["reactions"]["node_1"]
    R3 = results["reactions"]["node_3"]

    sum_Fy = Fy_applied + R1["Fy"] + R3["Fy"]
    tolerance = 1e-10

    assert abs(sum_Fy) < tolerance, f"Equilibrio falló: ΣFy = {sum_Fy}"
    print(f"✓ Test de equilibrio PASÓ: ΣFy = {sum_Fy:.2e}")


if __name__ == "__main__":
    test_equilibrium()
