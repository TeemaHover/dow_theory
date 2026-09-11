# -*- coding: utf-8 -*-
"""Which take-profit, if any, belongs in Trend Core?

Same 42 markets and Dow version as the final system. Selection rule fixed before
running: among the take-profit styles, choose the one with the best 2000-15
expectancy, then compare it with the current trail-only exit in 2016-26.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow3 as Q3
import qbt
pd.set_option("display.width", 250)

CONFIGS = [
    ("trail only (current)", {}),
    ("full TP 2R", {"tp_full_r": 2.0}),
    ("full TP 3R", {"tp_full_r": 3.0}),
    ("full TP 4R", {"tp_full_r": 4.0}),
    ("full TP 6R", {"tp_full_r": 6.0}),
    ("half at 1R, trail rest", {"tp1_r": 1.0}),
    ("half at 2R, trail rest", {"tp1_r": 2.0}),
    ("half at 3R, trail rest", {"tp1_r": 3.0}),
    ("half at 1R + breakeven", {"tp1_r": 1.0, "be_after_tp1": True}),
    ("half at 2R + breakeven", {"tp1_r": 2.0, "be_after_tp1": True}),
]

rows = []
for label, kw in CONFIGS:
    tr = Q.run(Q3.WIDE, Q3.DOW, **kw)
    e = Q.eras(tr)
    for era in (x[0] for x in Q.ERAS):
        m = ((tr["entry_time"] >= pd.Timestamp(dict((a, b) for a, b, _ in Q.ERAS)[era], tz="UTC"))
             & (tr["entry_time"] < pd.Timestamp(dict((a, c) for a, _, c in Q.ERAS)[era], tz="UTC")))
        hit = 100.0 * tr.loc[m, "tp1"].mean() if "tp1" in tr and kw.get("tp1_r") else (
            100.0 * (tr.loc[m, "reason"] == "target").mean() if kw.get("tp_full_r") else 0.0)
        st = e[era]
        rows.append({"exit style": label, "era": era, "n": st["n"], "win%": st["win%"],
                     "pf": st["pf"], "expR": st["expR"], "totR": st["totR"],
                     "ddR": st["maxDD_R"], "tp_hit%": round(hit, 1)})
    print(pd.DataFrame(rows[-2:]).to_string(index=False, header=(len(rows) == 2)), flush=True)

df = pd.DataFrame(rows)
df.to_csv("tp_tests.csv", index=False)
A = df[df["era"] == "A 2000-15"].set_index("exit style")
B = df[df["era"] == "B 2016-26"].set_index("exit style")
tp_only = A.drop(index="trail only (current)")
pick = tp_only["expR"].idxmax()
print()
print("SELECTED on 2000-15: %s  (expR %.4f, pf %.3f, win %.1f%%)" % (
    pick, A.loc[pick, "expR"], A.loc[pick, "pf"], A.loc[pick, "win%"]))
for era, T in (("2000-15", A), ("2016-26", B)):
    print("  %s  %-24s pf %.3f  expR %.4f  win %.1f%%  dd %.1fR" % (
        era, pick, T.loc[pick, "pf"], T.loc[pick, "expR"], T.loc[pick, "win%"], T.loc[pick, "ddR"]))
    t = "trail only (current)"
    print("  %s  %-24s pf %.3f  expR %.4f  win %.1f%%  dd %.1fR" % (
        era, t, T.loc[t, "pf"], T.loc[t, "expR"], T.loc[t, "win%"], T.loc[t, "ddR"]))
