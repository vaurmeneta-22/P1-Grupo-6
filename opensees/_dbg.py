import re, json
src = open('../edificio_3d.html', encoding='utf-8').read()
i = src.find('const elements = ')
print(repr(src[i:i+200]))
print('---')
rest = src[i+len('const elements = '):]
j = rest.find('];')
print('len:', j)
print('tail:', repr(rest[j-120:j+30]))