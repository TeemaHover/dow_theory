# -*- coding: utf-8 -*-
"""Load cached Dukascopy 1-minute bars and build higher timeframes.

Every timestamp is UTC and every bar is labelled by its OPEN time, so a bar at
time T covers [T, T + timeframe). A value computed from that bar is only known
at T + timeframe; f_asof below is the only place higher-timeframe information is
allowed to cross over, and it always uses the bar END time.
"""
import os, glob
import numpy as np
import pandas as pd

DATA = "D:/Indicator/data"

def years_available(sym):
    out = []
    for p in glob.glob(os.path.join(DATA, sym + "_*.npz")):
        try:
            out.append(int(os.path.basename(p).split("_")[1].split(".")[0]))
        except Exception:
            pass
    return sorted(out)

def load_m1(sym, y0=None, y1=None):
    frames = []
    for y in years_available(sym):
        if y0 is not None and y < y0:
            continue
        if y1 is not None and y > y1:
            continue
        z = np.load(os.path.join(DATA, "%s_%d.npz" % (sym, y)))
        frames.append(pd.DataFrame({
            "open": z["o"], "high": z["h"], "low": z["l"],
            "close": z["c"], "volume": z["v"]},
            index=pd.to_datetime(z["t"], unit="s", utc=True)))
    if not frames:
        raise SystemExit("no cached data for " + sym)
    df = pd.concat(frames).sort_index()
    return df[~df.index.duplicated(keep="first")]

AGG = {"open": "first", "high": "max", "low": "min",
       "close": "last", "volume": "sum"}

def resample(m1, rule):
    """Aggregate 1-minute bars. Bars are labelled by open time and empty bars dropped."""
    r = m1.resample(rule, label="left", closed="left").agg(AGG)
    return r.dropna(subset=["open"])

def asof(htf_values, htf_index, htf_rule, target_index):
    """Project higher-timeframe values onto a lower timeframe without lookahead.

    A higher-timeframe bar opening at T is only complete at T + rule, so its value
    is stamped at that end time and then carried forward. A target bar opening at
    t therefore sees only higher-timeframe bars that had already closed by t.
    """
    end = htf_index + pd.tseries.frequencies.to_offset(htf_rule)
    s = pd.Series(np.asarray(htf_values), index=end).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(target_index)).ffill().reindex(target_index)

def atr(df, n=14):
    """Wilder ATR."""
    h, l, c = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    pc = np.empty_like(c); pc[0] = c[0]; pc[1:] = c[:-1]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    out = np.empty_like(tr); out[:] = np.nan
    if len(tr) <= n:
        return pd.Series(out, index=df.index)
    seed = tr[1:n + 1].mean()
    out[n] = seed
    a = seed
    for i in range(n + 1, len(tr)):
        a = (a * (n - 1) + tr[i]) / n
        out[i] = a
    return pd.Series(out, index=df.index)


def load_h1(sym):
    """Hourly bars, with Dukascopy's synthetic weekend fills removed.

    When the market is shut Dukascopy still emits a bar holding the last price,
    which shows up as zero volume and a zero range. Those are not tradable bars
    and they distort ATR and swing detection, so they go.
    """
    import glob as _glob
    paths = sorted(_glob.glob(os.path.join(DATA, sym + "_H1_*.npz")))
    if not paths:
        raise SystemExit("no hourly data for " + sym)
    fr = []
    for p in paths:
        z = np.load(p)
        fr.append(pd.DataFrame({"open": z["o"], "high": z["h"], "low": z["l"],
                                "close": z["c"], "volume": z["v"]},
                               index=pd.to_datetime(z["t"], unit="s", utc=True)))
    df = pd.concat(fr).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    dead = (df["volume"] <= 0) & (df["high"] <= df["low"])
    return df[~dead]


def load_tag(sym, tag):
    """Load any cached timeframe by tag, e.g. D1 or M15."""
    import glob as _glob
    paths = sorted(_glob.glob(os.path.join(DATA, "%s_%s_*.npz" % (sym, tag))))
    if not paths:
        raise SystemExit("no %s data for %s" % (tag, sym))
    fr = []
    for p in paths:
        z = np.load(p)
        fr.append(pd.DataFrame({"open": z["o"], "high": z["h"], "low": z["l"],
                                "close": z["c"], "volume": z["v"]},
                               index=pd.to_datetime(z["t"], unit="s", utc=True)))
    df = pd.concat(fr).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    dead = (df["volume"] <= 0) & (df["high"] <= df["low"])
    return df[~dead]
