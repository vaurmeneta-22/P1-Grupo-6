# -*- coding: utf-8 -*-
"""
Parte E - primera demanda-capacidad (Grupo 6)

Caso COMBO selecto (1.2G + 1.0Q + 1.4EX + 1.4EY) — demanda-capacidad:

  1. Lee resultados/11_mapa_visor/analysis_map.js (fuerzas por caso, elementos
     y capacidad P-M por seccion).
  2. Para cada columna de hormigon calcula la demanda del caso COMBO:
       P  = |proyeccion de la fuerza resultante del extremo i/j sobre el eje
             del elemento|  (kN, compresion +)
       M  = |momento resultante| en el extremo con mayor momento  (kN*m)
  3. Elige la columna CRITICA con el mayor cociente de demanda (P_d, M_d)
     normalizado contra su curva P-M (interpolacion lineal del radio).
  4. Genera resultados/09_demanda_capacidad/demanda_capacidad_<id>.png:
     curva P-M (fiber) + punto (P_d, M_d) + cuantificacion del radio de
     sobreuso.

Convenciones: compresion +, traccion -. P en kN, M en kN*m.
"""

import json
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(REPO, "resultados", "11_mapa_visor", "analysis_map.js")
FIG = os.path.join(REPO, "resultados", "09_demanda_capacidad")
os.makedirs(FIG, exist_ok=True)

CASO = "COMBO"


def load_map():
    with open(MAP, "r", encoding="utf-8") as f:
        s = f.read()
    body = s[s.index("{"):]
    if body.rstrip().endswith(";"):
        body = body.rstrip()[:-1]
    return json.loads(body)


def axial(p, i, j):
    """Proyeccion de la fuerza global (p) sobre el eje del elemento (i->j)."""
    L = math.sqrt((j[0] - i[0]) ** 2 + (j[1] - i[1]) ** 2 + (j[2] - i[2]) ** 2) or 1.0
    ux = (j[0] - i[0]) / L
    uy = (j[1] - i[1]) / L
    uz = (j[2] - i[2]) / L
    # p en [Fx, Fy, Fz] segun fila del JSON (Fy es vertical)
    return p[0] * ux + p[1] * uz + p[2] * uy


def momento(p):
    """Modulo del momento resultante [Mx, My, Mz]."""
    return math.sqrt(p[3] ** 2 + p[4] ** 2 + p[5] ** 2)


def radio_demanda(P_d, M_d, Pcap, Mcap):
    """Radio de demanda sobre la curva P-M (interpola en P). Devuelve r>=0
    siendo r < 1 => dentro, r > 1 => fuera de capacidad."""
    if not Pcap:
        return None
    # buscar el punto de la curva con P mas cercano al P_d (interpolacion lineal)
    i = 0
    while i < len(Pcap) - 2 and Pcap[i + 1] < P_d:
        i += 1
    p0, p1 = Pcap[i], Pcap[i + 1]
    m0, m1 = Mcap[i], Mcap[i + 1]
    if p1 == p0:
        cap_m = (m0 + m1) / 2.0
    else:
        t = (P_d - p0) / (p1 - p0)
        cap_m = m0 + t * (m1 - m0)
    # cap: momento capaz para ese P; radio = demanda/capacidad en M
    return abs(M_d / cap_m) if cap_m != 0 else float("inf")


def main():
    d = load_map()
    elements = d["elements"]
    forces = d["forces"][CASO]
    cap = d["capacidad"]
    coords = d.get("node_coords", {})
    # curvatura del elemento (geometry de los ids: elements trae ni, nj)
    # los coordnode se indexan por id (str o int) segun el mapa
    results = []
    for el in elements:
        if el["type"] not in ("column", "steel_column"):
            continue
        eid = el["id"]
        f = forces.get(str(eid))
        if not f:
            continue
        i = f.get("i") or f.get("j")
        j = f.get("j") or f.get("i")
        if not i or not j:
            continue
        ni, nj = el["ni"], el["nj"]
        c_i = coords.get(str(ni)) or coords.get(ni)
        c_j = coords.get(str(nj)) or coords.get(nj)
        if not c_i or not c_j:
            continue
        P_i = axial(i, c_i, c_j)
        P_j = axial(j, c_i, c_j)
        P_d = max(abs(P_i), abs(P_j))            # axial demanda (compresion +)
        M_d = max(momento(i), momento(j))        # momento resultante demandado
        sec = el["section"]
        Pcap = Mcap = None
        if el["type"] == "column":
            clave = ("columna_id70" if el.get("id70")
                     else "columna_borde" if el.get("borde") else "columna")
            Pcap = cap.get(clave, {}).get("P")
            Mcap = cap.get(clave, {}).get("M")
        elif el["type"] == "steel_column":
            cur = cap.get("steel", {}).get(sec) or {}
            Pcap = cur.get("P")
            Mcap = cur.get("M")
        if not Pcap:
            Pcap = cap.get("muros", {}).get(sec, {}).get("P")
            Mcap = cap.get("muros", {}).get(sec, {}).get("M")
        r = radio_demanda(P_d, M_d, Pcap, Mcap)
        results.append({
            "id": eid, "type": el["type"], "section": sec,
            "P_d_kN": P_d, "M_d_kNm": M_d,
            "radio": r, "cap_sec": sec, "borde": bool(el.get("borde")),
            "id70": bool(el.get("id70")),
        })

    ##############################################################################
