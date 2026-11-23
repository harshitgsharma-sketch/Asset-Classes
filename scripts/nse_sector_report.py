#!/usr/bin/env python3
"""Sector valuation and return report from NSE month-end data.

Input: a long CSV (series,date,v1,v2,v3) where series is pe_<sector> (v1=P/E, v2=P/B, v3=Div Yield)
or tri_<sector> (v1=TRI). Nifty 50 reference comes from the same file (pe_large / tri_large) if present,
otherwise from --nifty-dir (CSV files pe_large.csv / tri_large.csv).
Usage: python3 sector_report.py long.csv [--nifty-dir ../backtest/data] [--json out.json]
"""
import csv
import json
import math
import os
import statistics
import sys

PE_MAX = 80.0
NAMES = {"bank": "Bank", "auto": "Auto", "fmcg": "FMCG", "it": "IT", "pharma": "Pharma", "health": "Healthcare",
         "metal": "Metal", "realty": "Realty", "finsvc": "Financial Services", "psubank": "PSU Bank",
         "pvtbank": "Private Bank", "media": "Media", "oilgas": "Oil & Gas", "durables": "Consumer Durables",
         "large": "Nifty 50"}


def f(x):
    try:
        v = float(str(x).replace(",", ""))
        return v if not math.isnan(v) else None
    except (TypeError, ValueError):
        return None


def load_long(path):
    out = {}
    for r in csv.DictReader(open(path)):
        out.setdefault(r["series"], {})[r["date"][:7]] = (r["date"], f(r.get("v1")), f(r.get("v2")), f(r.get("v3")))
    return out


def load_wide(path, kind):
    out = {}
    for r in list(csv.reader(open(path)))[1:]:
        vals = [f(v) for v in r[1:]] + [None, None, None]
        out[r[0][:7]] = (r[0], vals[0], vals[1], vals[2])
    return out


def pct_rank(series, x):
    s = [v for v in series if v is not None]
    return sum(1 for v in s if v <= x) / len(s) * 100 if s and x is not None else None


def cagr(tri, months, years):
    ks = sorted(tri)
    if len(ks) < years * 12 + 1:
        return None
    a, b = tri[ks[-1 - years * 12]][1], tri[ks[-1]][1]
    return (b / a) ** (1 / years) - 1 if a and b else None


def maxdd(tri):
    peak, mdd = 0, 0
    for k in sorted(tri):
        v = tri[k][1]
        if v:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1)
    return mdd


def main():
    src = sys.argv[1]
    data = load_long(src)
    nd = sys.argv[sys.argv.index("--nifty-dir") + 1] if "--nifty-dir" in sys.argv else None
    if "pe_large" not in data and nd:
        data["pe_large"] = load_wide(os.path.join(nd, "pe_large.csv"), "pe")
        data["tri_large"] = load_wide(os.path.join(nd, "tri_large.csv"), "tri")
    npb = {m: v[2] for m, v in data.get("pe_large", {}).items()}
    sectors = sorted({k.split("_", 1)[1] for k in data if k.startswith("pe_")} | {k.split("_", 1)[1] for k in data if k.startswith("tri_")})
    rows = []
    for s in sectors:
        pe, tri = data.get("pe_" + s, {}), data.get("tri_" + s, {})
        r = {"key": s, "name": NAMES.get(s, s)}
        if pe:
            ks = sorted(pe)
            last = pe[ks[-1]]
            pes = [pe[k][1] for k in ks]
            pes_ok = [v for v in pes if v and 0 < v <= PE_MAX]
            pbs = [pe[k][2] for k in ks if pe[k][2]]
            last10 = ks[-120:]
            r.update(val_from=ks[0], val_to=ks[-1], pe=last[1], pb=last[2], dy=last[3],
                     pe_unusable=len(pes) - len(pes_ok),
                     pe_med=statistics.median(pes_ok) if pes_ok else None,
                     pb_med=statistics.median(pbs) if pbs else None,
                     pb_med10=statistics.median([pe[k][2] for k in last10 if pe[k][2]]) if pbs else None,
                     pb_pct=pct_rank(pbs, last[2]),
                     pb_pct10=pct_rank([pe[k][2] for k in last10], last[2]),
                     pe_pct=pct_rank(pes_ok, last[1]) if last[1] and last[1] <= PE_MAX else None)
            rel = [pe[k][2] / npb[k] for k in ks if pe[k][2] and npb.get(k)]
            if rel:
                r.update(rel_pb=rel[-1], rel_pb_med=statistics.median(rel), rel_pb_pct=pct_rank(rel, rel[-1]))
        if tri:
            tk = sorted(tri)
            r.update(tri_from=tk[0], tri_to=tk[-1], cagr3=cagr(tri, None, 3), cagr5=cagr(tri, None, 5),
                     cagr10=cagr(tri, None, 10), cagr15=cagr(tri, None, 15), mdd=maxdd(tri))
            v = [tri[k][1] for k in tk]
            rets = [v[i] / v[i - 1] - 1 for i in range(1, len(v)) if v[i] and v[i - 1]]
            r["vol"] = statistics.pstdev(rets) * math.sqrt(12) if len(rets) > 12 else None
            nt = data.get("tri_large", {})
            if len(tk) > 12 and tk[-13] in nt and tk[-1] in nt:
                r["rel12"] = (v[-1] / v[-13]) - (nt[tk[-1]][1] / nt[tk[-13]][1])
            # largest single-month moves for a sanity check
            r["big_moves"] = [f"{tk[i]}:{rets[i - 1] * 100:+.0f}%" for i in range(1, len(v)) if v[i] and v[i - 1] and abs(v[i] / v[i - 1] - 1) > 0.25]
        rows.append(r)

    def p(x, d=1, pct=False):
        if x is None:
            return "-"
        return f"{x * 100:.{d}f}%" if pct else f"{x:.{d}f}"
    print(f"{'Sector':20s} {'P/E':>6} {'P/B':>5} {'PB med':>6} {'PB %ile':>7} {'PB/Nifty':>8} {'(med)':>6} {'5y CAGR':>7} {'10y':>6} {'15y':>6} {'MaxDD':>7} {'12m vs N50':>10} {'PE bad':>6}  val from / tri from")
    for r in sorted(rows, key=lambda r: (r.get("pb_pct") is None, -(r.get("pb_pct") or 0))):
        print(f"{r['name']:20s} {p(r.get('pe')):>6} {p(r.get('pb'),2):>5} {p(r.get('pb_med'),2):>6} {p(r.get('pb_pct'),0):>7} "
              f"{p(r.get('rel_pb'),2):>8} {p(r.get('rel_pb_med'),2):>6} {p(r.get('cagr5'),1,True):>7} {p(r.get('cagr10'),1,True):>6} "
              f"{p(r.get('cagr15'),1,True):>6} {p(r.get('mdd'),0,True):>7} {p(r.get('rel12'),1,True):>10} {r.get('pe_unusable','-'):>6}  "
              f"{r.get('val_from','-')} / {r.get('tri_from','-')}")
    for r in rows:
        if r.get("big_moves"):
            print("moves >25%:", r["name"], ", ".join(r["big_moves"]))
    if "--json" in sys.argv:
        json.dump(rows, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
