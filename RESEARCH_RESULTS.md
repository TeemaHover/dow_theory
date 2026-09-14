# What actually has an edge, and what does not

Local research, September 2026. Everything below comes from the backtest engine in
`research/`, run on data downloaded with `research/qdownload.py`, except where spot
gold is read directly from TradingView's own OANDA data. The TradingView strategy
build is not used: it had a position-sizing defect.

> **Correction, 14 September 2026 — read Part 6 before any number in Parts 2–5.**
> Those parts filled a stop at the stop price even when a day opened beyond it, and
> 47 trades that opened beyond their own stop were counted as profitable stop-outs.
> With realistic fills the basket figures in Parts 2, 4 and 5 are withdrawn. Spot gold
> still measures positive in every period tested; the basket does not.

## The current system (14 September 2026)

`TrendCore_Daily.pine` — daily breakout momentum on a trailing stop, plus the two
parts of classical Dow Theory that measured positive: the **primary trend** and
**Industrials + Transports confirmation** for US index charts. Entry Type can be
switched between Breakout (default), Retest, Breakout + Retest (Part 7) and
Breakout + Pullback (Part 9).

What is established, with realistic fills (Part 6), 6R take-profit, on spot gold
read from TradingView:

| period | trades | profit factor | per trade | total |
|---|---|---|---|---|
| 1975–1999 | 205 | 1.33 | +0.19R | +38R |
| 2000–2015 | 142 | 1.24 | +0.12R | +16R |
| 2016–2026 | 96 | 1.45 | +0.23R | +22R |

What is **not** established: the multi-market basket. The figures first published
here for 42 markets (PF 1.255, 27.8 trades a month) assumed stops filled at the stop
price through gaps and are withdrawn. With realistic fills the basket measured about
break-even, but its futures data has roll jumps that exaggerate gaps, so the real
figure needs a re-test on roll-adjusted data. Cash stock indices, which have no rolls,
measured PF 1.25 in 2000–15 and 0.95 in 2016–26.

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

## Part 5 — adding a take-profit

Same 42 markets and Dow version. Selection rule fixed before running: among the
take-profit styles, keep the one with the best 2000–15 expectancy.

| exit style | PF 2000–15 | PF 2016–26 | win rate | TP reached |
|---|---|---|---|---|
| **trailing stop only** | **1.313** | **1.177** | 37% | — |
| full exit at 6R (selected) | 1.265 | 1.147 | 37% | ~3% |
| full exit at 4R | 1.233 | 1.120 | 37% | ~8% |
| full exit at 3R | 1.174 | 1.082 | 37% | ~13% |
| full exit at 2R | 1.112 | 1.068 | 37% | ~24% |
| half at 3R, trail the rest | 1.255 | 1.131 | 37% | ~13% |
| half at 2R, trail the rest | 1.207 | 1.119 | 37% | ~24% |
| half at 1R, trail the rest | 1.159 | 1.106 | **46%** | ~46% |
| half at 1R, then stop to entry | 1.161 | 1.096 | 47% | ~46% |

Every take-profit costs profit factor in both eras, and the closer the target the
more it costs, because the edge lives in the rare very large winner. The indicator
now draws a stop-loss and a take-profit on every trade, defaulting to a full exit
at 6R, the least costly option; "Off (trail only)" restores the best measured result,
and "half at 1R" is there for anyone who prefers a 46% win rate at a lower profit
factor. Moving the stop to entry after the first half made no difference.

## Part 6 — realistic fills (correction)

Found while verifying the TradingView indicator bar by bar (0 mismatches against an
independent replay on 15-minute and daily gold, and on the S&P 500 with the real
Industrials + Transports check). The indicator is correct; the backtest was not:

- a stop was filled at the stop price even when the bar **opened** beyond it;
- a trade whose entry opened beyond its own stop was counted as stopped out at a profit
  (47 trades).

`qbt.run(..., gap_fills=True)` now fills such stops at the open. Same system, trailing
stop plus the indicator's 6R take-profit, PF 2000–15 / 2016–26:

| data | published fills | realistic fills |
|---|---|---|
| 42-market basket (Yahoo continuous futures) | 1.265 / 1.147 | 1.036 / 0.992 |
| cash stock indices, trail only, whole period | 1.149 | 1.095 |

The futures number overstates the damage: Yahoo's continuous futures are not
roll-adjusted, so contract rolls look like gaps. Gold futures showed a gapped stop on
38% of exits; OANDA spot gold on none since 2005. So the true basket figure is
unknown until it is re-tested on roll-adjusted data. Spot gold, read from TradingView
(3 bps costs, realistic fills, same-bar re-entry as the indicator, 6R take-profit):

| period | trades | PF | per trade | total |
|---|---|---|---|---|
| 1975–1999 | 205 | 1.33 | +0.19R | +38R |
| 2000–2015 | 142 | 1.24 | +0.12R | +16R |
| 2016–2026 | 96 | 1.45 | +0.23R | +22R |

