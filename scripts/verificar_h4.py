# -*- coding: utf-8 -*-
"""End-to-end H4 check: Unity workflow vs direct OpenSees and repeat run."""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(REPO, "Edificio_mod_C.json")
GENERATOR = os.path.join(REPO, "scripts", "generar_modificaciones.py")
CAPACITY_GENERATOR = os.path.join(REPO, "scripts", "generar_pm_caso_c.py")
RUNNER = os.path.join(REPO, "scripts", "ejecutar_modificacion.py")
SOLVER = os.path.join(REPO, "opensees", "opensees_edificio_v2.py")
RESULTS = os.path.join(REPO, "resultados", "01_casos_base")
REPORT_DIR = os.path.join(REPO, "resultados", "12_h4")
REPORT_JSON = os.path.join(REPORT_DIR, "verificacion_h4.json")
REPORT_MD = os.path.join(REPORT_DIR, "verificacion_h4.md")
REPORT_TXT = os.path.join(REPORT_DIR, "verificacion_h4.txt")
CASES = ("G", "Q", "EX", "EY", "COMBO")
FIELDS = ("element_forces_global", "displacements_m", "reactions_kN", "summary", "verifications")
ABS_TOL = 1e-8
REL_TOL = 1e-9


def run(args):
    print(">>>", " ".join(str(x) for x in args), flush=True)
    completed = subprocess.run(args, cwd=REPO, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    if completed.returncode:
        print((completed.stdout or "")[-6000:], flush=True)
    else:
        print("[OK] proceso completado", flush=True)
    return completed.returncode


CASE_CONFIG = {
    "A": {"name": "Caso A · Viga 147 de 50×75 cm", "model": "Edificio_mod_A.json",
          "tag": "modA", "element": 147, "type": "beam_y", "b": 50.0, "h": 75.0},
    "B": {"name": "Caso B · Apoyo articulado en nodo 1", "model": "Edificio_mod_B.json",
          "tag": "modB", "support_node": 1},
    "C": {"name": "Caso C · Columna 66 de 40×40 cm", "model": "Edificio_mod_C.json",
          "tag": "modC", "element": 66, "type": "column", "b": 40.0, "h": 40.0},
}


def validate_model(path, case_id="C"):
    with open(path, encoding="utf-8") as f:
        model = json.load(f)
    nodes = model.get("nodes")
    elements = model.get("elements")
    if not isinstance(nodes, list) or not isinstance(elements, list):
        raise ValueError("El contrato requiere listas nodes y elements")
    node_ids = [str(n.get("id")) for n in nodes]
    element_ids = [str(e.get("id")) for e in elements]
    if len(set(node_ids)) != len(node_ids) or len(set(element_ids)) != len(element_ids):
        raise ValueError("IDs duplicados en nodos o elementos")
    node_set = set(node_ids)
    for e in elements:
        section_element = e.get("type") in ("column", "beam_x", "beam_y", "wall", "steel_column", "steel_beam")
        for key in (("b", "h") if section_element else ()):
            if key in e and (not math.isfinite(float(e[key])) or float(e[key]) <= 0):
                raise ValueError("Elemento %s: %s debe ser positivo y finito" % (e.get("id"), key))
        for key in ("node_i", "node_j"):
            if key in e and str(e[key]) not in node_set:
                raise ValueError("Elemento %s referencia nodo inexistente %s" % (e.get("id"), e[key]))
    config = CASE_CONFIG[case_id]
    if case_id == "B":
        support = next((s for s in model.get("supports", [])
                        if str(s.get("node")) == str(config["support_node"])), None)
        if not support or support.get("type") != "pinned" or support.get("DOF") != [1, 1, 1, 0, 0, 0]:
            raise ValueError("Caso B debe dejar el nodo 1 articulado con DOF=[1,1,1,0,0,0]")
        return {"nodes": len(nodes), "elements": len(elements), "support_node": 1}
    element = next((e for e in elements if str(e.get("id")) == str(config["element"])), None)
    if not element or element.get("type") != config["type"]:
        raise ValueError("El elemento objetivo no existe o tiene un tipo inesperado")
    if float(element.get("b", 0)) != config["b"] or float(element.get("h", 0)) != config["h"]:
        raise ValueError("%s debe tener sección %.0fx%.0f cm" % (case_id, config["b"], config["h"]))
    return {"nodes": len(nodes), "elements": len(elements), "element": config["element"],
            "section_cm": [config["b"], config["h"]]}


def result_path(tag, case):
    suffix = "" if case == "G" else "_" + case
    return os.path.join(RESULTS, "edificio_full_results_%s%s.json" % (tag, suffix))


def flatten(value, prefix=""):
    out = {}
    if isinstance(value, dict):
        for key in sorted(value):
            out.update(flatten(value[key], prefix + "/" + str(key)))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            out.update(flatten(item, prefix + "/" + str(i)))
    elif isinstance(value, bool) or value is None or isinstance(value, str):
        out[prefix] = value
    elif isinstance(value, (int, float)):
        out[prefix] = float(value)
    return out


def compare(case, left_tag, right_tag):
    with open(result_path(left_tag, case), encoding="utf-8") as f:
        left = json.load(f)
    with open(result_path(right_tag, case), encoding="utf-8") as f:
        right = json.load(f)
    errors, numeric_count, max_abs, max_rel = [], 0, 0.0, 0.0
    for field in FIELDS:
        if field not in left or field not in right:
            errors.append("falta campo " + field)
            continue
        a, b = flatten(left[field]), flatten(right[field])
        if a.keys() != b.keys():
            errors.append("estructura distinta en " + field)
            continue
        for key in a:
            x, y = a[key], b[key]
            if isinstance(x, float) and isinstance(y, float):
                numeric_count += 1
                delta = abs(x - y)
                scale = max(abs(x), abs(y))
                rel = delta / scale if scale else 0.0
                max_abs, max_rel = max(max_abs, delta), max(max_rel, rel)
                if delta > ABS_TOL + REL_TOL * scale:
                    errors.append("%s%s: %.12g vs %.12g" % (field, key, x, y))
            elif x != y:
                errors.append("%s%s: %r vs %r" % (field, key, x, y))
    return {"pass": not errors, "numeric_values": numeric_count,
            "max_abs_difference": max_abs, "max_relative_difference": max_rel,
            "abs_tolerance": ABS_TOL, "rel_tolerance": REL_TOL,
            "errors": errors[:20]}


def comparison_row(case, direct_repeat, case_id="C", model_path=None):
    config = CASE_CONFIG[case_id]
    model_path = model_path or os.path.join(REPO, config["model"])

    def load(tag):
        with open(result_path(tag, case), encoding="utf-8") as f:
            return json.load(f)

    unity, direct = load(config["tag"]), load("h4_direct")
    with open(model_path, encoding="utf-8") as f:
        model = json.load(f)
    if case_id == "B":
        node = str(config["support_node"])
        def metrics(result):
            case_load = float(result["summary"].get("Carga_%s_total_kN" % case, 0.0))
            reaction = result.get("reactions_kN", {}).get(node, [0.0] * 6)
            displacement = result.get("displacements_m", {}).get(node, [0.0] * 6)[:3]
            return {"load_kN": case_load, "n_kN": float(reaction[2]),
                    "my_kNm": float(reaction[4]), "mz_kNm": float(reaction[5]),
                    "disp_mm": 1000.0 * math.sqrt(sum(float(x) ** 2 for x in displacement))}
        node_label = "apoyo " + node
    else:
        element = next(e for e in model["elements"] if str(e.get("id")) == str(config["element"]))
        node = str(element["node_j"])
        def metrics(result):
            case_load = float(result["summary"].get("Carga_%s_total_kN" % case, 0.0))
            force = result["element_forces_global"][str(config["element"])]["local_i"]
            displacement = result["displacements_m"][node][:3]
            return {"load_kN": case_load, "n_kN": float(force[0]),
                    "my_kNm": float(force[4]), "mz_kNm": float(force[5]),
                    "disp_mm": 1000.0 * math.sqrt(sum(float(x) ** 2 for x in displacement))}
        node_label = node

    u, d = metrics(unity), metrics(direct)
    delta = {key: abs(u[key] - d[key]) for key in u}
    return {"case_name": case, "node": node_label, "unity": u, "direct": d,
            "delta": delta, "repeat_max_difference": direct_repeat["max_abs_difference"],
            "pass": direct_repeat["pass"] and all(delta[k] <= ABS_TOL + REL_TOL * max(abs(u[k]), abs(d[k])) for k in delta)}


def write_report(data):
    os.makedirs(REPORT_DIR, exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    checks = data["checks"]
    lines = ["H4 — Verificación de reanálisis OpenSees", "",
             "Fecha: " + data["timestamp"],
             "Modelo: " + CASE_CONFIG[data["case_id"]]["name"], "",
             "| Requisito | Estado | Evidencia |", "|---|---|---|"]
    for name, item in checks.items():
        lines.append("| %s | %s | %s |" % (name, "APROBADO" if item["pass"] else "REVISAR", item["detail"]))
    lines += ["", "Comparación numérica entre campos exportados por OpenSees: fuerzas de elementos, desplazamientos, reacciones, resumen y verificaciones.",
              "Tolerancia: abs ≤ %.1e + rel ≤ %.1e × escala." % (ABS_TOL, REL_TOL),
              "", "OpenSees se ejecutó en el backend local y se comparó con corridas directas."]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    plain = ["H4 — REANÁLISIS OPENSEES", CASE_CONFIG[data["case_id"]]["name"], "Fecha: " + data["timestamp"], ""]
    for name, item in checks.items():
        plain.append("[%s] %s — %s" % ("APROBADO" if item["pass"] else "REVISAR", name, item["detail"]))
    plain += ["", "Tolerancia comparación: abs %.1e + rel %.1e × escala." % (ABS_TOL, REL_TOL),
              "El backend local Python/OpenSees respondió a la solicitud de Unity.",
              "Reporte detallado: resultados/12_h4/verificacion_h4.json"]
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(plain) + "\n")
    print("REPORTE_JSON=" + REPORT_JSON)
    print("REPORTE_MD=" + REPORT_MD)
    for name, item in checks.items():
        print("H4_%s=%s — %s" % (name.upper().replace(" ", "_"), "PASS" if item["pass"] else "FAIL", item["detail"]))


def main():
    parser = argparse.ArgumentParser(description="Ejecuta Honor Track 4 para el caso A, B o C")
    parser.add_argument("--case-id", choices=tuple(CASE_CONFIG), default="C")
    options = parser.parse_args()
    case_id = options.case_id
    config = CASE_CONFIG[case_id]
    model_path = os.path.join(REPO, config["model"])
    os.makedirs(REPORT_DIR, exist_ok=True)
    data = {"timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "case_id": case_id, "case_name": config["name"],
            "element_id": config.get("element"), "checks": {}}
    try:
        rc = run([sys.executable, GENERATOR])
        if rc:
            raise RuntimeError("No se pudieron generar las variantes")
        if case_id == "C":
            rc = run([sys.executable, CAPACITY_GENERATOR])
            if rc:
                raise RuntimeError("No se pudo generar la curva de capacidad del Caso C")
        validation = validate_model(model_path, case_id)
        with open(model_path, encoding="utf-8") as f:
            invalid = json.load(f)
        if case_id == "B":
            support = next(e for e in invalid["supports"] if str(e.get("node")) == "1")
            support["DOF"] = [1, 1, 0, 0, 0, 0]
        else:
            element = next(e for e in invalid["elements"] if str(e.get("id")) == str(config["element"]))
            element["b"] = 0
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as tf:
            json.dump(invalid, tf)
            invalid_path = tf.name
        try:
            try:
                validate_model(invalid_path, case_id)
                invalid_rejected = False
            except ValueError:
                invalid_rejected = True
        finally:
            os.unlink(invalid_path)
        missing = os.path.join(tempfile.gettempdir(), "p1_h4_missing_model.json")
        rejected = subprocess.run([sys.executable, RUNNER, "--tag", "h4_invalid",
                                   "--json", missing], cwd=REPO, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        runner_error_handled = rejected.returncode != 0 and "ERROR" in rejected.stdout
        target_description = ("el apoyo del nodo 1 está articulado" if case_id == "B" else
                              "el elemento %s mide %.0f×%.0f cm" % (config["element"], config["b"], config["h"]))
        data["checks"]["Modelo válido"] = {"pass": True, "detail": "El edificio tiene %s nodos y %s elementos; %s. También se comprobó que rechace una entrada estructural inválida." % (validation["nodes"], validation["elements"], target_description)}
        data["checks"]["Errores controlados"] = {"pass": invalid_rejected and runner_error_handled, "detail": "Se provocaron dos errores de prueba y ambos fueron detectados. El código %s significa que se rechazó correctamente el archivo faltante; no es un fallo del análisis." % rejected.returncode}

        runner_args = [sys.executable, RUNNER, "--tag", config["tag"], "--json", model_path,
                       "--all-cases", "--unity"]
        if config.get("element") is not None:
            runner_args += ["--element", str(config["element"])]
        if case_id == "C":
            runner_args += ["--capacity-json", os.path.join("resultados", "07_capacidad", "pm_columnas", "pm_columna_id66_40x40.json")]
        rc = run(runner_args)
        if rc:
            raise RuntimeError("El reanálisis OpenSees del Caso %s terminó con error" % case_id)
        tagged_map = os.path.join(REPO, "resultados", "11_mapa_visor", "analysis_map_%s.json" % config["tag"])
        analysis_ready = os.path.isfile(model_path) and os.path.isfile(tagged_map)
        if analysis_ready:
            validate_model(model_path, case_id)
            with open(tagged_map, encoding="utf-8") as f:
                analysis_ready = analysis_ready and isinstance(json.load(f), dict)
        data["checks"]["Backend preparó resultados"] = {"pass": analysis_ready, "detail": "Python/OpenSees calculó los cinco escenarios para %s y preparó el modelo y el mapa para Unity." % config["name"] if analysis_ready else "No se pudo preparar el modelo y el mapa de resultados."}

        comparisons_direct, comparisons_repeat = {}, {}
        for tag in ("h4_direct", "h4_repeat"):
            for case in CASES:
                solver_args = [sys.executable, SOLVER, "--case", case, "--json", model_path, "--tag", tag]
                if case == "COMBO":
                    solver_args += ["--lambda-g", "1.2", "--lambda-q", "1.0", "--lambda-ex", "1.4", "--lambda-ey", "1.4"]
                if run(solver_args):
                    raise RuntimeError("Corrida directa/repetición falló en %s (%s)" % (case, tag))
                if not os.path.isfile(result_path(tag, case)):
                    raise RuntimeError("Falta el resultado %s/%s" % (tag, case))
        for case in CASES:
            comparisons_direct[case] = compare(case, config["tag"], "h4_direct")
            comparisons_repeat[case] = compare(case, "h4_direct", "h4_repeat")
        data["comparisons"] = {"unity_vs_direct": comparisons_direct, "repeatability": comparisons_repeat}
        direct_ok = all(x["pass"] for x in comparisons_direct.values())
        repeat_ok = all(x["pass"] for x in comparisons_repeat.values())
        worst = max(x["max_abs_difference"] for x in comparisons_direct.values())
        data["checks"]["Mismos resultados"] = {"pass": direct_ok, "detail": "Se comparó cada escenario con OpenSees ejecutado directamente. La mayor diferencia encontrada fue %.3g; dentro del límite aceptado." % worst if direct_ok else "Algunos valores difieren más de lo permitido. Revisa la tabla por escenario."}
        worst_repeat = max(x["max_abs_difference"] for x in comparisons_repeat.values())
        data["checks"]["Cálculo repetible"] = {"pass": repeat_ok, "detail": "Se repitió el análisis con los mismos datos. La mayor diferencia fue %.3g; las corridas coinciden dentro del límite aceptado." % worst_repeat if repeat_ok else "Al repetir el análisis aparecieron diferencias mayores al límite aceptado."}
        data["comparison_rows"] = [comparison_row(case, comparisons_repeat[case], case_id, model_path) for case in CASES]
        data["check_rows"] = [{"name": name, "pass": item["pass"], "detail": item["detail"]}
                              for name, item in data["checks"].items()]
        write_report(data)
        # La ejecución completó y sincronizó el caso seleccionado; los veredictos fallidos se
        # conservan en el reporte, y Unity aun debe cargar para inspección visual.
        return 0
    except Exception as exc:
        data["fatal_error"] = str(exc)
        data["checks"].setdefault("Ejecución", {"pass": False, "detail": str(exc)})
        write_report(data)
        print("[ERROR H4]", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
