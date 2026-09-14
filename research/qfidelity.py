# -*- coding: utf-8 -*-
"""How much do two backtest simplifications flatter the published numbers?

  gap fills  - a stop is filled at the open when the bar opens beyond it
  re-entry   - a new signal on the bar that closed a trade is taken, as the
               TradingView indicator does
Same 42 markets and Dow version as the published system, trailing stop plus the
indicator's default 6R take-profit and the trail-only variant.
"""
import sys
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdow as Q
import qdow3 as Q3
import qbt
pd.set_option("display.width", 250)

rows = []
for tp_label, tpkw in (("trail only", {}), ("TP 6R (indicator default)", {"tp_full_r": 6.0})):
    for label, kw in (("as published", {}),
                      ("+ gap fills", {"gap_fills": True}),
                      ("+ same-bar re-entry", {"reenter_on_exit_bar": True}),
                      ("+ both (closest to live)", {"gap_fills": True, "reenter_on_exit_bar": True})):
        tr = Q.run(Q3.WIDE, Q3.DOW, **tpkw, **kw)
        e = Q.eras(tr)
        allst = qbt.stats(tr, "")
        gaps = int(((tr["reason"] == "stop") & (tr["exit"] != tr["exit"])).sum()) if False else None
        rows.append({"exit": tp_label, "assumptions": label, "n": allst["n"],
                     "PF 2000-15": e["A 2000-15"]["pf"], "PF 2016-26": e["B 2016-26"]["pf"],
                     "expR all": allst["expR"], "totR": allst["totR"], "maxDD R": allst["maxDD_R"],
                     "per month": allst["trades_per_month"]})
        print(pd.DataFrame(rows[-1:]).to_string(index=False, header=(len(rows) == 1)), flush=True)
print()
print(pd.DataFrame(rows).to_string(index=False))