Scripts: `research/qfidelity.py`, `research/qgaps.py`.

## Part 7 — retest entries

Rule fixed before testing. A normal Trend Core breakout arms a retest at the broken
level. Within W bars, a bar that comes back within tol × ATR of the level and closes on
the breakout side of it, filters still passing, is the entry; a close back through the
level cancels it. Stop either 2 × ATR from entry or 1 × ATR beyond the level. Variants:
W ∈ {5, 10}, tol ∈ {0.25, 0.5}, both stops, and "retest only" versus "breakout +
retest". Adoption rule: beat the breakout on both expectancy and total R in both eras
on clean data. All tests use realistic fills and the 6R take-profit.

**Do breakouts retest?** Yes, usually. Within 10 bars:

| data | retested and held | closed back through | never returned | new breakout first |
|---|---|---|---|---|
| spot gold, daily 1975–2026 | 49% | 26% | 0.8% | 24% |
| cash stock indices, daily | 55% | 27% | 0.1% | 17% |
| futures basket, daily | 52% | 27% | 0.4% | 21% |
| spot gold, 15-minute, Jun–Sep 2026 | 60% | 30% | 1.5% | 9% |

**Does entering on the retest help?** No variant passed, on any data set.

| entry | gold 1975–99 | gold 2000–15 | gold 2016–26 |
|---|---|---|---|
| breakout (default) | 1.33 / +38R | **1.24 / +16R** | 1.45 / +22R |
| retest W10 tol 0.5, 2 × ATR stop | 1.50 / +39R | 1.18 / +10R | 1.49 / +20R |
| retest W5 tol 0.5, stop beyond level | 1.62 / +59R | 1.03 / +2R | 1.38 / +19R |
| breakout + retest | ≈ 1.32 / +37R | ≈ 1.24 / +16R | 1.42 / +21R |

Retest-only is often better per trade but misses the trends that never pull back,
which are the biggest ones: gold 2000–15 shows it most sharply. On cash indices the
best retest variants raised 2000–15 expectancy but lowered total R (9.0 against
9.5 R a year) and deepened drawdown; on the basket, retest-only was clearly worse in
2016–26. "Breakout + retest" behaves like the breakout, because the breakout almost
always takes the trade first. On 15-minute gold (3½ months) the differences were
within noise.

The indicator therefore keeps Breakout as the default and offers Retest and
Breakout + Retest as options, with a purple line at the level being waited on. The
Pine version was checked against an independent replay in all five configurations:
0 mismatches in 25,916 values each, and identical to the previous version in
Breakout mode. Script: `research/qretest.py`.

Also found: on clean cash stock indices with realistic fills, the breakout system
itself lost money in 2016–26 (PF 0.95).

## Part 8 — trading failed breakouts the other way

Rule fixed before testing. Within W bars of a Trend Core breakout, a close back through
the broken level by more than tol × ATR is a failure, and it signals a position
opposite to the breakout at the next open. "Fade" trades only the failures (when flat);
"reverse" trades breakouts as usual and flips the position on a failure. Stops: 2 × ATR
from the signal close, or beyond the failed breakout's extreme plus 0.25 ATR. Same
trailing stop, 6R take-profit and realistic fills. W ∈ {5, 10}, tol ∈ {0, 0.5}, plus
opposite-trend-filter and 2R-target checks. The simulator reproduces the existing
engine exactly in breakout mode (1,328 trades at PF 1.245 and 1,038 at 0.953 on the
clean indices). Adoption: fade needs PF above 1 in both eras; reverse must beat the
breakout on expectancy and total R in both eras.

| data | breakout | fade (8 variants) | reverse (8 variants) |
|---|---|---|---|
| spot gold 1975–99 | 1.33 / +38R | 0.63–0.89 | 0.83–1.07 |
| spot gold 2000–15 | 1.24 / +16R | 0.45–0.62 | 0.70–0.81 |
| spot gold 2016–26 | 1.45 / +22R | 0.85–1.19 | 0.95–1.24 |
| cash indices 2000–15 | 1.245 | 0.84–0.96 | 0.92–1.03 |
| cash indices 2016–26 | 0.953 | 1.04–1.11 | 1.02–1.08 |
| futures basket 2000–15 | 1.036 | 0.89–0.95 | 0.91–1.00 |
| futures basket 2016–26 | 0.992 | 0.95–0.99 | 0.97–0.99 |

Nothing passed. On gold and the basket a failed breakout is usually a pullback inside
the trend rather than a reversal, so trading against it loses. On stock indices the
failures paid only in 2016–26, the same decade the breakout stopped working there — a
mirror image of the trend system, not a separate edge. With the opposite trend filter
almost no failures qualify (17 on gold in 51 years) and the result is the breakout
system. On 15-minute gold over Jun–Sep 2026 fading looked positive (PF 1.25), which the
long daily history contradicts. Script: `research/qfail.py`. Not added to the indicator.

