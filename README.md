# Dow Theory MTF Structure [XAUUSD] — Pine Script v6

Two files:

| File | Indicator name | What it is |
|---|---|---|
| `DowTheory_MTF_XAUUSD.pine` | Dow Theory MTF Structure | the base engine, sections 1 to 14 below |
| `DowTheory_MTF_XAUUSD_v2.pine` | Dow Theory MTF Structure + Liquidity | everything in the base file plus the liquidity map, counter-trend scalps and the corrected anti-chasing filter, section 15 below |

They have different names and short titles, so both can sit on the same chart while you compare them.

A low-noise, multi-timeframe Dow Theory market-structure indicator for discretionary Gold trading.
Primary engine: **Dow Theory swings + structure state machine + Break of Structure + multi-timeframe
confirmation + ATR noise filtering**. RSI / ADX / ATR / sessions are secondary filters only.

---

## 1. Architecture

The script is one file organised in the order the data flows:

| Section | What it does |
|---|---|
| 1. Inputs | Nine input groups: Structure, Noise Filter, Multi-Timeframe, Signals, Risk / Targets, Visualization, Filters, Sessions, Dashboard |
| 2. Utilities | Timeframe labels, state text/colours, session helper |
| 3–8. `f_engine()` | The whole structure engine: swing detection → Dow classification → state machine → BOS → reversal → sweeps. Pure calculation, no drawings, so the same function runs on the chart **and** inside `request.security()` |
| 9. Chart engine | `f_engine()` on the chart timeframe. Signals and drawings come from here |
| 10. MTF | Four `request.security()` calls (HTF / MTF / LTF / Entry) using `f_secEngine()` = engine values of the last **closed** bar of that timeframe |
| 11. Filters | RSI, ADX, ATR-compression, sessions, chop detection |
| 12. Bias | Combines the four timeframe states into one text (STRONG BULLISH, BULLISH — PULLBACK, MIXED / CONFLICT, REVERSAL DEVELOPING …) |
| 13. Score | 0–100 confidence score with seven components |
| 13b. Entries | Retest of a broken level, and the Dow pullback entry at a fresh HL / LH |
| 14. Signals | Gates + score → LONG / SHORT / REVERSAL / RETEST / PULLBACK |
| 14b. Trade levels | Stop loss, TP1/TP2/TP3, risk/reward zones, live R tracking, hit detection, stacked positions |
| 15. Visualization | Swing labels, structure lines, BOS lines, sweep / watch markers, signal labels, active levels, developing swing, chop shading |
| 16. Dashboard | One table, refreshed on the last bar only |
| 17. Alerts | Thirteen `alertcondition()` entries + dynamic `alert()` messages carrying score and levels |

Every timeframe runs the **same** engine with its own persistent state (`var` variables inside the function
are independent per call site), so the 4H, 1H, 15M and 5M rows are calculated identically.

---

## 2. How Dow Theory is detected

### Swings
1. `ta.pivothigh / ta.pivotlow` with `Swing Length` bars on each side. A pivot exists only after that many bars
   have **closed** after it. Nothing is assumed earlier.
2. **ATR significance filter** (`Use ATR Noise Filter`): a pivot becomes a *structural swing* only if it is at least
   `Minimum Swing Distance × ATR` away from the previous opposite swing. Shallow pivots are ignored.
3. **Alternation**: if two pivot highs arrive without a significant low between them, the higher one replaces the
   earlier one (same swing, refined). Same for lows. This is what keeps the chart from being covered in labels.

### Classification
Each new swing is compared with the previous same-side swing using `Minimum Structure Displacement × ATR`:

| Result | Label |
|---|---|
| higher than previous high + displacement | **HH** |
| lower than previous high − displacement | **LH** |
| inside the band | **EQH** (does not change structure) |
| higher than previous low + displacement | **HL** |
| lower than previous low − displacement | **LL** |
| inside the band | **EQL** |

### Structure state machine
States: `BULLISH (1)`, `BEARISH (-1)`, `NEUTRAL (0)`, `REVERSAL_BULLISH (2)` = bearish structure with bullish
reversal evidence, `REVERSAL_BEARISH (-2)` = bullish structure with bearish reversal evidence.

* The **trend only changes on a confirmed Break of Structure**, never because one candle crosses a level.
* In BULLISH a confirmed **LH** (or a low taken by wick only) moves the state to REVERSAL_BEARISH (watch).
* In BEARISH a confirmed **HL** (or a high exceeded by wick only) moves the state to REVERSAL_BULLISH (watch).
* A watch is cancelled when the original trend prints a new HH (bullish) / LL (bearish).
* NEUTRAL is the initial state until the first BOS.

### Break of Structure
* Level = the active confirmed swing high (bullish BOS) or swing low (bearish BOS).
* `BOS Confirmation = Close` (default): close must be beyond level ± `BOS Break Threshold × ATR`
  for `BOS Confirmation Candles` consecutive candles. `Wick` mode uses high/low.
* Each level can be broken **once**; after a BOS it is retired (drawn dotted) until the next swing confirms.

### Liquidity sweeps / failed breaks (Close mode only)
Wick beyond the active level but close back inside it. In a bullish context it is labelled
**FAILED BULL BREAK**, in a bearish context **BEARISH SWEEP** (mirror for lows). Sweeps never create a BOS;
they are reversal evidence and (optionally) trigger REVERSAL WATCH.

---

## 3. How the reversal system works (two stages)

**Stage 1 — REVERSAL WATCH** (no trade). Any of:
* a counter-trend Dow point: HL inside a bearish trend, LH inside a bullish trend;
* a liquidity sweep of the active structure level (when `Sweep Triggers Reversal Watch` is on).

The dashboard shows `REV WATCH ▲/▼`, an orange marker is printed once, and the "Reversal Watch" alert fires.

**Stage 2 — CONFIRMED REVERSAL.** A BOS *against* the current trend: close above the last LH (bullish) or below
the last HL (bearish), with the ATR threshold and confirmation candles satisfied. The state flips, the line is
labelled **CHoCH**, and the signal engine evaluates **LONG REVERSAL / SHORT REVERSAL**.

