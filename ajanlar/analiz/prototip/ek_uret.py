import json, yfinance as yf
from karne_deneme import analiz, fmt, AD
T=["KO","NVDA","NKE","SBUX","PFE","INTC","BA","SNAP","DOW","RIVN"]
AD_TR={"KO":"Coca-Cola","NVDA":"Nvidia","NKE":"Nike","SBUX":"Starbucks","PFE":"Pfizer","INTC":"Intel","BA":"Boeing","SNAP":"Snap","DOW":"Dow","RIVN":"Rivian"}
R={t:analiz(t) for t in T}
fiyat=json.load(open("fiyat.json"))
L=[]
# Sonuç matrisi
for grp in (T[:5],T[5:]):
    L.append("| Ölçü | "+" | ".join(f"{AD_TR[t]} ({t})" for t in grp)+" |"); L.append("|---|"+"---|"*len(grp))
    for k in range(1,11):
        cells=[]
        for t in grp:
            r=R[t]; v=fmt(k,r["M"][k]).replace("hesaplanamadı","—")
            b="**" if k in r["bel"] else ""
            cells.append(f"{b}{r['R'][k]} {v}{b}")
        L.append(f"| {k}. {AD[k]} | "+" | ".join(cells)+" |")
    L.append("| Borç (6+7 birleşik) | "+" | ".join(("**"+R[t]["borc_r"]+"**") if "B" in R[t]["bel"] else R[t]["borc_r"] for t in grp)+" |")
    L.append("| T. Temettü (5y) | "+" | ".join(("**"+R[t]["tem_r"]+"**") if "T" in R[t]["bel"] else R[t]["tem_r"] for t in grp)+" |")
    L.append("| Serbest nakit 3y ort. (milyar $) | "+" | ".join(f"{R[t]['fcf3']/1e9:.2f}" for t in grp)+" |")
    L.append("| **Tür → Sınıf** | "+" | ".join(f"{R[t]['tur']} → **{R[t]['sinif']}**" for t in grp)+" |")
    def fv(t):
        f=fiyat.get(t); 
        if not f: return "—"
        peg="hesaplanamaz" if f["peg"] is None else f"{f['peg']:.2f}"
        return f"PEG {peg} · nakit verimi {f['fv']*100:.1f}%"
    L.append("| Fiyat satırı | "+" | ".join(fv(t) for t in grp)+" |")
    L.append("")
open("ek_sonuc.md","w").write("\n".join(L))
# Ham veri
H=[]
rows=[("Gelir","gelir"),("Brüt kâr (doğrudan ya da gelir−maliyet)","brut"),("Faaliyet kârı","faal"),("Vergi öncesi kâr","vo"),
      ("Faiz gideri","faiz"),("Net kâr","net"),("İşletme nakdi","on"),("Yatırım harcaması","yat"),("Serbest nakit","fcf"),
      ("Nakit + kısa vadeli yatırım","likit"),("Toplam varlık","varlik"),("Kısa vadeli yükümlülük","kvy_"),("Özkaynak","oz"),
      ("Borç (toplam)","borc"),("Ödenen temettü","tem"),("Seyreltilmiş ort. hisse (milyon, ham)","hisse")]
for t in T:
    r=R[t]; Y=r["Y"]
    H.append(f"#### {AD_TR[t]} ({t}) — mali yıl sonları: "+", ".join(Y)+f" · tür: {r['tur']} · sınıf: {r['sinif']}")
    H.append("")
    H.append("| Kalem (milyar $) | "+" | ".join(e[:7] for e in Y)+" |"); H.append("|---|"+"---|"*len(Y))
    for ad,k in rows:
        d=r[k]
        vals=[]
        for e in Y:
            v=d.get(e)
            if isinstance(v,tuple): v=v[0]
            if v is None: vals.append("—")
            elif k=="hisse": vals.append(f"{v/1e6:,.0f}")
            else: vals.append(f"{v/1e9:.2f}")
        H.append(f"| {ad} | "+" | ".join(vals)+" |")
    src=r["borc"][Y[-1]][1]
    H.append(""); H.append(f"Son yıl borç kaynağı (XBRL isimleri): {', '.join(src) or 'yok'} · faaliyet kârı kaynağı: {r['faal_kaynak'].get(Y[-1],'—')}"
             + (f" · hisse: {', '.join(r['bolunme'])}" if r['bolunme'] else ""))
    H.append("")
open("ek_ham.md","w").write("\n".join(H))
# Yahoo bölünme sağlaması
for t in T:
    try: sp=yf.Ticker(t).splits
    except Exception as e: sp=f"hata {e}"
    sp2 = {str(i.date()):float(v) for i,v in sp.items() if i.year>=2019} if hasattr(sp,"items") else sp
    print(t, "kod tespiti:", R[t]["bolunme"], "| Yahoo (2019+):", sp2)
