import json

d = json.load(open('../Edificio.json', encoding='utf-8'))
coords = {n['id']: n for n in d['nodes']}
targets = {120, 121, 122, 126, 127, 128, 155, 156, 157, 158, 159, 160, 161, 162, 163}
rows = []
for e in d['elements']:
    if e['type'] in ('column', 'beam_x', 'beam_y') and (e['node_i'] in targets or e['node_j'] in targets):
        ci = coords[e['node_i']]
        cj = coords[e['node_j']]
        rows.append((e['id'], e['type'], e['section'],
                     str(e['node_i']) + '(z=' + str(int(ci['z'])) + ')',
                     str(e['node_j']) + '(z=' + str(int(cj['z'])) + ')'))
for r in sorted(rows):
    print(*r)