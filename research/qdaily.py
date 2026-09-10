import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig4, qbt, qrun, qmulti
pd.set_option("display.width", 240)

CUT = "2023-09-01"          # daily data spans ~10y, so split later
syms = qmulti.all_syms("D1")
print("daily symbols:", " ".join(syms))

def build_d1(sym, zz=1.0, atr_n=14):
    d1 = qdata.load_tag(sym, "D1")
    a = qdata.atr(d1, atr_n)
    st = qstruct.structure(d1, a, thr=zz)
    return d1, st

_c = {}
def run(nb, nt, satr, trail, use_trend=True, maxbars=250):
    frames = []
    for s in syms:
        if s not in _c:
            try:
                _c[s] = build_d1(s)
            except SystemExit:
                continue
        work, st = _c[s]
        ent, _ = qsig4.donchian_entries(work, st, n_break=nb, n_trend=nt,
                                        stop_atr=satr, use_trend=use_trend)
        w2 = work.copy(); w2["atr"] = st["atr"]
        tr = qbt.run(w2, ent, spread=qrun.SPREAD.get(s, 0.0), max_bars=maxbars,
                     trail_atr=trail, atr_col="atr")
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    return pd.concat(frames, ignore_index=True).sort_values("entry_time") if frames else pd.DataFrame()

rows = []
for nb in (20, 40, 55):
    for trail in (2.0, 3.0, 4.0):
        tr = run(nb, 100, 2.0, trail)
        if len(tr) == 0:
            continue
        i, o = qrun.split(tr, CUT)
        a, b = qbt.stats(i, ""), qbt.stats(o, "")
        rows.append({"break": nb, "trail": trail, "tr_n": a["n"], "tr_win%": a["win%"],
                     "tr_pf": a["pf"], "tr_expR": a["expR"], "tr_pm": a["trades_per_month"],
                     "te_n": b["n"], "te_win%": b["win%"], "te_pf": b["pf"], "te_expR": b["expR"]})
        print(pd.DataFrame(rows[-1:]).to_string(index=False), flush=True)
print()
print("=== daily Donchian momentum, 17 instruments, sorted by train expectancy ===")
print(pd.DataFrame(rows).sort_values("tr_expR", ascending=False).to_string(index=False))
