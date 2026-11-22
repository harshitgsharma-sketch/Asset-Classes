# India sector facts, 2016–2026: dispersion, persistence, drawdowns and concentration

- **Source:** Our own calculations on Yahoo Finance daily closes for 13 Nifty sector indices and the Nifty 50 (Nov 2016 to Nov 2026; `scripts/research/sector_calendar_stats.py` and `scripts/research/sector_momentum_test.py`), plus NSE, RBI and S&P DJI publications linked below.
- **Added:** 2026-11-22
- **Tags:** research, India, data, dispersion, drawdowns, concentration, credit cycle
- **Relevant models here:** Nifty sectors oscillator; Nifty 50 oscillator.

> Price indices, not total return (dividends excluded). Only 10 years of history, so a drawdown that started before 2016 is cut short, and "longest below a high" is a lower bound. 2026 is year-to-date. Not investment advice.

## 1. The gap between sectors is huge, every year

Calendar-year return minus the Nifty 50, for the best and worst of 13 sector indices:

| Year | Nifty 50 | Best sector | Worst sector | Spread |
|---|---|---|---|---|
| 2017 | +28.6% | Realty +81 pp | Pharma −35 pp | 116 pp |
| 2018 | +3.2% | IT +21 pp | Realty −36 pp | 57 pp |
| 2019 | +12.0% | Realty +17 pp | PSU Bank −30 pp | 47 pp |
| 2020 | +14.9% | Pharma +46 pp | PSU Bank −46 pp | 91 pp |
| 2021 | +24.1% | Metal +46 pp | FMCG −14 pp | 60 pp |
| 2022 | +4.3% | PSU Bank +66 pp | IT −30 pp | 97 pp |
| 2023 | +20.0% | Realty +61 pp | Bank −8 pp | 69 pp |
| 2024 | +8.8% | Pharma +30 pp | FMCG −9 pp | 39 pp |
| 2025 | +10.5% | PSU Bank +20 pp | Realty −27 pp | 47 pp |
| 2026 (to Nov) | −1.3% | Pharma +26 pp | IT −16 pp | 42 pp |

**Average spread: about 67 percentage points a year.** Sector choice can matter more than market timing in any given year, in both directions.

## 2. Last year's winners are a coin flip

For each year, take the four best sectors of the previous year and check whether they beat the Nifty again:

