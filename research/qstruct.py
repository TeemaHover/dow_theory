# -*- coding: utf-8 -*-
"""Dow structure: ATR zigzag swings, HH/HL/LH/LL, state, break of structure.

Non-repainting discipline: a swing pivot sits at the bar that made the extreme,
but it is not KNOWN until price retraces far enough to confirm it. Every output
here is stamped at the confirming bar, never at the pivot bar, so a backtest can
read row i and be certain that information existed at the close of bar i.
"""
import numpy as np
import pandas as pd

def zigzag(high, low, atrv, thr):
    """Confirmed swing pivots. Returns (kind, pivot_i, confirm_i, price) arrays.

    kind is +1 for a swing high, -1 for a swing low.
    """
    n = len(high)
    kind, piv, conf, price = [], [], [], []
    d = 1                      # 1 = tracking an up leg toward a high
    ext_i, ext_p = 0, high[0]
    for i in range(1, n):
        a = atrv[i]
        if a != a or a <= 0:
            continue
        t = thr * a
        if d == 1:
            if high[i] >= ext_p:
                ext_p, ext_i = high[i], i
            elif ext_p - low[i] >= t:
                kind.append(1); piv.append(ext_i); conf.append(i); price.append(ext_p)
                d = -1; ext_p, ext_i = low[i], i
        else:
            if low[i] <= ext_p:
                ext_p, ext_i = low[i], i
            elif high[i] - ext_p >= t:
                kind.append(-1); piv.append(ext_i); conf.append(i); price.append(ext_p)
                d = 1; ext_p, ext_i = high[i], i
    return (np.array(kind, dtype=np.int8), np.array(piv, dtype=np.int64),
            np.array(conf, dtype=np.int64), np.array(price, dtype=np.float64))

BULL, RANGE, BEAR = 1, 0, -1

def structure(df, atrv, thr=1.0):
    """Per-bar structure state built only from pivots already confirmed."""
    high = df["high"].to_numpy(np.float64)
    low = df["low"].to_numpy(np.float64)
    close = df["close"].to_numpy(np.float64)
    n = len(df)
    kind, piv, conf, price = zigzag(high, low, np.asarray(atrv, np.float64), thr)

    sh = np.full(n, np.nan)        # last confirmed swing high price
    sl = np.full(n, np.nan)        # last confirmed swing low price
    sh_i = np.full(n, -1, np.int64)
    sl_i = np.full(n, -1, np.int64)
    hh = np.zeros(n, np.int8)      # +1 higher high, -1 lower high, 0 unknown
    hl = np.zeros(n, np.int8)      # +1 higher low,  -1 lower low
    state = np.zeros(n, np.int8)

    cur_sh = cur_sl = np.nan
    cur_sh_i = cur_sl_i = -1
    prev_h = prev_l = np.nan
    lab_h = lab_l = 0
    k = 0
    for i in range(n):
        while k < len(conf) and conf[k] == i:
            if kind[k] == 1:
                prev_h = cur_sh
                cur_sh, cur_sh_i = price[k], piv[k]
                if prev_h == prev_h:
                    lab_h = 1 if cur_sh > prev_h else -1
            else:
                prev_l = cur_sl
                cur_sl, cur_sl_i = price[k], piv[k]
                if prev_l == prev_l:
                    lab_l = 1 if cur_sl > prev_l else -1
            k += 1
        sh[i], sl[i] = cur_sh, cur_sl
        sh_i[i], sl_i[i] = cur_sh_i, cur_sl_i
        hh[i], hl[i] = lab_h, lab_l
        if lab_h == 1 and lab_l == 1:
            state[i] = BULL
        elif lab_h == -1 and lab_l == -1:
            state[i] = BEAR
        else:
            state[i] = RANGE

    # break of structure: close beyond the confirmed swing, first time for that swing
    bull_bos = np.zeros(n, bool)
    bear_bos = np.zeros(n, bool)
    last_broken_hi = last_broken_lo = -1
    for i in range(n):
        if sh_i[i] >= 0 and sh_i[i] != last_broken_hi and close[i] > sh[i]:
            bull_bos[i] = True
            last_broken_hi = sh_i[i]
        if sl_i[i] >= 0 and sl_i[i] != last_broken_lo and close[i] < sl[i]:
            bear_bos[i] = True
            last_broken_lo = sl_i[i]

    out = pd.DataFrame(index=df.index)
    out["state"] = state
    out["sh"] = sh
    out["sl"] = sl
    out["hh"] = hh
    out["hl"] = hl
    out["bull_bos"] = bull_bos
    out["bear_bos"] = bear_bos
    out["atr"] = np.asarray(atrv)
    return out
