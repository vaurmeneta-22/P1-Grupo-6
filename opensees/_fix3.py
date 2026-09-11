import json, io

HTML = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\edificio_3d.html'
src = io.open(HTML, encoding='utf-8').read()
i = src.find('const elements = ')
arr_start = i + len('const elements = ')
decoder = json.JSONDecoder()
arr_obj, end_idx = decoder.raw_decode(src, arr_start)
# end_idx is right after the ']'
remaining = src[end_idx:]
print('remaining starts:', repr(remaining[:60]))
# If it starts with '};' that's junk. Remove it.
if remaining.startswith('};'):
    remaining = remaining[1:]  # remove the extra '}'
    print('removed extra }')
new_src = src[:end_idx] + remaining
io.open(HTML, 'w', encoding='utf-8').write(new_src)
# final verify
src2 = io.open(HTML, encoding='utf-8').read()
i2 = src2.find('const elements = ')
arr2, end2 = decoder.raw_decode(src2, i2 + len('const elements = '))
print('final count:', len(arr2))
print('after:', repr(src2[end2:end2+60]))