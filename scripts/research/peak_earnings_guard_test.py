"""Back-check for the peak-earnings guard's commodity trigger (backlog #19).
When the commodity price sits in the top fifth of its own 5-year range, does the
matching Nifty sector do worse over the next 12 months than at other times?
Nifty Metal vs COMEX copper (HG=F) and Nifty Energy vs Brent (BZ=F), monthly closes
from Yahoo Finance (max history). Run: python3 -I scripts/research/peak_earnings_guard_test.py
"""
import json, urllib.request, urllib.parse, datetime, statistics as st
UA = {'User-Agent': 'Mozilla/5.0'}
def monthly(sym):
    u = 'https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(sym, safe='') + '?range=max&interval=1mo'
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))['chart']['result'][0]
    return {datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m'): c for t, c in zip(j['timestamp'], j['indicators']['quote'][0]['close']) if c}
for idx, com, name in [('^CNXMETAL', 'HG=F', 'Metal vs copper'), ('^CNXENERGY', 'BZ=F', 'Energy vs Brent')]:
    S, C = monthly(idx), monthly(com)
    ms = sorted(set(S) & set(C))
    hot, rest = [], []
    for i, m in enumerate(ms):
        if i < 60 or i + 12 >= len(ms): continue
        win = [C[x] for x in ms[i - 60:i + 1]]
        lo, hi = min(win), max(win)
        pctl = (C[m] - lo) / (hi - lo) * 100 if hi > lo else 50
        fwd = S[ms[i + 12]] / S[m] - 1
        (hot if pctl >= 80 else rest).append((m, fwd))
    f = lambda xs: (st.median(x for _, x in xs) * 100, sum(1 for _, x in xs if x < 0) / len(xs) * 100) if xs else (float('nan'), float('nan'))
    h, r = f(hot), f(rest)
    print(f'{name}: {ms[0]} to {ms[-1]}')
    print(f'  commodity in top fifth of 5-yr range: {len(hot):3d} months, next-12m sector median {h[0]:+.1f}%, lower in {h[1]:.0f}%')
    print(f'  all other months:                     {len(rest):3d} months, next-12m sector median {r[0]:+.1f}%, lower in {r[1]:.0f}%')
    yrs = sorted({m[:4] for m, _ in hot}); print('  hot years:', ', '.join(yrs))
