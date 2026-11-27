"""Provisional scores: the same models, re-scored at today's prices between monthly runs.

The official score is set on the monthly run. Every day, this script takes each model's current
month of inputs, swaps in the latest prices from data/prices.json, moves the price-driven
indicators by as much as the new price moves them (distance from high, price vs moving averages,
RSI, ratios to gold or Brent...), and scores the row with the model's own scoring function.
Everything researched by hand (valuations, rates, flows, PMIs) stays as set on the monthly run.

Covers the readings whose prices are fetched daily: gold, the Nifty 50, Bitcoin, silver, Brent
and copper. Writes data/provisional.json; build_signals.py attaches it to the items.
Display only: it never replaces the official score.
"""
import json, os, sys
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, 'models')
OUT = os.path.join(ROOT, 'data', 'provisional.json')


def live_prices():
    p = json.load(open(os.path.join(ROOT, 'data', 'prices.json')))
    return p.get('fetched_at'), {k: v['value'] for k, v in p.get('values', {}).items() if v.get('value') is not None}


def rescore_filled(mod, price_map, live):
    """Engines whose price-driven indicators are filled by fill_derived() only where blank.
    For each indicator: new = hand value (or derived value) + (derived at live price - derived at
    the run price). So a hand-sourced level is kept and only moved by the price change."""
    raw = pd.read_csv(mod.INPUTS, dtype={'month': str})
    have = raw[mod.COLS].notna().sum(axis=1) >= getattr(mod, 'MIN_INPUTS', 1)
    last = raw[have].index[-1]
    orig = mod.fill_derived(raw.copy()).loc[last]
    cleared = raw.copy(); cleared.loc[last, mod.COLS] = np.nan
    d0 = mod.fill_derived(cleared.copy()).loc[last]
    moved = cleared.copy()
    used = {}
    for col, key in price_map.items():
        if key in live and col in moved and pd.notna(raw.loc[last, col]):
            moved.loc[last, col] = live[key]; used[col] = [float(raw.loc[last, col]), live[key]]
    d1 = mod.fill_derived(moved.copy()).loc[last]
    row = orig.to_dict()
    changed = []
    for c in mod.COLS:
        a, b = d0.get(c), d1.get(c)
        if pd.notna(a) and pd.notna(b) and abs(float(b) - float(a)) > 1e-9:
            base = orig.get(c) if pd.notna(orig.get(c)) else a
            row[c] = float(base) + float(b) - float(a); changed.append(c)
    for col, (_, v) in used.items():
        row[col] = v
    official = mod.score_row(orig.to_dict())
    prov = mod.score_row(row)
    return raw.loc[last, 'month'], official, prov, used, changed


def gold_like(name, item, price_map, live, bucket_names=('Valuation', 'Timing', 'Filter')):
    sys.path.insert(0, M)
    mod = __import__(name)
    month, off, prov, used, changed = rescore_filled(mod, price_map, live)
    return item, {
        'month': month, 'official_recomputed': round(off['Oscillator'], 1), 'score': round(prov['Oscillator'], 1),
        'buckets': {b: (None if pd.isna(prov.get(b)) else round(prov[b], 1)) for b in bucket_names},
        'prices': used, 'indicators_moved': len(changed)}


def commodities(live):
    sys.path.insert(0, M)
    import commodities_oscillator as co
    cfg = json.load(open(co.CONFIG))
    raw = pd.read_csv(co.INPUTS, dtype={'month': str})
    last = raw.index[-1]
    base = co.add_derived(raw.copy(), cfg).loc[last].to_dict()
    moved = raw.copy(); used = {}
    for col in ('silver_usd', 'gold_usd', 'brent_usd', 'copper_usd_t', 'usdinr'):
        if col in live and pd.notna(raw.loc[last, col]):
            moved.loc[last, col] = live[col]; used[col] = [float(raw.loc[last, col]), live[col]]
    row = co.add_derived(moved, cfg).loc[last].to_dict()
    out = {}
    for c in cfg['commodities']:
        if c['key'] not in ('SILVER', 'BRENT', 'COPPER'):
            continue
        s0, s1 = co.score_row(c, base), co.score_row(c, row)
        if not s0 or not s1:
            continue
        out['CMD_' + c['key']] = {
            'month': raw.loc[last, 'month'], 'official_recomputed': round(s0['Oscillator'], 1), 'score': round(s1['Oscillator'], 1),
            'buckets': {b: round(v, 1) for b, v in s1['buckets'].items()},
            'prices': {k: v for k, v in used.items() if k in (c['price_col'], 'usdinr', 'gold_usd')}, 'indicators_moved': None}
    return out


def main():
    at, live = live_prices()
    cwd = os.getcwd(); os.chdir(M)
    items = {}
    jobs = [
        ('gold_oscillator', 'GOLD', {'gold_usd': 'gold_usd', 'silver_usd': 'silver_usd', 'brent_usd': 'brent_usd', 'usdinr': 'usdinr'}),
        ('nifty_oscillator', 'NIFTY50', {'nifty': 'nifty', 'gold_usd': 'gold_usd', 'usdinr': 'usdinr', 'brent_usd': 'brent_usd'}),
        ('btc_oscillator', 'BTC', {'btc_usd': 'btc_usd', 'usdinr': 'usdinr'}),
    ]
    for name, item, pm in jobs:
        try:
            k, v = gold_like(name, item, pm, live); items[k] = v
        except Exception as e:
            print(f'WARN {item}: {type(e).__name__}: {e}')
    try:
        items.update(commodities(live))
    except Exception as e:
        print(f'WARN commodities: {type(e).__name__}: {e}')
    os.chdir(cwd)
    json.dump({'prices_at': at, 'items': items}, open(OUT, 'w'), indent=1)
    for k, v in items.items():
        print(f"{k:12} official(recomputed) {v['official_recomputed']:>5} -> provisional {v['score']:>5}  {v['prices']}")


if __name__ == '__main__':
    main()
