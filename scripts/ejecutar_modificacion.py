# -*- coding: utf-8 -*-
"""
EJECUTAR MODIFICACION DEL MODELO (Semana 5 - Laboratorio interactivo v1)

Ejecuta el flujo completo y reproducible:

    dato (--json)  ->  OpenSees (--case)  ->  analysis_map (--tag)  ->  Unity (--unity)

La linea base queda intacta: las corridas de modificacion se etiquetan
(--tag) y escriben edificio_full_results_<tag>_*.json y analysis_map_<tag>.*,
de modo que NUNCA se sobrescriben los resultados del modelo contractual.

Verificacion numerica integrada (ingenieril):
    * equilibrio de la corrida modificada  (verifications.equilibrio_error)
    * todas_ok del FE (conservacion, diafragma, masa sismica)
    * comparacion ANTES / DESPUES del elemento indicado: fuerzas de extremo
      (global y local = [N,Vy,Vz,T,My,Mz]) y desplazamiento de sus nodos.

Uso:
    python scripts/ejecutar_modificacion.py --tag modA --json Edificio_mod_A.json \
        --element 147 --unity
    python scripts/ejecutar_modificacion.py --tag modB --json Edificio_mod_B.json \
        --element 76 --unity
    python scripts/ejecutar_modificacion.py --restore   # Unity vuelve a la base
"""
import argparse
import json
import os
import subprocess
import sys
import shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V2 = os.path.join(REPO, "opensees", "opensees_edificio_v2.py")
EXPORT_MAP = os.path.join(REPO, "opensees", "exportar_analysis_map.py")
BASE_RESULTS = os.path.join(REPO, "resultados", "01_casos_base")
MAP_DIR = os.path.join(REPO, "resultados", "11_mapa_visor")
STREAM = os.path.join(REPO, "Unity", "Assets", "StreamingAssets")
BASE_MAP_JSON = os.path.join(MAP_DIR, "analysis_map.json")

SUFFIX = {
    "G": "",
    "Q": "_Q",
    "EX": "_EX",
    "EY": "_EY",
    "COMBO": "_COMBO",
}


def archivo_resultado(case, tag=""):
    if tag:
        return os.path.join(BASE_RESULTS, f"edificio_full_results_{tag}{SUFFIX[case]}.json")
    return os.path.join(BASE_RESULTS, f"edificio_full_results{SUFFIX[case]}.json")


