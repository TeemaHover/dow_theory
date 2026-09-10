# -*- coding: utf-8 -*-
"""Pick a configuration on TRAIN that clears 20 trades a month, then look at TEST once."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig4, qbt, qrun, qmulti, qclass
pd.set_option("display.width", 240)

CUT = "2023-09-01"
UNIVERSE = (qclass.CLASS["METALS"] + qclass.CLASS["ENERGY"] + qclass.CLASS["AGS"]
            + qclass.CLASS["EQUITY"] + qclass.CLASS["RATES"])
have = set(qmulti.all_syms("D1"))
UNIVERSE = [s for s in UNIVERSE if s in have]
print("universe: %d instruments" % len(UNIVERSE))

_c = {}
def get(sym):
    if sym not in _c:
        d1 = qdata.load_tag(sym, "D1")
        _c[sym] = (d1, qstruct.structure(d1, qdata.atr(d1, 14), thr=1.0))
    return _c[sym]

def run(nb, nt, satr, trail, spread_mult=1.0):
    frames = []
    for s in UNIVERSE:
        try:
            work, st = get(s)
        except SystemExit:
            continue
        if len(work) < 300:
            continue
        ent, _ = qsig4.donchian_entries(work, st, n_break=nb, n_trend=nt, stop_atr=satr)
        w2 = work.copy(); w2["atr"] = st["atr"]
        tr = qbt.run(w2, ent, spread=qrun.SPREAD.get(s, 0.0) * spread_mult,
                     max_bars=250, trail_atr=trail, atr_col="atr")
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    return pd.concat(frames, ignore_index=True).sort_values("entry_time") if frames else pd.DataFrame()

rows = []
for nb in (8, 10, 12, 15, 20):
    for trail in (2.5, 3.0, 3.5):
        tr = run(nb, 100, 2.0, trail)
        if len(tr) == 0:
            continue
        i, o = qrun.split(tr, CUT)
        a, b = qbt.stats(i, ""), qbt.stats(o, "")
        rows.append({"break": nb, "trail": trail, "tr_n": a["n"], "tr_win%": a["win%"],
                     "tr_pf": a["pf"], "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                     "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"], "te_expR": b["expR"]})
        print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)

df = pd.DataFrame(rows)
print()
print("=== configurations reaching 20+ trades/month, ranked by TRAIN expectancy ===")
ok = df[df["tr_pm"] >= 20].sort_values("tr_expR", ascending=False)
print(ok.to_string(index=False) if len(ok) else "none reach 20/month on this universe")
df.to_csv("final_sweep.csv", index=False)
