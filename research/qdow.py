# -*- coding: utf-8 -*-
"""Classical Dow Theory on daily bars, tested one element at a time.

Decision era A, 2000-2015: data nothing so far has been fitted to.
Confirmation era B, 2016-2026.

Rule fixed before running: an element is ADOPTED only if, against the Trend Core
baseline on the same instruments, it raises BOTH expectancy and profit factor in
BOTH eras. Anything else is rejected, however good one era looks.
"""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "D:/Indicator/research")
import qdata, qstruct, qbt
from qsig2 import ema
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)

CLASSES = {
    "metals": ["XAUUSD", "XAGUSD", "PLATINUM", "PALLADIUM", "COPPER"],
    "energy": ["WTI", "NATGAS", "HEATOIL", "GASOLINE"],
    "ags":    ["CORN", "SOYBEAN", "WHEAT", "COFFEE", "SUGAR", "COTTON", "COCOA"],
    "equity": ["SPX500", "NAS100", "DOW30", "RUSSELL", "NIKKEI", "FTSE", "DAX"],
    "rates":  ["TNOTE", "TBOND"],
}
UNIVERSE = sum(CLASSES.values(), [])
US_EQ = ["SPX500", "NAS100", "DOW30", "RUSSELL"]
FX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]

# round-trip cost in basis points of price, at or above typical retail CFD spreads
COST_BPS = {"XAUUSD": 3, "XAGUSD": 8, "PLATINUM": 15, "PALLADIUM": 50, "COPPER": 10,
            "WTI": 6, "NATGAS": 30, "HEATOIL": 15, "GASOLINE": 15,
            "CORN": 20, "SOYBEAN": 15, "WHEAT": 20, "COFFEE": 30, "SUGAR": 20,
            "COTTON": 20, "COCOA": 15,
            "SPX500": 2, "NAS100": 2, "DOW30": 2, "RUSSELL": 4, "NIKKEI": 3,
            "FTSE": 2, "DAX": 2, "TNOTE": 2, "TBOND": 3,
            "EURUSD": 1, "GBPUSD": 1.5, "USDJPY": 1.5, "AUDUSD": 2, "USDCAD": 2,
            "USDCHF": 2, "NZDUSD": 2.5}
ERAS = (("A 2000-15", "2000-01-01", "2016-01-01"),
        ("B 2016-26", "2016-01-01", "2100-01-01"))

_c = {}


def prep(sym):
    if sym not in _c:
        df = qdata.load_tag(sym, "D1L")
        df.index = df.index.normalize()
        df = df[~df.index.duplicated(keep="last")]
        _c[sym] = (df, qdata.atr(df, 14))
    return _c[sym]


def cstruct(sym, thr):
    """Peaks and troughs on daily CLOSES, as Dow read them."""
    k = ("cs", sym, thr)
    if k not in _c:
        df, atr = prep(sym)
        cf = pd.DataFrame({"high": df["close"], "low": df["close"], "close": df["close"]},
                          index=df.index)
        _c[k] = qstruct.structure(cf, atr, thr=thr)
    return _c[k]


def weekly_state(sym, thr=2.0):
    """Primary trend as peaks and troughs on weekly closes."""
    k = ("wk", sym, thr)
    if k not in _c:
        df, _ = prep(sym)
        w = df.resample("W-FRI", label="right", closed="right").agg(qdata.AGG)
        w = w.dropna(subset=["open"])
        wa = qdata.atr(w, 14)
        cf = pd.DataFrame({"high": w["close"], "low": w["close"], "close": w["close"]},
                          index=w.index)
        ws = qstruct.structure(cf, wa, thr=thr)
        # a week is only known once its Friday has closed
        s = pd.Series(ws["state"].to_numpy(float), index=w.index + pd.Timedelta(days=1))
        s = s[~s.index.duplicated(keep="last")]
        _c[k] = s.reindex(s.index.union(df.index)).ffill().reindex(df.index).fillna(0).to_numpy()
    return _c[k]


def lagged(values, src_index, target_index):
    """Another market's value as of YESTERDAY, aligned by date, so nothing peeks."""
    s = pd.Series(np.asarray(values, float), index=src_index).shift(1)
    return s.reindex(s.index.union(target_index)).ffill().reindex(target_index).to_numpy()


