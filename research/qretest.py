# -*- coding: utf-8 -*-
"""Retest entries for Trend Core, measured against the breakout entry.

Retest rule, fixed before running:
  * a breakout bar (the normal Trend Core signal, filters included) arms a retest
    at the broken level: the prior 8-bar high for longs, low for shorts;
  * within W bars, a bar that comes back to within tol x ATR of the level AND
    closes on the breakout side of it, with the filters still passing, is the entry;
  * a close back through the level cancels it (the breakout failed), and so does
    running out of bars; a newer breakout re-arms at its own level.
Stops: "atr2" is Trend Core's 2 x ATR from the entry close; "level" is 1 x ATR
beyond the retested level. Trailing stop, costs and gap fills as in qfidelity.

Decision data is the clean set: cash stock indices, which have no contract rolls.
Adoption rule, fixed before running: a variant replaces the breakout default only
if it beats it on BOTH expectancy and total R in BOTH eras on the clean set.
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
pd.set_option("display.width", 250)

CLEAN = ["NIKKEI", "FTSE", "DAX", "HANGSENG", "CAC40", "ASX200", "TSX", "STOXX50", "DJI", "DJT"]
Q.COST_BPS.update({"DJI": 2, "DJT": 3})

STATS = []   # retest statistics gathered while building signals


def build(mode="breakout", W=10, tol=0.5, stop_mode="atr2", nb=8, collect=False):
    def f(s, df, atr):
        h = df["high"].to_numpy(float)
        l = df["low"].to_numpy(float)
        c = df["close"].to_numpy(float)
        a = atr.to_numpy(float)
        n = len(c)
        hh = pd.Series(h).rolling(nb, min_periods=nb).max().shift(1).to_numpy()
        ll = pd.Series(l).rolling(nb, min_periods=nb).min().shift(1).to_numpy()
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

        d = np.zeros(n, int)
        stop = np.full(n, np.nan)
        tag = np.array([""] * n, dtype=object)
        if mode in ("breakout", "both"):
            d[brkL] = 1
            stop[brkL] = c[brkL] - 2.0 * a[brkL]
            d[brkS] = -1
            stop[brkS] = c[brkS] + 2.0 * a[brkS]
            tag[brkL | brkS] = "BRK"

        if mode in ("retest", "both"):
            P, pdir, age, arm_i = np.nan, 0, 0, -1
            for j in range(n):
                if pdir != 0:
                    age += 1
                    outcome = None
                    if pdir == 1:
                        if c[j] < P:
                            outcome = "failed"
                        elif l[j] <= P + tol * a[j] and c[j] > P and fl[j] and ok[j]:
                            outcome = "retest_entry"
                            if d[j] == 0:
                                d[j] = 1
                                stop[j] = c[j] - 2.0 * a[j] if stop_mode == "atr2" else P - 1.0 * a[j]
                                tag[j] = "RT"
                    else:
                        if c[j] > P:
                            outcome = "failed"
                        elif h[j] >= P - tol * a[j] and c[j] < P and fs[j] and ok[j]:
                            outcome = "retest_entry"
                            if d[j] == 0:
                                d[j] = -1
                                stop[j] = c[j] + 2.0 * a[j] if stop_mode == "atr2" else P + 1.0 * a[j]
                                tag[j] = "RT"
                    if outcome is None and age >= W:
                        outcome = "no_retest"
                    if outcome is not None:
                        if collect:
                            STATS.append((s, df.index[arm_i].year, outcome))
                        pdir = 0
                if brkL[j]:
                    if pdir != 0 and collect:
                        STATS.append((s, df.index[arm_i].year, "superseded"))
                    P, pdir, age, arm_i = hh[j], 1, 0, j
                elif brkS[j]:
                    if pdir != 0 and collect:
                        STATS.append((s, df.index[arm_i].year, "superseded"))
                    P, pdir, age, arm_i = ll[j], -1, 0, j

        with np.errstate(invalid="ignore"):
            valid = (d != 0) & np.isfinite(stop) & (((d > 0) & (stop < c)) | ((d < 0) & (stop > c)))
        d = np.where(valid, d, 0)
        stop = np.where(valid, stop, np.nan)
        target = np.where(d > 0, c + 100 * a, np.where(d < 0, c - 100 * a, np.nan))
        return pd.DataFrame({"dir": d, "stop": stop, "target": target,
                             "tag": np.where(d != 0, tag, "")}, index=df.index)
    return f


def eras_row(label, tr, extra=None):
    out = {"variant": label}
    for name, a, b in Q.ERAS:
        m = ((tr["entry_time"] >= pd.Timestamp(a, tz="UTC"))
             & (tr["entry_time"] < pd.Timestamp(b, tz="UTC")))
        st = qbt.stats(tr[m], name) if len(tr) else {"n": 0}
        years = (pd.Timestamp(min(b, "2026-09-14")) - pd.Timestamp(max(a, "2000-01-01"))).days / 365.25
        tag = name.split()[0]
        out[tag + " n"] = st.get("n", 0)
        out[tag + " win%"] = st.get("win%", 0)
        out[tag + " PF"] = st.get("pf", 0)
        out[tag + " expR"] = st.get("expR", 0)
        out[tag + " R/yr"] = round(st.get("totR", 0) / years, 1)
        out[tag + " ddR"] = st.get("maxDD_R", 0)
    if extra:
        out.update(extra)
    return out


VARIANTS = [("breakout (current)", dict(mode="breakout"))]
for W in (5, 10):
    for tol in (0.25, 0.5):
        for sm in ("atr2", "level"):
            VARIANTS.append(("retest W%d tol%.2f %s" % (W, tol, sm), dict(mode="retest", W=W, tol=tol, stop_mode=sm)))
            VARIANTS.append(("both   W%d tol%.2f %s" % (W, tol, sm), dict(mode="both", W=W, tol=tol, stop_mode=sm)))

ENGINE = dict(gap_fills=True, reenter_on_exit_bar=True, tp_full_r=6.0)


def run_set(syms, title):
    rows = []
    for label, kw in VARIANTS:
        tr = Q.run(syms, build(**kw), **ENGINE)
        share = {}
        if len(tr) and "tag" in tr:
            share["retest share %"] = round(100 * (tr["tag"] == "RT").mean(), 0)
        rows.append(eras_row(label, tr, share))
        print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("retest_%s.csv" % title.split()[0].lower(), index=False)
    return df


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "clean"
    if which == "stats":
        STATS.clear()
        Q.run(list(dict.fromkeys(CLEAN + Q3.WIDE)), build(mode="retest", W=10, tol=0.5, collect=True), **ENGINE)
        t = pd.DataFrame(STATS, columns=["sym", "year", "outcome"])
        t["set"] = np.where(t["sym"].isin(CLEAN), "cash indices", "futures basket")
        print("=== what happens after a Trend Core breakout (within 10 daily bars, 0.5 ATR band) ===")
        print((pd.crosstab(t["set"], t["outcome"], normalize="index") * 100).round(1).to_string())
        print(pd.crosstab(t["set"], t["outcome"]).to_string())
    elif which == "clean":
        print("=== CLEAN: cash stock indices, realistic fills, TP 6R ===")
        run_set(CLEAN, "clean")
    else:
        print("=== BASKET: 42 markets (futures data has roll jumps; secondary) ===")
        run_set(Q3.WIDE, "basket")
