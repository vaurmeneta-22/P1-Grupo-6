# -*- coding: utf-8 -*-
"""
areas_tributarias.py
Calcula la carga lineal que cada loza transfiere a sus vigas de borde
por el metodo de areas tributarias (45 grados).

Convencion del contrato (confirmada):
  - Nodos: (x, y, z) con z = ALTURA vertical.
  - Loza:  rectangulo en planta; xi..xj en X, zi..zj en la direccion Y (de nodos),
           yi = altura. Espesor t.
  - Cada loza pertenece a un piso por su altura yi (yace ~32.5cm sobre la
    reticula de vigas de ese piso).

Metodo 45:
  Losas rectangulares Lx x Ly; cada viga de borde recibe un area tributaria:
    - los 2 lados (direccion Y, vigas beam_x)  -> trapecios  (ejes largos)
    - las 2 lados (direccion X, vigas beam_y)   -> triangulos (ejes cortos)
  p_viga = w_losa * A_tributaria / L_borde   (kN/m)
  w_losa = gamma_concreto * t                (kN/m2)
"""

import json
import math
import os

# Concreto normal: densidad 2400 kg/m3 -> peso especifico (kN/m3).
# Unificado con opensees_edificio_v1.py / v2 (antes habia 25.0 aqui).
GAMMA_CONC = 2400.0 * 9.81 / 1000.0   # = 23.544 kN/m3

# Niveles de losa (yi, cm) -> piso; y nivel de nodo/viga de su reticula (z, cm)
# Determinado empiricamente: losa 388.5 -> nodos 356 ; 744.5 -> 712 ; etc.
PISO_ALTURAS = {
    388.5: ('Piso 1', 356.0),
    744.5: ('Piso 2', 712.0),
    1100.5: ('Piso 3', 1068.0),
    1456.5: ('Piso 4', 1424.0),
    1812.5: ('Techo', 1780.0),
}

# Tolerancia para emparejar la altura de una loza con su piso. Algunas losas
# (techo/parapeto) caen unos cm por encima del nivel nominal (p.ej. 1458.0 y
# 1814.0 vs 1456.5 y 1812.5); sin esto quedarian sin transferir su carga.
PISO_TOL_CM = 15.0

def piso_de(yi_cm):
    """Resuelve el piso (fl, z_reticula) mas cercano a yi_cm dentro de PISO_TOL_CM.
    Retorna (floor_label, z_viga_cm) o None si esta aislado."""
    for nominal, (fl, z) in PISO_ALTURAS.items():
        if abs(yi_cm - nominal) <= PISO_TOL_CM:
            return fl, z
    return None

def cargar_contrato(path):
    with open(path, 'encoding' if False else 'r', encoding='utf-8') as f:
        return json.load(f)

def normalizar_loza(e):
    """Loza -> dict normalizado: rect (xmin,xmax,ymin,ymax) en cm, espesor t en cm, altura yi."""
    xmin, xmax = sorted((e['xi'], e['xj']))
    ymin, ymax = sorted((e['zi'], e['zj']))   # zi..zj = eje Y de nodos
    return {
        'id': e['id'],
        'yi': e['yi'],                 # altura de la losa
        'xi': xmin, 'xmax': xmax,
        'ymin': ymin, 'ymax': ymax,
        't': e['t'],
        'Lx': xmax - xmin,
        'Ly': ymax - ymin,
    }

def vigas_por_nivel(beams, nid):
    """Retorna dict: (x_const)lista de beam_y y (y_const)lista de beam_x, por nivel z."""
    by_x = {}   # (z, x) -> lista de (y1,y2, id)
    by_y = {}   # (z, y) -> lista de (x1,x2, id)
    for e in beams:
        a, b = nid[e['node_i']], nid[e['node_j']]
        z = a['z']
        if abs(a['x'] - b['x']) < 0.5:   # beam_y: x constante, se extiende en Y
            x = a['x']
            y1, y2 = sorted((a['y'], b['y']))
            by_y.setdefault((z, x), []).append((y1, y2, e['id'], e['section']))
        elif abs(a['y'] - b['y']) < 0.5: # beam_x: y constante, se extiende en X
            y = a['y']
            x1, x2 = sorted((a['x'], b['x']))
            by_x.setdefault((z, y), []).append((x1, x2, e['id'], e['section']))
    return by_x, by_y