def _ent(df, L, S, stop_l, stop_s, a, tag):
    c = df["close"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        L = L & np.isfinite(stop_l) & (stop_l < c)
        S = S & np.isfinite(stop_s) & (stop_s > c)
        ok = np.isfinite(a) & (a > 0)
    L, S = L & ok, S & ok
    d = np.where(L, 1, np.where(S, -1, 0))
    stop = np.where(L, stop_l, np.where(S, stop_s, np.nan))
    target = np.where(d > 0, c + 100 * a, np.where(d < 0, c - 100 * a, np.nan))
    return pd.DataFrame({"dir": d, "stop": stop, "target": target,
                         "tag": np.where(d != 0, tag, "")}, index=df.index)


def tc(df, atr, nb=8, nt=100, satr=2.0, fl=None, fs=None):
    """Trend Core entries, with optional extra long / short conditions."""
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    a = atr.to_numpy(float)
    hh = pd.Series(h).rolling(nb, min_periods=nb).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(nb, min_periods=nb).min().shift(1).to_numpy()
    e = ema(c, nt)
    with np.errstate(invalid="ignore"):
        L = (c > hh) & (c > e)
        S = (c < ll) & (c < e)
    if fl is not None:
        L &= np.nan_to_num(np.asarray(fl, float)) > 0
    if fs is not None:
        S &= np.nan_to_num(np.asarray(fs, float)) > 0
    return _ent(df, L, S, c - satr * a, c + satr * a, a, "TC")


def run(syms, build, max_bars=250, trail=2.5, exit_on_close=False, trail_fn=None,
        cost_mult=1.0):
    frames = []
    for s in syms:
        try:
            df, atr = prep(s)
        except SystemExit:
            continue
        if len(df) < 400:
            continue
        ent = build(s, df, atr)
        w = df.copy()
        w["atr"] = atr
        spread = cost_mult * COST_BPS.get(s, 5) / 1e4 * df["close"].to_numpy(float)
        tl = ts_ = None
        if trail_fn is not None:
            tl, ts_ = trail_fn(s, df, atr)
        tr = qbt.run(w, ent, spread=spread, max_bars=max_bars, trail_atr=trail,
                     atr_col="atr" if trail else None, exit_on_close=exit_on_close,
                     trail_l=tl, trail_s=ts_)
        if len(tr):
            tr["sym"] = s
            frames.append(tr)
    if not frames:
        return pd.DataFrame()
    # time order matters for drawdown; per-market stacking would make it meaningless
    return pd.concat(frames, ignore_index=True).sort_values("entry_time").reset_index(drop=True)


def eras(tr):
    out = {}
    for name, a, b in ERAS:
        if len(tr) == 0:
            out[name] = {"n": 0}
            continue
        m = ((tr["entry_time"] >= pd.Timestamp(a, tz="UTC"))
             & (tr["entry_time"] < pd.Timestamp(b, tz="UTC")))
        out[name] = qbt.stats(tr[m], name)
    return out


# ── the elements ────────────────────────────────────────────────────────────
def b_base(s, df, atr):
    return tc(df, atr)


def b_struct(thr, strict):
    def f(s, df, atr):
        st = cstruct(s, thr)["state"].to_numpy()
        return tc(df, atr, fl=(st == 1) if strict else (st >= 0),
                  fs=(st == -1) if strict else (st <= 0))
    return f


def b_sma250(s, df, atr):
    c = df["close"].to_numpy(float)
    m = pd.Series(c).rolling(250, min_periods=250).mean().to_numpy()
    with np.errstate(invalid="ignore"):
        return tc(df, atr, fl=c > m, fs=c < m)


def b_weekly(s, df, atr):
    ws = weekly_state(s, 2.0)
    return tc(df, atr, fl=ws == 1, fs=ws == -1)


def b_vol_break(k):
    def f(s, df, atr):
        v = df["volume"].to_numpy(float)
        vma = pd.Series(v).rolling(20, min_periods=20).mean().shift(1).to_numpy()
        with np.errstate(invalid="ignore"):
            ok = (vma > 0) & (v > k * vma)
        return tc(df, atr, fl=ok, fs=ok)
    return f


def b_obv(s, df, atr):
    c = df["close"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
    oe = ema(obv, 50)
    return tc(df, atr, fl=obv > oe, fs=obv < oe)


def b_two_avg(mode):
    """Dow's original test: Industrials and Transports must agree."""
    def f(s, df, atr):
        conf = []
        for avg in ("DJI", "DJT"):
            adf, _ = prep(avg)
            if mode == "struct":
                val = cstruct(avg, 3.0)["state"].to_numpy(float)
            else:
                ac = adf["close"].to_numpy(float)
                val = np.where(ac > ema(ac, 100), 1.0, -1.0)
            conf.append(lagged(val, adf.index, df.index))
        up = (conf[0] == 1) & (conf[1] == 1)
        dn = (conf[0] == -1) & (conf[1] == -1)
        return tc(df, atr, fl=up, fs=dn)
    return f


def b_partner(s, df, atr):
    other = {"XAUUSD": "XAGUSD", "XAGUSD": "XAUUSD"}[s]
    odf, _ = prep(other)
    oc = odf["close"].to_numpy(float)
    val = lagged(np.where(oc > ema(oc, 100), 1.0, -1.0), odf.index, df.index)
    return tc(df, atr, fl=val == 1, fs=val == -1)


def b_dow(s, df, atr):
    """Buy a close above the last peak once the last trough was higher; mirror for shorts."""
    st = cstruct(s, 3.0)
    L = st["bull_bos"].to_numpy(bool) & (st["hl"].to_numpy() == 1)
    S = st["bear_bos"].to_numpy(bool) & (st["hh"].to_numpy() == -1)
    return _ent(df, L, S, st["sl"].to_numpy(float), st["sh"].to_numpy(float),
                atr.to_numpy(float), "DOW")


def t_struct(s, df, atr):
    """Trail the stop to the latest confirmed trough (longs) or peak (shorts)."""
    st = cstruct(s, 3.0)
    return st["sl"].to_numpy(float), st["sh"].to_numpy(float)


TESTS = [
    ("T0  Trend Core baseline",            "UNIVERSE", b_base, {}),
    ("T0b baseline, costs doubled",        "UNIVERSE", b_base, {"cost_mult": 2.0}),
    ("T1  peaks/troughs strict (thr3)",    "UNIVERSE", b_struct(3.0, True), {}),
    ("T1s   same, thr2",                   "UNIVERSE", b_struct(2.0, True), {}),
    ("T1t   same, thr5",                   "UNIVERSE", b_struct(5.0, True), {}),
    ("T2  peaks/troughs lenient (thr3)",   "UNIVERSE", b_struct(3.0, False), {}),
    ("T3  closing-price exit",             "UNIVERSE", b_base, {"exit_on_close": True}),
    ("T4  primary trend: 250d average",    "UNIVERSE", b_sma250, {}),
    ("T5  primary trend: weekly Dow",      "UNIVERSE", b_weekly, {}),
    ("T6  volume: breakout > 20d avg",     "VOL", b_vol_break(1.0), {}),
    ("T6s   same, > 1.25x avg",            "VOL", b_vol_break(1.25), {}),
    ("T7  volume: OBV above its average",  "VOL", b_obv, {}),
    ("T8  two averages DJI+DJT (Dow)",     "US_EQ", b_two_avg("struct"), {}),
    ("T8s   same, trend by EMA100",        "US_EQ", b_two_avg("ema"), {}),
    ("T9  gold/silver confirm each other", "METALPAIR", b_partner, {}),
    ("T10 classic Dow system standalone",  "UNIVERSE", b_dow,
        {"trail": None, "exit_on_close": True, "trail_fn": t_struct, "max_bars": 1000}),
    ("T10b Dow entries, Trend Core exit",  "UNIVERSE", b_dow, {}),
]


if __name__ == "__main__":
    vol_ok = []
    for s in UNIVERSE:
        try:
            df, _ = prep(s)
        except SystemExit:
            continue
        if (df["volume"] > 0).mean() >= 0.90:
            vol_ok.append(s)
    SUBSETS = {"UNIVERSE": UNIVERSE, "VOL": vol_ok, "US_EQ": US_EQ,
               "METALPAIR": ["XAUUSD", "XAGUSD"]}
    print("universe %d instruments; with usable volume: %d" % (len(UNIVERSE), len(vol_ok)))

    base_cache = {}
    rows = []
    for label, sub, build, kw in TESTS:
        subset = SUBSETS[sub]
        if sub not in base_cache:
            base_cache[sub] = eras(run(subset, b_base))
        base = base_cache[sub]
        res = eras(run(subset, build, **kw))
        better_all = True
        for era in (e[0] for e in ERAS):
            r, b = res[era], base[era]
            if r.get("n", 0) == 0 or b.get("n", 0) == 0:
                better = False
            else:
                better = (r["expR"] > b["expR"]) and (r["pf"] > b["pf"])
            better_all = better_all and better
            rows.append({"test": label, "syms": len(subset), "era": era,
                         "n": r.get("n", 0), "win%": r.get("win%", 0), "pf": r.get("pf", 0),
                         "expR": r.get("expR", 0), "totR": r.get("totR", 0),
                         "per_mo": r.get("trades_per_month", 0), "ddR": r.get("maxDD_R", 0),
                         "base_pf": b.get("pf", 0), "base_expR": b.get("expR", 0),
                         "beats": "yes" if better else "no", "verdict": ""})
        if label.startswith("T0 "):
            rows[-1]["verdict"] = "baseline"
        elif label.startswith("T0b"):
            rows[-1]["verdict"] = "cost check"
        else:
            rows[-1]["verdict"] = "ADOPT" if better_all else "reject"
        print(pd.DataFrame(rows[-2:]).to_string(index=False, header=(len(rows) == 2)),
              flush=True)

    pd.DataFrame(rows).to_csv("dow_tests.csv", index=False)
    print()
    print("=== FX in era A as well: does the exclusion hold on older data? ===")
    for era, st in eras(run(FX, b_base)).items():
        print(era, {k: st.get(k) for k in ("n", "win%", "pf", "expR", "totR")})
