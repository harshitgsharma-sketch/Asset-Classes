"""Parabolic-move check: how far each asset trades above its 150-day EMA.

Rule (from knowledge/sector-rotation-7-indian-bull-runs.md, backlog item 1):
  gap = close / EMA150(close) - 1
  gap >= 70%  -> "Parabolic"  (euphoric; the presenter's sell-side warning)
  gap >= 50%  -> "Stretched"  (watch)
  otherwise   -> "Normal"

It is a FLAG ONLY: it does not change any model score. It also back-tests itself on
each asset's own daily history (up to 10 years): every past episode above 70%, and
what the price did 3, 6 and 12 months after the first day it fired.

Started by fetch_prices.py, so the daily GitHub Action runs it without a workflow change. Best effort per asset: a failed
fetch keeps the previous reading, marked stale. Writes data/parabolic.json.
Standard library only.
"""
import json, os, urllib.request, urllib.parse, datetime, time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'parabolic.json')
UA = {'User-Agent': 'Mozilla/5.0 (entry-exit-board parabolic check)'}
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

SPAN = 150          # EMA length in trading days
PARABOLIC = 0.70    # gap that marks a parabolic move
STRETCHED = 0.50    # gap that marks "watch"
MERGE_DAYS = 63     # firings within ~3 months count as one episode
HORIZONS = {'3m': 63, '6m': 126, '12m': 252}

# board item id -> Yahoo Finance symbol
SYMBOLS = {
    'GOLD': 'GC=F', 'CMD_SILVER': 'SI=F', 'CMD_BRENT': 'BZ=F', 'CMD_COPPER': 'HG=F', 'BTC': 'BTC-USD',
    'CMD_ALUMINIUM': 'ALI=F', 'CMD_IRONORE': 'TIO=F', 'CMD_NATGAS': 'NG=F',
    'CRY_ETH': 'ETH-USD', 'CRY_XRP': 'XRP-USD', 'CRY_BNB': 'BNB-USD', 'CRY_SOL': 'SOL-USD',   # zinc: COMEX future barely trades, no daily series
    'NIFTY50': '^NSEI', 'GLB_NIFTY50': '^NSEI',
    'SEC_BANK': '^NSEBANK', 'SEC_IT': '^CNXIT', 'SEC_FMCG': '^CNXFMCG', 'SEC_REALTY': '^CNXREALTY',
    'SEC_ENERGY': '^CNXENERGY', 'SEC_AUTO': '^CNXAUTO', 'SEC_PSUBANK': '^CNXPSUBANK', 'SEC_METAL': '^CNXMETAL',
    'SEC_PHARMA': '^CNXPHARMA', 'SEC_INFRA': '^CNXINFRA', 'SEC_CONSUMPTION': '^CNXCONSUM', 'SEC_NEXT50': '^NSMIDCP',
    'SEC_NIFTY500': '^CRSLDX', 'SEC_FINSERV': 'NIFTY_FIN_SERVICE.NS',
    'GLB_HSCEI': '^HSCE', 'GLB_JCI': '^JKSE', 'GLB_MOEX': 'IMOEX.ME', 'GLB_IBOV': '^BVSP', 'GLB_IPC': '^MXX',
    'GLB_TASI': '^TASI.SR', 'GLB_CSI300': '000300.SS', 'GLB_CAC40': '^FCHI', 'GLB_RUT': '^RUT', 'GLB_AEX': '^AEX',
    'GLB_ACWI': 'ACWI', 'GLB_NDX': '^NDX', 'GLB_ASX200': '^AXJO', 'GLB_SP500': '^GSPC', 'GLB_KOSPI': '^KS11',
    'GLB_FTSE100': '^FTSE', 'GLB_NIKKEI': '^N225', 'GLB_WIG20': 'WIG20.WA', 'GLB_BIST100': 'XU100.IS',
    'GLB_FTSEMIB': 'FTSEMIB.MI', 'GLB_DAX': '^GDAXI', 'GLB_IBEX35': '^IBEX', 'GLB_TSX': '^GSPTSE',
    'RE_EMBASSY': 'EMBASSY.NS', 'RE_MINDSPACE': 'MINDSPACE.NS', 'RE_BIRET': 'BIRET.NS', 'RE_NXST': 'NXST.NS',
    'RE_PGINVIT': 'PGINVIT.NS', 'RE_IRBINVIT': 'IRBINVIT.NS', 'RE_INDIGRID': 'INDIGRID.NS',
}
# No usable Yahoo history (checked 22-Nov-2026): Private Bank, Midcap 150, Smallcap 250,
# Midcap Select, CPSE, Defence, the factor indices, bonds, carry, SM-REITs, housing.