# Tolerancia (cm) para el solape/cobertura: por debajo se considera hueco.
SOLAPE_MIN_CM = 0.5


def buscar_viga(seg_x, seg_y, nivel_z, eje, valor, min0, max0):
    """
    (Compat: usado por la verificacion de losas soportadas.)
    Busca TODAS las vigas en el plano nivel_z que yacen sobre el eje
    (eje='x' o 'y') = valor y cubren [min0, max0]. Retorna la lista de
    dicts {id, section, c0, c1, L_m, ov_cm} con cobertura > SOLAPE_MIN_CM,
    una por tramo recepto, en orden de coordenada creciente. NO se asigna
    aqui un unico 'ganador' (eso sigue en tramos_receptores).
    """
    out = []
    for c1, c2, idb, sec in lista_por_eje(seg_x, seg_y, nivel_z, eje, valor):
        ov = min(max0, c2) - max(min0, c1)
        if ov > SOLAPE_MIN_CM:
            a = max(min0, c1)
            b = min(max0, c2)
            out.append({
                'id': idb,
                'section': sec,
                'c0': a, 'c1': b,                # linea de contacto [cm]
                'Lcm': c2 - c1,
                'L': (c2 - c1) / 100.0,
                'ov_cm': b - a,
            })
    out.sort(key=lambda v: v['c0'])
    return out


def lista_por_eje(seg_x, seg_y, nivel_z, eje, valor):
    """Lista (c1, c2, idb, seccion) de las vigas del plano nivel_z cuyo eje
    (eje='x' -> beam_y en Y=valor; eje='y' -> beam_x en X=valor)."""
    return seg_y.get((nivel_z, valor), []) if eje == 'x' \
        else seg_x.get((nivel_z, valor), [])


def tramos_receptores(seg_x, seg_y, nivel_z, eje, valor, min0, max0):
    """Segmentacion del contacto [min0,max0] (cm) por VIGA receptora, con
    particion SIN SOLAPES ni dobles conteos. Retorna (tramos, huecos):
      - tramos: lista de dicts {s, e, vid, section, Lviga} que PARTE [min0,max0]
                en intervalos disjuntos (una viga puede ocupar varios); los
                solapes entre vigas se recortan en favor de la de mayor alcance.
      - huecos: lista (a_cm, b_cm) de los intervalos SIN viga (pendientes).
    El perfil de 45 grados sobre estos intervalos sumado al perfil sobre los
    huecos reproduce EXACTAMENTE el area del borde (conservacion por tramos).
    """
    segs = []
    for c1, c2, idb, sec in lista_por_eje(seg_x, seg_y, nivel_z, eje, valor):
        ov = min(max0, c2) - max(min0, c1)
        if ov > SOLAPE_MIN_CM:
            segs.append((max(min0, c1), min(max0, c2), idb, sec,
                         (c2 - c1) / 100.0))
    if not segs:
        return [], [(min0, max0)]

    segs.sort(key=lambda s: (s[0], s[1]))

    # fusionar segmentos de UNA MISMA viga que se tocan o solapan
    merged = []
    for a, b, vid, sec, L in segs:
        if merged and merged[-1][2] == vid and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]), vid, sec, L)
        else:
            merged.append((a, b, vid, sec, L))

    # sweep: recortar solapes entre vigas, sin dejar huecos internos indebidos
    tramos = []
    last_e = min0
    for a, b, vid, sec, L in merged:
        s2 = max(a, last_e)
        e2 = max(b, last_e)
        if e2 > s2:
            tramos.append({'s': s2, 'e': e2, 'vid': vid,
                           'section': sec, 'Lviga': L})
            last_e = e2

    # huecos: complemento de los tramos dentro de [min0,max0]
    cur = min0
    gaps = []
    for t in tramos:
        if t['s'] - cur > SOLAPE_MIN_CM:
            gaps.append((cur, t['s']))
        cur = max(cur, t['e'])
    if max0 - cur > SOLAPE_MIN_CM:
        gaps.append((cur, max0))
    return tramos, gaps

