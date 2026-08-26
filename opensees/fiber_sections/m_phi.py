"""
Curva Momento-Curvatura (M-phi) — Semana 3
Grupo 6 — Métodos Computacionales

Genera curva M-phi para una sección de hormigón armado usando Fiber Section.
"""


import openseespy.opensees as ops


def create_fiber_section(section_id, core_mat, cover_mat, steel_mat,
                         core_dims, cover_dims, steel_bars):
    """
    Crear sección de fibras de hormigón armado.

    Parámetros:
    - section_id: ID de la sección
    - core_mat: material del concreto confinado
    - cover_mat: material del concreto no confinado
    - steel_mat: material del acero de refuerzo
    - core_dims: (b, h) dimensiones del núcleo confinado
    - cover_dims: (b, h) dimensiones externas
    - steel_bars: lista de (x, y, area) para cada barra
    """
    ops.section('Fiber', section_id)

    # Concreto confinado (núcleo)
    ops.fiber(0, 0, core_mat, core_dims[0] * core_dims[1])

    # Concreto no confinado (recubrimiento)
    cover_area = cover_dims[0] * cover_dims[1] - core_dims[0] * core_dims[1]
    ops.fiber(0, 0, cover_mat, cover_area)

    # Acero de refuerzo
    for bar in steel_bars:
        ops.fiber(bar[1], bar[2], steel_mat, bar[0])

    print(f"Sección de fibras {section_id} creada")


def run_m_phi_analysis(section_id, max_curvature, num_steps):
    """
    Ejecutar análisis de momento-curvatura.

    Retorna:
    - moments: lista de momentos
    - curvatures: lista de curvaturas
    """
    # Configurar análisis
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)

    # Nodo de control (nodo ficticio)
    ops.node(100, 0, 0, 0)
    ops.fix(100, 1, 1, 1, 1, 1, 1)

    # Elemento de control
    ops.element('zeroLength', 1, 100, 100, '-mat', 1, '-dir', 6)

    # Integrador
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('DisplacementControl', 100, 6, max_curvature / num_steps)
    ops.algorithm('Linear')
    ops.analysis('Static')

    moments = []
    curvatures = []

    for i in range(num_steps):
        ok = ops.analyze(1)
        if ok != 0:
            print(f"Análisis falló en paso {i+1}")
            break
        moments.append(ops.getTime())
        curvatures.append(max_curvature * (i + 1) / num_steps)

    return moments, curvatures


def export_m_phi(moments, curvatures, filepath):
    """Exportar curva M-phi a JSON."""
    import json

    data = {
        "description": "Curva Momento-Curvatura (M-phi)",
        "units": {
            "moment": "kN*m",
            "curvature": "1/m"
        },
        "data": [{"moment": m, "curvature": k} for m, k in zip(moments, curvatures)]
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Curva M-phi exportada a: {filepath}")