## Part 9 — failed breakouts as pullbacks: re-entering with the trend

If a failure is usually a pullback, the useful question is whether to re-enter in the
original direction when it ends. Rule fixed before testing: after a failure, watch for
up to W2 bars; cancel as a reversal if the close goes more than 2 × ATR beyond the level
or the trend filters stop passing; enter in the breakout direction on "reclaim" (a
close back beyond the level) or "turn" (a close beyond the previous bar's high, or low
for shorts). Stops: 2 × ATR, or beyond the pullback's extreme. Modes: pullback-only,
breakout + pullback (whichever comes while flat), and exit-on-failure-then-re-enter.
W2 ∈ {10, 20}. The simulator reproduces the existing engine exactly in breakout mode.

**What happens after a failure** (within 10 bars):

| data | resumed: level reclaimed | reversed: > 2 ATR beyond | reversed: trend filter broke | sideways |
|---|---|---|---|---|
| spot gold, daily | 59% | 22% | 13% | 5% |
| cash stock indices | 59% | 25% | 14% | 2% |
| futures basket | 55% | 26% | 15% | 3% |
| spot gold, 15-minute | 59% | 19% | 18% | 4% |

**Breakout + pullback (reclaim, 2 × ATR stop)** against the breakout, PF and total R:

| data | breakout | breakout + pullback |
|---|---|---|
| spot gold 1975–99 | 1.33 / +38R | **1.43 / +50R** |
| spot gold 2000–15 | 1.24 / +16R | **1.33 / +22R** |
| spot gold 2016–26 | 1.45 / +22R | **1.49 / +24R** |
| futures basket 2000–15 | 1.036 / +6.6 R/yr | **1.041 / +7.7 R/yr** (428 pullback trades, +0.11R) |
| futures basket 2016–26 | 0.992 / −1.6 R/yr | **1.009 / +1.8 R/yr** (272 pullback trades, +0.15R) |
| cash indices 2000–15 | 1.245 / +9.5 R/yr, +0.1141R | 1.246 / +9.6 R/yr, +0.1140R |
| cash indices 2016–26 | 0.953 / −2.3 R/yr | 0.948 / −2.6 R/yr (71 pullback trades, −0.16R) |

Better on gold in every period and on the basket in both, a tie on stock indices — which
misses the pre-set rule by a hair on the clean set, so Breakout stays the default and
Breakout + Pullback is an option. It is robust to the window (10 or 20 bars) and the stop
(2 × ATR or swing). It adds few trades on gold (31 in 51 years), because the pullback
entry only fires once the breakout trade has already been stopped out. Pullback-only
entries were better per trade on gold but inconsistent elsewhere (cash indices 2016–26
PF 0.70–0.85); "turn" triggers were worse than "reclaim" outside gold; exiting on the
failure and re-entering lost everywhere (basket PF 0.90–0.96).

The indicator now detects failures in every mode — an orange marker at the level while it
watches, "FAILED - pullback?" when a breakout fails, then "RESUMED" or "REVERSAL", plus a
"Failed Breakout" alert — and can trade the re-entry with Entry Type "Breakout +
Pullback". The Pine version matched an independent replay with 0 mismatches in 32,100
values in each of Breakout, Breakout + Pullback, Retest and Breakout + Retest, and is
identical to the previous version in Breakout mode. Script: `research/qpull.py`.

## What to expect if you trade it

- On gold alone, about 9 trades a year on the daily chart. That falls far short of 20 a
  month; the basket that was meant to supply that frequency is not yet shown to be
  profitable.
- Roughly 36–43% winners depending on the decade. Long strings of small losses are normal.
- Worst drawdown on spot gold from 1975 to 2026 was about 35R (11R within 2016–26).
  At 0.25% risk per trade that is under 9% of the account.
- Losing years happen. Since 2016 on gold: 2016 (−2.1R), 2017 (−1.3R), 2021 (−5.3R),
  2023 (−1.2R), and 2026 so far (−0.5R); 2025 made +11R.
- The rules were only tested on daily bars. On 15-minute bars the indicator calculates
  correctly but nothing about its profitability there is known.

## Files

- `TrendCore_Daily.pine` — the system above, for TradingView.
- `research/qdownload.py` — downloads every market used here into `data/`.
- `research/qdow.py`, `qdow2.py`, `qdow3.py` — the Dow tests in Part 4, in order.
- `research/qtp.py` — the take-profit test in Part 5.
- `research/qfidelity.py`, `research/qgaps.py` — the fill correction in Part 6.
- `research/qretest.py` — the retest test in Part 7.
- `research/qfail.py` — the failed-breakout test in Part 8.
- `research/qpull.py` — the pullback re-entry test in Part 9.
- `research/` — data layer, structure detection, backtest engine, diagnostics.
- `data/` and the run outputs are not committed; the scripts regenerate them.
