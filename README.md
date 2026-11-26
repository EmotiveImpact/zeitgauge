# Zeitgauge

**Read the mood of a place, then build what people will want next.**

Zeitgauge turns public data into a plain verdict on where a region's households and society stand. It then suggests product directions that suit the moment and the phase that usually follows. It starts with the UK. The US is set up and ready to score, and links between regions show how a shift in one place is likely to reach another.

**UK, November 2026:** Downturn: the squeeze, society under strain. Household index 36, society index 33 (50 = normal).

## Quick start

```bash
pip install -e ".[dev]"
zeitgauge score --region uk          # verdict, playbook, scenarios
zeitgauge score --region uk --web    # also writes web/data.json
zeitgauge fetch --region uk --dry-run  # pull fresh ONS and Bank of England data
zeitgauge brier                      # how good have our forecasts been?
zeitgauge pulse --region uk --dry-run  # today's pulse from fast public signals
zeitgauge alerts --region uk --dry-run # any sudden spikes in the news right now?
zeitgauge social                     # which social platforms are on, and what they cost
pytest -q
```

Open `web/index.html` on a phone or in a browser for the dashboard.

## Three speeds

- **Monthly verdict:** official statistics, checked by a person in a pull request.
- **Daily pulse:** news tone, policy uncertainty, what people read up on and market gauges, every morning. It says whether this week is better or worse than the last four months, and what that hints about the next monthly verdict.
- **Hourly alerts:** a sudden jump in coverage of job cuts, prices, unrest, rates or the budget sends a GitHub issue, a phone push (ntfy) or a webhook.

Social media (Bluesky, YouTube, X, Reddit) can join the pulse one platform at a time. Everything is off until you switch it on. See `docs/pulse.md` and `docs/social.md`.

## What's inside

**Engine** (`src/zeitgauge/`)
- `scoring.py`: signals scored against their normal, blended into two lenses and placed on a four-phase cycle clock.
- `playbook.py`: phase, social stability and tech wave mapped to the feelings to design for.
- `ideas.py`: a weighted idea score, plus robust ranking across scenarios.
- `scenarios.py`: Schwartz-style worlds with signposts tied to real signals.
- `forecasting.py`: a forecast log with Brier scores, broken down by the signal or framework behind each call.
- `spillover.py`: links between regions through money, trade and culture, with delays.
- `indicators/`: Sahm rule and a light Political Stress Index (after Turchin).
- `pulse.py`: the daily pulse, scored against the last four months with a noise-calibrated combined score.
- `alerts.py`: hourly spike detection with cooldowns, plus ntfy, webhook and GitHub issue delivery.
- `social/`: official-API adapters for Bluesky, YouTube, X and Reddit, a switch per platform and a monthly budget for paid ones.
- `fetchers/`: ONS, FRED, Bank of England, GDELT news, Wikipedia pageviews, daily policy uncertainty and, optionally, Google Trends.

**Settings and data**
- `config/regions/`: one TOML file per region (signals, normals, swings, weights, sources).
- `config/scenarios/`: one TOML file of scenarios per region.
- `config/pulse/`: daily pulse signals and hourly alert watches per region.
- `config/social.toml`: the social media switches, costs and search terms.
- `data/readings/`: one JSON file per region per month.
- `data/forecasts.json`: the forecast log.
- `data/pulse/`, `data/alerts/`, `data/social/`: written by the daily and hourly runs.

**Docs** (`docs/`)
- `vision.md`: what this is for, and the roadmap.
- `algorithm.md`: exactly how the score works.
- `frameworks.md`: what to fold in, combine or leave out, including Strauss-Howe for the US.
- `books/`: the four core books (Perez, Schwartz, Meadows, Tetlock), with their key ideas and the rules Zeitgauge takes from each.
- `data-sources.md`: UK, US and global sources, with licence warnings.
- `third-party.md`: open-source projects we learn from, and their licences.
- `cross-region.md`: how regions affect each other, now and in version 2.
- `pulse.md`: the daily pulse and hourly alerts, how they score and where alerts go.
- `social.md`: what each social platform costs and how to switch it on.

## Monthly routine

1. On the 28th, GitHub Actions fetches the official series and opens a draft pull request (`.github/workflows/monthly-fetch.yml`).
2. Type in the manual signals: GfK confidence, the Bank of England projection, trust and unrest.
3. Run `zeitgauge score --region uk --web` and read the verdict.
4. Write three to five forecasts in `data/forecasts.json`, and resolve any that are due.
5. Merge.

## Daily and hourly

These run on their own once merged (`.github/workflows/daily-pulse.yml` and `hourly-alerts.yml`):

- Every morning at 06:23 UTC the pulse is saved to `data/pulse/` and `web/pulse.json`.
- Every hour at 17 minutes past, the alert watches are checked. New alerts open a GitHub issue by default.
- Optional: add the secret `NTFY_TOPIC` for phone pushes, or `ALERT_WEBHOOK_URL` for Slack or Discord.

## Status and honesty notes

- The UK scores are from real data published up to 26 November 2026.
- The download code is tested against saved sample files. It has not yet run against the live sites, because the build machine's network blocked them. Check the first live fetch by hand.
- The US configuration is complete, but it has no readings file yet.
- The daily pulse and alert sources (GDELT, Wikipedia, policy uncertainty) are tested against their documented formats, not yet live. Check the first scheduled runs.
- Normals, swings and link strengths are first estimates. Version 2 fits them from history.

## Licence

MIT. Third-party projects are not included. `scripts/get_third_party.sh` clones them separately (see `docs/third-party.md`).
