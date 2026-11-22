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
    """Nifty stocks on the board: STK_<NSE symbol> -> <symbol>.NS"""
    p = os.path.join(ROOT, 'data', 'signals.json')
    try:
        items = json.load(open(p))['items']
    except Exception:
        return {}
    return {i['id']: i['id'][4:] + '.NS' for i in items if i['id'].startswith('STK_')}


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
    status ='Parabolic' if g >= PARABOLIC else 'Stretched' if g >= STRETCHED else 'Normal'
    last_year = [x for x in gap[-252:] if x is not None]
    weekly = [[dates[i], round(gap[i], 4)] for i in range(len(gap) - 1, max(SPAN, len(gap) - 504) - 1, -5)][::-1]
    return {'asof': dates[-1], 'close': round(px[-1], 4), 'ema150': round(ema[-1], 4), 'gap': round(g, 4),
            'status': status, 'max_gap_1y': round(max(last_year), 4), 'min_gap_1y': round(min(last_year), 4),
            'history_from': dates[SPAN], 'episodes': episodes, 'gap_weekly_2y': weekly, 'drawdown': drawdown}


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
