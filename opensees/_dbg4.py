import io
HTML = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\edificio_3d.html'
src = io.open(HTML, encoding='utf-8').read()
i = src.find('const elements = ')
after = src[i:]
# find where next 'const ' starts after the elements block
j = after.find('\nconst ', 10)  # skip past 'const elements'
if j < 0:
    j = after.find('\n\nconst ')
print('next const at rel:', j)
print('context:', repr(after[j-40:j+60]))
# the array text is between 'const elements = ' and that boundary
# it should start with '[' (from our _fix.py) 
print('starts with:', repr(after[len('const elements = '):len('const elements = ')+20]))