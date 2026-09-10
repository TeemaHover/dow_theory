# -*- coding: utf-8 -*-
"""Signal construction plus a gate log.

Every rule that can block a trade is a named boolean column. The base setup and
the gates are kept separate so the backtest can answer two different questions:
what did we trade, and what did we refuse and why.
"""
import numpy as np
import pandas as pd

def dow_entries(work, st, htf=None, rr=2.0, stop_buf=0.25, max_break_atr=1.0,
                min_risk_atr=0.3, max_risk_atr=4.0, use_mtf=True, use_state=True,
                use_break=True, use_risk=True):
    """Break-of-structure continuation, long and short."""
    c = work["close"].to_numpy(np.float64)
    n = len(work)
    atr = st["atr"].to_numpy(np.float64)
    sh, sl = st["sh"].to_numpy(np.float64), st["sl"].to_numpy(np.float64)
    state = st["state"].to_numpy(np.int8)
    bull_bos = st["bull_bos"].to_numpy(bool)
    bear_bos = st["bear_bos"].to_numpy(bool)
    hstate = (htf.to_numpy(np.float64) if htf is not None else np.zeros(n))

    raw_l, raw_s = bull_bos.copy(), bear_bos.copy()

    with np.errstate(invalid="ignore"):
        brk_l = np.where(atr > 0, (c - sh) / atr, np.nan)
        brk_s = np.where(atr > 0, (sl - c) / atr, np.nan)

    g = pd.DataFrame(index=work.index)
    g["mtf_l"] = (hstate >= 0) if use_mtf else True
    g["mtf_s"] = (hstate <= 0) if use_mtf else True
    g["state_l"] = (state >= 0) if use_state else True
    g["state_s"] = (state <= 0) if use_state else True
    g["break_l"] = (brk_l <= max_break_atr) if use_break else True
    g["break_s"] = (brk_s <= max_break_atr) if use_break else True

    stop_l = sl - stop_buf * atr
    stop_s = sh + stop_buf * atr
    risk_l = np.where(atr > 0, (c - stop_l) / atr, np.nan)
    risk_s = np.where(atr > 0, (stop_s - c) / atr, np.nan)
    g["risk_l"] = ((risk_l >= min_risk_atr) & (risk_l <= max_risk_atr)) if use_risk else True
    g["risk_s"] = ((risk_s >= min_risk_atr) & (risk_s <= max_risk_atr)) if use_risk else True

    ok_l = raw_l & g["mtf_l"] & g["state_l"] & g["break_l"] & g["risk_l"] & np.isfinite(stop_l)
    ok_s = raw_s & g["mtf_s"] & g["state_s"] & g["break_s"] & g["risk_s"] & np.isfinite(stop_s)
    ok_l = ok_l.to_numpy(bool)
    ok_s = ok_s.to_numpy(bool)

    d = np.where(ok_l, 1, np.where(ok_s, -1, 0))
    stop = np.where(ok_l, stop_l, np.where(ok_s, stop_s, np.nan))
    risk = np.abs(c - stop)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))

    ent = pd.DataFrame({"dir": d, "stop": stop, "target": target,
                        "tag": np.where(d > 0, "BOS_L", np.where(d < 0, "BOS_S", ""))},
                       index=work.index)
    g["raw_l"], g["raw_s"] = raw_l, raw_s
    g["taken_l"], g["taken_s"] = ok_l, ok_s
    return ent, g

def veto_table(g):
    """For setups that existed but were refused, count which gate did the refusing."""
    out = []
    for side in ("l", "s"):
        raw = g["raw_" + side].to_numpy(bool)
        taken = g["taken_" + side].to_numpy(bool)
        blocked = raw & ~taken
        row = {"side": side, "raw_setups": int(raw.sum()), "taken": int(taken.sum()),
               "blocked": int(blocked.sum())}
        for gate in ("mtf", "state", "break", "risk"):
            col = g[gate + "_" + side]
            v = np.zeros(len(g), bool) if col.dtype == bool else np.zeros(len(g), bool)
            v = ~np.asarray(col, bool)
            row["by_" + gate] = int((blocked & v).sum())
        out.append(row)
    return pd.DataFrame(out)

def context(work, st, htf=None):
    """Features captured at entry so losses can be grouped and explained later."""
    f = pd.DataFrame(index=work.index)
    atr = st["atr"]
    f["hour"] = work.index.hour
    f["dow"] = work.index.dayofweek
    f["atr_pct"] = (atr / work["close"]).astype(float)
    f["atr_rank"] = (atr > atr.rolling(200, min_periods=50).mean()).astype(float)
    f["state"] = st["state"]
    f["htf_state"] = (htf if htf is not None else pd.Series(0.0, index=work.index))
    f["aligned"] = np.sign(f["htf_state"].fillna(0)) == np.sign(f["state"])
    rng = (work["high"] - work["low"]) / atr
    f["bar_rng_atr"] = rng
    f["body_frac"] = ((work["close"] - work["open"]).abs() /
                      (work["high"] - work["low"]).replace(0, np.nan))
    with np.errstate(invalid="ignore"):
        f["dist_sh_atr"] = (work["close"] - st["sh"]) / atr
        f["dist_sl_atr"] = (work["close"] - st["sl"]) / atr
    f["swing_span_atr"] = (st["sh"] - st["sl"]) / atr
    return f
