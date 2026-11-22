# Nifty 50 Oscillator — Standard Run Procedure (follow on every Nifty query)

Applies whenever the user asks about the Nifty 50 or Indian large-cap equities. Examples: "Nifty score", "run the Nifty model", "Nifty update", "should I buy/sell Nifty", "Nifty trend/outlook". The goal is **the same method and the same output format every time**. The design rationale for every indicator is in `nifty-model-design.md`.

Project files (all under `claude/`):
| File | Role |
|---|---|
| `nifty-model-design.md` | Model design, 40-indicator table with I/S/R/St/W, type, cheap→rich, rationale |
| `nifty-run-procedure.md` | This playbook: conventions, sources, rules, output template, logs |
| `nifty_oscillator.py` | Canonical engine. It is the only scoring code to use |
| `nifty-inputs-monthly.csv` | Month-end inputs: raw columns, plus i01..i40 (Jan-2018 → latest; scored from Nov-2021) |
| `nifty-scenarios.json` | Fixed Bear/Base/Bull EPS × PE paths and driver paths for the 5-yr projection |
| `nifty-score-log.csv` | Generated monthly scores (history + every run) |

There is no live Sheet yet. The CSV and the script are the source of truth.

---

## 1. Steps

1. **Load** the five data/code files with `project_read`, and write the script, CSVs and JSON into a working folder.
2. **Refresh inputs.** For every indicator, check how old its value is. Anything older than its update frequency (§3) gets refreshed by web search, trying the named source first. Record the value, its date and its source.
3. **Write the current month's row** in `nifty-inputs-monthly.csv` (month = YYYY-MM of the run date, overwriting the row if it already exists, `source` = "live run DD-Mon-YYYY"). If a new month has started since the last row, first finalise the previous month with month-end closes.
   - Fill the raw columns: `nifty, eps_ttm, gsec10, us10y, repo, fii_net_kcr, mf_net_kcr, gold_usd, usdinr, brent_usd, dxy`. The script derives #1, 2, 4, 5, 10, 11, 12, 13, 14, 19, 24, 26, 29, 30 and 40 from these.
   - Enter the remaining i-columns directly (units as in `SPEC`).
   - `gold_usd`, `usdinr`, `brent_usd` and `dxy` should match the same month in `gold-inputs-monthly.csv`. Reuse those values if the gold model was run this month.
4. **Run** `python3 nifty_oscillator.py all`. This produces the score log, the latest score and driver table, the like-for-like vs coverage split of the monthly change, the yearly trend table, the month-end sensitivity, the fair value and rule check, the 5-yr projection and the chart PNG. Report numbers only from this output; never estimate them by eye (see §9).
5. **Sanity check.** Quote the script's "like-for-like change" and "from coverage change" split, never a guess. If the score moved more than 8 points in a month, name the inputs that drove the move from the driver table.
6. **Report** using the template in §5. Send the chart PNG and `nifty-score-log.csv`.
7. **Save back** to the project (`project_write`, `local_path`): `nifty-inputs-monthly.csv` and `nifty-score-log.csv`, plus `nifty-scenarios.json` or the script only if they changed. Add a line to §8 (Run log) of this file.

## 2. Fixed conventions (do not vary between runs)

