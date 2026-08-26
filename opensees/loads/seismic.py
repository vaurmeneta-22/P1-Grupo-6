"""
Carga sísmica pseudoestática — Semana 3
Grupo 6 — Métodos Computacionales

Aplica patrón lateral idealizado en X (EX) e Y (EY).
"""


import openseespy.opensees as ops


def apply_seismic_pattern(load_pattern_id, direction, floor_forces):
    """
    Aplicar patrón sísmico lateral.

    Parámetros:
    - load_pattern_id: ID del patrón de carga
    - direction: 'X' o 'Y'
    - floor_forces: dict {node_id: force_kN}
    """
    ops.timeSeries('Linear', load_pattern_id)
    ops.pattern('Plain', load_pattern_id, load_pattern_id)

    for node_id, force in floor_forces.items():
        if direction == 'X':
            ops.load(int(node_id), force, 0.0, 0.0, 0.0, 0.0, 0.0)
        elif direction == 'Y':
            ops.load(int(node_id), 0.0, force, 0.0, 0.0, 0.0, 0.0)

    print(f"Patrón sísmico {load_pattern_id} aplicado en dirección {direction}")
