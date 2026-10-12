import sys, collections, statistics, calendar
sys.path.insert(0, sys.argv[3])
from ortak import *
F = load_file(sys.argv[1]); DB = load_db(sys.argv[2])
fset = {r['ep']: r for r in F}
# --- provenance agreement
ex = [r for r in DB if r['epi'] in fset and r['ct'] != BATCH]
da = [abs(r['a']-fset[r['epi']]['a']) for r in ex]; db_ = [abs(r['b']-fset[r['epi']]['b']) for r in ex]
dh = [abs(r['h']-fset[r['epi']]['h']) for r in ex]
print('exact matches', len(ex), '| |dA| max %.3f mean %.4f | |dB| max %.3f mean %.4f' % (max(da), statistics.mean(da), max(db_), statistics.mean(db_)))
print('  rows with both |d|<=0.05:', sum(1 for x, y in zip(da, db_) if x <= 0.0500001 and y <= 0.0500001), ' humidity equal:', sum(1 for x in dh if x < 0.5), 'max |dRH|', max(dh))
c1 = [r for r in ex if r['ca'] is not None]
print('  rows with DB cf1:', len(c1), 'max |dcf1|', max(max(abs(r['ca']-fset[r['epi']]['ca']), abs(r['cb']-fset[r['epi']]['cb'])) for r in c1))
srv = [r for r in DB if r['ct'] != BATCH]
print('  server rows in range', len(srv), 'exact', len(ex), '(%.2f%%), 1-s off 6, disagree 1' % (100*len(ex)/len(srv)))
# --- completeness per UTC? use Istanbul calendar month
byh = collections.defaultdict(list)
for r in F: byh[hour_ist(r['ep'])].append(r)
months = collections.OrderedDict()
d0 = datetime(2026,4,27)
for i in range(163):
    d = (d0+timedelta(days=i)); months.setdefault(d.strftime('%Y-%m'), []).append(d.strftime('%Y-%m-%d'))
print('\nCompleteness (Istanbul time) month: days | 2-min readings/expected | hours with any data/expected | hours >=75%% (>=23/30 readings) | days with >=18 h (any) | days >=18 valid(>=75%%) h')
tot = collections.Counter()
for m, days in months.items():
    exp_r = 720*len(days); n = sum(len(byh.get(f'{d} {h:02d}', [])) for d in days for h in range(24))
    hrs = [len(byh.get(f'{d} {h:02d}', [])) for d in days for h in range(24)]
    anyh = sum(1 for x in hrs if x > 0); v75 = sum(1 for x in hrs if x >= 23)
    d18 = sum(1 for d in days if sum(1 for h in range(24) if byh.get(f'{d} {h:02d}')) >= 18)
    d18v = sum(1 for d in days if sum(1 for h in range(24) if len(byh.get(f'{d} {h:02d}', [])) >= 23) >= 18)
    print(f'  {m}: {len(days)} d | {n}/{exp_r} ({100*n/exp_r:.1f}%) | {anyh}/{24*len(days)} ({100*anyh/(24*len(days)):.1f}%) | {v75} | {d18} | {d18v}')
    for k, v in (('days', len(days)), ('n', n), ('exp', exp_r), ('anyh', anyh), ('v75', v75), ('d18', d18), ('d18v', d18v)): tot[k] += v
print('  TOTAL:', dict(tot), 'reading completeness %.1f%%' % (100*tot['n']/tot['exp']))
# --- plausibility
neg = sum(1 for r in F if min(r['a'], r['b'], r['ca'], r['cb']) < 0)
lt = sum(1 for r in F if r['ca'] + 1e-9 < r['a'] or r['cb'] + 1e-9 < r['b'])
eq = sum(1 for r in F if r['ca'] == r['a'] and r['cb'] == r['b'])
hum = sum(1 for r in F if not (0 <= r['h'] <= 100))
print('\nPlausibility: negative values', neg, '| cf1 < atm (either channel)', lt, '| cf1 == atm both channels', eq, '| humidity outside 0-100', hum)
print('  humidity min/max', min(r['h'] for r in F), max(r['h'] for r in F), '| cf1 A max', max(r['ca'] for r in F), 'B max', max(r['cb'] for r in F), '| atm A max', max(r['a'] for r in F), 'B max', max(r['b'] for r in F))
print('  zeros: cf1 A==0', sum(r['ca']==0 for r in F), 'B==0', sum(r['cb']==0 for r in F), '| values >= 500 (cf1)', sum(max(r['ca'], r['cb']) >= 500 for r in F))
# ratio check cf_atm/cf1 above 25
# --- QA A/B
def bad(a, b):
    d = abs(a-b); m = (a+b)/2
    return d >= 5 and m > 0 and d/m >= 0.70
