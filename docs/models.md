# Prediction Models

All goal-derived markets come from a single scoreline probability distribution so they stay mutually consistent. Corner, card, and per-half markets are separate count models. Every model implements the `Predictor`/fit-predict shape and consumes shrinkage-adjusted team rates from `soccer_prediction.features`.

## Team rates

`compute_rates(history)` builds per-team attack/defence goal rates, corner-for/against rates, card rates, and half-time rates, with configurable exponential **recency weighting** and **shrinkage** of small samples toward a realistic global prior — important for sparse international data. With no history, the prior is 1.35 goals per team rather than a degenerate zero-goal forecast.

By default, forecasting loads the two target histories and the histories of up to ten of their most recent opponents. An eight-pass opponent adjustment propagates strength through paths such as A–D–F–Z: scoring against a strong defence counts more than scoring against a weak one. The graph is bounded by `opponent_network_depth` and `opponent_network_max_teams` to control API use. Direct head-to-head records receive a separate recency-weighted blend capped at 35%, so a small matchup sample cannot overwhelm broader form.

### Morale and momentum proxy

Recent wins, losses, goal margins, and consecutive streaks produce a bounded `[-1, 1]` morale proxy with a roughly 90-day half-life. A run of wins raises the signal while repeated losses lower it; draws break the current streak. The relative morale edge adjusts the two teams' expected goals in opposite directions, capped at 8% by default. This is deliberately a restrained form/momentum proxy—not a direct measurement of confidence, pride, dressing-room mood, injuries, or coaching psychology—and should be interpreted that way.

## Goals: robust ensemble (`ensemble`, default)

The default model is a linear probability pool with prior weights Dixon-Coles 35%, Negative Binomial 15%, Bivariate Poisson 30%, and Monte Carlo scenarios 20%. With at least 14 distinct fixtures, a bounded recent temporal holdout scores components by 1X2 log loss and shifts at most 45% of the prior toward the better recent fits. Smaller samples retain the documented priors. Every derived goal market comes from the same pooled grid; Poisson remains an unweighted benchmark.

## Goals: independent Poisson (`poisson`)

Estimates home/away goal expectations from team rates and forms the outer-product scoreline grid up to `model.max_goals`. Simple and fast; tends to under-predict draws.

## Goals: Dixon-Coles (`dixon_coles`)

Applies the standard four-cell Dixon-Coles tau correction to 0-0, 0-1, 1-0, and 1-1, then renormalizes. The dependence strength adapts to observed low-score draws. This is still a lightweight rate-based implementation rather than a joint maximum-likelihood fit of team strengths and the dependence parameter.

## Goals: Negative Binomial (`negative_binomial`)

Uses a Gamma-Poisson mixture for each team's goals. Dispersion is estimated from the history and bounded for sparse samples. Its heavier tails allocate more probability to scoreless and high-scoring surprises that an equidispersed Poisson model tends to understate.

## Goals: Bivariate Poisson (`bivariate_poisson`)

Adds a shared scoring process to private home and away Poisson processes. The shared component introduces positive within-match goal correlation, representing tempo and game-state effects where an open match raises both teams' scoring chances.

## Goals: latent-state simulation (`monte_carlo`)

Runs 20,000 pure-Python simulations by default. Each draw includes a shared log-normal tempo shock and explicit cagey, open, home-momentum, or away-momentum states. A stable fixture-derived seed makes repeated forecasts reproducible. Configure the run count and seed with `model.scenario_simulations` and `model.random_seed`.

## Robustness diagnostics

Every `MatchForecast` reports Poisson, Dixon-Coles, Negative Binomial, Bivariate Poisson, Monte Carlo, and the ensemble conclusion. Each row includes 1X2, model goals, over 2.5, BTTS, top score, and an approximate 80% sensitivity range; the ensemble range also includes component spread. These are not formally calibrated confidence guarantees. The report adds stacked 1X2 bars, forest-style ranges, goals-market comparison, an ensemble score heatmap, and tail-scenario bars. `scenario_analysis` also reports entropy, data quality, clean sheets, 0-0, five-plus goals, and large winning margins. The component models share data and feature estimates, so agreement is useful evidence but not an independent vote or a guarantee.

The score grid's final row and column are `max_goals+` overflow buckets for every goal model. This preserves tail probability consistently instead of discarding or conditionally renormalizing high scores.

Set `as_of` for retrospective forecasts; matches after that date are excluded from rates, adaptive weights, form, head-to-head, and morale. Set `neutral_venue=True` for tournament fixtures at neutral grounds to remove goal, corner, and card home effects.

## Derived goal markets

From the grid: `home_draw_away()` (1X2), `over_under(line)` (tail sums), `both_teams_to_score()` (`1 − P(home=0) − P(away=0) + P(0,0)`), and the correct-score cells.

## Corners: total and minimum

Per-team corner expectations from corner-for × opponent corner-against rates. When corner data exists, the same connected-opponent idea iteratively adjusts corner production and concession strength; recent direct meetings receive a capped corner blend. Over/under lines are Poisson upper-tail sums `P(total ≥ k)`. The **minimum** is the 10th-percentile floor of the per-team distribution — the smallest count whose cumulative probability reaches ~10%. "Minimum corners" is inference from the fitted count distribution, not a standard betting market; corners are overdispersed, so a Negative-Binomial count fit is a further upgrade.

## Cards

Poisson count model on team disciplinary rates with a home-advantage factor (home teams get fewer cards) and an optional referee-strictness multiplier. Produces yellow/red expectations, booking points, and over/under card lines. Cards are under-dispersed, so COM-Poisson is the accuracy upgrade.

## Player scoring and assists

Player goal and assist allocation uses per-appearance production rather than raw career totals, with position-specific empirical priors to stabilize small samples. When a player source supplies `recent_appearances`, `recent_goals`, and `recent_assists` for up to 20 games, recent form receives a bounded 55% blend; otherwise reports clearly mark an up-to-20 equivalent estimated from aggregate totals. The HTML report shows both compact per-player form bars and an all-player comparison chart (20 bars for the bundled two-squad data). The model exposes separate score, assist, score-or-assist, and first-scorer probabilities. Expected assists are limited to a 72% assisted-goal share so assist markets do not assume every goal has a credited assist. These estimates still assume participation and are not lineup/minutes-aware.

## Per-half scoring

Two independent Poisson models — first-half rates from half-time goals, second-half rates from full-minus-half goals — giving the probability each team scores in each half and the likeliest half-time result. This independent-halves approach is practitioner-grade, not a canonical academic method; treat per-half figures as estimates.

## Trustworthiness: backtesting

`walk_forward(history, model)` trains only on matches strictly before each test match (no look-ahead leakage) and scores predictions with ranked probability score, log-loss, Brier score, and a calibration curve. Use it to compare models before trusting a forecast.