- **Prices:** month-end Nifty 50 closes. "Today" = latest close, with the row flagged "month in progress".
- **ATH:** 26,373.20 intraday (Jan-2026) until it is broken. Earlier ATHs in the script: 18,604 (Oct-21) and 26,277 (Sep-24).
- **EPS (`eps_ttm`):** Nifty trailing EPS = close ÷ NSE consolidated trailing PE on the same date (NSE Indices or Trendlyne). From it, PE (#2) and BEER (#1 = 10-yr G-sec × PE / 100) are derived.
- **200-DMA ≈** mean of the last 10 month-end closes. **200-WMA ≈** mean of the last 46. **RSI(14)** is computed from monthly closes.
- **#3 Expected RBI change (bp, ~6 m):** take it from the OIS/MIBOR curve or a consensus of economist polls. In history it is filled with hindsight (actual repo 6 months later minus repo now), so treat back-test numbers on #3 as optimistic. Assumed forward repo path: 5.50 (Dec-26) → 5.75 (Feb-27). Update it after each MPC meeting.
- **#6 Forward PE:** price ÷ 12-m forward consensus EPS (blend of FY+1 and FY+2 by months remaining). Store the EPS in `fwd12m_eps_now` in the JSON for the fair-value calculation.
- **#7 EPS revisions:** 3-m % change in consensus FY+1 Nifty EPS (MOFSL, JM Financial or Bloomberg consensus as quoted in the press).
- **#10 FII flow:** NSDL FPI net equity flows, ₹ '000 crore per month (`fii_net_kcr`). The script sums the last 3 months.
- **#24 MF flow:** AMFI net inflow into equity-oriented schemes, ₹ '000 crore per month (`mf_net_kcr`). The script takes the 3-month average.
- **#40 Nifty ÷ Gold:** gold at international parity in ₹ per 10 g = gold_usd ÷ 31.1035 × 10 × USD/INR, with no duty.
- **Weights** = Impact × Severity × Reliability × Stability from `SPEC`. Blank inputs are skipped and the remaining weights re-normalised within each bucket. Buckets are V 40 / T 40 / F 20.
- **Score bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Vetoes:**
  - Falling knife: Osc ≤35 with Filter ≥70 or EPS revisions ≤−3% → "Buy vetoed".
  - Euphoria: Osc ≥66, Nifty/200-DMA ≥1.12 and breadth ≥80% → Trim.
- **Scenarios:** use `nifty-scenarios.json` unchanged. Change it only when asked, or at the annual review in April after FY results, and log the change in §7.

## 3. Data sources and update frequency

| # | Indicator | Source (first choice) | Freq |
|---|---|---|---|
| 1, 2 | BEER, trailing PE | NSE Indices PE (consolidated) → `eps_ttm`; CCIL/FBIL 10-yr G-sec | Monthly |
| 3 | Expected RBI change | MIBOR OIS 1-yr, MPC statement, Reuters poll | Monthly / after MPC |
| 4, 11, 19, 29, 30 | Price-derived | Nifty month-end close | Monthly |
| 5 | G-sec 6-m change | CCIL / RBI DBIE | Monthly |
| 6 | Forward PE | MOFSL/Kotak/Bloomberg consensus EPS | Monthly |
| 7 | EPS revisions | MOFSL "India Strategy", JM Financial monthly | Monthly |
| 8 | India VIX | NSE | Monthly |
| 9 | % Nifty 500 > 200-DMA | StockEdge / Trendlyne / Chartink market breadth | Monthly |
| 10 | FII flow | NSDL FPI monitor | Monthly |
| 12, 13 | DXY, Brent | Same as gold model | Monthly |
| 14 | India–US spread | CCIL 10-yr − FRED DGS10 | Monthly |
| 15 | FII ownership | NSE "India Ownership Tracker" / MOFSL (quarterly) | Quarterly |
| 16 | Midcap 150 PE ÷ Nifty PE | NSE Indices | Monthly |
| 17 | Premium to MSCI EM | MOFSL / Goldman / Morgan Stanley strategy notes | Monthly |
| 18 | US HY OAS | FRED BAMLH0A0HYM2 | Monthly |
| 20 | CPI | MOSPI (released ~12th) | Monthly |
| 21 | Market cap ÷ GDP | NSE/BSE m-cap ÷ trailing 4-qtr nominal GDP | Monthly |
| 22 | CAPE | Build from 10-yr Nifty EPS series (open task) | Monthly |
| 23, 34 | PB, dividend yield | NSE Indices | Monthly |
| 24 | MF flows | AMFI monthly | Monthly |
| 25 | Liquidity | RBI LAF data (net LAF ÷ NDTL) | Monthly |
| 26 | EPS growth TTM | Derived from `eps_ttm` | Monthly |
| 27 | Real GDP | MOSPI (quarterly, ~2-month lag) | Quarterly |
| 28 | PMI | HSBC India Manufacturing PMI (S&P Global) | Monthly |
| 31 | REER | RBI Bulletin table 50 (40-ccy, trade-wtd) | Monthly |
| 32 | Issuance | Prime Database (IPO + QIP + OFS) | Monthly |
| 33 | MTF book YoY | CareEdge / NSE MTF data | Monthly |
| 35 | Profit ÷ GDP | MOFSL corporate profit/GDP | Quarterly |
| 36 | Bank credit | RBI fortnightly | Monthly |
| 37 | Promoter holding change | NSE ownership report / MOFSL | Quarterly |
| 38 | Bank Nifty vs Nifty | NSE closes (3-m relative return) | Monthly |
| 39 | PCR | NSE option chain, month-end OI PCR | Monthly |
| 40 | Nifty ÷ Gold | Derived | Monthly |

**Staleness rule:** in the output, flag any input older than its update frequency as *(stale: date)* and any estimate as *(est.)*, and state the data coverage %.

**Priority gaps to fill:** #9 breadth, #16 midcap/Nifty PE, #22 CAPE, #25 liquidity, #32 issuance, #38 Bank Nifty relative return, #39 PCR. #6 forward PE, #23 PB and #34 DY exist only from mid-2026; back-fill them when time allows. History before Nov-2026 has coverage of 73–83%.

## 4. How to read the score (back-test notes, Nov-21 → Nov-26, reconstructed inputs)

- History range: **40.6 (Mar-26, Accumulate, the war sell-off) → 66.0 (Sep-24, Trim, the actual market top)**. Trim also flashed in Jul-24. The score never reached Buy (≤35) or Exit (>80). σ ≈ 5.
- Yearly averages: 2022 58.5 · 2023 55.5 · 2024 60.6 · 2025 51.8 · 2026 47.4. The 2026 floor fell as PE de-rated from ~24 to ~19–20.
- In-sample correlation of score with the next-12-m Nifty return ≈ −0.13. The sign is correct but the signal is weak in mid-range. **Treat 45–60 as neutral.** The model is most useful at extremes:
  - ≥64 preceded the Oct-24 → Feb-25 correction (−14%).
  - ≤48 (Feb–Apr 2025, Mar-26, Sep–Oct 2026) was followed by gains of roughly 7–15% within 1–4 months.
- Macro and valuation inputs offset each other, so the score mean-reverts to ~48–58. A true Buy (≤35) needs a price fall together with stress: VIX >25, FII outflows >₹80k cr per quarter, HY spreads >5% and negative EPS revisions. See the Bear path.
- History is reconstructed from approximate inputs (27–33 of 40 indicators). Treat it as indicative, ±3 points.

## 5. Output template (use every time, in this order)

1. **Headline (1–2 sentences):** score X/100 → SIGNAL, change vs last month (with the like-for-like split if coverage changed), Nifty level, data as-of date. **If the month is still in progress, the headline is a month-end prediction:** give the sensitivity table (`sens`: −5%…+5%) and the Nifty level at which the signal band flips.
2. **Sub-scores table:** Valuation / Timing / Filter with weights and scores, coverage %, and any veto status.
3. **Drivers:** top 3 pulling towards sell and top 3 pulling towards buy (from the driver table), each with value, score, type (Leading/Coincident/Lagging) and a one-line reason.
4. **Trend:** the `trend` output. A yearly table (avg / high / low / year-end Nifty) for every year in the log (5 years by default), the last 12 months month by month, the 12-m average and 3-m slope, the best calls (Trim at the Sep-24 top, low-40s readings before rallies), and the chart PNG.
5. **Entry/exit status:** fair value Low/Mid/High and Nifty vs Mid; which entry tranche or exit rule (§6) is met or closest to triggering, with concrete thresholds.
6. **5-yr outlook table:** Bear/Base/Bull × probability × score path (Nov-27…Nov-31) × Nifty path × exit PE × price CAGR, plus the probability-weighted path. Follow it with 2–3 bullets on implications.
7. **Data quality:** stale, estimated and missing inputs, and any fallback conventions used.
8. **Caveat line:** anchors are judgment-based, history is reconstructed, and this is not investment advice.
9. **Files:** chart PNG and `nifty-score-log.csv`.

For a narrow question (e.g. "just today's score"), give items 1–3 and 7, and offer the rest. For "score for this month + trend", give items 1–4, a two-line entry/exit status, a one-line 5-yr outlook, then 7–9.

**Style (user preference):** plain language. Explain jargon in a few words the first time it appears (e.g. BEER, OAS, 200-DMA). Use tables for numbers. Tag drivers Leading / Coincident / Lagging. Keep the reply readable on a phone.

## 6. Fair value and entry/exit rules (5-year holding window)

- **Fair value** = 12-m forward EPS × PE band (Low 16 / Mid 20 / High 24). Nov-26: fwd EPS 1,366 → **Low 21,860 · Mid 27,320 · High 32,780**. Cross-check: the PE implied by BEER at mid-range (1.45) = 145 ÷ 10-yr yield.
- **Entry (lump sums in thirds; any running SIP continues regardless):**
  - Tranche 1: Oscillator ≤35, or ≤40 together with Nifty ≤ FV Mid.
  - Tranche 2: Nifty ≤ FV Mid. **Met at Nov-26.**
  - Tranche 3: RBI pivots to easing (expected repo change ≤ −25 bp).
  - Accelerate (deploy the rest): Nifty ≤ FV Low × 1.05, or VIX ≥25 with the falling-knife veto off.
- **Exit:**
  - Oscillator ≥66 for 2 consecutive monthly reviews → trim one-third.
  - Nifty ≥ FV High → trim one-third.
  - BEER ≥1.75 → trim.
  - MTF YoY ≥60% while Oscillator ≥60 → trim.
  - Trailing stop: −15% from peak once up ≥30%.
  - **Time stop: exit the remainder 57 months after the first entry** (inside the 5-year window).
- **Re-entry after an exit:** only when the Oscillator is ≤50 again.

## 7. Change log (method / weights / scenarios)

- 19-Nov-2026: v1 built. 40 indicators, buckets 40/40/20, two-rule veto.
  - Defaults chosen pending the user's §5 decisions in the design doc: keep all 40, keep forward PE, FII weight 9, lump sums only, 5-year back-fill.
  - Scenarios: Bear EPS 7% CAGR / PE 15.5 (25%) · Base 12% / 19.5 (50%) · Bull 15% / 22.5 (25%).

## 8. Run log

| Run date | Month | Score | V / T / F | Signal | Nifty | Coverage | Notes |
|---|---|---|---|---|---|---|---|
| 19-Nov-2026 | 2026-11 | 51.3 | 47.1 / 62.8 / 36.8 | HOLD | 25,200 | 87% | Baseline. History back-filled Nov-21→Oct-26. +6.3 vs Oct = +5.8 like-for-like (Nov rally) + 0.5 from newly filled fwd PE |
| 19-Nov-2026 (18:47) | 2026-11 | 51.3 | 47.1 / 62.8 / 36.8 | HOLD | 25,200 | 87% | Re-run on request; 19-Nov close not yet published, kept 25,200. Month-end range 47 (−5%) – 55 (+5%); flips to Accumulate below ~24,800 |

## 9. Learnings and pitfalls (read before every run)

1. **Check the year of every search result.** Queries like "Nifty close 19 November" return the same date from the *previous* year (on 19-Nov-2026 every top result was 19-Nov-2025). Put the year in the query, read the article date, and reject any result whose year differs from the run year.
2. **Today's close may not exist yet.** NSE closes at 15:30 IST, and news is indexed a few hours later. If today's close is not confirmed, use the last confirmed close, say so in the headline, and rely on the month-end sensitivity table.
3. **"This month's score" in a month in progress is a prediction.** Answer with the `sens` range and the flip level, not a single number.
4. **Never eyeball attributions.** On 19-Nov-2026, the first report said about half of the +6.3 move came from new indicators; the script's like-for-like split showed only +0.5. Quote the script.
5. **History is reconstructed (±3 pts).** Mid-range readings (45–60) are neutral; the model's value is at extremes. Say this whenever reporting trend or back-test results.
6. **Shared inputs with gold.** DXY, Brent, USD/INR and gold must match `gold-inputs-monthly.csv` for the same month. Refresh them once and use the same values in both models.
7. **Files live in the project, not on disk.** In a new session, `project_read` every file, write it to a working folder, then run. Save back with `project_write` and `local_path`, and append §8.
8. **Routing.** The project instructions name gold only. Until a Nifty line is added (see `claude/asset-mgmt-index.md`), start every Nifty query by reading this file.
