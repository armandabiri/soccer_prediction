"""HTML visualizations comparing goal-model families and their ensemble."""

from __future__ import annotations

from html import escape

from soccer_prediction.models import MatchForecast, ModelEstimate, ScorelineGrid

__all__ = ["model_comparison_section", "ensemble_heatmap_section"]


def _name(item: ModelEstimate) -> str:
    return item.model_name.replace("_", " ").title()


def _badges(item: ModelEstimate) -> str:
    badges = []
    if item.is_ensemble:
        badges.append('<span class="model-badge conclusion">conclusion</span>')
    if item.is_selected:
        badges.append('<span class="model-badge">selected</span>')
    return "".join(badges)


def _outcome_chart(estimates: tuple[ModelEstimate, ...], home: str, away: str) -> str:
    rows = []
    for item in estimates:
        label = escape(_name(item)) + _badges(item)
        aria = f"{_name(item)}: {home} {item.home_win:.1%}, draw {item.draw:.1%}, {away} {item.away_win:.1%}"
        rows.append(
            f'<div class="model-row"><div class="model-label">{label}</div>'
            f'<div class="stacked" role="img" aria-label="{escape(aria, quote=True)}">'
            f'<span class="seg home" style="width:{item.home_win * 100:.2f}%">{item.home_win:.0%}</span>'
            f'<span class="seg draw" style="width:{item.draw * 100:.2f}%">{item.draw:.0%}</span>'
            f'<span class="seg away" style="width:{item.away_win * 100:.2f}%">{item.away_win:.0%}</span>'
            f"</div></div>"
        )
    return (
        '<h3>1X2 predictions by algorithm</h3><div class="model-chart">'
        + "".join(rows)
        + f'<div class="stack-legend"><span>■ {escape(home)}</span><span>■ Draw</span>'
        f'<span>■ {escape(away)}</span></div></div>'
    )


def _forest_chart(estimates: tuple[ModelEstimate, ...], home: str, away: str) -> str:
    outcomes = (
        (home, "home_win", "home_win_interval"),
        ("Draw", "draw", "draw_interval"),
        (away, "away_win", "away_win_interval"),
    )
    panels = []
    for outcome, point_field, interval_field in outcomes:
        rows = []
        for item in estimates:
            point = float(getattr(item, point_field))
            lower, upper = getattr(item, interval_field)
            rows.append(
                f'<div class="forest-row"><span>{escape(_name(item))}</span><span class="forest-track">'
                f'<i style="left:{lower * 100:.1f}%;width:{(upper - lower) * 100:.1f}%"></i>'
                f'<b style="left:{point * 100:.1f}%"></b></span><small>{point:.0%}</small></div>'
            )
        panels.append(f'<div class="forest-panel"><h4>{escape(outcome)}</h4>{"".join(rows)}</div>')
    return '<h3>Approximate 80% uncertainty ranges</h3><div class="forest-grid">' + "".join(panels) + "</div>"


def _market_chart(estimates: tuple[ModelEstimate, ...]) -> str:
    rows = []
    for item in estimates:
        rows.append(
            f'<div class="market-row"><span>{escape(_name(item))}</span>'
            f'<span class="mini-track"><i style="width:{item.over_2_5 * 100:.1f}%"></i></span>'
            f'<small>{item.over_2_5:.0%}</small><span class="mini-track btts">'
            f'<i style="width:{item.btts_yes * 100:.1f}%"></i></span><small>{item.btts_yes:.0%}</small></div>'
        )
    return (
        '<h3>Goals-market sensitivity</h3><div class="market-head"><span>Model</span><span>Over 2.5</span>'
        f'<span></span><span>BTTS</span><span></span></div><div class="market-chart">{"".join(rows)}</div>'
    )


