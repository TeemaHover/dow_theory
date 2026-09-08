# Dow Theory MTF Structure [XAUUSD] — Pine Script v6

File: `DowTheory_MTF_XAUUSD.pine`

A low-noise, multi-timeframe Dow Theory market-structure indicator for discretionary Gold trading.
Primary engine: **Dow Theory swings + structure state machine + Break of Structure + multi-timeframe
confirmation + ATR noise filtering**. RSI / ADX / ATR / sessions are secondary filters only.

---

## 1. Architecture

The script is one file organised in the order the data flows:

| Section | What it does |
|---|---|
| 1. Inputs | Eight input groups: Structure, Noise Filter, Multi-Timeframe, Signals, Visualization, Filters, Sessions, Dashboard |
| 2. Utilities | Timeframe labels, state text/colours, session helper |
| 3–8. `f_engine()` | The whole structure engine: swing detection → Dow classification → state machine → BOS → reversal → sweeps. Pure calculation, no drawings, so the same function runs on the chart **and** inside `request.security()` |
| 9. Chart engine | `f_engine()` on the chart timeframe. Signals and drawings come from here |
| 10. MTF | Four `request.security()` calls (HTF / MTF / LTF / Entry) using `f_secEngine()` = engine values of the last **closed** bar of that timeframe |
| 11. Filters | RSI, ADX, ATR-compression, sessions, chop detection |
| 12. Bias | Combines the four timeframe states into one text (STRONG BULLISH, BULLISH — PULLBACK, MIXED / CONFLICT, REVERSAL DEVELOPING …) |
| 13. Score | 0–100 confidence score with seven components |
| 14. Signals | Gates + score → LONG / SHORT / LONG REVERSAL / SHORT REVERSAL |
| 15. Visualization | Swing labels, structure lines, BOS lines, sweep / watch markers, signal labels, active levels, developing swing, chop shading |
| 16. Dashboard | One table, refreshed on the last bar only |
| 17. Alerts | Nine `alertcondition()` entries + dynamic `alert()` messages |

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
* **Grey background** = RANGING / CHOP, no signals.
