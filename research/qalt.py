# -*- coding: utf-8 -*-
"""Do any of the alternative entries carry directional information?

The benchmark to beat is a driftless random walk: with a stop at 1R and a target
at XR, a coin flip wins 1/(1+X) of the time. An entry only has edge if its win
rate sits meaningfully above that line after costs.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qmulti, qbt, qrun, qsig, qsig2, qdiag
pd.set_option("display.width", 220)

CUT = "2025-09-01"
syms = qmulti.all_syms()
FN = {"bos": qsig.dow_entries, "pullback": qsig2.pullback_entries,
      "sweep": qsig2.sweep_entries, "ma_pull": qsig2.ma_pull_entries}

rows = []
for name, fn in FN.items():
    for rr in (1.0, 1.5, 2.0, 3.0):
        try:
            tr = qmulti.run(syms, zz=1.0, entry_fn=fn, rr=rr)
        except Exception as e:
            print(name, rr, "FAIL", type(e).__name__, str(e)[:80]); continue
        if len(tr) == 0:
            continue
        i, o = qrun.split(tr, CUT)
        a, b = qbt.stats(i, ""), qbt.stats(o, "")
        coin = 100.0 / (1.0 + rr)
        rows.append({"entry": name, "rr": rr,
                     "tr_n": a["n"], "tr_win%": a["win%"], "coin%": round(coin, 1),
                     "edge_pp": round(a["win%"] - coin, 1),
                     "tr_pf": a["pf"], "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                     "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"],
                     "te_expR": b["expR"]})
        print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)

print()
print("=== full table, sorted by train expectancy ===")
df = pd.DataFrame(rows).sort_values("tr_expR", ascending=False)
print(df.to_string(index=False))