def areas_tributarias(loza):
    """Areas tributarias (metodo 45 grados) de una losa rectangular Lx x Ly.
    Retorna dict: {'x_min': A, 'x_max': A, 'y_min': A, 'y_max': A} (m2),
    siendo x_* los bordes en X=cte (vigas beam_y) y y_* los bordes en Y=cte
    (vigas beam_x).

    Regla del metodo 45:
      - Los DOS bordes CORTOS reciben triangulos; cada uno area = min^2/4.
        (triangulo de base "min" y altura "min/2" trazado a 45 grados).
      - Los DOS bordes LARGOS reciben trapezoides; el area restante se reparte
        por simetria: (Lx*Ly - 2*triangulos)/2 en cada lado largo.
    Consecuencia de verificar contra el area total: para una losa 4x8 m,
    los bordes de 4 m reciben 4 m2 c/u y los de 8 m reciben 12 m2 c/u.
    """
    Lx, Ly = loza['Lx'] / 100.0, loza['Ly'] / 100.0   # m
    minimo = min(Lx, Ly)
    triangulo = minimo * minimo / 4.0          # cada borde CORTO
    trapecio = (Lx * Ly - 2.0 * triangulo) / 2.0   # cada borde LARGO

    # Bordes x_min/x_max tienen longitud Ly (bordes en X=cte).
    # Bordes y_min/y_max tienen longitud Lx (bordes en Y=cte).
    if Lx <= Ly:
        # X=cte (long Ly) son los LARGOS   -> trapecio
        # Y=cte (long Lx) son los CORTOS   -> triangulo
        return {'x_min': trapecio, 'x_max': trapecio,
                'y_min': triangulo, 'y_max': triangulo}
    else:
        # X=cte (long Ly) son los CORTOS   -> triangulo
        # Y=cte (long Lx) son los LARGOS   -> trapecio
        return {'x_min': triangulo, 'x_max': triangulo,
                'y_min': trapecio, 'y_max': trapecio}


def _perfil_45(Lm_m, h_m, A_total_m2, a_m, b_m):
    """Integral del perfil ANCHO TRIBUTARIO de 45 grados sobre el tramo [a,b].

    El perfil exacto del metodo 45 sobre un borde de longitud Lm de una losa
    rectangular (lado corto Lc, h = Lc/2) es, medido a lo largo del borde s:
        w(s) = s            si   s <  h            (rampa de entrada)
               h            si   h <= s <= Lm - h  (meseta central)
               Lm - s       si   s >  Lm - h       (rampa de salida)
    (En un borde CORTO, Lm == Lc, la meseta degenera a longitud 0: dos rampas
    que se unen en s = h; el area es el triangulo Lc^2/4.)
    El area total analitica es A45 = h*(Lm - h); el perfil se escala por
    A_total_m2 / A45 para conservar EXACTAMENTE el area del borde (asi, cuando
    los tramos cubren el borde completo, la SUMA coincide con areas_tributarias
    hasta precision de maquina; con huecos, el remanente queda en 'huecos').

    C(s) = integral_0^s w(u) du por tramos:
        s <= h           -> s^2/2
        h <= s <= Lm-h   -> h*s - h^2/2
        s >= Lm-h        -> h*(Lm-h) - (Lm-s)^2/2
    Retorna (integral_ab escalada, A45).
    """
    Lm = float(Lm_m)
    h = float(h_m)
    if Lm <= 0.0 or h <= 0.0:
        return 0.0, 0.0
    a45 = h * (Lm - h)
    if a45 <= 0.0:
        return 0.0, a45
    escala = A_total_m2 / a45

    def C(x):
        x = min(max(x, 0.0), Lm)
        if x <= h:
            return 0.5 * x * x
        if x <= Lm - h:
            return h * x - 0.5 * h * h
        return h * (Lm - h) - 0.5 * (Lm - x) * (Lm - x)

    return (C(b_m) - C(a_m)) * escala, a45