Evidence collected in stage 1 is carried into the score: a reversal with a confirmed HL **and** a sweep scores
25/25 on the structure component; a "V" reversal with no prior evidence scores 10/25 and 5/10 on the reversal
component, so it rarely passes the default threshold.

Sequence the indicator is built for:
`BEARISH → sweep of the low → HL → close above the LH (CHoCH) → LONG REVERSAL`

---

## 4. Multi-timeframe system

* Defaults: HTF 4H, MTF 1H, LTF 15M, Entry 5M — all changeable.
* Each timeframe runs the full engine and reports: state, last high type, last low type, bars since last
  bullish/bearish BOS, bars since last reversal.
* **Non-repainting**: HTF values are `expression[1]` with `lookahead_on`, i.e. the value of the last **completed**
  HTF bar. History and realtime show exactly the same thing. A timeframe equal to the chart uses the live chart
  engine instead.
* **Signals are generated on the chart timeframe.** Put the chart on the Entry timeframe (5M). If the chart is on
  a different timeframe the dashboard warns you and signals use the chart structure instead.
* Bias logic (dashboard `MULTI-TF BIAS`):

| Condition | Bias |
|---|---|
| all four bullish / bearish | STRONG BULLISH / STRONG BEARISH |
| 4H & 1H bullish, 15M or 5M bearish (or turning up) | BULLISH — PULLBACK |
| 4H & 1H bearish, 15M or 5M bullish (or turning down) | BEARISH — PULLBACK |
| 4H or 1H in a reversal-watch state | REVERSAL DEVELOPING ▲ / ▼ |
| 4H and 1H opposed | MIXED / CONFLICT |
| otherwise | BULLISH (HTF) / BEARISH (HTF) / NEUTRAL |

---

## 5. Confidence score (0–100)

| Component | Max | Continuation signal | Reversal signal |
|---|---|---|---|
| Dow structure | 25 | HH+HL (or LH+LL) both confirmed 25 · one of them 17 · none 10 | 10 base + 10 if a counter-trend HL/LH preceded + 5 if a sweep preceded |
| HTF alignment | 25 | 4H 12 · 1H 8 · 15M 5. Same direction = full; opposite trend but in watch toward the trade = 50 %; same trend with a warning = 60 %; neutral = 35 %; opposed = 0 | same |
| BOS confirmation | 15 | close ≥ 0.5 ATR beyond the level 15, else 10; Wick mode 10 | same |
| Volatility | 10 | ATR not compressed 5 · price ≤ 60 % of max extension from the opposite swing 5 (else 2) | same |
| Momentum | 10 | RSI on the right side 5 · ADX ≥ threshold 5 (a disabled filter counts as 5) | same |
| Reversal | 10 | 10 if no timeframe is in a reversal watch against the trade | 10 with stage-1 evidence, 5 without |
| Noise | 5 | 5 if the last BOS the other way is ≥ 2 × "Minimum Bars Between Signals" ago | 5 if the previous same-direction BOS is that old |

Strength: 0–49 WEAK · 50–69 MODERATE · 70–84 STRONG · 85–100 VERY STRONG.
`Minimum Signal Score` (default 75, options 50–90) decides whether the label prints. The label tooltip shows the
breakdown. `Show Below-Threshold Setups` prints tiny grey markers for setups that failed only the score — useful
while tuning, off by default.

---

## 6. Exactly when LONG / SHORT print

Common gates for every signal (all must be true):
1. bar is closed (`Evaluate Signals On Bar Close Only`);
2. session allowed (if the session filter is on);
3. **not** RANGING / CHOP;
4. cooldown: ≥ `Minimum Bars Between Signals` since the previous signal of any kind;
5. price not further than `Max Extension From Swing × ATR` from the opposite swing;
6. score ≥ `Minimum Signal Score`.

**LONG** (continuation): chart structure is BULLISH and a bullish BOS confirms on this bar (close above the active
swing high by the threshold). HTF must not be strictly BEARISH; with `Continuation Signals Require MTF Not Opposed`
the 1H must not be strictly BEARISH either. Reversal-watch states on HTF do not block, they only cost points.

**LONG REVERSAL**: chart structure was BEARISH or REVERSAL_BULLISH and a bullish BOS (CHoCH) confirms. Allowed
against the HTF when `Allow Reversal Signals Against HTF` is on — then the rest of the setup has to be near
perfect to reach 75.

**SHORT / SHORT REVERSAL**: exact mirrors.

**Chop** (any of): ≥ `Chop: Trend Flips In Lookback` direction changes in the lookback; or ADX < threshold together
with (structure range < `Chop: Max Structure Range × ATR`, or ATR < `Min ATR / Avg` × average, or ≥ 2 equal
highs/lows in the lookback). Dashboard shows **NO TRADE — CHOP** and the background is shaded.

### Scenario check (defaults, chart on 5M)
| Scenario | Result |
|---|---|
| A · 4H/1H/15M bullish, 5M bullish BOS | `▲ LONG`, score 95–100 |
| B · mirror | `▼ SHORT` |
| C · 4H bearish, 15M bearish, 5M sweep → HL → close above LH | `↗ LONG REVERSAL` only if every other component is full (score lands at 75). If the 1H or 15M already flipped or is in watch, 77–90. Lower the threshold to 70 if you want counter-HTF reversals routinely |
| D · mirror | `↘ SHORT REVERSAL` |
| E · low ADX, small swings, repeated flips | `NO TRADE — CHOP`, no labels |
| F · 4H/1H bullish, 15M/5M bearish | Bias `BULLISH — PULLBACK`; no SHORT (HTF gate); a later 5M CHoCH up prints `LONG REVERSAL` = the pullback entry |
| G · wick above the high, close back below | no BOS; `FAILED BULL BREAK` / `BEARISH SWEEP` marker, state → REV WATCH ▼ |

---

## 7. Recommended settings for XAUUSD (chart on 5M)

