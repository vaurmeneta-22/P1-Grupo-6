import re

src = open('opensees_edificio_v2.py', encoding='utf-8').read()
lines = src.splitlines()
pat = re.compile(r'col_tops|\["type"\] in|in \("column"|t == "|t in \(|indices|is_col|vertical_support|CASE_COLUMN|CASE_BEAM')
for i, ln in enumerate(lines):
    if pat.search(ln):
        print(i + 1, ln.rstrip()[:150])