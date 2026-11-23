# NSE index history (month-end)

Official NSE Indices data, taken from the Historical Data report on niftyindices.com with the `nse-index-data` Claude skill. One value per month: the last trading day.

| File | Series | Columns |
|---|---|---|
| `tri_large.csv`, `tri_mid.csv`, `tri_small.csv` | Total Return Index: Nifty 50, Midcap 150, Smallcap 250 (Apr 2005 →) | Date, TRI |
| `pe_large.csv` | Nifty 50 valuation (Jan 2005 →) | Date, P/E, P/B |
| `pe_mid.csv` | **Nifty Midcap 100** valuation (Jul 2005 →): proxy, because Midcap 150 valuation starts only Apr 2016 | Date, P/E, P/B |
| `pe_small.csv` | **Nifty Smallcap 100** valuation (Mar 2011 →): proxy, because Smallcap 250 valuation starts only Apr 2016 | Date, P/E, P/B |
| `nse_sector_data.csv` | Long format, 28 series: `pe_<x>` (v1 P/E, v2 P/B, v3 div yield) and `tri_<x>` (v1 TRI) for the indices above plus Bank, Auto, FMCG, IT, Pharma, Healthcare, Metal, Realty, Financial Services, PSU Bank, Private Bank, Media, Oil & Gas, Consumer Durables | series, date, v1, v2, v3 |

In the first six files the date is stored as the 28th of the month. `nse_sector_data.csv` has the real trading dates.

**Known gaps (Nov 2026):**
- TRI not yet fetched for Financial Services, PSU Bank, Private Bank, Media, Oil & Gas and Consumer Durables. NSE throttled requests partway through.
- Index P/E is unusable when constituents post losses (Smallcap 100 2014–2020, Midcap 100 2020–21, Auto 2020–21, Bank 2018–19). Use P/B, and treat P/E above 80 as missing.

Checks: `python3 scripts/nse_sector_report.py models/nse-history/nse_sector_data.csv`. The market-cap rotation backtest that uses these files is in `research/market-cap-rotation/`.