def stock_symbols():
    """Nifty stocks on the board plus the watchlist: STK_<NSE symbol> -> <symbol>.NS"""
    out = {}
    try:
        items = json.load(open(os.path.join(ROOT, 'data', 'signals.json')))['items']
        out = {i['id']: i['id'][4:] + '.NS' for i in items if i['id'].startswith('STK_')}
    except Exception:
        pass
    try:
        import csv
        for r in csv.DictReader(open(os.path.join(ROOT, 'models', 'stock-watchlist.csv'), encoding='utf-8-sig')):
            out['STK_' + r['Symbol']] = r['Symbol'] + '.NS'
    except Exception:
        pass
    return out


def fetch(symbol):
    url = ('https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(symbol, safe='')
           + '?range=10y&interval=1d')
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                res = json.load(r)['chart']['result'][0]
            ts, cl = res['timestamp'], res['indicators']['quote'][0]['close']
            rows = [(datetime.datetime.utcfromtimestamp(t).date().isoformat(), c) for t, c in zip(ts, cl) if c]
            if len(rows) < SPAN + 20:
                raise ValueError(f'only {len(rows)} daily closes')
            return rows
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def analyse(rows):
    dates = [d for d, _ in rows]
    px = [c for _, c in rows]
    k = 2 / (SPAN + 1)
    ema = [px[0]]
    for p in px[1:]:
        ema.append(p * k + ema[-1] * (1 - k))
    gap = [None] * len(px)
    for i in range(SPAN, len(px)):       # skip the warm-up period
        gap[i] = px[i] / ema[i] - 1

    # back-test: episodes with gap >= PARABOLIC
    eps, cur = [], None
    for i, g in enumerate(gap):
        if g is None or g < PARABOLIC:
            continue
        if cur and i - cur['last_i'] <= MERGE_DAYS:
            cur['last_i'] = i
            if g > cur['peak_gap']:
                cur.update(peak_gap=g, peak_i=i)
        else:
            cur = {'start_i': i, 'last_i': i, 'peak_gap': g, 'peak_i': i}
            eps.append(cur)
    episodes = []
    for e in eps:
        s = e['start_i']
        fwd = {h: (round(px[s + n] / px[s] - 1, 4) if s + n < len(px) else None) for h, n in HORIZONS.items()}
        window = px[s:s + 253]
        dd = round(min(window) / max(window[:window.index(min(window)) + 1]) - 1, 4) if len(window) > 1 else None
        episodes.append({'start': dates[s], 'end': dates[e['last_i']], 'peak_date': dates[e['peak_i']],
                         'peak_gap': round(e['peak_gap'], 4), 'ret_after': fwd, 'max_drawdown_12m': dd})

    # drawdown from the running high (backlog #20; display only)
    peak, peak_i, dd, worst, worst_i, longest, since_i = px[0], 0, [], 0.0, 0, 0, 0
    for i, p in enumerate(px):
        if p >= peak:
            peak, peak_i = p, i
        d = p / peak - 1
        dd.append(d)
        if d < worst:
            worst, worst_i = d, i
        days = (datetime.date.fromisoformat(dates[i]) - datetime.date.fromisoformat(dates[peak_i])).days
        longest = max(longest, days)
    now = dd[-1]
    hi_i = max(range(len(px)), key=lambda i: px[i])
    drawdown = {
        'now': round(now, 4),                                   # vs highest close in the window
        'high': round(px[hi_i], 4), 'high_date': dates[hi_i],
        'years_below_high': round((datetime.date.fromisoformat(dates[-1]) - datetime.date.fromisoformat(dates[hi_i])).days / 365.25, 2),
        'worst': round(worst, 4), 'worst_date': dates[worst_i],
        'longest_below_high_years': round(longest / 365.25, 2),
        'share_of_days_deeper': round(sum(1 for d in dd if d < now) / len(dd), 3),   # how unusual today's fall is
        'window_from': dates[0],
    }

    g = gap[-1]
    setup = price_setup(dates, px)
    status ='Parabolic' if g >= PARABOLIC else 'Stretched' if g >= STRETCHED else 'Normal'
    last_year = [x for x in gap[-252:] if x is not None]
    weekly = [[dates[i], round(gap[i], 4)] for i in range(len(gap) - 1, max(SPAN, len(gap) - 504) - 1, -5)][::-1]
    return {'asof': dates[-1], 'close': round(px[-1], 4), 'ema150': round(ema[-1], 4), 'gap': round(g, 4),
            'status': status, 'max_gap_1y': round(max(last_year), 4), 'min_gap_1y': round(min(last_year), 4),
            'history_from': dates[SPAN], 'episodes': episodes, 'gap_weekly_2y': weekly, 'drawdown': drawdown,
            'setup': setup}


