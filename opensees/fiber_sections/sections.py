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

# Columna 70x70 del PORTICO EXTREMO (las 12 del plano estructural que se
# re-fuerzan: ids 66-113 / posiciones x en {-20,-30,-40,-45}). El plano del
# pórtico exige armadura perimetral MIXTA:
#     4 barras phi28 en las 4 esquinas + 16 barras phi36 intermedias
#     (etiquetadas B1/B2/B3: 4 en cara sup + 4 en cara inf + 4 por costado).
# Total 20 barras -> As = 4x28 + 16x36 = 187.5 cm2 (rho = 3.83%).
# Recubrimiento al centro de barra = 68 mm (40 + estribo phi10 + phi36/2).
COLUMNA_BORDE = {
    "nombre": "columna_borde_70x70",
    "tipo": "columna_borde",
    "b": 700.0, "h": 700.0,          # mm
    "rec": 68.0,                      # al centro de barra (phi36 manda)
    "estrobo": 10.0,
    "db": 36.0, "n_int": 16,          # 16 phi36 intermedias (B1/B2/B3)
    "db_esq": 28.0, "n_esq": 4,       # 4 phi28 en las esquinas
    "nFY": 24, "nFZ": 8,              # fibras de concreto
    "fuente": "plano pórtico extremo (4 phi28 esquinas + 16 phi36 perimetrales)",
}

# Seccion especial (SOLO elemento id=70): columna 70x70 del portico extremo
# con enfierradura FULL phi36 perimetral: 16 phi36 intermedias + 4 phi36 en
# las esquinas = 20 barras phi36. As = 20 x phi36 = 203.6 cm2 (rho = 4.16%).
COLUMNA_ID70 = {
    "nombre": "columna_id70",
    "tipo": "columna_id70",
    "b": 700.0, "h": 700.0,          # mm
    "rec": 68.0,                      # al centro de barra (phi36)
    "estrobo": 10.0,
    "db": 36.0, "n_int": 16,          # 16 phi36 intermedias
    "db_esq": 36.0, "n_esq": 4,       # 4 phi36 en las esquinas
    "nFY": 24, "nFZ": 8,              # fibras de concreto
    "fuente": "elemento id=70 (enfierradura full phi36 perimetral)",
}

MURO = {
    "nombre": "muro_30x356",
    "tipo": "muro",
    "bw": 300.0, "Lw": 3560.0,        # mm
    "borde": 400.0,                   # ancho de cada elemento de borde (mm)
    "rec": 50.0,                      # recubrimiento al centro de barra
    "nb_borde": 10, "db_borde": 40.0,  # phi40 por borde (disenio config unica)
    "db_malla": 10.0, "s_malla": 200.0,  # phi10 @ 20 cm, doble capa
    "filas_b": [80.0, 120.0, 160.0, 200.0, 240.0],
    "nFY": 40, "nFZ": 6,              # fibras de concreto (40 a lo largo)
    "fuente": "sections.json wall_30x356 + disenio config unica phi40",
}