def area_por_tramo_45(loza, borde, min0_cm, max0_cm, A_total_m2):
    """Integra sobre un TRAMO [min0_cm,max0_cm] (cm) del borde el ANCHO
    tributario del metodo 45 grados y devuelve el area tributaria (m2) de ese
    tramo. Perfil punto a punto exacto de 45 grados (ver _perfil_45); en un
    borde sin huecos la SUMA de todos los tramos conserva A_total_m2.
    """
    lo = borde.split('_')[0]               # 'x' o 'y'
    Lx, Ly = loza['Lx'], loza['Ly']        # cm
    L0 = Ly if lo == 'x' else Lx           # longitud total del borde (cm)
    Lc = min(Lx, Ly)                       # lado corto (cm)
    if L0 <= 0:
        return 0.0
    Lm = L0 / 100.0
    h = (Lc / 100.0) / 2.0
    # perfil parametrizado sobre s in [0, Lm] medido desde el INICIO del borde;
    # re-baselinear el tramo (coordenadas absolutas en cm, pueden ser negativas)
    base_cm = loza['ymin'] if lo == 'x' else loza['xi']
    a = (max(min0_cm, base_cm) - base_cm) / 100.0
    b = (max(max0_cm, base_cm) - base_cm) / 100.0
    if a >= b:
        return 0.0
    At, _ = _perfil_45(Lm, h, A_total_m2, a, b)
    return At