| Input | Value | Why |
|---|---|---|
| Swing Length | 5 | ≈ 25 min each side on 5M; raise to 7–8 for fewer swings |
| ATR Length | 14 | standard |
| Minimum Swing Distance | 1.2 ATR | gold's 5M noise is usually < 1 ATR |
| Minimum Structure Displacement | 0.3 ATR | avoids labelling double tops/bottoms as HH/LL |
| BOS Break Threshold | 0.15 ATR | filters one-tick breaks |
| BOS Confirmation | Close, 1 candle | use 2 candles in news-heavy sessions |
| Minimum Bars Between Signals | 20 | ≈ 100 min |
| Chop lookback / flips / range | 60 / 3 / 2.0 ATR | |
| RSI 14 > 50 / ADX 14 ≥ 20 / ATR ≥ 0.8 × SMA50 | on | secondary filters |
| Session filter | off (London + New York when on, UTC) | switch on if Asia gives you false BOS |
| Minimum Signal Score | 75 | expect roughly 1–4 signals per day |
| Chop symptoms required | 2 | one symptom alone no longer blocks trading |
| Allow reversals against HTF | off | the worst losses on gold came from these |
| Max extension from swing | 2.0 ATR | stops the indicator entering on a spike |
| Retest entries | on, armed 30 bars | second entry after a break, better price |
| Dow pullback entries | on | buys the confirmed HL in an uptrend |
| Stop Loss Basis | Tightest of both | structure stop, capped by 1.5 ATR |
| Structure SL Buffer | 0.25 ATR | keeps normal gold wicks out of the stop |
| Take Profit Basis | R Multiple, 1 / 2 / 3 R | switch to Structure Projection for measured moves |
| Keep Trades From Last | 30 days | rolling one-month window of trades |
| Safety Cap | 60 trades | ceiling on drawing objects |

On a 15M chart use Swing Length 4–5, Minimum Swing Distance 1.0 and set the Entry timeframe to 15.

---

## 8. Adding it to TradingView

1. Open a XAUUSD chart (OANDA, FXCM, or your broker feed) on the **5-minute** timeframe.
2. Bottom panel → **Pine Editor** → *Open* → *New indicator*, delete the template.
3. Paste the whole content of `DowTheory_MTF_XAUUSD.pine`.
4. **Save** (give it a name) → **Add to chart**.
5. Gear icon on the indicator → adjust inputs and colours. Dashboard position is under *Dashboard*.

The script was written for Pine Script v6 and checked by hand (bracket balance, line wrapping, v6 rules such as
booleans never being `na`). It has **not** been compiled inside TradingView from this environment. If the editor
reports an error, copy the exact message and line and it is normally a one-line fix.

---

## 9. Creating alerts

1. Right-click the chart → **Add alert** (or the clock icon).
2. *Condition*: choose **Dow Theory MTF Structure [XAUUSD]**, then one of:
   LONG · SHORT · LONG REVERSAL · SHORT REVERSAL · Bullish BOS · Bearish BOS · Reversal Watch ·
   Strong Bullish Alignment · Strong Bearish Alignment.
   Or choose **Any alert() function call** to receive the dynamic messages, e.g.
   `XAUUSD LONG | Score: 87 (VERY STRONG) | 4H BULLISH | 1H BULLISH | 15M BULLISH | 5M BOS▲ | Price 2412.35`
3. *Options*: **Once per bar close**. Signals are computed on bar close, so this matches what you see on the chart.
4. Name it and choose the notification channels. Create one alert per condition you want.

Alerts are only sent when the label would print (same gates and score threshold), so an alert equals a chart signal.

---

## 10. Reading the chart

* **Labels** HH / HL (green) and LH / LL (red) only on ATR-significant confirmed swings; EQH / EQL grey.
* **Structure lines** connect confirmed swings only; an extended swing moves its own label and line rather than
  adding new ones.
* **Solid level lines** = active swing high (red) and swing low (green); dotted = already broken.
* **Dashed lines + BOS ▲/▼** mark where structure broke; **CHoCH** marks a break that flipped the trend.
  Only the newest `Maximum Structure Levels` are kept.
* **dev H / dev L** is the unconfirmed candidate swing. It moves; confirmed labels never do.
* **Orange markers**: REV WATCH (stage 1), sweeps and failed breaks.
* **▲ LONG / ▼ SHORT** with the score; **↗ LONG REVERSAL / ↘ SHORT REVERSAL**. Hover for the score breakdown.
* **Chop background shading is off by default.** The RANGING / CHOP state is still enforced and is reported in
  the dashboard CONDITION row. Turn *Shade Chop Zones (background)* back on if you want the shading.
* **SL / TP lines** appear on every LONG / SHORT signal (see section 11).

---

## 11. Stop loss and take profit

Every LONG / SHORT / reversal signal draws its own trade levels. They are fixed on the signal bar and never move;
only the right edge of the drawing is extended while the trade is still running.

**Entry** is the close of the signal bar (white line, `ENTRY` label).

**Stop loss** (`Stop Loss Basis`):

| Mode | Placement |
|---|---|
| Structure | beyond the swing that protects the setup: the active swing low for a long, swing high for a short, minus/plus `Structure SL Buffer × ATR` |
| ATR | entry ∓ `ATR SL Multiplier × ATR` |
| Tightest of both (default) | whichever of the two sits closer to entry, so a very deep structure stop is capped by the ATR stop |

A safety rule forces a minimum distance of 0.15 ATR, so the stop can never land on or across the entry.

**Take profit** (`Take Profit Basis`):

* **R Multiple** (default): TP1 / TP2 / TP3 at 1R / 2R / 3R, where 1R is the distance from entry to stop.
  The multiples are editable.
* **Structure Projection**: the broken leg (active swing high to swing low) projected from the break level at
  1x, 1.618x and 2x. If that projection would land too close to entry, the R multiples are used instead.

Labels on the right of each line show the price and the R multiple, for example `TP2 4410.30  2.0R`.
The stop label also shows the risk in dollars per ounce.

**Zones.** A red tint covers entry to stop, a green tint covers entry to the final target, so the risk/reward
shape is readable at a glance. Turn them off with `Shade Risk / Reward Zones`.

