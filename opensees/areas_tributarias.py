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

GAMMA_CONC = 25.0  # kN/m3

# Niveles de losa (yi, cm) -> piso; y nivel de nodo/viga de su reticula (z, cm)
# Determinado empiricamente: losa 388.5 -> nodos 356 ; 744.5 -> 712 ; etc.
PISO_ALTURAS = {
    388.5: ('Piso 1', 356.0),
    744.5: ('Piso 2', 712.0),
    1100.5: ('Piso 3', 1068.0),
    1456.5: ('Piso 4', 1424.0),
    1812.5: ('Techo', 1780.0),
}

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

def cargas_para_vigas(contrato_path, nodos_map):
    """Calcula, para cada viga, la carga lineal total (kN/m) que recibe de las lozas.
    Retorna dict: viga_id -> {'p': kN/m, 'A_total': m2, 'origen': [loza_ids]}."""
    d = cargar_contrato(contrato_path)
    beams = [e for e in d['elements'] if e['type'] in ('beam_x', 'beam_y')]
    lozas = [normalizar_loza(e) for e in d['elements'] if e['type'] == 'loza']
    seg_x, seg_y = vigas_por_nivel(beams, nodos_map)

    cargas = {}   # viga_id -> acumulado
    def acum(vid, p, area):
        c = cargas.setdefault(vid, {'p': 0.0, 'A': 0.0, 'origen': []})
        c['p'] += p
        c['A'] += area
        c['origen'].append(vid)

    for lz in lozas:
        if lz['yi'] not in PISO_ALTURAS:
            continue
        nivel_z = PISO_ALTURAS[lz['yi']][1]
        w = GAMMA_CONC * (lz['t'] / 100.0)     # kN/m2
        A = areas_tributarias(lz)
        # buscar 4 bordes:
        #   borde ymin (y=ymin, se extiende en X de xmin..xmax) -> viga beam_x en y=ymin
        be = buscar_viga(seg_x, seg_y, nivel_z, 'y', lz['ymin'], lz['xi'], lz['xmax'])
        if be:
            p = w * A['y_min'] / be['L']
            acum(be['id'], p, A['y_min'])
        be = buscar_viga(seg_x, seg_y, nivel_z, 'y', lz['ymax'], lz['xi'], lz['xmax'])
        if be:
            p = w * A['y_max'] / be['L']
            acum(be['id'], p, A['y_max'])
        be = buscar_viga(seg_x, seg_y, nivel_z, 'x', lz['xi'], lz['ymin'], lz['ymax'])
        if be:
            p = w * A['x_min'] / be['L']
            acum(be['id'], p, A['x_min'])
        be = buscar_viga(seg_x, seg_y, nivel_z, 'x', lz['xmax'], lz['ymin'], lz['ymax'])
        if be:
            p = w * A['x_max'] / be['L']
            acum(be['id'], p, A['x_max'])
    return cargas

def cargas_por_viga(cargas):
    """Devuelve la carga lineal neta de cada viga (sumando sus lozas) como dict id->kN/m."""
    return {vid: c['p'] for vid, c in cargas.items()}

if __name__ == '__main__':
    repo = r'C:\Users\antoe\OneDrive\Antonia Espinoza Rubio\Universidad\Semestre 8\Métodos computacionales en Obras Civiles\P1\P1-Grupo-6'
    d = cargar_contrato(os.path.join(repo, 'Edificio.json'))
    nid = {n['id']: n for n in d['nodes']}
    cargas = cargas_para_vigas(os.path.join(repo, 'Edificio.json'), nid)
    netas = cargas_por_viga(cargas)
    import statistics
    print('vigas cargadas:', len(netas))
    print('rango de carga lineal: %.2f a %.2f kN/m' % (min(netas.values()), max(netas.values())))
    # peso total transferido = sum(p*viga_L); verificacion vs peso de todas las lozas
    beams = {e['id']: e for e in d['elements'] if e['type'] in ('beam_x','beam_y')}
    total = sum(p * (math.hypot(*( (
        nid[beams[vid]['node_j']]['x']-nid[beams[vid]['node_i']]['x'],
        nid[beams[vid]['node_j']]['y']-nid[beams[vid]['node_i']]['y']))) /100.0) for vid,p in netas.items())
    ws_losas = sum(GAMMA_CONC*(lz['t']/100.0) * ((lz['xmax']-lz['xi'])/100.0)*((lz['ymax']-lz['ymin'])/100.0)
                   for lz in (normalizar_loza(e) for e in d['elements'] if e['type']=='loza'))
    print('Peso total transferido a vigas: %.1f kN' % total)
    print('Peso total de lozas (real):     %.1f kN' % ws_losas)
    print('Cobertura: %.1f%%' % (100.0*total/ws_losas))