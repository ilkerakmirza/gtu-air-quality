import sys, bisect
sys.path.insert(0, sys.argv[3])
from ortak import *
F = load_file(sys.argv[1]); DB = load_db(sys.argv[2])
fe = sorted(r['ep'] for r in F); fs = set(fe)
for r in DB:
    if r['ct'] == BATCH: continue
    if r['epi'] in fs: continue
    i = bisect.bisect_left(fe, r['epi']); d = min(abs(fe[j]-r['epi']) for j in (i-1, i) if 0 <= j < len(fe))
    print('non-exact DB row', r['id'], r['rt'], 'a', r['a'], 'b', r['b'], 'cf1', r['ca'], 'nearest file row', d, 's')
