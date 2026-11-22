# Credit & Fixed-Income Oscillator — Standard Run Procedure (v1, indicative, 21-Nov-2026)

> **Release status:** v1. 7 sleeves, 30 indicators, one month of inputs, judgment anchors, no back-test. Report as **indicative** and act only at the extremes (≤35 or ≥66).

Applies to: "when should I lock in rates", "what duration should I buy", G-sec / gilt fund / target-maturity fund, corporate bond or credit-risk fund, bank FD (1–5 yr), RBI Floating Rate Savings Bond, "FD vs debt fund vs FRSB", "is it time to buy long bonds". For a cross-asset "bonds vs equity vs gold" question use the asset-class model instead. Design: `fixed-income-model-design.md`.

| File (`claude/`) | Role |
|---|---|
| `fixed-income-model-design.md` | Principles, indicators and anchors, weaknesses |
| `fixed-income-run-procedure.md` | This playbook |
| `fixed_income_oscillator.py` | Canonical engine. The only scoring code to use |
| `fixed-income-config.json` | Sleeves, indicators, anchors, bucket weights, horizon shocks, 5-yr lock-in paths (editable) |
| `fixed-income-inputs-monthly.csv` | One row per month of raw inputs (wide format) |
| `fixed-income-score-log.csv` | Output, regenerated every run |
| `fixed-income-oscillator.png` | Chart: sleeve oscillators + rate ladder |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → asset classes → **fixed income**. This model reuses the Nifty and asset-class inputs. If they were not re-run this month, reuse their last values and flag them *(stale: date)*.
2. **Load** the engine, config, inputs and log; write them to a working folder.
3. **Refresh inputs** (§3). Add or overwrite the row for the run month (`month` = YYYY-MM). Record every value's date and source in `source`; mark judgment values "est.".
4. **Run** `python3 fixed_income_oscillator.py all` (or `table`, `drivers KEY ...`, `call`, `ladder`, `lockin`, `chart`). Quote only numbers the script prints.
5. **Report** with the §5 template. Send `fixed-income-oscillator.png` and `fixed-income-score-log.csv`.
6. **Save back** inputs and score log (engine and config only if changed); add a §7 run-log line.

## 2. Fixed conventions

- Score 1 = yields high vs history and likely to fall (lock in, add duration); 100 = yields low or likely to rise (stay short / floating).
- **Shared inputs must be identical** to the same month's other models:
  - Nifty inputs: `repo` (repo), `repo_chg_6m` (i03), `cpi_yoy` (i20), `brent` (i13), `us10y`, `hy_oas` (i18).
  - Asset-class inputs: `gsec10`, `gsec5`, `gsec3`, `aaa1y`, `aaa5y`, `aa3y`, `tbill91`, `fd1y`, `cpi_exp1y`, `repo_exp1y`.
  - If the Nifty and asset-class 10-yr G-sec differ (they did on 21-Nov-2026: 7.20 vs 7.28), use the asset-class value so the curve is one snapshot, and flag the gap.
- `gsec10_6m_ago` = the 10-yr G-sec month-end six months earlier, from `nifty-inputs-monthly.csv`.
- `frsb` = NSC rate for the current quarter + 0.35 (resets 1 Jan / 1 Jul).
- `fd5y` = best large-bank (SBI / HDFC / ICICI) general-public 5-yr rate; `sfb5y` = information only.
- `liquidity` = net LAF ÷ NDTL (%; surplus positive). Until DBIE is used: net LAF absorption ÷ ~₹290 lakh cr, est.
- Check after each run that the Valuation buckets of GSEC_10Y, CORP_AAA_5Y, CREDIT_AA_3Y and SHORT_1Y equal the asset-class scores of GSEC_LONG, CORP_AAA, CREDIT_AA and SHORT_DEBT for the same month.

## 3. Inputs and sources

