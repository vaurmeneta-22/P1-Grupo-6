"""
Curva de interacción P-M — Semana 3
Grupo 6 — Métodos Computacionales

Genera curvas de interacción axial-momento para columnas y muros.
"""


import openseespy.opensees as ops


def generate_p_m_curve(section_id, axial_loads, max_moment, num_steps):
    """
    Generar curva P-M para un rango de cargas axiales.

    Parámetros:
    - section_id: ID de la sección de fibras
    - axial_loads: lista de niveles de carga axial (kN)
    - max_moment: momento máximo estimado (kN*m)
    - num_steps: número de pasos por nivel axial

    Retorna:
    - p_m_data: lista de (P, M_max) para cada nivel axial
    """
    p_m_data = []

    for P in axial_loads:
        # Aplicar carga axial constante
        ops.timeSeries('Linear', 1)
        ops.pattern('Plain', 1, 1)
        ops.load(100, 0.0, 0.0, P, 0.0, 0.0, 0.0)

        # Ejecutar análisis con control de desplazamiento
        ops.system('BandSPD')
        ops.numberer('RCM')
        ops.constraints('Plain')
        ops.integrator('DisplacementControl', 100, 6, max_moment / num_steps)
        ops.algorithm('Linear')
        ops.analysis('Static')

        M_max = 0
        for i in range(num_steps):
            ok = ops.analyze(1)
            if ok != 0:
                break
            M_max = ops.getTime()

        p_m_data.append({"P": P, "M_max": M_max})
        ops.loadConst('-time', 0.0)

    return p_m_data


def export_p_m_curve(p_m_data, element_type, filepath):
    """Exportar curva P-M a JSON."""
    import json

    data = {
        "description": f"Curva P-M para {element_type}",
        "units": {
            "P": "kN",
            "M": "kN*m"
        },
        "data": p_m_data
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Curva P-M ({element_type}) exportada a: {filepath}")
