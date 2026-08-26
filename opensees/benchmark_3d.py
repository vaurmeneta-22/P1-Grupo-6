"""
Benchmark 3D OpenSeesPy — Semana 1
Grupo 6 — Métodos Computacionales

Problema:Portal 3D con 2 columnas y 1 viga
- Nodos 3D con 6 GDL
- elasticBeamColumn
- geomTransf
- Apoyos empotrados
- Carga puntual vertical
- Verificación de equilibrio
- Exportación a JSON
"""

import openseespy.opensees as ops
import json
import os


def create_model():
    """Crear y configurar el modelo."""
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)
    print("Modelo 3D creado: 3D, 6 GDL por nodo")


def define_nodes():
    """Definir nodos del portal 3D."""
    # Nodo 1: base izquierda (0, 0, 0)
    ops.node(1, 0.0, 0.0, 0.0)
    # Nodo 2: cabeza izquierda (0, 3, 0)
    ops.node(2, 0.0, 3.0, 0.0)
    # Nodo 3: base derecha (5, 0, 0)
    ops.node(3, 5.0, 0.0, 0.0)
    # Nodo 4: cabeza derecha (5, 3, 0)
    ops.node(4, 5.0, 3.0, 0.0)
    print("Nodos definidos: 4 nodos en (x, y, z)")


def define_materials():
    """Definir materiales elásticos."""
    # Concreto (E, G approximation)
    E = 25e6  # kN/m² (f'c ≈ 25 MPa)
    G = 10e6  # kN/m²
    ops.uniaxialMaterial('Elastic', 1, E)
    print(f"Material definido: E = {E/1e6} MPa")


def define_sections():
    """Definir secciones elásticas."""
    # Columna: 0.30 x 0.30 m
    A_col = 0.30 * 0.30
    Iy_col = 0.30 * 0.30**3 / 12
    Iz_col = 0.30**3 * 0.30 / 12
    J_col = 0.30**4 * 0.08  # Aproximación para sección rectangular

    ops.section('Elastic', 1, 25e6, A_col, Iy_col, Iz_col, 10e6, J_col)
    print(f"Sección columna: {0.30*100:.0f}x{0.30*100:.0f} cm, A={A_col:.4f} m²")

    # Viga: 0.25 x 0.50 m
    A_beam = 0.25 * 0.50
    Iy_beam = 0.25 * 0.50**3 / 12
    Iz_beam = 0.50**3 * 0.25 / 12
    J_beam = 0.25 * 0.50**3 * 0.2

    ops.section('Elastic', 2, 25e6, A_beam, Iy_beam, Iz_beam, 10e6, J_beam)
    print(f"Sección viga: {0.25*100:.0f}x{0.50*100:.0f} cm, A={A_beam:.4f} m²")


def define_transformations():
    """Definir transformaciones geométricas para 3D."""
    # Para columnas: eje local Y vertical
    ops.geomTransf('Linear', 1, 0, 0, 1)  # vecxz = (0,0,1)
    # Para viga: eje local Y horizontal
    ops.geomTransf('Linear', 2, 0, 1, 0)  # vecxz = (0,1,0)
    print("Transformaciones definidas: Linear (columnas Y1, viga Y2)")


def define_elements():
    """Definir elementos viga-columna."""
    # Columna izquierda: nodo 1 → nodo 2
    ops.element('elasticBeamColumn', 1, 1, 2, 25e6, 0.09, 0.0005625, 0.0005625, 10e6, 0.000405, 1)

    # Viga: nodo 2 → nodo 4
    ops.element('elasticBeamColumn', 2, 2, 4, 25e6, 0.125, 0.002604, 0.001302, 10e6, 0.001563, 2)

    # Columna derecha: nodo 3 → nodo 4
    ops.element('elasticBeamColumn', 3, 3, 4, 25e6, 0.09, 0.0005625, 0.0005625, 10e6, 0.000405, 1)

    print("Elementos definidos: 2 columnas + 1 viga")


def define_supports():
    """Definir apoyos empotrados en bases."""
    # Nodo 1: empotrado (restringir todos los GDL)
    ops.fix(1, 1, 1, 1, 1, 1, 1)
    # Nodo 3: empotrado
    ops.fix(3, 1, 1, 1, 1, 1, 1)
    print("Apoyos definidos: empotrados en nodos 1 y 3")


def define_loads():
    """Definir cargas."""
    # Carga puntual vertical en nodo 2 (cabeza izquierda)
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    ops.load(2, 0.0, -10.0, 0.0, 0.0, 0.0, 0.0)
    print("Carga definida: -10 kN en Y (nodo 2)")


def run_analysis():
    """Ejecutar análisis."""
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)
    ops.loadConst('-time', 0.0)
    print("Análisis completado")


