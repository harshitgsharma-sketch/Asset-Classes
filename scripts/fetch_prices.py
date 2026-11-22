"""Fetch the latest market prices the page compares against the last scoring run.

Runs in the GitHub Action (server side, so no browser CORS limits). Every source is
best-effort: if one fails, the previous value is kept and marked with its old date.
Writes data/prices.json. Standard library only.
"""
import json, os, urllib.request, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'prices.json')
UA = {'User-Agent': 'Mozilla/5.0 (entry-exit-board price refresh)'}
NOW = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def yahoo(symbol, scale=1.0):
    j = get(f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=1d')
    meta = j['chart']['result'][0]['meta']
    return round(meta['regularMarketPrice'] * scale, 2), 'Yahoo Finance ' + symbol

def frankfurter_inr():
    j = get('https://api.frankfurter.app/latest?from=USD&to=INR')
    return round(j['rates']['INR'], 3), 'ECB reference rate (frankfurter.app)'

def coingecko_btc():
    j = get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
    return float(j['bitcoin']['usd']), 'CoinGecko'

SOURCES = {  # key: list of fetchers tried in order
    'gold_usd':     [lambda: yahoo('GC%3DF')],
    'silver_usd':   [lambda: yahoo('SI%3DF')],
    'brent_usd':    [lambda: yahoo('BZ%3DF')],
    'copper_usd_t': [lambda: yahoo('HG%3DF', 2204.62)],   # USD/lb -> USD/tonne
    'btc_usd':      [coingecko_btc, lambda: yahoo('BTC-USD')],
    'usdinr':       [frankfurter_inr, lambda: yahoo('INR%3DX')],
    'nifty':        [lambda: yahoo('%5ENSEI')],
}

def main():
    old = {}
    if os.path.exists(OUT):
        try: old = json.load(open(OUT)).get('values', {})
        except Exception: old = {}
    values = {}
    for key, fetchers in SOURCES.items():
        for f in fetchers:
            try:
                v, src = f()
                values[key] = {'value': v, 'source': src, 'at': NOW}
                break
            except Exception as e:
                last_err = f'{type(e).__name__}: {e}'
        else:
            if key in old:
                values[key] = dict(old[key], note='fetch failed; kept previous value')
            print(f'WARN {key}: {last_err}')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({'fetched_at': NOW, 'values': values}, open(OUT, 'w'), indent=1)
    print('prices:', {k: v['value'] for k, v in values.items()})

if __name__ == '__main__':
    main()
    # Daily parabolic-move check (data/parabolic.json). Run from here so the refresh
    # Action picks it up without a workflow change. Best effort: never fails the step.
    # Also the AMFI thematic-fund froth history (models/amfi-thematic-monthly.csv, sectors
    # model S4). Only new months are downloaded, so on most days this does nothing; the
    # sectors model picks up a new month on the next run.
    import subprocess, sys
    for script in ('fetch_parabolic.py', 'fetch_amfi_thematic.py'):
        try:
            subprocess.run([sys.executable, '-I', os.path.join(ROOT, 'scripts', script)], timeout=600)
        except Exception as e:
            print(f'WARN {script}: {type(e).__name__}: {e}')
