# -*- coding: utf-8 -*-
"""
Verificacion RC - cuadro comparativo (Parte D / Grupo 6)

Compara puntos caracteristicos de la interaccion P-M obtenidos por el modelo
de fibras (OpenSees, analysis_map.js / figures JSON) contra el bloque
rectangular ACI/NCh (verification_ha.py):

  * capacidad axial pura  P0
  * momento balanceado    (P_b, M_b)
  * momento en flexion pura (P=0)

Guarda resultados/08_verificacion/verificacion_rc.json con una tabla
consolidada por seccion (columna 70x70 y muro 30x356) para el reporte.

Nota: P0 del fiber no existe en la grilla de P-M cargada; se usa P0 analitico
(bloque) como referencia y el punto fiber de mayor P como "capacidad casi
pura" si se desea comparar. La comparacion principal es M_balanceado y
M_flexion_pura, que si estan en ambas fuentes.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from opensees.fiber_sections import verification_ha as vh  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP_7 = os.path.join(REPO, "resultados", "07_capacidad")
FIG = os.path.join(REPO, "resultados", "08_verificacion")
os.makedirs(FIG, exist_ok=True)


def m_flexion_pura(P, M):
    """Momento en el punto con P mas cercano a 0."""
    i = min(range(len(P)), key=lambda k: abs(P[k]))
    return P[i], M[i]


def pico(P, M):
    i = max(range(len(M)), key=lambda k: abs(M[k]))
    return P[i], abs(M[i])


def punto_en_p(P, M, P_target):
    """(P, M) interpolado de la curva en la P dada."""
    if P_target <= P[0]:
        return P[0], M[0]
    if P_target >= P[-1]:
        return P[-1], M[-1]
    i = 0
    while i < len(P) - 2 and P[i + 1] < P_target:
        i += 1
    p0, p1 = P[i], P[i + 1]
    m0, m1 = M[i], M[i + 1]
    t = (P_target - p0) / (p1 - p0) if p1 != p0 else 0.0
    return P_target, m0 + t * (m1 - m0)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    cfg = [
        ("columna_70x70", True,
         os.path.join(CAP_7, "pm_columnas", "pm_columna_70x70.json")),
        ("columna_borde_70x70", "columna_borde",
         os.path.join(CAP_7, "pm_columnas", "pm_columna_borde_70x70.json")),
        ("muro_30x356", False,
         os.path.join(CAP_7, "pm_muros", "pm_muro_30x356.json")),
    ]
    reporte = {}
    print("=" * 78)
    print("VERIFICACION RC  -  puntos caracteristicos (bloque ACI/NCh vs fiber)")
    print("=" * 78)
    for nombre, cfg_col, ruta in cfg:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
        P, M = data["P_kN_fiber"], data["M_kNm_fiber"]
        # analitico (bloque rectangular)
        P0 = vh.capacidad_pura_axial(cfg_col)
        Pb_a, Mb_a = vh.punto_momento_balanceado(cfg_col)
        Pph_a, Mph_a = vh.interaccion(cfg_col)  # PHA, MHA curvas
        # del fiber
        Pb_f, Mb_f = punto_en_p(P, M, Pb_a)     # evalua fiber en P balanceada analit
        Pp_f, Mp_f = m_flexion_pura(P, M)       # flexion pura
        # del analitico: flexion pura (P mas cerca de 0)
        i0 = min(range(len(Pph_a)), key=lambda k: abs(Pph_a[k]))
        M_pura_a = Mph_a[i0]

        fila = {
            "seccion": nombre,
            "P0": {"analitico_kN": P0},
            "balanceado": {
                "P_analitico_kN": Pb_a, "M_analitico_kNm": Mb_a,
                "M_fiber_en_Pb_kNm": Mb_f,
                "dif_rel_pct": 100.0 * (Mb_f - Mb_a) / Mb_a if Mb_a else None,
            },
            "flexion_pura": {
                "M_analitico_kNm": M_pura_a,
                "M_fiber_kNm": Mp_f,
                "dif_rel_pct": 100.0 * (Mp_f - M_pura_a) / M_pura_a if M_pura_a else None,
            },
            "pico_fiber": {"P_kN": Pb_f, "M_kNm": Mp_f},
        }
        reporte[nombre] = fila

        print(f"\n  {nombre}")
        print(f"    P0 (bloque)              = {P0:12.1f} kN")
        print(f"    balanceado analitico     = P {Pb_a:8.1f}  M {Mb_a:8.1f}")
        print(f"    M fiber @ P_bal          = {Mb_f:8.1f}  "
              f"dif {fila['balanceado']['dif_rel_pct']:.1f}%")
        print(f"    flex.pura analitico      = M {M_pura_a:8.1f}")
        print(f"    flex.pura fiber          = M {Mp_f:8.1f}  "
              f"dif {fila['flexion_pura']['dif_rel_pct']:.1f}%")
        print(f"    pico fiber               = P {Pb_f:8.1f}  M {Mp_f:8.1f}")

    with open(os.path.join(FIG, "verificacion_rc.json"), "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=1)
    print(f"\n-> resultados/08_verificacion/verificacion_rc.json")


if __name__ == "__main__":
    main()