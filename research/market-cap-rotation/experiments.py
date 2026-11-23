"""Variant tests: pick on 2008-2016 (in-sample), report 2017-2026 (out-of-sample)."""
import sys, glob, os, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation_backtest as bt

def load(ddir=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "models", "nse-history")):
    data = {}
    def la(prefix, want):
        m = {}
        for f in sorted(glob.glob(os.path.join(ddir, prefix + "*.csv"))): m.update(bt.load_series(f, want))
        return bt.month_end(m)
    for s in ("large", "mid", "small"):
        data["tri_"+s] = la(f"tri_{s}", ["totalreturnsindex"])
        data["pe_"+s] = la(f"pe_{s}", ["p/e"]); data["pb_"+s] = la(f"pe_{s}", ["p/b"])
    return data

data = load()
months, tri, rows = bt.build(data, metric="pb")
split = next(j for j, (i, r) in enumerate(rows) if r["month"] >= "2017-01")
IS, OOS = rows[:split], rows[split:]

def ev(rs, **kw):
    navs, hist, to = bt.run(months, tri, rs, **kw)
    m = bt.stats([a for _, a, _ in navs]); f = bt.stats([b for _, _, b in navs])
    return m, f, to / (len(navs) / 12)

W2 = dict(A=0.5, B=0.25, C=0.0, D=0.25, E=0.0, F=0.0)
variants = {
  "As designed (A-E, k=.4)": dict(),
  "As designed, k=.8": dict(k=0.8),
  "Valuation only A+B, k=.8": dict(use=("A","B"), k=0.8),
  "A+B+D, k=.8": dict(use=("A","B","D"), k=0.8),
  "A+B+D, k=1.0": dict(use=("A","B","D"), k=1.0),
  "A+B+D, k=1.0, band 5 1/3": dict(use=("A","B","D"), k=1.0, band=5, step=1/3),
  "A+B+D+E, k=1.0": dict(use=("A","B","D","E"), k=1.0),
  "A only, k=1.0": dict(use=("A",), k=1.0),
}
print(f"{'variant':<32} {'IS CAGR':>8} {'IS vs fix':>9} {'IS MDD':>7} | {'OOS CAGR':>8} {'OOS vs fix':>10} {'OOS MDD':>8} {'fixMDD':>7} {'turn':>6}")
for name, kw in variants.items():
    a, af, _ = ev(IS, **kw); b, bf, t = ev(OOS, **kw)
    print(f"{name:<32} {a['cagr']*100:7.2f}% {(a['cagr']-af['cagr'])*100:+8.2f}  {a['mdd']*100:6.1f}% | {b['cagr']*100:7.2f}% {(b['cagr']-bf['cagr'])*100:+9.2f}  {b['mdd']*100:7.1f}% {bf['mdd']*100:6.1f}% {t*100:5.0f}%")

# forward correlation at different horizons for the mid valuation-gap pillar
for h in (6, 12, 24, 36):
    for seg in ("mid", "small"):
        xs, ys = [], []
        for i, r in rows:
            if i + h >= len(months) or not r["live"][seg]: continue
            p = r["pillars"][seg]; xs.append((p["A"]*.5+p["B"]*.25+p["D"]*.25))
            ys.append(tri[seg][i+h]/tri[seg][i] - tri["large"][i+h]/tri["large"][i])
        print(f"h={h:2d} {seg:5s} corr(A+B+D score, fwd rel return) = {bt._corr(xs, ys):+.2f}  n={len(xs)}")
