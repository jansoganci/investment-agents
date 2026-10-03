"""Yahoo data for the trial: price, market cap (USD), split history, FX to USD.
Run: uv run --with yfinance python yahoo_indir.py KO NVDA ...   → writes yahoo.json"""
import json
import sys
import yfinance as yf
from karne_deneme import Company

out = {}
for t in sys.argv[1:]:
    tk = yf.Ticker(t)
    fi, info = tk.fast_info, tk.info
    unit = Company(t).unit
    fx = 1.0
    if unit != "USD":
        fx = float(yf.Ticker(f"{unit}USD=X").fast_info["last_price"])
    # splits with dates; whole ratios only (Yahoo also lists spin-off adjustments such as Pfizer 1.054)
    splits = [[str(i.date()), float(v)] for i, v in tk.splits.items() if float(v) >= 1.5 or float(v) <= 0.67]
    # P/E and dividend yield are computed from SEC figures × FX (Yahoo mixes currencies on ADRs)
    out[t] = {"price": float(fi["last_price"]), "market_cap": float(fi["market_cap"]), "currency": unit, "fx": fx,
              "splits": splits}
    print(t, out[t])
json.dump(out, open("yahoo.json", "w"), indent=1)
