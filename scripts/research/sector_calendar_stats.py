"""India sector facts from Yahoo Finance daily closes (about 10 years, 13 Nifty sector indices).
1. Calendar-year return of each sector, minus Nifty 50, and the best-worst spread.
2. Persistence: did last year's top-4 sectors beat the Nifty again the next year?
3. Worst peak-to-trough fall and the longest stretch below a previous high.
Run: python3 -I scripts/research/sector_calendar_stats.py
Used for knowledge/india-sector-facts-2016-2026.md.
"""
import json, urllib.request, urllib.parse, datetime
UA = {'User-Agent': 'Mozilla/5.0'}
S = {'Bank': '^NSEBANK', 'IT': '^CNXIT', 'FMCG': '^CNXFMCG', 'Realty': '^CNXREALTY', 'Energy': '^CNXENERGY',
     'Auto': '^CNXAUTO', 'PSU Bank': '^CNXPSUBANK', 'Metal': '^CNXMETAL', 'Pharma': '^CNXPHARMA',
     'Infra': '^CNXINFRA', 'Consumption': '^CNXCONSUM', 'Next 50': '^NSMIDCP', 'Fin Services': 'NIFTY_FIN_SERVICE.NS',
     'Nifty 50': '^NSEI'}

def daily(sym):
    u = ('https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(sym, safe='') + '?range=10y&interval=1d')
    j = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25))['chart']['result'][0]
    return [(datetime.datetime.utcfromtimestamp(t).date(), c) for t, c in zip(j['timestamp'], j['indicators']['quote'][0]['close']) if c]

D = {k: daily(v) for k, v in S.items()}
def year_ret(rows, y):
    a = [c for d, c in rows if d.year == y - 1]; b = [c for d, c in rows if d.year == y]
    return b[-1] / a[-1] - 1 if a and b else None
years = range(2017, datetime.date.today().year + 1)
print('Calendar-year return minus Nifty 50 (pp); last year is year-to-date')
tab = {}
for y in years:
    n = year_ret(D['Nifty 50'], y)
    tab[y] = {k: round((year_ret(v, y) - n) * 100, 1) for k, v in D.items() if k != 'Nifty 50' and year_ret(v, y) is not None}
    r = sorted(tab[y].items(), key=lambda x: -x[1])
    print(y, f'Nifty {n*100:+.1f}%', '| best', r[0], '| worst', r[-1], f'| spread {r[0][1]-r[-1][1]:.0f} pp')
print('\nPersistence: last year top-4 sectors, how many beat Nifty 50 the next year')
hits = tot = 0
for y in list(years)[1:]:
    top = [k for k, _ in sorted(tab[y-1].items(), key=lambda x: -x[1])[:4]]
    nxt = [tab[y].get(k) for k in top]
    h = sum(1 for x in nxt if x is not None and x > 0); hits += h; tot += len(top)
    bot = [k for k, _ in sorted(tab[y-1].items(), key=lambda x: x[1])[:4]]
    hb = sum(1 for k in bot if tab[y].get(k, 0) > 0)
    print(y, 'winners', top, f'-> {h}/4 beat again', '| losers', bot, f'-> {hb}/4 beat next year')
print(f'Overall: {hits}/{tot} = {hits/tot:.0%} of prior-year top-4 sectors beat the Nifty the following year')
print('\nWorst fall and longest time below a previous high')
for k, rows in D.items():
    peak = rows[0][1]; pk_d = rows[0][0]; mdd = 0; longest = 0
    for d, c in rows:
        if c >= peak: peak, pk_d = c, d
        mdd = min(mdd, c / peak - 1); longest = max(longest, (d - pk_d).days)
    print(f'{k:13s} worst fall {mdd*100:6.1f}%   longest below high {longest/365:4.1f} yrs   now {rows[-1][1]/max(c for _,c in rows)*100-100:6.1f}% from high')