def _transferir(contrato_path, nodos_map, extra_kn_m2=0.0,
                include_self_weight=True):
    """Nucleo de la transferencia por tramos (ver cargas_para_vigas).

    Retorna (cargas, huecos, aisladas):
      - cargas : dict viga_id -> {p, A, W, origen, aportes}
      - huecos : lista de dicts {loza, borde, hueco_cm, longitud_m, pendiente}
      - aisladas: lista de dicts {id, yi, motivo}
    """
    d = cargar_contrato(contrato_path)
    beams = [e for e in d['elements'] if e['type'] in ('beam_x', 'beam_y')]
    lozas = [normalizar_loza(e) for e in d['elements'] if e['type'] == 'loza']
    seg_x, seg_y = vigas_por_nivel(beams, nodos_map)

    cargas = {}          # viga_id -> acumulado
    vacios = []          # dicts de huecos con IDs (trazabilidad)
    aisladas = []        # losas sin NINGUN borde con viga (reportadas aparte)

    def add_aporte(vid, loza_id, borde, t, At, w):
        c = cargas.setdefault(vid, {'p': 0.0, 'A': 0.0, 'W': 0.0,
                                    'origen': [], 'aportes': []})
        Lv = t['Lviga']
        W = w * At
        p = W / Lv if Lv else 0.0
        c['p'] += p
        c['A'] += At                     # sin redondeo (conservacion ~1e-12)
        c['W'] += W
        c['origen'].append(loza_id)
        c['aportes'].append({            # trazabilidad: redondeado a 8 dec.
            'loza': loza_id,
            'borde': borde,
            'tramo': [round(t['s'], 1), round(t['e'], 1)],
            'unidades_tramo': 'cm',
            'vid': t['vid'],
            'area_m2': round(At, 8),
            'area_por_m2_kN_m2': round(w, 8),
            'W_kN': round(W, 8),
            'p_kN_m': round(p, 8),
        })

    for lz in lozas:
        res = piso_de(lz['yi'])
        if res is None:
            aisladas.append({'id': lz['id'], 'yi': lz['yi'],
                             'A_m2': (lz['Lx'] * lz['Ly']) / 10000.0,
                             'motivo': 'sin nivel reconocido'})
            continue
        nivel_z = res[1]
        w_pp = GAMMA_CONC * (lz['t'] / 100.0) if include_self_weight else 0.0
        w = w_pp + extra_kn_m2
        A_borde = areas_tributarias(lz)

        # Pares de bordes paralelos (para las reglas de borde libre).
        pares = {'y': ('y_min', 'y_max'), 'x': ('x_min', 'x_max')}
        opp = {'y_min': 'y_max', 'y_max': 'y_min',
               'x_min': 'x_max', 'x_max': 'x_min'}

        # (1) Localizar vigas reales por borde y segmentar en tramos receptores.
        ejes = {
            'y_min': ('y', lz['ymin'], lz['xi'], lz['xmax']),
            'y_max': ('y', lz['ymax'], lz['xi'], lz['xmax']),
            'x_min': ('x', lz['xi'], lz['ymin'], lz['ymax']),
            'x_max': ('x', lz['xmax'], lz['ymin'], lz['ymax']),
        }
        receptores = {}     # borde -> [tramos]
        huecos = {}
        tiene_viga = 0
        for borde, (eje, valor, m0, m1) in ejes.items():
            tramos, pend = tramos_receptores(seg_x, seg_y, nivel_z, eje,
                                             valor, m0, m1)
            if tramos:
                receptores[borde] = tramos
                tiene_viga += 1
            if pend:
                huecos[borde] = pend

        # Borde libre (sin viga) -> su area va al borde OPUESTO paralelo si
        # este tiene viga (voladizo, regla existente). Si AMBOS bordes de una
        # direccion estan libres, el area de ese par se reparte entre los 2
        # bordes de la OTRA direccion que SI tienen viga (losa 1-way). Las
        # losas sin NINGUNA viga en ningun borde quedan excluidas (aisladas).
        if tiene_viga == 0:
            aisladas.append({'id': lz['id'], 'yi': lz['yi'],
                             'A_m2': (lz['Lx'] * lz['Ly']) / 10000.0,
                             'motivo': 'sin viga en ningun borde'})
            continue

        # perfil base (45 grados) por tramo y por borde (sin EXTRA)
        base = {k: 0.0 for k in receptores}
        for k, tramos in receptores.items():
            acc = 0.0
            for t in tramos:
                ab = area_por_tramo_45(lz, k, t['s'], t['e'], A_borde[k])
                t['_At'] = ab
                t['_extra'] = 0.0
                acc += ab
            base[k] = acc

        # pasada 1: voladizo (borde libre -> borde OPUESTO paralelo con viga).
        # El area del borde libre se re-distribuye INTEGRA por los tramos del
        # receptor, proporcional a su perfil base.
        duplica = {}
        for k in ejes:
            if k not in receptores:
                o = opp[k]
                if o in receptores:
                    duplica[k] = o
        for src, dst in duplica.items():
            if base[dst]:
                for t in receptores[dst]:
                    t['_extra'] += A_borde[src] * (t['_At'] / base[dst])
            huecos.pop(src, None)

        # pasada 2: pares AMBOS-libres -> el area total del par se reparte en
        # los bordes de la OTRA direccion que tienen viga (losa 1-way),
        # proporcional al perfil base de sus tramos.
        for direc, (lo_k, hi_k) in pares.items():
            ot_dir = 'x' if direc == 'y' else 'y'
            ot_ks = pares[ot_dir]
            if lo_k not in receptores and hi_k not in receptores:
                real_ks = [k for k in ot_ks if k in receptores]
                if real_ks:
                    totb = sum(base[k] for k in real_ks)
                    extra_total = A_borde[lo_k] + A_borde[hi_k]
                    for k in real_ks:
                        if totb:
                            for t in receptores[k]:
                                t['_extra'] += (extra_total *
                                                (base[k] / totb) *
                                                (t['_At'] / base[k]))
                        else:
                            for i, t in enumerate(receptores[k]):
                                t['_extra'] += extra_total / len(receptores[k])
                    huecos.pop(lo_k, None)
                    huecos.pop(hi_k, None)

        # (2) Aplicar carga por borde a sus tramos.
        for borde, tramos in receptores.items():
            for t in tramos:
                At = t['_At'] + t['_extra']
                add_aporte(t['vid'], lz['id'], borde, t, At, w)

        # (3) Huecos de cobertura -> pendientes (no se compensan ni inventan).
        for borde, pend in huecos.items():
            A_bb = A_borde[borde]
            for (a, b) in pend:
                ah = area_por_tramo_45(lz, borde, a, b, A_bb)
                vacios.append({
                    'loza': lz['id'], 'borde': borde,
                    'hueco_cm': [a, b],
                    'longitud_m': round((b - a) / 100.0, 4),
                    'area_m2': ah,
                    'pendiente': 'cobertura parcial sin viga (definir regla)',
                })

    for vid, c in cargas.items():
        c['origen'] = sorted(set(c['origen']))
    return cargas, vacios, aisladas


