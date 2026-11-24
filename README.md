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
- `models/amfi-thematic-monthly.csv`: AMFI sectoral/thematic fund flows since Apr 2019 from `scripts/fetch_amfi_thematic.py` (daily, only new months). Scored by the sectors model as S4, thematic-fund froth.
- `data/parabolic.json`: daily parabolic-move check (gap above the 150-day EMA, plus a back-test) from `scripts/fetch_parabolic.py`. Shown as a flag; it never changes a score.
- Indian equities tab: three views. **Market cap**: Nifty 50, size indices, the large/mid/small rotation model with its 2008–2026 back-test (`scripts/size_rotation.py` → `data/size_rotation.json`, from the NSE history in `models/nse-history/`; research in `research/market-cap-rotation/`), and factors. **Sectors**: heat map, table and the stock-by-stock check. **Stocks**: a sector × setup heat map of value opportunities (short-term drawdown, long-term drawdown, consolidation, multi-year base), a 5-year deep-value table (price flat for 5+ years while EPS grew) and the screener. The setups come from `price_setup()` in `scripts/fetch_parabolic.py` (thresholds in `SETUP_RULE`), run daily on the same 10-year Yahoo history; display only, they never change a score.
- `models/stock-watchlist.csv`: stocks the owner tracks. They are always shown on the Stocks view, and the ones outside the Nifty 500 are fetched and scored too (`scripts/fetch_stock_fundamentals.py`, `scripts/fetch_parabolic.py`).
- `models/commodity-prices-monthly.csv`: World Bank monthly prices (plus the current month from Yahoo) for aluminium, zinc, iron ore and natural gas, from `scripts/fetch_commodity_history.py` (daily). The commodities engine scores those four from this file.
- `models/crypto-prices-monthly.csv` and `models/altcoin_oscillator.py`: Ethereum, XRP, BNB and Solana month-end closes (`scripts/fetch_crypto_history.py`, daily) and an indicative price-and-cycle model for them, with the Bitcoin model's macro filter. Output `models/altcoin-score-log.csv`.
- `knowledge/`: notes from videos, articles and books, shown in the site's Knowledge tab (index in `knowledge/index.json`). A launchd job on the owner's Mac runs `scripts/weekly_knowledge_push.sh` every Sunday at 19:00 to commit knowledge changes and push local commits.
- `models/`: the 12 engines, their inputs, configs, score logs and playbooks. Run all with `bash scripts/run_models.sh`.

## Run locally

```
pip install pandas numpy matplotlib
bash scripts/run_models.sh && python3 scripts/build_signals.py
python3 -m http.server 8000   # then open http://localhost:8000
```
