# What actually has an edge, and what does not

Local research, September 2026. Everything below comes from the backtest engine in
`research/`, run on data downloaded with `research/qdownload.py`. No TradingView
numbers are used: the TradingView strategy build had a position-sizing defect that
made its currency results meaningless.

## The current system (11 September 2026)

`TrendCore_Daily.pine` — daily breakout momentum on a trailing stop, plus the two
parts of classical Dow Theory that measured positive: the **primary trend** and
**Industrials + Transports confirmation** for US index charts.

Measured 2000–2026 on 42 commodity, index and bond markets, with realistic costs on
every market and every entry filled at the next day's open:

| | trades | win rate | profit factor | expectancy | trades/month |
|---|---|---|---|---|---|
| 2000–2026 | 8,566 | 36.9% | 1.255 | +0.124R | 27.8 |
| 2000–2015 | — | 37.5% | 1.313 | +0.152R | 27.2 |
| 2016–2026 | — | 36.1% | 1.177 | +0.085R | 28.6 |

20 of 27 years positive. +1,058R in total, and still +769R with the two best years
removed. 33 of 42 markets positive. Worst drawdown across the basket about 76R.
Gold on its own: 228 trades, 40.8% winners, profit factor 1.856, worst drawdown 9.2R.

## How the engine keeps itself honest

- A signal on bar *i* fills at the **open of bar i+1**, never on the signal bar.
- When one bar's range holds both the stop and the target, the **stop is taken**.
- Costs are charged **on entry and on exit, on every market**, as basis points of
  price set at or above typical retail CFD spreads, so they stay realistic back to 2000.
- Results are in **R multiples**, so nothing depends on position sizing.
- Swing structure is stamped at the bar that **confirmed** a pivot, never the bar
  that made it, and another market's data is only ever used as of **yesterday**.
- Decision rules were written down before the tests they judge were run.

## Part 1 — why the Dow-structure indicator loses (hourly bars)

The decisive measurement is the zero-cost control. Same entries, costs removed:

| entry set | win rate | coin-flip rate | profit factor |
|---|---|---|---|
| liquidity sweep, real spread | 33.0% | 33.3% | 0.885 |
| **liquidity sweep, zero cost** | **33.1%** | **33.3%** | **1.006** |

With costs removed it sits on exactly break-even: the hourly entries contain no
directional information. The win rate tracks a driftless random walk at every
target level (1R: 49.5% vs 50.0%, 2R: 34.0% vs 33.3%, 3R: 27.0% vs 25.0%).

Six entry hypotheses across roughly 60,000 pooled trades on 17 instruments — break
of structure, trend pullback, liquidity sweep, moving-average pullback, mean
reversion, session opening range — all landed within ±2 percentage points of
chance. Every filter in the original indicator was neutral or harmful; removing all
of them raised train profit factor from 1.056 to 1.200.

## Part 2 — daily breakout momentum

Daily breakout momentum on an ATR trailing stop, tested by asset class:

| class | train PF | test PF |
|---|---|---|
| metals | 1.481 | 2.206 |
| energy | 1.533 | 1.058 |
| rates | 1.282 | 1.018 |
| equity indices | 1.042 | 1.256 |
| agriculturals | 1.023 | 1.189 |
| FX majors | 0.892 | 0.889 |
| FX crosses | 0.819 | 0.565 |

> **Correction.** The Part 2 numbers above, and the first Trend Core release, charged
> costs only on gold, silver and currencies — every other market traded free, and the
> "3× spread" check multiplied zero by three. With realistic costs on every market,
> Trend Core on the original 25 markets over 2016–2026 is PF **1.150**, not 1.237. It
> still survives doubled costs (PF 1.085). Part 4 uses the corrected costs throughout.

On sixteen years it had never seen (2000–2015), with corrected costs, the original
Trend Core scored PF 1.274 over 3,865 trades at 20.2 a month.

Currency pairs are excluded, but for the recent decade rather than forever: they
trended in 2000–2015 (PF 1.207) and have not since (PF 0.848 in 2016–2026).

## Part 3 — why the win rate cannot be high

Same entries, fixed targets instead of the trailing exit:

| fixed target | win rate | profit factor |
|---|---|---|
| 0.5R | **64.2%** | 1.001 |
| 1.0R | 50.6% | 1.040 |
| 1.5R | 41.4% | 1.046 |
| 2.0R | 35.3% | 1.092 |
| 3.0R | 28.8% | 1.145 |

A 64% win rate is available and worth nothing. Win rate and payoff trade along one
line; only genuine edge moves the line. The trailing exit beats every fixed target
because it lets a winner run past 3R.

## Part 4 — classical Dow Theory on daily bars

Every earlier Dow test was on hourly bars, so "Dow Theory does not work" was never
shown. Here each Dow element is tested on daily data from 2000.

**Rule, fixed before running:** an element is adopted only if, against Trend Core on
the same markets, it raises **both** expectancy **and** profit factor in **both**
2000–2015 and 2016–2026.

