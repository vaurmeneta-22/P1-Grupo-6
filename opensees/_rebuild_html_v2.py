# -*- coding: utf-8 -*-
import json, io

HTML = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\edificio_3d.html'
P = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\Edificio.json'

with open(P, encoding='utf-8') as f:
    data = json.load(f)
nodes_by_id = {n['id']: n for n in data['nodes']}

def to_html(e):
    t = e['type']
    if t in ('column', 'beam_x', 'beam_y', 'steel_column', 'steel_beam'):
        ni = nodes_by_id[e['node_i']]
        nj = nodes_by_id[e['node_j']]
        xi = round(ni['x'] / 100.0, 6)
        yi = round(ni['z'] / 100.0, 6)
        zi = round(ni['y'] / 100.0, 6)
        xj = round(nj['x'] / 100.0, 6)
        yj = round(nj['z'] / 100.0, 6)
        zj = round(nj['y'] / 100.0, 6)
        b = round(e['b'] / 100.0, 6)
        h = round(e['h'] / 100.0, 6)
        return {'type': t, 'section': e['section'],
                'xi': xi, 'yi': yi, 'zi': zi,
                'xj': xj, 'yj': yj, 'zj': zj, 'b': b, 'h': h}
    else:
        out = {'type': t, 'section': e['section']}
        for k in ('xi', 'yi', 'zi', 'xj', 'yj', 'zj'):
            out[k] = round(e[k] / 100.0, 6)
        out['b'] = round(e.get('b', 0) / 100.0, 6)
        out['h'] = round(e.get('h', 0) / 100.0, 6)
        if t == 'loza':
            out['t'] = round(e.get('t', 0.0) / 100.0, 6)
        return out

arr = [to_html(e) for e in data['elements']]
body_text = json.dumps(arr, ensure_ascii=False, separators=(',', ':'))

# Format like the original: inline first, then 2-space indent rest
lines = json.dumps(arr, ensure_ascii=False, indent=2).split('\n')
# Rebuild compact: first element inline, rest indented
compact = '  ' + json.dumps(arr[0], ensure_ascii=False, separators=(',', ':')) + ',\n'
compact += '\n'.join('  ' + json.dumps(x, ensure_ascii=False, separators=(',', ':')) + (',' if i < len(arr)-1 else '')
                     for i, x in enumerate(arr[1:]))

src = io.open(HTML, encoding='utf-8').read()

# Find start of the elements array
idx = src.find('const elements = ')
if idx < 0:
    raise SystemExit('const elements not found')
array_start = idx + len('const elements = ')

# Use raw_decode to find the proper end of the JSON array
decoder = json.JSONDecoder()
_, end_idx = decoder.raw_decode(src, array_start)

new_arr_text = '[' + compact + ']'
new_src = src[:array_start] + new_arr_text + src[end_idx:]
io.open(HTML, 'w', encoding='utf-8').write(new_src)

# Verify
src2 = io.open(HTML, encoding='utf-8').read()
idx2 = src2.find('const elements = ')
_, end2 = decoder.raw_decode(src2, idx2 + len('const elements = '))
check = json.loads(src2[idx2 + len('const elements = '):end2])
print(f'OK: {len(check)} elements, last id check skipped')
print('steel types:', sorted(set(x['type'] for x in check if 'steel' in x['type'])))
print('first:', json.dumps(check[0], ensure_ascii=False)[:120])
print('last:', json.dumps(check[-1], ensure_ascii=False)[:120])