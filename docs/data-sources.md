# Data Sources

Every source implements the `DataSource` protocol (`fetch_team_history`, `fetch_fixtures`) and registers a name usable as `forecast_fixture(..., source=<name>)`. All are free.

## API-Football (`api_football`)

- Host `v3.football.api-sports.io`, header `x-apisports-key`. Free tier: **100 requests/day + 10/min**.
- Exposes fixture statistics (**corner kicks, yellow/red cards, shots**) and `score.halftime`. Confirmed **World Cup 2026** coverage.
- Key is read from `SOCCER_PREDICTION_API_FOOTBALL_KEY`. Requests go through the caching/backoff layer, so the daily quota stretches far.

## StatsBomb open-data (`statsbomb`)

- Free event-level data via the optional `statsbombpy` package (`pip install -e ".[accel]"`).
- Covers **World Cup 2018 and 2022** (and more); corners and cards are aggregated from events.
- **License: non-commercial + attribution.** Respect it; attribute StatsBomb in any published output.

## football-data.co.uk (`football_data_csv`)

- No auth. Bulk historical CSVs with columns `HC`/`AC` (corners), `HY`/`AY`/`HR`/`AR` (cards), `HTHG`/`HTAG` (half-time), `FTHG`/`FTAG` (full-time).
- **Club leagues only** (no internationals). Use it to fit corner/card rate priors. Terms: "All Rights Reserved" betting portal; personal use of downloaded files.

## openfootball (`worldcup_open`, `worldcup_2026`)

- No auth, **public domain (CC0)**. openfootball `worldcup.json` gives fixtures, full-time and half-time scores (`score.ft` / `score.ht`), and goalscorers.
- **Real, current World Cup 2026 results** live at `https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json` (constant `soccer_prediction.datasources.worldcup_open.WC2026_URL`).
- The registered `worldcup_2026` source fetches that file directly, so `forecast_fixture(home, away, source="worldcup_2026")` predicts from actual tournament results. `worldcup_open` reads any openfootball file from a URL or local path.
- Provides **goals and half-time scores only** — no corners or cards. Score, 1X2, BTTS, over/under, and per-half markets use real data; corner/card markets fall back to model priors. Use `api_football` (free key) or `statsbomb` for real corners/cards.

## Choosing a source

| Goal | Source |
| --- | --- |
| WC2026 fixtures + live corner/card/HT stats | `api_football` |
| International corner/card history | `statsbomb` (WC 2018/2022) |
| Deep corner/card rate priors | `football_data_csv` (club leagues) |
| WC fixture list + international goals/HT | `worldcup_open` |
| Offline demo, no setup | `bundled_wc2026`, `bundled_swi_col` |

Add your own source by implementing the protocol and decorating a factory with `@register_source("my_source")`.