| Column | First source | Freq |
|---|---|---|
| gsec10, gsec5, gsec3, aaa1y, aaa5y, aa3y | Same as the asset-class model (ABSLMF Daily Fixed Income Tracker; Trading Economics India 10Y) | Weekly |
| repo, repo_chg_6m, repo_exp1y, cpi_exp1y | RBI MPC resolution; OIS or economist consensus (as in Nifty i03) | After MPC |
| cpi_yoy | MoSPI CPI (~12th) | Monthly |
| tbill91 | RBI weekly T-bill auction | Weekly |
| fd1y, fd5y, sfb5y | SBI / HDFC rate cards; Upstox, Business Today FD round-ups | Monthly |
| nsc, frsb | Ministry of Finance small-savings notification (quarterly); RBI FRSB press release (half-yearly) | Quarterly |
| liquidity | RBI "Money Market Operations" press release (net liquidity absorbed / injected) | Weekly |
| fpi_debt_3m | NSDL FPI debt (or FAR) monthly net, last 3 months, ₹ '000 cr | Monthly |
| credit_growth, deposit_growth | RBI fortnightly scheduled-bank statement | Fortnightly |
| fiscal_def | Union Budget (BE), revised at the next Budget | Yearly |
| brent, us10y, hy_oas | Nifty inputs (i13, us10y, i18) | Monthly |

## 4. How to read it

- **Valuation** low = yields are high vs history. **Timing** high = rate cycle still rising (wait or stagger). The oscillator blends them; the duration call turns them into one verdict.
- A low score on SHORT_1Y means *park new money short*; it does not say long bonds are expensive. Compare GSEC_5Y and GSEC_10Y to decide when to extend.
- FRSB scores low when its coupon is high vs inflation **and** rates are rising (good for a floater). It has a 7-yr lock-in; recommend it only for money that can stay 7 years, or investors aged 60+.
- Break-even rise (ladder) = how far yields can rise in 12 m before the sleeve does worse than a T-bill. Below ~30 bp is thin cushion.
- The 5-yr lock-in table uses judgment rate paths. Show it as "under these paths", never as a forecast.

## 5. Output template

1. **Headline:** the duration verdict and the cheapest sleeve (score → signal), data as-of date.
2. **Sleeve table** (from `table`): sleeve · oscillator · signal · action · V / T / F · yield · veto.
3. **Rate cycle:** the shared Timing score and its top drivers (from `drivers GSEC_10Y`), each with value, score and Leading / Coincident / Lagging.
4. **Lock-in answer:** what to lock now, at what tenor, and the extend-duration triggers (from `call`).
5. **Rate ladder** (from `ladder`): yield, carry, break-even and ±100 bp returns.
6. **5-yr comparison** (from `lockin`): Bear / Base / Bull and probability-weighted, with the FRSB lock-in and pre-tax caveats.
7. **Data quality:** estimated inputs, stale imports, any shared-input mismatch.
8. **Caveat line:** v1, one month, judgment anchors, pre-tax, not investment advice.
9. **Files:** chart PNG and score log.

Plain language, tables, explain jargon the first time (duration, carry, OAS, FRSB, NDTL), phone-readable.

## 6. Change log

- 21-Nov-2026: v1 built at the user's request (item 6 of the roadmap: credit and fixed income). 7 sleeves, 30 indicators. Valuation B1–B7 copied from the asset-class model. UST 10-yr set so that a high US yield is a headwind (3.0 → 5.5%).

## 7. Run log

| Run date | Month | Verdict | Sleeves (oscillator) | Notes |
|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | STAY SHORT; extend later | SHORT_1Y 24.5 BUY · FRSB 29.3 BUY · GSEC_5Y 44.6 · GSEC_10Y 48.1 ACCUMULATE · AA 3y 51.7 · AAA 5y 52.5 · FD 5y 54.4 HOLD | First run. Rate-cycle Timing 63.4 (late tightening). 5-yr p-wtd: FRSB 7.81 · AAA 7.75 · 10-yr sold at yr 5 7.58 · roll 1-yr 7.30 · 5-yr G-sec 7.12 · 5-yr FD 6.77. V buckets match asset-class 33.6 / 44.3 / 42.7 / 9.6 |

## 8. Learnings and pitfalls

1. Put the **year in every search**; FD round-ups and FRSB articles have identically titled 2025 versions.
2. The 10-yr G-sec differs across models on 21-Nov-2026 (Nifty 7.20 on 19-Nov, asset class 7.28 on 17-Nov, TE 7.24 on 20-Nov). Refresh once and use the same value in all three on the next run.
3. "Up to" FD rates in news are the best tenor, not the 5-yr rate. Read the bank's 5-yr bucket.
4. FRSB's 7-yr lock-in exceeds the toolkit's 5-yr horizon. Always say so when FRSB ranks high.
5. The curve is inverted at the short end (1-yr AAA 8.03 > 10-yr G-sec 7.28) because a hike is priced and liquidity is tight. When the hike is delivered or liquidity eases, SHORT_1Y will re-rate fast; re-run after each MPC.