**Tracking.** While a trade runs the dashboard shows a TRADE row with the live R multiple. When price reaches the
stop or the final target the drawing freezes, dims, and is annotated `SL HIT`, `TP2 → SL`, or `TARGET +3.0R`.
A signal in the opposite direction closes the previous drawing with `closed · new signal`.
Only the newest `Max Trades Shown` trades stay on the chart.

**Alerts.** The LONG/SHORT alert message now carries the levels, for example
`XAUUSD LONG | Score: 87 (VERY STRONG) | 4H BULLISH | ... | Entry 4371.80 | SL 4352.10 | TP1 4391.50 | TP 4430.90`.
Two new alert conditions were added: **Take Profit Hit** and **Stop Loss Hit**.

These levels are drawing objects for discretionary use. The script is an indicator, not a strategy, so it does not
place or simulate orders, and the hit detection on the live bar can flicker intrabar before that bar closes.

---

## 12. Entry types

The engine now produces five kinds of entry. All of them pass the same gates and the same score threshold, and
all of them draw their own stop and targets.

| Label | Trigger | Typical use |
|---|---|---|
| `▲ LONG` / `▼ SHORT` | Break of Structure in the direction of the trend | the breakout itself |
| `↗ LONG REVERSAL` / `↘ SHORT REVERSAL` | stage-2 confirmed reversal, a break against the old trend | catching the turn |
| `⤴ LONG RETEST` / `⤵ SHORT RETEST` | price returns to the level it just broke and closes back off it | better price than the breakout candle |
| `▲ LONG PULLBACK` / `▼ SHORT PULLBACK` | a freshly confirmed HL inside bullish structure, LH inside bearish | classical Dow continuation, no new break needed |

**Retest.** After a break the level is remembered along with the bar it broke on. The entry arms for
`Retest Stays Armed` bars. It fires when price trades back to within `Retest Touch Tolerance` of the level and
closes beyond it in the trend direction on an up candle for longs, a down candle for shorts. There is one attempt
per break. The attempt is cancelled if price closes half an ATR through the level, which means the break failed.

**Dow pullback.** Fires on the bar that confirms a new higher low while structure is bullish, or a new lower high
while structure is bearish. It requires the higher timeframe to point the same way and the intermediate timeframe
not to oppose it. Because the swing needs `Swing Length` bars to confirm, the entry is deliberately late but never
repaints.

Both second-chance entries use a shorter cooldown, one third of `Minimum Bars Between Signals`, so a retest is not
swallowed by the breakout signal that preceded it. They also carry a lower break score than a fresh break, so they
need good multi-timeframe alignment to reach the threshold.

---

## 13. Stacked positions

Each signal creates its own position record with its own levels.

* A signal in the **same** direction adds a position. Two longs can run at once, each with its own stop and targets.
* A signal in the **opposite** direction closes every open position and marks them `closed · reverse signal`.
* Positions stay on the chart for a rolling window, `Keep Trades From Last`, which defaults to 30 days. Every
  position whose entry falls inside that window is drawn, open or closed. Older ones are removed automatically as
  time advances, so the chart always shows about the last month of trades.
* `Safety Cap` is a hard ceiling on the number of position drawings, default 60, so the script cannot exhaust
  TradingView's drawing objects on a busy month. Lower it if the chart feels crowded.
* TradingView keeps at most 500 labels per script and deletes the oldest when that is exceeded. On a low
  timeframe with many swing labels, the oldest trade labels can be dropped before the window expires. Turning off
  the swing or watch labels frees budget if you want the full month visible.
* The dashboard TRADE row shows how many positions are open and the live R multiple of the newest one.

---

## 14. Chop detection, rewritten

Chop is now a count of symptoms rather than a single trigger. The five symptoms are weak ADX, compressed ATR, a
small structure range, two or more equal highs or lows in the lookback, and frequent trend flips. Trading is
blocked when `Chop: Symptoms Required` of them are present at once, which defaults to two.

The old rule declared chop as soon as structure had flipped three times in the lookback, with no reference to ADX
or volatility. That misread ordinary trending markets with deep pullbacks as chop and blocked signals in exactly
the conditions worth trading. Raise the symptom count to trade more, lower it to trade less.

---

## 15. Liquidity map and counter-trend scalps (v2 file only)

This answers the case where the higher timeframe is short but the chart timeframe keeps producing tradeable legs
upward. Those legs are not noise. They are price reaching for liquidity that sits inside the higher-timeframe
range, and they can be traded small and in the opposite direction to the main bias.

### External and internal liquidity

**External liquidity**, drawn as two solid lines labelled `ERL HIGH` and `ERL LOW`, is the higher-timeframe swing
high and swing low. It is where the higher-timeframe leg is ultimately drawn. Taking one of them ends the current
range and starts an expansion.

**Internal liquidity**, drawn as two dotted orange lines labelled `IRL`, is the nearest chart-timeframe swing above
and below price that sits inside that range and has not been traded through yet. Those are the pools a pullback
reaches for while the higher timeframe stays in its trend. The engine remembers up to `Internal Pools Remembered`
of them per side and forgets each one the moment price trades through it.

The dashboard gains a LIQUIDITY row reading one of:

| Phase | Meaning |
|---|---|
| `INTERNAL · with trend` | inside the HTF range, chart timeframe agrees with it |
| `INTERNAL · counter-trend leg` | inside the range, chart timeframe has turned against the HTF. This is the scalp window |
| `INTERNAL · range` | inside the range with no HTF direction |
| `EXTERNAL · expansion` | price has left the range, the HTF leg is extending |

The right-hand cell shows the two nearest pools, or the range bounds when no internal pool survives.

### Counter-trend scalps

When the higher timeframe is bearish, every normal long is blocked by the higher-timeframe gate, which is correct
for a full position. The scalp path opens a small one instead:

* the higher timeframe is trending, in this example bearish;
* price is inside the higher-timeframe range, not in expansion;
* the chart timeframe puts in a bullish break of structure or a confirmed reversal;
* the nearest internal pool above is at least `Minimum Room To Next Pool` away, so the target is worth taking;
* the score clears `Minimum Scalp Score`, which defaults to 60 rather than 75, because higher-timeframe alignment
  can never pay points on a counter-trend trade.

