"""
Test de áreas tributarias — Verificación invariante
Grupo 6 — Métodos Computacionales

Verifica: Σ(cargas transferidas) = q × A
Tolerancia: 1e-10
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'opensees'))

from loads.gravity import calculate_gravity_load, verify_tributary_conservation


def test_tributary_areas():
    """Verificar conservación de carga en áreas tributarias."""
    print("=== TEST DE ÁREAS TRIBUTARIAS ===")

    q_slab = 4.0    # kN/m² (losa)
    q_finish = 1.5   # kN/m² (terminaciones)
    q_total = q_slab + q_finish  # 5.5 kN/m²

    # Ejemplo: viga recibe carga de un panel 3m x 4m
    area = 3.0 * 4.0  # 12 m²

    # Carga transferida (simular分配 a 2 vigas)
    transferred = [
        q_total * area * 0.6,  # 60% a viga 1
        q_total * area * 0.4   # 40% a viga 2
    ]

    is_conserved, error = verify_tributary_conservation(transferred, q_total, area)

    assert is_conserved, f"Conservación falló: error = {error}"
    print(f"✓ Test de áreas tributarias PASÓ: error = {error:.2e}")


if __name__ == "__main__":
    test_tributary_areas()
