import sys, collections, bisect
sys.path.insert(0, sys.argv[3])
from ortak import *
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
F = load_file(sys.argv[1]); DB = load_db(sys.argv[2])
# days coverage detail
hours = collections.defaultdict(set)
for r in F: hours[hour_ist(r['ep'])[:10]].add(hour_ist(r['ep']))
d0 = datetime(2026,4,27); alld = [(d0+timedelta(days=i)).strftime('%Y-%m-%d') for i in range(163)]
print('missing IST days:', [d for d in alld if d not in hours])
print('partial days (<18h):', {d: len(hours[d]) for d in alld if d in hours and len(hours[d]) < 18})
# rounding variants for inserts: recompute insert set
keep = [r for r in DB if not (r['ct']==BATCH and r['epi']<MAY1)]
keps = sorted(r['epi'] for r in keep)
def near(ep):
    i = bisect.bisect_left(keps, ep); c=[10**9]
    if i < len(keps): c.append(keps[i]-ep)
    if i: c.append(ep-keps[i-1])
    return min(c)
ins = [r for r in F if near(r['ep']) > 60]
hu = sum((Decimal(r['sa'])+Decimal(r['sb']))/2 for r in ins)
up = sum(((Decimal(r['sa'])+Decimal(r['sb']))/2).quantize(Decimal('0.1'), ROUND_HALF_UP) for r in ins)
ev = sum(((Decimal(r['sa'])+Decimal(r['sb']))/2).quantize(Decimal('0.1'), ROUND_HALF_EVEN) for r in ins)
py = sum(Decimal(str(round((r['a']+r['b'])/2, 1))) for r in ins)
print('insert n', len(ins), 'sum unrounded (a+b)/2 = %s | half-up %s | half-even %s | python float round %s' % (hu, up, ev, py))
# spot checks
def spot(h):
    rs = [r for r in F if hour_ist(r['ep']) == h]
    n = len(rs); cf = sum((r['ca']+r['cb'])/2 for r in rs)/n; rh = sum(r['h'] for r in rs)/n
    atm = sum((r['a']+r['b'])/2 for r in rs)/n
    epa = 0.524*cf - 0.0862*rh + 5.75
    ins_n = sum(1 for r in rs if near(r['ep']) > 60)
    print('  %s:00 IST  n=%d (insert %d)  mean cf1=%.3f  mean RH=%.2f  mean cf_atm=%.3f  EPA=%.3f' % (h, n, ins_n, cf, rh, atm, epa))
print('spot checks:')
spot('2026-05-15 14'); spot('2026-08-01 08')
cands = collections.defaultdict(list)
for r in F: cands[hour_ist(r['ep'])].append(r)
mid = [h for h, rs in sorted(cands.items()) if len(rs) >= 28 and 35 <= sum((r['a']+r['b'])/2 for r in rs)/len(rs) <= 65]
print('  hours with mean cf_atm 35-65:', len(mid), 'of', len(cands))
spot('2026-05-06 08') if '2026-05-06 08' in mid else None
print('  first few candidates', mid[:5], 'Oct-11-like check n/a')
