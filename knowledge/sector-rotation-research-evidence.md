# Sector rotation: what the research says

- **Source:** Desk research, 2026-11-22: academic papers (abstracts and summaries) plus two tests on our own data. Sources are linked inline and listed at the end.
- **Added:** 2026-11-22
- **Tags:** research, sector rotation, momentum, reversal, business cycle, monetary policy
- **Relevant models here:** Nifty sectors oscillator (C4 macro import, C8 relative strength, C16 3-year relative return).

> Summaries of published research, mostly US data. Where only an abstract or a secondary summary was available, that is stated. Not investment advice.

## The short version

| Claim you often hear | What the evidence says | Strength |
|---|---|---|
| Strong sectors keep outperforming (momentum) | True at short horizons in US data: industry momentum explains much of stock momentum. Weaker in recent samples, and weak in India 2016–2026 on our test. | Mixed |
| Over years, leaders lag and laggards lead (reversal) | Several studies find past-losing industries beat past-winning ones over 3–5 years. Our India test agrees at 12 months. | Fairly strong |
| Rotate by business-cycle phase (financials early, staples late…) | With *perfect* foresight of US recessions it adds about 2.3% a year before costs; realistic timing errors and costs make it statistically indistinguishable from zero. | Weak |
| Rotate by monetary policy (cyclicals when easing, defensives when tightening) | One US study (1973–2005) found 2–5% a year outperformance, stable over time. Not replicated for India here. | Moderate (one study) |
| Momentum is a free lunch | Momentum strategies suffer sudden crashes right after market falls, when beaten-down stocks rebound. | Strong |

## 1. Industry momentum (short horizon)