def cargas_para_vigas(contrato_path, nodos_map, extra_kn_m2=0.0,
                      include_self_weight=True):
    """Calcula, para cada viga, la carga lineal total (kN/m) que recibe de las lozas
    (transferencia por tramos junto al metodo de 45 grados).

    Retorna dict: viga_id -> {'p': kN/m, 'A': m2, 'W': kN, 'origen': [lozas],
                               'aportes': [{loza,borde,tramo,vid,area,W,p,...}]}.
    Los huecos de cobertura y las losas aisladas se reportan por separado via
    `huecos_y_aisladas()` o el resumen de verificar_areas_tributarias().
    """
    cargas, _, _ = _transferir(contrato_path, nodos_map, extra_kn_m2,
                               include_self_weight)
    return cargas


def huecos_y_aisladas(contrato_path, nodos_map, extra_kn_m2=0.0,
                      include_self_weight=True):
    """Retorna (huecos, aisladas) de la transferencia por tramos: huecos de
    cobertura (borde parcial sin viga) y losas aisladas (sin viga en ningun
    borde), cada uno con IDs y geometria para trazabilidad."""
    cargas, huecos, aisladas = _transferir(contrato_path, nodos_map,
                                           extra_kn_m2, include_self_weight)
    return huecos, aisladas

def cargas_por_viga(cargas):
    """Devuelve la carga lineal neta de cada viga (SUMAndo sus lozas) como dict id->kN/m."""
    return {vid: c['p'] for vid, c in cargas.items()}

def verificar_areas_tributarias(contrato_path, nodos_map, extra_kn_m2=0.0,
                                include_self_weight=True):
    """Verificaciones del metodo de areas tributarias por tramos (edificio real).

    Retorna (ok, resumen) con:
      - A_lozas_total_m2    : SUMA de area de las losas SOPORTADAS (con >=1 viga)
      - A_trib_total_m2     : area tributaria transferida a las vigas
      - A_huecos_m2         : area de los huecos de cobertura (borde parcial sin
                              viga), reportados como pendientes (NO compensados)
      - A_lozas_aisladas_m2 : area de las losas sin viga en NINGUN borde
      - conservacion        : por tramos:  A_trib + A_huecos = A_lozas (tol 1e-10)
      - W_losas / W_vigas   : peso y carga transferida (conservacion rel)
      - huecos_pendientes   : lista con IDs, borde, tramo (cm), longitud (m),
                              area (m2) y motivo (pendiente de definicion)
      - aisladas            : lista con ID, yi y motivo
    """
    d = cargar_contrato(contrato_path)
    beams_elem = [e for e in d['elements'] if e['type'] in ('beam_x', 'beam_y')]
    lozas = [normalizar_loza(e) for e in d['elements'] if e['type'] == 'loza']
    seg_x, seg_y = vigas_por_nivel(beams_elem,
                                   {n['id']: n for n in d['nodes']})
    soportadas, aisladas = [], []
    for lz in lozas:
        res = piso_de(lz['yi'])
        if res is None:
            aisladas.append({'loza': lz, 'motivo': 'sin nivel reconocido'})
            continue
        z = res[1]
        n_vy = len(buscar_viga(seg_x, seg_y, z, 'y', lz['ymin'],
                               lz['xi'], lz['xmax'])) \
             + len(buscar_viga(seg_x, seg_y, z, 'y', lz['ymax'],
                               lz['xi'], lz['xmax']))
        n_vx = len(buscar_viga(seg_x, seg_y, z, 'x', lz['xi'],
                               lz['ymin'], lz['ymax'])) \
             + len(buscar_viga(seg_x, seg_y, z, 'x', lz['xmax'],
                               lz['ymin'], lz['ymax']))
        (soportadas if (n_vy + n_vx) > 0 else aisladas).append(
            {'loza': lz,
             'motivo': 'sin viga en ningun borde' if (n_vy + n_vx) == 0 else '--'})

    A_lozas = sum(lz['loza']['Lx'] * lz['loza']['Ly'] for lz in soportadas) / 10000.0
    W_losas = sum(((GAMMA_CONC * (lz['loza']['t'] / 100.0)
                    if include_self_weight else 0.0) + extra_kn_m2) *
                  (lz['loza']['Lx'] * lz['loza']['Ly'] / 10000.0)
                  for lz in soportadas)
    A_aisladas = sum(lz['loza']['Lx'] * lz['loza']['Ly']
                     for lz in aisladas) / 10000.0

    cargas, huecos, aisladas_t = _transferir(contrato_path, nodos_map,
                                             extra_kn_m2, include_self_weight)
    A_trib = sum(c['A'] for c in cargas.values())
    A_huecos = sum(h['area_m2'] for h in huecos)

    # peso de las losas por sus areas transitadas (incluye huecos, que no se
    # transfieren aun, y aisladas, fuera de la referencia)
    w_por_id = {}
    for lz in soportadas:
        wid = lz['loza']['id']
        w_por_id[wid] = ((GAMMA_CONC * (lz['loza']['t'] / 100.0)
                          if include_self_weight else 0.0) + extra_kn_m2)
    W_huecos = sum(w_por_id.get(h['loza'], 0.0) * h['area_m2'] for h in huecos)

    W_vigas = sum(c['W'] for c in cargas.values())
    W_transferible = W_losas - W_huecos

    cons_w_rel = (abs(W_vigas - W_transferible) / W_transferible
                  if W_transferible else 0.0)
    cons_a_rel = abs((A_trib + A_huecos) - A_lozas) / A_lozas if A_lozas else 0.0
    ok = cons_w_rel < 1e-10 and cons_a_rel < 1e-10
    return ok, {
        'A_lozas_total_m2': A_lozas, 'A_trib_total_m2': A_trib,
        'A_huecos_m2': A_huecos, 'A_lozas_aisladas_m2': A_aisladas,
        'W_losas_kN': W_losas, 'W_huecos_kN': W_huecos,
        'W_vigas_kN': W_vigas,
        'conservacion_rel_W': cons_w_rel, 'conservacion_rel_A': cons_a_rel,
        'n_vigas_cargadas': len(cargas),
        'huecos_pendientes': sorted(huecos, key=lambda h: h['loza']),
        'n_losas_aisladas': len(aisladas_t),
        'aisladas': sorted(aisladas_t, key=lambda a: a.get('id', 0)),
    }

