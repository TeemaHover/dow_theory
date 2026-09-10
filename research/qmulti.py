# -*- coding: utf-8 -*-
"""Run one configuration across many instruments and pool the trades.

A rule that only works on one symbol is a property of that symbol's history.
Pooling gives both a bigger sample to reason about and a consistency check.
"""
import sys, glob, os
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig, qbt, qrun

def all_syms(tag="H1"):
    out = []
    for p in glob.glob(os.path.join(qdata.DATA, "*_%s_*.npz" % tag)):
        out.append(os.path.basename(p).split("_")[0])
    return sorted(set(out))

_c = {}
def build(sym, tf, htf, zz, atr_n=14):
    k = (sym, tf, htf, zz, atr_n)
    if k not in _c:
        _c[k] = qrun.build(sym, tf, htf, atr_n, zz)
    return _c[k]

def run(syms, tf="1h", htf="4h", zz=1.0, cut="2025-09-01", entry_fn=None,
        with_features=True, spread_override=None, **kw):
    frames = []
    for s in syms:
        try:
            work, st, hs = build(s, tf, htf, zz)
        except SystemExit:
            continue
        fn = entry_fn or qsig.dow_entries
        ent, g = fn(work, st, hs, **kw)
        feats = qsig.context(work, st, hs) if with_features else None
        sp = qrun.SPREAD.get(s, 0.0) if spread_override is None else spread_override
        tr = qbt.run(work, ent, spread=sp, features=feats)
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("entry_time")

def report(tr, cut="2025-09-01", title=""):
    tr_in, tr_out = qrun.split(tr, cut)
    print("== %s ==" % title)
    print(qbt.show([qbt.stats(tr, "POOLED all"),
                    qbt.stats(tr_in, "POOLED train"),
                    qbt.stats(tr_out, "POOLED test")]))
    rows = []
    for s, grp in tr.groupby("sym"):
        gi, go = qrun.split(grp, cut)
        a, b = qbt.stats(gi, s), qbt.stats(go, s)
        rows.append({"sym": s, "tr_n": a.get("n", 0), "tr_pf": a.get("pf", 0),
                     "tr_expR": a.get("expR", 0), "te_n": b.get("n", 0),
                     "te_pf": b.get("pf", 0), "te_expR": b.get("expR", 0)})
    print(pd.DataFrame(rows).to_string(index=False))
    return tr_in, tr_out

if __name__ == "__main__":
    syms = all_syms()
    print("symbols:", " ".join(syms))
    tr = run(syms, rr=2.0, zz=1.0)
    report(tr, title="baseline rr=2 zz=1.0")
