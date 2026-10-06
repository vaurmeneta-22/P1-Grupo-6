# -*- coding: utf-8 -*-
"""Servicio HTTP local para reanalisis OpenSees solicitado desde Unity."""
import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY = os.path.join(ROOT, "scripts", "verificar_h4.py")
REPORT_JSON = os.path.join(ROOT, "resultados", "12_h4", "verificacion_h4.json")
REPORT_TEXT = os.path.join(ROOT, "resultados", "12_h4", "verificacion_h4.txt")
CASES = {
    "A": {"model": "Edificio_mod_A.json", "tag": "modA", "element_id": 147, "width_cm": 50, "height_cm": 75},
    "B": {"model": "Edificio_mod_B.json", "tag": "modB", "node_id": 1, "support_type": "pinned"},
    "C": {"model": "Edificio_mod_C.json", "tag": "modC", "element_id": 66, "width_cm": 40, "height_cm": 40},
}


def validate_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("El cuerpo debe ser un objeto JSON.")
    case_id = payload.get("case_id")
    if case_id not in CASES:
        raise ValueError("Selecciona uno de los escenarios A, B o C.")
    expected = CASES[case_id]
    for field in ("element_id", "width_cm", "height_cm", "node_id", "support_type"):
        if field in expected and payload.get(field) != expected[field]:
            raise ValueError("Datos inválidos para el Caso %s (%s)." % (case_id, field))
    return payload


def run_analysis(payload):
    case_id = validate_request(payload)["case_id"]
    completed = subprocess.run(
        [sys.executable, VERIFY, "--case-id", case_id],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600)
    if completed.returncode:
        raise RuntimeError((completed.stdout or "")[-12000:] or "OpenSees terminó con error.")
    config = CASES[case_id]
    paths = (os.path.join(ROOT, config["model"]),
             os.path.join(ROOT, "resultados", "11_mapa_visor", "analysis_map_%s.json" % config["tag"]),
             REPORT_JSON, REPORT_TEXT)
    missing = [path for path in paths if not os.path.isfile(path)]
    if missing:
        raise RuntimeError("Faltan resultados del análisis: " + ", ".join(os.path.basename(p) for p in missing))
    with open(paths[0], encoding="utf-8") as f: model_json = f.read()
    with open(paths[1], encoding="utf-8") as f: map_json = f.read()
    with open(paths[2], encoding="utf-8") as f: report_json = f.read()
    with open(paths[3], encoding="utf-8") as f: report_text = f.read()
    return {"ok": True, "model_json": model_json, "analysis_map_json": map_json,
            "report_json": report_json, "report_text": report_text,
            "solver_log": (completed.stdout or "")[-6000:]}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/health":
            self.send_json(404, {"ok": False, "error": "Ruta no encontrada."})
            return
        self.send_json(200, {"ok": True, "service": "OpenSees H4", "ready": True})

    def do_POST(self):
        if self.path != "/reanalyze":
            self.send_json(404, {"ok": False, "error": "Ruta no encontrada."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 65536: raise ValueError("Tamaño de solicitud inválido.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            self.send_json(200, run_analysis(payload))
        except ValueError as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})
        except subprocess.TimeoutExpired:
            self.send_json(504, {"ok": False, "error": "El análisis excedió el tiempo máximo de una hora."})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": "Falló el reanálisis OpenSees.", "detail": str(exc)})

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description="Backend local HTTP para Honor Track 4")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = HTTPServer((args.host, args.port), Handler)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__ == "__main__": main()
