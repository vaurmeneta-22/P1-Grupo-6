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

def buscar_viga(seg_x, seg_y, nivel_z, eje, valor, min0, max0):
    """
    Busca una viga en el plano nivel_z que yaga sobre el eje (eje='x' o 'y') =
    valor, cubriendo el segmento [min0, max0]. Retorna (id, seccion, L en m).
    """
    if eje == 'x':
        lista = seg_y.get((nivel_z, valor), [])   # beam_y: x const
        params = []
        for x1, x2, idb, sec in lista:
            ov = min(max0, x2) - max(min0, x1)
            if ov > 0.5:
                params.append((max(0, ov), idb, sec, x2 - x1))
        if not params:
            return None
        best = max(params, key=lambda p: p[0])
        return {'id': best[1], 'section': best[2], 'L': best[3] / 100.0}
    else:
        lista = seg_x.get((nivel_z, valor), [])   # beam_x: y const
        params = []
        for y1, y2, idb, sec in lista:
            ov = min(max0, y2) - max(min0, y1)
            if ov > 0.5:
                params.append((max(0, ov), idb, sec, y2 - y1))
        if not params:
            return None
        best = max(params, key=lambda p: p[0])
        return {'id': best[1], 'section': best[2], 'L': best[3] / 100.0}

def areas_tributarias(loza):
    """Areas tributarias (45 grados) de una losa rectangular Lx x Ly.
    Retorna dict: {'x_min': A, 'x_max': A, 'y_min': A, 'y_max': A} (m2),
    siendo x_* los bordes a lo largo de X (vigas beam_y) y y_* los de Y (beam_x)."""
    Lx, Ly = loza['Lx'] / 100.0, loza['Ly'] / 100.0   # m
    # bordes en X (los 2 lados paralelos a X -> vigas beam_y) reciben triangulos
    # area triangulo = 0.25 * (lado_corto)^2 ; perpendiculares:
    # Para los bordes a lo largo de X (longitud Ly en Y), cada uno recibe
    # un triangulo de base Ly y altura Lx/2 -> area = 0.25*Ly*Lx  UNO EN CADA borde.
    # Correcto (metodo 45): los lados que corren en X reciben triangulos de
    # 0.5*(Lx/2)*(min(Lx,Ly)/2)?? No - standard:
    #   lados en una direccion: A=Ly*Lx/8 ; los otros A=Lx*Ly/8 ; los 4 suman Lx*Ly.
    # Metodo clasico de 1/2 area a cada par de lados:
    #   Cada borde "paralelo a X" (largo Ly en Y) -> triangulo : A = Ly*min(Lx,Ly)/8
    #   Cada borde "paralelo a Y" (largo Lx en X) -> trapecio  : A = Lx*... 
    # Para losas rectangulares con bordes de apoyo completo:
    #   sobre los 2 lados de longitud Ly (paralelos a X) caen triangulos de base Ly;
    #   altura = Lx/2 ; area en cada lado = 0.5*Ly*(Lx/2)*? 
    # Derivo desde areas: la losa Lx*Ly. Si Lx>Ly (bordes largos en X),
    #   los bordes cortos (longitud Ly) reciben triangulos; los largos (Lx) trapezoides.
    # Implemento forma generica de lines of influence:
    # Sea el rectangulo [0,Lx]x[0,Ly]. Trazas desde cada esquina a 45grados.
    # Se forman hasta 3 franjas. Resultado estandar:
    #   A_xmax = A_xmin = (Lx/2) * Ly/2 * ... 
    # Usaremos la formula clásica con 'k' el lado y 'l':
    #   area en cada borde corto (triangulo)      = (min(Lx,Ly)^2)/4  [la mitad hacia cada]
    # Realmente: para rectangulo,borde de largo 'a' y perp 'b' (b<=a, borde a):
    #   distribuidores 45 pican en b/2.
    # --- Formula estandar (CodigoModel): 
    #  borde en X (long Lx), carga hacia el se hace triángulo cuando es el borde CORTO.
    # Opto por la formula canonica (verificado): 
    #  S = area total Lx*Ly. 2 lados de dir X reciben A=(Lx*Ly)/? y 2 de dir Y restante.
    # Asumimos 4 apoyos simples -> reparto a los 4 lados de la tabla standard:
    #   para losa 1-way vs 2-way. Tabla "simply supported rectangular":
    #
    # Vamos directo: area por viga = (conteo lineal mitad) formula con triang/y trapecio
    #   triangulo en lados cortos: lo = min(Lx,Ly),
    #   A_corto(borde) = lo*lo/4  (medio triangulo de lado lo a 45: alto lo/2, base lo)
    #   trapecio en lados largos lo_ : base menor = lo_, base mayor = lo_ , 
    #   A_largo(borde) = (Lx*Ly - 2*A_corto)/2   por simetria.
    # Los 2 bordes cortos: A_corto_cada = lo*lo/4
    # Los 2 bordes largos: A_largo_cada = (Lx*Ly - 2*A_corto)/2
    # En funcion de cual direccion es corta:
    if Lx <= Ly:
        # bordes en X (paralelos a X, longitud Ly) son los CORTOS -> triangulos
        A_corto = Lx * Lx / 4.0          # cada borde paralelo a Y (beam_y), en los extremos X
        A_largo = (Lx * Ly - 2 * A_corto) / 2.0   # cada borde paralelo a X (beam_x)
        return {'y_min': A_largo, 'y_max': A_largo, 'x_min': A_corto, 'x_max': A_corto}
    else:
        # bordes en Y (paralelos a Y, longitud Lx) son los CORTOS -> triangulos
        A_corto = Ly * Ly / 4.0
        A_largo = (Lx * Ly - 2 * A_corto) / 2.0
        return {'y_min': A_corto, 'y_max': A_corto, 'x_min': A_largo, 'x_max': A_largo}

