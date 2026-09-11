import io, re
HTML = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\edificio_3d.html'
src = io.open(HTML, encoding='utf-8').read()
i = src.find('const elements = ')
# find the start of the NEXT 'const ' declaration after elements
rest = src[i:]
# skip past 'const elements' first few chars
m = re.search(r'\n\s*const\s+\w', rest[20:])
if m:
    boundary = i + 20 + m.start() + 1  # +1 for the \n
else:
    boundary = i + 20
print('boundary rel from i:', boundary - i)
print('context around boundary:', repr(src[boundary-30:boundary+50]))
# get the characters between 'const elements = ' and boundary
arr_region = src[i + len('const elements = '):boundary]
print('region starts:', repr(arr_region[:40]))
print('region ends:', repr(arr_region[-40:]))