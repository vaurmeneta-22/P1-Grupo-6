src = open('../edificio_3d.html', encoding='utf-8').read()
i = src.find('const elements = [')
after = src[i:]  # starts with 'const elements = [...'
depth = 0
found = False
for idx, ch in enumerate(after):
    if ch == '[': depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0:
            end = idx + 1
            found = True
            break
print('found:', found, 'end rel:', end if found else '?')
if found:
    arr_text = after[len('const elements = '):end]  # includes the outer []
    print('len arr text chars:', len(arr_text))
    import json
    arr = json.loads(arr_text)
    print('n elements parsed:', len(arr))
    print('last:', json.dumps(arr[-1], ensure_ascii=False)[:180])
    print('first steel count:', sum(1 for x in arr if 'steel' in x.get('type','')))