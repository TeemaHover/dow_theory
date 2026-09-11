# -*- coding: utf-8 -*-
"""Download OHLCV from the Yahoo chart API into data/ as npz files.

Tags written:
  H1  - hourly, last 730 days
  M15 - 15 minute, last 60 days
  D1  - daily, last 10 years
  D1L - daily from 2000, via explicit period bounds (range=max returns monthly bars)

Usage: python qdownload.py SYMBOLS TAGS      e.g.  python qdownload.py all D1L
"""
import urllib.request, urllib.parse, json, time, os, sys, datetime as dt
import numpy as np

OUT = "D:/Indicator/data"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

MAP = {
 # metals
 "XAUUSD": "GC=F", "XAGUSD": "SI=F", "PLATINUM": "PL=F", "PALLADIUM": "PA=F", "COPPER": "HG=F",
 # energy
 "WTI": "CL=F", "NATGAS": "NG=F", "HEATOIL": "HO=F", "GASOLINE": "RB=F",
 # agriculturals
 "CORN": "ZC=F", "SOYBEAN": "ZS=F", "WHEAT": "ZW=F", "COFFEE": "KC=F", "SUGAR": "SB=F",
 "COTTON": "CT=F", "COCOA": "CC=F",
 # equity indices
 "SPX500": "ES=F", "NAS100": "NQ=F", "DOW30": "YM=F", "RUSSELL": "RTY=F",
 "NIKKEI": "^N225", "FTSE": "^FTSE", "DAX": "^GDAXI",
 # rates
 "TNOTE": "ZN=F", "TBOND": "ZB=F",
 # the two Dow averages, and gold miners as gold's closest confirming partner
 "DJI": "^DJI", "DJT": "^DJT", "GDX": "GDX",
 # expansion, fixed before testing: remaining liquid markets in the same classes
 "BRENT": "BZ=F", "SOYOIL": "ZL=F", "SOYMEAL": "ZM=F", "OATS": "ZO=F", "RICE": "ZR=F",
 "OJ": "OJ=F", "LIVECATTLE": "LE=F", "FEEDERCATTLE": "GF=F", "LEANHOGS": "HE=F",
 "KCWHEAT": "KE=F", "HANGSENG": "^HSI", "STOXX50": "^STOXX50E", "CAC40": "^FCHI",
 "ASX200": "^AXJO", "TSX": "^GSPTSE", "TNOTE5": "ZF=F", "TNOTE2": "ZT=F",
 # currencies
 "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "JPY=X", "AUDUSD": "AUDUSD=X",
 "USDCAD": "USDCAD=X", "USDCHF": "USDCHF=X", "NZDUSD": "NZDUSD=X", "DXY": "DX-Y.NYB",
 "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X", "GBPJPY": "GBPJPY=X", "AUDJPY": "AUDJPY=X",
 "CADJPY": "CADJPY=X", "CHFJPY": "CHFJPY=X", "NZDJPY": "NZDJPY=X", "EURAUD": "EURAUD=X",
 "EURCAD": "EURCAD=X", "EURCHF": "EURCHF=X", "EURNZD": "EURNZD=X", "GBPAUD": "GBPAUD=X",
 "GBPCAD": "GBPCAD=X", "GBPCHF": "GBPCHF=X", "AUDCAD": "AUDCAD=X", "AUDCHF": "AUDCHF=X",
 "AUDNZD": "AUDNZD=X", "NZDCAD": "NZDCAD=X", "CADCHF": "CADCHF=X",
 # other
 "WTI_": "CL=F",
}
del MAP["WTI_"]

SPEC = {"H1": ("1h", "730d"), "M15": ("15m", "60d"), "D1": ("1d", "10y"), "D1L": ("1d", None)}

def fetch(ticker, interval, rng=None, p1=None, p2=None, tries=4):
    base = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(ticker)
    q = ("?interval=%s&range=%s" % (interval, rng)) if rng else (
        "?interval=%s&period1=%d&period2=%d" % (interval, p1, p2))
    last = None
    for i in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(base + q, headers=UA), timeout=40)
            return json.loads(r.read())
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last

def save(j, path):
    res = j["chart"]["result"][0]
    ts = np.asarray(res.get("timestamp") or [], dtype=np.int64)
    if len(ts) == 0:
        return 0
    q = res["indicators"]["quote"][0]
    def arr(k):
        return np.asarray([np.nan if v is None else v for v in q.get(k, [])], dtype=np.float64)
    o, h, l, c, v = arr("open"), arr("high"), arr("low"), arr("close"), arr("volume")
    if len(v) != len(ts):
        v = np.zeros(len(ts))
    ok = np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c) & (o > 0) & (c > 0)
    if ok.sum() < 50:
        return 0
    ts, o, h, l, c, v = ts[ok], o[ok], h[ok], l[ok], c[ok], v[ok]
    k = np.argsort(ts, kind="stable")
    ts, o, h, l, c, v = ts[k], o[k], h[k], l[k], c[k], v[k]
    keep = np.concatenate(([True], np.diff(ts) > 0))
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(path, t=ts[keep], o=o[keep].astype(np.float32), h=h[keep].astype(np.float32),
                        l=l[keep].astype(np.float32), c=c[keep].astype(np.float32),
                        v=np.nan_to_num(v[keep]).astype(np.float32))
    return int(keep.sum())

if __name__ == "__main__":
    names = list(MAP) if (len(sys.argv) < 2 or sys.argv[1] == "all") else sys.argv[1].split(",")
    tags = (sys.argv[2] if len(sys.argv) > 2 else "H1,M15,D1").split(",")
    p1 = int(dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc).timestamp())
    p2 = int(time.time())
    for name in names:
        tk = MAP.get(name)
        if not tk:
            print("unknown", name); continue
        for tag in tags:
            path = os.path.join(OUT, "%s_%s_yahoo.npz" % (name, tag))
            if os.path.exists(path):
                print("%-9s %-4s cached" % (name, tag), flush=True); continue
            iv, rng = SPEC[tag]
            try:
                j = fetch(tk, iv, rng=rng) if rng else fetch(tk, iv, p1=p1, p2=p2)
                print("%-9s %-4s %6d bars" % (name, tag, save(j, path)), flush=True)
            except Exception as e:
                print("%-9s %-4s FAIL %s" % (name, tag, str(e)[:50]), flush=True)
            time.sleep(0.5)
