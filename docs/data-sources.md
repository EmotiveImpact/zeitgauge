# Data sources

Everything here is free to read unless marked otherwise. "Auto" means a fetcher in `src/zeitgauge/fetchers/` already handles it. "Manual" means someone types the latest figure into the month's readings file.

Licences matter if Zeitgauge becomes a paid product. Licence warnings are marked **(licence)**.

---

## United Kingdom

**Household lens**

- **Consumer confidence (GfK, now part of NIQ).** Monthly headline and personal finance outlook, published in the last week of each month as a press release. Manual.
- **Bank of England inflation projection.** From the quarterly Monetary Policy Report. Manual.
- **CPI inflation.** ONS series D7G7. Auto (`ons`).
- **Real regular pay growth.** ONS labour market release. Manual for now, because the series ID varies between releases.
- **Unemployment rate, 16 and over.** ONS series MGSX. Auto (`ons`).
- **Bank Rate.** Bank of England database (IADB) series IUMABEDR. Auto (`boe`).
- **Direct debit failure rate.** Pay.UK data, shown in the ONS real-time indicators. Manual. Check it is still published each month.
- **Retail sales volume.** ONS retail sales release, year-on-year change. Manual.
- **Household saving ratio.** ONS series NRJS, quarterly. Auto (`ons`).

**Society lens**

- **House prices to earnings.** ONS annual affordability release. Manual.
- **Youth unemployment, 16 to 24.** ONS series MGWY. Auto (`ons`).
- **10-year gilt yield.** Bank of England database. Auto (`boe`). The series code in `uk.toml` still needs checking against the IADB site.
- **Trust and unrest.** A judgement score from -2 to +2. Draw on:
  - the ONS Opinions and Lifestyle Survey
  - the Ipsos Veracity Index
  - the Edelman Trust Barometer
  - news of protests

**Next to add**

- Economic Policy Uncertainty index, UK (policyuncertainty.com).
- Barclays or BRC consumer spending (press releases).
- Insolvency Service individual insolvencies (monthly).
- Google Trends, GB.

---

## United States

FRED series need no API key on the public CSV endpoint. Register a free key for heavy use.

**Household lens**

- **University of Michigan consumer sentiment.** FRED UMCSENT. Auto (`fred`).
- **Yield curve, 10-year minus 2-year.** FRED T10Y2Y. Auto (`fred`).
- **Sahm rule.** Computed from FRED UNRATE by `indicators/sahm.py`. Cross-check against FRED SAHMREALTIME. Auto (`derived`).
- **CPI inflation.** FRED CPIAUCSL, turned into a year-on-year rate. Auto (`fred`, `yoy`).
- **Unemployment rate.** FRED UNRATE. Auto (`fred`).
- **Personal saving rate.** FRED PSAVERT. Auto (`fred`).
- **Credit card delinquency rate.** FRED DRCCLACBS. Auto (`fred`).

**Society lens**

- **House prices to income.** Harvard Joint Center for Housing Studies, annual. Manual.
- **Youth unemployment, 16 to 24.** FRED LNS14024887. Auto (`fred`).
- **10-year Treasury yield.** FRED DGS10. Auto (`fred`).
- **Trust in federal government.** Pew Research Center. Manual.

**Next to add**

- New York Fed Survey of Consumer Expectations (free, monthly).
- New York Fed Household Debt and Credit Report (quarterly).
- Gallup confidence in institutions (annual).
- Economic Policy Uncertainty index, US.
- Conference Board consumer confidence **(licence: paid)**.

---

## Global and cross-region

- **OECD Data Explorer.** Composite leading indicators and consumer confidence for member countries, on one comparable scale. The best first source when adding a new region.
- **IMF World Economic Outlook and World Bank World Development Indicators.** Slow-moving context: growth, debt, demographics.
- **Our World in Data.** Clean long-run series under CC BY.
- **GDELT.** Free global news events and tone. Useful for unrest and contagion between regions.
- **ACLED.** Protest and political violence events **(licence: free for non-commercial use, paid for commercial use)**.
- **Fragile States Index.** Annual country scores.
- **World Values Survey.** Cultural values by country, in waves about five years apart.
- **Seshat Global History Databank.** Historical data on societies, used by Turchin's group **(licence: data is CC BY-NC-SA, non-commercial only)**.
- **Google Trends.** Via trendspyg (MIT). Relative search interest, so compare shapes and timing, not levels.

---

## A note on the build container

The machine this repository was built on could not reach the ONS, FRED or Bank of England websites, because its network proxy blocks them. The parsers are tested against saved sample files in `tests/fixtures/`. The download step will run for the first time on your own machine or in GitHub Actions. Run `zeitgauge fetch --region uk --dry-run` first and check the numbers against the source pages.
