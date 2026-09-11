# -*- coding: utf-8 -*-
"""Final check on the widened universe.

The 17 added markets were listed before any of them was tested and none is
dropped afterwards. Adoption rule: the Dow version must beat the Trend Core
baseline on expectancy AND profit factor in BOTH eras, and reach 20 trades a
month in BOTH eras.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow2 as Q2
import qbt
pd.set_option("display.width", 250)

ADDED = ["BRENT", "SOYOIL", "SOYMEAL", "OATS", "RICE", "OJ", "LIVECATTLE", "FEEDERCATTLE",
         "LEANHOGS", "KCWHEAT", "HANGSENG", "STOXX50", "CAC40", "ASX200", "TSX",
         "TNOTE5", "TNOTE2"]
Q.COST_BPS.update({"BRENT": 6, "SOYOIL": 20, "SOYMEAL": 20, "OATS": 30, "RICE": 30, "OJ": 40,
                   "LIVECATTLE": 15, "FEEDERCATTLE": 20, "LEANHOGS": 20, "KCWHEAT": 20,
                   "HANGSENG": 3, "STOXX50": 2, "CAC40": 2, "ASX200": 3, "TSX": 3,
                   "TNOTE5": 1.5, "TNOTE2": 1})
WIDE = Q.UNIVERSE + ADDED

BASE = Q2.build(8)
DOW = Q2.build(8, primary=True, twoavg=True)

def show(label, tr):
    e = Q.eras(tr)
    rows = []
    for era in (x[0] for x in Q.ERAS):
        st = e[era]
        rows.append({"config": label, "era": era, "n": st.get("n", 0), "win%": st.get("win%", 0),
                     "pf": st.get("pf", 0), "expR": st.get("expR", 0), "totR": st.get("totR", 0),
                     "per_mo": st.get("trades_per_month", 0), "ddR": st.get("maxDD_R", 0)})
    return rows

if __name__ == "__main__":
    print("widened universe: %d markets" % len(WIDE))
    tb, td = Q.run(WIDE, BASE), Q.run(WIDE, DOW)
    ab, ad = Q.run(ADDED, BASE), Q.run(ADDED, DOW)
    rows = (show("baseline, 42 markets", tb) + show("DOW version, 42 markets", td)
            + show("baseline, 17 added only", ab) + show("DOW version, 17 added only", ad))
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    eb, ed = Q.eras(tb), Q.eras(td)
    verdict = True
    print()
    for era in (x[0] for x in Q.ERAS):
        b, d = eb[era], ed[era]
        ok = d["expR"] > b["expR"] and d["pf"] > b["pf"] and d["trades_per_month"] >= 20
        verdict = verdict and ok
        print("%s  expR %.4f vs %.4f | pf %.3f vs %.3f | %.1f trades/month -> %s" % (
            era, d["expR"], b["expR"], d["pf"], b["pf"], d["trades_per_month"], "pass" if ok else "FAIL"))
    print("VERDICT:", "ADOPT the Dow version" if verdict else "do not adopt")

    print()
    print("=== DOW version, whole period 2000-2026 ===")
    print(qbt.show([qbt.stats(td, "DOW 42 markets"), qbt.stats(tb, "baseline 42 markets")]))

    print()
    print("=== DOW version by year ===")
    td = td.copy()
    td["year"] = td["entry_time"].dt.year
    tb = tb.copy()
    tb["year"] = tb["entry_time"].dt.year
    yr = []
    for y in sorted(td["year"].unique()):
        a = qbt.stats(td[td["year"] == y], "")
        b = qbt.stats(tb[tb["year"] == y], "")
        yr.append({"year": y, "n": a["n"], "win%": a["win%"], "pf": a["pf"], "totR": a["totR"],
                   "base_pf": b.get("pf", 0), "base_totR": b.get("totR", 0)})
    yr = pd.DataFrame(yr)
    print(yr.to_string(index=False))
    print("positive years: DOW %d of %d, baseline %d of %d" % (
        (yr["totR"] > 0).sum(), len(yr), (yr["base_totR"] > 0).sum(), len(yr)))
    tot = yr["totR"].sum()
    print("DOW total %.1fR; without its two best years %.1fR" % (tot, tot - yr["totR"].nlargest(2).sum()))

    print()
    per = []
    for s, g in td.groupby("sym"):
        a = qbt.stats(g, s)
        per.append({"sym": s, "n": a["n"], "pf": a["pf"], "expR": a["expR"]})
    per = pd.DataFrame(per)
    print("markets with positive expectancy under the DOW version: %d of %d" % (
        (per["expR"] > 0).sum(), len(per)))
    g = td[td["sym"] == "XAUUSD"]
    print("gold alone:", {k: v for k, v in qbt.stats(g, "gold").items() if k != "label"})
    td.to_csv("trades_dow_final.csv", index=False)
