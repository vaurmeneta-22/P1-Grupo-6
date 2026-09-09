"""
Secciones de fibra de la Parte D -  (Grupo 6)

Las fibras van en el plano local de la seccion (y: altura de flexion, z: espesor),
en mm. El concreto se discretiza con patches y el acero con layers.

  COLUMNA 70x70  (data/sections.json: width=0.70, height=0.70 m)
    8 barras 25 mm  +  estribos 10 mm (se anade como confinamiento implicito
    en el material)  -  recubrimiento = 40 mm al estribo, luego la barra queda
    a r = 40 + 10 + 25/2 = 62.5 mm del borde.
    Disposicion: 3 arriba, 2 laterales, 3 abajo (8 total).

  MURO 30x356  (la seccion mas frecuente del contrato: wall_30x356)
    espesor bw = 300 mm, largo total Lw = 3560 mm.
    Bordefile: 2 elementos de borde concentrados de 400x300 con 4 barras 16 mm
    en cada uno (2 por fila), separacion minima entre barras 80 mm.
    Malla central: 10 mm @ 20 cm en dos caras (doble): As x capa = 2 barras de
    10 mm cada 200 mm -> se discretiza como capa doble en la zona central.
"""

# ---------------------------------------------------------------------------
# configuracion por seccion
# ---------------------------------------------------------------------------
COLUMNA = {
    "nombre": "columna_70x70",
    "tipo": "columna",
    "b": 700.0, "h": 700.0,          # mm
    "rec": 62.5,                      # recubrimiento al centro de barra (mm)
    "estrobo": 10.0,
    "barras": 8, "db": 25.0,          # 8 phi25
    "nFY": 24, "nFZ": 8,              # fibras de concreto
    "fuente": "sections.json column_70x70",
}

MURO = {
    "nombre": "muro_30x356",
    "tipo": "muro",
    "bw": 300.0, "Lw": 3560.0,        # mm
    "borde": 400.0,                   # ancho de cada elemento de borde (mm)
    "rec": 50.0,                      # recubrimiento al centro de barra
    "nb_borde": 4, "db_borde": 16.0,  # 4 phi16 por borde (2 por extremo/fila)
    "db_malla": 10.0, "s_malla": 200.0,  # phi10 @ 20 cm, doble capa
    "nFY": 40, "nFZ": 6,              # fibras de concreto (40 a lo largo)
    "fuente": "sections.json wall_30x356 (contracto)",
}

# area de una barra (mm2)
def abar(d):
    return 3.141592653589793 * (d / 2.0) ** 2


def build_columna(mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra de la columna 70x70 (2D, bending fuerte).
    Eje y = altura (flexion), z = espesor (simetrica).
    Barras en 3 filas: 3 arriba / 2 centrales / 3 abajo."""
    import openseespy.opensees as ops
    s = COLUMNA
    b, h, r = s["b"], s["h"], s["rec"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -h / 2, -b / 2, h / 2, b / 2)

    y_top = h / 2 - r
    y_mid = 0.0
    y_bot = -h / 2 + r
    x1 = -b / 2 + r
    x2 = b / 2 - r
    db = s["db"]
    a = abar(db)
    # fila superior (3), central (2) e inferior (3)
    ops.layer("straight", mat_ac, 3, a, y_top, x1, y_top, x2)
    ops.layer("straight", mat_ac, 2, a, y_mid, x1, y_mid, x2)
    ops.layer("straight", mat_ac, 3, a, y_bot, x1, y_bot, x2)


def build_muro(mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra del muro 30x356 (2D, flexion en el plano).
    Eje y = largo Lw (flexion fuerte), z = espesor bw.
    - Elementos de borde (400 mm) en cada extremo: 2 barras de 16 mm por fila,
      filas separadas 80 mm (2 filas -> 4 por borde).
    - Malla central doble 10 @ 200 -> capa doble centrada en el espesor."""
    import openseespy.opensees as ops
    s = MURO
    Lw, bw, r = s["Lw"], s["bw"], s["rec"]
    borde = s["borde"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -Lw / 2, -bw / 2, Lw / 2, bw / 2)

    # -- elementos de borde -------------------------------------------------
    db = s["db_borde"]
    a = abar(db)
    # 2 filas x (2 barras por fila) dentro de cada borde, separacion 80 mm
    filas_b = [80.0, 240.0]           # a 80 y 240 mm del borde
    for fila in filas_b:
        # borde inferior (extremo y = -Lw/2)
        ops.layer("straight", mat_ac, 2, a, -Lw / 2 + fila, -bw / 2 + 45, -Lw / 2 + fila, bw / 2 - 45)
        # borde superior
        ops.layer("straight", mat_ac, 2, a, Lw / 2 - fila, -bw / 2 + 45, Lw / 2 - fila, bw / 2 - 45)

    # -- malla central doble ------------------------------------------------
    dbm = s["db_malla"]
    am = abar(dbm)
    # 2 capas x (una barra 10mm cada 200mm) => en la seccion 2D la capa es una
    # barra equivalente por posicion con area 2*am (una en cada cara).
    a_equiv = 2.0 * am
    y0 = -Lw / 2 + borde
    y1 = Lw / 2 - borde
    n = int(round((y1 - y0) / s["s_malla"])) + 1
    ops.layer("straight", mat_ac, n, a_equiv, y0, 0.0, y1, 0.0)


def build(section, mat_conc, mat_ac, sec_tag):
    """Construye la seccion segun el dict de configuracion."""
    if section["tipo"] == "columna":
        build_columna(mat_conc, mat_ac, sec_tag)
    elif section["tipo"] == "muro":
        build_muro(mat_conc, mat_ac, sec_tag)
    else:
        raise ValueError(section["tipo"])


def area_concreto(section):
    """Area bruta de hormigon (mm2)."""
    if section["tipo"] == "columna":
        return section["b"] * section["h"]
    return section["bw"] * section["Lw"]


def area_acero(section):
    """Area total de acero longitudinal (mm2) y datos geometricos."""
    if section["tipo"] == "columna":
        asb = abar(section["db"])
        return section["barras"] * asb
    # muro
    a_borde = section["nb_borde"] * abar(section["db_borde"])
    am = abar(section["db_malla"])
    y0 = section["Lw"] / 2 - section["borde"]
    n = int(round((2 * y0) / section["s_malla"])) + 1
    a_malla = n * 2.0 * am
    return a_borde + a_malla