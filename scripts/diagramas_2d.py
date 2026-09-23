# -*- coding: utf-8 -*-
"""
Diagramas de esfuerzos 2D (momento, axial y corte) de elementos representativos
del modelo completo, para el caso COMBO.

  * Viga interior:  M(x) parabolico (carga uniforme = losa tributaria que el FE
    aplica como beamUniform + peso propio nodal anclado en los extremos), V(x)
    lineal, N(x) ~ 0.  Anclado en los esfuerzos de extremo i del FE (momento
    proyectado en el plano vertical y corte).  El extremo j se reporta en el FE
    con "cara opuesta" (accion sobre el elemento), por lo que la parabola
    cierra contra -M_j y -V_j; la seleccion exige cierre de corte Y de momento.
  * Columna y muro criticos:  N constante, V constante y M transversal al eje
    lineal entre extremos (mismas demandas usadas en el chequeo P-M).

SALIDAS:
  * PNG en resultados/10_figuras/  (solo cuando se ejecuta como script).
  * `exportar_datos()`: dict de arrays para incrustar en analysis_map.js
    (pestana "Diagramas" del visor).

Unidades: kN, kN*m, m.  Caso COMBO con lambdas (G=1.2, Q=1.0, EX=EY=1.4).
"""
import json
import math
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTADOS_DIR = os.path.join(REPO, "resultados", "01_casos_base")
CASOS = [
    ("COMBO", "edificio_full_results_COMBO.json"),
    ("G", "edificio_full_results.json"),
    ("Q", "edificio_full_results_Q.json"),
    ("EX", "edificio_full_results_EX.json"),
    ("EY", "edificio_full_results_EY.json"),
]
RESULTADOS_COMBO = os.path.join(RESULTADOS_DIR, "edificio_full_results_COMBO.json")
EDIFICIO_JSON = os.path.join(REPO, "Edificio.json")
OUT_DIR = os.path.join(REPO, "resultados", "10_figuras")

# Elementos representativos elegidos por el grupo (mismos en los 5 casos)
VIGA_TAG = 147
COL_TAG = 261
MURO_TAG = 446

PISO_Z = {"Subterraneo": 0.0, "Piso 1": 3.56, "Piso 2": 7.12, "Piso 3": 10.68,
          "Piso 4": 14.24, "Techo": 17.80}


def piso_de_z(z_m):
    nombre = "Subterraneo"
    for k, z in PISO_Z.items():
        if z_m >= z - 1e-9:
            nombre = k
    return nombre


def fe_coords(e, nodes):
    """Coordenadas OpenSees (X, Y_plano, Z_altura) en m de los extremos i/j."""
    if e["type"] == "wall":
        a = [e["xi"] / 100.0, e["zi"] / 100.0, e["yi"] / 100.0]
        b = [e["xj"] / 100.0, e["zj"] / 100.0, e["yj"] / 100.0]
        return a, b
    na, nb = e["node_i"], e["node_j"]
    a = [nodes[na][k] / 100.0 for k in range(3)]
    b = [nodes[nb][k] / 100.0 for k in range(3)]
    return a, b


def _q_caso(caso, t):
    """Carga repartida (beamUniform) que el FE aplica en cada caso, en kN/m."""
    pG = t.get("p_G_kN_m", 0.0)
    pQ = t.get("p_Q_kN_m", 0.0)
    if caso == "G":
        return pG
    if caso == "Q":
        return pQ
    if caso in ("EX", "EY"):
        return 0.0
    if caso == "COMBO":
        return 1.2 * pG + 1.0 * pQ
    return 0.0


