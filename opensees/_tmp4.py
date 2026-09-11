import json

d = json.load(open('../Edificio.json', encoding='utf-8'))
coords = {n['id']: n for n in d['nodes']}
for nid in sorted({120, 121, 122, 126, 127, 128, 123, 124, 125,
                   158, 159, 160, 161, 162, 163}):
    n = coords.get(nid)
    f = {k: n[k] for k in ('x', 'y', 'z')} if n else None
    print(nid, f)