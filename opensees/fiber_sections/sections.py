"""
Secciones de fibra de la Parte D -  (Grupo 6)

Las fibras van en el plano local de la seccion (y: altura de flexion, z: espesor),
en mm. El concreto se discretiza con patches y el acero con layers.

COLUMNA 70x70  (data/sections.json: width=0.70, height=0.70 m)
     16 barras 28 mm perimetrales (5 cara sup + 5 cara inf + 3 por
     costado, sin repetir esquinas)  -  estribos 10 mm (se anade como
     confinamiento implicito en el material)  -  recubrimiento = 40 mm al
     estribo, luego la barra queda a r = 40 + 10 + 28/2 = 64.0 mm del borde.
     Disposicion perimetral (configuracion original del plano del contrato):
     parrilla perimetral sin barras al centro. As = 16 x Ø28 = 98.5 cm2
     (rho = 2.01%).

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
    "rec": 64.0,                      # recubrimiento al centro de barra (mm)
    "estrobo": 10.0,
    "barras": 16, "db": 28.0,         # 16 phi28 perimetral (5+5+3+3)
    "nFY": 24, "nFZ": 8,              # fibras de concreto
    "fuente": "sections.json column_70x70 (config original del plano)",
}

MURO = {
    "nombre": "muro_30x356",
    "tipo": "muro",
    "bw": 300.0, "Lw": 3560.0,        # mm
    "borde": 400.0,                   # ancho de cada elemento de borde (mm)
    "rec": 50.0,                      # recubrimiento al centro de barra
    "nb_borde": 4, "db_borde": 16.0,  # 4 phi16 por borde (2 por extremo/fila)
    "db_malla": 10.0, "s_malla": 200.0,  # phi10 @ 20 cm, doble capa
    "filas_b": [80.0, 240.0],         # filas de acero de borde (desde el extremo)
    "nFY": 40, "nFZ": 6,              # fibras de concreto (40 a lo largo)
    "fuente": "sections.json wall_30x356 (contracto)",
}


def muro_tipificado(clave, bw_cm, Lw_cm):
    """Config de seccion de muro generica con la misma regla que el 30x356
    (recubrimiento 50 mm al centro de barra, bordes con 4 phi16 en 2 filas y
    malla phi10 @ 20 cm doble capa en la zona central) pero escalada
    proporcionalmente a la geometria dada. `clave` es el nombre de la seccion
    en el contrato (p.ej. "30x2695"); bw_cm x Lw_cm son las dimensiones en cm.

    Regla de escala:
      - borde concentrado = 11.2% del largo (400/3560 del 30x356).
      - filas de acero de borde a 2.25% y 6.74% del largo (80/3560, 240/3560).
      - malla central de phi10 @ 200 mm doble capa (igual en todos).
      - fibras de concreto a lo largo proporcionales (40 para Lw=3560 mm).
    """
    bw = bw_cm * 10.0
    Lw = Lw_cm * 10.0
    return {
        "nombre": clave,
        "tipo": "muro",
        "bw": bw, "Lw": Lw,            # mm
        "borde": round(0.112 * Lw, 1),
        "rec": 50.0,
        "nb_borde": 4, "db_borde": 16.0,
        "db_malla": 10.0, "s_malla": 200.0,
        "filas_b": [round(0.0225 * Lw, 1), round(0.0674 * Lw, 1)],
        "nFY": max(16, int(round(Lw / 89.0))),
        "nFZ": 6,
        "fuente": "regla proporcional muro_tipificado()",
    }


# Muros reales del contrato (no 1D) que circulan en el edificio. El 30x356
# (reference) se mantiene en MURO; el resto se tipifican con la regla.
# Formato: (clave contrato, espesor cm, largo en planta cm). En el contrato
# "30x2695" el largo es 269.5 cm (los b/h de Edificio.json lo confirman).
MUROS_EXTRA = [
    ("60x291.5", 60.0, 291.5),
    ("60x292", 60.0, 292.0),
    ("25x795", 25.0, 795.0),
    ("25x585", 25.0, 585.0),
    ("30x2695", 30.0, 269.5),
    ("25x282", 25.0, 282.0),
    ("30x725", 30.0, 725.0),
    ("30x1000", 30.0, 1000.0),
    ("30x890", 30.0, 890.0),
    ("30x615", 30.0, 615.0),
    ("25x158", 25.0, 158.0),
    ("25x365", 25.0, 365.0),
    ("30x225", 30.0, 225.0),
    ("30x310", 30.0, 310.0),
]
WALLS = [muro_tipificado(clave, bw, Lw) for clave, bw, Lw in MUROS_EXTRA]

# area de una barra (mm2)
def abar(d):
    return 3.141592653589793 * (d / 2.0) ** 2


def build_columna(mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra de la columna 70x70 (2D, bending fuerte).
    Eje y = altura (flexion), z = espesor (simetrica).
    16 phi28 perimetrales: 5 en la cara superior + 5 en la inferior
    (incluyen las 4 esquinas) y 3 en cada costado (sin repetir esquinas)."""
    import openseespy.opensees as ops
    s = COLUMNA
    b, h, r = s["b"], s["h"], s["rec"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -h / 2, -b / 2, h / 2, b / 2)

    db = s["db"]
    a = abar(db)
    ysup = h / 2.0 - r          # posicion en y de las barras de caras
    xl = b / 2.0 - r            # posicion en x de las barras de costados
    # cara superior: 5 barras a lo ancho (incluye las 2 esquinas superiores)
    ops.layer("straight", mat_ac, 5, a, ysup, -xl, ysup, xl)
    # cara inferior: 5 barras a lo ancho (incluye las 2 esquinas inferiores)
    ops.layer("straight", mat_ac, 5, a, -ysup, -xl, -ysup, xl)
    # costados: 3 barras intermedias por lado, separadas el mismo paso
    ymin = -ysup / 2.0          # -143.0 (barra mas baja del costado)
    ymax = ysup / 2.0           # +143.0
    ops.layer("straight", mat_ac, 3, a, ymin, -xl, ymax, -xl)
    ops.layer("straight", mat_ac, 3, a, ymin, xl, ymax, xl)