- **[Moskowitz and Grinblatt (1999), "Do Industries Explain Momentum?"](https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum)**, Journal of Finance. A strong industry momentum effect accounts for much of the individual-stock momentum anomaly. Industry strategies stayed profitable after controlling for size, value and stock momentum. Momentum was strongest at intermediate horizons.
- Later work cited in the same literature finds past industry returns predict the next month's industry returns most strongly, with effects lasting up to a year.
- A Quantpedia-reviewed summary ([Interactive Brokers](https://www.interactivebrokers.com/campus/ibkr-quant-news/an-important-analysis-of-stock-momentum-and-reversal-factors/)) reports that 12-month industry momentum seems to have faded in the most recent sample, while 1-month reversal strengthened. That is a secondary summary only.
- **India:** [Sehgal and Jain (2011)](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html) find momentum profits in Indian sectoral returns, and that part of stock momentum is a sector effect.
- **Our test** (`scripts/research/sector_momentum_test.py`, 13 Nifty sector indices, Nov 2016 to Nov 2026). Ranking sectors by 6-month strength against the Nifty 50, the top third beat the bottom third by only −0.2 to +1.0 pp over the next 1–6 months. In other words, no usable momentum in this window.

## 2. Long-term industry reversal

- [Wu and Mazouz](https://orca.cardiff.ac.uk/88899/3/final_revised_draft7.pdf) (UK stocks) find stocks in past-losing industries beat those in past-winning industries over the next five years, even after controlling for stock and industry momentum, and point to mispricing as the likely cause.
- [Bornholt, Gharaibeh and Malin (2015)](https://ideas.repec.org/a/eee/intfin/v38y2015icp65-78.html) report strong industry return reversals that persist for years.
- **Our test:** ranking by 12-month strength, the top third *trailed* the bottom third by 6.5 pp over the next 12 months and 7.3 pp over the next 36.
- **SPIVA India Year-End 2025** ([S&P DJI](https://www.spglobal.com/spdji/en/documents/spiva/spiva-india-scorecard-year-end-2025.pdf)): of the six sectors that beat the S&P India BMI in 2024, five trailed it in 2025. Energy, Financials and Materials, which lagged in 2024, were strong outperformers in 2025.

**Why it matters here:** the sectors model treats 6-month relative strength (C8) and 3-year relative return (C16) as contrarian. Both the literature and our data support that for a holding period of up to 5 years.

## 3. Business-cycle rotation

- **[Stangl, Jacobsen and Visaltanachoti](https://mro.massey.ac.nz/items/ccadcb8d-2658-456b-9aab-4ba840fba845), "The myth of business cycle sector rotation"** (US, 1948–2007, 48 industries, NBER cycles), as summarised by [CXO Advisory](https://www.cxoadvisory.com/economic-indicators/perfect-sector-rotation):
  - With perfect foresight of the cycle, the conventional rotation beat the market by 2.3% a year before costs.
  - Being 1–2 months early or late cut that to 1.0–2.2%.
  - After trading costs, 1.1–1.9% a year, statistically indistinguishable from zero.
  - A follow-up by Molchanov and Stangl (2023) reaches the same conclusion.
- **Fidelity's business-cycle approach** ([2020 paper](https://www.fidelity.com/webcontent/ap101883-markets_sectors-content/21.01.0/business_cycle/Business_Cycle_Sector_Approach_2020.pdf)) maps US sectors to early, mid, late and recession phases using cycles since 1962. Fidelity itself cautions that no sector has behaved the same way in every cycle, and that cycles sometimes skip or repeat phases.
- **India check** (see the [flat-markets note](flat-markets-are-not-dead-markets.md)): autos and pharma led the 2008–14 flat phase and lagged in 2018–21, so the textbook sequence is not reliable here either.

## 4. Monetary-policy rotation

- **Conover, Jensen, Johnson and Mercer, "Sector Rotation and Monetary Conditions"** (Journal of Investing, 2008; US 1973–2005; summarised by [CXO Advisory](https://www.cxoadvisory.com/?p=1509) and [InvestmentNews](https://www.investmentnews.com/industry-news/investors-advised-to-monitor-fed-discount-rate-decisions/11262)):
  - The strategy tilts to cyclicals when the Fed starts easing and to defensives when it starts tightening.
  - Cyclicals averaged about 20.3% a year in easing periods and 2.3% in tightening periods.
  - The rotation beat the market by about 4.9% a year in tightening periods and 2.3% in easing periods, with similar results in both halves of the sample.
- Simpler and more observable than business-cycle phases, because a rate cut or hike is a known event rather than a forecast.

## 5. Momentum crashes

- **[Daniel and Moskowitz, "Momentum Crashes"](https://www.nber.org/papers/w20439)** (JFE 2016): momentum strategies crash in "panic" states, after market declines when volatility is high, and these crashes coincide with sharp rebounds. After falls, past losers carry betas above 3 and past winners below 0.5, so a rebound hits a winners-minus-losers bet hard. Scaling momentum exposure down when volatility is high reduces the damage.
- Practical meaning: rotating into whatever has led is most dangerous just after a market fall.

## What this means for the board

Triaged in the [board backlog](board-backlog.md) (research batch, 2026-11-22):

- **Already covered and supported:** the contrarian treatment of sector relative strength (C8, C16).
- **Board candidate:** an RBI policy-direction input (easing vs tightening) for the cyclical and defensive families. Check first whether the Nifty 50 model's Timing bucket, imported as C4, already captures it.
- **Knowledge only:** business-cycle phase rotation (weak after costs) and momentum crashes (relevant if a momentum overlay is ever added).

## Sources

- [Moskowitz & Grinblatt 1999 (AQR copy)](https://www.aqr.com/Insights/Research/Journal-Article/Do-Industries-Explain-Momentum) · [RePEc](https://ideas.repec.org/a/bla/jfinan/v54y1999i4p1249-1290.html)
- [Sehgal & Jain 2011](https://www.emerald.com/insight/content/doi/10.1108/09727981111129327/full/html)
- [Wu & Mazouz](https://orca.cardiff.ac.uk/88899/3/final_revised_draft7.pdf) · [Long-term industry reversals (JBF 2016)](https://ideas.repec.org/a/eee/jbfina/v68y2016icp236-250.html) · [Bornholt et al. 2015](https://ideas.repec.org/a/eee/intfin/v38y2015icp65-78.html)
- [Stangl et al., Massey](https://mro.massey.ac.nz/items/ccadcb8d-2658-456b-9aab-4ba840fba845) · [CXO summary](https://www.cxoadvisory.com/economic-indicators/perfect-sector-rotation)
- [Fidelity business cycle approach 2020](https://www.fidelity.com/webcontent/ap101883-markets_sectors-content/21.01.0/business_cycle/Business_Cycle_Sector_Approach_2020.pdf)
- [Conover et al. (CXO)](https://www.cxoadvisory.com/?p=1509) · [InvestmentNews](https://www.investmentnews.com/industry-news/investors-advised-to-monitor-fed-discount-rate-decisions/11262)
- [Daniel & Moskowitz, Momentum Crashes (NBER)](https://www.nber.org/papers/w20439)
- [SPIVA India Year-End 2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-india-scorecard-year-end-2025.pdf)
