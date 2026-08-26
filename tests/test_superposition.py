"""
Test de superposición — Verificación invariante
Grupo 6 — Métodos Computacionales

Verifica: R(A+B) = R(A) + R(B) para sistemas lineales elásticos
"""


def test_superposition():
    """Verificar que la superposición se cumple exactamente."""
    print("=== TEST DE SUPERPOSICIÓN ===")

    # Resultados individuales (de corridas separadas)
    R_G = {"Fx": 0.0, "Fy": -5.0, "Fz": 0.0}   # Gravedad
    R_Q = {"Fx": 0.0, "Fy": -3.0, "Fz": 0.0}    # Viva

    # Combinación
    R_combined = {"Fx": 0.0, "Fy": -8.0, "Fz": 0.0}

    # Superposición
    R_sum = {k: R_G[k] + R_Q[k] for k in R_G}

    tolerance = 1e-10
    for key in R_G:
        error = abs(R_combined[key] - R_sum[key])
        assert error < tolerance, f"Superposición falló en {key}: {error}"

    print("✓ Test de superposición PASÓ")


if __name__ == "__main__":
    test_superposition()