def get_results():
    """Obtener resultados del análisis."""
    results = {}

    # Deformadas
    results["displacements"] = {}
    for i in range(1, 5):
        disp = ops.nodeDisp(i)
        results["displacements"][f"node_{i}"] = {
            "ux": round(disp[0], 10),
            "uy": round(disp[1], 10),
            "uz": round(disp[2], 10),
            "rx": round(disp[3], 10),
            "ry": round(disp[4], 10),
            "rz": round(disp[5], 10)
        }

    # Reacciones
    results["reactions"] = {}
    for i in [1, 3]:
        reaction = ops.nodeReaction(i)
        results["reactions"][f"node_{i}"] = {
            "Fx": round(reaction[0], 10),
            "Fy": round(reaction[1], 10),
            "Fz": round(reaction[2], 10),
            "Mx": round(reaction[3], 10),
            "My": round(reaction[4], 10),
            "Mz": round(reaction[5], 10)
        }

    # Fuerzas internas
    results["element_forces"] = {}
    for i in range(1, 4):
        force = ops.eleForce(i)
        results["element_forces"][f"element_{i}"] = {
            "axial": round(force[0], 10),
            "shear_y": round(force[1], 10),
            "shear_z": round(force[2], 10),
            "torque": round(force[3], 10),
            "moment_y": round(force[4], 10),
            "moment_z": round(force[5], 10)
        }

    return results


def verify_equilibrium(results):
    """Verificar equilibrio global: ΣF + ΣR = 0."""
    print("\n--- VERIFICACIÓN DE EQUILIBRIO ---")

    # Fuerzas aplicadas
    Fx_applied = 0.0
    Fy_applied = -10.0  # kN
    Fz_applied = 0.0

    # Reacciones
    R1 = results["reactions"]["node_1"]
    R3 = results["reactions"]["node_3"]

    sum_Fx = Fx_applied + R1["Fx"] + R3["Fx"]
    sum_Fy = Fy_applied + R1["Fy"] + R3["Fy"]
    sum_Fz = Fz_applied + R1["Fz"] + R3["Fz"]

    print(f"ΣFx = {Fx_applied:.10f} + {R1['Fx']:.10f} + {R3['Fx']:.10f} = {sum_Fx:.10f}")
    print(f"ΣFy = {Fy_applied:.10f} + {R1['Fy']:.10f} + {R3['Fy']:.10f} = {sum_Fy:.10f}")
    print(f"ΣFz = {Fz_applied:.10f} + {R1['Fz']:.10f} + {R3['Fz']:.10f} = {sum_Fz:.10f}")

    tolerance = 1e-10
    if abs(sum_Fx) < tolerance and abs(sum_Fy) < tolerance and abs(sum_Fz) < tolerance:
        print("✓ EQUILIBRIO VERIFICADO: ΣF ≈ 0")
    else:
        print("✗ ERROR DE EQUILIBRIO: ΣF ≠ 0")


def export_results(results, filepath):
    """Exportar resultados a JSON."""
    output = {
        "model": {
            "ndm": 3,
            "ndf": 6,
            "description": "Portal 3D benchmark"
        },
        "nodes": {
            "1": {"x": 0.0, "y": 0.0, "z": 0.0, "fixity": [1,1,1,1,1,1]},
            "2": {"x": 0.0, "y": 3.0, "z": 0.0, "fixity": [0,0,0,0,0,0]},
            "3": {"x": 5.0, "y": 0.0, "z": 0.0, "fixity": [1,1,1,1,1,1]},
            "4": {"x": 5.0, "y": 3.0, "z": 0.0, "fixity": [0,0,0,0,0,0]}
        },
        "elements": {
            "1": {"type": "column", "nodes": [1, 2], "section": 1},
            "2": {"type": "beam", "nodes": [2, 4], "section": 2},
            "3": {"type": "column", "nodes": [3, 4], "section": 1}
        },
        "loads": {
            "1": {"type": "point", "node": 2, "Fx": 0.0, "Fy": -10.0, "Fz": 0.0}
        },
        "results": results
    }

    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nResultados exportados a: {filepath}")


def main():
    """Función principal del benchmark."""
    print("=" * 50)
    print("BENCHMARK 3D — PORTAL SIMPLE")
    print("Grupo 6 — Semana 1")
    print("=" * 50)

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
    verify_equilibrium(results)

    # Exportar
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(output_dir, exist_ok=True)
    export_results(results, os.path.join(output_dir, 'benchmark_3d.json'))

    print("\n--- RESUMEN ---")
    print("Desformadas (nodo 2, cabeza izquierda):")
    d = results["displacements"]["node_2"]
    print(f"  ux = {d['ux']:.6f} m")
    print(f"  uy = {d['uy']:.6f} m")
    print(f"  uz = {d['uz']:.6f} m")


if __name__ == "__main__":
    main()