It prints `↑ LONG SCALP` or `↓ SHORT SCALP` in a faded colour so it never reads like a full-size signal, and the
tooltip states which way the higher timeframe still points.

**Targets are different for a scalp.** Instead of 1R, 2R and 3R, the three levels are spaced at 40 per cent,
70 per cent and 100 per cent of the distance to the internal pool, so the final target sits exactly on the
liquidity being reached for. The R multiples on the labels are computed from the real prices, so they stay honest.
If no pool survives on that side, the standard R multiples apply.

`Scalp Maximum Target (R)`, default 2.0, is the ceiling. A distant pool would otherwise turn a scalp into a
full-size counter-trend position, so when the pool sits beyond that many multiples of risk the final target is
clamped there instead and the three levels are spaced across the clamped distance, giving 0.8R, 1.4R and 2.0R.
The pool wins whenever it is closer than the ceiling. `Minimum Room To Next Pool` remains the floor at the other
end, so a scalp is never taken for a target that is not worth the trade.

Two alert conditions were added, one per scalp direction.

### The anti-chasing fix

The base file measures extension from the opposite swing for every entry. At a break of structure the close is a
full swing leg from that swing by definition, so the 2.0 ATR ceiling rejected essentially every breakout entry and
left only pullbacks and retests firing.

The v2 file measures a break by how far past the level it just broke the candle closed, controlled by
`Max Close Beyond Broken Level`, default 1.0 ATR. Breakouts and reversals use that. Retest and pullback entries
keep the old swing-distance measure, which is the right one for them. The scoring function uses the same
per-entry-type reference for its volatility component.

---

## 16. Location filters (v2 file)

Structure tells you *what* the market is doing. These four filters decide *where* that structure is worth acting
on. They were added after live charts showed structurally correct signals losing purely because of their location.

### Liquidity proximity

`Block Entries Into Nearby Liquidity`, on by default with a 0.75 ATR requirement.

An entry is refused when the nearest untaken pool in its own direction sits closer than that. Selling two points
above an untouched swing low means price sweeps the pool, the trapped sellers get run, and the trade stops out
before it can go anywhere. The obstacle is the nearest internal pool, or the external range edge when no internal
pool survives on that side. This applies to breakouts, reversals, retests and pullbacks. Scalps keep their own
`Minimum Room To Next Pool` setting.

### Scalp zone, premium and discount

`Scalps Only From The Right Half Of The Range`, on by default at 0.5.

A counter-trend long scalp is only taken from the lower part of the higher-timeframe range, a short scalp only
from the upper part. Buying premium against a bearish higher timeframe is the worst location for that entry type.
Lower the fraction for a stricter discount requirement.

### Range block

`Range Blocks Continuation Entries`, on by default at four midpoint crossings.

While price stays inside the higher-timeframe range and keeps crossing its midpoint, breakout, retest and pullback
entries are refused. Reversals and scalps still fire, because fading the edges is the correct trade inside a range.

This exists because ADX cannot see a range this wide. Each leg of a two-hundred-point oscillation is directional
on its own, so ADX reads thirty and the chop filter never engages while the market whipsaws. Counting midpoint
crossings inside the higher-timeframe range detects the condition that ADX structurally cannot. The dashboard
CONDITION row shows `RANGE — fade only` when it is active.

### Price spacing

`Minimum Price Spacing Between Entries`, on by default at 1.0 ATR.

A second entry in the same direction must be that far in price from the previous one. The bar cooldown spaces
signals in time only, which still allowed three shorts within fifty bars at nearly the same price. One failed
premise then became three losing positions. Spacing in price makes each additional entry a genuinely different
trade.

---

## 17. Entry-timeframe veto

`Entry TF Veto On Continuations`, on by default, under Multi-Timeframe.

Until this was added the entry timeframe fed the dashboard row and the bias wording and nothing else. It never
gated a signal and never scored. That is why a short could print while the 5-minute row read BULLISH with a fresh
bullish break sitting right next to it on screen.

A with-trend entry, meaning breakout, retest or pullback, is now refused while the entry timeframe has broken
structure the other way within `Entry TF Opposing Break Within` bars, ten by default. Reversals and counter-trend
scalps are exempt, because for those the entry timeframe agreeing with the trade is the point.

When the veto is active the entry-timeframe row in the dashboard is marked with a no-entry symbol, so you can see
why a setup you expected did not print.

### Checking which build is on the chart

Signals are recomputed across all history whenever the script changes, so an update that appears to do nothing is
usually the previous copy still on the chart. Two checks that take a moment:

* The indicator title must read **Dow Theory MTF Structure + Liquidity**, with a short title of `DOW-MTF+L`. Plain
  `DOW-MTF` is the base file.
* Open the settings and look for the **Liquidity & Scalps** group containing `Block Entries Into Nearby Liquidity`,
  and the **Multi-Timeframe** group containing `Entry TF Veto On Continuations`. If either is missing, the pasted
  source is older than that change.

---

## 18. Code review pass

A full read of the v2 file found four issues, all fixed.

| Finding | Severity | Fix |
|---|---|---|
| `Enable LONG` and `Enable SHORT` were checked only by the breakout and reversal paths. Retest, pullback and scalp entries ignored them, so turning longs off still produced long entries | real bug | both switches now gate all five entry types |
| The scoring function runs ten times per bar and built its breakdown string every time, throwing away nine of them. On a long history that is wasted work that can push the script past TradingView's calculation budget | performance | the string is built only when the score could actually print |
| Three take-profit variables were declared through tuple destructuring and later reassigned by the scalp target logic | robustness | they are now plain float variables, so no reassignment happens on tuple-declared names |
| The entry-timeframe veto marker on the dashboard did not say which direction was refused | clarity | shows ⛔▲ when longs are vetoed and ⛔▼ when shorts are |

Checked and found sound: bracket, brace and quote balance; no tabs; every wrapped line indented off the four-space
grid so Pine reads it as a continuation; declaration order for all cross-section references; the nine-value
security tuples matching their four destructurings; array bounds guarded on every loop; division guarded wherever
a range could be zero; field access on the trade record always behind a `na` check; dashboard row indices inside
the declared table size; and a label block plus an alert condition for all five entry types.

