import io
p = '../edificio_3d.html'
src = io.open(p, encoding='utf-8').read()
src = src.replace('const elements = {"type"', 'const elements = [{"type"', 1)
io.open(p, 'w', encoding='utf-8').write(src)
print('fixed ok')