"""HTML section renderer for price-aware betting strategies."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from html import escape

from soccer_prediction.models import (
    Allocation,
    BettingStrategy,
    ExitStage,
    LiveScorePlan,
    PathLedgerRow,
    PresetSummary,
)

__all__ = ["strategy_section"]


def _money(value: Decimal | None) -> str:
    return "—" if value is None else f"${value:.2f}"

def _money0(value: Decimal) -> str:
    return f"${value:.2f}"


def _prob(value: Decimal | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _pct_of(value: Decimal, whole: Decimal) -> str:
    """A value expressed as a percent of the bankroll X (blank-safe)."""
    if whole == 0:
        return "—"
    return f"{value / whole * 100:.1f}%"


def _contracts(value: Decimal) -> str:
    """A contract count with no trailing zeros — but never mangling whole numbers.

    Contracts are whole units here; format as an integer. (A naive
    ``f"{v:f}".rstrip("0")`` turns 10 into 1 by stripping the trailing zero.)
    """
    normalized = value.normalize()
    text = f"{normalized:f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _table(headers: tuple[str, ...], rows: Sequence[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{escape(value)}</th>" for value in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    return (
        f'<table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def _details(summary: str, inner: str) -> str:
    return f'<details class="details-toggle"><summary>{escape(summary)}</summary>{inner}</details>'


def _settlement_label(settlement: str) -> str:
    """Human wording for one quote's settlement basis."""
    pretty = settlement.replace("regulation_time_", "reg. 90' ").replace("_", " ")
    return pretty.strip() or "unspecified"


def _settlement_banner(strategy: BettingStrategy) -> str:
    """A prominent note stating what result these markets settle on.

    Every non-live market here is priced from the model's regulation-time (90')
    scoreline grid and the quotes settle on the regulation result — extra time
    and penalties do NOT count. Whoever *advances* in a knockout is a separate
    market shown under "Extra time & penalties", never priced in this section.
    """
    kinds = {quote.settlement for quote in (item.quote for item in strategy.evaluations)}
    reg_time = any(kind.startswith("regulation_time") for kind in kinds)
    lead = (
        "These markets settle on the <strong>regulation-time (90') result</strong> — "
        "extra time and penalties do <strong>not</strong> count."
        if reg_time
        else "Check each quote's settlement basis before betting."
    )
    return (
        '<p class="settle-note">' + lead +
        " A knockout can still be level here (the draw is a real outcome); who advances "
        "after extra time or penalties is a separate market, shown under "
        "“Extra time &amp; penalties”, and is not priced below.</p>"
    )


# ---------------------------------------------------------------------------
# 1. Betting value & bankroll allocation — horizontal net-edge bar chart
# ---------------------------------------------------------------------------

