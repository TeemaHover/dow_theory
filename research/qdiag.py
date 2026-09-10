# -*- coding: utf-8 -*-
"""Why trades lose, and what we refused that we should not have.

Everything here is meant to be run on the TRAIN slice only. Splitting a sample
until something looks good is how false edges are born, so each report carries
its sample size and nothing with a thin bucket should be acted on.
"""
import numpy as np
import pandas as pd

def bucket(tr, col, q=4, min_n=25):
    """Expectancy by quantile bucket of one context feature."""
    if col not in tr or len(tr) < min_n:
        return None
    v = pd.to_numeric(tr[col], errors="coerce")
    if v.notna().sum() < min_n or v.nunique() < 3:
        return None
    try:
        b = pd.qcut(v, q, duplicates="drop")
    except Exception:
        return None
    g = tr.groupby(b, observed=True)["r"]
    out = pd.DataFrame({"n": g.size(), "expR": g.mean().round(3),
                        "win%": (g.apply(lambda s: 100.0 * (s > 0).mean())).round(1),
                        "totR": g.sum().round(1)})
    out.index.name = col
    return out[out["n"] >= max(10, min_n // 3)]

def scan(tr, min_n=40, top=12):
    """Rank context features by how far apart the best and worst buckets sit."""
    rows = []
    for col in [c for c in tr.columns if c.startswith("f_")]:
        t = bucket(tr, col, q=4, min_n=min_n)
        if t is None or len(t) < 2:
            continue
        rows.append({"feature": col, "buckets": len(t),
                     "best_expR": t["expR"].max(), "worst_expR": t["expR"].min(),
                     "spread": round(float(t["expR"].max() - t["expR"].min()), 3),
                     "min_n": int(t["n"].min())})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("spread", ascending=False).head(top)

def by_flag(tr, col):
    if col not in tr:
        return None
    g = tr.groupby(tr[col].astype(bool), observed=True)["r"]
    return pd.DataFrame({"n": g.size(), "expR": g.mean().round(3),
                         "win%": g.apply(lambda s: 100.0 * (s > 0).mean()).round(1),
                         "totR": g.sum().round(1)})

def exits(tr):
    g = tr.groupby("reason", observed=True)["r"]
    return pd.DataFrame({"n": g.size(), "expR": g.mean().round(3),
                         "totR": g.sum().round(1)})

def mfe_study(tr, levels=(0.5, 1.0, 1.5, 2.0, 3.0)):
    """How far losers ran in our favour before failing, and how many winners
    would survive a tighter or wider target."""
    out = []
    for lv in levels:
        reached = tr["mfe"] >= lv
        out.append({"mfe>=%.1fR" % lv: "", "n": int(reached.sum()),
                    "share%": round(100.0 * reached.mean(), 1),
                    "expR_of_those": round(tr.loc[reached, "r"].mean(), 3) if reached.any() else 0.0})
    return pd.DataFrame(out)

def missed(work, st, ent, horizon=24, min_move_atr=3.0, g=None):
    """Bars where a big move followed but we held no signal, grouped by why."""
    c = work["close"].to_numpy(np.float64)
    h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64)
    atr = st["atr"].to_numpy(np.float64)
    n = len(work)
    fwd_up = np.full(n, np.nan)
    fwd_dn = np.full(n, np.nan)
    for i in range(n - horizon):
        seg_h = h[i + 1:i + 1 + horizon].max()
        seg_l = l[i + 1:i + 1 + horizon].min()
        if atr[i] > 0:
            fwd_up[i] = (seg_h - c[i]) / atr[i]
            fwd_dn[i] = (c[i] - seg_l) / atr[i]
    big_up = fwd_up >= min_move_atr
    big_dn = fwd_dn >= min_move_atr
    d = ent["dir"].to_numpy(np.int64)
    res = {"bars": n,
           "big_up_bars": int(np.nansum(big_up)), "big_dn_bars": int(np.nansum(big_dn)),
           "big_up_with_long_signal": int((big_up & (d == 1)).sum()),
           "big_dn_with_short_signal": int((big_dn & (d == -1)).sum())}
    if g is not None:
        raw_l = g["raw_l"].to_numpy(bool)
        raw_s = g["raw_s"].to_numpy(bool)
        res["big_up_with_raw_setup"] = int((big_up & raw_l).sum())
        res["big_dn_with_raw_setup"] = int((big_dn & raw_s).sum())
        for gate in ("mtf", "state", "break", "risk"):
            res["up_blocked_by_" + gate] = int((big_up & raw_l & ~g[gate + "_l"].to_numpy(bool)).sum())
            res["dn_blocked_by_" + gate] = int((big_dn & raw_s & ~g[gate + "_s"].to_numpy(bool)).sum())
    return pd.Series(res)