# Value-opportunity setups (Indian equities, Bottom-up): how the price got where it is.
# Display only; never changes a score. Thresholds live here so the board and the notes agree.
SETUP_RULE = {
    'short': {'label': 'Short-term drawdown', 'days': 63, 'max_dd': -0.15,
              'text': 'fell 15% or more from its 3-month high'},
    'long': {'label': 'Long-term drawdown', 'days': 1260, 'max_dd': -0.30, 'min_years_below': 1.0,
             'text': '30% or more below its 5-year high, and that high is over a year old'},
    'consol': {'label': 'Consolidation', 'band': 0.25, 'min_days': 126,
               'text': 'has traded inside a 25% high-to-low band for 6 months or more'},
    # 5-year horizon: the price has gone nowhere for years. Judged against a bank deposit:
    # a price CAGR of 7% a year or less over the look-back (dividends not counted).
    'base': {'label': 'Multi-year base', 'max_cagr': 0.07, 'min_years': 5,
             'text': 'price has compounded 7% a year or less (about a fixed deposit) for 5 years or more'},
}


def price_setup(dates, px):
    """Short-term drawdown, long-term drawdown and consolidation readings for one price series."""
    R = SETUP_RULE
    n = len(px)
    def dd(days):
        w = px[-days:]
        return px[-1] / max(w) - 1
    def ret(days):
        return px[-1] / px[-days - 1] - 1 if n > days else None
    d3m = dd(R['short']['days'])
    w5 = px[-R['long']['days']:]
    hi5_i = n - len(w5) + max(range(len(w5)), key=lambda i: w5[i])
    d5y = px[-1] / px[hi5_i] - 1
    yrs5 = (datetime.date.fromisoformat(dates[-1]) - datetime.date.fromisoformat(dates[hi5_i])).days / 365.25
    # consolidation: longest window ending today whose high/low stays within the band
    hi = lo = px[-1]
    k = n - 1
    while k > 0:
        p = px[k - 1]
        nh, nl = max(hi, p), min(lo, p)
        if nh / nl - 1 > R['consol']['band']:
            break
        hi, lo, k = nh, nl, k - 1
    cdays = n - k
    # price CAGR over each look-back, and the longest look-back (in half years) that stayed at or under max_cagr
    d_last = datetime.date.fromisoformat(dates[-1])
    def cagr(years):
        target = d_last - datetime.timedelta(days=round(years * 365.25))
        if datetime.date.fromisoformat(dates[0]) > target + datetime.timedelta(days=10):
            return None
        j = next(i for i, d in enumerate(dates) if datetime.date.fromisoformat(d) >= target)
        return (px[-1] / px[j]) ** (1 / years) - 1
    cg = {str(y): cagr(y) for y in (3, 5, 7, 10)}
    flat = 0.0
    for h in range(2, 21):
        c = cagr(h / 2)
        if c is None:
            break
        if c <= R['base']['max_cagr']:
            flat = h / 2
    types = []
    if d3m <= R['short']['max_dd']:
        types.append('short')
    if d5y <= R['long']['max_dd'] and yrs5 >= R['long']['min_years_below']:
        types.append('long')
    if cdays >= R['consol']['min_days']:
        types.append('consol')
    if flat >= R['base']['min_years']:
        types.append('base')
    return {'types': types,
            'dd_3m': round(d3m, 4), 'dd_1y': round(dd(252), 4), 'dd_5y': round(d5y, 4),
            'high_5y_date': dates[hi5_i], 'years_below_5y_high': round(yrs5, 2),
            'ret_1m': None if ret(21) is None else round(ret(21), 4),
            'ret_3m': None if ret(63) is None else round(ret(63), 4),
            'consol_days': cdays, 'consol_months': round(cdays / 21, 1),
            'consol_range': round(hi / lo - 1, 4), 'consol_from': dates[k],
            'cagr': {k: None if v is None else round(v, 4) for k, v in cg.items()},
            'flat_years': flat, 'history_years': round((d_last - datetime.date.fromisoformat(dates[0])).days / 365.25, 1),
            'pos_in_range': round((px[-1] - lo) / (hi - lo), 3) if hi > lo else 0.5}


