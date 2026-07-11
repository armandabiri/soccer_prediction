# soccer-prediction — Quick reference for AI assistants

This file helps AIs quickly understand soccer-prediction and how to use it.
For full user-facing documentation see [README.md](README.md).

## 1. What this folder does

- Forecasts soccer matches (World Cup 2026 headline use case) from free historical stats: full-time/per-half scorelines, corners (total + minimum), cards, BTTS, over/under, goalscorer/assist markets, and knockout extra-time/penalty-shootout probabilities.
- Ships as an installable wheel (`soccer-prediction`) with a pure-Python runtime core, an optional `[accel]` extra for numpy/scipy/statsmodels/penaltyblog, a `soccer-predict` Typer CLI, and runnable offline examples.
- Is NOT a live betting service or a hosted API — it is a library and CLI that run locally against pluggable data sources.

## 2. Layout

| Area | Path | Contents |
| --- | --- | --- |
| Import package | `soccer_prediction/` | Public facade (`public.py`), CLI wiring (`__main__.py`), version (`version.py`) |
| Data sources | `soccer_prediction/datasources/` | `DataSource` protocol/registry (`base.py`) and adapters: API-Football, StatsBomb, football-data.co.uk CSV, openfootball, martj42 international results, plus a caching/rate-limit layer (`cache.py`) |
| Ingestion | `soccer_prediction/ingest/` | Record normalization and validation before feature computation |
| Features | `soccer_prediction/features/` | Team rate computation (`rates.py`) with recency weighting and shrinkage |
| Predictors | `soccer_prediction/predictors/` | `Predictor` protocol/registry (`base.py`) and models: Poisson, Dixon-Coles, corners, cards, half-time, knockout, scorers, markets derivation |
| Strategy | `soccer_prediction/strategy/` | Quote validation, value screening, bankroll allocation, live exits, path ledgers, presets, and strategy builder |
| Models | `soccer_prediction/models/` | Typed dataclasses for matches, teams, players, and predictions — see [`soccer_prediction/models/AGENTS.md`](soccer_prediction/models/AGENTS.md) |
| Calibration | `soccer_prediction/calibration/` | Walk-forward backtesting and evaluation metrics (RPS, log-loss, Brier) |
| CLI | `soccer_prediction/cli/` | Typer app (`main.py`) with `predict`, `fetch`, `backtest` subcommands |
| Config | `soccer_prediction/config/` | `AppConfig` loader merging `defaults.yaml` with `SOCCER_PREDICTION_*` env vars |
| Reporting | `soccer_prediction/reporting/` | Text/JSON/Markdown/HTML forecast and optional strategy renderers |
| Examples | `soccer_prediction/example/` | Offline worked examples (World Cup 2026, Switzerland vs Colombia) with bundled sample data |
| Tests | `tests/` | Test suite — see [`tests/AGENTS.md`](tests/AGENTS.md) |
| Docs | `docs/` | Topic docs: `api.md`, `data-sources.md`, `models.md` |

## 3. Entry points

- `soccer-predict` (console script) — `pyproject.toml` (Lines 51-52) → `soccer_prediction:main` → `soccer_prediction/cli/main.py` Typer `app`.
- `python -m soccer_prediction` — `soccer_prediction/__main__.py` (Lines 1-8) runs the bundled World Cup 2026 example via `soccer_prediction.example.run_example`.
- `forecast_fixture(home, away, *, model="dixon_coles", source="auto")` — `soccer_prediction/public.py`, the primary library entry point that assembles a `MatchForecast`.
- `build_betting_strategy(forecast, quotes, *, request=None, live_context=None)` — `soccer_prediction/strategy/public.py`; it calculates allocation and exits but never places orders.

## 4. Environment variables

