import sys, collections, bisect
sys.path.insert(0, sys.argv[3])
from ortak import *
from decimal import Decimal, ROUND_HALF_UP
F = load_file(sys.argv[1]); DB = load_db(sys.argv[2])
fset = {r['ep']: r for r in F}
print('file rows', len(F), 'db rows (<cut)', len(DB), 'db frac-sec rows', sum(r['frac'] for r in DB))
# step 1
batch = [r for r in DB if r['ct'] == BATCH]
print('batch rows', len(batch), 'of which <May1', sum(r['epi'] < MAY1 for r in batch))
dele = [r for r in batch if r['epi'] < MAY1 and r['epi'] not in fset]
print('STEP1 delete', len(dele), 'ids', min(r['id'] for r in dele), '-', max(r['id'] for r in dele), 'sum ids', sum(r['id'] for r in dele))
dids = {r['id'] for r in dele}
keep = [r for r in DB if r['id'] not in dids]
# step 2
exact = [r for r in keep if r['epi'] in fset and not r['frac']]
ok = [r for r in exact if abs(r['a']-fset[r['epi']]['a']) < 0.06 and abs(r['b']-fset[r['epi']]['b']) < 0.06]
bad = [r for r in exact if r not in ok]
print('exact ts matches', len(exact), 'STEP2 update (agree)', len(ok), 'disagree', len(bad))
for r in bad[:10]:
    f = fset[r['epi']]; print('  disagree', r['rt'], r['a'], r['b'], 'file', f['a'], f['b'])
mx = max(max(abs(r['a']-fset[r['epi']]['a']), abs(r['b']-fset[r['epi']]['b'])) for r in ok); print('  max |diff| among agreeing', round(mx,4))
near = [r for r in ok if max(abs(r['a']-fset[r['epi']]['a']), abs(r['b']-fset[r['epi']]['b'])) > 0.04]; print('  agreeing with |diff|>0.04:', len(near))
had = [r for r in ok if r['ca'] is not None]
chg = [r for r in had if abs(r['ca']-fset[r['epi']]['ca'])>1e-6 or abs(r['cb']-fset[r['epi']]['cb'])>1e-6]
print('  step2 rows already with cf1', len(had), '-> value would change', len(chg))
print('  step2 rows newly getting cf1', len(ok)-len(had))
print('  step2 by month', dict(collections.Counter(month_utc(r['epi']) for r in ok)))
print('  step2 checksum sum(cf1_a)=%.1f sum(cf1_b)=%.1f' % (sum(fset[r['epi']]['ca'] for r in ok), sum(fset[r['epi']]['cb'] for r in ok)))
batch_exact = [r for r in exact if r['ct']==BATCH]; print('  batch rows with exact match', len(batch_exact))
# DB rows with cf1 not in step2
other_cf1 = [r for r in keep if r['ca'] is not None and r not in ok]; print('  rows with cf1 outside step2 (<cut)', len(other_cf1))
# step 3
keps = sorted(r['epi'] for r in keep)  # frac ignored: none
extra = [int(x) for x in sys.argv[4].split(',')] if len(sys.argv) > 4 and sys.argv[4] else []
keps = sorted(keps + extra)
def nearest(ep):
    i = bisect.bisect_left(keps, ep); c = []
    if i < len(keps): c.append(abs(keps[i]-ep))
    if i > 0: c.append(abs(keps[i-1]-ep))
    return min(c) if c else 10**9
dist = [nearest(r['ep']) for r in F]
ins = [r for r, d in zip(F, dist) if d > 60]
ins_lt = [r for r, d in zip(F, dist) if d >= 60]
print('STEP3 insert (no DB row within <=60 s)', len(ins), '| if strict <60 s window:', len(ins_lt), '| file rows at exactly 60 s:', sum(d == 60 for d in dist))
print('  dist histogram (matched rows)', sorted(collections.Counter(d for d in dist if d <= 60).items())[:12], '...')
print('  insert by UTC month', dict(sorted(collections.Counter(month_utc(r['ep']) for r in ins).items())))
# checksums
def s(xs): return float(sum(xs))
pm = [pm_round(r['sa'], r['sb']).quantize(Decimal('0.1'), ROUND_HALF_UP) for r in ins]
ties = sum(1 for r in ins if ((Decimal(r['sa'])+Decimal(r['sb']))/2) % Decimal('0.1') == Decimal('0.05'))
print('  insert checksums: sum pm2_5(half-up)=%.1f  ties(x.x5)=%d  sum atm_a=%.1f sum atm_b=%.1f sum cf1_a=%.1f sum cf1_b=%.1f sum hum=%.0f' % (s(pm), ties, s(r['a'] for r in ins), s(r['b'] for r in ins), s(r['ca'] for r in ins), s(r['cb'] for r in ins), s(r['h'] for r in ins)))
print('  insert first/last', ins[0]['ts'], ins[-1]['ts'])
# file rows matched by DB but not exactly
fuzzy = [r for r, d in zip(F, dist) if 0 < d <= 60]; print('  file rows covered only by a non-exact DB row', len(fuzzy))
# final state
fin_keep = [r for r in keep if r['epi'] < CUT]
okids = {r['id'] for r in ok}
cf1_keep = sum(1 for r in fin_keep if r['ca'] is not None or r['id'] in okids)
total = len(fin_keep) + len(ins); cf1 = cf1_keep + len(ins)
print('FINAL <cut: total', total, 'with cf1', cf1, 'without cf1', total-cf1, '(kept DB', len(fin_keep), '+ insert', len(ins), ')')
nocf = [r for r in fin_keep if r['ca'] is None and r['id'] not in okids]
print('  rows without cf1 by month', dict(sorted(collections.Counter(month_utc(r['epi']) for r in nocf).items())))
eps = [r['epi'] for r in fin_keep] + [r['ep'] for r in ins]
hours = set(hour_ist(e) for e in eps)
byday = collections.Counter(h[:10] for h in hours)
print('  distinct IST hours', len(hours), 'days total', len(byday), 'days >=18h', sum(v >= 18 for v in byday.values()), 'days 6-17h', sum(6 <= v <= 17 for v in byday.values()), 'days <6h', sum(v < 6 for v in byday.values()))
print('  first/last IST day', min(byday), max(byday))
# file-only hours for comparison
fh = set(hour_ist(r['ep']) for r in F); fd = collections.Counter(h[:10] for h in fh)
print('  (file alone: hours', len(fh), 'days>=18', sum(v>=18 for v in fd.values()), '6-17', sum(6<=v<=17 for v in fd.values()), ')')
