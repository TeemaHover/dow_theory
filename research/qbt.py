# -*- coding: utf-8 -*-
"""Event-driven backtest with conservative fills and per-trade context capture.

Rules that keep the result honest:
  * a signal on bar i is filled at the OPEN of bar i+1, never on bar i;
  * when a bar's range contains both the stop and the target, the stop is taken,
    because from daily bars alone the order inside the bar is unknowable;
  * spread is charged on entry and on exit, in price units;
  * risk is |entry - stop| after costs, so every result is in R multiples and does
    not depend on account size or position sizing.
"""
import numpy as np
import pandas as pd

def run(work, entries, spread=0.0, max_bars=200, be_at_r=None, trail_atr=None,
        atr_col=None, features=None, allow_pyramid=False):
    """Simulate. `entries` needs columns dir/stop/target (dir 0 means no signal)."""
    o = work["open"].to_numpy(np.float64)
    h = work["high"].to_numpy(np.float64)
    l = work["low"].to_numpy(np.float64)
    c = work["close"].to_numpy(np.float64)
    idx = work.index
    n = len(work)

    d_arr = entries["dir"].to_numpy(np.int64)
    s_arr = entries["stop"].to_numpy(np.float64)
    t_arr = entries["target"].to_numpy(np.float64)
    tags = entries["tag"].to_numpy(object) if "tag" in entries else np.array([""] * n, object)
    atr_arr = work[atr_col].to_numpy(np.float64) if atr_col else None

    half = spread / 2.0
    rows = []
    i = 0
    in_pos = False
    while i < n - 1:
        if not in_pos and d_arr[i] != 0:
            d = int(d_arr[i])
            stop0, tgt0 = s_arr[i], t_arr[i]
            if not (stop0 == stop0 and tgt0 == tgt0):
                i += 1
                continue
            e_i = i + 1
            entry = o[e_i] + (half if d > 0 else -half)
            risk = abs(entry - stop0)
            if risk <= 0:
                i += 1
                continue
            stop = stop0
            mfe = mae = 0.0
            exit_i, exit_px, reason = -1, np.nan, ""
            moved_be = False
            for j in range(e_i, min(n, e_i + max_bars)):
                fav = (h[j] - entry) if d > 0 else (entry - l[j])
                adv = (entry - l[j]) if d > 0 else (h[j] - entry)
                mfe = max(mfe, fav / risk)
                mae = max(mae, adv / risk)
                hit_stop = (l[j] <= stop) if d > 0 else (h[j] >= stop)
                hit_tgt = (h[j] >= tgt0) if d > 0 else (l[j] <= tgt0)
                if hit_stop:                       # stop wins ties, deliberately
                    exit_i, exit_px, reason = j, stop, "stop"
                    break
                if hit_tgt:
                    exit_i, exit_px, reason = j, tgt0, "target"
                    break
                if be_at_r is not None and not moved_be and fav / risk >= be_at_r:
                    stop = entry
                    moved_be = True
                if trail_atr is not None and atr_arr is not None and atr_arr[j] == atr_arr[j]:
                    cand = (c[j] - trail_atr * atr_arr[j]) if d > 0 else (c[j] + trail_atr * atr_arr[j])
                    stop = max(stop, cand) if d > 0 else min(stop, cand)
            if exit_i < 0:
                exit_i = min(n - 1, e_i + max_bars - 1)
                exit_px, reason = c[exit_i], "timeout"
            exit_px = exit_px - half if d > 0 else exit_px + half
            r = ((exit_px - entry) / risk) * d
            rec = {"entry_time": idx[e_i], "exit_time": idx[exit_i], "dir": d,
                   "entry": entry, "stop": stop0, "target": tgt0, "exit": exit_px,
                   "r": r, "mfe": mfe, "mae": mae, "bars": exit_i - e_i,
                   "reason": reason, "tag": tags[i]}
            if features is not None:
                for k in features.columns:
                    rec["f_" + k] = features[k].iloc[i]
            rows.append(rec)
            i = exit_i if allow_pyramid else exit_i + 1
        else:
            i += 1
    return pd.DataFrame(rows)

def stats(tr, label=""):
    if tr is None or len(tr) == 0:
        return {"label": label, "n": 0}
    r = tr["r"].to_numpy(np.float64)
    wins, losses = r[r > 0], r[r < 0]
    gp, gl = wins.sum(), -losses.sum()
    months = max(1.0, (tr["entry_time"].max() - tr["entry_time"].min()).days / 30.44)
    return {"label": label, "n": len(r),
            "win%": round(100.0 * len(wins) / len(r), 1),
            "pf": round(gp / gl, 3) if gl > 0 else float("inf"),
            "expR": round(r.mean(), 4),
            "totR": round(r.sum(), 1),
            "avgW": round(wins.mean(), 2) if len(wins) else 0.0,
            "avgL": round(losses.mean(), 2) if len(losses) else 0.0,
            "maxDD_R": round(dd(r), 1),
            "trades_per_month": round(len(r) / months, 1)}

def dd(r):
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate(([0.0], eq)))[1:]
    return float((peak - eq).max())

def show(rowdicts):
    return pd.DataFrame(rowdicts).to_string(index=False)
