"""Exporta fuerzas por caso para Excel en español (UTF-8 BOM, ; y coma decimal).

Una fila por elementTag FE, conservado sin remapearlo a la geometría del visor.
Fuerzas en kN y momentos en kN·m. Los valores locales conservan el signo;
las columnas unity_abs son sus módulos, como en la ficha de Unity.
No modifica el CSV histórico ni ejecuta nuevamente el análisis.
"""
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "resultados" / "01_casos_base"
OUT = REPO / "resultados" / "04_fuerzas_elementos"
CASES = ("G", "Q", "EX", "EY", "COMBO")
GLOBAL = ("Fx_kN", "Fy_kN", "Fz_kN", "Mx_kNm", "My_kNm", "Mz_kNm")
LOCAL = ("N_kN", "Vy_kN", "Vz_kN", "T_kNm", "My_kNm", "Mz_kNm")
BLOCKS = (
    ("global_i", "global_i", GLOBAL, False),
    ("global_j", "global_j", GLOBAL, False),
    ("local_i", "local_i", LOCAL, False),
    ("local_j", "local_j", LOCAL, False),
    ("unity_abs_i", "local_i", LOCAL, True),
    ("unity_abs_j", "local_j", LOCAL, True),
)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    unity = json.loads((REPO / "Unity/Assets/StreamingAssets/analysis_map.json").read_text(encoding="utf-8"))
    headers = ["elementTag", "caso", "tipo", "seccion"]
    headers += [f"{prefix}_{component}" for prefix, _, names, _ in BLOCKS for component in names]
    for case in CASES:
        suffix = "" if case == "G" else "_" + case
        source = BASE / f"edificio_full_results{suffix}.json"
        forces = json.loads(source.read_text(encoding="utf-8"))["element_forces_global"]
        rows = []
        for tag in sorted(forces, key=int):
            element = forces[tag]
            for key, mapped in (("global_i", "i"), ("global_j", "j"), ("local_i", "li"), ("local_j", "lj")):
                if element[key] != unity["forces"][case][tag][mapped]:
                    raise ValueError(f"Unity difiere: {case}, elemento {tag}, {key}")
            row = [tag, case, element["type"], element.get("section", "")]
            for _, key, _, absolute in BLOCKS:
                row.extend(str(abs(v) if absolute else v).replace(".", ",") for v in element[key])
            rows.append(row)
        target = OUT / f"fuerzas_elementos_{case}.csv"
        with target.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";")
            writer.writerow(headers)
            writer.writerows(rows)
        # Reabrir el CSV y comprobar todos los valores, no solo la muestra.
        with target.open(encoding="utf-8-sig", newline="") as stream:
            exported = list(csv.DictReader(stream, delimiter=";"))
        assert len(exported) == len(forces)
        assert len({r["elementTag"] for r in exported}) == len(forces)
        for row in exported:
            element = forces[row["elementTag"]]
            for prefix, key, names, absolute in BLOCKS:
                for component, value in zip(names, element[key]):
                    expected = abs(value) if absolute else value
                    assert float(row[f"{prefix}_{component}"].replace(",", ".")) == expected
        print(f"OK {target.name}: {len(rows)} elementos; valores verificados contra JSON y Unity")


if __name__ == "__main__":
    main()
