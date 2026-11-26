# Reading several regions, and how one affects another

Zeitgauge scores each region on the same scale: 50 is that region's own normal. That makes regions comparable even when their raw numbers differ. For example, US sentiment has a normal of 85 and UK confidence a normal of -11.

## Version 1: hand-set links (now)

`src/zeitgauge/spillover.py` describes each link between two regions with three channels, each rated from 0 to 1:

- **Money.** Interest rates, bond yields and stock markets move together. When US Treasury yields jump, gilt yields usually follow within days.
- **Trade.** Exports, imports and prices. The US is the UK's largest single-country export market.
- **Culture.** Trends, platforms and media. A shared language and shared apps mean US consumer trends often reach the UK weeks or months later.

Each link also carries `lag_months`, the expected delay before the effect shows up. This follows Meadows: regions are stocks of confidence connected by flows with delays.

**First estimates**

- **US to UK:** money 0.7, trade 0.3, culture 0.7. Lag about three months.
- **UK to US:** money 0.2, trade 0.1, culture 0.3. Lag about six months.

The links are lopsided because the US is a much larger economy and the main source of global finance and online culture.

**What the function returns.** Given each region's household level and momentum, it returns three things for each region:

- the pressure arriving from the others
- where that pressure comes from
- when it is likely to arrive

The dashboard can then say something like: "The US is weakening. Expect some of that to reach UK confidence in about three months."

## Version 2: fitted links (once history is stored)

1. **Backfill history.** Pull 10 to 20 years of monthly readings for each region from ONS, FRED and the OECD. Score every month to build a history of the household index.
2. **Fit the connectedness.** Use the Diebold-Yilmaz connectedness index. It fits a vector autoregression across the regions' index histories, then asks how much of each region's surprise movements came from shocks in the others. The result is a table of "from" and "to" percentages, which replaces the hand-set channel weights.
3. **Use a rolling window.** Fit over rolling five-year windows so links can strengthen in a crisis, which is when they matter most.
4. **Measure the culture lag directly.** `fetchers/trends.lead_lag_months()` cross-correlates US and UK Google Trends series for product terms. This gives a measured delay for the culture channel, product by product.
5. **Add news contagion.** GDELT tone and event counts by country show how quickly unrest or panic in one place is covered in another.

## Adding a region

1. Create `config/regions/<id>.toml` with the same structure as `uk.toml`. The OECD Data Explorer gives comparable confidence and leading indicators for most large economies.
2. Add a readings file under `data/readings/<id>/`.
3. Add links to and from the new region in `spillover.LINKS`.
4. Optionally add a scenarios file and a cultural profile from the World Values Survey.

Good next regions are the euro area (a large UK trading partner with strong money links) and China (trade and supply chain links, though comparable monthly mood data is harder to get).