Two known behaviours that are deliberate rather than defects. Within a single bar the script cannot know whether
the target or the stop came first, so a bar that touches both is recorded as the target then the stop, which
flatters that result slightly. And the internal liquidity map holds confirmed swings only, so a low that formed
within the last `Swing Length` bars is not yet a pool and the proximity filter cannot see it.

---

## 19. External sweep rule

The gap this closes: both the liquidity proximity filter and the range block are defined only inside the
higher-timeframe range. Once price drops under the external low, the downside obstacle becomes empty and the
proximity filter passes unconditionally, while `boxed` requires price to be inside the range so the range block
switches off too. Both protections went quiet at exactly the spot where a short is most likely to fail, which is
what produced the two losing shorts below the 4-hour low.

### The rule

The moment price reaches a higher-timeframe extreme, the resting liquidity there has been collected. Selling
straight after the low is taken, or buying straight after the high is taken, is trading into the side that has
just been filled.

* Reaching the external low starts a cool-off. Every short is held until `External Sweep Cool-Off` bars have
  passed, twenty by default.
* Reaching the external high does the same for longs.
* It applies to all ten entry paths, breakout, reversal, retest, pullback and scalp, in both directions. There is
  no entry type for which buying right after the high is taken is a good idea.

### Grab versus breakdown

The cool-off is counted from the **start** of the excursion, not the last touch. A liquidity grab reverses
quickly and stays blocked for the whole window. A genuine breakdown that simply keeps trading below the level
resumes after the window expires, so a real higher-timeframe trend is not locked out. A later fresh excursion to
the level opens a new window.

### It also feeds the score

A swept external level is evidence for the opposite trade, so for twice the cool-off window it counts as sweep
evidence in the reversal and scalp scores. Taking the low is a reason to look for longs, not a reason to keep
selling.

### What you see

* `ERL SWEPT ▼` and `ERL SWEPT ▲` labels at the bar the level is first reached.
* The dashboard LIQUIDITY row reads `EXT SWEEP ▼ · shorts held` or `EXT SWEEP ▲ · longs held` during the cool-off.
* Two new alert conditions, External Low Swept and External High Swept.

Applied to the chart that prompted this, both shorts under the 4-hour low at roughly 4359 and 4352 are refused,
and the reversal long that followed the bounce scores higher for the sweep that preceded it.

---

## 20. Why positions were hitting the stop, and what changed

A diagnostic build recorded every closed position with the best it ever ran, in multiples of risk. Ten of
thirteen closed trades hit the stop, and they shared one signature.

| Across the ten losers | Value |
|---|---|
| Median best excursion | 0.20R |
| Median bars held | 4 |
| Median score | 88 |

A trade whose best moment is a fifth of the risk, four bars in, was wrong at entry. That rules out trade
management, because a breakeven stop or a trail cannot rescue a position that never reaches 1R, and it rules out
widening the stop, which would only enlarge the same losses. The entry location was the whole problem.

**Seven of the ten were shorts taken below the 4-hour low**, with range position as low as −0.47 and the target
column reading 99, the placeholder for "no obstacle found". They sold into a range whose low had already been
taken, with nothing left underneath, and the engine could not tell.

**The other three were shorts high in the range with dead momentum**, at ADX 16, 9 and 15, whose best excursions
were 0.05, 0.14 and 0.01.

**The score was not discriminating.** Losers scored 78 to 97, and a 97 lost. The only clean winner was the lowest
score on the board, a counter-trend long scalp at 67 taken from the discount half with a real target, which
reached its 2R ceiling in seven bars.

### The six changes

1. **`Require A Liquidity Target`**, on. No untaken pool or range edge in the trade's direction is now a refusal.
   Previously an unknown target was read as unlimited room; it actually means nowhere to go. This alone removes
   the seven-trade cluster.
2. **`Minimum Target Distance (R)`**, 1.5. The nearest opposing pool must be at least that many multiples of the
   prospective risk away, so a trade that cannot reach its own first target is never taken. The stop is now priced
   before the gate rather than after, which is why this is possible.
3. **`Entry Zone Limit`**, on at 0.15. Premium and discount now applies to every entry type rather than scalps
   alone. No shorts from the lowest 15 percent of the higher-timeframe range or below it, no longs from the
   highest 15 percent or above it.
4. **`ADX Hard Gate`**, on. ADX was worth five score points and blocked nothing, which is how an entry fired at a
   reading of 9. It now refuses every entry except a counter-trend scalp while ADX is under the threshold.
5. **Location-weighted alignment.** Higher-timeframe alignment peaks exactly when price is most extended, which is
   why the losers scored so well. The 25-point component is now multiplied by 1.0, 0.8 or 0.55 depending on where
   in the range the trade is being taken, so the score stops rewarding the worst locations. The label tooltip
   shows the factor as `Loc x0.55`.
6. **`Show Trade Diagnostics`**, off by default, under Dashboard. A second table listing every closed position
   with its best excursion, bars held, and the range position, target distance and ADX at entry. This is the table
   the analysis above came from. Leave it on while tuning; it turns judgement into measurement.

---

## 21. Correcting the over-restriction

The previous round cut signals almost to zero. The cause was one rule of mine, and it was wrong in principle.

**`Require A Liquidity Target` refused any entry with no pool ahead of it.** A trend, by definition, runs into
ground with no untaken structure in front of it. That rule therefore permitted trading only inside ranges and
never out of them. What actually killed the losing shorts was not a missing target, it was selling from the
bottom of a range whose low had already been taken, and the zone and sweep rules already handle that.

The rule is now inverted to match how a trader reads it. A pool sitting closer than `Minimum Target Distance`
still refuses the trade, because it cannot reach its own first target. No pool at all is open space, the best
case, and is allowed. The setting is renamed `Refuse Entries With No Room To Run`.

Three further changes, each aimed at more trades rather than fewer:

