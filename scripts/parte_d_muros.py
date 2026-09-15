"""
Extiende la Parte D: curvas P-M (fiber, OpenSees) para TODOS los muros reales
del contrato (secciones `sections.WALLS`), usando la regla proporcional de
enfierradura de muro_tipificado(). El 30x356 (MURO) se genera en
parte_d_fiber.py y se reutiliza tal cual (no se regenera aqui).

Para cada muro escribe resultados/07_capacidad/pm_muros/pm_<clave_contrato>.json
con el mismo formato de pm_muro_30x356.json: {"seccion", "P_kN_fiber", "M_kNm_fiber"}.

La grilla de carga axial es proporcional a la CAPACIDAD PURA DE COMPRESION de
la seccion de fibras (pico de la curva N-eps, > 0.85*f'c*Ag por el acero) y las
puntas quedan cerradas: traccion pura (-fy*As, 0) en la base y compresion pura
(0, Pcap_fibra) en el tope -- ver analysis.pm_completa.
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

FIG_DIR = os.path.join(BASE, "resultados", "07_capacidad", "pm_muros")
os.makedirs(FIG_DIR, exist_ok=True)


def guardar_pm(section, P, M):
    fname = f"pm_{section['nombre']}.json"
    path = os.path.join(FIG_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"tipo": "interaccion_PM",
                   "seccion": section["nombre"],
                   "P_kN_fiber": P, "M_kNm_fiber": M,
                   "P_trac_kN": P[0], "P_comp_kN": P[-1],
                   "modelo": "OpenSees fiber (muro_tipificado), puntas cerradas"},
                  f, indent=1, ensure_ascii=False)
    print(f"  json -> {os.path.relpath(path, BASE)}")
    return path


def guardar_png(section, P, M):
    path = os.path.join(FIG_DIR, f"pm_{section['nombre']}.png")
    plt.figure(figsize=(7, 5))
    M_full = list(M) + list(reversed([-m for m in M]))
    P_full = list(P) + list(reversed(P))
    plt.plot(M_full, P_full, "b-o", ms=3, lw=1.5)
    plt.xlabel("momento M [kN*m]")
    plt.ylabel("carga axial P [kN] (compresion +)")
    plt.title(f"Interaccion P-M - {section['nombre']} (fiber)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  png  -> {os.path.relpath(path, BASE)}")


def main():
    # Solo queda la version actual: borra curvas previas del destino, salvo
    # pm_muro_30x356 (lo genera parte_d_fiber.py; aqui no se regenera).
    for f in os.listdir(FIG_DIR):
        if f.startswith("pm_") and f.endswith(".json") or \
           (f.startswith("pm_") and f.endswith(".png")):
            if f == "pm_muro_30x356.json" or f == "pm_muro_30x356.png":
                continue
            os.remove(os.path.join(FIG_DIR, f))
    print(f"== Curvas P-M de {len(sections.WALLS)} muros ==")
    for sec in sections.WALLS:
        print(f"-- {sec['nombre']:10s}  bw={sec['bw']:.0f} Lw={sec['Lw']:.0f} "
              f"| borde={sec['borde']:.0f} nFY={sec['nFY']}")
        P, M = analysis.pm_completa(sec, verbose=True)
        guardar_pm(sec, P, M)
        guardar_png(sec, P, M)
    print("OK")


if __name__ == "__main__":
    main()