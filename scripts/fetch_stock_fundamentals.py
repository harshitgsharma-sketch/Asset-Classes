"""Fill the stock screener's inputs for the Nifty 500 from Yahoo Finance (via yfinance).

Runs in the GitHub Action (the Claude session's shell cannot reach Yahoo or NSE).
For the month of --asof it:
  1. downloads NSE's Nifty 500 constituent list (models/nifty500-constituents.csv),
  2. for every constituent with no row yet for that month (or all, with --overwrite),
     pulls price history, ratios, annual EPS / net income / equity / debt,
  3. appends rows to models/nifty500-stocks-inputs-monthly.csv in the engine's format,
     with name / sector / sector_index / type so the engine can score stocks that are not
     hand-configured in nifty500-stocks-config.json.
Rows already in the CSV for the month (the 50 Nifty 50 stocks sourced from screener.in) are
kept unless --overwrite. Price returns end at the last close on or before --asof, so they line
up with the NIFTY50 benchmark row. Best effort: a ticker that fails is skipped and listed.

Usage: python3 scripts/fetch_stock_fundamentals.py --asof 2026-11-20 [--overwrite] [--limit N]
"""
import argparse, csv, io, os, sys, time, datetime, math, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M = os.path.join(ROOT, "models")
INPUTS = os.path.join(M, "nifty500-stocks-inputs-monthly.csv")
CONST = os.path.join(M, "nifty500-constituents.csv")
LIST_URLS = ["https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
             "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
             "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept": "text/csv,*/*", "Referer": "https://www.niftyindices.com/"}
COLS = ["month", "ticker", "source", "price", "pe", "bv", "roe", "roe5", "roe3", "pg5", "pg_ttm", "px1", "px3", "px5",
        "eps_hist", "debt", "equity", "hi52", "lo52", "pe_med5", "gsec10", "name", "sector", "sector_index", "type"]

PSU_BANKS = {"SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDIANB", "BANKINDIA", "MAHABANK", "UCOBANK",
             "CENTRALBK", "IOB", "PSB"}
# NSE "Industry" (macro sector) -> sector index row in nifty-sectors-inputs-monthly.csv
SECTOR_INDEX = {
    "Information Technology": "IT", "Fast Moving Consumer Goods": "FMCG", "Healthcare": "PHARMA",
    "Automobile and Auto Components": "AUTO", "Metals & Mining": "METAL", "Oil Gas & Consumable Fuels": "ENERGY",
    "Power": "ENERGY", "Realty": "REALTY", "Capital Goods": "INFRA", "Construction": "INFRA",
    "Construction Materials": "INFRA", "Telecommunication": "INFRA", "Services": "INFRA",
    "Consumer Durables": "CONSUMPTION", "Consumer Services": "CONSUMPTION", "Textiles": "CONSUMPTION",
    "Media Entertainment & Publication": "CONSUMPTION", "Financial Services": "FINSERV",
}

def get_list():
    last = None
    for u in LIST_URLS:
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                txt = r.read().decode("utf-8-sig")
            rows = list(csv.DictReader(io.StringIO(txt)))
            if len(rows) > 400 and "Symbol" in rows[0]:
                with open(CONST, "w", newline="") as f:
                    f.write(txt)
                print(f"constituents: {len(rows)} from {u}")
                return rows
        except Exception as e:
            last = e
    if os.path.exists(CONST):
        print(f"constituent download failed ({last}); using saved {CONST}")
        return list(csv.DictReader(open(CONST, encoding="utf-8-sig")))
    sys.exit(f"cannot get Nifty 500 list: {last}")

def classify(sym, industry, yind):
    yind = (yind or "").lower()
    if industry == "Financial Services":
        if "bank" in yind:
            return ("PSUBANK" if sym in PSU_BANKS else "PVTBANK"), "lender"
        if "insurance" in yind:
            return "FINSERV", "insurer"
        if any(k in yind for k in ("credit", "mortgage", "lending")):
            return "FINSERV", "lender"
        return "FINSERV", "nonfin"   # exchanges, AMCs, brokers, registrars
    if industry == "Healthcare" and any(k in yind for k in ("care facilities", "medical", "diagnostic")):
        return "NIFTY500", "nonfin"  # hospitals / diagnostics: no matching sector index
    return SECTOR_INDEX.get(industry, "NIFTY500"), "nonfin"

def f(x, nd=2):
    try:
        v = float(x)
        return "" if math.isnan(v) or math.isinf(v) else round(v, nd)
    except (TypeError, ValueError):
        return ""

