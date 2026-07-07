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

## openfootball / martj42 (`worldcup_open`)

- No auth, **public domain (CC0)**. openfootball `world-cup.json` gives fixtures and half-time scores (1930–2026); martj42 gives international results (scores only).
- Best free backbone for the World Cup fixture list and international goal/half-time history.

## Choosing a source

| Goal | Source |
| --- | --- |
| WC2026 fixtures + live corner/card/HT stats | `api_football` |
| International corner/card history | `statsbomb` (WC 2018/2022) |
| Deep corner/card rate priors | `football_data_csv` (club leagues) |
| WC fixture list + international goals/HT | `worldcup_open` |
| Offline demo, no setup | `bundled_wc2026`, `bundled_swi_col` |

Add your own source by implementing the protocol and decorating a factory with `@register_source("my_source")`.