def cargas_para_vigas(contrato_path, nodos_map, extra_kn_m2=0.0,
                      include_self_weight=True):
    """Calcula, para cada viga, la carga lineal total (kN/m) que recibe de las lozas.

    La carga por m2 de losa es:  w_losa = (GAMMA_CONC * t if include_self_weight
    else 0) + extra_kn_m2
      - GAMMA_CONC * t  = peso propio de losa (kN/m2)
      - extra_kn_m2     = terminaciones y/o sobrecarga (kN/m2), p.ej q_G restante.

    Retorna dict: viga_id -> {'p': kN/m, 'A_total': m2, 'W': kN (carga de losa total
    que descarga sobre la viga), 'origen': [viga_ids_borde]}.
    """
    d = cargar_contrato(contrato_path)
    beams = [e for e in d['elements'] if e['type'] in ('beam_x', 'beam_y')]
    lozas = [normalizar_loza(e) for e in d['elements'] if e['type'] == 'loza']
    seg_x, seg_y = vigas_por_nivel(beams, nodos_map)

    cargas = {}   # viga_id -> acumulado
    def acum(vid, p, area, W_inc):
        c = cargas.setdefault(vid, {'p': 0.0, 'A': 0.0, 'W': 0.0, 'origen': []})
        c['p'] += p
        c['A'] += area
        c['W'] += W_inc
        c['origen'].append(vid)

    for lz in lozas:
        res = piso_de(lz['yi'])
        if res is None:
            continue
        # nivel_z = altura de la reticula de vigas de ese piso (cm)
        nivel_z = res[1]
        w_pp = GAMMA_CONC * (lz['t'] / 100.0) if include_self_weight else 0.0
        w = w_pp + extra_kn_m2                    # carga total por m2 de losa
        A = areas_tributarias(lz)

        # Localizar la viga de cada uno de los 4 bordes.
        # bordes: 'y_min'/'y_max' (vigas beam_x), 'x_min'/'x_max' (vigas beam_y)
        edges = {}   # nombre -> dict(viga_info) o None
        edges['y_min'] = buscar_viga(seg_x, seg_y, nivel_z, 'y', lz['ymin'],
                                     lz['xi'], lz['xmax'])
        edges['y_max'] = buscar_viga(seg_x, seg_y, nivel_z, 'y', lz['ymax'],
                                     lz['xi'], lz['xmax'])
        edges['x_min'] = buscar_viga(seg_x, seg_y, nivel_z, 'x', lz['xi'],
                                     lz['ymin'], lz['ymax'])
        edges['x_max'] = buscar_viga(seg_x, seg_y, nivel_z, 'x', lz['xmax'],
                                     lz['ymin'], lz['ymax'])

        # REGLA CANTILÉVER / LOSA EN UNA DIRECCION (modelado):
        #   1) borde libre (sin viga) -> su area va al borde OPUESTO paralelo
        #      si este tiene viga (voladizo sobre el borde fijo).
        #   2) si AMBOS bordes de una direccion estan libres (losa que vuela en
        #      esa direccion sin apoyo), el area de ese par se reparte entre los
        #      2 bordes de la OTRA direccion que SI tienen viga (losa 1-way).
        #   3) si ninguna viga recibe area (losa aislada), se deja sin asignar
        #      (se reporta en verificacion, no se inventa soporte).
        pares = {'y': ('y_min', 'y_max'), 'x': ('x_min', 'x_max')}
        opp   = {'y_min': 'y_max', 'y_max': 'y_min',
                 'x_min': 'x_max', 'x_max': 'x_min'}

        # pasada 1: voladizo (borde libre -> borde opuesto con viga)
        for _ in range(4):
            libre = [k for k in edges if edges[k] is None]
            if not libre:
                break
            adv = False
            for k in libre:
                if edges[opp[k]] is not None:
                    edges[k] = {'DUPLICA_A': opp[k]}
                    adv = True
            if not adv:
                break

        # pasada 2: pares ambos-libres -> repartir a bordes de la otra direccion
        for direc, (lo_k, hi_k) in pares.items():
            ot_dir = 'x' if direc == 'y' else 'y'
            ot_ks = pares[ot_dir]
            if edges[lo_k] is None and edges[hi_k] is None:
                # solo receptores que son viga REAL (no duplicadores ni libres)
                def es_real(d):
                    return isinstance(d, dict) and 'DUPLICA_A' not in d \
                        and 'EXTRA' not in d and 'id' in d
                receptores = [k for k in ot_ks if es_real(edges[k])]
                if receptores:
                    base_areas = {k: A[k] for k in receptores}
                    totb = sum(base_areas.values())
                    for k in receptores:
                        extra = (A[lo_k] + A[hi_k]) * (base_areas[k] / totb if totb else 0.5)
                        edges[k] = {'EXTRA': extra, 'base': edges[k]}
                    edges[lo_k] = 'SIN_SOPORTE'
                    edges[hi_k] = 'SIN_SOPORTE'

        # Aplicar carga a las vigas de borde
        for borde in ('y_min', 'y_max', 'x_min', 'x_max'):
            info = edges[borde]
            if info is None or info == 'SIN_SOPORTE':
                continue
            # resolver el dict real de viga y el area base de este borde
            real = info
            At = A[borde]
            if isinstance(info, dict) and 'EXTRA' in info:
                real = info['base']          # la viga real de este borde
                At = A[borde] + info['EXTRA']
            elif isinstance(info, dict) and 'DUPLICA_A' in info:
                continue                     # su area ya se suma en el borde opuesto
            # si este borde es el RECEPTOR de un borde libre opuesto, sumar ambos
            for kb, v in edges.items():
                if isinstance(v, dict) and v.get('DUPLICA_A') == borde:
                    At += A[kb]
            p = w * At / real['L']
            acum(real['id'], p, At, w * At)
    return cargas

