# Peter Schwartz: The Art of the Long View (1991)

**Subtitle:** Planning for the Future in an Uncertain World.

## The book in one paragraph

You cannot predict the future, but you can prepare for several of them. Schwartz learned scenario planning at Shell, where Pierre Wack's team had helped the company prepare for the 1973 oil shock. He later co-founded the Global Business Network. The book teaches how to write a small set of plausible, very different stories about the future, use them to rehearse decisions, and watch for early signs of which story is unfolding. The point is better decisions today, not a correct forecast.

## The key ideas

### 1. Scenarios are tools for decisions

A scenario is a story about how the world might turn out, built around a decision you have to make. Good scenarios change what people do. Interesting scenarios that change nothing have failed.

### 2. Challenge the "official future"

Every organisation carries an unspoken assumption about how things will go. Scenario work drags that assumption into the open and tests it against alternatives.

### 3. Predetermined elements and critical uncertainties

- **Predetermined elements** are things already in motion that will play out whatever happens. Examples: the age structure of the population, mortgages already fixed for two to five years.
- **Critical uncertainties** are important forces whose direction is genuinely unknown. These become the axes of the scenarios.

### 4. The eight steps

1. Name the focal issue or decision.
2. List the key forces in the immediate environment (customers, suppliers, competitors).
3. List the driving forces behind them: social, technological, economic, environmental and political.
4. Rank them by importance and by uncertainty.
5. Pick the scenario logics: usually two highly important, highly uncertain forces as a two-by-two.
6. Flesh out each scenario as a story with a memorable name.
7. Work out the implications for the decision.
8. Choose leading indicators and signposts that will show which scenario is unfolding.

### 5. Common plots

Schwartz lists story shapes that keep recurring:

- Winners and Losers
- Challenge and Response
- Evolution
- Revolution
- Cycles
- Infinite Possibility
- The Lone Ranger
- My Generation

Recognising a plot helps you write the scenario and spot it in the news.

### 6. Information hunting

Look in unusual places:

- remarkable people with odd vantage points
- the fringes of society, where new behaviour starts
- science and technology journals
- music, film and youth culture
- publications outside your own field

Change shows up at the edges first.

### 7. Three or four scenarios, no "most likely"

Avoid a central case flanked by high and low versions, because people simply pick the middle. Avoid attaching probabilities to whole scenarios for the same reason. Give each scenario equal dignity.

### 8. Rehearse the future

Walk through each scenario as if it were real. Ask what you would do and what you would regret. Decisions that work across all of them are robust. Decisions that only work in one are bets, and should be labelled as such.

## What Zeitgauge takes from it

- **Rule S1: every region gets a two-by-two.** The UK scenarios use two axes:
  - *Inflation path:* sticky or easing (`cpi`, `boe_infl_fcst`, `bank_rate`)
  - *Social fabric:* holding or fraying (society lens, `trust_unrest`)

  That gives four worlds, each with a working name:
  - **Thaw:** easing inflation, fabric holding
  - **Grind:** sticky inflation, fabric holding
  - **Frayed:** sticky inflation, fabric fraying
  - **Uneasy calm:** easing inflation, fabric fraying
  These live in `config/scenarios/uk.toml`.
- **Rule S2: signposts are signals.** Each scenario lists conditions on signals Zeitgauge already scores, such as "inflation falling" (CPI momentum above zero). `scenarios.py` counts how many are lit each month. In November 2026 the count was Frayed 4 of 4, Grind 3 of 4, Uneasy calm 2 of 4 and Thaw 1 of 4. The count shows where to pay attention. It is deliberately kept separate from odds.
- **Rule S3: rank ideas by robustness.** `ideas.robust_rank()` scores every idea in every scenario. It blends expected payoff with the worst case through the `caution` setting (0.4 by default). The idea scorer's "still works in the next phase" rating is the quick version of the same principle.
- **Rule S4: predetermined elements go in the readings note.** For example, the mortgage refix wave, or a tax change already announced. They shift the timing of effects without changing the scenario.
- **Rule S5: look at the edges.** The culture channel (Google Trends via `fetchers/trends.py`, and later GDELT) is our version of information hunting at the fringe.

## A tension we resolve on purpose

Schwartz warns against putting probabilities on scenarios. Tetlock insists on probabilities so that calls can be scored. Zeitgauge keeps both:

- The four scenarios are shown side by side without odds, as Schwartz advises.
- The signposts underneath them become precise, dated, probabilistic forecasts in `data/forecasts.json`, which can be scored.
- `robust_rank` uses rough weights only to rank ideas, and its worst-case term keeps a low-odds scenario from being ignored.

## Limits

- Scenarios are only as good as the axes chosen. Revisit them twice a year, or after a shock.
- Group scenario work is where much of the value lies. A solo version is weaker, so share the scenarios and argue about them.
