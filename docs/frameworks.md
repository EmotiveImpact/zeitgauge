# Frameworks: what to fold in, what to combine, what to leave out

Zeitgauge follows one rule from Tetlock: **stay a fox**. Measured signals drive the score. Big theories sit beside it as lenses, and each one earns trust through forecasts scored by `brier_by()`. A theory can be weak alone and still useful in combination, because it points at something the numbers can check.

Each entry below says what the framework is, what Zeitgauge does with it, and why.

---

## Already in the engine

**Composite index (OECD Composite Leading Indicators)**
- Signals are scored against their normal, flipped so positive means better for households, then blended.
- This is the core of `scoring.py`, and it is explainable to anyone.

**Cycle clock (ONS and Eurostat business cycle clocks)**
- Level and momentum together place a region in one of four phases.
- This produces the headline verdict.

**Lipstick effect and affordable treats**
- In a squeeze, people trade down on big items and keep small luxuries.
- This drives the downturn playbook (`playbook.py`).

**Sahm rule** (`indicators/sahm.py`)
- Real-time recession signal from unemployment.
- A US household signal now. For the UK it counts as supporting evidence only, because it has been tested less there.

**Yield curve**
- When short-term rates sit above long-term rates, recessions have tended to follow.
- A leading US signal. For the UK it will be added as a gilt version once the series codes are verified.

**Turchin's Political Stress Index, light version** (`indicators/psi.py`)
- Pressures on wages, elites and state finances multiply each other.
- Updated annually and feeds the society lens.

**Perez technology surges** (`docs/books/perez.md`)
- Installation, turning point, deployment.
- Applied as the tech wave overlay in the playbook.

**Schwartz scenarios** (`docs/books/schwartz.md`, `config/scenarios/uk.toml`)
- Four worlds with signposts.
- Used to rank ideas by robustness.

**Meadows systems thinking** (`docs/books/meadows.md`)
- Stocks, delays and leverage points.
- Shapes household buffers, the lags in cross-region links, and the "money control" products.

**Tetlock forecasting** (`docs/books/tetlock.md`)
- Precise, dated, scored forecasts.
- Lives in `forecasting.py` and `data/forecasts.json`.

---

## Strauss-Howe: yes for the US, as a story lens

**What it is.** William Strauss and Neil Howe argue that American history runs in cycles of about 80 years. Each cycle has four "turnings" of about 20 years: High, Awakening, Unravelling and Crisis. A generational archetype comes of age in each. They place the US in a Fourth Turning (Crisis) that began around 2008 and ends in the early 2030s.

**Why academics are wary.** Critics make four points:

- The cycle is fitted to American and Anglo history after the fact.
- The dates stretch to fit events.
- Generations are not uniform.
- As stated, it is hard to prove wrong.

These are fair criticisms of it as a scientific theory. Popularity with some political figures has also made some people dismiss it for reasons that have nothing to do with evidence.

**Why it is still useful for the US version.**

- It is the most widely used generational story in American media, marketing and politics. Knowing the story helps you read the culture, whether or not the theory is true.
- Its Crisis-era description (low trust, institutions under strain, a hunger for order and belonging) can be checked against data.
- It overlaps with Turchin's prediction, made in 2010 by a completely different method, that US instability would rise through the 2010s and peak around 2020. When two independent approaches point the same way and the measured data agrees, the case gains weight.

**How Zeitgauge uses it.**

- In `config/regions/us.toml` it is a `[narrative]` block with **weight 0**. It never moves the score.
- It names the data that should confirm it: `trust_gov`, `youth_unemployment` and `house_income`. The dashboard shows the story next to those numbers, so anyone can see whether they agree.
- Forecasts it inspires are tagged `basis = "strauss-howe"`. If its record beats chance over time, it can earn a small weight. If it doesn't, it stays a story.
- For targeting, use real cohort data rather than archetypes: spending by age band (ONS, US Consumer Expenditure Survey) and wealth by age (Federal Reserve Survey of Consumer Finances).

**For the UK: leave it off by default.** Britain's generational history differs. The post-war settlement, Thatcherism and Brexit do not map neatly onto American turnings. The UK society lens already covers trust and strain through measured data.

---

## Fold in next

**Economic Policy Uncertainty index (Baker, Bloom and Davis)**
- What it is: a monthly count of newspaper articles about economic policy uncertainty, published free for both the UK and the US.
- Why: it separates **fear** from **pain**. If uncertainty is high but real pay is fine, people are anxious, not broke, so they want reassurance and flexibility (pausable subscriptions, guarantees). If real pay is falling, the pain is real, so value products win.
- Where: a household signal, leading, for both regions.

