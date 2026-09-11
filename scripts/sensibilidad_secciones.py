# -*- coding: utf-8 -*-
"""
Sensibilidad de discretizacion M-phi (Parte D / Grupo 6)

Corre la curva momento-curvatura de la columna 70x70 y del muro 30x356 con
varias mallas de fibras (nFY x nFZ) y compara:

  - M_ult   : momento ultimo (pico de la curva)      [kN*m]
  - phi_ult : curvatura en el corte por concreto      [1/m]
  - EI      : rigidez inicial (pendiente de la zona elastica)

Objetivo: demostrar que la malla nominal (columna 24x8, muro 40x6) ya es
convergente, y cuantificar el cambio relativo respecto a la malla fina.

Salida: resultados/07_capacidad/sensibilidad/sensibilidad_secciones.json
"""

import json
import math
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "opensees"))

from fiber_sections import analysis, sections  # noqa: E402

FIG = os.path.join(BASE, "resultados", "07_capacidad", "sensibilidad")
os.makedirs(FIG, exist_ok=True)


def rigidez_inicial(phi, M):
    """Rigidez inicial EI = dM/dphi en el tramo pseudo-elastico.
    Ajusta la recta con los primeros puntos hasta M=25% del pico."""
    if not phi:
        return None
    peak = max(abs(m) for m in M)
    n = min(len(phi) - 1, 30)
    for k in range(2, len(phi)):
        if abs(M[k]) > 0.25 * peak:
            n = k
            break
    n = max(n, 2)
    # regresion lineal simple sobre phi[0:n], M[0:n]
    sx = sum(phi[:n])
    sy = sum(M[:n])
    sxx = sum(x * x for x in phi[:n])
    sxy = sum(x * y for x, y in zip(phi[:n], M[:n]))
    den = n * sxx - sx * sx
    if den == 0:
        return None
    return (n * sxy - sx * sy) / den


def correr(desc, section, mallas, P_N=0.0, label="columna"):
    out = []
    for k, (nFY, nFZ) in enumerate(mallas):
        s = dict(section)
        s["nFY"] = nFY
        s["nFZ"] = nFZ
        phi, M, n_ok = analysis.mom_curv(s, P=P_N * 1000.0)
        if not M:
            print(f"  {desc:>12s} nFY={nFY:3d} nFZ={nFZ:2d}: SIN CONVERGENCIA")
            continue
        peak_idx = max(range(len(M)), key=lambda kk: abs(M[kk]))
        M_ult = abs(M[peak_idx])
        Phi_ult = phi[peak_idx]
        EI = rigidez_inicial(phi, M)
        out.append({"nFY": nFY, "nFZ": nFZ, "n_fib": nFY * nFZ,
                    "M_ult_kNm": M_ult, "phi_ult_1m": Phi_ult,
                    "EI_kNm2": EI, "pasos_ok": n_ok,
                    "P_kN": P_N})
        print(f"  {desc:>12s} nFY={nFY:3d} nFZ={nFZ:2d} "
              f"-> M_ult={M_ult:9.2f}  phi_ult={Phi_ult:8.5f}  "
              f"EI={EI and EI/1e6:8.2f} MN*m2  (pasos={n_ok})")
    # cambio relativo vs la malla mas fina
    if out:
        ref = out[-1]
        for o in out:
            o["dM_ult_rel_pct"] = 100.0 * (o["M_ult_kNm"] - ref["M_ult_kNm"]) / ref["M_ult_kNm"]
            o["dPhi_rel_pct"] = 100.0 * (o["phi_ult_1m"] - ref["phi_ult_1m"]) / ref["phi_ult_1m"] if ref["phi_ult_1m"] else None
    return out


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 70)
    print("SENSIBILIDAD DE DISCRETIZACION  (momento-curvatura)")
    print("=" * 70)

    res = {}

    print("\n-- Columna 70x70  (P = 0) --")
    col_mallas = [[12, 4], [24, 8], [48, 16], [96, 32]]
    res["columna_70x70"] = correr("columna", sections.COLUMNA, col_mallas)

    print("\n-- Muro 30x356  (P = 0) --")
    mur_mallas = [[20, 4], [40, 6], [60, 8], [80, 12]]
    res["muro_30x356"] = correr("muro", sections.MURO, mur_mallas)

    op = os.path.join(FIG, "sensibilidad_secciones.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"\n-> resultados/07_capacidad/sensibilidad/sensibilidad_secciones.json")
    print("OK")


if __name__ == "__main__":
    main()