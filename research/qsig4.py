# -*- coding: utf-8 -*-
"""Donchian time-series momentum: the strategy class with the longest published
record across futures and currencies. Entry on an N-day extreme in the direction
of a long trend filter, risk from ATR, and winners held with a trailing stop."""
import numpy as np
import pandas as pd
from qsig2 import _frame, ema, rolling_min, rolling_max

def donchian_entries(work, st, htf=None, rr=None, n_break=20, n_trend=100,
                     stop_atr=2.0, use_trend=True, **_):
    h = work["high"].to_numpy(np.float64); l = work["low"].to_numpy(np.float64)
    c = work["close"].to_numpy(np.float64)
    atr = st["atr"].to_numpy(np.float64)
    hh = pd.Series(h).rolling(n_break, min_periods=n_break).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n_break, min_periods=n_break).min().shift(1).to_numpy()
    trend = ema(c, n_trend)
    L = c > hh
    S = c < ll
    if use_trend:
        L = L & (c > trend)
        S = S & (c < trend)
    stop_l = c - stop_atr * atr
    stop_s = c + stop_atr * atr
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    d = np.where(np.isfinite(stop) & np.isfinite(atr) & (atr > 0), d, 0)
    # no fixed target: these are held on a trailing stop, so aim far away
    target = np.where(d > 0, c + 100.0 * atr, np.where(d < 0, c - 100.0 * atr, np.nan))
    tag = np.where(d > 0, "DON_L", np.where(d < 0, "DON_S", ""))
    return _frame(work, d, stop, target, tag)
