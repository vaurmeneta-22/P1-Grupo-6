"""Tablas de resultados existentes para Excel español; no reanaliza el modelo.

Ejecutar desde cualquier directorio. CSV UTF-8 BOM, delimitador ;, coma decimal.
Los archivos originales se conservan. No infiere geometría de nodos auxiliares.
"""
import csv
import math
from pathlib import Path
from exportar_fuerzas_por_caso import main as export_forces, REPO, CASES
import json

ROOT = REPO / "resultados"
WRITTEN = []


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (float, int)):
        if not math.isfinite(value):
            raise ValueError("Valor no finito")
        return str(value).replace(".", ",")
    return str(value)


def write(path, rows):
    if not rows:
        raise ValueError(f"Tabla vacia: {path}")
    headers = list(dict.fromkeys(k for row in rows for k in row))
    target = ROOT / path
    expected = [[cell(row.get(k)) for k in headers] for row in rows]
    with target.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream, delimiter=";")
        writer.writerow(headers)
        writer.writerows(expected)
    with target.open(newline="", encoding="utf-8-sig") as stream:
        actual = list(csv.reader(stream, delimiter=";"))
    assert actual == [headers] + expected, path
    for row, original in zip(actual[1:], rows):
        for key, value in zip(headers, row):
            source = original.get(key)
            if isinstance(source, (int, float)) and not isinstance(source, bool):
                assert float(value.replace(",", ".")) == source, (path, key)
    WRITTEN.append((path, len(rows)))


def main():
    export_forces()
    cases = {c: read(f"01_casos_base/edificio_full_results{'' if c == 'G' else '_' + c}.json") for c in CASES}
    analysis = read("11_mapa_visor/analysis_map.json")
    unity = json.loads((REPO / "Unity/Assets/StreamingAssets/analysis_map.json").read_text(encoding="utf-8"))
    assert analysis == unity, "El mapa de Unity difiere del mapa de resultados"
    checks, summaries = [], []
    for case, data in cases.items():
        assert data["case"] == case
        assert data["displacements_m"] == analysis["disp"][case]
        for tag, values in analysis["reacciones"][case].items():
            assert data["reactions_kN"][tag] == values
        rows = []
        for tag, values in sorted(data["reactions_kN"].items(), key=lambda kv: int(kv[0])):
            rows.append(dict(nodoTag=int(tag), caso=case, aparece_en_tabla_Unity=tag in analysis["reacciones"][case],
                             **dict(zip(("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm"), values))))
        write(f"02_reacciones/reacciones_{case}.csv", rows)
        rows = []
        for tag, v in sorted(data["displacements_m"].items(), key=lambda kv: int(kv[0])):
            rows.append(dict(nodoTag=int(tag), caso=case, ux_m=v[0], uy_m=v[1], uz_m=v[2],
                             ux_mm=v[0]*1000, uy_mm=v[1]*1000, uz_mm=v[2]*1000,
                             u_planta_mm=math.hypot(v[0], v[1])*1000,
                             rx_rad=v[3], ry_rad=v[4], rz_rad=v[5]))
        write(f"03_desplazamientos/desplazamientos_{case}.csv", rows)
        if case in analysis["sismo"]:
            write(f"05_sismo/sismo_por_piso_{case}.csv", [dict(caso=case, **r) for r in analysis["sismo"][case]])
        rows = []
        for name, d in analysis["diagramas"][case].items():
            assert len(d["x"]) == len(d["N"]) == len(d["V"]) == len(d["M"])
            for x, n, v, m in zip(d["x"], d["N"], d["V"], d["M"]):
                rows.append(dict(caso=case, representante=name, elementTag=d["tag"], tipo=d["tipo"],
                                 seccion=d["seccion"], piso=d["piso"], L_m=d["L"], x_local_m=x, N_kN=n, V_kN=v, M_kNm=m))
        write(f"10_figuras/diagramas_representativos_{case}.csv", rows)
        scalar_checks = {k: v for k, v in data["verifications"].items() if not isinstance(v, (dict, list))}
        checks.append(dict(caso=case, **scalar_checks))
        summaries.append(dict(caso=case, nodos=data["summary"]["nodes_total"], elementos_FE=data["summary"]["elements_structural"],
                              carga_total_kN=data["summary"][f"Carga_{case}_total_kN"],
                              **{f"lambda_{c}": (data.get("superposition") or {}).get("lambdas", {}).get(c, 1 if c == case else 0) for c in ("G", "Q", "EX", "EY")}))
    write("01_casos_base/resumen_casos_excel.csv", summaries)
    write("08_verificacion/verificaciones_casos_excel.csv", checks)
    write("11_mapa_visor/tributarias_excel.csv", [dict(elementTag=int(tag), **{k:v for k,v in d.items() if k != "aportes"})
          for tag,d in cases["G"]["tributary_by_viga"].items()])
    # P-M: curvas fibra y HA tienen distinta cantidad de puntos; filas separadas.
    for folder in ("pm_columnas", "pm_muros"):
        rows = []
        for file in sorted((ROOT / "07_capacidad" / folder).glob("*.json")):
            d = json.loads(file.read_text(encoding="utf-8"))
            for model in ("fiber", "HA"):
                ps, ms = d.get(f"P_kN_{model}", []), d.get(f"M_kNm_{model}", [])
                assert len(ps) == len(ms)
                rows.extend(dict(curva=file.stem, seccion=d["seccion"], modelo=model, punto=i, P_kN=p, M_kNm=m)
                            for i,(p,m) in enumerate(zip(ps,ms),1))
        write(f"07_capacidad/{folder}/curvas_PM_excel.csv", rows)
    d = read("07_capacidad/mom_curv/mom_curv_columna_70x70.json")
    assert len(d["phi_1m"]) == len(d["M_kNm"])
    write("07_capacidad/mom_curv/momento_curvatura_excel.csv", [dict(seccion=d["seccion"], P_kN=d["P_kN"], paso=i, phi_1_m=p, M_kNm=m)
          for i,(p,m) in enumerate(zip(d["phi_1m"],d["M_kNm"]),1)])
    d = read("07_capacidad/sensibilidad/sensibilidad_secciones.json")
    write("07_capacidad/sensibilidad/sensibilidad_excel.csv", [dict(seccion=s, **r) for s,rows in d.items() for r in rows])
    with (ROOT / "06_superposicion/verificacion.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        for k in ("max_err_rel", "tol"):
            row[k] = float(row[k])
        row["n"] = int(row["n"])
        row["tol_proyecto"] = 1e-10
        row["cumple_tol_proyecto"] = row["max_err_rel"] < 1e-10
    write("06_superposicion/verificacion_excel.csv", rows)
    # La demanda crítica existente solo corresponde a COMBO: no inventar otros casos.
    d = read("09_demanda_capacidad/demanda_capacidad_critica.json")
    write("09_demanda_capacidad/demanda_capacidad_critica_COMBO_excel.csv", [{k:v for k,v in d.items() if not isinstance(v,(dict,list))}])
    for path, count in WRITTEN:
        print(f"OK {path}: {count} filas")
    print(f"{len(WRITTEN)} tablas adicionales verificadas; 5 CSV de fuerzas actualizados")


if __name__ == "__main__":
    main()
