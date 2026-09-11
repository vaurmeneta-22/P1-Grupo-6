"""
Verificacion independiente con Hormigon Armado (bloque rectangular ACI/NCh)
- Parte D  (Grupo 6)

Calcula por formulas ANALITICAS del curso de H.A. la interaccion P-M nominal
de una seccion y la compara con la obtenida por OpenSees (fiber). Solo usa
Python estandar (sin OpenSees): es el contraste independiente pedido por el
enunciado ("al menos una comparacion independiente con contenidos del curso").

Metodo (ACI 318-19 / NCh430 compatible):
  - Diagrama de compresiones rectangular equivalente:
      alpha1 = 0.85                      (f'c <= 28 MPa)
      alpha1 = max(0.85 - 0.05*(f'c-28)/7 , 0.65)
      beta1  = 0.85 - 0.05*(f'c - 28)/7  (mismo piso >= 0.65)
      a = beta1 * c
  - Ruina controlada por concreto: eps_cu = 0.0035 en la fibra extrema
    comprimida. Posicion del eje neutro c (desde la fibra extrema).
  - Compatibilidad: eps_si = eps_cu * (c - di) / c, con di = distancia a la
    fibra extrema. Traccion positiva. Tension en el acero:
      fs = E_s * eps_s,   |fs| <= f_y  ;  con E_s = 200000 MPa.
  - Equilibrio:
      P = Cc + sum(Fs_i),   Cc = alpha1*f'c*b*a
      M = Cc*(h/2 - a/2) + sum(Fs_i * (h/2 - di))
  - Barriendo c desde traccion pura (c->0, todo el acero fluye en traccion)
    hasta compresion pura (c -> h) se obtiene la curva (P, M).
  - Capacidad axial pura (c = h):  P0 = 0.85*f'c*(Ag - Ast) + fy*Ast.

Convenciones: compresion +, traccion -. P en kN, M en kN*m.
"""

import math

F_C = 35.0     # MPa
FY = 420.0     # MPa
ES = 200000.0  # MPa
EPS_CU = 0.0035


def _constantes(fc=F_C):
    a1 = 0.85 if fc <= 28.0 else max(0.85 - 0.05 * (fc - 28.0) / 7.0, 0.65)
    b1 = 0.85 if fc <= 28.0 else max(0.85 - 0.05 * (fc - 28.0) / 7.0, 0.65)
    return a1, b1


def seccion_columna(b=700.0, h=700.0, rec=64.0, db=28.0):
    """Columna 70x70 con 16 phi28 perimetrales (5 cara sup + 5 cara inf +
    3 por costado, sin repetir esquinas): devuelve
    (b, h, barras, Ast_total).
    barras = [(di, Asi), ...] con di = distancia desde fibra extrema
    comprimida (la cara superior en la flexion)."""
    As = math.pi * (db / 2.0) ** 2
    r = rec
    hy = h / 2.0 - r                      # posicion de las caras (286 mm)
    # cara superior e inferior: 5 barras a lo ancho (incluyen las esquinas)
    barras = [(r, 5.0 * As), (h - r, 5.0 * As)]
    # costados: 3 barras intermedias por lado (2 por nivel: izq + der),
    # equidistantes entre esquinas -> y = -hy/2, 0, +hy/2
    for y in (-hy / 2.0, 0.0, hy / 2.0):
        barras.append((h / 2.0 - y, 2.0 * As))
    Ast = 16.0 * As
    return b, h, barras, Ast


def _resolve_seccion(cfg):
    """Mapea el selector de seccion a la tupla (b, h, barras, Ast).
    Acepta bool (True=columna, False=muro, API historica) o str
    ('columna' | 'muro' | 'columna_borde' | 'columna_id70'), verificando que
    el selector corresponda al bloque analitico usado."""
    if cfg is True or cfg == "columna":
        return seccion_columna()
    if cfg is False or cfg == "muro":
        return seccion_muro()
    if cfg == "columna_id70":
        return seccion_columna_id70()
    return seccion_columna_borde()


def seccion_columna_id70(b=700.0, h=700.0, rec=68.0, db=36.0):
    """Columna 70x70 del elemento id=70 con enfierradura FULL phi36
    perimetral: 4 phi36 en las esquinas + 16 phi36 intermedias (20 barras).
    Devuelve (b, h, barras, Ast_total)."""
    A36 = math.pi * (db / 2.0) ** 2
    r = rec
    hy = h / 2.0 - r                        # 282 mm (centro de las caras)
    # cara superior e inferior: 2 esquinas phi36 + 4 intermedias phi36
    barras = [(r, 2.0 * A36 + 4.0 * A36),
              (h - r, 2.0 * A36 + 4.0 * A36)]
    # costados: 4 phi36 por lado, equidistantes entre las esquinas
    dy = 2.0 * hy / 5.0
    for k in range(1, 5):
        y = -hy + k * dy                    # -169.2 .. +169.2
        barras.append((h / 2.0 - y, 2.0 * A36))
    Ast = 20.0 * A36
    return b, h, barras, Ast


