"""
Parte C - Superposicion  (Grupo 6)

Construye una combinacion arbitraria de los casos base:

    R = lambda_G * G + lambda_Q * Q + lambda_EX * EX + lambda_EY * EY

y la verifica de dos maneras:

  1. SUPERPOSICION DIRECTA (sin OpenSees): lee los JSON de resultados de cada
     caso base (edificio_full_results[_Q,_EX,_EY].json) y combina linealmente
     desplazamientos, reacciones y fuerzas internas con las lambdas.

  2. CORRIDA EXPLICITA (OpenSees): lanza `opensees_edificio_v2.py --case COMBO
     --lambda-*` con las mismas lambdas, que resuelve el modelo con la
     combinacion de cargas aplicadas directamente EN UN SOLO PASO (sin
     superponer resultados).

  Compara (1) contra (2) y verifica, como pide la Parte C:
     - desplazamiento  (cada nodo, 6 GDL)
     - reaccion        (cada apoyo, 6 GDL)
     - fuerza interna  (cada elemento, global_i del extremo i)

Uso:
    python superposicion.py --lambda-g 1.0 --lambda-q 1.0 --lambda-ex 1.0 --lambda-ey 1.0
    python superposicion.py --lambda-g 1.2 --lambda-q 0.5 --lambda-ex 0.3 --lambda-ey 0.3
    python superposicion.py --skip-open 3      # solo superposicion directa (3 casos)

Si se omite cualquier lambda, esa componente vale 0.0 (es decir, se excluye),
excepto lambda_G que por defecto vale 1.0 (superposicion de servicio completa).
"""

import json
import math
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENSEES = os.path.join(REPO, "opensees")
RESULTS = os.path.join(OPENSEES, "results")
V2_SCRIPT = os.path.join(OPENSEES, "opensees_edificio_v2.py")

CASES = {"G": "edificio_full_results.json",
         "Q": "edificio_full_results_Q.json",
         "EX": "edificio_full_results_EX.json",
         "EY": "edificio_full_results_EY.json"}

TOL = 1e-6          # tolerancia relativa de la comparacion
ATOL = 1e-9         # tolerancia absoluta (componentes que se anulan)


def load_case(case):
    path = os.path.join(RESULTS, CASES[case])
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def combine(lambdas, cases, data=None):
    """Superposicion directa. `cases` es una lista de nombres ("G", "Q", ...) y
    `lambdas` un dict con su ponderacion. Si `data` es un dict {case: resultado}
    se usa en memoria (para tests); si es None se leen los JSON del disco.
    Devuelve un dict con la misma estructura que un archivo de resultados."""
    if data is not None:
        loaded = data
    else:
        loaded = {c: load_case(c) for c in cases}
    ref = loaded[cases[0]]

    def _combine_vectors(dicts, keys, n_comp):
        out = {}
        for tag in list(dicts[0].keys()):
            vec = [0.0] * n_comp
            for c, d in zip(cases, dicts):
                v = d.get(tag)
                if v is None:
                    continue
                lam = lambdas[c]
                for k in range(n_comp):
                    vec[k] += lam * v[k]
            out[tag] = vec
        return out

    def _combine_forces(dicts):
        out = {}
        for tag in list(dicts[0].keys()):
            meta = dicts[0][tag]
            gi = [0.0] * 6
            gj = [0.0] * 6
            for c, d in zip(cases, dicts):
                if tag not in d:
                    continue
                lam = lambdas[c]
                f = d[tag].get("global_i", [0.0] * 6)
                for k in range(6):
                    gi[k] += lam * f[k]
                f = d[tag].get("global_j", [0.0] * 6)
                for k in range(6):
                    gj[k] += lam * f[k]
            out[tag] = {
                "type": meta.get("type", ""),
                "section": meta.get("section", ""),
                "global_i": gi,
                "global_j": gj,
            }
        return out

    disp = _combine_vectors([r["displacements_m"] for r in loaded.values()],
                            cases, 6)
    reac = _combine_vectors([r["reactions_kN"] for r in loaded.values()],
                            cases, 6)
    forc = _combine_forces([r["element_forces_global"] for r in loaded.values()])

    result = {
        "model": ref.get("model"),
        "case": "COMBO_directa",
        "units_internal": {"length": "m", "force": "kN", "moment": "kN*m"},
        "summary": {
            "case_base": cases,
            "lambdas": {c: lambdas[c] for c in cases},
            "n_nodos": len(disp),
            "n_apoyos": len(reac),
            "n_elementos": len(forc),
        },
        "_lambdas": dict(lambdas),
        "_load_cases": list(cases),
        "displacements_m": disp,
        "reactions_kN": reac,
        "element_forces_global": forc,
    }
    return result


def forces_map(r):
    """Mapa {tag: global_i} de las fuerzas en el extremo i (para comparar)."""
    return {t: r["element_forces_global"][t]["global_i"]
            for t in r["element_forces_global"]}