def summarise(items):
    """Pool every past episode: how prices did after the rule fired."""
    eps = [e for it in items.values() for e in it.get('episodes', [])]
    out = {'episodes': len(eps), 'assets_with_episodes': sum(1 for it in items.values() if it.get('episodes'))}
    for h in HORIZONS:
        r = sorted(e['ret_after'][h] for e in eps if e['ret_after'][h] is not None)
        if r:
            out[h] = {'n': len(r), 'median': round(r[len(r) // 2], 4),
                      'share_lower': round(sum(1 for x in r if x < 0) / len(r), 3)}
    return out


def main():
    old = {}
    if os.path.exists(OUT):
        try:
            old = json.load(open(OUT)).get('items', {})
        except Exception:
            old = {}
    symbols = dict(SYMBOLS, **stock_symbols())

    def one(kv):
        iid, sym = kv
        try:
            return iid, dict(analyse(fetch(sym)), symbol=sym)
        except Exception as e:
            if iid in old:
                return iid, dict(old[iid], note=f'fetch failed ({type(e).__name__}); kept previous reading')
            return iid, {'symbol': sym, 'error': f'{type(e).__name__}: {e}'[:120]}

    with ThreadPoolExecutor(max_workers=6) as ex:
        items = dict(ex.map(one, sorted(symbols.items())))
    good = {k: v for k, v in items.items() if 'gap' in v}
    out = {'built_at': NOW,
           'rule': {'ema_days': SPAN, 'parabolic_gap': PARABOLIC, 'stretched_gap': STRETCHED,
                    'source': 'knowledge/sector-rotation-7-indian-bull-runs.md', 'affects_scores': False},
           'setup_rule': SETUP_RULE,
           'summary': dict(summarise(good), covered=len(good), failed=sorted(k for k in items if k not in good),
                           parabolic_now=sorted(k for k, v in good.items() if v['status'] == 'Parabolic'),
                           stretched_now=sorted(k for k, v in good.items() if v['status'] == 'Stretched')),
           'items': items}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), allow_nan=False)
    s = out['summary']
    print(f"parabolic check: {s['covered']} assets, {s['episodes']} past episodes; "
          f"parabolic now {s['parabolic_now']}, stretched now {s['stretched_now']}, failed {s['failed']}")


if __name__ == '__main__':
    main()
