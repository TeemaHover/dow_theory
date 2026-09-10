# -*- coding: utf-8 -*-
"""Two hypotheses with better prior evidence than structure breakouts.

meanrev - intraday FX is more mean reverting than trending, so fade stretched moves
orb     - session opening range breaks, a documented intraday effect
"""
import numpy as np
import pandas as pd
from qsig2 import _frame, ema, rolling_min, rolling_max

def meanrev_entries(work, st, htf=None, rr=1.5, n=20, k=2.0, stop_buf=0.5,
                    trend_filter=False, **_):
    o = work["open"].to_numpy(np.float64); h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64);  c = work["close"].to_numpy(np.float64)
    atr = st["atr"].to_numpy(np.float64)
    sma = pd.Series(c).rolling(n, min_periods=n).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        z = (c - sma) / atr
    L = (z <= -k) & (c > o)
    S = (z >= k) & (c < o)
    if trend_filter:
        e200 = ema(c, 200)
        L &= c > e200
        S &= c < e200
    stop_l = np.minimum(l, rolling_min(l, 3)) - stop_buf * atr
    stop_s = np.maximum(h, rolling_max(h, 3)) + stop_buf * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    risk = np.abs(c - stop)
    d = np.where(np.isfinite(stop) & (risk > 0.05 * atr), d, 0)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
    tag = np.where(d > 0, "MR_L", np.where(d < 0, "MR_S", ""))
    return _frame(work, d, stop, target, tag)

def orb_entries(work, st, htf=None, rr=2.0, open_hour=7, range_hours=1,
                trade_hours=6, stop_buf=0.1, **_):
    """Break of the first hours of the London session, traded for the rest of it."""
    h = work["high"].to_numpy(np.float64); l = work["low"].to_numpy(np.float64)
    c = work["close"].to_numpy(np.float64)
    atr = st["atr"].to_numpy(np.float64)
    idx = work.index
    hour = idx.hour.to_numpy()
    day = idx.normalize()
    n = len(work)
    hi = np.full(n, np.nan); lo = np.full(n, np.nan)
    cur_day = None
    rh = rl = np.nan
    for i in range(n):
        if day[i] != cur_day:
            cur_day = day[i]; rh = rl = np.nan
        if open_hour <= hour[i] < open_hour + range_hours:
            rh = h[i] if rh != rh else max(rh, h[i])
            rl = l[i] if rl != rl else min(rl, l[i])
        hi[i], lo[i] = rh, rl
    active = (hour >= open_hour + range_hours) & (hour < open_hour + range_hours + trade_hours)
    L = active & (c > hi) & np.isfinite(hi)
    S = active & (c < lo) & np.isfinite(lo)
    first = np.ones(n, bool)
    seen_l = seen_s = None
    for i in range(n):
        if i > 0 and day[i] != day[i - 1]:
            seen_l = seen_s = None
        if L[i]:
            if seen_l is not None:
                L[i] = False
            else:
                seen_l = i
        if S[i]:
            if seen_s is not None:
                S[i] = False
            else:
                seen_s = i
    stop_l = lo - stop_buf * atr
    stop_s = hi + stop_buf * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    risk = np.abs(c - stop)
    d = np.where(np.isfinite(stop) & (risk > 0.05 * atr), d, 0)
    target = np.where(d > 0, c + rr * risk, np.where(d < 0, c - rr * risk, np.nan))
    tag = np.where(d > 0, "ORB_L", np.where(d < 0, "ORB_S", ""))
    return _frame(work, d, stop, target, tag)
