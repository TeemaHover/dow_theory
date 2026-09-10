# -*- coding: utf-8 -*-
"""Asset-class test of daily trend following.

The grouping below is decided BEFORE looking at results and follows the published
finding that time-series momentum is strong in commodities and equity indices and
weak in developed-market currency crosses. Testing a class is a single hypothesis;
picking winning tickers one by one is not.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig4, qbt, qrun, qmulti
pd.set_option("display.width", 240)

CLASS = {
 "METALS":  ["XAUUSD", "XAGUSD", "PLATINUM", "PALLADIUM", "COPPER"],
 "ENERGY":  ["WTI", "NATGAS", "HEATOIL", "GASOLINE"],
 "AGS":     ["CORN", "SOYBEAN", "WHEAT", "COFFEE", "SUGAR", "COTTON", "COCOA"],
 "EQUITY":  ["SPX500", "NAS100", "DOW30", "RUSSELL", "NIKKEI", "FTSE", "DAX"],
 "RATES":   ["TNOTE", "TBOND"],
 "FXMAJOR": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "DXY"],
 "FXCROSS": ["EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY",
             "EURAUD", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF",
             "AUDCAD", "AUDCHF", "AUDNZD", "NZDCAD", "CADCHF"],
}
CUT = "2023-09-01"
have = set(qmulti.all_syms("D1"))

_c = {}
def get(sym):
    if sym not in _c:
        d1 = qdata.load_tag(sym, "D1")
        _c[sym] = (d1, qstruct.structure(d1, qdata.atr(d1, 14), thr=1.0))
    return _c[sym]

def run(syms, nb=20, nt=100, satr=2.0, trail=3.0):
    frames = []
    for s in syms:
        if s not in have:
            continue
        try:
            work, st = get(s)
        except SystemExit:
            continue
        if len(work) < 300:
            continue
        ent, _ = qsig4.donchian_entries(work, st, n_break=nb, n_trend=nt, stop_atr=satr)
        w2 = work.copy(); w2["atr"] = st["atr"]
        tr = qbt.run(w2, ent, spread=qrun.SPREAD.get(s, 0.0), max_bars=250,
                     trail_atr=trail, atr_col="atr")
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    return pd.concat(frames, ignore_index=True).sort_values("entry_time") if frames else pd.DataFrame()

rows = []
store = {}
for cls, names in CLASS.items():
    tr = run(names)
    if len(tr) == 0:
        continue
    store[cls] = tr
    i, o = qrun.split(tr, CUT)
    a, b = qbt.stats(i, ""), qbt.stats(o, "")
    rows.append({"class": cls, "syms": len([s for s in names if s in have]),
                 "tr_n": a["n"], "tr_win%": a["win%"], "tr_pf": a["pf"], "tr_expR": a["expR"],
                 "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"], "te_expR": b["expR"],
                 "pm": a["trades_per_month"]})
print("=== daily Donchian by asset class ===")
print(pd.DataFrame(rows).to_string(index=False))

print()
print("=== yearly consistency, commodities + equity indices only ===")
sel = CLASS["METALS"] + CLASS["ENERGY"] + CLASS["AGS"] + CLASS["EQUITY"]
tr = run(sel)
if len(tr):
    tr["year"] = tr["entry_time"].dt.year
    rows = []
    for y, gg in tr.groupby("year"):
        a = qbt.stats(gg, str(y))
        rows.append({"year": y, "n": a["n"], "win%": a["win%"], "pf": a["pf"],
                     "expR": a["expR"], "totR": a["totR"]})
    print(pd.DataFrame(rows).to_string(index=False))
    i, o = qrun.split(tr, CUT)
    print()
    print(qbt.show([qbt.stats(tr, "COMMOD+EQ all"), qbt.stats(i, "train"), qbt.stats(o, "TEST")]))
    yr = pd.DataFrame(rows)
    print("positive years: %d of %d" % ((yr["totR"] > 0).sum(), len(yr)))