| Variable | Purpose |
| --- | --- |
| `SOCCER_PREDICTION_API_FOOTBALL_KEY` | API-Football key; read from env only, never hard-coded. |
| `SOCCER_PREDICTION_API_FOOTBALL_HOST` | Overrides the API-Football host (default `v3.football.api-sports.io`). |
| `SOCCER_PREDICTION_CACHE_DIR` | On-disk response cache directory (default `.cache/soccer_prediction`). |
| `SOCCER_PREDICTION_CACHE_TTL_HOURS` | Cache freshness window in hours. |
| `SOCCER_PREDICTION_MODEL_MAX_GOALS` | Scoreline grid size for goal models. |
| `SOCCER_PREDICTION_MODEL_RECENCY_WINDOW_DAYS` | Recency-weighting window for team rates. |
| `SOCCER_PREDICTION_MODEL_TIME_DECAY_XI` | Time-decay parameter for goal-rate weighting. |
| `SOCCER_PREDICTION_RATE_LIMITS_API_FOOTBALL` | Overrides the API-Football daily request cap. |

## 5. Key concepts for code changes

- Runtime dependencies are pure-Python (`typer`, `pyyaml`); the scientific stack (numpy, scipy, pandas, statsmodels, penaltyblog, statsbombpy, requests) is gated behind the optional `[accel]` extra so `pip install` stays fast — do not add a hard import of an `[accel]` package outside code that degrades gracefully without it.
- Every data source implements the `DataSource` protocol (`fetch_team_history`, `fetch_fixtures`) and registers via `@register_source(name)` in `soccer_prediction/datasources/base.py`. Adapters lacking corner, card, or half-time data hardcode zeros rather than omitting the fields, and downstream predictors (`corners.py`, `cards.py`) fall back to league-average priors when the observed rate is near zero.
- Every prediction model implements the `Predictor` protocol (`fit`, `predict_scoreline`, `predict_market`) and registers via `@register_model(name)` in `soccer_prediction/predictors/base.py`; `dixon_coles` is the default model in `forecast_fixture`.
- Sources that also expose squad data implement the optional `PlayerSource` protocol (`fetch_players`) in `soccer_prediction/datasources/base.py`; `forecast_fixture` only attaches `scorers` to the `MatchForecast` when the resolved source satisfies this protocol.
- Strategy money, prices, fees, and quantities use `Decimal`. Entry screening uses asks plus costs; exit cash uses bid-side targets minus fees. Missing or stale quotes are never replaced by midpoints.
- `soccer_prediction/example/fixture_example.py::write_reports` includes the packaged `illustrative_demo_not_live` snapshot by default; pass `quote_path` for current quotes or `include_strategy=False` for forecast-only output.
- Report writers (`soccer_prediction/example/fixture_example.py::write_reports`, `soccer_prediction/example/worldcup2026_live.py::write_wc2026_report`) generate timestamped filenames (`<name>_<YYYY-MM-DD_HH-MM-SS>.{html,md}`) by default; the CLI's `--output` flag always writes to the literal given path instead.
- `soccer_prediction/example/fixture_example.py::FIXTURES` is the single constant registry of competing team pairs (Switzerland/Colombia, France/Morocco, Argentina/Egypt); each entry owns its own bundled data files and registered source names via `FixtureDataSource`, so adding a fixture never collides with another one's registration.
- Authored source files are expected to stay under 300 lines per project convention; `soccer_prediction/reporting/html_report.py` currently exceeds this at 387 lines and is a candidate for splitting (for example, extracting the per-market section renderers into a submodule) before further additions.

## 6. Tests

```bash
python -m pytest --cov=soccer_prediction
```

## 7. Related

- [`soccer_prediction/models/AGENTS.md`](soccer_prediction/models/AGENTS.md) — typed dataclasses consumed throughout this package.
- [`tests/AGENTS.md`](tests/AGENTS.md) — test suite layout and fixtures.
- [`README.md`](README.md) — human-facing overview, quick start, and CLI reference.

---
Generated by Codebase Cartographer | Run manifest: `.intelag/reports/cartographer/20260707_174126/cartographer_run_manifest.v1.json`
