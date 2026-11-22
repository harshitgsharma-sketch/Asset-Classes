# Credit & Fixed-Income Entry/Exit Oscillator (INR investor) — Design (v1, indicative, built 21-Nov-2026)

**Goal:** answer **"when should I lock in rates, and at what duration?"** for an INR investor with a holding period of up to 5 years. It scores seven fixed-income sleeves from **1 (lock in / add) to 100 (stay short / exit)** and adds a duration call, a rate ladder with 12-m horizon returns, and a 5-yr lock-in vs roll vs float comparison.
**Engine:** `fixed_income_oscillator.py` · **Config:** `fixed-income-config.json` · **Inputs:** `fixed-income-inputs-monthly.csv` · **Log:** `fixed-income-score-log.csv` · **Playbook:** `fixed-income-run-procedure.md` · **Chart:** `fixed-income-oscillator.png`.

> Not investment advice. v1: one month of inputs, judgment anchors, no back-test. Report as **indicative**.

## 1. Principles

1. **Same engine as the other models.** Indicator score = clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100); W = Impact × Severity × Reliability × Stability; blank inputs skipped and weights re-normalised within each bucket.
2. **For bonds, "cheap" means high yield vs history *and* a rate cycle that is about to turn down.** Valuation says *what* is cheap; Timing says *whether to lock in now or wait*.
3. **Never contradict the asset-class model.** The Valuation indicators of the 10-yr G-sec, AAA 5-yr, AA 3-yr and 1-yr AAA sleeves (B1–B7) use the same formulas and anchors as `asset-classes-config.json`, so their Valuation buckets equal that model's scores (33.6 / 44.3 / 42.7 / 9.6 on 21-Nov-2026).
4. **Shared inputs are identical** to the Nifty and asset-class rows for the same month: repo, expected repo change (Nifty i03), CPI (i20), Brent (i13), UST 10-yr, US HY OAS (i18), and the asset-class curve (G-sec 10/5/3-yr, AAA 1/5-yr, AA 3-yr, T-bill, 1-yr FD, expected CPI, expected repo path).
5. **Floaters run the other way.** For RBI Floating Rate Savings Bonds, rising rates are a tailwind, so their Timing and Filter scores are flipped (101 − s).

## 2. Buckets and weights (by profile)

| Profile | Sleeves | Valuation | Timing | Filter |
|---|---|---|---|---|
| duration | GSEC_10Y, GSEC_5Y, BANK_FD_5Y | 45% | 40% | 15% |
| credit | CORP_AAA_5Y, CREDIT_AA_3Y | 50% | 35% (+ HY OAS) | 15% |
| short | SHORT_1Y | 70% | 20% | 10% |
| floating | FRSB | 55% | 35% (inverted) | 10% (inverted) |

Bands: ≤20 Strong buy · 21–35 Buy · 36–50 Accumulate · 51–65 Hold · 66–80 Trim · >80 Exit. Each band maps to a plain action per profile (e.g. duration: Lock in now / Accumulate in tranches / Hold, new money short / Trim duration / Exit to short or floating).
**Veto:** oscillator ≤35 while its Timing bucket ≥70 → "Lock-in vetoed: rate cycle still against you; stagger in thirds".

## 3. Indicators (30: 12 shared Timing/Filter + 18 Valuation)

**Shared rate-cycle Timing (T1–T9; high = yields likely to rise)**

| id | Indicator | Type | W | Cheap → Rich |
|---|---|---|---|---|
| T1 | Expected RBI repo change, ~6 m (= Nifty i03) | Leading | 17.5 | −75 → +75 bp |
| T4 | 10-yr G-sec 6-m change (momentum) | Coincident | 14.0 | −75 → +75 bp |
| T2 | Real policy rate: repo − expected CPI | Leading | 12.0 | +2.0 → −1.0 pp |
| T3 | Inflation turn: expected CPI − current CPI | Leading | 9.0 | −1.5 → +1.5 pp |
| T5 | India CPI YoY (= Nifty i20) | Coincident | 5.9 | 2 → 7% |
| T6 | System liquidity, net LAF % NDTL | Leading | 5.1 | +1.5 → −1.0% |
| T7 | Brent (= Nifty i13) | Coincident | 5.1 | $55 → $110 |
| T9 | UST 10-yr | Coincident | 4.5 | 3.0 → 5.5% |
| T8 | FPI net flow into Indian debt, 3 m | Coincident | 4.2 | +₹40k → −₹40k cr |

