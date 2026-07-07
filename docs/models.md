# Prediction Models

All goal-derived markets come from a single scoreline probability distribution so they stay mutually consistent. Corner, card, and per-half markets are separate count models. Every model implements the `Predictor`/fit-predict shape and consumes shrinkage-adjusted team rates from `soccer_prediction.features`.

## Team rates

`compute_rates(history)` builds per-team attack/defence goal rates, corner-for/against rates, card rates, and half-time rates, with exponential **recency weighting** and **shrinkage** of small samples toward a global prior — important for sparse international data.

## Goals: independent Poisson (`poisson`)

Estimates home/away goal expectations from team rates and forms the outer-product scoreline grid up to `model.max_goals`. Simple and fast; tends to under-predict draws.

## Goals: Dixon-Coles (`dixon_coles`, default)

Extends the Poisson grid with a low-score dependence correction that lifts draw mass on 0-0/1-1/1-0/0-1 outcomes, then renormalizes. This is the standard accuracy upgrade for football scorelines (Dixon & Coles, 1997). Falls back to Poisson if fitting is degenerate. When the optional `[accel]` extra with `penaltyblog` is installed, a full maximum-likelihood Dixon-Coles fit can be substituted behind the same interface.

## Derived goal markets

From the grid: `home_draw_away()` (1X2), `over_under(line)` (tail sums), `both_teams_to_score()` (`1 − P(home=0) − P(away=0) + P(0,0)`), and the correct-score cells.

## Corners: total and minimum

Per-team corner expectations from corner-for × opponent corner-against rates. Over/under lines are Poisson upper-tail sums `P(total ≥ k)`. The **minimum** is the 10th-percentile floor of the per-team distribution — the smallest count whose cumulative probability reaches ~10%. "Minimum corners" is inference from the fitted count distribution, not a standard betting market; corners are overdispersed, so a Negative-Binomial fit (via the `[accel]` extra) is the natural upgrade.

## Cards

Poisson count model on team disciplinary rates with a home-advantage factor (home teams get fewer cards) and an optional referee-strictness multiplier. Produces yellow/red expectations, booking points, and over/under card lines. Cards are under-dispersed, so COM-Poisson is the accuracy upgrade.

## Per-half scoring

Two independent Poisson models — first-half rates from half-time goals, second-half rates from full-minus-half goals — giving the probability each team scores in each half and the likeliest half-time result. This independent-halves approach is practitioner-grade, not a canonical academic method; treat per-half figures as estimates.

## Trustworthiness: backtesting

`walk_forward(history, model)` trains only on matches strictly before each test match (no look-ahead leakage) and scores predictions with ranked probability score, log-loss, Brier score, and a calibration curve. Use it to compare models before trusting a forecast.
