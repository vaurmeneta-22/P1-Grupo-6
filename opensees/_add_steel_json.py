# -*- coding: utf-8 -*-
import json, shutil

P = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\Edificio.json'
with open(P, encoding='utf-8') as f:
    data = json.load(f)

steel_columns = [
    (703, '126', '161'), (704, '123', '158'), (705, '127', '162'),
    (706, '124', '159'), (707, '128', '163'), (708, '125', '160'),
]
steel_braces = [
    (709, '120', '158'), (710, '126', '158'), (711, '121', '159'),
    (712, '127', '159'), (713, '122', '160'), (714, '128', '160'),
]

new = []
for eid, ni, nj in steel_columns:
    new.append({
        'id': eid, 'type': 'steel_column', 'section': '300x300x20',
        'node_i': int(ni), 'node_j': int(nj),
        'b': 30.0, 'h': 30.0, 't': 2.0,
        'lift_cm': 0, 'ext_start_cm': 0, 'ext_end_cm': 0, 'ext_bot_cm': 0,
    })
for eid, ni, nj in steel_braces:
    new.append({
        'id': eid, 'type': 'steel_beam', 'section': '300x300x50',
        'node_i': int(ni), 'node_j': int(nj),
        'b': 30.0, 'h': 30.0, 't': 5.0,
        'lift_cm': 0, 'ext_start_cm': 0, 'ext_end_cm': 0, 'ext_bot_cm': 0,
    })

data['elements'].extend(new)

# secciones nuevas para el viewer/inspector
data['sections'].append({'name': '300x300x20', 'b': 30.0, 'h': 30.0})
data['sections'].append({'name': '300x300x50', 'b': 30.0, 'h': 30.0})

shutil.copyfile(P, P + '.bak2')
with open(P, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print('total elements:', len(data['elements']))
print('types:', sorted(set(e['type'] for e in data['elements'])))