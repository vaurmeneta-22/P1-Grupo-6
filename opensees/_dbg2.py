src = open('../edificio_3d.html', encoding='utf-8').read()
# find const elements = [
i = src.find('const elements = [')
# find matching ]; - but need to handle nested brackets; simple approach: find first ]; after i
after = src[i:]
# count brackets
depth = 0
end = -1
for idx, ch in enumerate(after):
    if ch == '[':
        depth += 1
    elif ch == ']':
        depth -= 1
        if depth == 0:
            end = idx + 1
            break
print('array start char:', i)
print('array end char (incl]):', i+end)
print('len array text:', end)
# show around end
print('...tail snippet:')
print(repr(after[end-80:end+40]))