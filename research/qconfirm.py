# -*- coding: utf-8 -*-
"""Final confirmation of the chosen configuration, plus the win-rate tradeoff."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig4, qbt, qrun, qmulti, qclass, qfinal
pd.set_option("display.width", 240)

CUT = "2023-09-01"
NB, TRAIL = 8, 2.5
tr = qfinal.run(NB, 100, 2.0, TRAIL)
i, o = qrun.split(tr, CUT)
print("=== CHOSEN CONFIG: break=%d, trail=%.1f ATR, stop=2.0 ATR, EMA100 filter ===" % (NB, TRAIL))
print("universe: %d instruments (commodities, indices, rates - no FX)" % len(qfinal.UNIVERSE))
print(qbt.show([qbt.stats(tr, "ALL 2016-2026"), qbt.stats(i, "train to 2023-09"),
                qbt.stats(o, "TEST 2023-09 on")]))

print()
print("=== by year ===")
tr["year"] = tr["entry_time"].dt.year
rows = []
for y, gg in tr.groupby("year"):
    a = qbt.stats(gg, str(y))
    rows.append({"year": y, "n": a["n"], "win%": a["win%"], "pf": a["pf"],
                 "expR": a["expR"], "totR": a["totR"]})
yr = pd.DataFrame(rows)
print(yr.to_string(index=False))
print("positive years: %d of %d" % ((yr["totR"] > 0).sum(), len(yr)))
tot = yr["totR"].sum()
best2 = yr.nlargest(2, "totR")["totR"].sum()
print("total %.1fR; excluding the two best years %.1fR" % (tot, tot - best2))

print()
print("=== per instrument ===")
rows = []
for s, gg in tr.groupby("sym"):
    a = qbt.stats(gg, s)
    rows.append({"sym": s, "n": a["n"], "per_month": a["trades_per_month"],
                 "win%": a["win%"], "pf": a["pf"], "expR": a["expR"], "totR": a["totR"]})
df = pd.DataFrame(rows).sort_values("expR", ascending=False)
print(df.to_string(index=False))
print("positive instruments: %d of %d" % ((df["expR"] > 0).sum(), len(df)))

print()
print("=== the win-rate dial: same entries, fixed targets instead of a trail ===")
rows = []
for rr in (0.5, 1.0, 1.5, 2.0, 3.0):
    frames = []
    for s in qfinal.UNIVERSE:
        try:
            work, st = qfinal.get(s)
        except SystemExit:
            continue
        if len(work) < 300:
            continue
        ent, _ = qsig4.donchian_entries(work, st, n_break=NB, n_trend=100, stop_atr=2.0)
        e = ent.copy()
        c = work["close"].to_numpy(float)
        risk = np.abs(c - e["stop"].to_numpy(float))
        d = e["dir"].to_numpy(int)
        e["target"] = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
        w2 = work.copy(); w2["atr"] = st["atr"]
        t = qbt.run(w2, e, spread=qrun.SPREAD.get(s, 0.0), max_bars=250)
        if len(t):
            frames.append(t)
    t = pd.concat(frames, ignore_index=True)
    a = qbt.stats(t, "")
    rows.append({"fixed_target": "%.1fR" % rr, "n": a["n"], "win%": a["win%"],
                 "pf": a["pf"], "expR": a["expR"], "totR": a["totR"]})
    print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)
print()
print(pd.DataFrame(rows).to_string(index=False))
tr.to_csv("trades_final.csv", index=False)
print()
print("trades written to trades_final.csv")
