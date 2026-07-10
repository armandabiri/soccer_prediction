# Prediction Models

All goal-derived markets come from a single scoreline probability distribution so they stay mutually consistent. Corner, card, and per-half markets are separate count models. Every model implements the `Predictor`/fit-predict shape and consumes shrinkage-adjusted team rates from `soccer_prediction.features`.

## Team rates

`compute_rates(history)` builds per-team attack/defence goal rates, corner-for/against rates, card rates, and half-time rates, with configurable exponential **recency weighting** and **shrinkage** of small samples toward a realistic global prior — important for sparse international data. With no history, the prior is 1.35 goals per team rather than a degenerate zero-goal forecast.

By default, forecasting loads the two target histories and the histories of up to ten of their most recent opponents. An eight-pass opponent adjustment propagates strength through paths such as A–D–F–Z: scoring against a strong defence counts more than scoring against a weak one. The graph is bounded by `opponent_network_depth` and `opponent_network_max_teams` to control API use. Direct head-to-head records receive a separate recency-weighted blend capped at 35%, so a small matchup sample cannot overwhelm broader form.

## Goals: robust ensemble (`ensemble`, default)

The default model is a linear probability pool of Dixon-Coles (30%), Negative Binomial (25%), Bivariate Poisson (20%), and Monte Carlo scenarios (25%). Combining models with different failure modes makes the headline grid less sensitive to any single distributional assumption. The weights are normalized and every derived goal market still comes from the same final grid.

## Goals: independent Poisson (`poisson`)

Estimates home/away goal expectations from team rates and forms the outer-product scoreline grid up to `model.max_goals`. Simple and fast; tends to under-predict draws.

## Goals: Dixon-Coles (`dixon_coles`)

Extends the Poisson grid with a low-score dependence correction that lifts low-scoring draw mass, then renormalizes. The correction strength adapts to the observed low-draw frequency. This remains a lightweight Dixon-Coles-inspired approximation rather than a full maximum-likelihood fit.

## Goals: Negative Binomial (`negative_binomial`)

Uses a Gamma-Poisson mixture for each team's goals. Dispersion is estimated from the history and bounded for sparse samples. Its heavier tails allocate more probability to scoreless and high-scoring surprises that an equidispersed Poisson model tends to understate.

## Goals: Bivariate Poisson (`bivariate_poisson`)

Adds a shared scoring process to private home and away Poisson processes. The shared component introduces positive within-match goal correlation, representing tempo and game-state effects where an open match raises both teams' scoring chances.

## Goals: latent-state simulation (`monte_carlo`)

Runs 20,000 pure-Python simulations by default. Each draw includes a shared log-normal tempo shock and explicit cagey, open, home-momentum, or away-momentum states. A stable fixture-derived seed makes repeated forecasts reproducible. Configure the run count and seed with `model.scenario_simulations` and `model.random_seed`.

## Robustness diagnostics

Every `MatchForecast` compares Poisson, Dixon-Coles, Negative Binomial, Bivariate Poisson, and Monte Carlo 1X2 estimates. `scenario_analysis` reports the maximum model disagreement, normalized 1X2 entropy, recent-data uncertainty, middle-80% goal ranges, clean sheets, 0-0, five-plus-goal matches, and three-plus-goal winning margins. `matchup_context` adds recency-weighted form, direct meetings, indirect graph paths, and an inferred tempo/width/physicality style based on the goal, corner, and card models. “Model agreement” measures agreement among these assumptions; it is not a guarantee of accuracy.

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
