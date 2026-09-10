# -*- coding: utf-8 -*-
"""Alternative entry hypotheses, each a different claim about where edge lives.

  pullback  - trend continuation bought on a retracement rather than a breakout
  sweep     - a failed break of a swing level, i.e. stops taken then reclaimed
  ma_pull   - trend by moving average, entry on a pullback to the fast average

All three share the interface of qsig.dow_entries so the same runner can drive them.
"""
import numpy as np
import pandas as pd

def _frame(work, d, stop, target, tag):
    ent = pd.DataFrame({"dir": d, "stop": stop, "target": target, "tag": tag},
                       index=work.index)
    g = pd.DataFrame(index=work.index)
    g["raw_l"] = d > 0
    g["raw_s"] = d < 0
    g["taken_l"] = d > 0
    g["taken_s"] = d < 0
    for k in ("mtf", "state", "break", "risk"):
        g[k + "_l"] = True
        g[k + "_s"] = True
    return ent, g

def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()

def rolling_min(x, n):
    return pd.Series(x).rolling(n, min_periods=1).min().to_numpy()

def rolling_max(x, n):
    return pd.Series(x).rolling(n, min_periods=1).max().to_numpy()

def pullback_entries(work, st, htf=None, rr=2.0, stop_buf=0.25, lookback=5,
                     retr_lo=0.30, retr_hi=0.85, use_mtf=True, **_):
    o = work["open"].to_numpy(np.float64); h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64);  c = work["close"].to_numpy(np.float64)
    n = len(work)
    atr = st["atr"].to_numpy(np.float64)
    sh, sl = st["sh"].to_numpy(np.float64), st["sl"].to_numpy(np.float64)
    state = st["state"].to_numpy(np.int8)
    hs = htf.to_numpy(np.float64) if htf is not None else np.zeros(n)

    leg = sh - sl
    with np.errstate(invalid="ignore"):
        retr_up = (sh - c) / leg          # how deep we have pulled back in an up leg
        retr_dn = (c - sl) / leg
    up_ok = (state > 0) & (retr_up >= retr_lo) & (retr_up <= retr_hi)
    dn_ok = (state < 0) & (retr_dn >= retr_lo) & (retr_dn <= retr_hi)
    if use_mtf:
        up_ok &= hs >= 0
        dn_ok &= hs <= 0
    trig_up = c > o                       # a bar that turns back up
    trig_dn = c < o
    L = up_ok & trig_up & (c > l)
    S = dn_ok & trig_dn

    swing_lo = rolling_min(l, lookback)
    swing_hi = rolling_max(h, lookback)
    stop_l = np.minimum(swing_lo, l) - stop_buf * atr
    stop_s = np.maximum(swing_hi, h) + stop_buf * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    risk = np.abs(c - stop)
    ok = np.isfinite(stop) & (risk > 0.05 * atr)
    d = np.where(ok, d, 0)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
    tag = np.where(d > 0, "PB_L", np.where(d < 0, "PB_S", ""))
    return _frame(work, d, stop, target, tag)

def sweep_entries(work, st, htf=None, rr=2.0, stop_buf=0.20, use_mtf=False, **_):
    o = work["open"].to_numpy(np.float64); h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64);  c = work["close"].to_numpy(np.float64)
    n = len(work)
    atr = st["atr"].to_numpy(np.float64)
    sh, sl = st["sh"].to_numpy(np.float64), st["sl"].to_numpy(np.float64)
    hs = htf.to_numpy(np.float64) if htf is not None else np.zeros(n)

    L = (l < sl) & (c > sl) & np.isfinite(sl)     # broke the low, closed back above
    S = (h > sh) & (c < sh) & np.isfinite(sh)
    if use_mtf:
        L &= hs >= 0
        S &= hs <= 0
    stop_l = l - stop_buf * atr
    stop_s = h + stop_buf * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    risk = np.abs(c - stop)
    ok = np.isfinite(stop) & (risk > 0.05 * atr)
    d = np.where(ok, d, 0)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
    tag = np.where(d > 0, "SW_L", np.where(d < 0, "SW_S", ""))
    return _frame(work, d, stop, target, tag)

def ma_pull_entries(work, st, htf=None, rr=2.0, fast=20, slow=100, stop_buf=0.5,
                    use_mtf=False, **_):
    o = work["open"].to_numpy(np.float64); h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64);  c = work["close"].to_numpy(np.float64)
    atr = st["atr"].to_numpy(np.float64)
    ef, es = ema(c, fast), ema(c, slow)
    up, dn = (ef > es) & (c > es), (ef < es) & (c < es)
    touch_l = (l <= ef) & (c > ef)
    touch_s = (h >= ef) & (c < ef)
    L, S = up & touch_l, dn & touch_s
    stop_l = np.minimum(l, ef) - stop_buf * atr
    stop_s = np.maximum(h, ef) + stop_buf * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    risk = np.abs(c - stop)
    ok = np.isfinite(stop) & (risk > 0.05 * atr)
    d = np.where(ok, d, 0)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
    tag = np.where(d > 0, "MA_L", np.where(d < 0, "MA_S", ""))
    return _frame(work, d, stop, target, tag)
