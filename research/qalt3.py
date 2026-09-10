import sys
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qmulti, qbt, qrun, qsig, qsig2, qsig3
pd.set_option("display.width", 240)
CUT = "2025-09-01"
syms = qmulti.all_syms()
rows = []

def go(label, fn, rr, spread=None, **kw):
    tr = qmulti.run(syms, zz=1.0, entry_fn=fn, rr=rr, with_features=False,
                    spread_override=spread, **kw)
    if len(tr) == 0:
        print(label, "no trades"); return
    i, o = qrun.split(tr, CUT)
    a, b = qbt.stats(i, ""), qbt.stats(o, "")
    coin = 100.0 / (1.0 + rr)
    rows.append({"strategy": label, "rr": rr, "tr_n": a["n"], "tr_win%": a["win%"],
                 "coin%": round(coin, 1), "edge_pp": round(a["win%"] - coin, 1),
                 "tr_pf": a["pf"], "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                 "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"], "te_expR": b["expR"]})
    print(pd.DataFrame(rows[-1:]).to_string(index=False), flush=True)

# control: same entries, zero transaction cost
go("bos ZERO-COST", qsig.dow_entries, 2.0, spread=0.0)
go("sweep ZERO-COST", qsig2.sweep_entries, 2.0, spread=0.0)
# hypotheses with better priors
for k in (1.5, 2.0, 2.5):
    go("meanrev k=%.1f" % k, qsig3.meanrev_entries, 1.5, k=k)
go("meanrev k=2.0 rr1", qsig3.meanrev_entries, 1.0, k=2.0)
go("orb London", qsig3.orb_entries, 2.0)
go("orb London rr1", qsig3.orb_entries, 1.0)
print()
print(pd.DataFrame(rows).sort_values("tr_expR", ascending=False).to_string(index=False))
