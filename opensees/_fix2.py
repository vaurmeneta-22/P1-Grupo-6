import io
HTML = r'C:\Users\56990\Desktop\Universidad\8vo Semestre\Metodos Computacionales\P1-Grupo-6\edificio_3d.html'
src = io.open(HTML, encoding='utf-8').read()
i = src.find('const elements = ')
prefix = src[:i + len('const elements = ')]
rest = src[i + len('const elements = '):]
# rest = [{...first},{...last};\n\n  const nodesData = [...]
# The array part ends before ';', so find ';\n\n  const nodesData'
fix_pos = rest.find('};\n\n  const nodesData')
if fix_pos < 0:
    # try other patterns
    fix_pos = rest.find('};\nconst nodesData')
print('fix_pos:', fix_pos)
if fix_pos >= 0:
    arr_part = rest[:fix_pos + 1]  # includes the closing '}'
    after = rest[fix_pos:]  # starts with '};\n...'
    new = prefix + arr_part + ']' + after
    io.open(HTML, 'w', encoding='utf-8').write(new)
    print('fixed: inserted ] before ;')
    # verify
    import json
    src2 = io.open(HTML, encoding='utf-8').read()
    i2 = src2.find('const elements = ')
    arr_start = i2 + len('const elements = ')
    decoder = json.JSONDecoder()
    arr_obj, end_idx = decoder.raw_decode(src2, arr_start)
    print('parsed elements count:', len(arr_obj))
    print('after elements:', repr(src2[end_idx:end_idx+40]))
