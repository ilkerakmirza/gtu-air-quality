import sys
sys.path.insert(0, sys.argv[2])
from ortak import *
F = load_file(sys.argv[1])
for r in F:
    if r['ca'] + 1e-9 < r['a'] or r['cb'] + 1e-9 < r['b']: print('cf1<atm', r['ts'], r['a'], r['b'], r['ca'], r['cb'])
    if 0.524*(r['ca']+r['cb'])/2 - 0.0862*r['h'] + 5.75 < 0: print('negEPA', r['ts'], r['ca'], r['cb'], r['h'])
# gaps > 1 h
for p, q in zip(F, F[1:]):
    if q['ep'] - p['ep'] > 3600: print('gap', p['ts'], '->', q['ts'], round((q['ep']-p['ep'])/3600, 1), 'h')
# ratio atm/cf1 check above 25 (should be <1)
import statistics
hi = [r['a']/r['ca'] for r in F if r['ca'] > 50]; print('atm/cf1 ratio for cf1>50: median %.3f' % statistics.median(hi))
print('QA-flag rows by month', __import__('collections').Counter(month_utc(r['ep']) for r in F if abs(r['ca']-r['cb'])>=5 and abs(r['ca']-r['cb'])/((r['ca']+r['cb'])/2)>=0.7))
