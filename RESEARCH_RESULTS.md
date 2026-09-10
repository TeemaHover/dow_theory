# What actually has an edge, and what does not

Local research run, 10 September 2026. Everything below comes from a backtest
engine written from scratch in `research/`, run on data downloaded to `data/`.
No TradingView numbers are used, because the TradingView strategy build had a
position-sizing defect that made its currency results meaningless.

## How the engine keeps itself honest

- A signal on bar *i* fills at the **open of bar i+1**. Never on the signal bar.
- When one bar's range contains both the stop and the target, the **stop is taken**.
  From bar data alone the order inside the bar is unknowable, so it resolves against us.
- Spread is charged **on entry and on exit**, per instrument.
- Every result is in **R multiples** — profit divided by the initial risk — so nothing
  depends on position sizing. This is what the TradingView build got wrong.
- Swing structure is stamped at the bar that **confirmed** a pivot, not the bar that
  made it, so no result uses information that did not exist at the time.
- Data is split at a fixed date. Parameters were chosen on **train** and the test
  slice was looked at afterwards.

## Part 1 — why the Dow-structure indicator loses

The decisive measurement is the zero-cost control. Same entries, transaction costs
removed:

| entry set | win rate | coin-flip rate | profit factor |
|---|---|---|---|
| liquidity sweep, real spread | 33.0% | 33.3% | 0.885 |
| **liquidity sweep, zero cost** | **33.1%** | **33.3%** | **1.006** |

With costs removed it sits on exactly break-even. The entries contain **no
directional information**. The win rate tracks a driftless random walk at every
target level:

| target | random walk predicts | measured |
|---|---|---|
| 1R | 50.0% | 49.5% |
| 2R | 33.3% | 34.0% |
| 3R | 25.0% | 27.0% |
| 4R | 20.0% | 22.1% |

Six entry hypotheses were tested across roughly 60,000 pooled trades on 17
instruments — break of structure, trend pullback, liquidity sweep, moving-average
pullback, mean reversion, session opening range. **All six landed within ±2
percentage points of chance.** Losses equal the spread, near enough.

Every filter in the original indicator was neutral or harmful. Removing all of
them — MTF alignment, structure state, extension cap, risk bounds — raised train
profit factor from 1.056 to 1.200. The MTF machinery in particular was worth
about 0.03R per trade, which is noise.

This is not a tuning problem. There is nothing to tune.

## Part 2 — what does work

Daily breakout momentum held on an ATR trailing stop. Tested by asset class,
which is a single hypothesis per class rather than instrument-picking:

| class | instruments | train PF | test PF |
|---|---|---|---|
| metals | 5 | 1.481 | **2.206** |
| energy | 4 | 1.533 | 1.058 |
| rates | 2 | 1.282 | 1.018 |
| equity indices | 7 | 1.042 | 1.256 |
| agriculturals | 7 | 1.023 | 1.189 |
| **FX majors** | 8 | **0.892** | **0.889** |
| **FX crosses** | 19 | **0.819** | **0.565** |

The commodity/FX split holds in both halves of the data and matches the published
finding that time-series momentum is strong in commodities and index futures and
absent in developed-market currency crosses. **Do not run this on FX pairs.**

### The configuration

Daily bars. Long when the close exceeds the highest high of the prior 8 bars and
sits above the 100-EMA; short on the mirror. Initial stop 2.0 × ATR(14). Exit on a
trailing stop of 2.5 × ATR(14) that ratchets and never loosens. No fixed target.
Universe: 25 commodities, equity indices and rates.

| slice | trades | win rate | profit factor | expectancy | trades/month |
|---|---|---|---|---|---|
| all, 2016–2026 | 2,484 | 36.2% | 1.237 | +0.112R | 20.8 |
| train, to Sep 2023 | 1,723 | 36.2% | 1.171 | +0.080R | 20.8 |
| **test, Sep 2023 on** | **761** | **36.3%** | **1.384** | **+0.183R** | **21.0** |

Test is better than train, which is the opposite of an overfitting signature.

**Consistency**: 9 of 11 years positive (2021 −28.7R and 2023 −2.8R were the
losers). Total +277.6R; **excluding the two best years, still +98.7R**. 18 of 25
instruments positive. Gold on its own: profit factor 1.818.

**Parameter stability**: every combination of lookback ∈ {8,10,12,15,20} and trail
∈ {2.5,3.0,3.5} produced train PF between 1.167 and 1.257 and test PF between 1.21
and 1.41. A flat surface, not a spike. It also survives 3× the assumed spread.

## Part 3 — why the win rate cannot be high

Same entries, fixed targets instead of the trailing exit:

| fixed target | win rate | profit factor |
|---|---|---|
| 0.5R | **64.2%** | 1.001 |
| 1.0R | 50.6% | 1.040 |
| 1.5R | 41.4% | 1.046 |
| 2.0R | 35.3% | 1.092 |
| 3.0R | 28.8% | 1.145 |

A 64% win rate is available and it is worth nothing — profit factor 1.001. Win
rate and payoff trade off against each other along one line, and only genuine edge
moves the whole line. Chasing win rate is how the previous indicator ended up
with twelve entry types and no edge. The trailing exit beats every fixed target
here (1.237) precisely because it lets a winner run past 3R.

## What to expect if you trade it

- About 21 trades a month **across the whole 25-instrument basket** — under one per
  month on any single chart. The frequency and the smoothness both come from the
  basket. Running it on gold alone is a different, much lumpier proposition.
- Roughly 36% winners. Long strings of small losses are normal.
- Worst observed drawdown 72R. At 1% risk per trade that is a 72% account
  drawdown, so position sizing needs to be far smaller than 1% — or the basket
  needs to be traded with correlation-aware sizing.
- 2021 was a losing year. So was 2023. That is the shape of this strategy.

## Files

- `TrendCore_Daily.pine` — the strategy above, for TradingView.
- `research/` — data layer, structure detection, backtest engine, diagnostics.
- `data/` — downloaded OHLC (not committed).
- `research/trades_final.csv` — every trade behind the headline table.
