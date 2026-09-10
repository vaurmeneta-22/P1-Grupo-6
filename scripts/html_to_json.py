# -*- coding: utf-8 -*-
"""
Convierte edificio_3d.html -> Edificio.json (contrato OpenSees <-> Unity).

- Nodos: del nodesData del HTML, pasados a cm (n.x, n.y=altura, n.z -> x,y,z).
- Columnas: node_i = nodo mas cercano a (xi,yi,zi), node_j = mas cercano a
  (xj,yj,zj). Unity/visualizar re-extienden +beam_h/2 en el tope de columna.
- Vigas beam_x: node_i/node_j = nodos mas cercanos en la misma linea (misma z
  y altura, x dentro del vano); ext_start_cm/ext_end_cm y lift_cm se derivan.
- Vigas beam_y: igual, misma x y altura, z dentro del vano.
- Lozas y muros: coordenadas directas en cm (sin node_i/node_j).
"""
import json
import os
import io
from collections import defaultdict

BASE = r'C:\Users\56990\Desktop\Universidad\8vo semestre\Metodos Computacionales\P1-Grupo-6'
html_path = os.path.join(BASE, 'edificio_3d.html')
out_path = os.path.join(BASE, 'Edificio.json')

with io.open(html_path, encoding='utf-8') as f:
    s = f.read()

ns = s.index('const nodesData = [')
ne = s.index('];', ns)
nodes_html = json.loads('[' + s[ns+len('const nodesData = ['):ne].strip().rstrip(',').rstrip() + ']')

ss = s.index('const supportsSet = new Set(')
se = s.index(')', ss)
supports_html = json.loads(s[ss+len('const supportsSet = new Set('):se])

es = s.index('const elements = [')
ee = s.index('];', es)
elements_html = json.loads('[' + s[es+len('const elements = ['):ee].strip().rstrip().rstrip(',') + ']')

# --- sections ---
sections, seen_sec = [], set()
for e in elements_html:
    if e['type'] in ('column', 'beam_x', 'beam_y'):
        name = e['section']
        if name not in seen_sec:
            seen_sec.add(name)
            sections.append({'name': name, 'b': round(e['b'] * 100, 2), 'h': round(e['h'] * 100, 2)})

floors = [
    {'name': 'Subterraneo', 'elevation_base': 0, 'elevation_top': 356, 'top_of_beam': 396},
    {'name': 'Piso 1', 'elevation_base': 356, 'elevation_top': 712, 'top_of_beam': 752},
    {'name': 'Piso 2', 'elevation_base': 712, 'elevation_top': 1068, 'top_of_beam': 1108},
    {'name': 'Piso 3', 'elevation_base': 1068, 'elevation_top': 1424, 'top_of_beam': 1464},
    {'name': 'Piso 4', 'elevation_base': 1424, 'elevation_top': 1780, 'top_of_beam': 1820},
]

def floor_of(h_cm):
    for fl in floors:
        if fl['elevation_base'] <= h_cm < fl['elevation_top']:
            return fl['name']
    return 'Piso 4' if h_cm >= 1780 else 'Subterraneo'

nodes_json = []
for n in nodes_html:
    nodes_json.append({
        'id': n['id'],
        'x': round(n['x'] * 100, 4),
        'y': round(n['z'] * 100, 4),
        'z': round(n['y'] * 100, 4),
        'floor': floor_of(round(n['y'] * 100, 2)),
    })

# indice auxiliar para buscar nodos de viga
# (por altura aproximada y eje fijo)
beams_cleaned = []

def dist3(a, b):
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2) ** 0.5

elements_json = []
eid = 1
skipped = []