**Credit Timing:** K1 US HY OAS (= Nifty i18), Leading, W 6.75, 6.0 → 2.5%.
**Supply Filter:** F1 bank credit growth − deposit growth (Lagging, W 5.1, −3 → +5 pp; banks short of deposits sell G-secs and issue CDs) · F2 Centre fiscal deficit, budget year (Lagging, W 6.75, 3.0 → 6.5% GDP).

**Valuation by sleeve**

| Sleeve | Indicators (cheap → rich) |
|---|---|
| GSEC_10Y | B1 real 10-yr yield (3.0 → 0.0 pp) · B2 10-yr − repo (2.0 → 0.0) · B3 level (7.8 → 5.9%) · B4 India − US 10-yr (4.5 → 1.5 pp) — identical to asset-class GSEC_LONG |
| GSEC_5Y | real 5-yr (2.75 → −0.25) · 5-yr − repo (1.75 → −0.25) · level (7.6 → 5.5%) |
| CORP_AAA_5Y | B5 real (3.5 → 0.5) · B6 spread over 5-yr G-sec (120 → 30 bp) — identical to asset-class CORP_AAA |
| CREDIT_AA_3Y | B5 real (4.5 → 1.5) · B6 spread over 3-yr G-sec (250 → 100 bp) — identical to CREDIT_AA |
| SHORT_1Y | B7 1-yr AAA − expected avg repo (1.75 → 0) · B5 real (3.0 → 0.0) — identical to SHORT_DEBT |
| BANK_FD_5Y | D1 real 5-yr FD (2.5 → −0.5) · D2 level (7.5 → 5.5%) · D3 FD − 5-yr G-sec (+25 → −125 bp) |
| FRSB | L1 real coupon (3.0 → 0.5) · L2 coupon − 5-yr G-sec (1.25 → −0.25 pp) |

## 4. Extra outputs (computed by the script)

- **Duration call:** the shared rate-cycle Timing score plus the short / 5-yr / 10-yr oscillators give one verdict: Lock in long · Long cheap but rates rising (thirds) · Lock in medium (3–5-yr ladder) · Stay short (+ floating) · Shorten · Neutral ladder. It prints the triggers to extend duration.
- **Rate ladder:** yield, modified duration, carry over the 91-d T-bill, break-even yield rise over 12 m (carry ÷ duration), and 12-m returns for −100…+100 bp shocks (return ≈ yield − duration × shock). FDs and FRSB are not marked to market.
- **5-yr lock-in comparison:** lock 5-yr G-sec / AAA (net of 0.10 pp/yr expected loss) / bank FD vs roll 1-yr AAA vs FRSB (NSC + 0.35) vs a 10-yr G-sec sold after 5 years, under Bear / Base / Bull rate paths in the config (25/50/25), with a probability-weighted result.

## 5. Known weaknesses (v1)

- One month; no back-test; anchors are estimates of ~2010–26 ranges.
- The Timing bucket is shared, so all fixed-rate sleeves carry the same rate-cycle view; they differ only through Valuation and bucket weights.
- Liquidity (% NDTL), FPI debt flows and the expected repo path are estimates; replace them with RBI DBIE / NSDL FPI / OIS data.
- FD rates are one large bank (HDFC 5-yr); SBI's 5-yr bucket was 6.05% on 9-Oct. Small-finance-bank rates are shown as information only.
- FRSB has a **7-yr lock-in** (early exit only for 60+), which exceeds the 5-yr horizon. It scores well but fits only money that can stay 7 years.
- Everything is **pre-tax**. All sleeves here are taxed at slab rate (no indexation on debt funds bought after Apr-2023), so the ranking survives tax; the tax layer (roadmap item 3) will add post-tax and wrapper effects.
- The 1-yr AAA yield (8.03%) is above the 10-yr G-sec (7.28%) because money markets are tight and a hike is priced. That makes SHORT_1Y look very cheap; B7 already measures it against the expected repo path, not spot repo.

## 6. Roadmap

1. Back-fill monthly inputs 2012→ (FBIL/CCIL curve, RBI DBIE liquidity, NSDL FPI debt, SBI FD history, NSC history) and reset anchors to 5th/95th percentiles.
2. Back-test: does a ≤35 score on GSEC_10Y beat rolling T-bills over 12/36 m, and does the duration call beat a static 5-yr ladder?
3. Use the OIS curve for T1 and `repo_exp1y`; add SDL, 54EC and tax-free PSU sleeves.
4. Feed post-tax returns from the tax/cost layer and target weights from the portfolio allocator.
