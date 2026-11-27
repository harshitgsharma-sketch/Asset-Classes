"""Mutual fund lookup: map every open-ended Indian mutual fund and ETF to the board reading that
best describes what it holds, so a fund can be added to My portfolio and pick up a score.

Source: AMFI's daily NAV file (all schemes, with their SEBI category). Each scheme is matched by
name first (index funds, ETFs, sector and overseas funds: "Nifty Bank", "Nasdaq 100", "Gold"...),
then by category (Mid Cap Fund -> Nifty Midcap 150, Gilt -> 10-yr G-sec...). Hybrid funds, solution
funds and anything unmatched are left out. Plans and options are merged into one entry per fund.

Writes data/funds.json: [[fund name, AMC, category, board item id, basis], ...]. Best effort:
keeps the previous file if AMFI cannot be reached. Standard library only.
"""
import json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'funds.json')
URL = 'https://portal.amfiindia.com/spages/NAVAll.txt'

# name rules, most specific first: (regex on the lower-case name, item id)
NAME = [
    (r'\bsilver\b', 'CMD_SILVER'), (r'\bgold\b', 'GOLD'),
    (r'nasdaq', 'GLB_NDX'), (r's&p 500|us (equity|bluechip|specific)|u\.s\.|american|nyse fang', 'GLB_SP500'),
    (r'japan|nikkei', 'GLB_NIKKEI'), (r'china|hang seng', 'GLB_HSCEI'), (r'brazil', 'GLB_IBOV'), (r'taiwan|korea', 'GLB_KOSPI'),
    (r'europe', 'GLB_DAX'),
    (r'psu bank', 'SEC_PSUBANK'), (r'private bank', 'SEC_PVTBANK'), (r'\bcpse\b|\bpsu\b|public sector', 'SEC_CPSE'),
    (r'defen[cs]e', 'SEC_DEFENCE'), (r'next 50|junior', 'SEC_NEXT50'),
    (r'midcap 150|mid ?cap 150', 'SEC_MIDCAP150'), (r'midcap select', 'SEC_MIDSELECT'), (r'smallcap 250|small ?cap 250', 'SEC_SMALLCAP250'),
    (r'nifty 500|nifty500|bse 500', 'SEC_NIFTY500'),
    (r'financial services|\bfinancial\b|\bbfsi\b', 'SEC_FINSERV'),
    (r'\bbank(ing)?\b(?!.*(psu|debt|bond|corporate))', 'SEC_BANK'),
    (r'pharma|health ?care|healthcare', 'SEC_PHARMA'), (r'technology|\bit\b|digital|tech\b', 'SEC_IT'),
    (r'fmcg', 'SEC_FMCG'), (r'consumption|consumer', 'SEC_CONSUMPTION'), (r'infra', 'SEC_INFRA'),
    (r'\bauto\b|automotive|mobility', 'SEC_AUTO'), (r'energy|power|oil', 'SEC_ENERGY'), (r'metal|commodit', 'SEC_METAL'),
    (r'realty|real estate|housing', 'SEC_REALTY'),
    (r'nifty 50\b|nifty50|sensex|nifty 100\b|bse 100\b', 'NIFTY50'),
]
# category rules: (substring of the AMFI category, item id); None = leave out
CAT = [
    ('Arbitrage', 'CRY_ARBITRAGE'), ('Hybrid', None), ('Solution', None), ('Children', None), ('Retirement', None),
    ('Overnight', 'FI_SHORT_1Y'), ('Liquid', 'FI_SHORT_1Y'), ('Money Market', 'FI_SHORT_1Y'), ('Ultra Short', 'FI_SHORT_1Y'),
    ('Low Duration', 'FI_SHORT_1Y'), ('Floater', 'FI_SHORT_1Y'),
    ('Gilt Fund with 10 year', 'FI_GSEC_10Y'), ('Gilt', 'FI_GSEC_10Y'), ('Long Duration', 'FI_GSEC_10Y'), ('Dynamic Bond', 'FI_GSEC_10Y'),
    ('Medium to Long', 'FI_GSEC_10Y'), ('Credit Risk', 'FI_CREDIT_AA_3Y'), ('Medium Duration', 'FI_CREDIT_AA_3Y'),
    ('Corporate Bond', 'FI_CORP_AAA_5Y'), ('Banking and PSU', 'FI_CORP_AAA_5Y'), ('Short Duration', 'FI_CORP_AAA_5Y'),
    ('Debt ETF', 'FI_GSEC_5Y'), ('Index Funds', None), ('Debt Scheme', 'FI_CORP_AAA_5Y'),
    ('Large & Mid', 'SEC_NIFTY500'), ('Large Cap', 'NIFTY50'), ('Mid Cap', 'SEC_MIDCAP150'), ('Small Cap', 'SEC_SMALLCAP250'), ('Flexi', 'SEC_NIFTY500'), ('Multi Cap', 'SEC_NIFTY500'), ('Focused', 'SEC_NIFTY500'),
    ('ELSS', 'SEC_NIFTY500'), ('Contra', 'SEC_NIFTY500'), ('Value', 'SEC_NIFTY500'), ('Dividend Yield', 'SEC_NIFTY500'),
    ('overseas', 'GLB_ACWI'), ('Gold', 'GOLD'), ('Silver', 'CMD_SILVER'),
]
DEBT_CAT = ('Debt', 'Gilt', 'Liquid', 'Overnight', 'Money Market', 'Arbitrage')
STRIP = re.compile(r'\s*[-–(]?\s*(direct|regular)\b.*$|\s*-\s*(growth|idcw|dividend|bonus).*$', re.I)


def match(name, cat):
    low = name.lower()
    if not any(c in cat for c in DEBT_CAT):
        for rx, iid in NAME:
            if re.search(rx, low):
                return iid, 'name'
    for key, iid in CAT:
        if key.lower() in cat.lower():
            return iid, 'category'
    return None, None


def main():
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (entry-exit-board fund lookup)'})
        text = urllib.request.urlopen(req, timeout=60).read().decode('utf-8', 'replace')
    except Exception as e:
        print(f'WARN funds: {type(e).__name__}: {e}; keeping the previous file'); return
    cat = amc = None; seen = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('Open Ended Schemes') or line.startswith('Close Ended') or line.startswith('Interval Fund'):
            cat = line if line.startswith('Open Ended') else None; continue
        if ';' not in line:
            amc = line; continue
        if not cat or line.startswith('Scheme Code'):
            continue
        parts = line.split(';')
        if len(parts) < 4:
            continue
        name = STRIP.sub('', parts[3]).strip(' -')
        name = re.sub(r'\s+', ' ', name)
        c = cat[cat.find('(') + 1:].rstrip(')')
        if name.lower() in seen:
            continue
        iid, basis = match(name, c)
        if iid:
            seen[name.lower()] = [name, re.sub(r'\s*Mutual Fund$', '', amc or ''), c.split(' - ')[-1], iid, basis]
    rows = sorted(seen.values(), key=lambda r: r[0].lower())
    if len(rows) < 300:
        print(f'WARN funds: only {len(rows)} matched; keeping the previous file'); return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    by = {}
    for r in rows:
        by[r[3]] = by.get(r[3], 0) + 1
    print(f'funds: {len(rows)} funds mapped;', dict(sorted(by.items(), key=lambda x: -x[1])[:12]))


if __name__ == '__main__':
    main()