for e in elements_html:
    t = e['type']
    if t in ('column', 'beam_x', 'beam_y'):
        if t == 'column':
            # misma (x,z), altura mas cercana
            cand_i = [n for n in nodes_json if abs(n['x'] - e['xi']*100) < 1e-6 and abs(n['y'] - e['zi']*100) < 1e-6]
            cand_j = [n for n in nodes_json if abs(n['x'] - e['xj']*100) < 1e-6 and abs(n['y'] - e['zj']*100) < 1e-6]
            def pick(cands, h):
                return min(cands, key=lambda n: abs(n['z'] - h))
            if not cand_i or not cand_j:
                skipped.append((eid, t, e['section'], 'columna sin nodo en (x,z)'))
                eid += 1
                continue
            ni = pick(cand_i, e['yi']*100)['id']
            nj = pick(cand_j, e['yj']*100)['id']
            # nodo_i: base; nodo_j: techo. Sin lift/ext (la extension del tope es
            # implicita en Unity con beam_h/2 = 0.4m para vigas 60x80).
            lift = 0
            ext_s = ext_e = ext_bot = 0
        else:
            axis = 'x' if t == 'beam_x' else 'z'
            # nodos candidatos: misma altura de extremo, eje transversal fijo,
            # y coordenada de avance dentro del vano.
            if axis == 'x':
                fij_y = e['yi'] * 100  # altura
                fij_z = e['zi'] * 100  # eje transversal
                lo, hi = sorted([e['xi'] * 100, e['xj'] * 100])
                cands = [n for n in nodes_json if abs(n['z'] - fij_y) < 25.0
                         and abs(n['y'] - fij_z) < 1e-4 and lo - 1e-3 <= n['x'] <= hi + 1e-3]
                ni = min(cands, key=lambda n: abs(n['x'] - e['xi'] * 100)) if cands else None
                nj = min(cands, key=lambda n: abs(n['x'] - e['xj'] * 100)) if cands else None
            else:
                fij_y = e['yi'] * 100
                fij_x = e['xi'] * 100
                lo, hi = sorted([e['zi'] * 100, e['zj'] * 100])
                cands = [n for n in nodes_json if abs(n['z'] - fij_y) < 25.0
                         and abs(n['x'] - fij_x) < 1e-4 and lo - 1e-3 <= n['y'] <= hi + 1e-3]
                ni = min(cands, key=lambda n: abs(n['y'] - e['zi'] * 100)) if cands else None
                nj = min(cands, key=lambda n: abs(n['y'] - e['zj'] * 100)) if cands else None
            if ni is None or nj is None:
                skipped.append((eid, t, e['section'], 'viga sin nodo en el vano'))
                eid += 1
                continue
            nni, nnj = ni, nj
            lift = round(e['yi'] * 100 - nni['z'], 2)
            if axis == 'x':
                ext_s = round(e['xi'] * 100 - nni['x'], 2)
                ext_e = round(e['xj'] * 100 - nnj['x'], 2)
            else:
                ext_s = round(e['zi'] * 100 - nni['y'], 2)
                ext_e = round(e['zj'] * 100 - nnj['y'], 2)
            ni, nj = nni['id'], nnj['id']
            ext_bot = 0

        elements_json.append({
            'id': eid,
            'type': t,
            'section': e['section'],
            'node_i': ni,
            'node_j': nj,
            'b': round(e['b'] * 100, 2),
            'h': round(e['h'] * 100, 2),
            'lift_cm': lift,
            'ext_start_cm': ext_s,
            'ext_end_cm': ext_e,
            'ext_bot_cm': ext_bot,
        })
    else:
        out = {
            'id': eid,
            'type': t,
            'section': e['section'],
            'b': round(e.get('b', 0) * 100, 2),
            'h': round(e.get('h', 0) * 100, 2),
            'xi': round(e['xi'] * 100, 4),
            'yi': round(e['yi'] * 100, 4),
            'zi': round(e['zi'] * 100, 4),
            'xj': round(e['xj'] * 100, 4),
            'yj': round(e['yj'] * 100, 4),
            'zj': round(e['zj'] * 100, 4),
        }
        if t == 'loza':
            out['t'] = round(e['t'] * 100, 2)
        if t in ('steel_column', 'steel_beam'):
            # Acero: igual que columnas, nodo mas cercano a cada extremo.
            co_i = (e['xi']*100, e['zi']*100, e['yi']*100)
            co_j = (e['xj']*100, e['zj']*100, e['yj']*100)
            def pick(cands, co):
                return min(cands, key=lambda n: dist3((n['x'], n['y'], n['z']), co))
            ni = pick(nodes_json, co_i)['id']
            nj = pick(nodes_json, co_j)['id']
            max_d = max(dist3((nn['x'], nn['y'], nn['z']), co)
                        for nn, co in ((next(n for n in nodes_json if n['id']==ni), co_i),
                                       (next(n for n in nodes_json if n['id']==nj), co_j)))
            out['node_i'] = ni
            out['node_j'] = nj
            out['t'] = round(float(str(e['section']).split('x')[2]), 4)  # mm del tubo
        elements_json.append(out)
    eid += 1

supports_json = [{'node': int(i), 'DOF': [1, 1, 1, 1, 1, 1], 'type': 'fixed'} for i in sorted(supports_html)]

data = {
    'model': {
        'description': 'Edificio completo (actualizado desde edificio_3d.html)',
        'ndm': 3, 'ndf': 6,
        'units': {'length': 'cm', 'force': 'kN', 'moment': 'kN*m'},
    },
    'sections': sections,
    'floors': floors,
    'nodes': nodes_json,
    'elements': elements_json,
    'supports': supports_json,
}

# backup del json actual
bak = out_path + '.bak'
if os.path.exists(out_path):
    if os.path.exists(bak):
        os.remove(bak)
    os.rename(out_path, bak)

with io.open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print('nodos:', len(nodes_json), '| elementos:', len(elements_json))
by_t = {}
for e in elements_json:
    by_t[e['type']] = by_t.get(e['type'], 0) + 1
print('por tipo:', by_t)
if skipped:
    print('WARNING omitidos:')
    for k in skipped:
        print('  ', k)
else:
    print('OK: todos los elementos resueltos')