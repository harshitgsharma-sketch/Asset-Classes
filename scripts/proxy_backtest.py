"""Price-proxy back-test for the sectors and global-markets models.

Those two models have no score history, and their valuation inputs (P/E, CAPE, ERP) have no free
10-year history, so they cannot be back-tested whole. What can be tested is the part of each model
that is computed from price alone, using the same indicators, anchors and weights as the model:

  Sectors (models/sector_oscillator.py), relative to the Nifty 50:
    C8   1-yr return minus Nifty 50 (pp)            cheap -25, rich +25   weight 3x4x0.875x1.0
    C16  5-yr return minus Nifty 50 (pp/yr)         cheap -10, rich +10   weight 2x3x0.75x1.0
    tested against the sector's return minus the Nifty 50's over the next 12 months.
  Global markets (models/global_oscillator.py), local-currency index prices:
    T1   index / 200-day MA                         cheap 0.88, rich 1.15  weight 3x5x1x1
    T4   1-yr return minus ACWI (pp)                cheap +20, rich -20    weight 3x4x0.875x1
    T5   monthly RSI(14)                            cheap 35, rich 80      weight 2x4x0.75x1
    F1   index / 200-week MA                        cheap 0.95, rich 1.60  weight 2x4x1x1
    F4   3-yr CAGR minus ACWI (pp/yr)               cheap -10, rich +10    weight 2x3x0.75x1
    tested against the index's own return over the next 12 months.

Called from fetch_parabolic.py with the daily closes it already downloads. Writes
data/proxy_backtest.json. Display only. Standard library only.
"""
import json, os, statistics, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'proxy_backtest.json')
BANDS = [('Strong buy', 20), ('Buy', 35), ('Accumulate', 50), ('Hold', 65), ('Trim', 80), ('Exit', 101)]
SECTOR = {'C8': (-25, 25, 3 * 4 * .875), 'C16': (-10, 10, 2 * 3 * .75)}
GLOBAL = {'T1': (.88, 1.15, 15), 'T4': (20, -20, 3 * 4 * .875), 'T5': (35, 80, 6), 'F1': (.95, 1.60, 8), 'F4': (-10, 10, 4.5)}
H = 12


def band(s):
    return next(b for b, top in BANDS if s <= top)


def ind(x, cheap, rich):
    return max(1.0, min(100.0, 1 + 99 * (x - cheap) / (rich - cheap)))


def score(vals, spec):
    num = den = 0.0
    for k, (c, r, w) in spec.items():
        if vals.get(k) is not None:
            num += w * ind(vals[k], c, r); den += w
    return num / den if den and len([1 for k in spec if vals.get(k) is not None]) >= max(1, len(spec) - 2) else None


def monthly(rows):
    """[(date, close)] daily -> ordered [(yyyy-mm, close, index of that day in rows)] month-end."""
    out = {}
    for k, (d, c) in enumerate(rows):
        out[d[:7]] = (c, k)
    return [(m, c, k) for m, (c, k) in sorted(out.items())]


def ma(rows, k, n):
    if k + 1 < n:
        return None
    return sum(c for _, c in rows[k + 1 - n:k + 1]) / n


def rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    up = dn = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        d = b - a
        up += max(d, 0); dn += max(-d, 0)
    return 100.0 if dn == 0 else 100 - 100 / (1 + up / dn)


def ret(mm, j, back):
    return mm[j][1] / mm[j - back][1] - 1 if j - back >= 0 else None


def summ(obs):
    out = []
    for b, _ in BANDS:
        r = sorted(x for bb, x in obs if bb == b)
        if not r:
            out.append({'band': b, 'n': 0}); continue
        out.append({'band': b, 'n': len(r), 'median': round(statistics.median(r), 4), 'hit': round(sum(x > 0 for x in r) / len(r), 3)})
    return out


def run(hist):
    """hist: {item id: [(date, close), ...]} daily closes."""
    res = {'built_at': datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(), 'horizon_months': H}
    nifty, acwi = hist.get('NIFTY50'), hist.get('GLB_ACWI')
    # sectors, relative to Nifty 50
    if nifty:
        nm = {m: c for m, c, _ in monthly(nifty)}
        obs, per, now = [], {}, {}
        for iid, rows in hist.items():
            if not iid.startswith('SEC_'):
                continue
            mm = [x for x in monthly(rows) if x[0] in nm]
            o = []
            for j in range(len(mm)):
                m = mm[j][0]
                r1, r5 = ret(mm, j, 12), ret(mm, j, 60)
                n1 = nm[m] / nm[mm[j - 12][0]] - 1 if j >= 12 else None
                n5 = nm[m] / nm[mm[j - 60][0]] - 1 if j >= 60 else None
                v = {'C8': None if r1 is None else 100 * (r1 - n1),
                     'C16': None if r5 is None else 100 * ((1 + r5) ** .2 - (1 + n5) ** .2)}
                s = score(v, SECTOR)
                if s is None:
                    continue
                if j == len(mm) - 1:
                    now[iid] = round(s, 1)
                if j + H < len(mm):
                    f = mm[j + H][1] / mm[j][1] - nm[mm[j + H][0]] / nm[m]
                    o.append((band(s), f))
            obs += o; per[iid] = summ(o)
        res['sectors'] = {'measure': 'return minus Nifty 50 over the next 12 months', 'by_band': summ(obs), 'n': len(obs),
                          'indices': len(per), 'per_item': per, 'proxy_now': now}
    # global markets, own return
    if acwi:
        am = {m: c for m, c, _ in monthly(acwi)}
        obs, per, now = [], {}, {}
        for iid, rows in hist.items():
            if not iid.startswith('GLB_') or iid == 'GLB_NIFTY50':
                continue
            mm = monthly(rows); closes = [c for _, c, _ in mm]
            o = []
            for j in range(len(mm)):
                m, c, k = mm[j]
                r1, r3 = ret(mm, j, 12), ret(mm, j, 36)
                a1 = am[m] / am[mm[j - 12][0]] - 1 if j >= 12 and m in am and mm[j - 12][0] in am else None
                a3 = am[m] / am[mm[j - 36][0]] - 1 if j >= 36 and m in am and mm[j - 36][0] in am else None
                m200, m1000 = ma(rows, k, 200), ma(rows, k, 1000)
                v = {'T1': c / m200 if m200 else None, 'F1': c / m1000 if m1000 else None, 'T5': rsi(closes[:j + 1]),
                     'T4': None if r1 is None or a1 is None else 100 * (r1 - a1),
                     'F4': None if r3 is None or a3 is None else 100 * ((1 + r3) ** (1 / 3) - (1 + a3) ** (1 / 3))}
                s = score(v, GLOBAL)
                if s is None:
                    continue
                if j == len(mm) - 1:
                    now[iid] = round(s, 1)
                if j + H < len(mm):
                    o.append((band(s), mm[j + H][1] / c - 1))
            obs += o; per[iid] = summ(o)
        res['global'] = {'measure': 'index return in local currency over the next 12 months', 'by_band': summ(obs), 'n': len(obs),
                         'indices': len(per), 'per_item': per, 'proxy_now': now}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, 'w'), separators=(',', ':'))
    for k in ('sectors', 'global'):
        if k in res:
            print(f"proxy back-test {k}: {res[k]['n']} months over {res[k]['indices']} indices",
                  [(r['band'], r.get('n'), r.get('median')) for r in res[k]['by_band']])
    return res