def build_muro(section, mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra de un muro generico (2D, flexion en el plano).
    Eje y = largo Lw (flexion fuerte), z = espesor bw.
    - Elementos de borde (borde mm) en cada extremo: 2 barras por fila,
      filas separadas segun filas_b (2 filas -> 4 por borde) del config.
    - Malla central doble db_malla @ s_malla -> capa doble en el espesor."""
    import openseespy.opensees as ops
    s = section
    Lw, bw, r = s["Lw"], s["bw"], s["rec"]
    borde = s["borde"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -Lw / 2, -bw / 2, Lw / 2, bw / 2)

    # -- elementos de borde -------------------------------------------------
    db = s["db_borde"]
    a = abar(db)
    # 2 filas x (2 barras por fila) dentro de cada borde
    filas_b = s.get("filas_b", [80.0, 240.0])
    for fila in filas_b:
        # borde inferior (extremo y = -Lw/2)
        ops.layer("straight", mat_ac, 2, a, -Lw / 2 + fila, -bw / 2 + 45, -Lw / 2 + fila, bw / 2 - 45)
        # borde superior
        ops.layer("straight", mat_ac, 2, a, Lw / 2 - fila, -bw / 2 + 45, Lw / 2 - fila, bw / 2 - 45)

    # -- malla central doble ------------------------------------------------
    dbm = s["db_malla"]
    am = abar(dbm)
    # 2 capas x (una barra 10mm cada s_malla) => en la seccion 2D la capa es una
    # barra equivalente por posicion con area 2*am (una en cada cara).
    a_equiv = 2.0 * am
    y0 = -Lw / 2 + borde
    y1 = Lw / 2 - borde
    n = max(1, int(round((y1 - y0) / s["s_malla"])) + 1)
    ops.layer("straight", mat_ac, n, a_equiv, y0, 0.0, y1, 0.0)


def build(section, mat_conc, mat_ac, sec_tag):
    """Construye la seccion segun el dict de configuracion."""
    if section["tipo"] == "columna":
        build_columna(mat_conc, mat_ac, sec_tag)
    elif section["tipo"] == "muro":
        build_muro(section, mat_conc, mat_ac, sec_tag)
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