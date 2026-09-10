# -*- coding: utf-8 -*-
# Regenera 'const elements = [...]' del viewer desde Edificio.json (mismo orden 1:1).
import json, re, io

REPO = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6'
HTML = REPO + r'\edificio_3d.html'
P = REPO + r'\Edificio.json'

with open(P, encoding='utf-8') as f:
    data = json.load(f)
nodes_by_id = {n['id']: n for n in data['nodes']}

def to_html(e):
    t = e['type']
    if t in ('column', 'beam_x', 'beam_y', 'steel_column', 'steel_beam'):
        ni = nodes_by_id[e['node_i']]
        nj = nodes_by_id[e['node_j']]
        xi = round(ni['x'] / 100.0, 6)
        yi = round(ni['z'] / 100.0, 6)   # altura
        zi = round(ni['y'] / 100.0, 6)
        xj = round(nj['x'] / 100.0, 6)
        yj = round(nj['z'] / 100.0, 6)
        zj = round(nj['y'] / 100.0, 6)
        b = round(e['b'] / 100.0, 6)
        h = round(e['h'] / 100.0, 6)
        return {'type': t, 'section': e['section'],
                'xi': xi, 'yi': yi, 'zi': zi,
                'xj': xj, 'yj': yj, 'zj': zj, 'b': b, 'h': h}
    else:  # wall / loza: coords directas (cm -> m), ya esta en el JSON
        out = {'type': t, 'section': e['section']}
        for k in ('xi', 'yi', 'zi', 'xj', 'yj', 'zj'):
            out[k] = round(e[k] / 100.0, 6)
        out['b'] = round(e.get('b', 0) / 100.0, 6)
        out['h'] = round(e.get('h', 0) / 100.0, 6)
        if t == 'loza':
            out['t'] = round(e.get('t', 0.0) / 100.0, 6)
        return out

arr = [to_html(e) for e in data['elements']]

# Generar texto con mismo estilo: un elemento por linea salvo la 1a
body = json.dumps(arr[0], ensure_ascii=False, separators=(',', ':')) + ',\n'
body += ',\n'.join('  ' + json.dumps(x, ensure_ascii=False, separators=(',', ':')) for x in arr[1:])

src = io.open(HTML, encoding='utf-8').read()
start = src.index('const elements = [')
head = src[:start]
rest = src[start:]
end_rel = rest.index('];')
tail = src[start + end_rel + 2:]

new = head + 'const elements = [' + body + '];\n' + tail
with io.open(HTML, 'w', encoding='utf-8') as f:
    f.write(new)
print('escritos', len(arr), 'elementos en el HTML')
print('tipos:', sorted(set(x['type'] for x in arr)))