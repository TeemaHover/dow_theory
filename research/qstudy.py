# -*- coding: utf-8 -*-
"""Diagnosis on the pooled TRAIN set: what separates winners from losers."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qmulti, qbt, qdiag, qrun, qsig
pd.set_option("display.width", 200)

CUT = "2025-09-01"
syms = qmulti.all_syms()

print("### reward-to-risk sweep, pooled over %d instruments (train only)" % len(syms))
rows = []
for rr in (1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0):
    tr = qmulti.run(syms, rr=rr, zz=1.0)
    i, o = qrun.split(tr, CUT)
    a, b = qbt.stats(i, "rr=%.0f" % rr), qbt.stats(o, "")
    rows.append({"rr": rr, "tr_n": a["n"], "tr_win%": a["win%"], "tr_pf": a["pf"],
                 "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                 "te_n": b["n"], "te_pf": b["pf"], "te_expR": b["expR"]})
print(pd.DataFrame(rows).to_string(index=False))

print()
print("### swing-threshold sweep, pooled (train only)")
rows = []
for zz in (0.5, 0.75, 1.0, 1.5, 2.0):
    tr = qmulti.run(syms, rr=2.0, zz=zz)
    i, o = qrun.split(tr, CUT)
    a, b = qbt.stats(i, ""), qbt.stats(o, "")
    rows.append({"zz": zz, "tr_n": a["n"], "tr_win%": a["win%"], "tr_pf": a["pf"],
                 "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                 "te_n": b["n"], "te_pf": b["pf"], "te_expR": b["expR"]})
print(pd.DataFrame(rows).to_string(index=False))

print()
print("### context scan on pooled TRAIN losers/winners (rr=2, zz=1.0)")
tr = qmulti.run(syms, rr=2.0, zz=1.0)
i, o = qrun.split(tr, CUT)
print(qdiag.scan(i, min_n=200, top=14).to_string(index=False))

print()
print("### exit reasons (train)")
print(qdiag.exits(i).to_string())

print()
for col in ("f_aligned", "f_state", "f_hour"):
    t = qdiag.bucket(i, col, q=6, min_n=200) if col != "f_aligned" else qdiag.by_flag(i, col)
    if t is not None:
        print("--- %s ---" % col)
        print(t.to_string())
        print()

print("### how far trades run (train)")
print(qdiag.mfe_study(i).to_string(index=False))