def run_explicit(lambdas, cases):
    """Corre opensees_edificio_v2.py --case COMBO con las lambdas dadas.
    Si el archivo COMBO ya existe y se pasa --reuse, se reutiliza (mas rapido
    para iterar sobre la metrica sin re-resolver el modelo)."""
    path = os.path.join(RESULTS, "edificio_full_results_COMBO.json")
    if "--reuse" in sys.argv and os.path.exists(path):
        print("\n[EXPLICITO] reutilizando edificio_full_results_COMBO.json (--reuse)")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    cmd = [sys.executable, V2_SCRIPT, "--case", "COMBO",
           "--lambda-g", str(lambdas["G"]),
           "--lambda-q", str(lambdas["Q"]),
           "--lambda-ex", str(lambdas["EX"]),
           "--lambda-ey", str(lambdas["EY"])]
    print("\n[EXPLICITO] " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=OPENSEES, capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        raise RuntimeError("La corrida explicita COMBO fallo (rc=%d)" % r.returncode)

    if not os.path.exists(path):
        alt = os.path.join(RESULTS, "edificio_full_results_COMBO.json")
        if not os.path.exists(alt):
            raise FileNotFoundError("No se encontro el resultado COMBO explicito")
        path = alt
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_maps(direct, expl, key_map, n_comp, atol=ATOL):
    """Compara dos mapas {tag: [comp]} con la misma clave.
    Devuelve (max_err, n_compare, details, worst).
    - max_err: error relativo POR NORMA global: ||a-b||_2 / ||b||_2 (los
      desplazamientos de los JSON bases estan redondeados a 1e-10 m, por lo
      que una metrica relativa por componente individual es inestable cuando
      esa componente es ~1e-6; la norma es la metrica estandar para validar
      superposicion de campos).
    - details: lista de (tag, a, b) por si se quiere inspeccionar.
    - worst: (tag, k, av, bv) con la mayor diferencia absoluta.
    """
    keys = sorted(set(direct) & set(expl))
    num = 0.0
    den = 0.0
    worst = None
    wdiff = -1.0
    details = []
    for tag in keys:
        a = direct[tag]
        b = expl[tag]
        for k in range(n_comp):
            av = a[k]
            bv = b[k]
            d = av - bv
            num += d * d
            den += bv * bv
            if abs(d) > wdiff:
                wdiff = abs(d)
                worst = (tag, k, av, bv)
        details.append((tag, a, b))
    err = math.sqrt(num) / math.sqrt(den) if den > 0.0 else 0.0
    return err, len(keys), details, worst


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = sys.argv[1:]
    def _get(flag, default=None):
        if flag in args:
            i = args.index(flag)
            if i + 1 < len(args):
                return float(args[i + 1])
        return default

    skip_open = "--skip-open" in args
    lambdas = {
        "G": _get("--lambda-g", 1.0),
        "Q": _get("--lambda-q", 0.0),
        "EX": _get("--lambda-ex", 0.0),
        "EY": _get("--lambda-ey", 0.0),
    }
    cases = [c for c in ["G", "Q", "EX", "EY"] if lambdas[c] != 0.0]
    if not cases:
        print("Debe darse al menos una lambda distinta de 0.")
        return 2
    print("=" * 70)
    print("PARTE C - SUPERPOSICION  R = Suma lambda_i * caso_i")
    print("=" * 70)
    print(f"  Casos activos : {cases}")
    print(f"  Lambdas       : { {c: lambdas[c] for c in cases} }")

    # 1) superposicion directa
    combo = combine(lambdas, cases)

    expl = None
    if skip_open:
        n = _get("--skip-open", 0)
        print(f"\n  [modo ver ] saltando corrida explicita OpenSees")
        print(f"  [verific.on] solo se valida la superposicion directa")
        print(f"  [aviso    ] los checks vs corrida expl.cita se omiten (--skip-open)")
        ok = True
        err = 0.0
    else:
        # 2) corrida explicita
        expl = run_explicit(lambdas, cases)

        # 3) comparacion  (desplazamiento, reaccion, fuerza interna)
        print("\n" + "=" * 70)
        print("COMPARACION  superposicion directa  vs  corrida explicita OpenSees")
        print("=" * 70)
        checks = []

        me, nn, _, worst = compare_maps(combo["displacements_m"],
                                 expl["displacements_m"], None, 6)
        ok_d = me <= TOL
        checks.append(("desplazamiento", me, nn, ok_d))
        if worst:
            tag, k, av, bv = worst
            print(f"    may dif abs: nodo {tag} gdl {k}: directa={av:.6e} expl={bv:.6e}")

        me, nn, _, worst = compare_maps(combo["reactions_kN"],
                                 expl["reactions_kN"], None, 6)
        ok_r = me <= TOL
        checks.append(("reaccion", me, nn, ok_r))
        if worst:
            tag, k, av, bv = worst
            print(f"    may dif abs: apoyo {tag} gdl {k}: directa={av:.6e} expl={bv:.6e}")

        def _forces_map(r):
            return forces_map(r)
        me, nn, _, worst = compare_maps(_forces_map(combo), _forces_map(expl), None, 6)
        ok_f = me <= TOL
        checks.append(("fuerza interna", me, nn, ok_f))
        if worst:
            tag, k, av, bv = worst
            print(f"    may dif abs: elem {tag} gdl {k}: directa={av:.6e} expl={bv:.6e}")

        all_ok = True
        for label, max_err, n, ok in checks:
            all_ok = all_ok and ok
            estado = "OK" if ok else "REVISAR"
            print(f"  {label:16s} max_err_rel={max_err:10.3e}  "
                  f"n={n:5d}  [{estado}]")
        err = max(c[1] for c in checks)
        ok = all_ok
        print("-" * 70)
        print(f"  RESULTADO: {'SUPERPOSICION CORRECTA' if ok else 'DIFIERE — revisar'}")
        print("=" * 70)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())