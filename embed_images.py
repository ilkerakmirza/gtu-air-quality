import json, base64, re, os, sys

# Fix stdout encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('photos_b64.json', 'r') as f:
    photos = json.load(f)

with open('campus_b64_small.txt', 'r', encoding='utf-8-sig') as f:
    campus_small_b64 = f.read().strip()

# Find Turkish campus map
tr_file = None
for fn in os.listdir('.'):
    if fn.startswith('22TR') and fn.endswith('.jpg'):
        tr_file = fn
        break

with open(tr_file, 'rb') as f:
    campus_tr_b64 = base64.b64encode(f.read()).decode()

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Build replacements dict (old -> new)
repls = {
    'src="campus_map_small.jpg"':
        'src="data:image/jpeg;base64,' + campus_small_b64 + '"',
    'src="https://abl.gtu.edu.tr/resimler/103/t_48573638.jpg"':
        'src="data:image/jpeg;base64,' + photos['ilker'] + '"',
    'src="https://abl.gtu.edu.tr/resimler/103/t_10332.jpg"':
        'src="data:image/jpeg;base64,' + photos['pinar'] + '"',
    'src="https://abl.gtu.edu.tr/resimler/108/t_1093.jpg"':
        'src="data:image/jpeg;base64,' + photos['ozgun'] + '"',
    'src="https://abl.gtu.edu.tr/resimler/103/t_68394858.jpg"':
        'src="data:image/jpeg;base64,' + photos['serra'] + '"',
}

# Find dynamic TR map src
m = re.search(r'src="([^"]*22TR[^"]*\.jpg)"', html)
if m:
    repls[m.group(0)] = 'src="data:image/jpeg;base64,' + campus_tr_b64 + '"'

for old, new in repls.items():
    html = html.replace(old, new)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

size_mb = len(html.encode('utf-8')) / 1024 / 1024
still_external = 'abl.gtu.edu.tr' in html or 'campus_map_small.jpg' in html
print(f'Done. Size={size_mb:.1f}MB  ExternalRefs={still_external}')