def row_for(sym, meta, asof, yf, pd):
    t = yf.Ticker(sym + ".NS")
    info = t.info or {}
    h = t.history(period="6y", interval="1d", auto_adjust=False)
    if h is None or h.empty:
        raise ValueError("no price history")
    h.index = h.index.tz_localize(None)
    h = h[h.index <= pd.Timestamp(asof)]
    close = h["Close"].dropna()
    px = float(close.iloc[-1]); d0 = close.index[-1]
    def ret(years):
        start = close[close.index <= d0 - pd.DateOffset(years=years)]
        if start.empty: return ""
        return f(((px / float(start.iloc[-1])) ** (1 / years) - 1) * 100, 1)
    yr = h[h.index > d0 - pd.DateOffset(years=1)]
    inc = t.income_stmt; bs = t.balance_sheet
    def series(df, names):
        if df is None or df.empty: return []
        for n in names:
            if n in df.index:
                s = df.loc[n].dropna().sort_index()
                return [(c, float(v)) for c, v in s.items()]
        return []
    eps = series(inc, ["Diluted EPS", "Basic EPS"])
    ni = series(inc, ["Net Income Common Stockholders", "Net Income"])
    eq = series(bs, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
    debt = series(bs, ["Total Debt"])
    eqd = dict(eq)
    roes = [100 * v / eqd[c] for c, v in ni if c in eqd and eqd[c] > 0]
    roe5 = f(sum(roes) / len(roes), 1) if roes else ""
    roe3 = f(sum(roes[-3:]) / len(roes[-3:]), 1) if roes else ""
    pg = ""
    if len(ni) >= 2 and ni[0][1] > 0 and ni[-1][1] > 0:
        pg = f(((ni[-1][1] / ni[0][1]) ** (1 / (len(ni) - 1)) - 1) * 100, 1)
    roe = info.get("returnOnEquity")
    pe = info.get("trailingPE")
    sidx, typ = classify(sym, meta["Industry"], info.get("industry"))
    yrs = f"{eps[0][0].year}-{eps[-1][0].year}" if eps else "n/a"
    return {
        "month": asof[:7], "ticker": sym,
        "source": f"Yahoo Finance via yfinance, close {d0:%d-%b-%y}; annual {yrs} ({len(eps)} yrs EPS); NSE industry {meta['Industry']}",
        "price": f(px), "pe": f(pe) if pe and pe > 0 else "", "bv": f(info.get("bookValue")),
        "roe": f(roe * 100, 1) if roe is not None else "", "roe5": roe5, "roe3": roe3,
        "pg5": pg, "pg_ttm": f(info["earningsGrowth"] * 100, 1) if info.get("earningsGrowth") is not None else "",
        "px1": ret(1), "px3": ret(3), "px5": ret(5),
        "eps_hist": " ".join(str(f(v)) for _, v in eps if f(v) != ""),
        "debt": f(debt[-1][1] / 1e7, 0) if debt else "", "equity": f(eq[-1][1] / 1e7, 0) if eq else "",
        "hi52": f(yr["High"].max()) if "High" in yr else "", "lo52": f(yr["Low"].min()) if "Low" in yr else "",
        "pe_med5": "", "gsec10": "", "name": meta["Company Name"], "sector": meta["Industry"],
        "sector_index": sidx, "type": typ,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", required=True)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--sleep", type=float, default=0.6)
    a = ap.parse_args()
    import yfinance as yf, pandas as pd
    month = a.asof[:7]
    rows = list(csv.DictReader(open(INPUTS)))
    have = {r["ticker"] for r in rows if r["month"] == month}
    cons = get_list()
    todo = [c for c in cons if a.overwrite or c["Symbol"] not in have]
    if a.limit: todo = todo[:a.limit]
    print(f"{len(cons)} constituents, {len(have)} already have {month} rows, fetching {len(todo)}")
    new, fails = [], []
    for i, c in enumerate(todo, 1):
        sym = c["Symbol"]
        for attempt in (1, 2):
            try:
                new.append(row_for(sym, c, a.asof, yf, pd)); break
            except Exception as e:
                if attempt == 2: fails.append(f"{sym}: {type(e).__name__} {e}"[:160])
                time.sleep(3)
        if i % 25 == 0: print(f"  {i}/{len(todo)} done, {len(fails)} failed")
        time.sleep(a.sleep)
    got = {r["ticker"] for r in new}
    keep = [r for r in rows if not (r["month"] == month and r["ticker"] in got)]
    # fill classification columns on existing rows for this month (blank for hand-configured ones)
    out = keep + new
    with open(INPUTS, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore"); w.writeheader()
        for r in out: w.writerow({k: r.get(k, "") for k in COLS})
    print(f"wrote {len(new)} rows; {len(fails)} failed")
    for x in fails: print("  FAIL " + x)

if __name__ == "__main__":
    main()