def seccion_columna_borde(b=700.0, h=700.0, rec=68.0, db=36.0,
                          db_esq=28.0):
    """Columna 70x70 del portico extremo con 20 barras perimetrales mixtas:
    4 phi28 en las esquinas + 16 phi36 intermedias (B1/B2/B3: 4 por cara).
    Devuelve (b, h, barras, Ast_total). barras = [(di, Asi), ...] con
    di = distancia desde la fibra extrema comprimida (cara superior)."""
    A36 = math.pi * (db / 2.0) ** 2
    A28 = math.pi * (db_esq / 2.0) ** 2
    r = rec
    hy = h / 2.0 - r                        # 282 mm (centro de las caras)
    # cara superior e inferior: 2 esquinas phi28 + 4 intermedias phi36
    barras = [(r, 2.0 * A28 + 4.0 * A36),
              (h - r, 2.0 * A28 + 4.0 * A36)]
    # costados: 4 phi36 por lado, equidistantes entre las esquinas
    dy = 2.0 * hy / 5.0
    for k in range(1, 5):
        y = -hy + k * dy                    # -169.2 .. +169.2
        barras.append((h / 2.0 - y, 2.0 * A36))
    Ast = 4.0 * A28 + 16.0 * A36
    return b, h, barras, Ast


def seccion_muro(bw=300.0, Lw=3560.0, rec=50.0, borde=400.0,
                 filas_b=None, db_borde=40.0, db_malla=10.0, s_malla=200.0):
    """Muro tipificado con enfierradura repartida en el borde (φ40, filas con
    separación ≥40mm) + malla phi10@20 doble en la zona central.
    Cada fila pone 2 barras φdb_borde (una por cara del espesor) en el borde
    inferior y 2 en el superior (misma disposición que build_muro/fiber).
    Si filas_b=None usa 5 filas para el 30x356."""
    if filas_b is None:
        filas_b = [80.0, 120.0, 160.0, 200.0, 240.0]   # 30x356, Lw=3560
    bars = []
    ab = math.pi * (db_borde / 2.0) ** 2
    am = math.pi * (db_malla / 2.0) ** 2
    for fk in filas_b:
        bars.append((fk, 2.0 * ab))          # borde inferior (2 caras)
        bars.append((Lw - fk, 2.0 * ab))     # borde superior
    n = int(round((Lw - 2 * borde) / s_malla))
    n_malla = 0
    for k in range(1, n + 1):
        yk = borde + k * s_malla
        if yk < Lw - borde:
            bars.append((yk, 2.0 * am))      # malla doble capa
            n_malla += 1
    Ast = len(filas_b) * 4.0 * ab + n_malla * 2.0 * am
    return bw, Lw, bars, Ast


def interaccion(cfg_col=True, n_c=400):
    """Barre c y devuelve (P_kN, M_kNm) de la interaccion nominal.
    cfg_col: True/False (col/muro, API historica) o 'columna'/'muro'/
    'columna_borde'."""
    b, h, barras, Ast = _resolve_seccion(cfg_col)
    a1, b1 = _constantes()

    P_kN, M_kNm = [], []
    # c va desde un valor pequeno (todo acero traccionado, ~0.05h) hasta h
    cds = [0.05 * h + k * (h - 0.05 * h) / (n_c - 1) for k in range(n_c)]
    for c in cds:
        a = b1 * c
        Cc = a1 * F_C * b * a
        if a > h:                      # bloque iguala/rebasa seccion
            a = h
            Cc = a1 * F_C * b * h
        Fs = 0.0
        Ms = 0.0
        for di, Asi in barras:
            eps = EPS_CU * (c - di) / c
            fs = ES * eps
            if fs > FY:
                fs = FY
            elif fs < -FY:
                fs = -FY
            Fs += fs * Asi
            Ms += fs * Asi * (h / 2.0 - di)
        P = Cc + Fs
        M = Cc * (h / 2.0 - a / 2.0) + Ms
        P_kN.append(P / 1e3)
        M_kNm.append(M / 1e6)
    return P_kN, M_kNm


def capacidad_pura_axial(cfg_col=True):
    """P0 nominal (NCh/ACI sin factor), P en kN. Col, muro o columna_borde."""
    b, h, barras, Ast = _resolve_seccion(cfg_col)
    Ag = b * h
    P0 = 0.85 * F_C * (Ag - Ast) + FY * Ast
    return P0 / 1e3


def punto_momento_balanceado(cfg_col=True):
    """Punto balanceado: e = fy/Es en traccion con eps_cu en compresion.
    De la compatibilidad con la barra mas traccionada (di = h-rec):
      c_b = eps_cu*d / (eps_cu + fy/Es),  d = h - rec.
    Devuelve (P[kN], M[kN*m])."""
    b, h, barras, Ast = _resolve_seccion(cfg_col)
    rec = {"columna_borde": 68.0, "columna_id70": 68.0, "muro": 50.0,
           False: 50.0, "columna": 64.0, True: 64.0}[cfg_col]
    a1, b1 = _constantes()
    d = h - rec
    c = EPS_CU * d / (EPS_CU + FY / ES)
    a = min(b1 * c, h)
    Cc = a1 * F_C * b * a
    Fs_tot = 0.0
    Ms = 0.0
    for di, Asi in barras:
        eps = EPS_CU * (c - di) / c
        fs = max(min(ES * eps, FY), -FY)
        Fs_tot += fs * Asi
        Ms += fs * Asi * (h / 2.0 - di)
    P = Cc + Fs_tot
    M = Cc * (h / 2.0 - a / 2.0) + Ms
    return P / 1e3, M / 1e6