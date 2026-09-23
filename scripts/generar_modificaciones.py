# -*- coding: utf-8 -*-
"""
GENERAR MODIFICACIONES DEL MODELO (Semana 5)

Deriva los contratos modificados a partir del contrato maestro `Edificio.json`
SIN tocar la linea base. Cada modificacion = 1 variante reproducible.

  Mod A  ->  Edificio_mod_A.json   Viga 147 : seccion 60x80 -> 50x75 cm
  Mod B  ->  Edificio_mod_B.json   Columna 1 (nodo 1): base EMPOTRADA 1,1,1,1,1,1
                                    -> base ARTICULADA 1,1,1,0,0,0 (giros libres)

Uso:
    python scripts/generar_modificaciones.py
"""
import copy
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAESTRO = os.path.join(REPO, "Edificio.json")


def cargar(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def guardar(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return [k for k, v in data.items()]  # claves raiz


def mostrar_dif(data_base, data_mod, titulo):
    """Reporta diferencias estructurales del contrato."""
    def ficha(d, key):
        e = next(e for e in d["elements"] if e["id"] == int(key))
        return e
    beam = ficha(data_base, 147)
    print(f"\n=== {titulo} ===")
    print(f"  viga 147   base: section={beam['section']} b={beam['b']}cm h={beam['h']}cm")
    beam_m = ficha(data_mod, 147)
    print(f"  viga 147   mod : section={beam_m['section']} b={beam_m['b']}cm h={beam_m['h']}cm")
    s_base = next(s for s in data_base["supports"] if s["node"] == 1)
    s_mod = next(s for s in data_mod["supports"] if s["node"] == 1)
    print(f"  apoyo nodo1 base: type={s_base['type']} DOF={s_base['DOF']}")
    print(f"  apoyo nodo1 mod : type={s_mod['type']} DOF={s_mod['DOF']}")
    diffs = 0
    for key in ("nodes", "elements", "supports", "floors"):
        if len(data_base.get(key, [])) != len(data_mod.get(key, [])):
            print(f"  [ATENCION] len({key}) difiere")
            diffs += 1
    if not diffs:
        print("  topologia (nodos/elementos/apoyos/floors) SIN cambios de cantidad")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    base = cargar(MAESTRO)

    # --- Mod A: dimension de viga 147 ---
    mod_a = copy.deepcopy(base)
    for e in mod_a["elements"]:
        if e["id"] == 147:
            e["section"] = "50x75"
            e["b"] = 50.0
            e["h"] = 75.0
    guardar(mod_a, os.path.join(REPO, "Edificio_mod_A.json"))

    # --- Mod B: condicion de apoyo de la columna 1 ---
    mod_b = copy.deepcopy(base)
    for s in mod_b["supports"]:
        if s["node"] == 1:
            s["type"] = "pinned"
            s["DOF"] = [1, 1, 1, 0, 0, 0]
    guardar(mod_b, os.path.join(REPO, "Edificio_mod_B.json"))

    mostrar_dif(base, mod_a, "Mod A -> Edificio_mod_A.json (rigidez viga 147)")
    mostrar_dif(base, mod_b, "Mod B -> Edificio_mod_B.json (apoyo columna 1)")
    print("\nOK: Edificio_mod_A.json y Edificio_mod_B.json generados "
          "(linea base intocada).")


if __name__ == "__main__":
    main()