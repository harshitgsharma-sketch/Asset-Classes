# Nifty 500 Stock Screener — Standard Run Procedure (v1, indicative, published 21-Nov-2026)

> **Release status (22-Nov-2026):** universe extended to the Nifty 500. The 50 Nifty 50 stocks are sourced by hand from screener.in on the monthly run; the other ~450 are filled by `scripts/fetch_stock_fundamentals.py` from Yahoo Finance (yfinance), which has 4 years of annual EPS, so their V2 uses a 3-yr window. 9 of the 11 design indicators are live for non-financials (V5 own-median PE is not sourced; V4 applies to lenders only). There is one month of data and no back-test. Always say "v1 / indicative" and quote the universe size when reporting.

Applies to any question about individual Indian large-cap stocks: "cheapest Nifty stocks", "is TCS cheap", "rate HDFC Bank", "stock screener", "which Nifty 50 names to buy or trim". Same method and same output every time. Design: `nifty500-stocks-model-design.md`.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `nifty500-stocks-model-design.md` | Design, indicators, weaknesses, data plan |
| `nifty500-stocks-run-procedure.md` | This playbook |
| `stock_oscillator.py` | Canonical engine. The only scoring code to use |
| `nifty500-stocks-config.json` | Per-stock set-up: sector, sector index, type, flags |
| `nifty500-stocks-inputs-monthly.csv` | Long format, one row per (month, ticker), plus a NIFTY50 benchmark row |
| `nifty500-stocks-score-log.csv` | Generated scores (regenerated on every run) |
| `nifty-sectors-inputs-monthly.csv` | Read only: sector index PE for V1 |

## 1. Steps

1. **Run the sector model first** (`nifty-sectors-run-procedure.md`), or at least refresh its PE column. V1 uses the sector index PE for the same month; if the month is missing, the latest is used and flagged stale.
2. **Load** the engine, config, inputs, sector inputs and log, and write them to a working folder.
3. **Refresh inputs** (§3). Add rows for the new month (`month` = YYYY-MM of the run; overwrite rows for the same month). Put the date and source in `source`.
4. **Run** `python3 stock_oscillator.py all` (ranked table). For detail: `python3 stock_oscillator.py drivers TCS HDFCBANK`. Quote only numbers the script prints.
5. **Report** with the §5 template. Send `nifty500-stocks-score-log.csv`.
6. **Save back** inputs, score log (and engine/config only if changed). Add a §8 run-log line.

## 2. Fixed conventions

- **Score:** per indicator clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive/headwind. Bands ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Buckets:** Valuation 50 · Quality 25 · Momentum 25. Weights W = I × S × R × St (`SPEC`). Blanks skipped and re-normalised; thin-bucket rule (one indicator → half-way to 50).
- **Benchmark row:** `ticker=NIFTY50` holds `px1` (1-yr price return %), `px3` (3-yr price CAGR %) and `gsec10`. Use Nifty closes on the same date as the stock prices, and the Nifty model's `gsec10`.
- **EPS CAGR for V2:** from `eps_hist` (6 fiscal-year EPS, oldest → newest, space-separated). If the base year is a loss, V2 is skipped; if history is short, Screener's 5-yr profit CAGR (`pg5`) is used.
- **Vetoes and flags:** design §4. "NOT RATED" = no valuation input; do not act on the number.

## 3. Inputs, sources, frequency

| Column | Meaning | Source (first choice) | Freq |
|---|---|---|---|
| price, pe, bv, roe | Close, Stock P/E, book value/share, ROE (latest) | screener.in/company/<SYMBOL>/consolidated/ top ratios | Monthly |
| roe5, roe3 | Return on Equity 5 Years / 3 Years | Screener "Return on Equity" box | Monthly |
| pg5, pg_ttm | Compounded Profit Growth 5 Yrs / TTM | Screener "Compounded Profit Growth" box | Quarterly |
| px1, px3, px5 | Stock Price CAGR 1 / 3 / 5 Yrs | Screener "Stock Price CAGR" box | Monthly |
| eps_hist | Annual EPS, last 6 fiscal years | Screener Profit & Loss table | Yearly (after Q4) |
| debt, equity | Borrowings; Equity Capital + Reserves | Screener Balance Sheet (latest half-year) | Half-yearly |
| hi52, lo52 | High / Low | Screener top ratios | Monthly |
| pe_med5 | Own 5-yr median PE (V5) | Screener PE chart "Median PE" (logged-in) or Trendlyne PE band | Monthly — **not yet sourced** |
| NIFTY50 px1/px3 | Nifty 1-yr return, 3-yr CAGR (price) | Nifty closes from NSE / market wraps on the same dates | Monthly |
| gsec10 | 10-yr G-sec yield | `nifty-inputs-monthly.csv` | Monthly |