def _allocations(strategy: BettingStrategy) -> str:
    bankroll = strategy.request.bankroll
    allocated: dict[str, Allocation] = {item.evaluation.quote.key: item for item in strategy.allocations}
    max_edge = max(
        (abs(item.net_edge) for item in strategy.evaluations if item.net_edge is not None),
        default=Decimal("0.01"),
    ) or Decimal("0.01")

    chart_rows: list[str] = []
    table_rows: list[tuple[str, ...]] = []
    for item in strategy.evaluations:
        position = allocated.get(item.quote.key)
        bought = position is not None
        edge = item.net_edge or Decimal(0)
        width_pct = float(abs(edge) / max_edge * 50)
        side = "right" if edge >= 0 else "left"
        color = "var(--home)" if edge >= 0 else "var(--away)"
        fill_style = (
            f"left:50%; width:{width_pct:.1f}%; background:{color};"
            if side == "right"
            else f"right:50%; width:{width_pct:.1f}%; background:{color};"
        )
        tag = '<span class="tag buy">bought</span>' if bought else ""
        if position is not None:
            detail = (
                f'<span class="pctv">{_pct_of(position.amount, bankroll)} of X</span>'
                f'<span class="sub3">{_money(position.amount)}</span>'
            )
        else:
            detail = escape(item.intent)
        chart_rows.append(
            '<div class="edge-row">'
            f'<div class="edge-name" title="{escape(item.reason, quote=True)}">'
            f"{escape(item.quote.market)}: {escape(item.quote.selection)}{tag}</div>"
            f'<div class="edge-track"><div class="zero"></div><div class="fill" style="{fill_style}"></div></div>'
            f'<div class="edge-value"><b>{_money(item.net_edge)}</b>{detail}</div>'
            "</div>"
        )
        table_rows.append(
            (
                f"{item.quote.market}: {item.quote.selection}",
                _prob(item.model_probability),
                _money(item.quote.ask),
                _money(item.fair_price),
                _money(item.max_buy_price),
                _money(item.net_edge),
                _pct_of(position.amount, bankroll) if position else "—",
                _money(position.amount if position else Decimal(0)),
                str(position.contracts if position else 0),
                _money(position.maximum_loss if position else Decimal(0)),
                _money(position.gross_payout if position else Decimal(0)),
                _money(position.net_profit_if_win if position else Decimal(0)),
                _settlement_label(item.quote.settlement),
                item.reason,
                item.intent,
            )
        )
    deployed = bankroll - strategy.uninvested_cash
    deployed_pct = float(deployed / bankroll * 100) if bankroll else 0.0
    cash_pct = max(0.0, 100.0 - deployed_pct)
    split = (
        f'<div class="split-bar" title="of your bankroll X = {_money(bankroll)}">'
        f'<span class="dep" style="width:{deployed_pct:.1f}%">deployed {deployed_pct:.0f}%</span>'
        f'<span class="csh" style="width:{cash_pct:.1f}%">cash {cash_pct:.0f}%</span></div>'
        f'<p class="foot">Bankroll <strong>X = {_money(bankroll)}</strong>; deployed '
        f'{_pct_of(deployed, bankroll)} ({_money(deployed)}), cash {_pct_of(strategy.uninvested_cash, bankroll)} '
        f'({_money(strategy.uninvested_cash)}). Venue <strong>{escape(strategy.venue)}</strong>; '
        f'plan {escape(strategy.request.plan)}; quoted {escape(strategy.quote_observed_at.isoformat())}.</p>'
    )
    legend = (
        '<div class="cmap-legend">'
        '<span><span class="sw" style="background:var(--home)"></span>'
        "blue = positive net edge (bought)</span>"
        '<span><span class="sw" style="background:var(--away)"></span>'
        "red = negative / no edge — no bet</span>"
        "</div>"
    )
    chart = f'<div class="edge-chart">{"".join(chart_rows)}</div>{legend}'
    table = _table(
        (
            "Market / score", "Model", "Ask", "Fair", "Max buy", "Net edge", "% of X", "Allocated", "Contracts",
            "Max loss", "Gross", "Net win", "Settles on", "Reason", "Intent",
        ),
        table_rows,
    )
    table_details = _details("Show full pricing table (every quote, every column)", table)
    return (
        "<h2>Betting value &amp; bankroll allocation</h2>"
        f'<div class="card">{_settlement_banner(strategy)}{split}{chart}{table_details}</div>'
    )


# ---------------------------------------------------------------------------
# 2. Live correct-score exit ladder — per-score mini timeline cards
# ---------------------------------------------------------------------------

def _stage_bar(stage: ExitStage, total_contracts: Decimal) -> str:
    """One exit step whose track fill is the share of the position sold here.

    The bar length = contracts sold this window / total held, so the plan's
    "sell 40% now, 35%, then 25%" reads straight off the widths. The dollar
    value and the price mechanics move to the label and tooltip.
    """
    executable = stage.executable_now
    share = float(stage.contracts / total_contracts * 100) if total_contracts else 0.0
    now_cls = " now" if executable else ""
    now_text = "fillable now" if executable else "not yet fillable"
    contracts = _contracts(stage.contracts)
    safe = (
        f'<span class="safe-star" title="Cumulative planned cash covers the conservative portfolio '
        f'recovery target">★ safe at {_money(stage.recovery_target)}</span>'
        if stage.safe_to_sell
        else ""
    )
    return (
        f'<div class="ladder-step{now_cls}">'
        f'<span class="lbl">{escape(stage.minute_range)}</span>'
        f'<span class="track" title="sell {share:.0f}% of the position ({contracts} contracts) at '
        f'limit {_money(stage.target_price)}; fair {_money(stage.fair_value)}, bid {_money(stage.current_bid)} '
        f"— {now_text}\">"
        f'<b style="width:{share:.1f}%"></b></span>'
        f'<span class="amt"><span class="pctv">{share:.0f}%</span>'
        f'<span class="sub3">{contracts}c · {_money(stage.cash_received)}</span>{safe}</span>'
        "</div>"
    )