| test | 2000–15 PF | 2016–26 PF | trades/mo | outcome |
|---|---|---|---|---|
| baseline Trend Core, 25 markets | 1.274 | 1.150 | 20.2 / 20.7 | — |
| peaks & troughs, strict (3 ATR) | 1.280 | 1.097 | 9 | rejected |
| peaks & troughs, strict (2 ATR) | 1.246 | 1.148 | 9 | rejected |
| peaks & troughs, strict (5 ATR) | 1.391 | 1.234 | 8 | passes, not used — cuts trades by ~60% and total profit roughly in half |
| peaks & troughs, lenient | 1.300 | 1.185 | 16 | passes, not used — lower total profit in both eras |
| **exit only on a closing break** | 1.056 | **0.939** | 17 | **rejected** — 2016–26 drawdown 203R against 87R |
| **primary trend (250-day average)** | **1.301** | **1.209** | 17–18 | **adopted** |
| primary trend (weekly peaks & troughs) | 1.307 | 1.193 | 8 | passes, not used — cuts trades to a third |
| volume: breakout day above 20-day average | 1.139 | 1.139 | 15 | rejected |
| volume: breakout day above 1.25× average | 1.178 | 1.146 | 12 | rejected |
| volume: on-balance volume trend | 1.233 | 1.166 | 17 | rejected — worse in 2000–15 |
| **Industrials + Transports agree** (US index futures; base 0.933 / 1.040) | **1.477** | **1.769** | 0.8 | **adopted for US index charts** |
| same, trend by EMA instead of peaks & troughs | 0.991 | 1.101 | 2 | passes weakly; peak-and-trough version used |
| gold and silver confirm each other (base 1.547 / 1.492) | 1.658 | 1.475 | 1.5 | rejected — failed 2016–26 |
| classic Dow system on its own | 1.434 | 1.162 | 2.8 | works as a separate system; not merged |
| Dow entries with Trend Core's exit | 1.234 | 1.046 | 6 | rejected |

So Dow Theory is not dead on daily bars: the primary trend and Dow's own
two-average test both improve the system, and a pure classical Dow system is
profitable on its own. Dow's volume rule and his closing-price rule did not help,
and the closing-price exit did real damage.

**Keeping 20 trades a month.** Primary trend plus two-average confirmation dropped
the 25-market basket to about 16 trades a month, and shorter breakouts could not
restore 20 without giving back the gains. Instead the universe was widened by 17
markets from the same classes — Brent, soybean oil and meal, oats, rice, orange
juice, live and feeder cattle, lean hogs, KC wheat, Hang Seng, Euro Stoxx 50,
CAC 40, ASX 200, TSX, 5- and 2-year notes — **listed before any were tested, and
none dropped afterwards.**

| 42 markets | trades/mo | PF | expectancy | max drawdown |
|---|---|---|---|---|
| 2000–15, Dow version | 27.2 | **1.313** | 0.152R | 72.5R |
| 2000–15, baseline | 33.7 | 1.277 | 0.137R | 74.8R |
| 2016–26, Dow version | 28.6 | **1.177** | 0.085R | 67.1R |
| 2016–26, baseline | 35.4 | 1.130 | 0.064R | 73.8R |

Adopted: better in both eras on both measures, and above 20 trades a month in both.

### Limits worth knowing

- The Dow version trades less, so over the whole 27 years it makes about 10% less
  total R than the plain breakout (1,058R vs 1,171R). In 2016–2026 it makes more.
- Its drawdown advantage on the full basket is small: 76R against 77R over the whole
  period, 67R against 74R in 2016–2026. (On the original 25 markets it was large:
  49R against 87R in 2016–2026.)
- A first draft of these results understated every drawdown, because trades were
  not put in time order before it was measured. The figures here are corrected;
  profit factor, expectancy and win rate never depended on order.
- The two-average rule rests on about 120 and 85 trades in the two eras: a large
  effect on a small sample.
- Yahoo's continuous futures are not back-adjusted for contract rolls. That adds
  noise to every test equally, and its volume data has roll artefacts, which may
  understate what volume could do with cleaner data.
- The Pine version enters at the signal day's close; the backtest bought at the
  next open. The Pine version does not subtract costs.
- The Pine port of the peak-and-trough logic was checked against the tested Python:
  zero mismatches over about 26,000 daily bars on four markets. It compiles on
  TradingView, and `DJ:DJI` and `DJ:DJT` both resolve there.

## What to expect if you trade it

- About 28 trades a month **across all 42 markets** — under one a month on any single
  chart. The frequency and the smoothness both come from the basket.
- Roughly 37% winners. Long strings of small losses are normal.
- Worst drawdown about 76R, measured on closed trades in entry order; with many
  markets open at once the mark-to-market figure can differ. At 0.25% risk per trade
  that is about 19% of the account; at 1% it would be about three-quarters of it.
- Losing years happen: 7 of 27 lost money, the worst being 2009 (−43R), 2016 (−21R)
  and 2023 (−21R).

## Files

- `TrendCore_Daily.pine` — the system above, for TradingView.
- `research/qdownload.py` — downloads every market used here into `data/`.
- `research/qdow.py`, `qdow2.py`, `qdow3.py` — the Dow tests in Part 4, in order.
- `research/` — data layer, structure detection, backtest engine, diagnostics.
- `data/` and the run outputs are not committed; the scripts regenerate them.
