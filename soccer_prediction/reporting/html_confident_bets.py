"""Most-confident markets and a normalized $100 model bankroll plan."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from soccer_prediction.models import MatchForecast
from soccer_prediction.reporting.html_components import _dot, _pct
from soccer_prediction.reporting.html_market_plan import render_market_plan
from soccer_prediction.reporting.market_optimizer import optimize_fixture_markets

__all__ = ["confident_bets_section"]

_BANKROLL = 100.0
_MIN_PROB = 0.08


@dataclass(frozen=True, slots=True)
class _Pick:
    category: str
    market: str
    selection: str
    probability: float
    side: str  # home | away | draw | neutral
    note: str = ""


def confident_bets_section(forecast: MatchForecast) -> str:
    """List high-confidence model picks and a $100 normalized allocation."""
    market_plan = optimize_fixture_markets(forecast)
    if market_plan is not None:
        return render_market_plan(market_plan)
    picks = _collect_picks(forecast)
    if not picks:
        return ""
    categories = sorted({pick.category for pick in picks})
    cat_budget = _BANKROLL / len(categories)
    weights = _category_weights(picks)
    allocations: list[tuple[_Pick, float, float]] = []
    for category in categories:
        group = [pick for pick in picks if pick.category == category]
        total_w = sum(weights[id(pick)] for pick in group) or 1.0
        for pick in group:
            stake = cat_budget * weights[id(pick)] / total_w
            share = 100.0 * stake / _BANKROLL
            allocations.append((pick, stake, share))
    allocations.sort(key=lambda item: (-item[2], -item[0].probability, item[0].category, item[0].selection))
    rows: list[str] = []
    for pick, stake, share in allocations:
        color = _side_color(pick.side)
        rows.append(
            f'<tr style="background:color-mix(in srgb,{color} 12%,transparent)">'
            f"<td>{escape(pick.category)}</td>"
            f"<td>{_dot(color)}{escape(pick.market)}</td>"
            f"<td>{escape(pick.selection)}</td>"
            f'<td class="n">{_pct(pick.probability)}</td>'
            f'<td class="n">${stake:.2f}</td>'
            f'<td class="n">{share:.1f}%</td>'
            f"<td>{escape(pick.note)}</td></tr>"
        )
    cat_bars = "".join(_category_bar(category, cat_budget) for category in categories)
    legend = (
        '<div class="cmap-legend">'
        f'<span>{_dot("var(--home)")}Home-side lean</span>'
        f'<span>{_dot("var(--away)")}Away-side lean</span>'
        f'<span>{_dot("var(--draw)")}Draw / neutral market</span>'
        '<span><i class="cmap-swatch home"></i>Category budget slice</span>'
        "</div>"
    )
    table = (
        '<div style="overflow-x:auto"><table>'
        '<thead><tr><th>Category</th><th>Market</th><th>Selection</th>'
        '<th class="n">Model prob</th><th class="n">Stake</th>'
        '<th class="n">% of $100</th><th>Note</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )
    total = sum(stake for _pick, stake, _share in allocations)
    return (
        '<h2>Most confident markets - $100 model bankroll</h2><div class="card">'
        '<p class="sub">Equal budget per category, then proportional stakes within each category by '
        "relative confidence. Rows are sorted by % of $100 (highest first). This is a "
        "model-probability plan (not venue quotes); it normalizes categories so corners, scorers, "
        "scores, and result markets are comparable on one $100 roll.</p>"
        f"{legend}"
        f'<div class="cat-budget">{cat_bars}</div>'
        f"{table}"
        f'<p class="foot">Deployed <strong>${total:.2f}</strong> across {len(allocations)} picks in '
        f"{len(categories)} categories (${cat_budget:.2f} each). Cash held: "
        f"<strong>${max(0.0, _BANKROLL - total):.2f}</strong>. Replace model probs with executable "
        "asks before staking real money.</p></div>"
    )


def _category_bar(category: str, budget: float) -> str:
    width = 100.0 * budget / _BANKROLL
    return (
        f'<div class="cat-budget-row"><span class="cat-budget-label">{escape(category)}</span>'
        f'<div class="cat-budget-track"><span class="cat-budget-fill" style="width:{width:.1f}%"></span></div>'
        f'<span class="cat-budget-amt">${budget:.2f}</span></div>'
    )


def _side_color(side: str) -> str:
    if side == "home":
        return "var(--home)"
    if side == "away":
        return "var(--away)"
    return "var(--draw)"


def _category_weights(picks: list[_Pick]) -> dict[int, float]:
    """Confidence weight: probability raised to temper longshots within a category."""
    return {id(pick): max(pick.probability, 1e-6) ** 1.25 for pick in picks}


def _collect_picks(forecast: MatchForecast) -> list[_Pick]:
    home = forecast.fixture.home_team
    away = forecast.fixture.away_team
    picks: list[_Pick] = []
    home_p, draw_p, away_p = forecast.correct_score.home_draw_away()
    result_candidates = (
        ("Match result", f"{home} win", home_p, "home"),
        ("Match result", "Draw", draw_p, "draw"),
        ("Match result", f"{away} win", away_p, "away"),
    )
    best_result = max(result_candidates, key=lambda item: item[2])
    if best_result[2] >= _MIN_PROB:
        picks.append(
            _Pick("1X2", best_result[0], best_result[1], best_result[2], best_result[3], "top 1X2")
        )
    under, over = forecast.correct_score.over_under(2.5)
    ou_side = ("Over 2.5", over, "neutral") if over >= under else ("Under 2.5", under, "neutral")
    if ou_side[1] >= 0.45:
        picks.append(_Pick("Goals", "Total goals", ou_side[0], ou_side[1], ou_side[2], "O/U 2.5"))
    btts_yes = forecast.btts.probability
    btts_no = 1.0 - btts_yes
    chosen = ("BTTS yes", btts_yes, "neutral") if btts_yes >= btts_no else ("BTTS no", btts_no, "neutral")
    if chosen[1] >= 0.45:
        picks.append(_Pick("Goals", "Both teams to score", chosen[0], chosen[1], chosen[2]))

    ranked_scores = _top_scores(forecast, limit=3)
    for label, probability in ranked_scores:
        if probability < _MIN_PROB:
            continue
        home_g, away_g = _parse_score(label)
        side = "home" if home_g > away_g else "away" if away_g > home_g else "draw"
        picks.append(_Pick("Correct score", "Exact score", label, probability, side, "top scorelines"))

    for line, probability in sorted(forecast.corners.total_over_lines.items()):
        over_p = probability
        under_p = 1.0 - probability
        if over_p >= under_p and over_p >= 0.50:
            picks.append(
                _Pick("Corners", f"Total corners O{line:g}", f"Over {line:g}", over_p, "neutral")
            )
        elif under_p >= 0.50:
            picks.append(
                _Pick("Corners", f"Total corners U{line:g}", f"Under {line:g}", under_p, "neutral")
            )
        break  # one primary corner line
    if forecast.corners.home_expected >= forecast.corners.away_expected:
        picks.append(
            _Pick(
                "Corners",
                "Team corners lean",
                f"{home} more corners ({forecast.corners.home_expected:.1f} vs "
                f"{forecast.corners.away_expected:.1f})",
                min(0.72, 0.50 + 0.08 * (forecast.corners.home_expected - forecast.corners.away_expected)),
                "home",
                "expected corners",
            )
        )
    else:
        picks.append(
            _Pick(
                "Corners",
                "Team corners lean",
                f"{away} more corners ({forecast.corners.away_expected:.1f} vs "
                f"{forecast.corners.home_expected:.1f})",
                min(0.72, 0.50 + 0.08 * (forecast.corners.away_expected - forecast.corners.home_expected)),
                "away",
                "expected corners",
            )
        )

    for line, probability in sorted(forecast.cards.over_under_lines.items()):
        if probability >= 0.50:
            picks.append(_Pick("Cards", f"Cards O{line:g}", f"Over {line:g}", probability, "neutral"))
        elif 1.0 - probability >= 0.50:
            picks.append(
                _Pick("Cards", f"Cards U{line:g}", f"Under {line:g}", 1.0 - probability, "neutral")
            )
        break

    if forecast.scorers is not None:
        scorers = sorted(forecast.scorers.players, key=lambda item: item.score_probability, reverse=True)
        for player in scorers[:3]:
            if player.score_probability < 0.12:
                continue
            side = "home" if player.team.casefold() == home.casefold() else "away"
            picks.append(
                _Pick(
                    "Scorers",
                    "Anytime scorer",
                    player.player,
                    player.score_probability,
                    side,
                    player.team,
                )
            )
        assisters = sorted(forecast.scorers.players, key=lambda item: item.assist_probability, reverse=True)
        for player in assisters[:2]:
            if player.assist_probability < 0.10:
                continue
            side = "home" if player.team.casefold() == home.casefold() else "away"
            picks.append(
                _Pick(
                    "Assists",
                    "Anytime assist",
                    player.player,
                    player.assist_probability,
                    side,
                    player.team,
                )
            )

    if forecast.knockout is not None:
        ko = forecast.knockout
        if ko.home_advance >= ko.away_advance:
            picks.append(
                _Pick("Knockout", "To advance", home, ko.home_advance, "home", "incl. ET/pens")
            )
        else:
            picks.append(
                _Pick("Knockout", "To advance", away, ko.away_advance, "away", "incl. ET/pens")
            )

    if forecast.per_half.half_time_result is not None:
        ht = forecast.per_half.half_time_result
        side = "draw"
        if home.casefold() in ht.selection.casefold():
            side = "home"
        elif away.casefold() in ht.selection.casefold():
            side = "away"
        if ht.probability >= 0.30:
            picks.append(_Pick("Halves", "Half-time result", ht.selection, ht.probability, side))

    return picks


def _top_scores(forecast: MatchForecast, *, limit: int) -> list[tuple[str, float]]:
    grid = forecast.correct_score
    scored: list[tuple[str, float]] = []
    for home_goals, row in enumerate(grid.probabilities):
        for away_goals, probability in enumerate(row):
            home_label = f"{home_goals}{'+' if home_goals == grid.home_goals_max else ''}"
            away_label = f"{away_goals}{'+' if away_goals == grid.away_goals_max else ''}"
            scored.append((f"{home_label}-{away_label}", probability))
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def _parse_score(label: str) -> tuple[int, int]:
    left, right = label.replace("+", "").split("-", 1)
    return int(left), int(right)
