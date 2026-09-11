# -*- coding: utf-8 -*-
"""Stage two: turn the passing Dow elements into one system without breaking the
20-trades-a-month floor.

Selection rule, fixed before running: among configurations that reach 20 trades a
month in era A, take the one with the best era-A expectancy. It is adopted only if,
in era B, it beats the Trend Core baseline on both expectancy and profit factor and
still reaches 20 trades a month.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qbt
from qsig2 import ema
pd.set_option("display.width", 250)


def m_primary(df):
    c = df["close"].to_numpy(float)
    m = pd.Series(c).rolling(250, min_periods=250).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        return c > m, c < m


def m_struct(s):
    st = Q.cstruct(s, 3.0)["state"].to_numpy()
    return st >= 0, st <= 0


def m_twoavg(df):
    conf = []
    for avg in ("DJI", "DJT"):
        adf, _ = Q.prep(avg)
        val = Q.cstruct(avg, 3.0)["state"].to_numpy(float)
        conf.append(Q.lagged(val, adf.index, df.index))
    return (conf[0] == 1) & (conf[1] == 1), (conf[0] == -1) & (conf[1] == -1)


def build(nb, primary=False, struct=False, twoavg=False):
    def f(s, df, atr):
        fl = np.ones(len(df), bool)
        fs = np.ones(len(df), bool)
        if primary:
            a, b = m_primary(df); fl &= a; fs &= b
        if struct:
            a, b = m_struct(s); fl &= a; fs &= b
        if twoavg and s in Q.US_EQ:
            a, b = m_twoavg(df); fl &= a; fs &= b
        return Q.tc(df, atr, nb=nb, fl=fl, fs=fs)
    return f


def line(label, tr):
    e = Q.eras(tr)
    out = []
    for era in (x[0] for x in Q.ERAS):
        st = e[era]
        out.append({"config": label, "era": era, "n": st.get("n", 0), "win%": st.get("win%", 0),
                    "pf": st.get("pf", 0), "expR": st.get("expR", 0), "totR": st.get("totR", 0),
                    "per_mo": st.get("trades_per_month", 0), "ddR": st.get("maxDD_R", 0)})
    return out


if __name__ == "__main__":
    U = Q.UNIVERSE
    rows = []
    cfgs = [("baseline nb8", build(8))]
    for nb in (8, 7, 6, 5):
        cfgs.append(("primary nb%d" % nb, build(nb, primary=True)))
    for nb in (8, 7, 6, 5):
        cfgs.append(("primary+DJI/DJT nb%d" % nb, build(nb, primary=True, twoavg=True)))
    cfgs.append(("primary+troughs nb8", build(8, primary=True, struct=True)))
    cfgs.append(("baseline nb5 (control)", build(5)))

    results = {}
    for label, b in cfgs:
        tr = Q.run(U, b)
        results[label] = tr
        rows += line(label, tr)
        print(pd.DataFrame(rows[-2:]).to_string(index=False, header=(len(rows) == 2)), flush=True)

    df = pd.DataFrame(rows)
    A = df[df["era"] == "A 2000-15"].set_index("config")
    B = df[df["era"] == "B 2016-26"].set_index("config")
    base_a, base_b = A.loc["baseline nb8"], B.loc["baseline nb8"]

    print()
    cand = A[(A["per_mo"] >= 20) & (A.index != "baseline nb8") & (~A.index.str.contains("control"))]
    if len(cand) == 0:
        print("SELECTION: nothing with a filter reaches 20 trades/month in era A")
    else:
        pick = cand["expR"].idxmax()
        ok = (B.loc[pick, "expR"] > base_b["expR"] and B.loc[pick, "pf"] > base_b["pf"]
              and B.loc[pick, "per_mo"] >= 20)
        print("SELECTION on era A: %s  (A expR %.4f vs base %.4f)" % (
            pick, A.loc[pick, "expR"], base_a["expR"]))
        print("CONFIRMATION in era B: expR %.4f vs %.4f, pf %.3f vs %.3f, %.1f/month -> %s" % (
            B.loc[pick, "expR"], base_b["expR"], B.loc[pick, "pf"], base_b["pf"],
            B.loc[pick, "per_mo"], "ADOPT" if ok else "REJECT"))

    print()
    print("=== primary-trend filter by asset class (nb8), expectancy per trade ===")
    base = results["baseline nb8"]
    prim = results["primary nb8"]
    out = []
    for cls, syms in Q.CLASSES.items():
        for era, a, b in Q.ERAS:
            def pick_(tr):
                m = (tr["sym"].isin(syms) & (tr["entry_time"] >= pd.Timestamp(a, tz="UTC"))
                     & (tr["entry_time"] < pd.Timestamp(b, tz="UTC")))
                return qbt.stats(tr[m], "")
            x, y = pick_(base), pick_(prim)
            out.append({"class": cls, "era": era, "base_n": x.get("n", 0), "base_expR": x.get("expR", 0),
                        "prim_n": y.get("n", 0), "prim_expR": y.get("expR", 0)})
    print(pd.DataFrame(out).to_string(index=False))

    print()
    print("=== two averages on US index futures, trade by trade ===")
    tr = results["primary+DJI/DJT nb8"]
    us = tr[tr["sym"].isin(Q.US_EQ)]
    bs = base[base["sym"].isin(Q.US_EQ)]
    for era, a, b in Q.ERAS:
        mu = (us["entry_time"] >= pd.Timestamp(a, tz="UTC")) & (us["entry_time"] < pd.Timestamp(b, tz="UTC"))
        mb = (bs["entry_time"] >= pd.Timestamp(a, tz="UTC")) & (bs["entry_time"] < pd.Timestamp(b, tz="UTC"))
        print(era, "baseline:", qbt.stats(bs[mb], "")), print(era, "with DJI/DJT:", qbt.stats(us[mu], ""))
    df.to_csv("dow_stage2.csv", index=False)