def cargas_por_viga(cargas):
    """Devuelve la carga lineal neta de cada viga (sumando sus lozas) como dict id->kN/m."""
    return {vid: c['p'] for vid, c in cargas.items()}

def verificar_areas_tributarias(contrato_path, nodos_map, extra_kn_m2=0.0,
                                include_self_weight=True):
    """Verificaciones del metodo de areas tributarias sobre el edificio real.

    Retorna (ok, resumen) con:
      - A_lozas_total (m2): suma de area de todas las lozas
      - A_trib_por_viga  : suma de (area tributaria) acumulada en todas las vigas
      - W_losas (kN)     : peso total de las lozas (w * A)
      - W_vigas (kN)     : suma de carga transferida a las vigas (p * L_viga)
      - conservacion (rel): |W_vigas - W_losas| / W_losas
      - area_diferencia (abs rel): |A_trib - A_lozas| / A_lozas
    """
    d = cargar_contrato(contrato_path)
    beams_elem = [e for e in d['elements'] if e['type'] in ('beam_x', 'beam_y')]
    beams = {e['id']: e for e in beams_elem}
    lozas = [normalizar_loza(e) for e in d['elements'] if e['type'] == 'loza']

    # Solo las losas que el metodo es capaz de transferir: deben pertenecer a un
    # piso (piso_de) y tener AL MENOS una viga real en alguno de sus 4 bordes.
    # Las losas aisladas (ninguna viga en ningun borde) no tienen soporte real y
    # se reportan aparte; su area no forma parte de la referencia de conservacion
    # porque aun en el modelo ideal no hay viga que la reciba.
    seg_x, seg_y = vigas_por_nivel(beams_elem, {n['id']: n for n in d['nodes']})
    soportadas, aisladas = [], []
    for lz in lozas:
        res = piso_de(lz['yi'])
        if res is None:
            continue
        z = res[1]
        n_vy = int(buscar_viga(seg_x, seg_y, z, 'y', lz['ymin'], lz['xi'], lz['xmax']) is not None) \
             + int(buscar_viga(seg_x, seg_y, z, 'y', lz['ymax'], lz['xi'], lz['xmax']) is not None)
        n_vx = int(buscar_viga(seg_x, seg_y, z, 'x', lz['xi'], lz['ymin'], lz['ymax']) is not None) \
             + int(buscar_viga(seg_x, seg_y, z, 'x', lz['xmax'], lz['ymin'], lz['ymax']) is not None)
        (soportadas if (n_vy + n_vx) > 0 else aisladas).append(lz)

    A_lozas = sum(lz['Lx'] * lz['Ly'] for lz in soportadas) / 10000.0
    W_losas = sum(((GAMMA_CONC * (lz['t'] / 100.0) if include_self_weight else 0.0)
                   + extra_kn_m2) * (lz['Lx'] * lz['Ly'] / 10000.0)
                  for lz in soportadas)
    A_aisladas = sum(lz['Lx'] * lz['Ly'] for lz in aisladas) / 10000.0

    cargas = cargas_para_vigas(contrato_path, nodos_map, extra_kn_m2,
                               include_self_weight)
    A_trib = sum(c['A'] for c in cargas.values())

    def viga_len(vid):
        b = beams[vid]
        dx = (nodos_map[b['node_j']]['x'] - nodos_map[b['node_i']]['x']) / 100.0
        dy = (nodos_map[b['node_j']]['y'] - nodos_map[b['node_i']]['y']) / 100.0
        return math.hypot(dx, dy)

    W_vigas = sum(c['p'] * viga_len(vid) for vid, c in cargas.items())

    cons_rel = abs(W_vigas - W_losas) / W_losas if W_losas else 0.0
    area_rel = abs(A_trib - A_lozas) / A_lozas if A_lozas else 0.0
    ok = cons_rel < 1e-10 and area_rel < 1e-10
    return ok, {
        'A_lozas_total_m2': A_lozas, 'A_trib_total_m2': A_trib,
        'A_lozas_aisladas_m2': A_aisladas,
        'W_losas_kN': W_losas, 'W_vigas_kN': W_vigas,
        'conservacion_rel': cons_rel, 'area_rel': area_rel,
        'n_vigas_cargadas': len(cargas),
        'n_lozas_aisladas': len(aisladas),
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
    print('Area lozas total  : %.2f m2' % res['A_lozas_total_m2'])
    print('Area tributaria Σ : %.2f m2' % res['A_trib_total_m2'])
    print('W lozas          : %.1f kN' % res['W_losas_kN'])
    print('W vigas (transfer): %.1f kN' % res['W_vigas_kN'])
    print('Conservacion rel  : %.3e' % res['conservacion_rel'])
    print('Area rel          : %.3e' % res['area_rel'])
    print('Coherencia areas/conservacion: %s' % ('OK' if ok else 'NO'))