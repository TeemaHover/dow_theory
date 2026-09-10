# -*- coding: utf-8 -*-
"""Run one configuration over a symbol and report train/test separately."""
import sys, argparse
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qsig, qbt

SPREAD = {"XAUUSD": 0.30, "XAGUSD": 0.02, "EURUSD": 0.00010, "GBPUSD": 0.00012,
          "USDJPY": 0.012, "AUDUSD": 0.00012, "USDCAD": 0.00014,
          "USDCHF": 0.00014, "NZDUSD": 0.00018}

def build(sym, tf="1h", htf_rule="4h", atr_n=14, zz=1.0):
    h1 = qdata.load_h1(sym)
    work = h1 if tf == "1h" else qdata.resample(h1, tf)
    a = qdata.atr(work, atr_n)
    st = qstruct.structure(work, a, thr=zz)
    hf = qdata.resample(h1, htf_rule)
    ha = qdata.atr(hf, atr_n)
    hst = qstruct.structure(hf, ha, thr=zz)
    htf_state = qdata.asof(hst["state"].to_numpy(), hst.index, htf_rule, work.index)
    return work, st, htf_state

def split(tr, cut="2021-01-01"):
    if len(tr) == 0:
        return tr, tr
    m = tr["entry_time"] < pd.Timestamp(cut, tz="UTC")
    return tr[m], tr[~m]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sym", default="XAUUSD")
    ap.add_argument("--tf", default="1h")
    ap.add_argument("--htf", default="4h")
    ap.add_argument("--zz", type=float, default=1.0)
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--cut", default="2021-01-01")
    ap.add_argument("--no-mtf", action="store_true")
    a = ap.parse_args()

    work, st, htf_state = build(a.sym, a.tf, a.htf, zz=a.zz)
    ent, g = qsig.dow_entries(work, st, htf_state, rr=a.rr, use_mtf=not a.no_mtf)
    feats = qsig.context(work, st, htf_state)
    tr = qbt.run(work, ent, spread=SPREAD.get(a.sym, 0.0), atr_col=None, features=feats)

    print("%s %s  bars=%d  %s -> %s" % (a.sym, a.tf, len(work),
          work.index[0].date(), work.index[-1].date()))
    tr_in, tr_out = split(tr, a.cut)
    print(qbt.show([qbt.stats(tr, "ALL"), qbt.stats(tr_in, "train<" + a.cut),
                    qbt.stats(tr_out, "TEST>=" + a.cut)]))
    print()
    print("gate refusals:")
    print(qsig.veto_table(g).to_string(index=False))
    return tr, g, work, st

if __name__ == "__main__":
    main()
