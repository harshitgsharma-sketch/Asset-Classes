# Real-Assets Model — Standard Run Procedure (v1, indicative, 21-Nov-2026)

> **Release status:** v1. 12 listed trusts (6 REITs, 2 SM-REITs, 4 InvITs), 7 indicators, 9 cities, one month of scores, judgment anchors, no back-test. Report as **indicative** and act only at the extremes (≤35 or ≥66).

Applies to: REIT / InvIT / SM-REIT score, "is Embassy / IndiGrid cheap", REIT vs InvIT vs G-sec, real-estate income, "should I buy a house or rent", rent-vs-buy for a city, "is property in <city> expensive". Design: `real-assets-model-design.md`.

| File (`claude/`) | Role |
|---|---|
| `real-assets-model-design.md` | Principles, indicators, anchors, calculator logic, weaknesses |
| `real-assets-run-procedure.md` | This playbook |
| `real_assets_oscillator.py` | Canonical engine. The only scoring code to use |
| `real-assets-config.json` | Families, anchors, securities, tax, city defaults, rent-vs-buy defaults |
| `real-assets-inputs-monthly.csv` | Long format: one row per (month, security) + one MACRO row |
| `real-assets-rentbuy-scenarios.json` | Saved rent-vs-buy scenarios (the user's inputs) |
| `real-assets-score-log.csv` · `real-assets-city-log.csv` · `real-assets-rentbuy-log.csv` | Outputs, regenerated every run |
| `real-assets-scores.png` | Ranking chart |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → asset classes → **real assets**. This model reuses the asset-class MACRO inputs (10-yr G-sec, repo, expected repo, home-loan rate, income CAGR); use the same month's values.
2. **Load** engine, config, inputs, scenarios and logs; write them to a working folder.
3. **Refresh inputs** (§3). Add or overwrite rows for the run month (`month` = YYYY-MM). Put every value's date and source in `source`; mark judgment values "est.".
4. **Run** `python3 real_assets_oscillator.py all` (or `drivers KEY ...`, `table`, `cities`, `chart`).
   Rent vs buy: `python3 real_assets_oscillator.py rentbuy` (saved scenarios) or with the user's numbers, e.g.
   `python3 real_assets_oscillator.py rentbuy city=Pune price=9000000 rent=28000 hold_yrs=5 tax_regime=old loan_rate=8.25 down_payment_pct=25`.
   Quote only numbers the script prints.
5. **Report** with the §5 template. Send `real-assets-scores.png` and the relevant log.
6. **Save back** inputs, logs (and engine/config/scenarios only if changed); add a §7 run-log line. If the user gave their own property numbers, save them as a named scenario.

## 2. Fixed conventions

- Score 1 = cheap/buy, 100 = rich/sell; bands as in the index. Buckets V 55 / F 25 / T 20; thin-bucket rule 0.5; falling-knife veto (≤35 with Filter ≥70).
- **Yield** = latest quarterly DPU × 4 ÷ last close. Use the DPU *declared* for the latest quarter, not the paid-out amount in a year.
- **NAV** = the latest independent-valuer NAV per unit (usually 30-Sep and 31-Mar). Flag a NAV older than 6 months as stale.
- **DPU growth** = latest quarter vs the same quarter a year earlier (`dpu_q_ly`), or a reported YoY % (`dpu_yoy`).
- **LTV** = net debt ÷ gross asset value (REITs) or net debt ÷ AUM/EV (InvITs), as reported.
- **MACRO row** must equal the asset-class inputs for the month: `gsec10`, `repo`, `repo_exp1y`.
- **Taxable share** = (interest + dividends from new-regime SPVs + other income) ÷ DPU. Blank → family default (config).
- **City inputs** (config `rent_vs_buy.cities`): Anarock gross yields and 2019 → latest price change; `home_loan` and `income_cagr` = the asset-class inputs.
- **Rent vs buy:** never present the four saved "example_" scenarios as the user's own result. Ask for (or use given) city, price, rent, loan rate, down payment, holding period, tax regime and slab; everything else defaults.

## 3. Inputs and sources

| Column | First source | Freq |
|---|---|---|
| price, hi52, lo52, mcap_cr | Screener.in company page (`/company/<NSE code>/`: EMBASSY, MINDSPACE, BIRET, KRT, BAGMANE, NXST, INDIGRID, PGINVIT, IRBINVIT, CAPINVIT) | Monthly |
| dpu_q (+ components) | NSE "Outcome of board meeting" filing for the quarter (`nsearchives.nseindia.com/corporate/<CODE>_...Outcome...pdf`); press releases; Multibagg / Construction World news | Quarterly |
| nav | Same outcome filing ("NAV per unit as per independent valuer") or results press release | Half-yearly |
| dpu_q_ly / dpu_yoy | Same quarter last year's filing, or the press release's "YoY" | Quarterly |
| ltv | Results press release / earnings presentation | Quarterly |
| SM-REIT dpu_q | BSE filings / Multibagg / Scanx for PropShare schemes | Quarterly |
| gsec10, repo, repo_exp1y | Asset-class inputs, same month | Monthly |
| City rent_yield, px_gain | Anarock "top housing markets" / Knight Frank India Real Estate (H1/H2) | Half-yearly |
| Stamp duty | State IGR sites; re-check yearly | Yearly |

## 4. How to read it

- **REITs:** a low V2 (discount to NAV) with a high V1 (yield below G-sec) means the market doubts the valuer's NAV or expects rates to stay high. Prefer trusts cheap on both, with positive DPU growth.
- **InvITs:** compare within the family. High yield on a road InvIT is partly your own capital coming back; check F1 and concession life.
- **Post-tax yield** is what an investor at the stated slab keeps from distributions; unit price changes are taxed separately (LTCG 12.5% after 12 months, STCG 20%).
- **City score** says whether a city's homes are cheap or rich vs history; **rent-vs-buy** says what to do on a specific flat. The break-even price growth is the key number: buy only if you believe prices will beat it over your holding period.

## 5. Output template

1. **Headline:** cheapest and richest 3 trusts (oscillator → signal), the listed-REIT weighted yield vs the 10-yr G-sec, data as-of date.
2. **Ranked table** (from `table`): trust · family · oscillator · signal · V/F/T · yield · spread · P/NAV · DPU YoY · post-tax yield.
3. **By family:** median oscillator and yield.
4. **For each trust asked about (or the 2 cheapest and 2 richest):** top pulls from `drivers` (value, score, Leading/Coincident/Lagging, one-line reason) and flags.
5. **Property:** city table (from `cities`) and, if asked, the rent-vs-buy result: net worth both ways, gap, break-even growth, score → read, and the sensitivity grid.
6. **Data quality:** estimated and stale inputs, missing NAV/LTV, flags, design §5 weaknesses.
7. **Caveat line:** v1, one month, judgment anchors, not investment advice; verify tax and stamp duty for your case.
8. **Files:** chart PNG and logs.

Plain language, tables, explain jargon the first time, phone-readable.

## 6. Change log

- 21-Nov-2026: v1 built at the user's request (item 11 of the roadmap: "Track InvITs and SM-REITs, and a rent-vs-buy calculator for property"). 12 trusts, 7 indicators, 9 cities, rent-vs-buy calculator with old/new tax regime.

## 7. Run log

| Run date | Month | Cheapest | Richest | Notes |
|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | Brookfield 42.6 · Titania 44.4 · Embassy 47.3 (all Accumulate) | Bagmane 73.3 Trim · IndiGrid 66.7 Trim · Mindspace 64.7 Hold | First run. Listed-REIT weighted yield 6.16% vs G-sec 7.28; REIT weighted P/NAV 0.87x; InvIT weighted yield 10.67%. Cities: Mumbai 31.4 and Bengaluru 32.0 Cheap; Noida 57.3 richest. Example rent-vs-buy (5 yrs, 6% growth): break-even price growth 6.2–6.5%/yr |

## 8. Learnings and pitfalls

1. Put the **year in every search**; REIT/InvIT news repeats "Q2" every year (Q2 FY26 = Sep-2025, Q2 FY27 = Sep-2026). Check the quarter-end date in the filing.
2. Screener's "Dividend yield" for REITs/InvITs counts only the dividend component; ignore it and use DPU ÷ price.
3. Screener price lines show "20 Nov" with no year; confirm via market cap or news date.
4. The NSE board-outcome PDF is the most reliable single source: it has DPU components and NAV.
5. The asset-class model's REIT row (yield-only) can read "very expensive" while this model reads Accumulate/Hold: the difference is the NAV discount and DPU growth, which only this model sees.
