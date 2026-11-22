"""Thematic-fund froth from AMFI monthly reports (backlog item 17).

For each month since Apr 2019, reads AMFI's monthly report
(https://portal.amfiindia.com/spages/am<mon><year>repo.xls), open-ended equity
section only, and records:
  - sectoral/thematic net inflow, AUM and number of schemes (the category was split
    into "Sectoral Fund" and "Thematic Fund" in 2025; both are summed)
  - total open-ended equity net inflow and AUM
Derived monthly measures:
  - flow_3m_pct_aum: 3-month sum of sectoral/thematic net inflow / equity AUM, in %
  - share_3m: sectoral/thematic share of equity net inflow, 3-month sums
  - new_schemes_6m: rise in the number of sectoral/thematic schemes over 6 months
    (a proxy for NFO launches; mergers and closures net out)
  - aum_share: sectoral/thematic AUM / equity AUM
Writes models/amfi-thematic-monthly.csv. Only new months are downloaded; earlier
rows are kept. Needs pandas plus xlrd (old .xls) or openpyxl.

Run: python3 -I scripts/fetch_amfi_thematic.py
"""
import csv, datetime, io, os, re, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'models', 'amfi-thematic-monthly.csv')
UA = {'User-Agent': 'Mozilla/5.0 (entry-exit-board AMFI fetch)'}
MON = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
START = (2019, 4)
FIELDS = ['month', 'them_net_cr', 'them_aum_cr', 'them_schemes', 'eq_net_cr', 'eq_aum_cr',
          'flow_3m_pct_aum', 'share_3m', 'new_schemes_6m', 'aum_share']


def xlsx_rows(raw):
    """First worksheet of an .xlsx as rows of strings, standard library only ('nan' = empty)."""
    import zipfile, xml.etree.ElementTree as ET
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    z = zipfile.ZipFile(io.BytesIO(raw))
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
    sheet = sorted(n for n in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n))[0]
    grid = {}
    for c in ET.fromstring(z.read(sheet)).iter('{%s}c' % ns['m']):
        ref = c.get('r'); col_s = re.match(r'[A-Z]+', ref).group(); row = int(ref[len(col_s):]) - 1
        col = 0
        for ch in col_s:
            col = col * 26 + ord(ch) - 64
        v = c.find('m:v', ns); t = c.get('t')
        if t == 'inlineStr':
            val = ''.join(x.text or '' for x in c.iter('{%s}t' % ns['m']))
        elif v is None:
            continue
        else:
            val = shared[int(v.text)] if t == 's' else v.text
        grid.setdefault(row, {})[col - 1] = (val or '').strip()
    width = max((max(r) for r in grid.values() if r), default=0) + 1
    return [[grid.get(i, {}).get(j, 'nan') or 'nan' for j in range(width)] for i in range(max(grid) + 1)]


def parse(raw):
    if raw[:2] == b'PK':                       # .xlsx (every month since mid-2020)
        rows = xlsx_rows(raw)
    else:                                       # legacy .xls: needs pandas + xlrd
        import pandas as pd
        x = pd.read_excel(io.BytesIO(raw), header=None)
        rows = [[str(v).strip() for v in r] for r in x.values.tolist()]
    # open-ended section A: from the first "Growth/Equity" header to the next "Sub Total"
    start = next(i for i, r in enumerate(rows) if re.search(r'growth/equity|^II equity schemes', ' '.join(r[:2]).replace('nan', '').strip(), re.I))
    end = next(i for i in range(start + 1, len(rows)) if re.search(r'sub ?total', ' '.join(rows[i][:2]), re.I))
    hdr = next(r for r in rows[:15] if any('Net Inflow' in c for c in r))
    ci = {k: next(j for j, c in enumerate(hdr) if re.search(p, c, re.I)) for k, p in
          [('n', r'No\. of Schemes'), ('net', r'Net Inflow'), ('aum', r'^(Net Assets|AUM)')]}
    num = lambda r, k: float(r[ci[k]]) if r[ci[k]] not in ('nan', '') else 0.0
    them = [r for r in rows[start + 1:end] if re.search(r'sectoral|thematic', ' '.join(r[:3]), re.I)]
    if not them:
        raise ValueError('no sectoral/thematic row')
    tot = rows[end]
    return {'them_net_cr': sum(num(r, 'net') for r in them), 'them_aum_cr': sum(num(r, 'aum') for r in them),
            'them_schemes': sum(num(r, 'n') for r in them), 'eq_net_cr': num(tot, 'net'), 'eq_aum_cr': num(tot, 'aum')}


def months():
    y, m = START
    today = datetime.date.today()
    while (y, m) <= (today.year, today.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    have = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT)):
            have[r['month']] = r
    rows = {}
    for y, m in months():
        key = f'{y}-{m:02d}'
        if key in have and have[key].get('them_net_cr'):
            rows[key] = {k: float(have[key][k]) for k in ['them_net_cr', 'them_aum_cr', 'them_schemes', 'eq_net_cr', 'eq_aum_cr']}
            continue
        url = f'https://portal.amfiindia.com/spages/am{MON[m - 1]}{y}repo.xls'
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                rows[key] = parse(r.read())
        except Exception as e:
            print(f'skip {key}: {type(e).__name__}: {str(e)[:80]}')
    keys = sorted(rows)
    out = []
    for i, k in enumerate(keys):
        r = dict(rows[k], month=k)
        last3 = [rows[keys[j]] for j in range(max(0, i - 2), i + 1)]
        if len(last3) == 3:
            tn, en = sum(x['them_net_cr'] for x in last3), sum(x['eq_net_cr'] for x in last3)
            r['flow_3m_pct_aum'] = round(100 * tn / r['eq_aum_cr'], 3)
            r['share_3m'] = round(tn / en, 3) if en > 0 else ''
        if i >= 6:
            r['new_schemes_6m'] = int(r['them_schemes'] - rows[keys[i - 6]]['them_schemes'])
        r['aum_share'] = round(r['them_aum_cr'] / r['eq_aum_cr'], 4)
        for f in ['them_net_cr', 'them_aum_cr', 'eq_net_cr', 'eq_aum_cr']:
            r[f] = round(r[f], 1)
        r['them_schemes'] = int(r['them_schemes'])
        out.append(r)
    with open(OUT, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in out:
            w.writerow({k: r.get(k, '') for k in FIELDS})
    last = out[-1]
    print(f"amfi thematic: {len(out)} months to {last['month']}; flow_3m_pct_aum {last.get('flow_3m_pct_aum')}, "
          f"share_3m {last.get('share_3m')}, new_schemes_6m {last.get('new_schemes_6m')}, aum_share {last['aum_share']}")


if __name__ == '__main__':
    main()
