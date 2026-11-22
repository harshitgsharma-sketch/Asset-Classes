# Low-Risk Carry Model — Standard Run Procedure (v1, indicative, 21-Nov-2026)

> **Release status:** v1. Two strategies, 10 indicators, one month, judgment anchors, no back-test, realised vol and dividend yield estimated. Report as **indicative**.

Applies to: "arbitrage fund or liquid fund?", "where to park cash", "should I write covered calls", "is option selling well paid now", "low-risk carry", "everything is Hold, what earns", "post-tax yield on arbitrage". Design: `carry-model-design.md`.

| File (`claude/`) | Role |
|---|---|
| `carry-model-design.md` | Principles, indicators, tax assumptions, weaknesses |
| `carry-run-procedure.md` | This playbook |
| `carry_oscillator.py` | Canonical engine. The only scoring code to use |
| `carry-config.json` | Indicators, anchors, weights, tax scenarios, call strike/tenor/cost (editable) |
| `carry-inputs-monthly.csv` | One row per month of raw inputs |
| `carry-score-log.csv` | Output, regenerated every run |

## 1. Steps

1. **Run order:** gold → Nifty 50 → sectors → global → asset classes → **carry**. It imports the Nifty oscillator and reuses Nifty and asset-class inputs, so use their latest values; if not re-run this month, reuse and flag *(stale: date)*.
2. **Load** engine, config, inputs and log.
3. **Set the tax slab:** `tax.scenario` in the config (default `slab30`). Ask the user once if unknown and record it in §6.
4. **Refresh inputs** (§3). Add or overwrite the run-month row; put every value's date and source in `source`; mark judgment values "est.".
5. **Run** `python3 carry_oscillator.py all` (or `table`, `drivers KEY`, `tax`, `sens`, `chart`). Quote only numbers the script prints.
6. **Report** with the §5 template. Send `carry-oscillator.png` and `carry-score-log.csv`.
7. **Save back** inputs and score log (engine/config only if changed); add a §6 run-log line.

## 2. Fixed conventions

- 1 = carry very attractive, 100 = poor. Standard bands; action lines in the design §3.
- **Shared inputs must equal the other models' same-month values:** `nifty`, `vix` (Nifty i08), `osc_nifty` (Nifty score log `oscillator`); `repo`, `repo_exp1y`, `cpi_exp1y`, `tbill91` (asset-class inputs).
- `arb_ret_1m`, `arb_ret_3m` = **simple, not annualised**, direct-plan returns of the largest arbitrage fund (Kotak Arbitrage) from its latest factsheet; the engine annualises.
- `liquid_ytm` = a large liquid fund's direct-plan YTM; `liquid_ter` its TER.
- `atm_iv` = Nifty near-month ATM implied vol; `rv20` = 20-session realised vol (annualised %). If ATM IV is missing the engine uses India VIX.

## 3. Inputs and sources

| Column | First source | Freq |
|---|---|---|
| nifty, vix, osc_nifty | Nifty model inputs / score log | Monthly |
| repo, repo_exp1y, cpi_exp1y, tbill91 | Asset-class inputs (RBI, OIS est.) | Monthly |
| atm_iv | sahi.com "Nifty 50 ATM IV" page; NSE option chain | Weekly |
| rv20 | NSE historical index data (compute 20-d stdev × √252); stockmojo.in IV-vs-HV page | Weekly |
| nifty_div_yield | NSE Indices Nifty 50 factsheet (div yield) | Monthly |
| liquid_ytm, liquid_ter | Tata / Axis / ABSL liquid fund factsheet (direct); cross-check ABSLMF Daily Fixed Income Tracker 3-m CD/CP | Monthly |
| arb_ret_1m, arb_ret_3m | Kotak Arbitrage Fund page (kotakmf.com, direct growth); Nifty 50 Arbitrage TRI as cross-check | Monthly |

## 4. How to read it

- The arbitrage score is mostly a **tax story**: the post-tax edge (A1) carries the most weight. Run `tax` to show the user's slab; below the 30% slab a liquid fund usually wins.
- The covered-call score is mostly a **volatility story**: run `sens` to show the India VIX level at which it turns Accumulate/Buy.
- A low covered-call score never overrides the Nifty model. If the Nifty scores Buy (≤35), hold uncapped; if it scores Trim/Exit, trim per the Nifty §6 rules rather than writing calls.
- Covered-call yield is the premium received, not a return forecast; report the 1-SD down-month loss and the called-away probability next to it.

## 5. Output template

1. **Headline:** best carry now (strategy → score → signal → action line), tax slab used, data as-of date.
2. **Table** (from `table`): strategy · score · signal · gross yield · post-tax yield · liquid post-tax hurdle · edge vs liquid.
3. **Drivers** for each strategy (from `drivers`): value, score, Leading/Coincident/Lagging, one-line reason.
4. **Tax slab table** (from `tax`) and **VIX sensitivity** (from `sens`) with the flip levels.
5. **Downside give-up:** covered call 1-SD down-month loss, called-away probability, upside cap; arbitrage exit load and negative-spread risk.
6. **Data quality:** estimated inputs, stale imports, §5 design weaknesses.
7. **Caveat line:** v1, indicative, one month, judgment anchors, not investment advice.
8. **Files:** chart PNG and score log.

Plain language, tables, explain jargon the first time (basis, ATM IV, VRP), phone-readable.

## 6. Change log and run log

- 21-Nov-2026: v1 built at the user's request (roadmap item 8). Covered call priced by Black-Scholes with a 1.5-pt call-skew allowance after the first draft (no skew) put C1 at its anchor floor.

| Run date | Month | Arbitrage | Covered call | Tax | Notes |
|---|---|---|---|---|---|
| 21-Nov-2026 | 2026-11 | 43.8 ACCUMULATE (post-tax 5.42% vs liquid 4.77%, +0.66 pp) | 58.9 HOLD (premium 0.79%/m, post-tax 6.37%/yr, 1-SD down month −3.7%) | slab30 | First run. Arbitrage edge disappears at the 20% slab (−0.06 pp). Covered call turns Accumulate at VIX ~18 and Buy at ~20. rv20 and dividend yield est. |

## 7. Learnings and pitfalls

1. Put the **year in every search**: Business Standard "Nifty November futures trade at premium" pages from Nov-2025 rank first; reject them.
2. Fund pages mix dates: Kotak shows NAV to 20-Nov but returns to 31-Oct. Record the returns date.
3. Near-expiry futures premium (e.g. 45 pts with 4 days left) annualises to absurd numbers; use fund returns or the next-month contract.
4. Money-market rates are well above repo in Nov-2026 (3-m CD 7.29% vs repo 5.50%) because liquidity is in deficit; that lifts liquid yields and narrows the arbitrage edge.
