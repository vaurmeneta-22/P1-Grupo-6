"""
Parte D - capacidad de hormigon armado (fiber sections vs bloque ACI)
(Grupo 6)

Genera en resultados/07_capacidad/ los resultados de la Parte D:
  - curva mom-curvatura (M-phi) de la seccion representativa columna_70x70,
  - interaccion P-M de la columna y del muro_30x356 (OpenSees, fibers),
  - comparacion con la verificacion independiente del curso H.A.
    (bloque rectangular alpha1/beta1, compatibility of strains).

Salidas (resultados/07_capacidad/):
  * mom_curv/mom_curv_columna_70x70.json / .png
  * pm_columnas/pm_columna_70x70.json / .png   (fiber + HA)
  * pm_muros/pm_muro_30x356.json / .png     (fiber + HA)
"""

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "opensees"))

from fiber_sections import analysis, sections, verification_ha as vh  # noqa: E402

CAP_7 = os.path.join(BASE, "resultados", "07_capacidad")
FIG_DIR = {
    "mom_curv": os.path.join(CAP_7, "mom_curv"),
    "pm": os.path.join(CAP_7, "pm_columnas"),   # contenedor segun caso
}


def dir_de(nombre, section):
    """Por el prefijo del archivo: mom_curv_* -> mom_curv; pm columna ->
    pm_columnas; pm muro -> pm_muros."""
    if nombre.startswith("mom_curv"):
        return os.path.join(CAP_7, "mom_curv")
    if "muro" in section["nombre"]:
        return os.path.join(CAP_7, "pm_muros")
    return os.path.join(CAP_7, "pm_columnas")


def guardar_json(nombre, section, datos):
    d = dir_de(nombre, section)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{nombre}_{section['nombre']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=1, ensure_ascii=False)
    print(f"  json -> {os.path.relpath(path, BASE)}")
    return path


def guardar_png(nombre, section, title):
    d = dir_de(nombre, section)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{nombre}_{section['nombre']}.png")
    plt.title(title)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  png  -> {os.path.relpath(path, BASE)}")


def curva_mom_curv_columna():
    print("== Curva M-phi de la columna 70x70 (P=0) ==")
    phi, M, n = analysis.mom_curv(sections.COLUMNA)
    print(f"  pasos ok={n}, phi_max={phi[-1]:.5f} 1/m, M_ult={M[-1]:.1f} kN*m")
    plt.figure(figsize=(7, 5))
    plt.plot(phi, M, "b-", lw=1.6, label="OpenSees fiber (Concrete02+Steel01)")
    plt.xlabel("curvatura $\\phi$  [1/m]")
    plt.ylabel("momento M  [kN* m]")
    plt.legend()
    plt.axvline(phi[-1], color="r", ls="--", lw=1)
    guardar_json("mom_curv", sections.COLUMNA,
                 {"tipo": "mom_curv", "seccion": sections.COLUMNA["nombre"],
                  "P_kN": 0.0, "phi_1m": phi, "M_kNm": M,
                  "n_ok": n, "M_ult_kNm": M[-1],
                  "modelo": "OpenSees dispBeamColumn + fiber"})
    guardar_png("mom_curv", sections.COLUMNA,
                f"Momento-curvatura columna {sections.COLUMNA['nombre']}")


def interaccion(section, cfg_col, grid, nombre, titulo, figura=True):
    print(f"== Interaccion P-M {section['nombre']} ==")
    P, M = analysis.pm_interaction(section, grid, verbose=True)
    Ph, Mh = vh.interaccion(cfg_col)
    a1, b1 = vh._constantes()
    if figura:
        plt.figure(figsize=(7, 5))
        plt.plot(M, P, "b-o", ms=3, lw=1.5,
                 label="OpenSees fiber (capacidad M-phi)")
        plt.plot(Mh, Ph, "r-s", ms=2.5, lw=1.2,
                 label="H.A. bloque rectangular $\\alpha_1,\\beta_1$")
        plt.xlabel("momento M  [kN* m]")
        plt.ylabel("carga axial P  [kN]  (compresion +)")
        plt.legend()
        plt.gca().invert_xaxis()
    guardar_json(nombre, section, {
        "tipo": "interaccion_PM",
        "seccion": section["nombre"],
        "P_kN_fiber": P, "M_kNm_fiber": M,
        "P_kN_HA": Ph, "M_kNm_HA": Mh,
        "alpha1": a1, "beta1": b1,
        "modelo": "OpenSees fiber vs bloque rectangular ACI/NCh"})
    if figura:
        guardar_png(nombre, section, titulo)
    return P, M


def main():
    curva_mom_curv_columna()
    interaccion(sections.COLUMNA, True,
                [0, 500, 1500, 2500, 3500, 4500, 5000, 5500, 6000,
                 7000, 8000, 9000, 10000, 11000, 12000, 13000,
                 14000, 15000, 16000, 17000, 18000, 19000],
                "pm", "Interaccion P-M - columna 70x70")
    interaccion(sections.COLUMNA_BORDE, "columna_borde",
                [0, 500, 1500, 2500, 3500, 4500, 5000, 5500, 6000,
                 7000, 8000, 9000, 10000, 12000, 14000, 16000,
                 18000, 20000, 22000, 23500],
                "pm", "Interaccion P-M - columna 70x70 portico extremo")
    interaccion(sections.MURO, False,
                [0, 2000, 5000, 8000, 11000, 14000, 17000, 20000,
                 23000, 26000, 29000, 32000, 35000],
                "pm", "Interaccion P-M - muro 30x356")
    interaccion(sections.COLUMNA_ID70, "columna_id70",
                [0, 500, 1500, 2500, 3500, 4500, 5000, 5500, 6000,
                 7000, 8000, 9000, 10000, 12000, 14000, 16000,
                 18000, 20000, 22000, 23500, 24000],
                "pm", "Interaccion P-M - columna id=70", figura=False)
    print("OK")


if __name__ == "__main__":
    main()