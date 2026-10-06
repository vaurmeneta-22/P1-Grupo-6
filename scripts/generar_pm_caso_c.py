"""Generate the element-specific fiber P-M curve for Mod C (column 66)."""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "opensees"))
from fiber_sections import analysis, sections


def main():
    contract_path = os.path.join(ROOT, "Edificio_mod_C.json")
    with open(contract_path, encoding="utf-8") as stream:
        contract = json.load(stream)
    element = next((item for item in contract["elements"]
                    if item["id"] == 66 and item["type"] == "column"), None)
    if element is None or element["section"] != "40x40":
        raise ValueError("Mod C must define column 66 as 40x40 cm")

    # Caso didáctico de falla: sección 40x40 cm y cuatro barras Ø12 en esquina.
    cfg = dict(sections.COLUMNA_MOD_C)
    cfg["nombre"] = "columna_id66_40x40"
    cfg["b"] = 400.0
    cfg["h"] = 400.0
    cfg["fuente"] = "Mod C: columna 66, armadura 4 phi12 en esquinas"
    cover = cfg["rec"]
    clear_between_opposite_bars = cfg["b"] - 2.0 * cover - cfg["db"]
    if cfg["b"] <= 2.0 * cover or clear_between_opposite_bars < 25.0:
        raise ValueError("Mod C rebar layout violates its minimum 25 mm clear-spacing check")

    p_values, m_values = analysis.pm_completa(cfg, verbose=True)
    if len(p_values) < 4 or len(p_values) != len(m_values):
        raise RuntimeError("Fiber analysis did not produce a usable closed P-M curve")
    if any(not math.isfinite(float(value)) for value in p_values + m_values):
        raise RuntimeError("Fiber analysis produced non-finite P-M values")

    path = os.path.join(ROOT, "resultados", "07_capacidad", "pm_columnas",
                        "pm_columna_id66_40x40.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "tipo": "interaccion_PM",
        "element_id": 66,
        "seccion": "40x40",
        "b_cm": 40.0,
        "h_cm": 40.0,
        "recubrimiento_centro_barra_mm": cover,
        "armadura": "4 phi12 en las esquinas",
        "As_mm2": sections.area_acero(cfg),
        "rho": sections.area_acero(cfg) / (cfg["b"] * cfg["h"]),
        "separacion_libre_entre_barras_opuestas_mm": clear_between_opposite_bars,
        "P_kN_fiber": p_values,
        "M_kNm_fiber": m_values,
        "P_trac_kN": p_values[0],
        "P_comp_kN": p_values[-1],
        "modelo": "OpenSees Fiber (Concrete02 + Steel01), columna de borde Mod C",
    }
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    print(f"OK: curva P-M especifica de columna 66 -> {os.path.relpath(path, ROOT)}")
    print(f"    barras=4 phi12; recubrimiento al centro=56 mm; rho={payload['rho']:.4f}")
    print(f"    separacion libre entre barras opuestas={clear_between_opposite_bars:.1f} mm")


if __name__ == "__main__":
    main()
