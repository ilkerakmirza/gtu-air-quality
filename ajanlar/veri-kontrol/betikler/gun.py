import sys, collections
sys.path.insert(0, sys.argv[2])
from ortak import *
F = load_file(sys.argv[1])
c = collections.Counter(datetime.fromtimestamp(r['ep'], IST).strftime('%Y-%m-%d') for r in F)
for thr, lab in ((648, '>=90% of 720 (Barkjohn 2021)'), (540, '>=75% of 720')):
    print(lab, sum(v >= thr for v in c.values()), 'of 163 calendar days; by month', dict(sorted(collections.Counter(d[:7] for d, v in c.items() if v >= thr).items())))
print('days below 90%:', {d: v for d, v in sorted(c.items()) if v < 648})