def _comparison_table(estimates: tuple[ModelEstimate, ...]) -> str:
    rows = []
    for item in estimates:
        weight = f"{item.ensemble_weight:.0%}" if item.ensemble_weight else "—"
        loss = f"{item.validation_log_loss:.3f}" if item.validation_log_loss is not None else "—"
        rows.append(
            f"<tr><td>{escape(_name(item))}{_badges(item)}</td><td>{escape(item.role)}</td>"
            f'<td class="n">{weight}</td><td class="n">{item.home_win:.1%}</td>'
            f'<td class="n">{item.draw:.1%}</td><td class="n">{item.away_win:.1%}</td>'
            f'<td class="n">{item.home_expected_goals:.2f}–{item.away_expected_goals:.2f}</td>'
            f'<td class="n">{item.over_2_5:.1%}</td><td class="n">{item.btts_yes:.1%}</td>'
            f'<td class="n">{escape(item.most_likely_score)} ({item.most_likely_score_probability:.1%})</td>'
            f'<td class="n">{loss}</td></tr>'
        )
    header = (
        "<thead><tr><th>Algorithm</th><th>Role</th><th class=\"n\">Weight</th>"
        '<th class="n">Home</th><th class="n">Draw</th><th class="n">Away</th>'
        '<th class="n">Model goals</th><th class="n">O2.5</th><th class="n">BTTS</th>'
        '<th class="n">Top score</th><th class="n">Validation loss</th></tr></thead>'
    )
    return (
        f'<h3>Decision table</h3><div class="table-scroll"><table>{header}'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def model_comparison_section(forecast: MatchForecast) -> str:
    """Render all goal algorithms, uncertainty ranges, and ensemble diagnostics."""
    analysis = forecast.scenario_analysis
    if analysis is None or not analysis.model_estimates:
        return ""
    estimates = analysis.model_estimates
    ensemble = next((item for item in estimates if item.is_ensemble), estimates[-1])
    winner = max(
        ((forecast.fixture.home_team, ensemble.home_win), ("Draw", ensemble.draw),
         (forecast.fixture.away_team, ensemble.away_win)),
        key=lambda value: value[1],
    )
    validation = "static prior weights"
    if analysis.ensemble_validation_matches:
        validation = (
            f"regularized temporal validation on {analysis.ensemble_validation_matches} matches "
            f"({analysis.ensemble_validation_from} to {analysis.ensemble_validation_to})"
        )
    intro = (
        f'<p class="conclusion-line"><strong>Ensemble conclusion:</strong> {escape(winner[0])} '
        f"{winner[1]:.1%}. Selected output model: <strong>{escape(analysis.selected_model_name)}</strong>. "
        f"Weights use {escape(validation)}.</p>"
    )
    notes = " ".join(
        f"<strong>{escape(_name(item))}:</strong> {escape(item.description)}" for item in estimates
    )
    method = escape(analysis.interval_method)
    foot = (
        f'<p class="foot">The Poisson row is an unweighted benchmark. Component rows are blended once into '
        f"the ensemble; they are not independent votes because they share data and rate features. Lower temporal "
        f"validation log loss is better. Ranges use {method}; they are sensitivity diagnostics, not calibrated "
        f"guarantees. {notes}</p>"
    )
    content = (
        intro
        + _outcome_chart(estimates, forecast.fixture.home_team, forecast.fixture.away_team)
        + _forest_chart(estimates, forecast.fixture.home_team, forecast.fixture.away_team)
        + _market_chart(estimates)
        + _comparison_table(estimates)
        + foot
    )
    return f'<h2>Algorithm comparison &amp; ensemble</h2><div class="card model-card">{content}</div>'


def _aggregate_grid(grid: ScorelineGrid, cutoff: int = 5) -> list[list[float]]:
    result = [[0.0 for _ in range(cutoff + 1)] for _ in range(cutoff + 1)]
    for home_goals, row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(row):
            result[min(home_goals, cutoff)][min(away_goals, cutoff)] += probability
    return result


def ensemble_heatmap_section(forecast: MatchForecast) -> str:
    """Render a compact ensemble score-distribution heatmap."""
    grid = forecast.ensemble_scoreline
    if grid is None:
        return ""
    values = _aggregate_grid(grid)
    maximum = max(max(row) for row in values) or 1.0
    cells = ['<div class="heat blank"></div>']
    cells.extend(f'<div class="heat axis">{goal if goal < 5 else "5+"}</div>' for goal in range(6))
    for home_goals, row in enumerate(values):
        cells.append(f'<div class="heat axis">{home_goals if home_goals < 5 else "5+"}</div>')
        for away_goals, probability in enumerate(row):
            alpha = 0.10 + 0.82 * probability / maximum
            home_label = home_goals if home_goals < 5 else "5 plus"
            away_label = away_goals if away_goals < 5 else "5 plus"
            aria = f"home {home_label}, away {away_label}: {probability:.1%}"
            cells.append(
                f'<div class="heat" role="img" aria-label="{aria}" style="background:rgba(37,99,235,{alpha:.2f})">'
                f"{probability:.1%}</div>"
            )
    return (
        '<h2>Ensemble score distribution</h2><div class="card"><p class="sub">Rows are home goals; '
        'columns are away goals. The 5+ cells collect the full upper tail.</p>'
        f'<div class="heatmap">{"".join(cells)}</div></div>'
    )
