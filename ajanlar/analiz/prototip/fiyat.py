import json, yfinance as yf
from karne_deneme import analiz
out = {}
for t in ["KO","NVDA","NKE","SBUX","PFE","INTC","BA","SNAP","DOW","RIVN"]:
    r = analiz(t)
    try:
        tk = yf.Ticker(t); fi = tk.fast_info
        fiyat, pd = float(fi["last_price"]), float(fi["market_cap"])
        info = tk.info; pe = info.get("trailingPE")
    except Exception as e:
        print(t, "fiyat alınamadı:", e); continue
    Y = r["Y"]; net = r["net"]; son = Y[-1]; i3 = Y[-4]
    a, b = net.get(i3), net.get(son)
    buy = ((b / a) ** (1/3) - 1) if a and b and a > 0 and b > 0 else None
    peg = (pe / (buy * 100)) if pe and buy and buy > 0 else None
    fv = r["fcf"].get(son, 0) / pd
    out[t] = dict(fiyat=fiyat, pd=pd, pe=pe, buy=buy, peg=peg, fv=fv)
    pegs = "anlamsız (kâr yok ya da düşüyor)" if peg is None else f"{peg:.2f} ({'cazip' if peg<=1 else 'makul' if peg<=2 else 'pahalı'})"
    fvs = f"{fv*100:.1f}% ({'cazip' if fv>=.05 else 'makul' if fv>=.02 else 'pahalı' if fv>0 else 'nakit yakıyor'})"
    print(f"{t:5s} fiyat {fiyat:8.2f}$  piyasa değeri {pd/1e9:7.0f} milyar$  F/K {pe if pe is None else round(pe,1)}  "
          f"net kâr büy.(3y) {'—' if buy is None else f'{buy*100:.1f}%'}  PEG {pegs}  FCF verimi {fvs}")
json.dump(out, open("fiyat.json","w"))
