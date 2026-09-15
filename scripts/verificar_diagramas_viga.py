# -*- coding: utf-8 -*-
"""
Auditoria de consistencia de esfuerzos de extremo (viga 2D en su plano de
flexion) contra el cierre de una viga con carga uniforme equivalente.

Para cada viga con tributaria de tramo completo calculamos, en su plano de
flexion (momento sobre la binormal y corte en la direccion transversal):
  * wlosa  = carga de losa realmente aplicada como beamUniform (1.2 pG + 1.0 pQ)
  * w_eq   = wlosa + 1.2 * peso propio  (lo que usaba diagramas_2d)
  * wV     = (V_i + V_j)/L  -> carga implicada por el cierre de cortante
  * wM     = 2*M_i + 2*V_i*L + 2*M_j ... formula (ver abajo) -> carga implicada
            por el cierre de momento en el extremo j bajo 2 hipotesis de signo
            (+M_j vs -M_j)

Si el elemento es una viga Euler-Bernoulli con carga uniforme real = wlosa,
entonces (con la convencion de cara opuesta en j) debe cumplirse:
    M_i + V_i*L - (w_L/2)L^2  =  -M_j     (cierre de momento)
    V_i - w_V*L               =  -V_j     (cierre de corte)
es decir, existe w tal que wV ~ wlosa y wM ~ wlosa.

El script imprime una tabla y decide la hipotesis de signo que "cierra".
"""
import json
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS_COMBO = os.path.join(REPO, "resultados", "01_casos_base",
                                "edificio_full_results_COMBO.json")
EDIFICIO_JSON = os.path.join(REPO, "Edificio.json")


def beam_planar(tag, forces, tribu, eis, nodes):
    """Esfuerzos 2D de la viga en su plano de flexion vertical."""
    e = eis[tag]
    na, nb = e["node_i"], e["node_j"]
    a = [nodes[na][k] / 100.0 for k in range(3)]
    b = [nodes[nb][k] / 100.0 for k in range(3)]
    v = [b[k] - a[k] for k in range(3)]
    L = math.sqrt(sum(x * x for x in v))
    u = [x / L for x in v]
    bx, by, bz = (-u[1], u[0], 0.0)
    bl = math.sqrt(bx * bx + by * by) or 1.0
    B = (bx / bl, by / bl, 0.0)

    g = forces[str(tag)]
    gi, gj = g["global_i"], g["global_j"]
    M_i = sum(gi[3 + k] * B[k] for k in range(3))
    M_j = sum(gj[3 + k] * B[k] for k in range(3))
    V_i, V_j = gi[2], gj[2]
    N_i = sum(gi[k] * u[k] for k in range(3))

    t = tribu.get(str(tag), {})
    wlosa = 1.2 * t.get("p_G_kN_m", 0.0) + 1.0 * t.get("p_Q_kN_m", 0.0)
    bw, hh = [float(x) for x in e["section"].split("x")]
    sw = bw * hh / 1e6 * 25.0
    w_eq = wlosa + 1.2 * sw

    wV = (V_i + V_j) / L if L else 0.0
    # hipotesis A (misma convencion):  M_i+V_i L-(w/2)L^2 = M_j
    wM_A = 2.0 * (M_i + V_i * L - M_j) / L ** 2
    # hipotesis B (cara opuesta en j): M_i+V_i L-(w/2)L^2 = -M_j
    wM_B = 2.0 * (M_i + V_i * L + M_j) / L ** 2

    # cierre directo de cortante (residuo vs wlosa y vs w_eq)
    resS_vs_wlosa = abs((V_i + V_j) - wlosa * L) / max(wlosa * L, 1e-6)
    resS_vs_weq = abs((V_i + V_j) - w_eq * L) / max(w_eq * L, 1e-6)

    return {
        "tag": tag, "sec": e["section"], "L": round(L, 3),
        "M_i": M_i, "M_j": M_j, "V_i": V_i, "V_j": V_j, "N_i": N_i,
        "wlosa": wlosa, "w_eq": w_eq, "wV": wV, "wM_A": wM_A, "wM_B": wM_B,
        "resS_losa": resS_vs_wlosa, "resS_eq": resS_vs_weq,
    }


