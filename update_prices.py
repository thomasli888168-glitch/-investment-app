#!/usr/bin/env python3
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

TICKERS = ["2330.TW", "00981A.TW", "2880.TW", "2892.TW", "TSMY"]
FX_TICKER = "TWD=X"

def yahoo_chart(symbol):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol, safe="") + "?range=5d&interval=1d&events=div%2Csplits"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 investment-app/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def latest(symbol):
    data = yahoo_chart(symbol)
    result = data.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError("Yahoo Finance 無資料")
    meta = result[0].get("meta", {})
    price = meta.get("regularMarketPrice")
    ts = meta.get("regularMarketTime")
    if price is None:
        closes = (result[0].get("indicators", {}).get("quote") or [{}])[0].get("close") or []
        price = next((x for x in reversed(closes) if x is not None), None)
        ts_list = result[0].get("timestamp") or []
        ts = ts_list[-1] if ts_list else None
    if price is None:
        raise RuntimeError("找不到最新價格")
    if ts:
        d = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
    else:
        d = ""
    return float(price), d

def main():
    out = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at_tw": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "prices": {},
        "fx": {},
        "errors": {}
    }

    for symbol in TICKERS:
        try:
            p, d = latest(symbol)
            out["prices"][symbol] = {"price": p, "date": d}
        except Exception as e:
            out["errors"][symbol] = str(e)

    try:
        fx, d = latest(FX_TICKER)
        out["fx"]["USD_TWD"] = {"value": fx, "date": d}
    except Exception as e:
        out["errors"]["USD_TWD"] = str(e)

    # Keep the file valid even if one symbol temporarily fails.
    old_path = "prices.json"
    if os.path.exists(old_path):
        try:
            old = json.load(open(old_path, encoding="utf-8"))
            for symbol, value in old.get("prices", {}).items():
                if symbol not in out["prices"]:
                    out["prices"][symbol] = value
            if "USD_TWD" not in out["fx"] and old.get("fx", {}).get("USD_TWD"):
                out["fx"]["USD_TWD"] = old["fx"]["USD_TWD"]
        except Exception:
            pass

    with open(old_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(json.dumps(out, ensure_ascii=False, indent=2))
    if not out["prices"]:
        sys.exit("所有行情都抓取失敗")

if __name__ == "__main__":
    main()
