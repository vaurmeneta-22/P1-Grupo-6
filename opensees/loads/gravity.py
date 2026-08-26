"""
Carga gravitacional — Semana 2
Grupo 6 — Métodos Computacionales

Calcula cargas gravitacionales usando áreas tributarias.
q_G = peso propio de losa + cargas de terminaciones
"""


def calculate_gravity_load(q_slab, q_finishes, tributary_area):
    """
    Calcular carga gravitacional total transferida a una viga.

    Parámetros:
    - q_slab: carga superficial de losa (kN/m²)
    - q_finishes: carga superficial de terminaciones (kN/m²)
    - tributary_area: área tributaria (m²)

    Retorna:
    - q_G: carga superficial total (kN/m²)
    - F_G: carga total transferida (kN)
    """
    q_G = q_slab + q_finishes
    F_G = q_G * tributary_area
    return q_G, F_G


def convert_to_line_load(total_force, beam_length):
    """
    Convertir carga total a carga lineal distribuida.

    Parámetros:
    - total_force: carga total (kN)
    - beam_length: largo de la viga (m)

    Retorna:
    - w: carga lineal (kN/m)
    """
    return total_force / beam_length


def verify_tributary_conservation(transferred_loads, q_total, area):
    """
    Verificar conservación de carga: Σ(cargas transferidas) = q × A.

    Tolerancia: 1e-10
    """
    expected = q_total * area
    actual = sum(transferred_loads)
    error = abs(actual - expected)

    if error < 1e-10:
        return True, error
    return False, error
