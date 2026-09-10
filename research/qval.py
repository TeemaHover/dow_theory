# -*- coding: utf-8 -*-
"""Is the daily momentum result real, or a few instruments carrying the rest?"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig4, qbt, qrun, qmulti
pd.set_option("display.width", 240)

CUT = sys.argv[1] if len(sys.argv) > 1 else "2023-09-01"
syms = qmulti.all_syms("D1")
print("instruments: %d" % len(syms))

_c = {}
def get(sym):
    if sym not in _c:
        d1 = qdata.load_tag(sym, "D1")
        _c[sym] = (d1, qstruct.structure(d1, qdata.atr(d1, 14), thr=1.0))
    return _c[sym]

def run(nb=20, nt=100, satr=2.0, trail=3.0, use_trend=True, spread_mult=1.0):
    frames = []
    for s in syms:
        try:
            work, st = get(s)
        except SystemExit:
            continue
        if len(work) < 300:
            continue
        ent, _ = qsig4.donchian_entries(work, st, n_break=nb, n_trend=nt,
                                        stop_atr=satr, use_trend=use_trend)
        w2 = work.copy(); w2["atr"] = st["atr"]
        tr = qbt.run(w2, ent, spread=qrun.SPREAD.get(s, 0.0) * spread_mult,
                     max_bars=250, trail_atr=trail, atr_col="atr")
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    return pd.concat(frames, ignore_index=True).sort_values("entry_time") if frames else pd.DataFrame()

tr = run()
i, o = qrun.split(tr, CUT)
print(qbt.show([qbt.stats(tr, "ALL"), qbt.stats(i, "train"), qbt.stats(o, "TEST")]))

print()
print("=== per instrument (full sample) ===")
rows = []
for s, gg in tr.groupby("sym"):
    a = qbt.stats(gg, s)
    rows.append({"sym": s, "n": a["n"], "win%": a["win%"], "pf": a["pf"],
                 "expR": a["expR"], "totR": a["totR"]})
df = pd.DataFrame(rows).sort_values("expR", ascending=False)
print(df.to_string(index=False))
pos = (df["expR"] > 0).sum()
print("instruments with positive expectancy: %d of %d (%.0f%%)" % (pos, len(df), 100.0*pos/len(df)))

print()
print("=== by calendar year (pooled) ===")
tr["year"] = tr["entry_time"].dt.year
rows = []
for y, gg in tr.groupby("year"):
    a = qbt.stats(gg, str(y))
    rows.append({"year": y, "n": a["n"], "win%": a["win%"], "pf": a["pf"],
                 "expR": a["expR"], "totR": a["totR"]})
print(pd.DataFrame(rows).to_string(index=False))

print()
print("=== robustness: does it survive worse assumptions? ===")
rows = []
for label, kw in (("baseline", {}),
                  ("no trend filter", {"use_trend": False}),
                  ("stop 1.5 ATR", {"satr": 1.5}),
                  ("stop 3 ATR", {"satr": 3.0}),
                  ("trail 2.5", {"trail": 2.5}),
                  ("trail 4", {"trail": 4.0}),
                  ("break 15", {"nb": 15}),
                  ("break 30", {"nb": 30}),
                  ("trend ema 50", {"nt": 50}),
                  ("trend ema 200", {"nt": 200}),
                  ("3x spread", {"spread_mult": 3.0}),
                  ("10x spread", {"spread_mult": 10.0})):
    t = run(**kw)
    if len(t) == 0:
        continue
    ii, oo = qrun.split(t, CUT)
    a, b = qbt.stats(ii, ""), qbt.stats(oo, "")
    rows.append({"variant": label, "tr_n": a["n"], "tr_pf": a["pf"], "tr_expR": a["expR"],
                 "te_n": b["n"], "te_pf": b["pf"], "te_expR": b["expR"],
                 "pm": a["trades_per_month"]})
print(pd.DataFrame(rows).to_string(index=False))