**ADX is now tiered.** Continuation entries still need the full threshold, since trend strength is the premise of
the trade. Reversals and scalps need 60 percent of it, because a reversal happens precisely as trend strength
dies and holding it to the trend bar was blocking the good ones. It still refuses a market with no pulse, which
is what produced the entry at ADX 9.

**Scalps are allowed in a neutral higher timeframe.** They previously required the higher timeframe to be
strictly trending. Range fades into internal liquidity were the only consistently profitable pattern in the
recorded data, and that rule locked them out of exactly the market they suit.

**`Move Stop To Entry After TP1`**, new and on by default. Once the first target trades, the stop moves to the
entry price and the drawing switches to a dotted line marked `BE STOP`. Three of thirteen tracked positions
reached a full unit of risk or more and then gave it all back. This converts those from losses to scratches
without costing a single signal, and outcomes closed that way are tagged `BE` rather than `SL`.

### Gate audit

`Show Trade Diagnostics` now draws a second table listing, for every bar that produced a valid setup, which rule
refused it and what share of setups that rule accounts for. Rules refusing more than 40 percent are red, 15 to 40
amber. This is how to tune the stack: turn it on, find the rule at the top, and decide whether it is earning its
place. Guessing at which filter is starving the system is what cost the last round.

---

## 22. Fair value gap entries, and what the audit found

### The gap entry

A displacement leg that breaks structure leaves a three-bar hole behind it: the high of the first bar sits below
the low of the third. Price returning into that hole is the same idea as the level retest, but the gap sits above
the broken level rather than at it, so it triggers earlier and considerably more often.

`Enable Fair Value Gap Entries`, on by default. A gap is only recorded if it is at least `Minimum Gap Size`, a
quarter of an ATR, so ordinary bar-to-bar spacing is ignored. It stays armed for 40 bars, allows one attempt, and
dies the moment price closes through it. The live gap is drawn as a tinted box. The entry passes the same gate
stack as every other type and prints `LONG FVG` or `SHORT FVG`.

On a 15-minute chart this visibly multiplied the number of entries, which answers the question it was built for.

### What the gate audit actually says

Turning on `Show Trade Diagnostics` and reading the audit over 587 recorded setups:

| Refused by | Setups | Share |
|---|---|---|
| Higher timeframe opposed | 286 | 49% |
| Premium / discount zone | 195 | 33% |
| No room to run | 157 | 27% |
| Chop | 132 | 22% |
| Range block | 82 | 14% |
| Score below threshold | 74 | 13% |
| External sweep cool-off | 64 | 11% |
| Price spacing | 44 | 7% |
| Pool too close | 32 | 5% |
| ADX | 16 | 3% |
| Cooldown | 17 | 3% |
| Entry timeframe veto | 10 | 2% |

**The higher-timeframe gate is the binding constraint, not any of the filters added recently.** It refuses nearly
half of everything, and it is doubly strict because `Continuation Signals Require MTF Not Opposed` demands that
the 4-hour *and* the 1-hour both agree. On a 15-minute chart that means trading only when three timeframes are
stacked, which is both rare and usually late. Standard practice is to take direction from one higher timeframe
and let the next one down be the pullback.

Ranked by trades recovered per unit of risk added:

1. Turn **`Continuation Signals Require MTF Not Opposed`** off. The 4-hour gate stays. This is the single largest
   lever available.
2. Lower **`Minimum Target Distance`** from 1.5R to 1.0R. Recovers part of the 27 percent.
3. Raise **`Chop: Symptoms Required`** from 2 to 3.

Leave the premium and discount zone alone despite its 33 percent. That is the rule that was blocking the losing
cluster, and it is doing the job it was added for.

### Backtesting

`DowTheory_MTF_XAUUSD_STRATEGY.pine` is the same engine wrapped as a `strategy()`, so TradingView's Strategy
Tester reports real trade counts, win rate, profit factor and drawdown. It enters on every signal, exits at the
stop or the final target, and models the move to break even. Costs are set to 0.005 percent commission and two
ticks of slippage; raise them to match your broker before trusting any number.

An `indicator()` cannot be backtested, which is why the separate file exists. Load it, open the Strategy Tester
tab, and toggle one input at a time to see what each rule is worth.

---

## 23. Measured: turning off the MTF requirement changes nothing

I recommended `Continuation Signals Require MTF Not Opposed` off as the single largest lever. Measured on the
chart, it is worth nothing. The audit counts were identical to the digit before and after the toggle: 587 setups
seen, 286 refused as higher-timeframe opposed, 25 taken.

The reason is that the 4-hour and the 1-hour agree nearly all the time in this data, so the 1-hour clause almost
never binds independently. The 49 percent refusal rate is the **4-hour gate alone**. Relaxing it means taking
counter-trend positions with full size, which is exactly what produced the earlier cluster of stop-outs.

That path already exists and is doing well. Widening the counter-trend scalp is the sound way to add trades;
weakening the 4-hour gate is not.

### The current record

Nine closed positions readable in the diagnostics:

| Outcome | Count | R |
|---|---|---|
| Target reached | 3 | +1.6, +3.0, +3.0 |
| Break even after TP1 or TP2 | 3 | 0.0 |
| Stopped | 3 | −1.0 each |
| **Net** | **9** | **+4.6R** |

Two things stand out. The break-even rule converted three positions that had reached their first or second target
and then reversed; without it the same nine trades net +1.6R instead of +4.6R, so that one rule is worth roughly
three units of risk across this sample. And the three remaining losers show best excursions of 0.04, 0.24 and 0.27
units, the same "wrong at entry" signature as before, all of them shorts taken in a market that kept rallying
against a bearish 4-hour.

Nine trades is not a sample to draw conclusions from. Treat the sign as encouraging and the magnitude as noise
until there are several dozen.

---

## 24. Support and resistance, and the first real backtest

### The S/R layer

A single swing is one opinion. A price that several confirmed swings have turned at is a level. The engine now
clusters confirmed swings into levels: a new swing within `Level Merge Tolerance` of an existing level joins it
and raises its touch count, otherwise it starts a new one. Levels with at least `Touches To Count As A Level`
touches are the ones that matter, and the nearest above and below are drawn as dashed lines tagged `RES x3`
and `SUP x2`.