rq = [r for r in F if bad(r['ca'], r['cb'])]
rqa = [r for r in F if bad(r['a'], r['b'])]
print('\nQA |A-B|>=5 & >=70%: 2-min rows flagged on cf1', len(rq), 'on atm', len(rqa))
for r in rq[:10]: print('   ', r['ts'], 'cf1 A', r['ca'], 'B', r['cb'])
hq = []
for h, rs in byh.items():
    A = sum(r['ca'] for r in rs)/len(rs); B = sum(r['cb'] for r in rs)/len(rs)
    if bad(A, B): hq.append((h, round(A,1), round(B,1)))
print('  hours flagged (hourly means of cf1 A vs B):', len(hq), hq[:10])
# loose: |A-B|>=5 alone, or rel>=70 alone
print('  rows |A-B|>=5 only:', sum(abs(r['ca']-r['cb'])>=5 for r in F), '| rows rel>=70% only:', sum((r['ca']+r['cb'])>0 and abs(r['ca']-r['cb'])/((r['ca']+r['cb'])/2)>=0.7 for r in F))
# Barkjohn 2021 24-h rule: drop if |A-B|>5 and %diff > 2 SD... (just report daily mean channel diff stats)
byd = collections.defaultdict(list)
for r in F: byd[datetime.fromtimestamp(r['ep'], IST).strftime('%Y-%m-%d')].append(r)
dd = []
for d, rs in byd.items():
    A = sum(r['ca'] for r in rs)/len(rs); B = sum(r['cb'] for r in rs)/len(rs); dd.append((abs(A-B), abs(A-B)/((A+B)/2) if A+B else 0, d))
print('  daily |A-B| max %.2f, daily rel diff max %.1f%%, mean rel diff %.1f%%; days with B>A: %d of %d' % (max(x[0] for x in dd), 100*max(x[1] for x in dd), 100*statistics.mean(x[1] for x in dd), sum(1 for d, rs in byd.items() if sum(r['cb'] for r in rs) > sum(r['ca'] for r in rs)), len(byd)))
# --- spikes (report only)
print('\nSpikes (report only, nothing removed):')
spk = []
rows = F
for i in range(len(rows)):
    w = [rows[j] for j in range(max(0,i-7), min(len(rows), i+8)) if j != i and abs(rows[j]['ep']-rows[i]['ep']) <= 900]
    if len(w) < 6: continue
    med = statistics.median((x['ca']+x['cb'])/2 for x in w); v = (rows[i]['ca']+rows[i]['cb'])/2
    if v > 3*med and v - med > 20: spk.append((rows[i]['ts'], round(v,1), round(med,1), rows[i]['ca'], rows[i]['cb']))
print('  isolated 2-min spikes (cf1 mean > 3x and > +20 ug/m3 above +-15 min median):', len(spk), '| both channels agree in', sum(1 for s in spk if not bad(s[3], s[4])))
for s in sorted(spk, key=lambda s: -s[1])[:6]: print('   ', s)
hm = []
for h, rs in byh.items():
    cf = sum((r['ca']+r['cb'])/2 for r in rs)/len(rs); rh = sum(r['h'] for r in rs)/len(rs)
    hm.append((round(0.524*cf-0.0862*rh+5.75,1), h, len(rs), round(cf,1)))
hm.sort(reverse=True)
print('  top hourly EPA PM2.5:', hm[:5])
e = sorted(x[0] for x in hm); print('  hourly EPA percentiles p50 %.1f p90 %.1f p99 %.1f max %.1f; hours > 55.4: %d; negative EPA hours: %d' % (e[len(e)//2], e[int(.9*len(e))], e[int(.99*len(e))], e[-1], sum(x > 55.4 for x in e), sum(x < 0 for x in e)))
neg2 = sum(1 for r in F if 0.524*(r['ca']+r['cb'])/2 - 0.0862*r['h'] + 5.75 < 0); print('  2-min rows with negative EPA result:', neg2)
