import csv, sys, collections
from datetime import datetime, timezone
rows=[]
with open(sys.argv[1], newline='') as f:
    r=csv.DictReader(f)
    print(r.fieldnames)
    for x in r: rows.append(x)
print('rows',len(rows))
empty=collections.Counter()
for x in rows:
    for k,v in x.items():
        if v is None or v.strip()=='' : empty[k]+=1
print('empty',empty)
offs=collections.Counter(x['time_stamp'][-6:] for x in rows); print('offsets',offs)
ts=[int(datetime.fromisoformat(x['time_stamp']).timestamp()) for x in rows]
print('sorted',ts==sorted(ts),'dups',len(ts)-len(set(ts)))
d=collections.Counter(b-a for a,b in zip(ts,ts[1:])); print('deltas top',d.most_common(15)); print('n distinct deltas',len(d))
print('first',datetime.fromtimestamp(ts[0],timezone.utc),'last',datetime.fromtimestamp(ts[-1],timezone.utc))
# runs
runs=[]; i=0
while i<len(ts):
    if i+1<len(ts):
        st=ts[i+1]-ts[i]; j=i+1
        while j+1<len(ts) and ts[j+1]-ts[j]==st: j+=1
        runs.append((ts[i],st,j-i+1)); i=j+1
    else: runs.append((ts[i],0,1)); i+=1
print('runs',len(runs))