def reporte_elemento(case, tag, element, json_mod):
    """Imprime ANTES/DESPUES del elemento modificado (fuerzas y desplazamiento)."""
    def cargar(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    base = cargar(archivo_resultado(case))
    mod = cargar(archivo_resultado(case, tag))

    with open(json_mod, encoding="utf-8") as f:
        contrato = json.load(f)
    eid = str(element)
    ei = next((e for e in contrato["elements"] if str(e["id"]) == eid), None)
    ni = nj = None
    if ei is not None and "node_i" in ei:
        ni, nj = ei["node_i"], ei["node_j"]

    def fuerza(r, key):
        d = r["element_forces_global"].get(eid, {}).get(key)
        if d is None:
            return None
        return [round(v, 4) for v in d]

    print(f"\n  Elemento {element} (extremos {ni}/{nj})  caso {case}  "
          f"base vs {tag}:")
    for clave, lbl in (("global_i", "Fx,Fy,Fz,Mx,My,Mz [i] (g)"),
                       ("global_j", "Fx,Fy,Fz,Mx,My,Mz [j] (g)"),
                       ("local_i", "N,Vy,Vz,T,My,Mz [i] (l)"),
                       ("local_j", "N,Vy,Vz,T,My,Mz [j] (l)")):
        a, b = fuerza(base, clave), fuerza(mod, clave)
        if a is None or b is None:
            continue
        deltas = [round((x - y) / y * 100.0, 2) if abs(y) > 1e-9 else 0.0
                  for x, y in zip(b, a)]
        print(f"    {lbl:32s} base={a}")
        print(f"    {'':32s} mod ={b}")
        print(f"    {'':32s} d%  ={deltas}")

    for n in (ni, nj):
        a = base["displacements_m"].get(str(n))
        b = mod["displacements_m"].get(str(n))
        if a is None or b is None:
            continue
        a_mm = [round(x * 1000.0, 4) for x in a]
        b_mm = [round(x * 1000.0, 4) for x in b]
        print(f"    desplazamiento nodo {n} [mm]  base={a_mm}")
        print(f"    {'':10s}               mod ={b_mm}")


def verificar(case, tag):
    with open(archivo_resultado(case, tag), encoding="utf-8") as f:
        mod = json.load(f)
    v = mod.get("verifications", {})
    s = mod.get("summary", {})
    print("\n  === VERIFICACION INGENIERIL corrida modificada (tag=%s, caso=%s) ==="
          % (tag, case))
    print(f"    carga total {case}: {s.get(f'Carga_{case}_total_kN')} kN")
    print(f"    equilibrio (suma F + R): error = {v.get('equilibrio_error')}")
    print(f"    conmutacion/diafragma:   err_max = {v.get('diafragma_compatibilidad_err_max_m')} m")
    print(f"    conservacion areas:      rel = {v.get('area_conservacion_rel')}")
    print(f"    conservacion carga:      rel = {v.get('carga_conservacion_rel')}")
    print(f"    todas_ok del FE:          {v.get('todas_ok')}")
    ok = (v.get("equilibrio_error", 1.0) < 1e-6 and v.get("todas_ok", False))
    print("    ==> %s" % ("APROBADO" if ok else "REVISAR"))
    return ok


def sincronizar_unity(tag, json_mod):
    """Copia el mapa etiquetado y el contrato modificado a StreamingAssets."""
    src_map = os.path.join(MAP_DIR, f"analysis_map_{tag}.json")
    for src, dst in ((src_map, os.path.join(STREAM, "analysis_map.json")),
                     (json_mod, os.path.join(STREAM, "Edificio.json"))):
        if not os.path.exists(src):
            print(f"    [SKIP] no existe {src}")
            continue
        shutil.copyfile(src, dst)
        print(f"    -> {os.path.relpath(dst, REPO)} ({os.path.getsize(dst)} B)")
        meta = dst + ".meta"
        if not os.path.exists(meta):
            shutil.copyfile(src + ".meta", meta) if os.path.exists(src + ".meta") else None
    print("    Unity lista para Play (modo modificado activo).")


def restaurar_unity():
    shutil.copyfile(BASE_MAP_JSON, os.path.join(STREAM, "analysis_map.json"))
    shutil.copyfile(os.path.join(REPO, "Edificio.json"),
                    os.path.join(STREAM, "Edificio.json"))
    print("  StreamingAssets restaurado a la LINEA BASE.")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Flujo modificacion -> reanalisis -> Unity")
    ap.add_argument("--tag", default="", help="etiqueta de la corrida")
    ap.add_argument("--json", default="", help="contrato modificado (Edificio_mod_X.json)")
    ap.add_argument("--case", default="COMBO", help="caso a re-correr (default COMBO)")
    ap.add_argument("--all-cases", action="store_true",
                    help="re-correr G, Q, EX, EY Y COMBO (mapa totalmente consistente)")
    ap.add_argument("--element", type=int, default=None,
                    help="elemento a comparar antes/despues")
    ap.add_argument("--unity", action="store_true",
                    help="sincronizar StreamingAssets con la corrida modificada")
    ap.add_argument("--restore", action="store_true",
                    help="restaurar StreamingAssets a la linea base")
    for lam in ("--lambda-g", "--lambda-q", "--lambda-ex", "--lambda-ey"):
        ap.add_argument(lam, type=float, default=None)
    # Lambdas de la combinacion: por defecto IGUALES al baseline (1.2/1.0/1.4/1.4)
    # para que base vs modificado sean estrictamente comparables (mismo combo).
    ap.add_argument("--combo-lambdas", type=str, default="1.2,1.0,1.4,1.4",
                    help="G,Q,EX,EY de la combinacion COMBO (default = baseline)")
    args = ap.parse_args()

    if args.restore:
        restaurar_unity()
        return 0

    if not args.tag or not args.json:
        ap.error("se requiere --tag y --json (o --restore)")

    json_mod = os.path.abspath(args.json)
    if not os.path.exists(json_mod):
        print(f"[ERROR] no existe {json_mod}")
        return 1
    case = args.case.upper()

    # 1) OpenSees (reanalisis del modelo modificado)
    casos = ["G", "Q", "EX", "EY", "COMBO"] if args.all_cases else [case]
    lg, lq, lex, ley = (float(x) for x in args.combo_lambdas.split(","))
    if args.lambda_g is not None: lg = args.lambda_g
    if args.lambda_q is not None: lq = args.lambda_q
    if args.lambda_ex is not None: lex = args.lambda_ex
    if args.lambda_ey is not None: ley = args.lambda_ey
    for c in casos:
        cmd = [sys.executable, V2, "--case", c, "--json", json_mod, "--tag", args.tag]
        if c == "COMBO":
            cmd += ["--lambda-g", str(lg), "--lambda-q", str(lq),
                    "--lambda-ex", str(lex), "--lambda-ey", str(ley)]
        print(">>> OpenSees:", " ".join(os.path.relpath(a) if os.path.sep in a else a
                                        for a in cmd[1:]))
        r = subprocess.run(cmd, cwd=REPO, encoding="utf-8")
        if r.returncode != 0 or not os.path.exists(archivo_resultado(c, args.tag)):
            print(f"[ERROR] reanalisis OpenSees fallo para {c}")
            return 1

    # 2) Exportar analysis_map etiquetado
    cmd2 = [sys.executable, EXPORT_MAP, "--json", json_mod, "--tag", args.tag]
    print(">>> Exportar mapa:", " ".join(cmd2[1:]))
    r2 = subprocess.run(cmd2, cwd=REPO, encoding="utf-8")
    if r2.returncode != 0:
        print("[ERROR] exportar_analysis_map fallo")
        return 1

    # 3) Verificacion numerica (equilibrio, conservacion, antes/despues)
    ok = True
    for c in casos:
        ok &= verificar(c, args.tag)
    if args.element is not None:
        reporte_elemento(case, args.tag, args.element, json_mod)
    if not ok:
        print("[WARN] hay corridas que no cumplen todas las auditorias del FE")

    # 4) Sincronizar Unity (opcional)
    if args.unity:
        sincronizar_unity(args.tag, json_mod)

    print("\n>>> FLUJO COMPLETO TAG=%s. La linea base sigue intacta "
          "(resultados y editable no etiquetados)." % args.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())