def muro_tipificado(clave, bw_cm, Lw_cm):
    """Config de seccion de muro generica con regla proporcional al largo.

    Regla de escala:
      - borde concentrado = 11.2% del largo (400/3560 del 30x356).
      - filas de acero de borde repartidas entre 2.25% y 6.74% del largo
        con separacion minima 40 mm (minimo 2 filas).
      - db_borde = 40 mm (disenio: misma config para todas las secciones).
      - malla central de phi10 @ 200 mm doble capa (igual en todos).
      - fibras de concreto a lo largo proporcionales.
    """
    bw = bw_cm * 10.0
    Lw = Lw_cm * 10.0
    lo, hi = 0.0225 * Lw, 0.0674 * Lw
    rango = hi - lo
    if rango <= 0:
        filas = [lo]
    else:
        n = max(2, int(rango / 40.0) + 1)
        filas = [round(lo + rango * k / (n - 1), 1) for k in range(n)]
    return {
        "nombre": clave,
        "tipo": "muro",
        "bw": bw, "Lw": Lw,            # mm
        "borde": round(0.112 * Lw, 1),
        "rec": 50.0,
        "nb_borde": len(filas) * 2, "db_borde": 40.0,
        "db_malla": 10.0, "s_malla": 200.0,
        "filas_b": filas,
        "nFY": max(16, int(round(Lw / 89.0))),
        "nFZ": 6,
        "fuente": "regla proporcional muro_tipificado() phi40",
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


def build_columna_borde(mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra de la columna 70x70 del PORTICO EXTREMO
    (2D, bending fuerte). Eje y = altura (flexion), z = espesor (simetrica).
    20 barras perimetrales mixtas: 4 phi28 en las esquinas + 16 phi36
    intermedias (B1/B2/B3: 4 por cara), esquinas compartidas entre caras."""
    import openseespy.opensees as ops
    s = COLUMNA_BORDE
    b, h, r = s["b"], s["h"], s["rec"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -h / 2, -b / 2, h / 2, b / 2)

    a36 = abar(s["db"])          # area phi36 (intermedias)
    a28 = abar(s["db_esq"])      # area phi28 (esquinas)
    ysup = h / 2.0 - r           # posicion en y de las caras
    xl = b / 2.0 - r             # posicion en x de los costados

    # esquinas: 4 barras phi28 (una en cada esquina)
    for sx in (-xl, xl):
        for sy in (-ysup, ysup):
            ops.layer("straight", mat_ac, 1, a28, sy, sx, sy, sx)

    # cara superior/interior: 4 phi36 intermedias repartidas entre las
    # esquinas (x de -xl*0.6 a +xl*0.6 en 4 puntos equiespaciados: la barra
    # mas cercana a la esquina queda a 1/5 del semiancho)
    dx = 2.0 * xl / 5.0
    ops.layer("straight", mat_ac, 4, a36, ysup, -xl + dx, ysup, xl - dx)
    ops.layer("straight", mat_ac, 4, a36, -ysup, -xl + dx, -ysup, xl - dx)
    # costados: 4 phi36 intermedias repartidas entre las esquinas en y
    dy = 2.0 * ysup / 5.0
    ops.layer("straight", mat_ac, 4, a36, -ysup + dy, -xl, ysup - dy, -xl)
    ops.layer("straight", mat_ac, 4, a36, -ysup + dy, xl, ysup - dy, xl)


def build_columna_id70(mat_conc, mat_ac, sec_tag):
    """Crea la seccion fibra de la columna 70x70 del elemento id=70
    (2D, bending fuerte). Igual distribucion perimetral que la del portico
    extremo (20 barras) pero con TODAS las barras phi36 (full phi36)."""
    import openseespy.opensees as ops
    s = COLUMNA_ID70
    b, h, r = s["b"], s["h"], s["rec"]

    ops.section("Fiber", sec_tag, "-GJ", 1.0)
    ops.patch("rect", mat_conc, s["nFY"], s["nFZ"],
              -h / 2, -b / 2, h / 2, b / 2)

    a36 = abar(s["db"])          # area phi36
    ysup = h / 2.0 - r           # posicion en y de las caras
    xl = b / 2.0 - r             # posicion en x de los costados

    # 4 esquinas phi36
    for sx in (-xl, xl):
        for sy in (-ysup, ysup):
            ops.layer("straight", mat_ac, 1, a36, sy, sx, sy, sx)

    # caras sup/inf: 4 phi36 intermedias
    dx = 2.0 * xl / 5.0
    ops.layer("straight", mat_ac, 4, a36, ysup, -xl + dx, ysup, xl - dx)
    ops.layer("straight", mat_ac, 4, a36, -ysup, -xl + dx, -ysup, xl - dx)
    # costados: 4 phi36 intermedias
    dy = 2.0 * ysup / 5.0
    ops.layer("straight", mat_ac, 4, a36, -ysup + dy, -xl, ysup - dy, -xl)
    ops.layer("straight", mat_ac, 4, a36, -ysup + dy, xl, ysup - dy, xl)


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
    elif section["tipo"] == "columna_borde":
        build_columna_borde(mat_conc, mat_ac, sec_tag)
    elif section["tipo"] == "columna_id70":
        build_columna_id70(mat_conc, mat_ac, sec_tag)
    elif section["tipo"] == "muro":
        build_muro(section, mat_conc, mat_ac, sec_tag)
    else:
        raise ValueError(section["tipo"])


def area_concreto(section):
    """Area bruta de hormigon (mm2)."""
    if section["tipo"] in ("columna", "columna_borde", "columna_id70"):
        return section["b"] * section["h"]
    return section["bw"] * section["Lw"]


def area_acero(section):
    """Area total de acero longitudinal (mm2) y datos geometricos."""
    if section["tipo"] == "columna":
        asb = abar(section["db"])
        return section["barras"] * asb
    if section["tipo"] in ("columna_borde", "columna_id70"):
        return (section["n_esq"] * abar(section["db_esq"])
                + section["n_int"] * abar(section["db"]))
    # muro
    a_borde = section["nb_borde"] * abar(section["db_borde"])
    am = abar(section["db_malla"])
    y0 = section["Lw"] / 2 - section["borde"]
    n = int(round((2 * y0) / section["s_malla"])) + 1
    a_malla = n * 2.0 * am
    return a_borde + a_malla