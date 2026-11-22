"""Did heavy sectoral/thematic fund buying line up with weaker market returns afterwards?
Uses models/amfi-thematic-monthly.csv and Yahoo Finance monthly closes for the Nifty 500
(^CRSLDX) and Nifty Midcap/Next 50 proxy. Splits months into thirds by each froth
measure and compares the following 6- and 12-month Nifty 500 returns.
Run: python3 -I scripts/research/amfi_froth_test.py
"""
import csv, json, os, urllib.request, datetime, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows = list(csv.DictReader(open(os.path.join(ROOT, 'models', 'amfi-thematic-monthly.csv'))))
j = json.load(urllib.request.urlopen(urllib.request.Request(
    'https://query1.finance.yahoo.com/v8/finance/chart/%5ECRSLDX?range=10y&interval=1mo', headers={'User-Agent': 'Mozilla/5.0'}), timeout=25))['chart']['result'][0]
px = {}
for t, c in zip(j['timestamp'], j['indicators']['quote'][0]['close']):
    if c: px[datetime.datetime.utcfromtimestamp(t).strftime('%Y-%m')] = c
ms = sorted(px)
def fwd(m, n):
    if m not in px: return None
    i = ms.index(m)
    return px[ms[i + n]] / px[m] - 1 if i + n < len(ms) else None
for meas in ['flow_3m_pct_aum', 'share_3m', 'new_schemes_6m', 'aum_share']:
    for h in (6, 12):
        pts = [(float(r[meas]), fwd(r['month'], h)) for r in rows if r[meas] not in ('', None) and fwd(r['month'], h) is not None]
        pts.sort()
        n = len(pts); q = n // 3
        lo, mid, hi = pts[:q], pts[q:n - q], pts[n - q:]
        f = lambda s: st.median(y for _, y in s) * 100
        print(f'{meas:16s} next {h:2d}m Nifty 500: low third {f(lo):+5.1f}%  middle {f(mid):+5.1f}%  high third {f(hi):+5.1f}%  '
              f'(n={n}; high third = {hi[0][0]:.3g} and above)')
top = sorted(rows, key=lambda r: -float(r['flow_3m_pct_aum'] or 0))[:6]
print('\nTop months by flow_3m_pct_aum and what followed (Nifty 500):')
for r in sorted(top, key=lambda r: r['month']):
    a, b = fwd(r['month'], 6), fwd(r['month'], 12)
    print(r['month'], r['flow_3m_pct_aum'], 'next 6m', f'{a*100:+.1f}%' if a is not None else '-', 'next 12m', f'{b*100:+.1f}%' if b is not None else '-')
