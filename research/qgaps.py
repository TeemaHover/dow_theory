# -*- coding: utf-8 -*-
"""Where does the gap-fill loss come from: real overnight gaps, or roll jumps in
unadjusted continuous futures?

Cash indices have no contract rolls, so their gaps are all real. Trades align one
for one between the two runs: the stop is hit on the same bar either way and only
the fill price changes.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow3 as Q3
import qbt
pd.set_option("display.width", 250)

CASH = ["NIKKEI", "FTSE", "DAX", "HANGSENG", "CAC40", "ASX200", "TSX", "STOXX50"]
CLASS_OF = {}
for cls, syms in Q.CLASSES.items():
    for s in syms:
        CLASS_OF[s] = cls
for s in ("BRENT",):
    CLASS_OF[s] = "energy"
for s in ("SOYOIL", "SOYMEAL", "OATS", "RICE", "OJ", "LIVECATTLE", "FEEDERCATTLE", "LEANHOGS", "KCWHEAT"):
    CLASS_OF[s] = "ags"
for s in ("HANGSENG", "STOXX50", "CAC40", "ASX200", "TSX"):
    CLASS_OF[s] = "equity"
for s in ("TNOTE5", "TNOTE2"):
    CLASS_OF[s] = "rates"

base = Q.run(Q3.WIDE, Q3.DOW)
gap = Q.run(Q3.WIDE, Q3.DOW, gap_fills=True)
key = ["sym", "entry_time"]
m = base.merge(gap[key + ["r", "exit"]], on=key, suffixes=("", "_gap"))
assert len(m) == len(base) == len(gap), (len(m), len(base), len(gap))
m["slip"] = m["r_gap"] - m["r"]
m["gapped"] = m["slip"] < -1e-9
m["kind"] = np.where(m["sym"].isin(CASH), "cash index", "futures")
m["cls"] = m["sym"].map(CLASS_OF)

def summarize(g):
    wb, lb = g.loc[g.r > 0, "r"].sum(), -g.loc[g.r < 0, "r"].sum()
    wg, lg = g.loc[g.r_gap > 0, "r_gap"].sum(), -g.loc[g.r_gap < 0, "r_gap"].sum()
    return pd.Series({"trades": len(g), "PF published": round(wb / lb, 3), "PF gap fills": round(wg / lg, 3),
                      "exits gapped %": round(100 * g.gapped.mean(), 1),
                      "avg slippage when gapped (R)": round(g.loc[g.gapped, "slip"].mean(), 2) if g.gapped.any() else 0.0,
                      "edge lost per trade (R)": round(g.slip.mean(), 3)})

print("=== by market type ===")
print(m.groupby("kind").apply(summarize, include_groups=False).to_string())
print()
print("=== by asset class ===")
print(m.groupby("cls").apply(summarize, include_groups=False).to_string())
print()
print("=== cash indices, one by one ===")
print(m[m.kind == "cash index"].groupby("sym").apply(summarize, include_groups=False).to_string())
print()
entry_gap = (m["reason"] == "stop") & (m["bars"] == 0) & (m["r"] > 0)
print("trades stopped out on their entry bar at a PROFIT in the published engine (opened beyond their own stop): %d" % int(entry_gap.sum()))