def datos_viga(tag, e, nodes, forces, q):
    pa, pb = fe_coords(e, nodes)
    v = [pb[k] - pa[k] for k in range(3)]
    L = math.sqrt(sum(x * x for x in v))
    u = [x / L for x in v]
    b = [-u[1], u[0], 0.0]
    bl = math.sqrt(b[0] ** 2 + b[1] ** 2) or 1.0
    b = [b[0] / bl, b[1] / bl, 0.0]

    gi = forces[str(tag)]["global_i"]
    gj = forces[str(tag)]["global_j"]
    Mb_i = sum(gi[3 + k] * b[k] for k in range(3))
    Mb_j = sum(gj[3 + k] * b[k] for k in range(3))
    Vz_i, Vz_j = gi[2], gj[2]
    N_i = sum(gi[k] * u[k] for k in range(3))

    # q es la carga repartida REAL del caso (solo la losa tributaria, que es lo
    # unico aplicado como beamUniform; el peso propio es nodal y no curva el
    # diagrama). El extremo j del FE se reporta en "cara opuesta" (accion sobre
    # el elemento), por lo que la parabola debe cerrar contra -M_j y -V_j.
    W = q * L
    residual = abs((Vz_i + Vz_j) - W) / max(W, 1e-6)
    resMJ = abs(Mb_i + Vz_i * L - 0.5 * q * L * L + Mb_j) / max(abs(Mb_j), 1e-6)

    nx = 201
    x = [L * i / (nx - 1) for i in range(nx)]
    M = [Mb_i + Vz_i * xx - 0.5 * q * xx * xx for xx in x]
    V = [Vz_i - q * xx for xx in x]
    N = [N_i] * nx
    return {
        "tag": tag, "tipo": e["type"], "seccion": e["section"], "L": L,
        "q": q, "resid": residual, "resMJ": resMJ,
        "x": x, "M": M, "V": V, "N": N,
        "piso": piso_de_z(pa[2]), "coords_i": pa, "coords_j": pb,
        "extremos": {"M_i": Mb_i, "M_j": Mb_j, "V_i": Vz_i, "V_j": Vz_j, "N": N_i},
    }


def datos_vertical(tag, e, nodes, forces):
    pa, pb = fe_coords(e, nodes)
    v = [pb[k] - pa[k] for k in range(3)]
    L = math.sqrt(sum(x * x for x in v))
    u = [x / L for x in v]
    gi = forces[str(tag)]["global_i"]
    gj = forces[str(tag)]["global_j"]

    Ni = sum(gi[k] * u[k] for k in range(3))
    Nj = sum(gj[k] * u[k] for k in range(3))
    Mi, Mj = gi[3:], gj[3:]
    Mui = sum(Mi[k] * u[k] for k in range(3))
    Muj = sum(Mj[k] * u[k] for k in range(3))
    Mti = math.sqrt(sum((Mi[k] - Mui * u[k]) ** 2 for k in range(3)))
    Mtj = math.sqrt(sum((Mj[k] - Muj * u[k]) ** 2 for k in range(3)))
    Vi = math.sqrt(sum((gi[k] - Ni * u[k]) ** 2 for k in range(3)))
    Vj = math.sqrt(sum((gj[k] - Nj * u[k]) ** 2 for k in range(3)))

    nx = 2
    return {
        "tag": tag, "tipo": e["type"], "seccion": e["section"], "L": L,
        "x": [0.0, L], "N": [-Ni, -Ni], "V": [Vi, Vi], "M": [Mti, Mtj],
        "N_int": -Ni, "V_int": (Vi + Vj) / 2.0,
        "piso": piso_de_z(pa[2]), "coords_i": pa, "coords_j": pb,
        "extremos": {"N_i": Ni, "N_j": Nj,
                     "M_t_i": Mti, "M_t_j": Mtj, "V_i": Vi, "V_j": Vj},
    }


def estilo(ax, titulo, ylabel, unit):
    ax.grid(True, alpha=0.3, ls="--")
    ax.set_title(titulo, fontsize=10)
    ax.set_ylabel("%s [%s]" % (ylabel, unit), fontsize=9)
    ax.axhline(0, color="k", lw=0.8)


