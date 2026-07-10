# API Reference

Public surface of `soccer_prediction`. Import from the top-level package or `soccer_prediction.public`.

## Forecasting

### `forecast_fixture(home, away, *, model="ensemble", source="auto") -> MatchForecast`

Forecast every supported market for a fixture.

- `home`, `away` (`str`): team names.
- `model` (`str`): registered predictor — `ensemble` (default), `poisson`, `dixon_coles`, `negative_binomial`, `bivariate_poisson`, or `monte_carlo`.
- `source` (`str`): data source — `auto` (model priors, no network), a registered adapter (`api_football`, `football_data_csv`, `worldcup_open`, `statsbomb`), or a bundled demo source (`bundled_wc2026`, `bundled_swi_col`).
- Returns a `MatchForecast`. Raises `InsufficientHistoryError` when a non-`auto` source yields no usable history.

### `predict_match(home, away, market, *, model="ensemble", source="auto") -> MarketPrediction`

Return a single market: `result`, `over_under`, `btts`, or any key from `derive_markets` (`home_win`, `draw`, `away_win`, `over_2_5`, `btts_yes`, …).

## Result types (`soccer_prediction.models`)

| Type | Key fields |
| --- | --- |
| `MatchForecast` | `result`, `correct_score` (`ScorelineGrid`), `over_under`, `btts`, `per_half`, `corners`, `cards`, `scenario_analysis`, `matchup_context`, `model_name`, `generated_notes` |
| `ScenarioAnalysis` | simulation count and goal intervals, clean-sheet/tail probabilities, model disagreement, outcome uncertainty, `model_estimates` |
| `ModelEstimate` | one model's 1X2 probabilities and home/away expected goals |
| `MatchupContext` | recent forms, direct-meeting record, opponent-network paths/coverage, and inferred game style |
| `TeamForm` | recency-weighted effective sample, points, goals, corners, and last-five result labels |
| `PlayerStats` | career appearances/goals/assists plus optional matched `recent_*` fields covering at most 20 appearances |
| `PlayerMarketPrediction` | separate score/assist probabilities, combined and first-scorer probabilities, recent-form display metrics |
| `ScorelineGrid` | `home_draw_away()`, `both_teams_to_score()`, `over_under(line)`, `total_probability()`, `cell_probability(h, a)` |
| `CornersPrediction` | `home_expected`, `away_expected`, `total_expected`, `total_over_lines`, `home_minimum`, `away_minimum`, `prob_at_least` |
| `CardsPrediction` | `yellows_expected`, `reds_expected`, `total_expected`, `over_under_lines`, `booking_points_expected` |
| `PerHalfPrediction` | `first_half_grid`, `second_half_grid`, `*_half_home_expected`, `*_half_away_expected`, `half_time_result` |
| `MarketPrediction` | `market`, `selection`, `probability`, `line`, `description` |
| `TeamMatchStats` | frozen per-match record: goals, half-time goals, corners, cards, `source`, `fetched_at` |

## Reporting (`soccer_prediction.reporting`)

- `render_text(forecast) -> str`
- `render_markdown(forecast) -> str`
- `render_html(forecast, *, title=None) -> str` — self-contained, theme-aware HTML document.
- `render_json(forecast) -> str`

## Extension points

- `soccer_prediction.datasources.base`: `DataSource` protocol, `register_source(name)`, `get_source(name)`, `list_sources()`.
- `soccer_prediction.predictors.base`: `Predictor` protocol, `register_model(name)`, `get_model(name)`, `list_models()`.
- `soccer_prediction.calibration`: `walk_forward(history, model)`, `metrics_report(result)`, `ranked_probability_score`, `log_loss`, `brier_score`, `calibration_curve`.

## Configuration (`soccer_prediction.config`)

`load_config(path=None) -> AppConfig`. Env overrides (prefix `SOCCER_PREDICTION_`):

| Env variable | Field | Default |
| --- | --- | --- |
| `SOCCER_PREDICTION_API_FOOTBALL_KEY` | `api_football.api_key` | `""` |
| `SOCCER_PREDICTION_API_FOOTBALL_HOST` | `api_football.host` | `v3.football.api-sports.io` |
| `SOCCER_PREDICTION_CACHE_DIR` | `cache.dir` | `.cache/soccer_prediction` |
| `SOCCER_PREDICTION_CACHE_TTL_HOURS` | `cache.ttl_hours` | `24` |
| `SOCCER_PREDICTION_MODEL_MAX_GOALS` | `model.max_goals` | `8` |
| `SOCCER_PREDICTION_MODEL_RECENCY_WINDOW_DAYS` | `model.recency_window_days` | `730` |
| `SOCCER_PREDICTION_MODEL_TIME_DECAY_XI` | `model.time_decay_xi` | `0.0039` |
| `SOCCER_PREDICTION_MODEL_SCENARIO_SIMULATIONS` | `model.scenario_simulations` | `20000` |
| `SOCCER_PREDICTION_MODEL_RANDOM_SEED` | `model.random_seed` | `2026` |
| `SOCCER_PREDICTION_MODEL_OPPONENT_NETWORK_DEPTH` | `model.opponent_network_depth` | `1` |
| `SOCCER_PREDICTION_MODEL_OPPONENT_NETWORK_MAX_TEAMS` | `model.opponent_network_max_teams` | `12` |

API keys are read from the environment only; never commit them.