if __name__ == '__main__':
    # Ruta relativa al repo (busca Edificio.json en la raiz del repo).
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo = base  # carpeta P1-Grupo-6
    json_path = os.path.join(repo, 'Edificio.json')
    if not os.path.exists(json_path):
        # por si se corre desde la raiz del repo
        json_path = os.path.join(os.getcwd(), 'Edificio.json')
    d = cargar_contrato(json_path)
    nid = {n['id']: n for n in d['nodes']}
    cargas = cargas_para_vigas(json_path, nid)
    netas = cargas_por_viga(cargas)
    if netas:
        import statistics
        print('vigas cargadas:', len(netas))
        print('rango de carga lineal: %.2f a %.2f kN/m' % (min(netas.values()), max(netas.values())))
    ok, res = verificar_areas_tributarias(json_path, nid)
    print('Area lozas (soportadas): %.2f m2' % res['A_lozas_total_m2'])
    print('Area tributaria (SUMA) : %.2f m2' % res['A_trib_total_m2'])
    print('Area huecos (pendientes): %.6f m2' % res['A_huecos_m2'])
    print('Area losas aisladas    : %.2f m2 (%d)' % (
        res['A_lozas_aisladas_m2'], res['n_losas_aisladas']))
    print('W lozas               : %.1f kN' % res['W_losas_kN'])
    print('W huecos (pendientes) : %.3f kN' % res['W_huecos_kN'])
    print('W vigas (transfer)    : %.1f kN' % res['W_vigas_kN'])
    print('Conservacion W   rel  : %.3e' % res['conservacion_rel_W'])
    print('Conservacion A   rel  : %.3e' % res['conservacion_rel_A'])
    print('Coherencia areas/conservacion: %s' % ('OK' if ok else 'NO'))
    huecos = res['huecos_pendientes']
    if huecos:
        print('Huecos por tramo (%d):' % len(huecos))
        for h in huecos:
            print('  loza %d borde %-5s [%s] cm  L=%.2f m  A=%.3f m2'
                  % (h['loza'], h['borde'],
                     ','.join(str(x) for x in h['hueco_cm']),
                     h['longitud_m'], h['area_m2']))
    aisl = res['aisladas']
    if aisl:
        print('Losas aisladas (%d):' % len(aisl))
        for a in aisl:
            print('  loza %s yi=%s (%s)' % (a.get('id', '?'),
                                          a.get('yi', '?'),
                                          a['motivo']))
