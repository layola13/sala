#!/usr/bin/env python3
"""Agent AS census: apply the classification map to the extracted .NET surface.

Reads classify_map.py / classify_map2.py and dotnet_surface.tsv from this
directory, asserts EVERY distinct extracted type is classified exactly once,
and writes gap_classification.tsv next to this script.

Classification (same 口径 as the whole cross-language census batch):
  E 已有等价 / D 可直接对应 / M 需建模 / X 模型不合
Family rules used in the map's notes:
  R1 exception types -> X (SA models errors as status codes + error-code names)
  R2 delegate types   -> X (callbacks are handle+poll/registration in SA)
  R3 EventArgs types   -> X (event/subscription model)
"""
import csv, collections, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, 'classify_map.py'), encoding='utf-8').read())
exec(open(os.path.join(HERE, 'classify_map2.py'), encoding='utf-8').read())

CLS = {'E': '已有等价', 'D': '可直接对应', 'M': '需建模', 'X': '模型不合'}

rows = list(csv.DictReader(open(os.path.join(HERE, 'dotnet_surface.tsv'), encoding='utf-8'), delimiter='\t'))
types = {}
for r in rows:
    if r['owner'] != '':
        continue
    key = (r['namespace'], r['name'])
    mem = sum(1 for m in rows if m['owner'] == r['name'] and m['namespace'] == r['namespace'])
    if key not in types or mem > types[key]['members']:
        types[key] = {'kind': r['kind'], 'members': mem,
                      'obsolete': r['obsolete'], 'assembly': r['assembly']}
print(f"raw type rows={sum(1 for r in rows if r['owner']=='')} distinct (ns,name)={len(types)}")

missing = [k for k in types if k not in MAP]
extra = [k for k in MAP if k not in types]
if missing:
    print('UNMAPPED:', missing)
if extra:
    print('MAP-ONLY (not extracted):', extra)
if missing or extra:
    sys.exit(1)

out = open(os.path.join(HERE, 'gap_classification.tsv'), 'w', encoding='utf-8')
out.write("namespace\ttype\tkind\tmembers\tobsolete\tclass\tsa_evidence\tnote\n")
cnt = collections.defaultdict(collections.Counter)
tot = collections.Counter()
for (ns, name) in sorted(types):
    t = types[(ns, name)]
    cls, ev, note = MAP[(ns, name)]
    out.write("\t".join([ns, name, t['kind'], str(t['members']), t['obsolete'],
                         CLS[cls], ev, note]) + "\n")
    cnt[ns][cls] += 1
    tot[cls] += 1
out.close()

print("== per-namespace class counts (E/D/M/X, types) ==")
for ns in sorted(cnt, key=lambda n: -sum(cnt[n].values())):
    c = cnt[ns]
    print(f"{ns}\t{sum(c.values())}\tE={c['E']}\tD={c['D']}\tM={c['M']}\tX={c['X']}")
print(f"TOTAL\t{sum(tot.values())}\tE={tot['E']}\tD={tot['D']}\tM={tot['M']}\tX={tot['X']}")
mw = collections.Counter()
for (ns, name), t in types.items():
    mw[MAP[(ns, name)][0]] += t['members']
print("== member-weighted ==")
for k in 'EDMX':
    print(f"{CLS[k]}\tmembers={mw[k]}")
