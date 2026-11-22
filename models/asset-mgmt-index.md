# Asset Mgmt — Model Index and Query Routing (read first)

This project holds entry/exit oscillators for INR investors with a holding period of 5 years or less. All use the same engine: 1 = cheap/buy and 100 = rich/sell, with the bands ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.

| Asset | Ask about | Playbook (follow exactly) | Engine | Inputs | Scenarios / config | Log | Design |
|---|---|---|---|---|---|---|---|
| Gold | gold score, update, buy/sell, trend, outlook | `claude/gold-run-procedure.md` | `claude/gold_oscillator.py` | `claude/gold-inputs-monthly.csv` | `claude/gold-scenarios.json` | `claude/gold-score-log.csv` | `claude/gold-valuation-model.md` |
| Nifty 50 | Nifty / Indian equity score, update, buy/sell, trend, outlook | `claude/nifty-run-procedure.md` | `claude/nifty_oscillator.py` | `claude/nifty-inputs-monthly.csv` | `claude/nifty-scenarios.json` | `claude/nifty-score-log.csv` | `claude/nifty-model-design.md` |
| 20 Nifty sector / size / theme indices (v1) | sector or index score, Bank Nifty, midcap/smallcap valuation, overweight/underweight, sector rotation | `claude/nifty-sectors-run-procedure.md` | `claude/sector_oscillator.py` | `claude/nifty-sectors-inputs-monthly.csv` | `claude/nifty-sectors-config.json` | `claude/nifty-sectors-score-log.csv` | `claude/nifty-sectors-model-design.md` (+ doc https://claude.ai/artifact/JsKitKkpVfAGR9Fp6o39fX) |
| Global indices, top-20 economies (v1.0: 23 markets + MSCI ACWI, Nifty 50 ranked like any market) | any equity-market score, 5-yr entry/exit, entry plan, expected return, invest abroad, country over/underweight, "rate all markets on valuation" (`python3 global_oscillator.py valuation`) | `claude/global-indices-run-procedure.md` | `claude/global_oscillator.py` | `claude/global-indices-inputs-monthly.csv` + `claude/global-indices-valuation-history.csv` | `claude/global-indices-config.json` | `claude/global-indices-score-log.csv` + `claude/global-indices-valuation-log.csv` | `claude/global-indices-model-plan.md` (§10 roadmap) |
| **All asset classes for an INR investor (v1, valuation only)**: Indian large/mid/small caps, global & US equity, gold, silver, long G-secs, AAA, AA credit, short-term debt, cash, REITs, residential property, US Treasuries (per-trust REIT/InvIT and rent-vs-buy questions → real assets row) | "rate all asset classes", cheapest asset, equity vs debt vs gold vs property, where to put new money, allocation tilt, silver / bonds / FD / REIT / property valuation | `claude/asset-classes-run-procedure.md` | `claude/asset_class_oscillator.py` | `claude/asset-classes-inputs-monthly.csv` | `claude/asset-classes-config.json` | `claude/asset-classes-score-log.csv` | `claude/asset-classes-model-design.md` |
| **Real assets (v1, indicative)**: listed REITs, SM-REITs and InvITs (12 trusts) + residential property by city + rent-vs-buy calculator | REIT / InvIT / SM-REIT score, "is Embassy / IndiGrid cheap", REIT vs InvIT yield, real-estate income, "rent or buy a house", rent-vs-buy on my numbers, "is property in <city> expensive" | `claude/real-assets-run-procedure.md` | `claude/real_assets_oscillator.py` (`all`, `cities`, `rentbuy`) | `claude/real-assets-inputs-monthly.csv` | `claude/real-assets-config.json` + `claude/real-assets-rentbuy-scenarios.json` | `claude/real-assets-score-log.csv` + `claude/real-assets-city-log.csv` + `claude/real-assets-rentbuy-log.csv` | `claude/real-assets-model-design.md` |

**Sector model is v1 (built 20 Nov 2026):** one month of scores, 7 of 17 design core indicators, no back-test. Report it as indicative; see its run procedure §7.

**Global model is v1.0 (21 Nov 2026):**
- Headline: a 5-yr score (V 75 / F 15 / M 10, local currency) plus an entry plan (lump sum vs tranches) and a rough expected INR return net of cost.
- 10 markets have 3–6 measured valuation inputs (forward P/E, CAPE, dividend yield vs own history); 13 rest on a single one.
- No back-test yet; it is blocked until a price/return data source is connected.
- The `valuation` column in its score log is now the v1.0 cycle-adjusted Valuation bucket (G1–G7).

Report it as indicative; see its run procedure §7 and §9.

**Asset-class model is v1 (21 Nov 2026):** valuation only, 15 assets / 37 indicators, imports the Valuation buckets of the gold, Nifty, sector and global models; judgment anchors, one month, no back-test. Report as indicative; see its run procedure §8 and design §4.

**Real-assets model is v1 (21 Nov 2026), indicative:** 12 listed trusts scored on yield vs G-sec, price vs NAV, distribution growth, leverage and timing; 9 cities scored with the asset-class RESI_RE anchors; rent-vs-buy calculator on the user's inputs (old/new tax regime). One month, judgment anchors, no back-test. Report as indicative; see its run procedure §4 and design §5. For a bare "REIT valuation" question, the asset-class REIT row is the cross-asset view and this model is the per-trust view.

**Automation:** the scheduled task "Asset Mgmt monthly model refresh" runs the models in the run order below at 11:13 IST on the 3rd of each month. The first run is on 3-Dec-2026.

## Every query: same steps, same output

1. Identify the asset and open its playbook. Read its "Learnings and pitfalls" section first (Nifty §9, sectors §9, global §9, asset classes §8).
2. `project_read` the engine, inputs, scenarios/config, history files and log, and write them to a working folder. Nothing persists on disk between sessions.
3. Refresh stale inputs by web search, putting the **year in every query** and rejecting results whose date is from another year.
4. Run the engine (`python3 <engine> all`). Report **only numbers the script prints**. Never estimate them by eye.
5. Answer in the playbook's §5 output template, in plain language with tables, tagging each driver Leading / Coincident / Lagging.
   - If the month is still in progress, the headline is a month-end prediction with a range (gold, Nifty 50).
   - Gold/Nifty: include the yearly 5-year trend table and the last 12 months.
6. Send the chart PNG (if any) and score log. Save the updated inputs, log and run-log line back to the project.

## Shared conventions

- DXY, Brent, USD/INR and gold price are inputs to gold and Nifty 50. Use identical month-end values in both CSVs.
- The sector model imports the Nifty 50 model's Timing bucket (C4) and reuses its Brent, USD/INR, repo-path and MTF inputs, so run Nifty 50 first.
- The global model reuses the Nifty inputs' HY spread (i18), DXY, Brent, USD/INR, repo, expected repo change and G-sec, plus India CPI, on its GLOBAL and NIFTY50 rows. The Nifty 50 is ranked in it like any other market; no vs-Nifty column is reported.
- The asset-class model imports the Valuation buckets and oscillators of gold, Nifty 50, Midcap 150 / Smallcap 250 (sectors) and ACWI / S&P 500 (global), and reuses Nifty close/EPS, gold, silver, USD/INR, INR REER (Nifty i31), repo and CPI.
- The real-assets model reuses the asset-class MACRO inputs (10-yr G-sec, repo, expected repo, home-loan rate, income CAGR). Its market-cap-weighted listed-REIT yield is the candidate value for the asset-class `reit_yield` input.
- **Run order: gold → Nifty 50 → sectors → global → asset classes → real assets.**
- History before Nov-2026 is reconstructed (±3 points) for gold/Nifty; sectors, global and asset classes have no score history yet. Mid-range scores are neutral; the models are most useful at extremes.
- Not investment advice. Cheap/rich anchors are judgment-based.

## Suggested project-instructions text (to be added by the user in project settings)

> For any question about gold, the Nifty 50, the Nifty sector/size/theme indices, global equity indices, asset classes in general, or REITs / InvITs / property / rent-vs-buy (score, update, buy/sell, trend, outlook, overweight/underweight, invest abroad, valuation ranking, expected return, "rate all asset classes", allocation tilt), first read claude/asset-mgmt-index.md, then follow that asset's run procedure exactly. Score only with its oscillator script, report in its §5 output template, and save the updated inputs, score log and run log back to the project.
