# -*- coding: utf-8 -*-
"""Failed breakouts as pullbacks: re-enter in the trend direction when they end.

Rule, fixed before running:
  * a Trend Core breakout starts a 10-bar watch on the broken level;
  * a close back through the level is a FAILURE, and starts a PULLBACK watch in the
    original breakout direction, for up to W2 bars;
  * the pullback is cancelled as a probable reversal if the close goes more than
    deep x ATR beyond the level, or the trend filters stop passing; a newer breakout
    also ends it;
  * the pullback ENTRY, in the breakout direction at the next open, fires on
      "reclaim": a close back beyond the broken level, or
      "turn":    a close beyond the previous bar's high (low for shorts),
    with the trend filters passing;
  * stop "swing" = beyond the pullback's extreme plus 0.25 x ATR; "atr2" = 2 x ATR.
Exits as everywhere else: 2.5 x ATR trailing stop, 6R take-profit, gap fills, 250 bars.

Modes: breakout (baseline) | pullback (pullback entries only, when flat) |
       both (breakout or pullback, whichever when flat) |
       both_exit (as both, but a failure also closes the breakout position).
Adoption, fixed before running: beat the breakout on BOTH expectancy and total R in
BOTH eras on the clean set.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow3 as Q3
import qbt
import qfail as F
pd.set_option("display.width", 260)

OUTCOMES = []


def simulate(s, mode="breakout", W=10, W2=10, trig="reclaim", pstop="swing", deep=2.0,
             tp_r=6.0, collect=False):
    idx, o, h, l, c, a, hh, ll, fl, fs, ok, brkL, brkS = F.arrays(s)
    n = len(c)
    half_bps = Q.COST_BPS.get(s, 5) / 1e4 / 2.0
    trades = []
    pos, entry, stop, risk, tgt, e_i, half, tag = 0, np.nan, np.nan, np.nan, np.nan, -1, 0.0, ""
    pend = None
    P, wdir, age = np.nan, 0, 0
    pbP, pbdir, pbAge, pbExt, pb_i = np.nan, 0, 0, np.nan, -1

    def close_trade(j, px, why):
        nonlocal pos
        exit_px = px - pos * half
        trades.append((idx[e_i], pos, ((exit_px - entry) / risk) * pos, tag, why))
        pos = 0

    def end_pullback(outcome):
        nonlocal pbdir
        if collect and pbdir != 0:
            OUTCOMES.append((s, idx[pb_i].year, outcome))
        pbdir = 0

    for j in range(n):
        if pend is not None:
            kind, d, stop0, si, ptag = pend
            pend = None
            if kind == "exit":
                if pos != 0:
                    close_trade(j, o[j], "failure_exit")
            elif pos == 0:
                half = half_bps * c[si]
                entry = o[j] + d * half
                r = abs(entry - stop0)
                if r > 0:
                    pos, stop, risk, e_i, tag = d, stop0, r, j, ptag
                    tgt = entry + d * tp_r * r
        if pos != 0:
            if (l[j] <= stop) if pos > 0 else (h[j] >= stop):
                px = o[j] if ((o[j] < stop) if pos > 0 else (o[j] > stop)) else stop
                close_trade(j, px, "stop")
            elif (h[j] >= tgt) if pos > 0 else (l[j] <= tgt):
                px = o[j] if ((o[j] > tgt) if pos > 0 else (o[j] < tgt)) else tgt
                close_trade(j, px, "target")
            elif j - e_i >= 249:
                close_trade(j, c[j], "timeout")
        if pos != 0 and ok[j]:
            cand = c[j] - pos * 2.5 * a[j]
            stop = max(stop, cand) if pos > 0 else min(stop, cand)

        # pullback already running (from an earlier failure): cancel or trigger
        pb, pb_stop = 0, np.nan
        if pbdir != 0:
            pbAge += 1
            pbExt = min(pbExt, l[j]) if pbdir == 1 else max(pbExt, h[j])
            if not ok[j]:
                pass
            elif pbdir == 1:
                if deep is not None and c[j] < pbP - deep * a[j]:
                    end_pullback("reversal: fell > %.0f ATR" % deep)
                elif not fl[j]:
                    end_pullback("reversal: trend filter broke")
                elif (trig == "reclaim" and c[j] > pbP) or (trig == "turn" and j > 0 and c[j] > h[j - 1]):
                    pb = 1
                    pb_stop = pbExt - 0.25 * a[j] if pstop == "swing" else c[j] - 2 * a[j]
                    end_pullback("resumed: " + trig)
            else:
                if deep is not None and c[j] > pbP + deep * a[j]:
                    end_pullback("reversal: fell > %.0f ATR" % deep)
                elif not fs[j]:
                    end_pullback("reversal: trend filter broke")
                elif (trig == "reclaim" and c[j] < pbP) or (trig == "turn" and j > 0 and c[j] < l[j - 1]):
                    pb = -1
                    pb_stop = pbExt + 0.25 * a[j] if pstop == "swing" else c[j] + 2 * a[j]
                    end_pullback("resumed: " + trig)
            if pbdir != 0 and pbAge >= W2:
                end_pullback("expired")
        if pb != 0 and not ((pb_stop < c[j]) if pb > 0 else (pb_stop > c[j])):
            pb = 0

        # breakout watch: detect a failure, which starts a new pullback
        failure = 0
        if wdir != 0:
            age += 1
            if ok[j] and wdir == 1 and c[j] < P:
                failure = 1
            elif ok[j] and wdir == -1 and c[j] > P:
                failure = -1
            elif age >= W:
                wdir = 0
            if failure != 0:
                if pbdir != 0:
                    end_pullback("superseded")
                pbP, pbdir, pbAge, pb_i = P, failure, 0, j
                pbExt = l[j] if failure == 1 else h[j]
                wdir = 0
        if brkL[j] or brkS[j]:
            if pbdir != 0 and failure == 0:
                end_pullback("new breakout first")
            if brkL[j]:
                P, wdir, age = hh[j], 1, 0
            else:
                P, wdir, age = ll[j], -1, 0

        brk = 1 if brkL[j] else (-1 if brkS[j] else 0)
        if mode == "breakout":
            if pos == 0 and brk != 0:
                pend = ("enter", brk, c[j] - brk * 2 * a[j], j, "BRK")
        elif mode == "pullback":
            if pos == 0 and pb != 0:
                pend = ("enter", pb, pb_stop, j, "PB")
        else:
            if mode == "both_exit" and failure != 0 and pos == failure:
                pend = ("exit", 0, np.nan, j, "")
            elif pos == 0 and brk != 0:
                pend = ("enter", brk, c[j] - brk * 2 * a[j], j, "BRK")
            elif pos == 0 and pb != 0:
                pend = ("enter", pb, pb_stop, j, "PB")
    if pos != 0:
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
        p = g[g["tag"] == "PB"]
        out[k + " PB n"] = len(p)
        out[k + " PB expR"] = round(p["r"].mean(), 3) if len(p) else 0.0
    return out


VARIANTS = [("breakout (current)", dict(mode="breakout"))]
for mode in ("pullback", "both", "both_exit"):
    for W2 in (10, 20):
        for trig in ("reclaim", "turn"):
            for pstop in ("swing", "atr2"):
                VARIANTS.append(("%-9s W2=%-2d %-7s %s" % (mode, W2, trig, pstop),
                                 dict(mode=mode, W2=W2, trig=trig, pstop=pstop)))
VARIANTS.append(("pullback  W2=10 reclaim swing, no depth limit", dict(mode="pullback", W2=10, trig="reclaim", pstop="swing", deep=None)))
VARIANTS.append(("pullback  W2=10 turn    swing, no depth limit", dict(mode="pullback", W2=10, trig="turn", pstop="swing", deep=None)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "clean"
    if which == "stats":
        OUTCOMES.clear()
        syms = list(dict.fromkeys(F.CLEAN + Q3.WIDE))
        run(syms, mode="pullback", W2=10, trig="reclaim", pstop="swing", collect=True)
        t = pd.DataFrame(OUTCOMES, columns=["sym", "year", "outcome"])
        t["set"] = np.where(t["sym"].isin(F.CLEAN), "cash indices", "futures basket")
        print("=== after a failed breakout (close back through the level), within 10 bars ===")
        print((pd.crosstab(t["set"], t["outcome"], normalize="index") * 100).round(1).to_string())
        print(pd.crosstab(t["set"], t["outcome"]).to_string())
    else:
        syms = F.CLEAN if which == "clean" else Q3.WIDE
        print("=== %s: pullback-after-failure tests, realistic fills ===" % which.upper())
        rows = []
        for label, kw in VARIANTS:
            rows.append(row(label, run(syms, **kw)))
            print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)
        pd.DataFrame(rows).to_csv("pull_%s.csv" % which, index=False)
