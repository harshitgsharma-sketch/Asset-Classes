# Real-Assets Model (INR investor) — Design (v1, indicative, built 21-Nov-2026)

**Goal:** two tools for real assets, holding period up to 5 years, same conventions as the other project models.
1. **Listed REITs, SM-REITs and InvITs:** an entry/exit oscillator per security, **1 = cheap/buy, 100 = rich/sell**.
2. **Residential property:** a city valuation score (identical anchors to the asset-class model's RESI_RE row) and a **rent-vs-buy calculator** on the user's own numbers.

**Engine:** `real_assets_oscillator.py` · **Config:** `real-assets-config.json` · **Inputs:** `real-assets-inputs-monthly.csv` (long format) · **Scenarios:** `real-assets-rentbuy-scenarios.json` · **Logs:** `real-assets-score-log.csv`, `real-assets-city-log.csv`, `real-assets-rentbuy-log.csv` · **Chart:** `real-assets-scores.png` · **Playbook:** `real-assets-run-procedure.md`.

> Not investment advice. Anchors are judgment-based (listing-to-date ranges; Indian REITs listed from 2019, InvITs from 2017) until back-filled.

## 1. Principles

1. **Yield vs the risk-free rate first.** Every trust is judged first on distribution yield minus the 10-yr G-sec, the same yardstick the asset-class model uses for REITs (R2). Office-REIT anchors are identical (+1.5 → −1.5 pp), so the two models agree on that leg.
2. **Price vs NAV is the second anchor.** The independent valuer's NAV (fair value of the buildings or concessions less debt) is the closest thing to a book value. A discount says the market prices the assets below appraisal.
3. **Growth and leverage filter the yield.** A high yield with falling distributions or heavy debt is a value trap, not a bargain.
4. **Families, not one ruler.** Office REITs, the retail REIT, SM-REITs, power InvITs and road InvITs have different normal yields. Road InvITs own finite-life concessions, so part of each payout is return of capital and their "normal" yield is higher.
5. **Tax shown, not scored.** Distributions mix interest (slab), dividends (exempt if the SPV is on the old corporate tax regime, slab otherwise) and debt repayment (reduces cost). A post-tax yield column is shown at the user's slab.
6. **Property is a decision, not a ticker.** For a home, the useful output is "rent or buy, on my numbers", plus whether the city is cheap or rich vs its own history.

## 2. Part 1 engine (listed trusts)

- Indicator score = clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive/headwind.
- W = Impact × Severity × Reliability × Stability. Blank inputs skipped and weights re-normalised inside each bucket; a missing bucket drops out and the others are re-weighted. A bucket resting on one live indicator moves only half-way from 50 (thin rule).
- **Buckets:** Valuation 55% · Filter 25% · Timing 20%.
- **Signal bands:** ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit.
- **Falling-knife veto:** oscillator ≤35 with Filter ≥70 → "ACCUMULATE (veto)".
- Yield = latest quarterly DPU × 4 ÷ price (annualised run-rate, not trailing 12 m).

| ID | Indicator | Bucket | Type | I·S·R·St | Office REIT | Retail REIT | SM-REIT | Power InvIT | Road InvIT |
|---|---|---|---|---|---|---|---|---|---|
| V1 | Yield − 10-yr G-sec (pp) | V | Leading | 5·4·.875·1 | +1.5 → −1.5 | +1.0 → −2.0 | +3.0 → 0.0 | +5.0 → +1.5 | +6.0 → +2.0 |
| V2 | Price ÷ latest NAV (x) | V | Leading | 4·4·.75·.875 | 0.80 → 1.15 | 0.85 → 1.20 | 0.85 → 1.15 | 0.85 → 1.25 | 0.75 → 1.15 |
| V3 | Yield level (%) | V | Leading | 3·3·.75·.75 | 8.0 → 5.5 | 7.0 → 4.5 | 10.0 → 7.5 | 13.0 → 9.0 | 14.0 → 9.5 |
| F1 | DPU growth, latest quarter YoY (%) | F | Lagging | 4·3·.75·.75 | +12 → −6 | +12 → −6 | +5 → −10 | +8 → −8 | +8 → −12 |
| F2 | Net debt ÷ asset value (%) | F | Lagging | 3·3·.875·1 | 15 → 45 | 15 → 45 | 0 → 45 | 40 → 70 | 40 → 70 |
| T1 | Expected repo change, next 12 m (bp) | T | Leading | 4·3·.75·1 | −75 → +50 (all) | | | | |
| T2 | Position in 52-week range (%) | T | Coincident | 3·3·.625·.75 | 0 → 100 (all) | | | | |

Cheap → rich anchor shown. T1 = (`repo_exp1y` − `repo`) × 100, the same macro inputs as the asset-class model.

**Universe (v1, 12):** office REITs Embassy, Mindspace, Brookfield India, Knowledge Realty, Bagmane Prime; retail REIT Nexus Select; SM-REITs PropShare Platina and Titania; power InvITs IndiGrid and Powergrid InvIT; road InvITs IRB InvIT and Capital Infra Trust.

**Information outputs:** distribution yield, spread vs G-sec, P/NAV, DPU growth, post-tax yield = yield × (1 − slab × taxable share), market-cap-weighted listed-REIT yield (a candidate for the asset-class model's `reit_yield` input) and P/NAV, market-cap-weighted InvIT yield.

## 3. Part 2a — city valuation (consistency with the asset-class model)

Score per city = the asset-class RESI_RE formula with the same anchors and weights:
R3 gross rental yield − home-loan rate (−2 → −6 pp, W 12.5) · R4 rental yield (5.0 → 2.8%, W 5.6) · R5 price CAGR − nominal income CAGR (−3 → +5 pp, W 6.0).
City inputs: Anarock gross yields at Q2-2026 and the 2019 → Q2-2026 price change (6.5 years); income CAGR 10.5% and home loan 8.0% are the asset-class inputs. Cities: Mumbai, Delhi, Gurugram, Noida, Bengaluru, Hyderabad, Pune, Chennai, Kolkata.

## 4. Part 2b — rent-vs-buy calculator

Month-by-month simulation over the holding period. Both sides start with the same cash.
- **Buyer:** pays down payment + stamp duty & registration (city default) + brokerage (+ GST if under construction), then EMI, maintenance and property tax. Old tax regime: interest deduction up to ₹2 lakh a year (Income-tax Act 2025 s.22(2), ex-24(b)) and, if `use_80c`, principal up to ₹1.5 lakh; loses any HRA saving (`hra_tax_saving_per_yr`). New regime: no deduction for a self-occupied home. On sale: selling cost, outstanding loan, capital-gains tax (12.5% + cess if held more than 24 months, else slab).
- **Renter:** pays a security deposit (returned at the end, no interest) and rent (+ brokerage, as months per year), growing each year; invests the rest of the starting cash and every month's difference (owning cost − rent) at `alt_return`, taxed at `alt_tax` on gains at the end.
- **Outputs:** both net worths, the gap (₹ and % of price), the **break-even price growth** (the yearly appreciation that makes buying equal to renting), a sensitivity grid (price growth 0/3/6/9% × hold 3/5/10 yrs) and a **score**: renter's advantage as % of price mapped −15% → 1 (buy clearly better) to +25% → 100 (rent clearly better). Bands: ≤20 BUY clearly better · 21–35 Buy better · 36–50 Close, lean buy · 51–65 Close, lean rent · 66–80 Rent better · >80 RENT clearly better.
- **Defaults** (config `rent_vs_buy.defaults`): 20% down, 8.0% for 20 yrs, hold 5, price and rent growth 6%, maintenance 0.35% + property tax 0.10% of value a year, buy brokerage 1%, sell cost 2%, deposit 3 months, rent brokerage 0.5 month a year, alternative return 9% pre-tax with 12.5% tax on gains, new regime, slab 31.2%.

## 5. Known weaknesses (v1)

- One month of data, no back-test. Anchors are judgment, not percentiles; REIT history is short (2019→) and yields re-rated as the market matured.
- **V1 and V2 often disagree for REITs:** yields are below the G-sec (rich on V1) while units trade at a 10–20% discount to NAV (cheap on V2). NAV depends on the valuer's cap rates, which lag market rates.
- Yield uses one quarter × 4. Seasonal or one-off quarters (for example Capital Infra Trust's −29% YoY) distort V1/V3/F1.
- NAV missing for Bagmane and stale (Mar-2026) for IRB InvIT; LTV missing for Embassy, Brookfield, KRT, Powergrid InvIT and IRB InvIT.
- SM-REITs have no live traded price: yields are on the ₹10 lakh issue price (est.), so the timing and P/NAV legs are blank.
- Taxable share of distributions is a family default where the component split was not sourced.
- T1 (repo path) is the same for all trusts and currently adds a uniform headwind.
- City rent yields for Pune, Chennai and Kolkata are estimates; city stamp duty is approximate (male buyer) and must be checked on the state IGR site.
- Rent-vs-buy ignores the non-financial value of owning, rent-control and eviction risk, renovation spend, and the old regime's ₹2 lakh loss set-off rules for let-out property.

## 6. Roadmap

1. Back-fill quarterly DPU, NAV and prices since listing (NSE filings) and reset anchors to 5th/95th percentiles; back-test ≤35 vs cash over 12/36 m.
2. Use trailing-12-m DPU once four quarters are on file; add occupancy and WALE for REITs, concession life left for road InvITs.
3. Feed the market-cap-weighted REIT yield to the asset-class model's `reit_yield` each month and add an InvIT row there.
4. Add more InvITs (Bharat Highways, Indus Infra, NHIT, Cube) and newly listed SM-REITs.
5. Rent-vs-buy: add under-construction timeline (pre-EMI), a second-home/let-out mode, and city price-growth forecasts.
