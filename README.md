# Entry/Exit Board

A one-page dashboard over 12 entry/exit oscillators for an INR investor with a holding period of 5 years or less.
Every model scores 1 (cheap, buy) to 100 (rich, sell): ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.

Not investment advice. Cheap/rich anchors are judgment-based. The only back-test is an in-sample band check on the 13 readings with a 5-year score history (Snapshot tab, "Does the scale work?"); those scores were reconstructed after the fact, so it is a sanity check, not proof.

## How it stays current

| When | What happens | Where |
|---|---|---|
| Every page open or refresh | The page loads `data/signals.json` (no cache), recomputes every section in the browser, checks each model's input age against its refresh cadence, and pulls live Bitcoin and USD/INR prices to show drift since the last scoring run | `index.html`, `app.js` |
| Daily, 07:00 IST | GitHub Action re-runs all 12 oscillators, fetches gold, silver, Brent, copper, Bitcoin, USD/INR and Nifty prices, re-scores the price-driven models at those prices (provisional), refreshes the mutual fund list, rebuilds `data/signals.json`, runs a sanity check (`scripts/check_signals.py`: stops without publishing if readings vanish, a score leaves 1–100 or an inputs date goes backwards), sends band-change alerts, writes the monthly summary note, commits if anything changed | `.github/workflows/refresh.yml` |
| Monthly (3rd) | The Claude model run refreshes the inputs that need research (P/Es, CAPE, PMIs, RBI rates, REIT NAVs, housing) and commits them to `models/`; the push triggers the Action | `models/*-inputs-monthly.csv` |

**Official vs provisional scores.** The official score is set on the monthly run. Every day, `scripts/provisional_scores.py` takes each model's current month of inputs, swaps in the latest prices, moves the price-driven indicators by as much as the price moves them, and scores the row with the model's own scoring function; hand-researched inputs stay as they were. It covers gold, the Nifty 50, Bitcoin, silver, Brent and copper (`data/provisional.json`), is shown as "At today's prices", and never replaces the official score. At the run's own prices it reproduces each official score exactly.

**Alerts and the monthly note.** When a headline reading changes band, or its parabolic flag turns on, the Action opens a GitHub issue labelled `band-alert` (GitHub emails the repo owner about new issues). When the Gold & Nifty 50 model run moves to a new month, `scripts/monthly_summary.py` writes `knowledge/monthly-summary-YYYY-MM.md` (shown in the Knowledge tab) and sends it the same way. For Telegram too, add two repository secrets, `TELEGRAM_BOT_TOKEN` (from @BotFather) and `TELEGRAM_CHAT_ID`.

**Testing the scale** (Snapshot tab):
- *Does the scale work?* An in-sample band check on the 13 readings with a 5-year score history (reconstructed, so a sanity check only).
- *Live track record*: only months scored at the time (`source` not "reconstructed" in the score logs), with the price change since. The honest test; it needs a year to say anything.
- *Price-only check* for the sectors and global models (`scripts/proxy_backtest.py`, run from `fetch_parabolic.py` on its 10-year daily closes): the price-based indicators of each model with the model's own anchors and weights. Not a test of the full models.

**Market mood** (Snapshot): the mean of the Nifty 50 valuation score, AMFI thematic-fund froth and the share of rich minus cheap readings, monthly since 2021.

**What changed.** `scripts/build_signals.py` keeps one score snapshot per model run in `data/score-snapshots.json` (last 24 runs per model), and each item gets a `prev` score: from the previous stored run, or from the monthly score history where one exists.

**My portfolio** (`#portfolio`): holdings, weights and staged-entry plans are kept in the viewer's browser only (`localStorage`), never sent anywhere; Export and Import move them between devices as a JSON file. Mutual funds and ETFs come from AMFI's daily NAV file (`scripts/fetch_funds.py` → `data/funds.json`) and are scored as the index their name or SEBI category points to. The site is installable (`manifest.webmanifest`, `sw.js`: network first, last good copy offline). `?all=1` in the URL opens with Hold, Trim and Exit shown.

Daily prices do **not** change official scores: the price-driven indicators inside each model's inputs are set on the monthly run. The page shows how far prices have moved since then, the provisional score, and flags moves of 5% or more.

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
