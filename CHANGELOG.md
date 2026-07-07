# Changelog

All notable changes to `soccer-prediction` are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-07

Initial release.

### Added

- Free-data ingestion behind a `DataSource` protocol: API-Football, StatsBomb open-data, football-data.co.uk CSV, and openfootball/martj42 adapters, with a caching layer (TTL, atomic writes, token-bucket rate limiting, exponential backoff on 429/5xx).
- Ingest-boundary normalization and validation that quarantines malformed records.
- Shrinkage-adjusted team rate computation with exponential recency weighting.
- Prediction models behind a `Predictor` protocol: independent Poisson and Dixon-Coles goal models producing a scoreline grid; market derivation (1X2, over/under, BTTS, correct score); dedicated corners (total + minimum), cards, and per-half models.
- Walk-forward backtesting with ranked probability score, log-loss, Brier score, and calibration curve.
- Public API (`forecast_fixture`, `predict_match`), a `soccer-predict` Typer CLI (`predict`/`fetch`/`backtest`), and text/JSON/Markdown/HTML reporting.
- Offline worked examples: World Cup 2026 (Brazil vs Argentina) and Switzerland vs Colombia, each with bundled sample history and generated HTML/Markdown reports.
- Full test suite (`pytest`), typed to `mypy --strict`, linted with `ruff`.

### Packaging

- Pure-Python runtime with light dependencies (`typer`, `pyyaml`); heavy scientific/accelerator libraries (`numpy`, `scipy`, `pandas`, `statsmodels`, `penaltyblog`, `statsbombpy`) are optional under the `accel` extra.
- Version sourced from installed wheel metadata; build with `python -m build`.

[0.1.0]: https://github.com/armandabiri/soccer-prediction/releases/tag/v0.1.0
