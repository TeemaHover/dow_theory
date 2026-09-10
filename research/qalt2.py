import sys
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qmulti, qbt, qrun, qsig2
pd.set_option("display.width", 220)
CUT = "2025-09-01"
syms = qmulti.all_syms()
rows = []
for name, fn in (("sweep", qsig2.sweep_entries), ("ma_pull", qsig2.ma_pull_entries)):
    for rr in (1.0, 1.5, 2.0, 3.0):
        tr = qmulti.run(syms, zz=1.0, entry_fn=fn, rr=rr, with_features=False)
        if len(tr) == 0:
            print(name, rr, "no trades"); continue
        i, o = qrun.split(tr, CUT)
        a, b = qbt.stats(i, ""), qbt.stats(o, "")
        coin = 100.0 / (1.0 + rr)
        rows.append({"entry": name, "rr": rr, "tr_n": a["n"], "tr_win%": a["win%"],
                     "coin%": round(coin, 1), "edge_pp": round(a["win%"] - coin, 1),
                     "tr_pf": a["pf"], "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                     "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"], "te_expR": b["expR"]})
        print(pd.DataFrame(rows[-1:]).to_string(index=False), flush=True)
print()
print(pd.DataFrame(rows).sort_values("tr_expR", ascending=False).to_string(index=False))
