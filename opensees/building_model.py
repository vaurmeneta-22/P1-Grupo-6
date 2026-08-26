"""
Modelo global del Edificio de Ingeniería — Semana 2
Grupo 6 — Métodos Computacionales

Este script genera el modelo estructural 3D completo del edificio.
Los datos de geometría se leen de data/building_geometry.json.
"""

import openseespy.opensees as ops
import json
import os


def load_geometry(filepath):
    """Cargar geometría del edificio desde JSON."""
    with open(filepath, 'r') as f:
        return json.load(f)


def create_model():
    """Crear modelo vacío."""
    ops.wipe()
    ops.model('basic', '-ndm', 3, '-ndf', 6)


def define_nodes(geometry):
    """Definir nodos del edificio."""
    for node_id, coords in geometry["nodes"].items():
        ops.node(int(node_id), coords["x"], coords["y"], coords["z"])
    print(f"Nodos definidos: {len(geometry['nodes'])}")


def define_supports(geometry):
    """Definir apoyos del edificio."""
    for node_id, fixity in geometry["supports"].items():
        ops.fix(int(node_id), *fixity)
    print(f"Apoyos definidos: {len(geometry['supports'])} nodos restringidos")


def define_rigid_diaphragms(geometry):
    """Definir diafragmas rígidos por piso."""
    for floor_id, diaphragm in geometry["diaphragms"].items():
        ops.rigidDiaphragm(diaphragm["perp_dir"], *diaphragm["nodes"])
    print(f"Diafragmas definidos: {len(geometry['diaphragms'])}")


def define_elements(geometry):
    """Definir elementos estructurales."""
    for elem_id, elem in geometry["elements"].items():
        ops.element(
            'elasticBeamColumn',
            int(elem_id),
            elem["nodes"][0],
            elem["nodes"][1],
            elem["E"],
            elem["A"],
            elem["Iy"],
            elem["Iz"],
            elem["G"],
            elem["J"],
            elem["geomTransf"]
        )
    print(f"Elementos definidos: {len(geometry['elements'])}")


def run_linear_analysis():
    """Ejecutar análisis lineal estático."""
    ops.system('BandSPD')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ops.analyze(1)
    ops.loadConst('-time', 0.0)
    print("Análisis completado")


def main():
    """Punto de entrada principal."""
    base_dir = os.path.dirname(__file__)
    geometry_path = os.path.join(base_dir, '..', 'data', 'building_geometry.json')

    print("Cargando geometría del edificio...")
    geometry = load_geometry(geometry_path)

    create_model()
    define_nodes(geometry)
    define_supports(geometry)
    define_rigid_diaphragms(geometry)
    define_elements(geometry)

    print("\nModelo listo para análisis de carga.")


if __name__ == "__main__":
    main()
