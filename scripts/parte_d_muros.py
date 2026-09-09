"""
Extiende la Parte D: curvas P-M (fiber, OpenSees) para TODOS los muros reales
del contrato (secciones `sections.WALLS`), usando la regla proporcional de
enfierradura de muro_tipificado(). El 30x356 (MURO) se genera en
parte_d_fiber.py y se reutiliza tal cual (no se regenera aqui).

Para cada muro escribe figures/pm_<clave_contrato>.json con el mismo formato
de pm_muro_30x356.json: {"seccion", "P_kN_fiber", "M_kNm_fiber"}.

La grilla de carga axial es proporcional a la capacidad axial bruta
P0 ~ 0.85*f'c*Ag (kN) para no fijar valores que no escalan a muros largos
(p.ej. 30x1000): 13 puntos de 0 a ~0.97*P0.
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "opensees"))

from fiber_sections import analysis, sections  # noqa: E402
from fiber_sections.verification_ha import F_C  # noqa: E402

FIG_DIR = os.path.join(BASE, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

FRACCIONES_P = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.97]


def p0_bruto_kN(section):
    """Capacidad axial bruta P0 = 0.85*f'c*Ag, en kN (para la grilla)."""
    Ag = section["bw"] * section["Lw"]          # mm2
    return 0.85 * F_C * Ag / 1e3


def grid_para(section):
    P0 = p0_bruto_kN(section)
    return [round(P0 * f, 1) for f in FRACCIONES_P]


def guardar_pm(section, P, M):
    fname = f"pm_{section['nombre']}.json"
    path = os.path.join(FIG_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tipo": "interaccion_PM",
                   "seccion": section["nombre"],
                   "P_kN_fiber": P, "M_kNm_fiber": M,
                   "modelo": "OpenSees fiber (muro_tipificado)"},
                  f, indent=1, ensure_ascii=False)
    print(f"  json -> {os.path.relpath(path, BASE)}")
    return path


def guardar_png(section, P, M):
    path = os.path.join(FIG_DIR, f"pm_{section['nombre']}.png")
    plt.figure(figsize=(7, 5))
    plt.plot(M, P, "b-o", ms=3, lw=1.5)
    plt.xlabel("momento M [kN*m]")
    plt.ylabel("carga axial P [kN] (compresion +)")
    plt.title(f"Interaccion P-M - {section['nombre']} (fiber)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  png  -> {os.path.relpath(path, BASE)}")


def main():
    print(f"== Curvas P-M de {len(sections.WALLS)} muros ({F_C} MPa) ==")
    for sec in sections.WALLS:
        print(f"-- {sec['nombre']:10s}  bw={sec['bw']:.0f} Lw={sec['Lw']:.0f} "
              f"| borde={sec['borde']:.0f} nFY={sec['nFY']}")
        grid = grid_para(sec)
        P, M = analysis.pm_interaction(sec, grid, verbose=True)
        guardar_pm(sec, P, M)
        guardar_png(sec, P, M)
    print("OK")


if __name__ == "__main__":
    main()