def plot_viga(d, caso):
    """Diagrama clásico M(x), V(x) y N(x) de una viga."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8.2, 9.5), sharex=True,
                                     constrained_layout=True)
    x, M, V, N, L = d["x"], d["M"], d["V"], d["N"], d["L"] * 100.0  # cm

    a1.fill_between(x, M, color="#1f77b4", alpha=0.35)
    a1.plot(x, M, color="#0d5a91", lw=1.8)
    im = max(range(len(M)), key=lambda k: abs(M[k]))
    a1.annotate("M_max = %+.1f kN·m" % M[im], (x[im], M[im]),
                textcoords="offset points", xytext=(8, 6), fontsize=8)
    estilo(a1, "Diagrama de momento flector  M(x) — losa tributaria aplicada q=%.2f kN/m"
               % d["q"], "Momento", "kN·m")

    a2.fill_between(x, V, color="#d62728", alpha=0.35)
    a2.plot(x, V, color="#8f1010", lw=1.8)
    iv = max(range(len(V)), key=lambda k: abs(V[k]))
    a2.annotate("V_max = %+.1f kN" % V[iv], (x[iv], V[iv]),
                textcoords="offset points", xytext=(8, 6), fontsize=8)
    estilo(a2, "Diagrama de esfuerzo de corte  V(x)", "Corte", "kN")

    a3.plot(x, N, color="#2ca02c", lw=1.8)
    a3.fill_between(x, N, color="#2ca02c", alpha=0.3)
    estilo(a3, "Diagrama de esfuerzo axial  N(x) (+ = traccion)", "Axial", "kN")

    a3.set_xlabel("Posicion a lo largo de la viga  [cm]", fontsize=9)
    fig.suptitle(("Viga id=%d  %s  %s  |  L=%.2f m  |  %s  |  Caso %s\n"
                   "Fuerzas de extremo i del FE — el extremo j se reporta en "
                   "cara opuesta (cierre contra -M_j/-V_j, verificado %.0f%%/%.0f%%)") %
                  (d["tag"], d["tipo"], d["seccion"], d["L"], d["piso"], caso,
                   d["resid"] * 100, d["resMJ"] * 100), fontsize=10)


def plot_vertical(d, nombre, caso):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(8.2, 9.5),
                                     constrained_layout=True)
    x, N, V, M, L = d["x"], d["N"], d["V"], d["M"], d["L"] * 100.0
    q0, q1 = d["coords_i"], d["coords_j"]

    a1.plot(x, N, color="#2ca02c", lw=2.0)
    a1.fill_between(x, N, color="#2ca02c", alpha=0.3)
    a1.annotate("N = %+.1f kN" % N[0], (x[0], N[0]),
                textcoords="offset points", xytext=(6, 6), fontsize=8)
    estilo(a1, "Diagrama de esfuerzo axial  N(x)  (+ = traccion)", "Axial", "kN")

    a2.plot(x, V, color="#d62728", lw=2.0)
    a2.fill_between(x, V, color="#d62728", alpha=0.3)
    a2.annotate("V = %+.1f kN" % V[0], (x[0], V[0]),
                textcoords="offset points", xytext=(6, 6), fontsize=8)
    estilo(a2, "Diagrama de esfuerzo de corte transversal  V(x)", "Corte", "kN")

    a3.plot(x, M, color="#1f77b4", lw=2.0)
    a3.fill_between(x, M, color="#1f77b4", alpha=0.35)
    im = max(range(len(M)), key=lambda k: M[k])
    a3.annotate("M_max = %.1f kN·m" % M[im], (x[im], M[im]),
                textcoords="offset points", xytext=(6, -14), fontsize=8)
    estilo(a3, "Diagrama de momento transversal al eje  M(x)", "Momento", "kN·m")

    a3.set_xlabel("Posicion a lo largo del eje Z (altura)  [cm]", fontsize=9)
    fig.suptitle(("%s id=%d  %s  %s  |  L=%.2f m  |  base z=%.2f m  (%s)  |  Caso %s\n"
                   "Esfuerzos de extremo del elemento FE (i = base)") %
                  (nombre, d["tag"], d["tipo"], d["seccion"], d["L"],
                   d["coords_i"][2], d["piso"], caso), fontsize=10)


def exportar_datos(tag=""):
    """Devuelve el dict `diagramas` para analysis_map.js: 5 casos x 3 elementos.
    Con `tag` (corrida de modificacion) prefiere los resultados etiquetados
    edificio_full_results_<tag>_*.json y cae a la linea base si no existen."""
    with open(EDIFICIO_JSON, encoding="utf-8") as f:
        contrato = json.load(f)
    eis = {e["id"]: e for e in contrato["elements"]}
    nodes = {n["id"]: [n["x"], n["y"], n["z"]] for n in contrato["nodes"]}

    def _tagged(fname):
        if not tag:
            return fname
        if fname == "edificio_full_results.json":
            candidate = fname.replace("edificio_full_results.json",
                                      f"edificio_full_results_{tag}.json")
        else:
            case = fname.replace("edificio_full_results_", "").replace(".json", "")
            candidate = fname.replace("edificio_full_results.json",
                                      f"edificio_full_results_{tag}_{case}.json")
        path = os.path.join(RESULTADOS_DIR, candidate)
        return candidate if os.path.exists(path) else fname

    def _load(fname):
        with open(os.path.join(RESULTADOS_DIR, fname), encoding="utf-8") as f:
            return json.load(f)

    # Elementos fijos elegidos por el grupo; se reusan en los 5 casos
    viga_tag, col_tag, mur_tag = VIGA_TAG, COL_TAG, MURO_TAG

    def limp(d):
        o = {}
        for k in ("tag", "tipo", "seccion", "L", "piso"):
            if k in d:
                o[k] = d[k]
        for k in ("x", "M", "V", "N"):
            o[k] = [round(v, 4) for v in d[k]]
        if "q" in d:
            o["q"] = round(d["q"], 4)
            o["resid"] = round(d["resid"], 4)
            o["resMJ"] = round(d["resMJ"], 4)
        return o

    out = {}
    for caso, fname in CASOS:
        data = _load(_tagged(fname))
        forces = data["element_forces_global"]
        tribu = data.get("tributary_by_viga", {})
        q = _q_caso(caso, tribu.get(str(viga_tag), {}))
        v = datos_viga(viga_tag, eis[viga_tag], nodes, forces, q)
        c = datos_vertical(col_tag, eis[col_tag], nodes, forces)
        m = datos_vertical(mur_tag, eis[mur_tag], nodes, forces)
        out[caso] = {"viga": limp(v), "columna": limp(c), "muro": limp(m)}
    return out


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with open(RESULTADOS_COMBO, encoding="utf-8") as f:
        datos = json.load(f)
    with open(EDIFICIO_JSON, encoding="utf-8") as f:
        contrato = json.load(f)
    forces = datos["element_forces_global"]
    tribu = datos.get("tributary_by_viga", {})
    eis = {e["id"]: e for e in contrato["elements"]}
    nodes = {n["id"]: [n["x"], n["y"], n["z"]] for n in contrato["nodes"]}

    os.makedirs(OUT_DIR, exist_ok=True)

    viga_tag, col_tag, mur_tag = VIGA_TAG, COL_TAG, MURO_TAG

    # ---------- Figuras: un trio por caso (mismos elementos siempre) ----------
    figuras = []
    for caso, fname in CASOS:
        with open(os.path.join(RESULTADOS_DIR, fname), encoding="utf-8") as f:
            data = json.load(f)
        fcs = data["element_forces_global"]
        trb = data.get("tributary_by_viga", {})
        v = datos_viga(viga_tag, eis[viga_tag], nodes, fcs,
                       _q_caso(caso, trb.get(str(viga_tag), {})))
        c = datos_vertical(col_tag, eis[col_tag], nodes, fcs)
        m = datos_vertical(mur_tag, eis[mur_tag], nodes, fcs)

        plot_viga(v, caso)
        f1 = os.path.join(OUT_DIR,
            "Diagrama 2D Momento-Corte-Axial Viga %d (%s) (%s).png" %
            (v["tag"], v["seccion"], caso))
        plt.savefig(f1, dpi=150)
        plt.close()

        plot_vertical(c, "Columna", caso)
        f2 = os.path.join(OUT_DIR,
            "Diagrama 2D Axial-Corte-Momento Columna %d (%s) (%s).png" %
            (c["tag"], c["seccion"], caso))
        plt.savefig(f2, dpi=150)
        plt.close()

        plot_vertical(m, "Muro", caso)
        f3 = os.path.join(OUT_DIR,
            "Diagrama 2D Axial-Corte-Momento Muro %d (%s) (%s).png" %
            (m["tag"], m["seccion"], caso))
        plt.savefig(f3, dpi=150)
        plt.close()

        figuras.append((f1, f2, f3))
        print("Caso %-5s | Viga %d M %+.1f -> %+.1f | Col N %+.1f | Muro M %+.0f -> %+.0f"
              % (caso, v["tag"], v["M"][0], v["M"][-1],
                 -c["extremos"]["N_i"], m["extremos"]["M_t_i"], m["extremos"]["M_t_j"]))

    # ---------- Resumen ----------
    print("\nFiguras generadas en %s:" % OUT_DIR)
    for f1, f2, f3 in figuras:
        for p in (f1, f2, f3):
            print("  *", os.path.basename(p),
                  "(%.0f KB)" % (os.path.getsize(p) / 1024))
    print()
    best = datos_viga(viga_tag, eis[viga_tag], nodes, forces,
                      _q_caso("COMBO", tribu.get(str(viga_tag), {})))
    ex = best["extremos"]
    print("VIGA id=%d %s L=%.2fm  q(COMBO)=%.2f kN/m  (corte %.1f%%  momentoj %.1f%%)"
          % (best["tag"], best["seccion"], best["L"], best["q"],
             best["resid"] * 100, best["resMJ"] * 100))
    print("   M_i=%+.1f M_j=%+.1f kN·m | V_i=%+.1f V_j=%+.1f kN | N=%.1f kN"
          % (ex["M_i"], ex["M_j"], ex["V_i"], ex["V_j"], ex["N"]))
    print("   M_max(sagging) = %.1f kN·m @ x=%.2f m"
          % (max(best["M"]), best["x"][best["M"].index(max(best["M"]))]))


if __name__ == "__main__":
    main()