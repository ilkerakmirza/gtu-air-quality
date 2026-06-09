import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('index.html', 'r', encoding='utf-8') as f:
    h = f.read()

old = """onerror="this.src=\\'campus_map_small.jpg\\';this.onerror=function(){this.style.display=\\'none\\';this.nextElementSibling.style.display=\\'flex\\'}\""""
new = """onerror="this.style.display='none';this.nextElementSibling.style.display='flex'\""""

# Use the exact string found
old_exact = "onerror=\"this.src='campus_map_small.jpg';this.onerror=function(){this.style.display='none';this.nextElementSibling.style.display='flex'}\""
new_exact  = "onerror=\"this.style.display='none';this.nextElementSibling.style.display='flex'\""

if old_exact in h:
    h = h.replace(old_exact, new_exact)
    print('Fixed!')
else:
    print('Not found with exact match')
    idx = h.find('campus_map_small.jpg')
    print('Still at:', idx)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(h)

remaining = 'campus_map_small.jpg' in h or 'abl.gtu.edu.tr' in h
print('External refs remaining:', remaining)
size = len(h.encode('utf-8')) / 1024 / 1024
print(f'File size: {size:.1f} MB')
