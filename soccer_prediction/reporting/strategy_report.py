"""Text and Markdown rendering for price-aware betting strategies."""

from __future__ import annotations

from decimal import Decimal

from soccer_prediction.models import Allocation, BettingStrategy

__all__ = ["strategy_markdown", "strategy_text"]


def _money(value: Decimal | None) -> str:
    return "—" if value is None else f"${value:.2f}"


def _probability(value: Decimal | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _allocation_map(strategy: BettingStrategy) -> dict[str, Allocation]:
    return {item.evaluation.quote.key: item for item in strategy.allocations}


def _allocation_rows(strategy: BettingStrategy) -> list[str]:
    allocations = _allocation_map(strategy)
    rows = [
        "### Betting value & bankroll allocation",
        "",
        f"Quote venue: **{strategy.venue}**; observed: `{strategy.quote_observed_at.isoformat()}`; "
        f"plan: **{strategy.request.plan}**; bankroll: **{_money(strategy.request.bankroll)}**.",
        "",
        "| Market / score | Model probability | Current ask | Fair price | Maximum buy | Estimated net edge | "
        "Allocated | Contracts | Maximum loss | Gross payout | Net profit if win | Reason | Intent |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in strategy.evaluations:
        position = allocations.get(item.quote.key)
        rows.append(
            f"| {item.quote.market}: {item.quote.selection} | {_probability(item.model_probability)} "
            f"| {_money(item.quote.ask)} | {_money(item.fair_price)} | {_money(item.max_buy_price)} "
            f"| {_money(item.net_edge)} "
            f"| {_money(position.amount if position else Decimal(0))} "
            f"| {position.contracts if position else Decimal(0)} "
            f"| {_money(position.maximum_loss if position else Decimal(0))} "
            f"| {_money(position.gross_payout if position else Decimal(0))} "
            f"| {_money(position.net_profit_if_win if position else Decimal(0))} "
            f"| {item.reason} | {item.intent} |"
        )
    deployed = strategy.request.bankroll - strategy.uninvested_cash
    rows.extend(
        [
            "",
            f"**Deployed:** {_money(deployed)} · **Uninvested:** {_money(strategy.uninvested_cash)} · "
            f"**Maximum loss:** {_money(sum((item.maximum_loss for item in strategy.allocations), Decimal(0)))}",
            "",
        ]
    )
    return rows


def _stage_cell(stage: object) -> str:
    from soccer_prediction.models import ExitStage

    assert isinstance(stage, ExitStage)
    return (
        f"m{stage.minute} ({stage.minute_range}), fair {_money(stage.fair_value)}, "
        f"bid {_money(stage.current_bid)} x {stage.bid_depth}, limit {_money(stage.target_price)}, "
        f"now {'yes' if stage.executable_now else 'no'}, "
        f"sell {stage.fraction:.0%} / {stage.contracts}, cash if filled {_money(stage.cash_received)}, "
        f"profit if filled {_money(stage.profit_locked)}"
    )


def _live_rows(strategy: BettingStrategy) -> list[str]:
    rows = [
        "### Live correct-score exit ladder",
        "",
        "| Score | Pre-match position active | First exit | Second exit | Final exit "
        "| If another goal arrives | Next scores |",
        "| --- | :-: | --- | --- | --- | --- | --- |",
    ]
    for item in strategy.live_scores:
        stages = item.stages
        rows.append(
            f"| {item.score} | {'yes' if item.position_active else 'no'} "
            f"| {_stage_cell(stages[0])} | {_stage_cell(stages[1])} | {_stage_cell(stages[2])} "
            f"| {item.goal_before_fill} | {item.next_home_score} or {item.next_away_score} |"
        )
    if strategy.live_scores:
        rows.extend(["", f"Assumptions: {strategy.live_scores[0].assumptions}", ""])
    return rows


def _path_rows(strategy: BettingStrategy) -> list[str]:
    rows = [
        "### Major scoring paths & capital recovery",
        "",
        "| Path | Score | Stage cash | Cumulative cash | Active-position costs | Realized P/L | "
        "Position recovered | Active costs recovered | Full $10 recovered | +$0.25 / +$0.50 / +$1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | :-: | :-: | :-: | :-: |",
    ]
    for item in strategy.path_ledger:
        fixed = "/".join("yes" if flag else "no" for flag in (
            item.fixed_profit_025, item.fixed_profit_050, item.fixed_profit_100
        ))
        rows.append(
            f"| {item.path} | {item.score} | {_money(item.stage_cash)} | {_money(item.cumulative_cash)} "
            f"| {_money(item.active_position_costs)} | {_money(item.realized_profit)} "
            f"| {'yes' if item.individual_recovered else 'no'} "
            f"| {'yes' if item.active_positions_recovered else 'no'} "
            f"| {'yes' if item.full_bankroll_recovered else 'no'} | {fixed} |"
        )
    return [*rows, ""]


def _preset_rows(strategy: BettingStrategy) -> list[str]:
    rows = [
        "### Conservative, balanced & aggressive plans",
        "",
        "| Plan | Minimum reserve | Deployed | Uninvested | Maximum loss | Exit percentages | Exact allocations |",
        "| --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for preset in strategy.presets:
        positions = "; ".join(
            f"{item.evaluation.quote.selection}: {_money(item.amount)} / {item.contracts} contracts"
            for item in preset.allocations
        ) or "none — keep bankroll in cash"
        exits = "/".join(f"{fraction:.0%}" for fraction in preset.exit_fractions)
        rows.append(
            f"| {preset.name} | {_money(preset.reserve)} | {_money(preset.deployed)} "
            f"| {_money(preset.uninvested_cash)} | {_money(preset.maximum_loss)} | {exits} | {positions} |"
        )
    return [*rows, ""]


def strategy_markdown(strategy: BettingStrategy) -> str:
    """Render all required strategy tables as Markdown."""
    warnings = ["### Execution rule & risk limits", ""]
    warnings.extend(f"- {warning}" for warning in strategy.warnings)
    warnings.extend(
        [
            "- Decision rule: buy only when the executable ask is at or below the reported maximum buy price; "
            "during the match, sell only against an executable bid at or above the staged limit.",
            "- Stage cash and profit are conditional on a full fill at the limit. The current bid/depth and "
            "‘now’ flag show whether it is executable from this snapshot.",
            "- A limit order that has not filled is not recovered cash. Refresh quotes and rebuild after every goal.",
            "",
        ]
    )
    return "\n".join(
        [*_allocation_rows(strategy), *_live_rows(strategy), *_path_rows(strategy), *_preset_rows(strategy), *warnings]
    )


def strategy_text(strategy: BettingStrategy) -> str:
    """Render a compact plain-text strategy summary."""
    deployed = strategy.request.bankroll - strategy.uninvested_cash
    lines = [
        "Betting strategy (price-aware)",
        f"Venue/quote time: {strategy.venue} / {strategy.quote_observed_at.isoformat()}",
        f"Plan: {strategy.request.plan}; bankroll {_money(strategy.request.bankroll)}; "
        f"deployed {_money(deployed)}; cash {_money(strategy.uninvested_cash)}",
    ]
    for item in strategy.allocations:
        lines.append(
            f"BUY {item.evaluation.quote.key}: {item.contracts} contracts, {_money(item.amount)}, "
            f"net edge {_money(item.evaluation.net_edge)}, max loss {_money(item.maximum_loss)}"
        )
    if not strategy.allocations:
        lines.append("NO BET: no quote clears the safety-adjusted value and risk constraints.")
    lines.extend(f"Warning: {warning}" for warning in strategy.warnings)
    return "\n".join(lines)
