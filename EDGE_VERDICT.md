# Is the edge real? — measurement record

Date: 2026-09-10. Build: `DowTheory_MTF_XAUUSD_STRATEGY.pine` (DOW-BT), OANDA data,
10K account, 0.005% commission, 2 ticks slippage, `process_orders_on_close = true`.

## 1. Currency results as the Strategy Tester reports them

| Symbol | TF | Period | Trades | Win rate | Profit factor | Net | Max DD |
|---|---|---|---|---|---|---|---|
| XAUUSD | 5M  | Aug 17 – Sep 10 2026   |  5 | 20.0% | 0.000 | -8.69%  | 10.71% |
| XAUUSD | 15M | Jun 1 – Sep 10 2026    | 15 | 20.0% | 1.181 | +1.36%  |  8.01% |
| XAUUSD | 1H  | Jan 2 2025 – Sep 10 2026 | 44 | 25.0% | 1.637 | +14.31% | 12.04% |
| XAUUSD | 4H  | Jan 3 2023 – Sep 10 2026 | 21 | 19.1% | 0.188 | -26.49% | 33.55% |
| EURUSD | 1H  | Jan 2 2025 – Sep 10 2026 | 61 | 18.0% | 3.942 | +11.56% |  2.68% |

The same logic on the same instrument inverts from PF 1.637 (1H) to PF 0.188 (4H)
to PF 0.000 (5M).

## 2. The currency numbers are inflated by a position-sizing defect

Position size in the trade list ranges from 0.28 units to 9,700 units, median 39.
Rows sharing an entry timestamp and entry price sum to one full-size position, i.e.
TradingView is listing *partial exits of one position* as separate trades. Cause:
`strategy.exit("x", stop = btStop, limit = btTgt)` is re-issued on every bar without
`qty`, which can emit several exit orders against the same entry.

Consequences:
- reported trade counts overstate the number of independent signals;
- reported win rate is depressed by near-zero fragment exits;
- currency profit factor is weighted by whichever fragments happened to be large.

Re-measuring each trade as a pure price move (equal weight, size-independent) gives
a materially lower profit factor than the currency figure in both samples:
1.637 -> 1.174 on gold, 3.942 -> 1.609 on EURUSD.

## 3. Equal-risk re-analysis of the two profitable samples

| | XAUUSD 1H | EURUSD 1H |
|---|---|---|
| Trades | 44 | 61 |
| Win rate | 25.0% | 19.7% |
| Total price movement captured | +6.14% | +5.69% |
| Gross gain / gross loss | 41.37% / 35.23% | 15.03% / 9.34% |
| Profit factor (equal weight) | 1.174 | 1.609 |
| Largest single winner | +9.84% | +9.82% |
| Top 3 winners as share of gross gain | 66.9% | 79.9% |
| **PF excluding the single best trade** | **0.895** | **0.558** |
| **PF excluding the top 3 trades** | **0.388** | **0.324** |

Both samples turn losing when one trade is removed.

Winner distributions:
- XAUUSD 1H: 9.84, 9.23, 8.62, 4.47, 2.74, 2.33 — a plausible trend-follower tail.
- EURUSD 1H: 9.82, 1.13, 1.05, 0.62, 0.55, 0.49 — one outlier, then a cliff.

Near-zero round trips (|move| < 0.01%): 5 of 44 on gold, 17 of 61 on EURUSD. These
account for under 1% of gross loss, so collapsing the fragments would not change the
top-trade dependency above.

## 4. Verdict

The edge is **not demonstrated**. Not disproven either — the samples are too small
for that — but nothing here establishes one.

Reasons, in order of weight:
1. Results invert across timeframes on the same instrument and the same code.
2. Every positive result collapses below break-even when its best trade is removed.
3. Sample sizes (44 and 61 trades) put the 95% interval on win rate at roughly
   14–40%, wide enough to contain both a good system and a worthless one.
4. The backtest itself has a defect (partial-exit fragmentation and 34,000x variation
   in position size), so the currency figures were not measuring signal quality.

The earlier headline of profit factor 2.451 came from a single 18-trade window and
does not survive any of the above.

## 5. What would actually settle it

- Fix the exit so one signal produces one position (pass `qty_percent = 100` or guard
  the re-issue), then re-measure. Until then no currency figure from this build means
  anything.
- Size every trade at a fixed fraction of risk so profit factor reflects the signal.
- Require several hundred trades before drawing a conclusion — walk forward across
  2015–2026 on gold rather than the ~20 months TradingView loads at 1H.
- Test on instruments and periods never used while tuning, and accept the result.
