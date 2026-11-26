# How Zeitgauge scores a region

The method is simple on purpose, so anyone can check it by hand. Version 2 will fit the weights from data (see the end of this page).

## 1. Score each signal against its normal

For each signal:

> score = direction × (latest − normal) ÷ swing

- **normal** is the long-run typical value for that region, for example 2.5% for UK inflation.
- **swing** is how far the signal usually moves in a normal year: its typical spread.
- **direction** is +1 if higher is better for households (confidence, pay) and −1 if higher is worse (inflation, unemployment).

So a score of −1 means "one typical swing worse than normal". Scores are capped at ±2.5 so one extreme reading can't swamp the rest.

## 2. Momentum

> momentum = direction × (latest − previous) ÷ swing

Positive momentum means things are getting better for households, whatever the signal.

## 3. Blend into two lenses

- **Household lens:** money in people's pockets and how they feel about it.
- **Society lens:** strain on the social fabric (housing, youth jobs, state finances, trust).

Each lens is a weighted average of its signals. Leading signals, which tend to move first, weigh 1.5. The rest weigh 1.0. Signals with no reading this month are skipped.

The index shown on the dashboard is:

> index = 50 + 20 × lens level

So 50 is normal, 30 is one swing worse and 70 is one swing better.

## 4. Place the region on the cycle clock

| | Momentum up | Momentum down |
|---|---|---|
| **Level above normal** | Expansion | Slowdown |
| **Level below normal** | Recovery | Downturn |

If momentum is very small (below 0.03), the verdict adds "levelling off".

## 5. Add the society overlay

If the society lens level is below −0.25, the verdict adds "society under strain". This switches the playbook overlay from "stable" to "strained".

## 6. Add the tech wave and the scenarios

- The readings file's `tech_wave` field (`install`, `turn` or `deploy`) adds Perez-based advice.
- If the region has a scenarios file, Zeitgauge counts which signposts are lit (see `docs/books/schwartz.md`).
- If the region has a narrative lens (Strauss-Howe for the US), it is shown with weight 0.

## 7. Turn it into product ideas

The phase and overlay select "feelings to design for" from `playbook.py`. Ideas are then scored in two ways:

- **Weighted score (0 to 100).** Fit with today's phase 30%, still works in the next phase 25%, audience size 20%, your skills 15%, low cost to test 10%.
- **Robust rank across scenarios.** A blend of the expected payoff and the worst case (`ideas.robust_rank`).

## 8. Keep score

Each month, write three to five forecasts in `data/forecasts.json`. When they resolve, record the outcome. `zeitgauge brier` shows accuracy overall and for each signal or framework.

## UK, November 2026

- **Household index 36**, **society index 33**.
- Verdict: **"Downturn: the squeeze, society under strain"**.
- Scenario signposts lit: Frayed 4 of 4, Grind 3 of 4, Uneasy calm 2 of 4, Thaw 1 of 4.

## Version 2 (once 10+ years of history are stored)

- **Weights.** A dynamic factor model in place of hand-set weights. See macro-regime-nowcaster in `docs/third-party.md`.
- **Phase cut-offs.** A Markov regime-switching model in place of the fixed four-quadrant split, so the model learns its own phases and gives a probability for each.
- **Normals and swings.** Fitted from rolling ten-year windows.
- **Cross-region links.** Fitted with Diebold-Yilmaz connectedness (see `docs/cross-region.md`).
