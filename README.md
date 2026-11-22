# Entry/Exit Board

A one-page dashboard over 12 entry/exit oscillators for an INR investor with a holding period of 5 years or less.
Every model scores 1 (cheap, buy) to 100 (rich, sell): ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.

Not investment advice. Cheap/rich anchors are judgment-based, and no model is back-tested yet.

## How it stays current

| When | What happens | Where |
|---|---|---|
| Every page open or refresh | The page loads `data/signals.json` (no cache), recomputes every section in the browser, checks each model's input age against its refresh cadence, and pulls live Bitcoin and USD/INR prices to show drift since the last scoring run | `index.html`, `app.js` |
| Daily, 07:00 IST | GitHub Action re-runs all 12 oscillators, fetches gold, silver, Brent, copper, Bitcoin, USD/INR and Nifty prices, rebuilds `data/signals.json`, commits if anything changed | `.github/workflows/refresh.yml` |
| Monthly (3rd) | The Claude model run refreshes the inputs that need research (P/Es, CAPE, PMIs, RBI rates, REIT NAVs, housing) and commits them to `models/`; the push triggers the Action | `models/*-inputs-monthly.csv` |

Daily prices do **not** change scores by themselves: the price-driven indicators inside each model's inputs are set on the monthly run. The page shows how far prices have moved since then and flags moves of 5% or more.

## Layout

- `index.html`, `app.js`: the site (GitHub Pages, deploy from branch `main`, folder `/`).
- `data/signals.json`: every reading, freshness metadata and prices, built by `scripts/build_signals.py`.
- `data/prices.json`: latest prices from `scripts/fetch_prices.py`.
- `data/parabolic.json`: daily parabolic-move check (gap above the 150-day EMA, plus a back-test) from `scripts/fetch_parabolic.py`. Shown as a flag; it never changes a score.
- `knowledge/`: notes from videos, articles and books, shown in the site's Knowledge tab (index in `knowledge/index.json`). A launchd job on the owner's Mac runs `scripts/weekly_knowledge_push.sh` every Sunday at 19:00 to commit knowledge changes and push local commits.
- `models/`: the 12 engines, their inputs, configs, score logs and playbooks. Run all with `bash scripts/run_models.sh`.

## Run locally

```
pip install pandas numpy matplotlib
bash scripts/run_models.sh && python3 scripts/build_signals.py
python3 -m http.server 8000   # then open http://localhost:8000
```
