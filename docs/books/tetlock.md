# Philip Tetlock and Dan Gardner: Superforecasting (2015)

**Subtitle:** The Art and Science of Prediction.

## The book in one paragraph

Tetlock's earlier research found that the average expert forecast was barely better than chance. The pundits most confident in one big idea did worst. Then, in a forecasting tournament run by the US intelligence research agency IARPA from 2011 to 2015, his Good Judgment Project found a small group of ordinary people who forecast world events far better than everyone else. The book explains what they do differently. Their methods are habits anyone can learn: break questions down, start from base rates, think in fine-grained probabilities, update often in small steps, work in teams and keep score.

## The key ideas

### 1. Keep score or you learn nothing

Vague forecasts ("there is a risk of recession") cannot be checked. A useful forecast has three parts:

- a precise event
- a deadline
- a probability

The Brier score then measures accuracy. 0 is perfect. Always saying 50% scores 0.25. Lower is better.

### 2. Calibration and resolution

- **Calibration:** things you call 70% likely should happen about 70% of the time.
- **Resolution:** being decisive, moving away from 50% when the evidence allows.

Good forecasters manage both.

### 3. Foxes beat hedgehogs

Hedgehogs know one big thing and fit the world to it. Foxes know many small things and blend them. Foxes forecast better. Big-theory frameworks are useful inputs, but they should not be allowed to dominate.

### 4. Outside view first, then inside view

Start with the base rate: how often has this kind of thing happened before? Only then adjust for the details of the case. Most people do it the other way round and get carried away by the story.

### 5. Fermi-ise

Break a hard question into smaller parts you can estimate. Example: "Will UK confidence recover by summer?" becomes three questions. How fast does real pay recover? When do rates fall? How do people react?

### 6. Update often, in small steps

Superforecasters revise frequently but modestly. They avoid two errors:

- ignoring new information
- lurching at every headline

### 7. Granularity matters

The best forecasters distinguish 60% from 65%, and that precision measurably improves their scores.

### 8. Look for clashing causal forces

Most outcomes are a tug of war. List the forces pushing each way before settling on a number.

### 9. Teams and aggregation

Small teams that share evidence and challenge each other beat individuals. Averaging many forecasts beats most individuals. Nudging the average slightly towards the extremes ("extremising") helps further.

### 10. Perpetual beta

The best forecasters treat their beliefs as hypotheses to test, review their mistakes honestly and keep improving. Tetlock found this trait mattered more than raw intelligence.

### 11. Skill fades with distance

Accuracy falls as the forecast horizon lengthens. Questions within a year or so can be forecast with real skill. Beyond a few years, even experts approach chance. Long-range thinking still has value, but it belongs to scenarios (see `schwartz.md`).

### 12. The ten commandments (plus one)

1. Triage: focus on questions where effort pays off.
2. Break hard problems into tractable parts.
3. Balance inside and outside views.
4. Balance under- and over-reaction to evidence.
5. Look for the clashing causal forces.
6. Distinguish as many degrees of doubt as the problem allows, and no more.
7. Balance under- and over-confidence, prudence and decisiveness.
8. Look for the errors behind your mistakes, and beware hindsight bias.
9. Bring out the best in others, and let them bring out the best in you.
10. Master the error-balancing bicycle: practise with feedback.
11. Don't treat the commandments as commandments.

## What Zeitgauge takes from it

- **Rule T1: every monthly verdict comes with forecasts.** Write three to five precise, dated, probabilistic questions in `data/forecasts.json`. The first four were written on 26 November 2026.
- **Rule T2: base rate first.** Before writing a probability, use `forecasting.base_rate()` to ask how often this has happened in the stored history. Write the base rate in the question's notes.
- **Rule T3: frameworks compete on their record.** Each forecast names its `basis`: the signal or framework behind it. `brier_by()` scores each basis separately and `zeitgauge brier` prints the table. Strauss-Howe, Turchin, Perez and plain signals all earn trust the same way. A framework with a poor record loses influence, and one with a strong record can earn a weight in the score.
- **Rule T4: stay a fox.** No single framework drives the verdict. The score is a blend of many signals. Big theories sit beside it as lenses, and they are tested through forecasts.
- **Rule T5: horizon discipline.** Forecasts run 6 to 18 months ahead. Anything longer goes into the scenarios.
- **Rule T6: review when things resolve.** When a forecast resolves, record the outcome and one line on why it went right or wrong. Review the scores each quarter.

## Limits

- Tournament questions were short-horizon and clearly resolvable. Product decisions are often neither, which is why Zeitgauge pairs forecasting with scenarios.
- A good Brier score needs many resolved questions. Expect about a year before the numbers mean much.