**Fetch tip:** web-fetch each Screener page with one prompt asking for a single `key=value;` line (see the §8 run note). 50 stocks take about 50 fetches. For the full Nifty 200 use a Screener screen export instead (design §6).

**Staleness:** flag any input older than its frequency as *(stale: date)*, and estimates as *(est.)*.

## 4. How to read it

- v1 has **one month of scores only** and no back-test. Treat 36–65 as neutral and act only at extremes (≤35 or ≥66).
- The score ranks stocks *within* equities. Whether to add to equities at all comes from the Nifty 50, sector and asset-class models.
- Low scores in cyclicals (metals, oil, coal) usually come from peak earnings. Check the flags.
- Insurers and holdcos are mis-measured by PE/ROE (design §5). Treat their scores as a placeholder.

## 5. Output template

1. **Headline:** the cheapest 5 and richest 5 stocks with score → signal, plus the data as-of date and universe size ("50 of the Nifty 200").
2. **Ranked table** (from `table`): ticker · sector · score · signal · V/Q/M · PE · coverage.
3. **For each stock asked about:** the top 3 pulls each way from `drivers` (value, score, Leading/Coincident/Lagging, one-line reason).
4. **Signal counts** and the vetoes and flags that change the read (value trap, falling knife, not rated, one-offs).
5. **Data quality:** universe size, indicators live (9 of 11; V5 missing), stale and estimated inputs.
6. **Caveat line:** single-month v1, judgment anchors, not investment advice.
7. **Files:** `nifty500-stocks-score-log.csv`.

Plain language, tables, explain jargon the first time, phone-readable.

## 6. Change log

- 22-Nov-2026: universe extended to the Nifty 500 (files renamed nifty200-stocks-* → nifty500-stocks-*). New `scripts/fetch_stock_fundamentals.py` downloads NSE's `ind_nifty500list.csv` (saved as `nifty500-constituents.csv`), pulls Yahoo Finance data for every constituent without a row this month, and writes name/sector/sector_index/type columns; the engine uses those for stocks not in the config. V2 uses a 3-yr window when only 4 years of EPS are known. The board keeps non-Nifty-50 stocks out of its headline counts and signal lanes.

- 21-Nov-2026: v1 built and run on the 50 Nifty 50 constituents (screener.in data, close 20-Nov-2026). V2 is skipped on a loss-year EPS base; "NOT RATED" was added for stocks with no valuation input; Q1/Q4/V4 fall back to 3-yr ROE when there is no 5-yr figure.

## 7. v1 vs design (what is still missing)

- Yahoo-sourced stocks (outside the Nifty 50): 4 yrs of EPS (3-yr V2 window), Yahoo's TTM ROE and PE, NSE-industry-to-sector-index mapping (hospitals, chemicals, diversified → Nifty 500 PE).
- V5 (PE vs own 5-yr median) needs PE history.
- No EPS revisions, 200-DMA or P/EV for insurers.
- No history before Nov-26 and no back-test.

## 8. Run log

| Run date | Month | Cheapest | Richest | Notes |
|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | Hindalco 23.2 Buy · Coal India 24.3 Buy · ONGC 28.2 Buy · Infosys 29.4 Buy · TCS 30.6 Buy · SBI 32.7 Buy | Jio Financial 89.8 Exit · Grasim 80.8 Exit · Bharti Airtel 78.1 Trim · Max Healthcare 77.2 Trim · Eternal 73.4 Trim (IndiGo 81.4, not rated) | First run, 50 stocks, screener.in close 20-Nov-26; Nifty 25,514 (19-Nov-26); 1-yr −2.6%, 3-yr CAGR 9.0%; G-sec 7.20 |

## 9. Learnings and pitfalls

1. Screener pages fetch reliably with `/company/<NSE symbol>/consolidated/`. URL-encode `&` (M&M → `M%26M`). Some pages return blanks on the first try (SBI Life); retry the standalone URL `/company/<SYMBOL>/`.
2. Screener's 5-yr ROE can be blank for companies that changed year-end or listed recently (Nestle India, Jio Financial). Use the standalone page or the 3-yr ROE fallback.
3. Demergers and one-off gains distort EPS history (Tata Motors → TMPV, HUL ice cream, ITC Hotels). Flag them in config, do not edit the data.
4. The Screener chart API (median PE) is blocked to automated fetch (robots). V5 needs an export.
5. Put the year in every search and reject results from another year (Nifty §9 pitfall 1).