def main():
    res = json.load(open(RESULTADOS_COMBO, encoding="utf-8"))
    ct = json.load(open(EDIFICIO_JSON, encoding="utf-8"))
    forces = res["element_forces_global"]
    tribu = res.get("tributary_by_viga", {})
    nodes = {n["id"]: [n["x"], n["y"], n["z"]] for n in ct["nodes"]}
    eis = {e["id"]: e for e in ct["elements"]}

    rows = []
    for tag_str, t in tribu.items():
        tag = int(tag_str)
        e = eis.get(tag)
        if not e or e["type"] not in ("beam_x", "beam_y"):
            continue
        ap = t.get("aportes", [])
        span = sum(abs(a["tramo_m"][1] - a["tramo_m"][0]) for a in ap) if ap else 0.0
        na, nb = e["node_i"], e["node_j"]
        a = [nodes[na][k] / 100.0 for k in range(3)]
        b = [nodes[nb][k] / 100.0 for k in range(3)]
        L = math.dist(a, b)
        if L < 1e-6 or abs(span - L) / L > 0.25:
            continue
        if str(tag) not in forces:
            continue
        rows.append(beam_planar(tag, forces, tribu, eis, nodes))

    rows.sort(key=lambda r: r["tag"])
    print(f"{'tag':>4} {'sec':>6} {'L':>6} "
          f"{'M_i':>8} {'M_j':>8} {'V_i':>7} {'V_j':>7} "
          f"{'wLosa':>7} {'w_eq':>7} {'wV':>7} {'wM_A':>7} {'wM_B':>7} "
          f"{'resS_l':>6} {'resS_e':>6}")
    for r in rows:
        print(f"{r['tag']:>4} {r['sec']:>6} {r['L']:>6.2f} "
              f"{r['M_i']:>8.1f} {r['M_j']:>8.1f} {r['V_i']:>7.1f} {r['V_j']:>7.1f} "
              f"{r['wlosa']:>7.2f} {r['w_eq']:>7.2f} {r['wV']:>7.2f} "
              f"{r['wM_A']:>7.2f} {r['wM_B']:>7.2f} "
              f"{r['resS_losa']*100:>6.1f} {r['resS_eq']*100:>6.1f}")

    print("\nRazon wM_B vs wV  (===1 -> viga con carga puramente uniforme, "
          "signo cara opuesta en j)")
    print("Razon wM_A vs wV  (===1 -> viga con carga puramente uniforme, "
          "misma convencion)")
    for r in rows:
        razB = r["wM_B"] / r["wV"] if abs(r["wV"]) > 1e-6 else float("nan")
        razA = r["wM_A"] / r["wV"] if abs(r["wV"]) > 1e-6 else float("nan")
        print(f"tag {r['tag']:>4}: wM_B/wV={razB:5.2f}   wM_A/wV={razA:5.2f}")

    # Y conteo final: cuantas vigas cumplen simultaneamente los 3 cierres
    okB = sum(1 for r in rows
              if abs(r["wM_B"] / r["wV"] - 1.0) < 0.03
              and abs(r["wV"] / max(r["wlosa"], 1e-9) - 1.0) < 0.03)
    okA = sum(1 for r in rows
              if abs(r["wM_A"] / r["wV"] - 1.0) < 0.03
              and abs(r["wV"] / max(r["wlosa"], 1e-9) - 1.0) < 0.03)
    print(f"\nVigas con wM_B ~ wV ~ wlosa (cara opuesta): {okB}/{len(rows)}")
    print(f"Vigas con wM_A ~ wV ~ wlosa (misma convencion): {okA}/{len(rows)}")


if __name__ == "__main__":
    sys.exit(main())