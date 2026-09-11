import json

d = json.load(open('../Edificio.json', encoding='utf-8'))
for e in d['elements']:
    ni, nj = e.get('node_i'), e.get('node_j')
    if ni in (123, 124, 125) or nj in (123, 124, 125):
        print(e['id'], e['type'], e['section'], ni, nj, e.get('b'), e.get('h'))