def _score_side(score: str) -> str:
    try:
        home, away = (int(value.replace("+", "")) for value in score.split("-", 1))
    except ValueError:
        return "draw"
    return "home" if home > away else "away" if away > home else "draw"


def _score_portfolio_distribution(strategy: BettingStrategy) -> str:
    """Stake allocation and terminal P/L for mutually exclusive exact scores."""
    positions = [
        item for item in strategy.allocations if item.evaluation.quote.market == "correct_score"
    ]
    if not positions:
        return ""
    plans = {item.score: item for item in strategy.live_scores}
    total_cost = sum((item.amount for item in positions), Decimal(0)) or Decimal(1)
    covered_probability = Decimal(0)
    rows: list[str] = []
    bars: list[str] = []
    for position in sorted(
        positions,
        key=lambda item: (
            -(plans.get(item.evaluation.quote.selection).model_probability if plans.get(item.evaluation.quote.selection) else Decimal(0)),
            item.evaluation.quote.selection,
        ),
    ):
        score = position.evaluation.quote.selection
        plan = plans.get(score)
        probability = plan.model_probability if plan else Decimal(0)
        covered_probability += probability
        stake_share = position.amount / total_cost
        net_if_final = position.gross_payout - total_cost
        side = _score_side(score)
        color = f"var(--{side})"
        bars.append(
            f'<div class="score-dist-row"><span class="score-dist-label">{escape(score)}</span>'
            f'<div class="score-dist-track"><span style="width:{float(stake_share * 100):.1f}%;'
            f'background:{color}"></span></div>'
            f'<span class="score-dist-value">{stake_share:.1%} · P {probability:.1%}</span></div>'
        )
        rows.append(
            "<tr>"
            f'<td><span class="dot" style="background:{color}"></span>{escape(score)}</td>'
            f'<td class="n">{probability:.1%}</td>'
            f'<td class="n">{_money(position.amount)}</td>'
            f'<td class="n">{stake_share:.1%}</td>'
            f'<td class="n">{_contracts(position.contracts)}</td>'
            f'<td class="n">{_money(position.gross_payout)}</td>'
            f'<td class="n">{_money(net_if_final)}</td></tr>'
        )
    other_probability = max(Decimal(0), Decimal(1) - covered_probability)
    rows.append(
        "<tr><td>Any unowned score</td>"
        f'<td class="n">{other_probability:.1%}</td><td class="n">$0.00</td>'
        '<td class="n">0.0%</td><td class="n">0</td><td class="n">$0.00</td>'
        f'<td class="n">{_money(-total_cost)}</td></tr>'
    )
    table = (
        '<div style="overflow-x:auto"><table><thead><tr><th>90-minute final score</th>'
        '<th class="n">Model P</th><th class="n">Money in</th><th class="n">Stake share</th>'
        '<th class="n">Contracts</th><th class="n">Gross payout</th>'
        '<th class="n">Portfolio P/L</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )
    return (
        '<h3>Exact-score portfolio: money distribution and 90-minute outcomes</h3>'
        '<p class="sub">These outcomes are mutually exclusive. The stake bars add to 100%; Model P is '
        'the ensemble probability of that final regulation score. Portfolio P/L subtracts the cost of '
        'every exact-score position, because all losing score contracts settle at $0.</p>'
        f'<div class="score-dist">{"".join(bars)}</div>{table}'
        f'<p class="ladder-foot">Owned scores cover {covered_probability:.1%} of modeled outcomes; '
        f'any other final score loses the full exact-score pool of {_money(total_cost)}.</p>'
    )


def _live(strategy: BettingStrategy) -> str:
    if not strategy.live_scores:
        return ""
    bankroll = strategy.request.bankroll
    # Card badge = each score's share of the TOTAL staked across every correct-score
    # card, so the badges across all cards sum to 100%. (Cost as a % of X is shown as
    # secondary context.) Cards with no position contribute 0% and still sum cleanly.
    ladder_total = sum((item.position_cost for item in strategy.live_scores), Decimal(0)) or Decimal(1)
    cards: list[str] = []
    for item in strategy.live_scores:
        total = sum((stage.contracts for stage in item.stages), Decimal(0))
        steps = "".join(_stage_bar(stage, total) for stage in item.stages)
        active_cls = "" if item.position_active else " inactive"
        if item.position_active:
            held = _contracts(item.allocated_contracts)
            badge = f'<span class="ladder-badge active">{_pct_of(item.position_cost, ladder_total)} of stake</span>'
            head_note = (
                f'<p class="ladder-cost">{_pct_of(item.position_cost, bankroll)} of X · '
                f'{_money(item.position_cost)} · {held} contracts held</p>'
            )
            if item.safe_sell_price is not None:
                if item.safe_sell_price <= Decimal("0.99"):
                    safe_line = (
                        f'<p class="safe-sell"><span class="safe-star">★</span> Safe portfolio exit: '
                        f'sell all at <strong>{_money(item.safe_sell_price)}/contract</strong> or better '
                        f'to net at least <strong>{_money(item.safe_recovery_target)}</strong>.</p>'
                    )
                else:
                    safe_line = (
                        f'<p class="safe-sell unsafe"><span class="safe-star">★</span> Required safe price '
                        f'is <strong>{_money(item.safe_sell_price)}/contract</strong> — above the $0.99 '
                        f'contract ceiling, so this position alone cannot cover the branch loss.</p>'
                    )
            else:
                safe_line = ""
        else:
            badge = '<span class="ladder-badge">no position · 0%</span>'
            head_note = ""
            safe_line = ""
        risk_line = (
            f'<p class="ladder-risk">Impossible now: {_money(item.impossible_cost_now)} · '
            f'next {escape(item.next_home_score)} invalidates {_money(item.next_home_goal_loss)} · '
            f'next {escape(item.next_away_score)} invalidates {_money(item.next_away_goal_loss)} · '
            f'3% safety target {_money(item.safe_recovery_target)}</p>'
        )
        cards.append(
            f'<div class="ladder-card{active_cls}"><div class="ladder-head">'
            f'<span class="ladder-score">{escape(item.score)}</span>{badge}</div>'
            f"{head_note}"
            f"{safe_line}{risk_line}"
            f'<div class="ladder-steps">{steps}</div>'
            f'<p class="ladder-foot">next goal → {escape(item.next_home_score)} or {escape(item.next_away_score)}'
            f" &nbsp;·&nbsp; if it lands before a fill: {escape(item.goal_before_fill)}</p></div>"
        )
    legend = (
        f'<p class="ladder-foot">Assumptions: {escape(strategy.live_scores[0].assumptions)} '
        "The badge on each card is that score's share of the total correct-score stake, so the badges add up "
        "to 100%. Within a card, each row is one exit window and its bar/number is the share of that position "
        "sold in the window; a highlighted row is executable against the current bid right now.</p>"
    )
    return (
        '<h2>Live correct-score exit ladder</h2>'
        f'<div class="card">{_score_portfolio_distribution(strategy)}'
        f'<div class="ladder-grid">{"".join(cards)}</div>{legend}</div>'
        + _selldown(strategy)
    )


# ---------------------------------------------------------------------------
# 2b. Sell-down progress — one cash bar per open position, open positions only
# ---------------------------------------------------------------------------

def _selldown_card(item: LiveScorePlan) -> str:
    """Show planned cash against the portfolio-aware safe-recovery target."""
    held = item.allocated_contracts
    cost = item.position_cost
    total_cash = sum((stage.cash_received for stage in item.stages), Decimal(0)) or Decimal("0.01")
    recovery_target = item.safe_recovery_target
    scale = max(total_cash, recovery_target, Decimal("0.01"))
    recovered = min(recovery_target, total_cash)
    surplus = max(Decimal(0), total_cash - recovery_target)
    shortfall = max(Decimal(0), recovery_target - total_cash)

    stage_rows: list[str] = []
    running = Decimal(0)
    for stage in item.stages:
        prior = running
        running += stage.cash_received
        toward_recovery = min(stage.cash_received, max(Decimal(0), recovery_target - prior))
        toward_surplus = max(Decimal(0), stage.cash_received - toward_recovery)
        recovery_w = float(toward_recovery / scale * 100)
        surplus_w = float(toward_surplus / scale * 100)
        safe = (
            f'<span class="safe-star" title="Cumulative cash {_money(running)} meets '
            f'the safe target {_money(recovery_target)}">★ {_money(recovery_target)}</span>'
            if stage.safe_to_sell
            else ""
        )
        stage_rows.append(
            f'<div class="wf-stage">'
            f'<span class="wf-stage-lbl">{escape(stage.minute_range)}</span>'
            f'<div class="wf-stage-bar" title="{escape(stage.minute_range)}: '
            f'sell {_contracts(stage.contracts)}c → +{_money(stage.cash_received)}">'
            f'<span class="wf-seg stake" style="width:{recovery_w:.1f}%"></span>'
            f'<span class="wf-seg profit" style="width:{surplus_w:.1f}%"></span>'
            f"</div>"
            f'<span class="wf-stage-amt">+{_money(stage.cash_received)}{safe}</span></div>'
        )

    recovery_pct = float(recovered / scale * 100)
    surplus_pct = float(surplus / scale * 100)
    shortfall_pct = float(shortfall / scale * 100)
    result_cls = "profit" if surplus > 0 else "loss" if shortfall > 0 else ""
    return (
        f'<div class="wf-card"><div class="wf-head">'
        f'<span class="wf-score">{escape(item.score)}</span>'
        f'<span class="wf-sub">{_contracts(held)} contracts · {_money(cost)} in</span></div>'
        f'<div class="wf-summary-bar" title="Blue covers the conservative next-goal portfolio loss; '
        f'red is cash above that safety target">'
        f'<span class="wf-seg stake" style="width:{recovery_pct:.1f}%">'
        f'<span class="wf-seglab">covered {_money(recovered)}</span></span>'
        f'<span class="wf-seg profit" style="width:{surplus_pct:.1f}%">'
        f'<span class="wf-seglab">surplus {_money(surplus)}</span></span>'
        f'<span class="wf-seg shortfall" style="width:{shortfall_pct:.1f}%">'
        f'<span class="wf-seglab">short {_money(shortfall)}</span></span></div>'
        f'<div class="wf-stages">{"".join(stage_rows)}</div>'
        f'<div class="wf-result {result_cls}">'
        f'planned cash {_money(total_cash)} vs safe portfolio target {_money(recovery_target)} = '
        f'<strong>{_money(total_cash - recovery_target)}</strong></div>'
        "</div>"
    )


def _selldown(strategy: BettingStrategy) -> str:
    active = [item for item in strategy.live_scores if item.position_active]
    if not active:
        return ""
    cards = "".join(_selldown_card(item) for item in active)
    legend = (
        '<div class="cmap-legend">'
        '<span><span class="sw" style="background:var(--home)"></span>'
        "blue = covering next-goal invalidated positions</span>"
        '<span><span class="sw" style="background:var(--away)"></span>'
        "red = cash above the safe target</span>"
        '<span><span class="sw" style="background:var(--bar)"></span>'
        "grey = unrecovered shortfall</span>"
        '<span><span class="safe-star">★ $</span> first stage where cumulative cash is safe</span>'
        "</div>"
        '<p class="foot">“Safe” is conservative: cash from selling this score must cover the larger '
        "of the two exact-score costs made impossible by the next home or away goal, plus the strategy "
        "safety margin. It assumes the displayed limit price fills with sufficient bid depth before "
        "another goal; it is not guaranteed.</p>"
    )
    return (
        '<h2>Position sell-down, step by step</h2>'
        f'<div class="card"><div class="wf-grid">{cards}</div>{legend}</div>'
    )


# ---------------------------------------------------------------------------
# 3. Major scoring paths & capital recovery — vertical score tree
# ---------------------------------------------------------------------------

def _pl_class(profit: Decimal) -> str:
    if profit > 0:
        return "profit"
    if profit < 0:
        return "loss"
    return ""


def _node_fill(profit: Decimal, reference: Decimal) -> str:
    """Blue (profit) / red (loss) intensity scales with |P/L| vs the largest swing."""
    if profit == 0 or reference == 0:
        return "background:var(--card);"
    hue = "var(--home)" if profit > 0 else "var(--away)"
    depth = float(min(Decimal(1), abs(profit) / reference))
    pct = 12 + depth * 46
    return f"background:color-mix(in srgb,{hue} {pct:.0f}%,var(--card));"


def _tree_node(row: PathLedgerRow, reference: Decimal, bankroll: Decimal) -> str:
    marks = "".join(
        f'<span class="{"hit" if hit else ""}" title="+{label} ({_pct_of(amount, bankroll)} of X)"></span>'
        for hit, label, amount in (
            (row.fixed_profit_025, "$0.25", Decimal("0.25")),
            (row.fixed_profit_050, "$0.50", Decimal("0.50")),
            (row.fixed_profit_100, "$1.00", Decimal("1.00")),
        )
    )
    recovered = "full bankroll recovered" if row.full_bankroll_recovered else (
        "position recovered" if row.active_positions_recovered else ""
    )
    signed_pct = _pct_of(row.realized_profit, bankroll)
    if row.realized_profit > 0 and signed_pct != "—":
        signed_pct = "+" + signed_pct
    title = (
        f"net P/L {_money0(row.realized_profit)} ({signed_pct} of X); "
        f"cumulative cash {_money0(row.cumulative_cash)}, active costs {_money0(row.active_position_costs)}"
        + (f" — {recovered}" if recovered else "")
    )
    return (
        f'<div class="ptree-node {_pl_class(row.realized_profit)}" '
        f'style="{_node_fill(row.realized_profit, reference)}" title="{escape(title, quote=True)}">'
        f'<div class="sc">{escape(row.score)}</div>'
        f'<div class="pl">{signed_pct}</div>'
        f'<div class="marks">{marks}</div></div>'
    )


def _paths(strategy: BettingStrategy) -> str:
    if not strategy.path_ledger:
        return ""
    branches: dict[str, list[PathLedgerRow]] = {}
    for row in strategy.path_ledger:
        branches.setdefault(row.path, []).append(row)

    bankroll = strategy.request.bankroll
    reference = max(
        (abs(row.realized_profit) for row in strategy.path_ledger), default=Decimal(1)
    ) or Decimal(1)
    root_row = next(iter(branches.values()))[0] if branches else None
    branch_html: list[str] = []
    for path, rows in branches.items():
        steps = rows[1:] if len(rows) > 1 else rows
        chain = '<div class="ptree-stem"></div>'.join(_tree_node(row, reference, bankroll) for row in steps)
        label = escape(path.split(" → ", 1)[-1] if " → " in path else path)
        branch_html.append(
            f'<div class="ptree-branch"><div class="ptree-branch-label">{label}</div>{chain}</div>'
        )

    root_html = (
        f'<div class="ptree-root">{_tree_node(root_row, reference, bankroll)}'
        '<div class="ptree-stem"></div></div>'
        if root_row is not None
        else ""
    )
    tree = (
        f'<div class="ptree">{root_html}'
        f'<div class="ptree-branches">{"".join(branch_html)}</div></div>'
    )
    legend = (
        '<div class="cmap-legend">'
        '<span><span class="sw" style="background:var(--home)"></span>'
        "blue = net profit (% of X) — deeper = bigger swing</span>"
        '<span><span class="sw" style="background:var(--away)"></span>'
        "red = net loss — deeper = bigger swing</span>"
        '<span><span class="sw" style="background:var(--home)"></span>'
        "dot lit = fixed-profit milestone reached</span>"
        "</div>"
    )
    table_rows = [
        (
            item.path, item.score, _pct_of(item.realized_profit, bankroll), _money(item.realized_profit),
            _money(item.stage_cash), _money(item.cumulative_cash), _money(item.active_position_costs),
            "yes" if item.individual_recovered else "no",
            "yes" if item.active_positions_recovered else "no",
            "yes" if item.full_bankroll_recovered else "no",
            "/".join("yes" if value else "no" for value in (
                item.fixed_profit_025, item.fixed_profit_050, item.fixed_profit_100
            )),
        )
        for item in strategy.path_ledger
    ]
    table = _table(
        (
            "Path", "Score", "P/L % of X", "P/L $", "Stage cash", "Cumulative", "Active costs", "Position",
            "Active", "Full bankroll", "+.25/+.50/+1",
        ),
        table_rows,
    )
    note = (
        f'<p class="foot">All four paths share the opening 0-0, with X = {_money(bankroll)}. Reading down a '
        "branch replays one plausible sequence of goals; the number in each node is net profit/loss at that "
        "point as a percent of X after any staged exits fill, and the three dots mark whether the $0.25 / $0.50 "
        "/ $1.00 fixed-profit milestones have been hit.</p>"
    )
    return (
        "<h2>Major scoring paths &amp; capital recovery</h2>"
        f'<div class="card">{tree}{legend}{note}'
        f'{_details("Show full path ledger table", table)}</div>'
    )


# ---------------------------------------------------------------------------
# 4. Conservative, balanced & aggressive plans — side-by-side plan cards
# ---------------------------------------------------------------------------

def _preset_card(preset: PresetSummary) -> str:
    # X is the true bankroll = deployed + uninvested cash, so deployed% + cash%
    # sum to 100. (reserve is a minimum-cash floor, not the actual split.) One
    # accent hue per deployed slice; the list and tooltips name each selection.
    total = preset.deployed + preset.uninvested_cash or Decimal(1)
    deployed_pct = float(preset.deployed / total * 100)
    segments: list[str] = []
    for position in preset.allocations:
        share = float(position.amount / total * 100)
        segments.append(
            f'<span style="width:{share:.1f}%;background:var(--accent)" '
            f'title="{escape(position.evaluation.quote.selection, quote=True)}: '
            f'{_pct_of(position.amount, total)} of X ({_money0(position.amount)})">'
            f"{escape(position.evaluation.quote.selection)}</span>"
        )
    cash_pct = max(0.0, 100.0 - deployed_pct)
    segments.append(f'<span class="cash" style="width:{cash_pct:.1f}%">cash {cash_pct:.0f}%</span>')
    positions_html = "".join(
        f'<li><span class="nm">{escape(position.evaluation.quote.selection)}</span>'
        f'<span class="amt"><b>{_pct_of(position.amount, total)}</b> '
        f'<span class="sub3">{_money0(position.amount)} / {position.contracts}c</span></span></li>'
        for position in preset.allocations
    ) or '<li><span class="nm">none — retain cash</span></li>'
    exits = " / ".join(f"{fraction:.0%}" for fraction in preset.exit_fractions)
    return (
        f'<div class="plan-card"><h4>{escape(preset.name)}</h4>'
        f'<p class="sub2">min. reserve {_pct_of(preset.reserve, total)} of X · exits {exits}</p>'
        f'<div class="plan-bar">{"".join(segments)}</div>'
        '<div class="plan-stats">'
        f'<div>Deployed<b>{_pct_of(preset.deployed, total)}</b></div>'
        f'<div>Cash<b>{_pct_of(preset.uninvested_cash, total)}</b></div>'
        f'<div>Max loss<b>{_pct_of(preset.maximum_loss, total)}</b></div>'
        f'<div>Positions<b>{len(preset.allocations)}</b></div>'
        "</div>"
        f'<ul class="plan-positions">{positions_html}</ul></div>'
    )


def _presets(strategy: BettingStrategy) -> str:
    if not strategy.presets:
        return ""
    cards = "".join(_preset_card(preset) for preset in strategy.presets)
    table_rows: list[tuple[str, ...]] = []
    for item in strategy.presets:
        whole = item.deployed + item.uninvested_cash or Decimal(1)
        allocations = "; ".join(
            f"{position.evaluation.quote.selection}: {_pct_of(position.amount, whole)} "
            f"({_money(position.amount)} / {position.contracts})"
            for position in item.allocations
        ) or "none — retain cash"
        table_rows.append(
            (item.name, _pct_of(item.deployed, whole), _pct_of(item.uninvested_cash, whole),
             _pct_of(item.maximum_loss, whole), _money(item.reserve), _money(item.deployed),
             _money(item.uninvested_cash), "/".join(f"{value:.0%}" for value in item.exit_fractions), allocations)
        )
    table = _table(
        ("Plan", "Deployed %X", "Cash %X", "Max loss %X", "Reserve $", "Deployed $", "Cash $",
         "Exit percentages", "Allocations"),
        table_rows,
    )
    return (
        "<h2>Conservative, balanced &amp; aggressive plans</h2>"
        f'<div class="card"><div class="plan-grid">{cards}</div>'
        f'{_details("Show full plan comparison table", table)}</div>'
    )


def strategy_section(strategy: BettingStrategy | None) -> str:
    """Return the full optional strategy section."""
    if strategy is None:
        return ""
    warnings = "".join(f"<li>{escape(value)}</li>" for value in strategy.warnings)
    rule = (
        '<h2>Execution rule &amp; risk limits</h2><div class="card"><ul>' + warnings +
        "<li>Buy only at or below the maximum reported buy price; sell only against an executable bid "
        "at or above the staged limit.</li><li>Stage cash is conditional on a full fill; current bid and depth "
        "determine the ‘now’ flag.</li><li>Unfilled orders are not recovered cash. Refresh after every goal.</li>"
        "</ul></div>"
    )
    return _allocations(strategy) + _live(strategy) + _paths(strategy) + _presets(strategy) + rule
