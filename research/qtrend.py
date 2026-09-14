# -*- coding: utf-8 -*-
"""Should a pullback watch end as a REVERSAL when the close crosses the trend filter?

Prompted by a chart where the label said REVERSAL because a bounce closed a hair past
the 100 EMA, and price then resumed. Rules compared, fixed before running:
  close     any close past the EMA100 / SMA250 ends the watch as a reversal (current)
  none      only a close more than 2 ATR beyond the level is a reversal; a close past
            the averages just pauses the entry until they pass again
  margin    the close must be at least 0.5 or 1.0 ATR past the EMA or SMA
Two measurements:
  labels    hindsight over the next 20 bars: a REVERSAL is wrong if price closes back
            beyond the level in the original direction; a RESUMED is wrong if price
            closes more than 2 ATR on the other side of the level
  trading   Breakout + Pullback (reclaim trigger, 2 x ATR stop, 10-bar window)
Adoption, fixed before running: fewer wrong REVERSAL labels without more wrong RESUMED
labels, and trading at least as good as the current rule in both eras on the clean set.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow3 as Q3
import qpull as PB
import qfail as F
pd.set_option("display.width", 250)

RULES = [("current: any close past EMA/SMA", dict(trend_cancel="close")),
         ("2 ATR only", dict(trend_cancel="none")),
         ("past the averages by 0.5 ATR", dict(trend_cancel="margin", margin=0.5)),
         ("past the averages by 1.0 ATR", dict(trend_cancel="margin", margin=1.0))]
H = 20


def labels(s, trend_cancel="close", margin=0.0, W=10, W2=10, deep=2.0):
    idx, o, h, l, c, a, hh, ll, fl, fs, ok, brkL, brkS = F.arrays(s)
    n = len(c)
    e100 = F.ema(c, 100)
    s250 = pd.Series(c).rolling(250, min_periods=250).mean().to_numpy()
    out = []
    P, wdir, age = np.nan, 0, 0
    pbP, pbdir, pbAge = np.nan, 0, 0
    for j in range(n):
        if pbdir != 0:
            pbAge += 1
            if ok[j]:
                filt = fl[j] if pbdir == 1 else fs[j]
                deep_hit = (c[j] < pbP - deep * a[j]) if pbdir == 1 else (c[j] > pbP + deep * a[j])
                if np.isfinite(s250[j]):
                    br = (max(e100[j] - c[j], s250[j] - c[j]) if pbdir == 1 else max(c[j] - e100[j], c[j] - s250[j])) / a[j]
                else:
                    br = 0.0
                broken = (not filt) and (trend_cancel == "close" or (trend_cancel == "margin" and br >= margin))
                if deep_hit or broken:
                    out.append((j, pbdir, pbP, "REVERSAL")); pbdir = 0
                elif filt and ((c[j] > pbP) if pbdir == 1 else (c[j] < pbP)):
                    out.append((j, pbdir, pbP, "RESUMED")); pbdir = 0
            if pbdir != 0 and pbAge >= W2:
                out.append((j, pbdir, pbP, "undecided")); pbdir = 0
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
                pbP, pbdir, pbAge = P, failure, 0
                wdir = 0
        if brkL[j] or brkS[j]:
            if pbdir != 0 and failure == 0:
                pbdir = 0
            P, wdir, age = (hh[j], 1, 0) if brkL[j] else (ll[j], -1, 0)
    rows = []
    for j, d, lvl, what in out:
        if j + H >= n:
            continue
        seg = c[j + 1:j + 1 + H]
        if what == "REVERSAL":
            wrong = bool(np.any(seg > lvl)) if d == 1 else bool(np.any(seg < lvl))
        elif what == "RESUMED":
            wrong = bool(np.any(seg < lvl - 2 * a[j])) if d == 1 else bool(np.any(seg > lvl + 2 * a[j]))
        else:
            wrong = False
        rows.append((s, idx[j], what, wrong))
    return rows


def label_table(syms, title):
    res = []
    for name, kw in RULES:
        rows = []
        for s in syms:
            try:
                rows += labels(s, **kw)
            except SystemExit:
                continue
        t = pd.DataFrame(rows, columns=["sym", "t", "what", "wrong"])
        rev, rsm = t[t.what == "REVERSAL"], t[t.what == "RESUMED"]
        res.append({"rule": name, "REVERSAL": len(rev), "REVERSAL wrong %": round(100 * rev.wrong.mean(), 1),
                    "RESUMED": len(rsm), "RESUMED wrong %": round(100 * rsm.wrong.mean(), 1),
                    "undecided": int((t.what == "undecided").sum())})
    print("=== %s: label accuracy, hindsight %d bars ===" % (title, H))
    print(pd.DataFrame(res).to_string(index=False), flush=True)


def trade_table(syms, title):
    res = [PB.row("breakout (reference)", PB.run(syms, mode="breakout"))]
    for name, kw in RULES:
        res.append(PB.row("B+P, " + name, PB.run(syms, mode="both", W2=10, trig="reclaim", pstop="atr2", **kw)))
    cols = ["variant", "A n", "A PF", "A expR", "A R/yr", "A PB n", "A PB expR", "B n", "B PF", "B expR", "B R/yr", "B PB n", "B PB expR"]
    print("=== %s: Breakout + Pullback trading ===" % title)
    print(pd.DataFrame(res)[cols].to_string(index=False), flush=True)


if __name__ == "__main__":
    for syms, title in ((F.CLEAN, "CLEAN cash indices"), (Q3.WIDE, "BASKET 42 markets")):
        label_table(syms, title)
        trade_table(syms, title)
        print()