It is used two ways:

* **As a gate on every entry.** No buying with resistance within `Room To The Level`, no selling with support that
  close. This applies to all twelve entry paths.
* **As an entry of its own.** `Enable S/R Rejection Entries` fires `LONG S/R` or `SHORT S/R` when price wicks into
  a proven level and closes back off it. It is the one entry that needs no break of structure first, and it
  re-arms after `S/R Entry Re-Arm` bars so a level cannot fire repeatedly.

### What the Strategy Tester says

XAUUSD 15-minute, 1 June to 10 September 2026, 10K account, 100 percent of equity per trade, 0.005 percent
commission, two ticks of slippage.

| Configuration | Trades | Win rate | Profit factor | Net | Max drawdown |
|---|---|---|---|---|---|
| Before S/R | 28 | 32.1% | **0.802** | −2.72% | 7.56% |
| With S/R | 18 | 22.2% | **2.451** | +5.81% | 4.68% |
| With S/R, single 1R target | 19 | 26.3% | **2.583** | +6.35% | 4.51% |
| With S/R, 0.3R target | 19 | 26.3% | **2.303** | +5.86% | 4.79% |

The first two rows are a clean A/B on identical settings. **Support and resistance turned a losing system into a
profitable one**, from a profit factor of 0.80 to 2.45, while cutting maximum drawdown by nearly half.

### On the 65 percent win rate

The same table is the argument against chasing it. The system got dramatically better while its win rate fell
from 32 percent to 22 percent, because the filter removed far more losers than winners and the survivors run
further. Profit factor, not win rate, is what pays.

Rows three and four settle it empirically. Cutting the target from 1R to 0.3R did not move the win rate at all,
5 of 19 either way, and profit factor fell. The losing trades are stopped out before they reach any target, so a
smaller target only shrinks the winners. You cannot buy a higher win rate with target size in this system.

A 65 percent win rate is reachable only by a system whose winners are smaller than its losers, and tuning
parameters on this sample size until a number appears is curve fitting, which produces exactly the result that
does not survive live. The honest target is expectancy: profit factor above 1.5 with drawdown you can sit
through. This currently sits at 2.45 on 18 trades, which is encouraging and far too small a sample to trust.

### One loose end

A full settings reset produced 14 trades at profit factor 1.204 rather than the 18 at 2.451 measured minutes
earlier with the same script. Some input differs between the chart's stored values and the code defaults and I
did not isolate which before stopping. Treat the 2.451 figure as conditional on that configuration until it is
reproduced from a clean reset.

---

## 25. Runtime bug: max_bars_back

The indicator compiled cleanly and then drew nothing at all. No labels, no dashboard, no levels. TradingView
surfaced the reason only as a small banner under the chart:

```text
Error on bar 6696: The requested historical offset (301) is beyond the historical buffer's limit (300)
```

Pine allocates a 300-bar history buffer when it cannot infer how far back a series is read. Something in the
engine reaches past that, and the script dies silently at runtime rather than at compile time, which is why every
check for a compile error came back clean.

Both files now declare `max_bars_back = 1000` in their header. This is the documented remedy and costs nothing
but memory.

The lesson for this project: **a Pine script can compile, report no error, and still be completely dead.** From
here, confirming a build means seeing it draw, not seeing it compile.

### Which file to load

| File | Load it on | Purpose |
|---|---|---|
| `DowTheory_MTF_XAUUSD_v2.pine` | your trading chart | the indicator, `DOW-MTF+L`, carries the alerts |
| `DowTheory_MTF_XAUUSD_STRATEGY.pine` | a separate test chart | the backtest build, `DOW-BT`, feeds the Strategy Tester |

They are not alternatives and neither is wrong. Running both on one chart doubles every drawing and is what
produced the two entries in the legend.

---

## 26. Marker lanes

Swing labels were being covered by the orange markers. In one place two `LH` labels appeared adjacent with
nothing between them, which looked like a structure bug; the `LL` between them was simply hidden underneath a
`REV WATCH` label.

Every bar-anchored marker now sits in its own lane, measured outward from the bar's high or low:

| Lane | Contents |
|---|---|
| 0 | swing labels, HH / HL / LH / LL / EQH / EQL, on the price itself |
| 1 | entry signals |
| 2 | sweeps and failed breaks |
| 3 | reversal watch |
| 4 | swept external liquidity |

`Marker Lane Spacing (x ATR)` under Visualization sets the gap, 0.5 by default. Raise it if markers still crowd
on a busy chart, set it to zero to stack everything on the price as before.

Swing labels stay on the price because they are the reference everything else is read against. Nothing can now
cover them.

### The historical buffer error

Four tests on the live chart, each one ruling something out:

| Test | Result | Conclusion |
|---|---|---|
| Changed the only `300` in the code to 150 | error still read 301 against 300 | not my drawing lookback |
| Raised `max_bars_back` from 1000 to 5000 | reported limit stayed 300 | the declaration never reaches that series |
| Recompiled five materially different builds | error bar stayed 6702 every time | a live error would move |
| Reloaded the page | error cleared completely | it is session state, not the running script |

The weight of that points to a stale artifact left behind by the backtest script after it was removed from the
chart, rather than a fault in the indicator. I could not prove it outright, because the Pine Editor stopped
opening in that browser session before I could load the fixed build on a clean page.

**To settle it:** open a fresh chart that has never had the strategy on it, paste the indicator, and add it. If no
caution banner appears, it was the stale artifact.

### Timeframe clamping, which is a real fix either way

Chasing this exposed a genuine problem. On a 15-minute chart the indicator was calling `request.security` for a
5-minute entry timeframe. Asking for a timeframe **finer** than the chart forces Pine to buffer that finer series,
which costs performance and is a real way to exhaust the history buffer, and the declaration-level
`max_bars_back` does not extend it.

Every requested timeframe is now clamped so it is never finer than the chart. A row configured below the chart
timeframe reads the chart's own structure instead, and the dashboard note says so. On a 5-minute chart nothing
changes, since all four configured timeframes are equal or higher.