#   MUROS: misma demanda-capacidad con la curva P-M de la seccion tipificada #
##############################################################################
    mur_results = []
    for el in elements:
        if el["type"] != "wall":
            continue
        eid = el["id"]
        f = forces.get(str(eid))
        if not f:
            continue
        i = f.get("i") or f.get("j")
        j = f.get("j") or f.get("i")
        if not i or not j:
            continue
        ni, nj = el["ni"], el["nj"]
        c_i = coords.get(str(ni)) or coords.get(ni)
        c_j = coords.get(str(nj)) or coords.get(nj)
        if not c_i or not c_j:
            continue
        P_i = axial(i, c_i, c_j)
        P_j = axial(j, c_i, c_j)
        P_d = max(abs(P_i), abs(P_j))
        M_d = max(momento(i), momento(j))
        sec = el["section"]
        cur = cap.get("muros", {}).get(sec) or {}
        Pcap, Mcap = cur.get("P"), cur.get("M")
        if not Pcap:
            continue
        r = radio_demanda(P_d, M_d, Pcap, Mcap)
        mur_results.append({
            "id": eid, "type": "wall", "section": sec,
            "P_d_kN": P_d, "M_d_kNm": M_d, "radio": r,
        })

    mur_results.sort(key=lambda x: (x["radio"] if x["radio"] is not None else -1),
                     reverse=True)
    n_fuera = sum(1 for r in mur_results if r["radio"] is not None and r["radio"] > 1.0)
    print(f"\nMuros analizados: {len(mur_results)}  |  FUERA: {n_fuera}  "
          f"DENTRO: {len(mur_results) - n_fuera}")
    if mur_results:
        m = mur_results[0]
        rr = f"{m['radio']:.3f}" if m["radio"] is not None else "n/a"
        print(f"Muro critico: id={m['id']} {m['section']}  P={m['P_d_kN']:.1f} "
              f"M={m['M_d_kNm']:.1f} radio={rr}")

    results.sort(key=lambda x: (x["radio"] if x["radio"] is not None else -1),
                 reverse=True)
    crit = results[0]
    print("=" * 70)
    print(f"DEMANDA - CAPACIDAD  caso {CASO}  (columnas)")
    print("=" * 70)
    print(f"Columnas analizadas: {len(results)}")
    print(f"\nCRITICA: id={crit['id']}  tipo={crit['type']}  "
          f"seccion={crit['section']}")
    print(f"   P_d = {crit['P_d_kN']:.1f} kN  (axial compresion)")
    print(f"   M_d = {crit['M_d_kNm']:.1f} kN*m  (momento resultante)")
    print(f"   radio = {crit['radio']:.3f}  "
          f"({'DENTRO' if crit['radio'] < 1 else 'FUERA DE'} capacidad)")

    # top 10 para contexto
    print("\nTop 10 por radio:")
    for k in results[:10]:
        r = f"{k['radio']:.3f}" if k["radio"] is not None else "n/a"
        print(f"   id={k['id']:<5d} {k['type']:<13s} {k['section']:<10s}"
              f" P={k['P_d_kN']:8.1f} M={k['M_d_kNm']:8.1f} radio={r}")

    # figura de la critica
    sec = crit["section"]
    if crit["type"] == "column":
        clave = ("columna_id70" if crit.get("id70")
                 else "columna_borde" if crit.get("borde") else "columna")
        Pcap = cap.get(clave, {}).get("P")
        Mcap = cap.get(clave, {}).get("M")
    else:
        cur = cap.get("steel", {}).get(sec) or {}
        Pcap = cur.get("P")
        Mcap = cur.get("M")
    if Pcap and Mcap:
        plt.figure(figsize=(7, 5))
        plt.plot(Mcap, Pcap, "b-o", ms=3, lw=1.5, label="Capacidad P-M (fiber)")
        plt.plot([0, crit["M_d_kNm"]], [crit["P_d_kN"], crit["P_d_kN"]],
                 "k--", lw=0.8, alpha=0.5)
        plt.plot([crit["M_d_kNm"], crit["M_d_kNm"]], [0, crit["P_d_kN"]],
                 "k--", lw=0.8, alpha=0.5)
        plt.plot(crit["M_d_kNm"], crit["P_d_kN"], "ro", ms=9,
                 label=f"Demanda (P,M) = ({crit['P_d_kN']:.0f}, {crit['M_d_kNm']:.0f})")
        plt.xlabel("momento M  [kN*m]")
        plt.ylabel("carga axial P  [kN]  (compresion +)")
        plt.title(f"Demanda-Capacidad columna {sec} (id {crit['id']})  "
                  f"- caso {CASO}")
        plt.legend()
        plt.grid(alpha=0.3)
        plt.gca().invert_xaxis()
        plt.tight_layout()
        out = os.path.join(FIG, f"demanda_capacidad_{crit['id']}.png")
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"\nfigura -> resultados/09_demanda_capacidad/"
              f"demanda_capacidad_{crit['id']}.png")

        # guardar datos para el reporte
        dato = {
            "caso": CASO, "id": crit["id"], "tipo": crit["type"],
            "seccion": sec,
            "P_d_kN": crit["P_d_kN"], "M_d_kNm": crit["M_d_kNm"],
            "radio": crit["radio"],
            "Pcap_kN": Pcap, "Mcap_kNm": Mcap,
            "criterio": "P por proyeccion axial, M momento resultante "
                        "del extremo con mayor demanda",
        }
        jp = os.path.join(FIG, "demanda_capacidad_critica.json")
        with open(jp, "w", encoding="utf-8") as f:
            json.dump(dato, f, indent=1)
        print(f"datos  -> resultados/09_demanda_capacidad/"
              f"demanda_capacidad_critica.json")
    else:
        print(f"\n[aviso] no hay curva P-M para seccion {sec}; omito figura")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    main()