- **17 of 36 (47%) did.** That is no better than chance.
- Last year's four *worst* sectors beat the Nifty the next year 20 of 36 times (56%).
- Clean reversals: none of 2017's top four beat the Nifty in 2018; none of 2019's top four did in 2020; three of 2022's four laggards beat the Nifty in 2023; and all four of 2023's laggards did in 2024.
- SPIVA India found the same in 2025: five of the six sectors that beat the market in 2024 trailed it in 2025 ([S&P DJI](https://www.spglobal.com/spdji/en/documents/spiva/spiva-india-scorecard-year-end-2025.pdf)).

Over 12 months, ranking by trailing 12-month strength, leaders trailed laggards by about 6.5 pp (see the [research note](sector-rotation-research-evidence.md)).

## 3. Sector drawdowns are deep and long

| Index | Worst fall (2016–26) | Longest below a previous high | Now vs its high (Nov 2026) |
|---|---|---|---|
| PSU Bank | −73% | 5.0 years | at high |
| Metal | −64% | 3.2 years | −10% |
| Auto | −62% | 3.9 years | −3% |
| Realty | −56% | 3.5 years | −18% |
| Bank | −48% | 1.0 year | at high |
| IT | −44% | 2.5 years | −32% |
| Infra | −44% | 3.0 years | −1% |
| Fin Services | −44% | 1.7 years | at high |
| Pharma | −42% | 3.7 years | −2% |
| Next 50 | −42% | 2.9 years | −6% |
| Energy | −41% | 2.3 years | −17% |
| Nifty 50 | −38% | 1.3 years | −2% |
| FMCG | −36% | 2.3 years | −27% |
| Consumption | −32% | 2.2 years | −5% |

- Deep cyclicals (PSU Bank, Metal, Auto, Realty) fell 56–73% at some point. The Nifty's worst was −38% (the 2020 Covid crash).
- Several sectors spent 3–5 years below a previous high while the Nifty recovered within about 1.3 years.
- A single-sector position needs to be sized for a 60–70% fall and a multi-year wait.
- **Today's laggards:** IT (−32%) and FMCG (−27%) are furthest below their highs, followed by Realty (−18%) and Energy (−17%).

## 4. The Nifty 50 is heavily concentrated in financials

- Financial services were about **37.7%** of the Nifty 50 in March 2023 and **33.5%** in March 2024. IT was 13–14%, and oil and gas 12–13% ([NSE Nifty 50 whitepaper 2024](https://www.niftyindices.com/docs/default-source/indices/nifty-50/nifty-50-whitepaper-2024.pdf), [2023](https://www.niftyindices.com/docs/default-source/indices/nifty-50/nifty-50-whitepaper_2023.pdf)).
- IT was the largest sector around 2000 at about 25%, and the index had no IT at its 1995 launch ([NSE, 25 years of Nifty 50](https://archives.nseindia.com/content/indices/25_Years_Journey_of_Nifty50_2022-01.pdf)).
- An index fund is therefore already a large bet on banks and NBFCs. A "Bank Nifty plus Nifty 50" portfolio doubles that bet.

## 5. The bank credit cycle in one picture

- Gross NPAs of Indian banks peaked at about **11.2–11.6% in March 2018**, with public-sector banks at about 14.6%. Much of that came from forced recognition after RBI's asset quality reviews ([CRISIL](https://www.crisil.com/en/home/newsroom/press-releases/2018/06/rs5-lakh-crore-slippages-to-npas-in-fiscal-2018-mars-banks-profitability.html), [Business Standard](https://www.business-standard.com/article/finance/bs-banking-annual-2019-the-worst-may-finally-be-over-119121801442_1.html)).
- They fell to about **2.3–2.8% by 2025**, the lowest in roughly 20 years ([PIB backgrounder](https://pib.gov.in/PressReleasePage.aspx?PRID=2201357)).
- **The stock market lined up with that cycle:** PSU Bank was the worst sector in 2019 and 2020 (−30 and −46 pp vs Nifty), near the NPA peak, and the best in 2022 (+66 pp) as NPAs fell and credit growth hit a decadal high of 15% in FY23.
- The sectors model's banking module already tracks credit growth and GNPA direction (design §5.2).

## What this means for the board

Triaged in the [board backlog](board-backlog.md) (research batch, 2026-11-22):

- **Supports existing design:** contrarian relative strength (C8, C16); own-history anchors.
- **Board candidate:** show each sector's **drawdown from its high and years below it** in the sector drawer, next to the score. It is computed from data the parabolic check already downloads daily, and gives context for the "Buy" readings on beaten-down sectors (IT, FMCG today). Display only, no score change.
- **Knowledge only:** Nifty concentration (affects allocation, not entry/exit timing).

## Sources

- Yahoo Finance daily closes (via `scripts/research/`)
- [SPIVA India Year-End 2025](https://www.spglobal.com/spdji/en/documents/spiva/spiva-india-scorecard-year-end-2025.pdf)
- [NSE Nifty 50 whitepaper 2024](https://www.niftyindices.com/docs/default-source/indices/nifty-50/nifty-50-whitepaper-2024.pdf) · [2023](https://www.niftyindices.com/docs/default-source/indices/nifty-50/nifty-50-whitepaper_2023.pdf) · [25 years of Nifty 50](https://archives.nseindia.com/content/indices/25_Years_Journey_of_Nifty50_2022-01.pdf)
- [CRISIL on FY18 NPAs](https://www.crisil.com/en/home/newsroom/press-releases/2018/06/rs5-lakh-crore-slippages-to-npas-in-fiscal-2018-mars-banks-profitability.html) · [Business Standard Banking Annual](https://www.business-standard.com/article/finance/bs-banking-annual-2019-the-worst-may-finally-be-over-119121801442_1.html) · [PIB backgrounder](https://pib.gov.in/PressReleasePage.aspx?PRID=2201357)
