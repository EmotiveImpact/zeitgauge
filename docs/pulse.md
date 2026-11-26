# The daily pulse and hourly alerts

Zeitgauge now reads a region at three speeds.

1. **Monthly verdict.** Official statistics against long-run normals. Slow and steady on purpose, and checked by a person in a pull request each month.
2. **Daily pulse.** Fast public signals, read every morning. It asks whether this week is better or worse than the last four months.
3. **Hourly alerts.** A watch on news coverage (and X, if switched on) that flags a sudden jump in a topic within the hour.

The pulse and the alerts never change the monthly verdict. They tell you where to look and what might be coming. Like every other part of Zeitgauge, they earn trust through scored forecasts.

---

## What the pulse reads

**United Kingdom** (`config/pulse/uk.toml`)

- **Policy uncertainty in the papers.** Baker, Bloom and Davis daily index. Free under CC BY 4.0, so credit them wherever it is shown.
- **Tone of UK news about money and jobs.** GDELT average tone.
- **Share of UK news about the squeeze.** GDELT coverage share for cost of living, food banks, redundancies and energy bills.
- **Share of UK news about strikes and protest.** GDELT coverage share.
- **People reading up on recession and layoffs.** Wikipedia pageviews. English Wikipedia is read worldwide, so this is a signal for the English-speaking world.
- **10-year gilt yield, daily.** Bank of England database. The series code IUDMNPY still needs checking after the first live run.
- **Searches for help with money.** Google Trends. Off by default because it needs an extra package; see the config file.

**United States** (`config/pulse/us.toml`)

- Policy uncertainty (FRED USEPUINDXD)
- The VIX fear gauge (FRED VIXCLS)
- The daily yield curve (FRED T10Y2Y)
- GDELT news tone and squeeze coverage for the US
- Wikipedia pageviews

**Social media** joins as one extra signal per platform once you switch it on. See `docs/social.md`.

---

## How the score works

For each signal:

1. Average the last 7 days. Weekly averages smooth out weekends and one-off days.
2. Look at every 7-day average in the 120 days before that. Their median is "usual". Their spread, measured with the median absolute deviation, is the typical swing. Medians ignore the odd wild day, which daily data is full of.
3. Score = direction × (this week − usual) ÷ swing, capped at ±2.5. Direction makes positive always mean better for households.

Then the scores are combined into one number that asks how unlikely this week's mix would be if nothing had really changed:

- combined = sum of (weight × score) ÷ (square root of the sum of weights squared × 1.2)
- index = 50 + 10 × combined, kept between 0 and 100

**Reading the index**

- **50** means the same as the last four months.
- **65 or more** reads as improving. Ordinary noise gets that high on about 1 day in 20.
- **35 or less** reads as worsening.
- In between reads as steady.

One loud signal on its own rarely moves the pulse out of steady. Several signals pointing the same way do. The 1.2 in the formula was set by simulation, and a test (`tests/test_pulse.py`) checks that pure noise reads as steady about 9 days in 10.

**The early read** compares the pulse's mood with the monthly phase. For example, an improving pulse during a downturn reads: "An early hint that the squeeze is easing. The official figures have yet to confirm it." The pulse also counts how many days in a row it has held the same mood.

**Safeguards**

- A signal whose latest data is more than 10 days old is skipped as stale.
- A signal needs at least 37 days of data before it counts.
- If less than half the weight comes through, the pulse says so and gives no index.
- A single day more than 3 swings from usual is listed as unusual, so you can look into it.

---

## Hourly alerts

Each watch in the config is a news query. Every hour, Zeitgauge fetches the past week of hourly coverage and compares the last two hours with the rest of the week.

An alert fires only when both are true:

- coverage is at least **2 times** its usual level, and
- it is at least **3 swings** above usual.

Needing both stops a quiet topic doubling from 1 to 2 articles from firing, and stops a busy topic wobbling in its normal range. After an alert, that watch stays quiet for 12 hours.

**UK watches:** job cuts, price shocks, strikes and unrest, rates and banks, and tax and budget news.
**US watches:** job cuts, tariffs and trade, and market or banking stress.

Edit the queries, thresholds and cooldown in `config/pulse/<region>.toml`.

**Where alerts go**

- **GitHub issue.** On by default, so you get a notification in the GitHub app. To stop it, set the repository variable `ALERT_ISSUES` to `false`.
- **Phone push through ntfy.** Free. Install the ntfy app, subscribe to a long random topic name, and save that name as the secret `NTFY_TOPIC`. Anyone who knows the topic name can read the messages, so make it hard to guess.
- **Any webhook.** Slack, Discord and similar. Save the URL as the secret `ALERT_WEBHOOK_URL`.

Every alert is also saved to `data/alerts/<region>/log.jsonl` and `web/alerts.json`.

---

## Running it

```bash
zeitgauge pulse --region uk --dry-run   # print today's pulse, write nothing
zeitgauge pulse --region uk --web       # save it and update web/pulse.json
zeitgauge alerts --region uk --dry-run  # check the watches now
zeitgauge social                        # which social platforms are on
```

**Schedules** (in `.github/workflows/`)

- `daily-pulse.yml` runs at 06:23 UTC. That is 06:23 UK time in winter and 07:23 in summer. It commits to main directly.
- `hourly-alerts.yml` runs at 17 minutes past each hour. It commits only when something changed.
- Both share a lock, so they never push at the same moment.

**Actions minutes:** the hourly job uses about one minute a run, roughly 750 a month. With the daily, monthly and test runs, the total is about 850 of the 2,000 free minutes a month on a private repository. A public repository has no limit.

If `main` is protected, allow `github-actions[bot]` to push, or the commit steps will fail.

---

## Files

- `data/pulse/<region>/latest.json`: today's full breakdown.
- `data/pulse/<region>/history.csv`: one row a day (index, lenses, mood).
- `web/pulse.json` and `web/alerts.json`: ready for the app to read.

---

## Honest limits

- The live sources have not yet been called from the build machine, because its network blocks them. The parsers are tested against the documented formats and saved samples. Check the first scheduled run by hand.
- GDELT and Wikipedia measure what is written and read. That is attention, which often runs ahead of spending, but it can also be driven by one big story.
- Fifty in the pulse means "the same as the last four months". It is a different 50 from the monthly verdict, where 50 means the long-run normal.
- Weights are first guesses. Once a few months of pulse history exist, check which signals led the monthly verdict and reweight them.
