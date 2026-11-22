# Asset-Class Valuation Model (INR investor) — Design (v1, built 21-Nov-2026)

**Goal:** rate every main asset class open to someone living in India from **1 (cheap vs its own history) to 100 (rich)**, so they can be compared side by side and tilted against a strategic allocation. Holding period up to 5 years, same as the other project models.
**Engine:** `asset_class_oscillator.py` (same scoring family as gold / Nifty / sectors / global). **Config:** `asset-classes-config.json`. **Inputs:** `asset-classes-inputs-monthly.csv`. **Log:** `asset-classes-score-log.csv`. **Playbook:** `asset-classes-run-procedure.md`.

> Not investment advice. Anchors are judgment-based estimates of 10–20-year ranges until back-filled.

## 1. Principles

1. **Each asset is judged against its own history**, never against another asset's raw yield or PE. A 4% rental yield and an 8% bond yield can both be "fair".
2. **Reuse, don't re-score.** Where the project already has a model (Nifty 50, sector, global, gold), its **Valuation bucket is imported** as the heaviest indicator, so this model cannot contradict them. Cross-asset indicators are added on top.
3. **One cross-asset yardstick per asset**: yield or earnings yield vs the 10-yr G-sec, or a real (inflation-adjusted) yield. That is what makes a bond, a REIT and an equity comparable.
4. **Currency matters for foreign assets.** Foreign assets carry an INR-REER indicator: a weak (cheap) rupee makes foreign assets dear to buy.
5. **Valuation only.** Timing and filter signals live in the dedicated models; their full oscillator is shown next to the valuation score where one exists.

## 2. Engine

- Indicator score = clamp(1 + 99 × (x − cheap)/(rich − cheap), 1, 100). High = expensive.
- Weight W = Impact × Severity × Reliability × Stability. Blank inputs are skipped and weights re-normalised. An asset with only one live indicator moves half-way to 50 (thin rule).
- Labels: ≤20 Very cheap · 21–35 Cheap · 36–50 Fair, cheap side · 51–65 Fair, rich side · 66–80 Expensive · >80 Very expensive.
- Tilt vs strategic weight: ≤35 Overweight (add) · 36–50 Neutral, lean add · 51–65 Neutral, lean trim · ≥66 Underweight (trim).
- Information columns (not scored): running income yield of each asset, and the asset's own-model oscillator and signal.

## 3. Universe and indicators (15 assets, 37 indicators)

| Asset | Indicators (cheap → rich anchor) | Import |
|---|---|---|
| Nifty 50 | E1 Nifty Valuation bucket (1→100) · E2 earnings yield − 10-yr G-sec (+0.5 → −4.0 pp) | Nifty model V |
| Midcap 150 | E1 sector Valuation bucket · E3 PE ÷ Nifty PE (0.9 → 1.6x) · E2 EY − G-sec (−1 → −5 pp) | sector model V |
| Smallcap 250 | E1 · E3 (0.9 → 1.7x) · E2 (−1 → −5.5 pp) | sector model V |
| Global equity (ACWI, INR) | E1 global ACWI Valuation bucket · X1 INR REER (106 → 90) | global model V |
| US equity (S&P 500, INR) | E1 global S&P Valuation bucket · E4 fwd EY − UST 10-yr (+5 → −1 pp) · X1 | global model V |
| Gold (INR) | M1 gold Valuation bucket · M2 INR price vs 36-m avg (−10 → +40%) | gold model V |
| Silver (INR) | M3 gold/silver ratio (95 → 55) · M2 vs 36-m avg (−15 → +60%) · M1 gold V (monetary-metal level) | gold model V |
| Long G-secs (10-yr) | B1 real yield vs expected CPI (3.0 → 0.0 pp) · B2 10-yr − repo (2.0 → 0.0) · B3 yield level (7.8 → 5.9%) · B4 India − US 10-yr (4.5 → 1.5 pp) | — |
| AAA corporate (~5-yr) | B5 real yield (3.5 → 0.5 pp) · B6 spread over G-sec (120 → 30 bp) | — |
| AA credit (~3-yr) | B5 real yield (4.5 → 1.5 pp) · B6 spread (250 → 100 bp) | — |
| Short-term debt (1-yr AAA/CDs) | B7 1-yr AAA − expected avg repo next 12 m (1.75 → 0 pp) · B5 real yield (3.0 → 0.0) | — |
| Cash (liquid / T-bill / FD) | C1 real 91-d T-bill (2.5 → −2.0 pp) · C2 real 1-yr FD (2.5 → −2.0) | — |
| Listed REITs | R1 distribution yield (8.0 → 5.5%) · R2 yield − 10-yr G-sec (+1.5 → −1.5 pp) | — |
| Residential property | R3 rental yield − home-loan rate (−2 → −6 pp) · R4 rental yield (5.0 → 2.8%) · R5 price CAGR − income CAGR (−3 → +5 pp, Lagging) | — |
| US Treasuries / TIPS (INR) | F1 10-yr TIPS real yield (2.5 → −0.5%) · F2 US real − India real (+1.5 → −2.0 pp) · X1 INR REER | — |

"Expected CPI" = the 12-month-ahead CPI path (RBI projection), not the last print, so real yields look forward.
**Excluded:** crypto (no cash flow / valuation anchor), InvITs (add with a yield series), SGB primary (discontinued).

## 4. Known weaknesses (v1)

- One month of data; no back-test. Anchors are estimates (§3), not computed percentiles.
- Real estate inputs are city-level surveys (Anarock, Knight Frank) and lag; reliability set low (0.5–0.625).
- REIT history is short (listed since 2019) and REIT yields re-rated as the market matured — partly a regime change, like peripheral-Europe banks in the global model.
- US-equity E1 already contains an ERP indicator (G2); E4 adds the level, so ERP is partly double-counted.
- Short-term debt reads "very cheap" partly because money-market liquidity is tight and hikes are priced; the B7 adjustment uses an estimated repo path.
- Silver M2 uses a 36-month average after a huge 2025–26 spike; replace it with a 10-yr real-price anchor.

## 5. Roadmap

1. Back-fill monthly inputs 2016→ (CCIL, FBIL, RBI DBIE, NSE, FRED) and reset anchors to 5th/95th percentiles.
2. Back-test: does a ≤35 score beat cash in INR over 12/36 m, and ≥66 lag?
3. Add InvITs, international REITs, and an "expected 5-yr INR return" column (yield + growth − valuation drift).
4. Allocation view: strategic weights ± tilt by score (plan phase 4 of the global model).
