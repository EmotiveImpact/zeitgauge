# The weekly brief: what people need right now

Every Monday Zeitgauge turns its three speeds (the monthly verdict, the daily pulse and the hourly alerts) into one short read: which needs are strongest this week, the evidence behind each, and what to build for them.

It arrives as a GitHub issue, so it lands in the GitHub app on your phone. It is also saved to `data/brief/<region>/` and `web/brief.json` for the app.

---

## What a brief contains

1. **The read.** Where the region stands and the three strongest needs, in a paragraph.
2. **What moved this week.** Daily signals that jumped since last week, unusual single days and news alerts.
3. **Needs right now.** For each of the top three:
   - **Why now:** the signals backing it, each with its latest value against normal and which way it is heading.
   - **Pulling the other way:** any signals that argue against it.
   - **What to build:** two ideas, each with a format, a rough price and the cheapest way to test demand.
   - **If the cycle turns:** whether the need still works in the phase that usually comes next.
   - **Would weaken if:** what to watch that would make the need fade.
   - **Scorecard:** the dated call that will check it.
4. **Also showing.** Other needs with real support that did not make the top three.
5. **Watch next.** The scenario the signposts point to most, and which needs survive the next phase.
6. **Scorecard.** Calls settled this week and the running record.

---

## How a need is scored

The needs live in `config/needs.toml`. Each one lists its **drivers**: the signals that make it more pressing. For example, money control grows when the personal finance outlook, Direct Debit failures, real pay and inflation are bad for households.

For each driver the region has:

- **aligned score** = the signal's score, flipped when the need grows as that signal gets worse. Positive means the signal backs the need.
- Monthly signals use their score against the long-run normal. Daily pulse signals use their score against the last four months, at **half weight**, because daily data is noisier.

Then for the need as a whole:

- **evidence** = the weighted average of its aligned scores.
- **rank** = evidence, plus **0.5** if the need suits the current phase or social mood in the playbook, plus **0.25** if one of its alert watches fired this week.
- A need is mentioned only if its evidence is above **0.25** and at least two of its drivers have data.

**Confidence**

- **Strong:** three or more signals firmly back it (aligned score of 0.5 or more) and evidence is at least 0.75.
- **Moderate:** two or more firmly back it and evidence is at least 0.4.
- **Early:** support is thinner or rests on one loud signal.

**Trend** compares each driver with last month (or, for daily signals, last week). The need reads as still growing, holding steady or easing.

**Ideas.** Two per need, in catalogue order, except that an idea tagged with the current technology wave goes first. In the build and hype phase of a technology, tools and templates that help ordinary people use it tend to sell (Perez).

---

## How the brief keeps score of itself

Every need in the top three becomes a dated call in `data/forecasts.json`, with the basis `need:<id>`:

> Google searches in the UK for 'air fryer recipes' and 'draught excluder' are higher in the 4 weeks to 1 March 2027 than in the same 4 weeks a year earlier. Chance: 65%.

- The searches for each need are set under `check` in `config/needs.toml`.
- The chance is 65% for a Strong need, 60% for Moderate and 55% for Early.
- A need that already has an open call does not get another, so the log grows by a few calls a month rather than three a week.
- Calls are checked 13 weeks later with Google Trends. Comparing with the same weeks a year earlier takes out the seasons, so heated throws are not judged against summer.
- One download covers both windows, because Trends numbers are only comparable within a single request.
- If Trends is down or rate-limited, the call stays open and is tried again next week.

`zeitgauge brier` shows the record for each need separately. Once a need has been called a few times, its record tells you how far to trust it. A need that keeps missing should have its drivers or searches rethought.

---

## Running it

```bash
zeitgauge brief --region uk --dry-run            # print this week's brief, write nothing
zeitgauge brief --region uk --web --log-calls    # save it, update web/brief.json, log the calls
zeitgauge brief --region uk --check              # also settle calls that have come due
zeitgauge brief --region uk --date 2026-11-30    # write the brief as if it were that day
```

Settling calls needs the Trends package: `pip install -e ".[trends]"`.

**Schedule:** `.github/workflows/weekly-brief.yml` runs on Mondays at 07:07 UTC, after the daily pulse. It opens one issue per region with a brief (set the repository variable `BRIEF_ISSUES` to `false` to stop that), sends a short phone push if `NTFY_TOPIC` is set, and commits to main. A region with no monthly readings yet (the US today) is skipped.

---

## Editing the catalogue

Each need in `config/needs.toml` has:

- `id`, `name` and `feeling` (one line on what people want).
- `phases` and `overlay`: where it fits the playbook. Overlay-only needs (safety, comfort) follow the social mood more than the economy.
- `drivers`: `signal` for a monthly signal or `pulse` for a daily one, `when` (`worse` or `better`) and `weight`. `social_*` matches any social platform that is switched on. Ids a region lacks are skipped, so one catalogue serves the UK and the US.
- `alerts`: alert watch ids that make it more pressing when they fire.
- `check`: two or three Google searches that should rise if the need is real.
- `ideas`: name, format, price band and the cheapest test. Add `tech = "install"` for an idea that rides the current technology wave.

A test checks that every signal, pulse and alert id in the catalogue exists, so a typo fails the build.

---

## Honest limits

- The brief is only as fresh as its inputs. Most weeks the monthly figures have not changed, so the top needs move slowly and the "what moved" section carries the news.
- The needs and their drivers are judgement, informed by the books in `docs/books/` and past downturns. The scorecard is how that judgement gets tested.
- Google searches are a proxy for demand. A need can be real while searches stay flat, for example when people buy from habit.
- Ideas are starting points. The test listed with each one is the real answer to whether it sells.
