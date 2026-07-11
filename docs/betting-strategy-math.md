# Betting strategy calculation contract

This document defines the deterministic baseline used by the optional betting
strategy report. It is an analysis aid, not an order-execution system or a
guarantee of profit.

## Prices and value

For one $1-settled contract with model probability `p`, executable ask `a`, buy
fee rate `fb`, and configured per-contract slippage `s`:

- raw fair value = `p`
- raw edge = `p - a`
- all-in buy cost = `a + a*fb + s`
- conservative probability `pc` = the relevant 1X2 interval lower bound when
  available; otherwise `max(0, p - safety_margin)`
- net edge = `pc - all-in buy cost`
- maximum limit buy = `max(0, pc - a*fb - s)`, rounded down to the venue tick

A contract is eligible only when net edge is strictly positive and the quote
has enough ask-side size for at least one declared quantity step. Missing
prices are never replaced by a midpoint or last trade.

Sell proceeds for quantity `q`, executable bid or limit target `b`, and sell fee
rate `fs` are `q*b*(1-fs)`. A planned limit sale is not realized cash until it
fills. Each exit stage carries the snapshot's current bid and bid depth plus an
`executable_now` flag; projected cash is explicitly conditional on a full fill
at the target. Price, money, fees, and quantities use `Decimal` arithmetic.

## Allocation

Eligible contracts are ordered by net edge, then canonical market key. The
allocator greedily purchases the largest permitted quantity at each step while
respecting all constraints:

- total all-in spend <= bankroll minus the preset cash reserve;
- one exact score <= 30% of bankroll;
- all exact scores together <= 60% of bankroll;
- quantity <= quoted ask-side depth and is a multiple of `quantity_step`;
- no leverage and no forced deployment.

Rounding residue remains cash. Gross settlement payout is quantity because each
winning contract pays $1. Maximum loss is all-in purchase cost. Net winning
profit is gross payout minus all-in purchase cost.

## Live exact-score value

For a current score at minute `t`, the contract settles at $1 only if no further
goals occur. The baseline uses the forecast score grid's expected home and away
goals, scaled by remaining regulation time and explicit live multipliers:

`lambda_remaining = (lambda_home*home_multiplier + lambda_away*away_multiplier) * max(0, 90-t)/90`

`current_score_fair = exp(-lambda_remaining)`

Team-rate multipliers are bounded to `[0.25, 3.0]`; context multipliers to
`[0.50, 1.50]`. Each red card multiplies that team's rate by 0.85 and its
opponent's by 1.10. When explicitly enabled, a leading/defending team's rate is
multiplied by 0.90 and a trailing/pressing team's rate by 1.10. Injury,
substitution, and pressure multipliers apply to total tempo. None of these
effects is inferred: callers supply them, along with added time, and reports
show every override.
With fixed rates and an unchanged score, fair value must not decrease as time
passes.

Exit targets occur at minutes 55, 70, and 82 (plus declared added time for the
last window). Each target is `fair - safety_margin/2`, clamped to `[tick, 0.99]`
and rounded down to tick. Conservative, balanced, and aggressive sell fractions
are 60/30/10, 40/35/25, and 20/30/50 percent. Integer/step rounding assigns the
remainder to the final stage.

## Recovery ledgers

Reports distinguish:

1. individual position recovery: realized proceeds >= that position's cost;
2. active-position recovery: cumulative proceeds >= costs of score positions
   that have become active on the path;
3. complete-bankroll recovery: cumulative proceeds >= original bankroll.

For each non-final path state, only the first planned exit is assumed to fill;
the next goal invalidates the remaining current-score contracts. At the final
path state, all three planned stages are assumed to fill. Reports test whether
realized profit above active-position costs reaches $0.25, $0.50, and $1.00.
No state is described as risk-free unless complete-bankroll worst-case loss is
exactly zero after costs.

## Invariants

- All probabilities and prices remain in `[0,1]`.
- Allocated spend never exceeds bankroll or the preset deployment limit.
- Exact-score concentration limits always hold.
- Contract counts never exceed quote depth and respect quantity steps.
- Cash plus spend reconciles to bankroll at cent precision.
- Realized cash never includes an unfilled order.
- A goal invalidates the unsold balance of the previous exact-score contract.
- Fixed-rate current-score value is monotonic with elapsed time.
