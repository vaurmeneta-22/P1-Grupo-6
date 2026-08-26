"""
Carga viva — Semana 3
Grupo 6 — Métodos Computacionales

Aplica carga viva usando la misma geometría tributaria que G.
"""


def calculate_live_load(q_live, tributary_area):
    """
    Calcular carga viva transferida a una viga.

    Parámetros:
    - q_live: carga superficial viva (kN/m²)
    - tributary_area: área tributaria (m²)

    Retorna:
    - F_Q: carga viva total (kN)
    """
    return q_live * tributary_area
