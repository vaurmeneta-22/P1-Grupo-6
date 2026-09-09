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


def seccion_columna(b=700.0, h=700.0, rec=62.5, db=25.0,
                    n_arriba=3, n_lat=2, n_abajo=3):
    """Columna 70x70 con 8phi25: devuelve (b, h, barras, Ast_total).
    barras = [(di, Asi), ...] con di = distancia desde fibra extrema
    comprimida (la cara superior en la flexion)."""
    As = math.pi * (db / 2.0) ** 2
    barras = [(rec, n_arriba * As),
              (h / 2.0, n_lat * As),
              (h - rec, n_abajo * As)]
    Ast = (n_arriba + n_lat + n_abajo) * As
    return b, h, barras, Ast


def seccion_muro(bw=300.0, Lw=3560.0, rec=50.0, borde=400.0,
                 db_borde=16.0, n_borde=4, db_malla=10.0, s_malla=200.0):
    """Muro 30x356: elementos de borde con 4phi16 cada uno + malla phi10@20
    doble en la zona central. Barras discretizadas en el largo."""
    bars = []
    Asb = n_borde * math.pi * (db_borde / 2.0) ** 2
    am = math.pi * (db_malla / 2.0) ** 2
    # borde inferior (cara comprimida), malla, borde superior
    y_malla = [borde + 50.0, Lw - borde - 50.0]     # centros de malla (2 zonas simples)
    # mas representativo: barras de malla distribuidas cada s_malla
    n = int(round((Lw - 2 * borde) / s_malla))
    for k in range(1, n + 1):
        yk = borde + k * s_malla
        bars.append((yk, 2.0 * am))                  # doble capa
    bars += [(rec, Asb), (Lw - rec, Asb)]
    Ast = 2 * Asb + n * 2.0 * am
    return bw, Lw, bars, Ast


def interaccion(cfg_col=True, n_c=400):
    """Barre c y devuelve (P_kN, M_kNm) de la interaccion nominal.
    cfg_col=True: columna, False: muro."""
    if cfg_col:
        b, h, barras, Ast = seccion_columna()
    else:
        b, h, barras, Ast = seccion_muro()
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
    """P0 nominal (NCh/ACI sin factor), P en kN. Col o muro."""
    if cfg_col:
        b, h, barras, Ast = seccion_columna()
    else:
        b, h, barras, Ast = seccion_muro()
    Ag = b * h
    P0 = 0.85 * F_C * (Ag - Ast) + FY * Ast
    return P0 / 1e3


def punto_momento_balanceado(cfg_col=True):
    """Punto balanceado: e = fy/Es en traccion con eps_cu en compresion.
    De la compatibilidad con la barra mas traccionada (di = h-rec):
      c_b = eps_cu*d / (eps_cu + fy/Es),  d = h - rec.
    Devuelve (P[kN], M[kN*m])."""
    if cfg_col:
        b, h, barras, Ast = seccion_columna()
        rec = 62.5
    else:
        b, h, barras, Ast = seccion_muro()
        rec = 50.0
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