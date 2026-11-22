# Knowledge

Notes from videos, articles and books that inform the Entry/Exit Board models. They can be read here on GitHub, or in the **Knowledge** tab of the site.

**Start here:**
- [Sector investing playbook](sector-investing-playbook.md): the rules the notes add up to.
- [Board backlog](board-backlog.md): what moved into the board and why.

### Research notes

| Note | Source | Added | Tags |
|---|---|---|---|
| [Sector rotation: what the research says](sector-rotation-research-evidence.md) | Desk research (academic papers, SPIVA, our tests) | 2026-11-22 | momentum, reversal, business cycle, monetary policy |
| [Sector froth: fund launches, IPO waves and capex booms](sector-froth-signals.md) | Desk research (papers, AMFI, Morningstar) | 2026-11-22 | froth, thematic funds, IPO waves, capital cycle |
| [Valuing cyclical sectors](valuing-cyclical-sectors.md) | Desk research (Lynch, Marathon, McKinsey) | 2026-11-22 | valuation, cyclicals, capital cycle, ROIC |
| [India sector facts, 2016–2026](india-sector-facts-2016-2026.md) | Our data + NSE, RBI, S&P | 2026-11-22 | dispersion, persistence, drawdowns, concentration |

### Video notes

| Note | Source | Added | Tags |
|---|---|---|---|
| [Flat markets are not dead markets: sectors keep rotating](flat-markets-are-not-dead-markets.md) | [WeekendInvesting (YouTube)](https://www.youtube.com/watch?v=90xkdiThhcY) | 2026-11-22 | sector rotation, consolidation, defensives, momentum |
| [Identifying winning sectors: four sector-rotation approaches](identifying-winning-sectors.md) | [ET Money (YouTube)](https://www.youtube.com/watch?v=y4xDxyrGqJc) | 2026-11-22 | sector rotation, business cycle, relative valuation, growth vs GDP |
| [Sector rotation through the economic cycle (the classic US sequence)](sector-rotation-economic-cycle-schwab.md) | [Charles Schwab (YouTube)](https://www.youtube.com/watch?v=C0BK_Mip9oM) | 2026-11-22 | sector rotation, business cycle, US |
| [Sector rotation: 7 Indian bull runs, and why the leaders keep changing](sector-rotation-7-indian-bull-runs.md) | [SOIC (YouTube)](https://www.youtube.com/watch?v=WuipYcJcChU) | 2026-11-22 | sector rotation, Nifty, capital cycle, valuation, cycles |

Decisions on what moves into the board are logged in [board-backlog.md](board-backlog.md).

## How ideas are triaged

Each week a video (or article) becomes one note here. Every actionable idea in it is then sorted into one of four outcomes:

| Outcome | When | What happens |
|---|---|---|
| **Board: build** | All four tests below pass, and the change is small enough to ship in a week | Built into the model's config or inputs, run, and shown before it goes live. Logged in the backlog. |
| **Board: candidate** | Tests 1–3 pass, but it needs a new data source or a back-test first | Logged in the backlog with the model, bucket, indicator, data source and the blocker. |
| **Already covered** | A model already measures it (check `models/*-model-design.md`) | Noted in the backlog with where it lives, so it isn't proposed again. Sometimes the video suggests a better threshold; that goes in as a candidate. |
| **Knowledge only** | Fails any test: stock-picking, industry stories outside the board's indices, history, frameworks, opinions | Stays in the note for later use (research, stock ideas, future models). |

**The four tests for the board**

1. **Measurable and repeatable.** A number with a public source that can be refreshed every month (or every day), not a judgment call.
2. **Fits the board's job.** It changes an entry or exit decision for an INR investor holding for 5 years or less, on something the board already scores (an asset class, index, sector, factor, market or stock).
3. **Adds something new.** Not already measured by an existing indicator, bucket or veto.
4. **Shippable.** The data can be collected inside the monthly run without a new paid source, and the effect on scores is small and explainable.

Scores on the board are never changed silently: anything that moves a live score is shown first.

## Adding a note

1. Add a Markdown file to this folder, named in lowercase with hyphens (for example `capital-cycle-basics.md`). Start it with a `#` title, then a short list of source, date added and tags.
2. Add a row to the table above.
3. Add an entry to `index.json` with the same `slug` (the file name without `.md`), `title`, `file`, `source`, `source_url`, `added` and `tags`. The site's Knowledge tab lists notes from this file, newest first.

Changes in this folder are committed and pushed once a week by `scripts/weekly_knowledge_push.sh` (see the main README).
