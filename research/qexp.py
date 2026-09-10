# -*- coding: utf-8 -*-
"""Ablations and sweeps. Tuning reads TRAIN only; TEST is printed but not chased."""
import sys, itertools
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig, qbt, qdiag, qrun

_cache = {}
def build(sym, tf, htf, zz, atr_n=14):
    k = (sym, tf, htf, zz, atr_n)
    if k not in _cache:
        _cache[k] = qrun.build(sym, tf, htf, atr_n, zz)
    return _cache[k]

def trial(sym, tf="1h", htf="4h", zz=1.0, cut="2025-09-01", **kw):
    work, st, hs = build(sym, tf, htf, zz)
    ent, g = qsig.dow_entries(work, st, hs, **kw)
    feats = qsig.context(work, st, hs)
    tr = qbt.run(work, ent, spread=qrun.SPREAD.get(sym, 0.0), features=feats)
    tr_in, tr_out = qrun.split(tr, cut)
    return tr, tr_in, tr_out, g

def row(label, tr_in, tr_out):
    a = qbt.stats(tr_in, label)
    b = qbt.stats(tr_out, "")
    return {"config": label,
            "tr_n": a.get("n", 0), "tr_pf": a.get("pf", 0), "tr_expR": a.get("expR", 0),
            "tr_win%": a.get("win%", 0), "tr_pm": a.get("trades_per_month", 0),
            "te_n": b.get("n", 0), "te_pf": b.get("pf", 0), "te_expR": b.get("expR", 0),
            "te_win%": b.get("win%", 0)}

if __name__ == "__main__":
    sym = sys.argv[1] if len(sys.argv) > 1 else "XAUUSD"
    out = []
    base = dict(rr=2.0, zz=1.0)
    _, i0, o0, g0 = trial(sym, **base)
    out.append(row("baseline", i0, o0))
    for gate in ("use_mtf", "use_state", "use_break", "use_risk"):
        kw = dict(base); kw[gate] = False
        _, i, o, _ = trial(sym, **kw)
        out.append(row("no " + gate.replace("use_", ""), i, o))
    kw = dict(base, use_mtf=False, use_state=False, use_break=False, use_risk=False)
    _, i, o, _ = trial(sym, **kw)
    out.append(row("no gates at all", i, o))
    print("== gate ablation (%s) ==" % sym)
    print(pd.DataFrame(out).to_string(index=False))

    out = []
    for rr in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0):
        _, i, o, _ = trial(sym, rr=rr, zz=1.0)
        out.append(row("rr=%.1f" % rr, i, o))
    print()
    print("== reward-to-risk sweep ==")
    print(pd.DataFrame(out).to_string(index=False))

    out = []
    for zz in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        _, i, o, _ = trial(sym, rr=2.0, zz=zz)
        out.append(row("zz=%.2f" % zz, i, o))
    print()
    print("== swing threshold sweep (x ATR) ==")
    print(pd.DataFrame(out).to_string(index=False))
