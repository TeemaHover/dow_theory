# -*- coding: utf-8 -*-
"""Failed breakouts: trade the failure in the opposite direction.

Rule, fixed before running:
  * a Trend Core breakout (filters included) starts a watch on the broken level;
  * within W bars, a CLOSE back through that level by more than tol x ATR is a failure
    (the watch also ends on expiry, or when a newer breakout replaces it);
  * the failure signals a position OPPOSITE to the breakout, taken at the next open.

Modes:
  breakout   Trend Core as it is (baseline)
  fade       only failure trades, taken when flat, to measure the signal by itself
  reverse    breakouts as usual; a failure closes the breakout position if still open
             and opens the opposite one (flat: just opens it)
Fade stop: "atr2" = 2 x ATR from the signal close; "swing" = beyond the extreme the
failed breakout reached, plus 0.25 x ATR. Exits for every trade: 2.5 x ATR trailing
stop, 6R take-profit, stops filled at the open when a bar opens beyond them, 250-bar cap.
Filter: "none" fades regardless of trend; "opposite" requires the opposite trend filters.

Adoption rules, fixed before running, judged on the clean set (cash stock indices):
  fade      profit factor above 1 in BOTH eras
  reverse   beats the breakout on BOTH expectancy and total R in BOTH eras
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow2 as Q2
import qdow3 as Q3
import qbt
from qsig2 import ema
pd.set_option("display.width", 260)

CLEAN = ["NIKKEI", "FTSE", "DAX", "HANGSENG", "CAC40", "ASX200", "TSX", "STOXX50", "DJI", "DJT"]
Q.COST_BPS.update({"DJI": 2, "DJT": 3})


def arrays(s):
    df, atr = Q.prep(s)
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    a = atr.to_numpy(float)
    hh = pd.Series(h).rolling(8, min_periods=8).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(8, min_periods=8).min().shift(1).to_numpy()
    e = ema(c, 100)
    pu, pdn = Q2.m_primary(df)
    with np.errstate(invalid="ignore"):
        fl = (c > e) & pu
        fs = (c < e) & pdn
    if s in Q.US_EQ:
        gu, gd = Q2.m_twoavg(df)
        fl &= gu
        fs &= gd
    ok = np.isfinite(a) & (a > 0)
    with np.errstate(invalid="ignore"):
        brkL = (c > hh) & fl & ok
        brkS = (c < ll) & fs & ok
    return df.index, o, h, l, c, a, hh, ll, fl, fs, ok, brkL, brkS


def simulate(s, mode="breakout", W=10, tol=0.0, fstop="swing", filt="none", tp_r=6.0):
    idx, o, h, l, c, a, hh, ll, fl, fs, ok, brkL, brkS = arrays(s)
    n = len(c)
    half_bps = Q.COST_BPS.get(s, 5) / 1e4 / 2.0
    trades = []

    pos, entry, stop, risk, tgt, e_i, half, tag = 0, np.nan, np.nan, np.nan, np.nan, -1, 0.0, ""
    pend = None                      # (kind, dir, stop0, signal_i, tag)
    P, wdir, age, hi_s, lo_s = np.nan, 0, 0, np.nan, np.nan

    def close_trade(j, px, why):
        nonlocal pos
        exit_px = px - pos * half
        trades.append((idx[e_i], pos, ((exit_px - entry) / risk) * pos, tag, why))
        pos = 0

    for j in range(n):
        # 1. act at this bar's open on what the previous close decided
        if pend is not None:
            kind, d, stop0, si, ptag = pend
            pend = None
            if kind == "reverse" and pos != 0:
                close_trade(j, o[j], "reversed")
            if pos == 0:
                half = half_bps * c[si]
                entry = o[j] + d * half
                r = abs(entry - stop0)
                if r > 0:
                    pos, stop, risk, e_i, tag = d, stop0, r, j, ptag
                    tgt = entry + d * tp_r * r
        # 2. stop, then target, inside this bar (a bar opening beyond fills at the open)
        if pos != 0:
            if (l[j] <= stop) if pos > 0 else (h[j] >= stop):
                px = o[j] if ((o[j] < stop) if pos > 0 else (o[j] > stop)) else stop
                close_trade(j, px, "stop")
            elif (h[j] >= tgt) if pos > 0 else (l[j] <= tgt):
                px = o[j] if ((o[j] > tgt) if pos > 0 else (o[j] < tgt)) else tgt
                close_trade(j, px, "target")
            elif j - e_i >= 249:
                close_trade(j, c[j], "timeout")
        # 3. trail at the close
        if pos != 0 and ok[j]:
            cand = c[j] - pos * 2.5 * a[j]
            stop = max(stop, cand) if pos > 0 else min(stop, cand)
        # 4. failure watch, then arming, then decide for the next open
        fade = 0
        fade_stop = np.nan
        if wdir != 0:
            age += 1
            hi_s = max(hi_s, h[j]); lo_s = min(lo_s, l[j])
            if ok[j] and wdir == 1 and c[j] < P - tol * a[j]:
                fade, fade_stop = -1, (c[j] + 2 * a[j] if fstop == "atr2" else hi_s + 0.25 * a[j])
                wdir = 0
            elif ok[j] and wdir == -1 and c[j] > P + tol * a[j]:
                fade, fade_stop = 1, (c[j] - 2 * a[j] if fstop == "atr2" else lo_s - 0.25 * a[j])
                wdir = 0
            elif age >= W:
                wdir = 0
        if fade != 0 and filt == "opposite" and not (fs[j] if fade < 0 else fl[j]):
            fade = 0
        if fade != 0 and not ((fade_stop > c[j]) if fade < 0 else (fade_stop < c[j])):
            fade = 0
        if brkL[j]:
            P, wdir, age, hi_s, lo_s = hh[j], 1, 0, h[j], l[j]
        elif brkS[j]:
            P, wdir, age, hi_s, lo_s = ll[j], -1, 0, h[j], l[j]

        brk = 1 if brkL[j] else (-1 if brkS[j] else 0)
        if mode == "breakout":
            if pos == 0 and brk != 0:
                pend = ("enter", brk, c[j] - brk * 2 * a[j], j, "BRK")
        elif mode == "fade":
            if pos == 0 and fade != 0:
                pend = ("enter", fade, fade_stop, j, "FADE")
        else:  # reverse
            if brk != 0 and brk == fade:
                # a new breakout in the failure's own direction: take it as a breakout
                fade = 0
            if fade != 0 and pos == -fade:
                pend = ("reverse", fade, fade_stop, j, "FADE")
            elif fade != 0 and pos == 0:
                pend = ("enter", fade, fade_stop, j, "FADE")
            elif pos == 0 and brk != 0:
                pend = ("enter", brk, c[j] - brk * 2 * a[j], j, "BRK")
    if pos != 0:
        # like qbt: a trade still open when the data ends is closed at the last close
        close_trade(n - 1, c[n - 1], "end")
    return trades


def run(syms, **kw):
    rows = []
    for s in syms:
        try:
            for t in simulate(s, **kw):
                rows.append((s,) + t)
        except SystemExit:
            continue
    tr = pd.DataFrame(rows, columns=["sym", "entry_time", "dir", "r", "tag", "reason"])
    return tr.sort_values("entry_time").reset_index(drop=True)


def row(label, tr):
    out = {"variant": label}
    for name, a, b in Q.ERAS:
        m = (tr["entry_time"] >= pd.Timestamp(a, tz="UTC")) & (tr["entry_time"] < pd.Timestamp(b, tz="UTC"))
        g = tr[m]
        st = qbt.stats(g, name) if len(g) else {"n": 0}
        years = (pd.Timestamp(min(b, "2026-09-14")) - pd.Timestamp(max(a, "2000-01-01"))).days / 365.25
        k = name.split()[0]
        out[k + " n"] = st.get("n", 0)
        out[k + " PF"] = st.get("pf", 0)
        out[k + " expR"] = st.get("expR", 0)
        out[k + " R/yr"] = round(st.get("totR", 0) / years, 1)
        out[k + " ddR"] = st.get("maxDD_R", 0)
        f = g[g["tag"] == "FADE"]
        out[k + " fade n"] = len(f)
        out[k + " fade expR"] = round(f["r"].mean(), 3) if len(f) else 0.0
    return out


VARIANTS = [("breakout (current)", dict(mode="breakout"))]
for mode in ("fade", "reverse"):
    for W in (5, 10):
        for tol in (0.0, 0.5):
            for fstop in ("swing", "atr2"):
                VARIANTS.append(("%-7s W%-2d tol%.1f %s" % (mode, W, tol, fstop),
                                 dict(mode=mode, W=W, tol=tol, fstop=fstop)))
VARIANTS.append(("fade    W10 tol0.0 swing, opposite trend", dict(mode="fade", W=10, tol=0.0, fstop="swing", filt="opposite")))
VARIANTS.append(("reverse W10 tol0.0 swing, opposite trend", dict(mode="reverse", W=10, tol=0.0, fstop="swing", filt="opposite")))
VARIANTS.append(("fade    W10 tol0.0 swing, TP 2R", dict(mode="fade", W=10, tol=0.0, fstop="swing", tp_r=2.0)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "clean"
    syms = CLEAN if which == "clean" else Q3.WIDE
    print("=== %s: failed-breakout tests, realistic fills ===" % which.upper())
    rows = []
    for label, kw in VARIANTS:
        rows.append(row(label, run(syms, **kw)))
        print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)
    pd.DataFrame(rows).to_csv("fail_%s.csv" % which, index=False)