**Google Trends, via trendspyg** (`fetchers/trends.py`)
- What it is: weekly search interest, available within days.
- Why: it confirms which playbook items are actually rising, for example whether "press on nails" is climbing now. It also measures the US to UK lag for the culture channel.
- Where: the culture channel in `spillover.py` and a "trend check" on each playbook item.

**Minsky's financial instability hypothesis**
- What it is: in good times, borrowing shifts from safe (income covers repayments) to speculative (income covers interest only) to fragile (only rising prices keep borrowers afloat).
- Why: it measures how hot a Perez frenzy is running, and it warns of household credit stress before defaults appear. Watch buy now pay later (BNPL) use, credit card growth and household debt to income.
- Where: a future `credit` lens, and a modifier on the tech wave overlay.

**Bass and Rogers diffusion of innovations**
- What it is: adoption follows an S-curve, moving through innovators, early adopters, early majority, late majority and laggards.
- Why: Perez tells you the era, and diffusion tells you where one product category sits within it. The best mass-market moment is the jump from early adopters to the early majority.
- Where: an optional field on each idea, `adoption_stage`, in the idea scorer.

**Inglehart and Welzel cultural map (World Values Survey)**
- What it is: countries placed on two axes, traditional versus secular values and survival versus self-expression values, from surveys run every five years or so.
- Why: the same economic phase feels different in different cultures. A downturn in a self-expression culture still sells identity and individuality. In a more survival-minded culture, safety leads.
- Where: a slow-moving region profile that adjusts playbook wording. It is never part of the monthly score.

**GDELT**
- What it is: a free global database of news events and tone, updated every 15 minutes.
- Why: it gives a measured version of the `trust_unrest` judgement signal, and a way to watch news contagion between regions.
- Where: the society lens (protest and unrest event counts) and cross-region links. It is heavy to process, so start with monthly country counts.

**ACLED**
- What it is: curated data on protests, riots and political violence.
- Why: it is cleaner than GDELT for unrest.
- Licence warning: free for non-commercial use only. A commercial product needs a paid licence.

---

## Keep, but only for display or context

**Kondratiev waves.** The long-wave idea survives through Perez, who supplies a mechanism and phase signals. Kondratiev's own price-wave dating is contested, and Perez is the better-supported version.

**Misery index (inflation plus unemployment).** Easy to explain, but our household index already contains both. Show it as a familiar number. Don't score it twice.

**Hofstede's cultural dimensions.** Helpful for wording and local adaptation, but dated and broad-brush. Use the World Values Survey for anything measured.

**Fragile States Index.** An annual cross-country comparison. Useful once Zeitgauge covers several regions, too slow for monthly reading.

**Big Mac index.** It measures currency value, not mood. Useful later for pricing a product in a new region.

**Spengler and Toynbee's rise-and-fall-of-civilisations books.** Good for thinking, impossible to measure. Turchin and the Seshat databank are their data-driven successors, and Zeitgauge uses them in that form.

---

## Leave out

**The hemline index.** A 2010 study by van Baardwijk and Franses found hemlines lag the economy by about three years, which makes them useless as a signal. It remains a fun story for content.

**The men's underwear index.** Anecdotal, and already covered by retail sales.

**The skyscraper index.** Very few data points and long, irregular lags.

**Elliott waves, the Benner cycle and similar fixed-cycle charts.** No mechanism that can be tested, and easy to fit to the past.

---

## Combinations that add understanding

These pairings tell you more together than either does alone.

1. **Perez, Minsky and diffusion.** Era, plus credit froth, plus adoption stage, gives the timing for a product launch.
2. **Lipstick effect and Google Trends.** The theory says small treats rise in a squeeze. Trends shows which ones are rising this month.
3. **Strauss-Howe, Turchin and Pew trust data.** A story, checked against a structural model, checked against a survey. When all three agree, the US society reading carries more weight. When they disagree, trust the data.
4. **Schwartz and Tetlock.** Scenarios set out the possible worlds. Signposts become scored forecasts, and scoring shows which lenses deserve trust.
5. **Meadows and spillover.** Regions are linked stocks with delays. Diebold-Yilmaz connectedness puts fitted numbers on the links (see `docs/cross-region.md`).
6. **World Values Survey and the playbook.** Same phase, different feeling, which is why US and UK playbook wording will diverge.
7. **Policy uncertainty and confidence.** Together they separate fear from pain, which decides whether to sell reassurance or value.
