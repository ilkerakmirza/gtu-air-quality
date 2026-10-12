import csv, json, re, bisect
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
IST = timezone(timedelta(hours=3))
CUT = int(datetime(2026,10,6,21,0,tzinfo=timezone.utc).timestamp())
MAY1 = int(datetime(2026,5,1,tzinfo=timezone.utc).timestamp())
BATCH = '2026-06-15 10:48:00.171785+00'

def load_file(path):
    out = []
    with open(path, newline='') as f:
        for x in csv.DictReader(f):
            out.append(dict(ep=int(datetime.fromisoformat(x['time_stamp']).timestamp()), ts=x['time_stamp'],
                h=float(x['humidity']), a=float(x['pm2.5_atm_a']), b=float(x['pm2.5_atm_b']),
                ca=float(x['pm2.5_cf_1_a']), cb=float(x['pm2.5_cf_1_b']),
                sa=x['pm2.5_atm_a'], sb=x['pm2.5_atm_b']))
    return out

def load_db(path):
    s = open(path).read()
    if s.lstrip().startswith('{'):
        s = json.loads(s)['result']
    m = re.search(r'<untrusted-data-[^>]+>\s*(\[.*\])\s*</untrusted-data', s, re.S)
    rows = json.loads(m.group(1))
    for r in rows:
        ep = Decimal(r['ep'])
        r['epi'] = int(ep); r['frac'] = ep != int(ep)
        for k in ('p','a','b','ca','cb','h'):
            r[k] = None if r[k] is None else float(r[k])
    return rows

def pm_round(sa, sb):
    return (Decimal(sa)+Decimal(sb))/2

def hour_ist(ep):
    return datetime.fromtimestamp(ep, IST).strftime('%Y-%m-%d %H')
def month_utc(ep):
    return datetime.fromtimestamp(ep, timezone.utc).strftime('%Y-%m')
