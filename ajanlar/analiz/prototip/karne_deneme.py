"""Deneme: 10 ölçü + tür + sınıf kuralı, gerçek SEC verisiyle. Projeye ait değil (scratchpad)."""
import json, sys
from datetime import date

SEKTOR = {"KO": "Zorunlu tüketim", "NVDA": "Bilgi teknolojisi", "NKE": "Zorunlu olmayan tüketim",
          "SBUX": "Zorunlu olmayan tüketim", "PFE": "Sağlık", "INTC": "Bilgi teknolojisi", "BA": "Sanayi",
          "SNAP": "İletişim hizmetleri", "DOW": "Malzeme", "RIVN": "Zorunlu olmayan tüketim"}

ES = {  # eş anlamlılar listeleri
    "gelir": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
              "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "maliyet": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "brut": ["GrossProfit"],
    "faaliyet": ["OperatingIncomeLoss"],
    "vergi_oncesi": ["IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                     "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"],
    "vergi": ["IncomeTaxExpenseBenefit"],
    "net": ["NetIncomeLoss"],
    "faiz": ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt", "InterestAndDebtExpense", "InterestPaidNet"],
    "isletme_nakit": ["NetCashProvidedByUsedInOperatingActivities"],
    "yatirim": ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    "nakit": ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"],
    "kv_yatirim": ["MarketableSecuritiesCurrent", "ShortTermInvestments", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "ozkaynak": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "hisse": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
    "temettu": ["PaymentsOfDividends", "PaymentsOfDividendsCommonStock", "PaymentsOfOrdinaryDividends"],
    "varlik": ["Assets"], "kv_yukumluluk": ["LiabilitiesCurrent"],
    "hbk": ["EarningsPerShareDiluted"],
}
BORC_UV = [["LongTermDebt"], ["LongTermDebtNoncurrent", "LongTermDebtCurrent"],
           ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebtAndCapitalLeaseObligationsCurrent"],
           ["ConvertibleDebtNoncurrent", "ConvertibleDebtCurrent", "ConvertibleNotesPayable", "LongTermNotesPayable"]]
BORC_KV = ["CommercialPaper", "ShortTermBorrowings"]


def d(s): return date.fromisoformat(s)


class Sirket:
    def __init__(self, t):
        self.t = t
        self.f = json.load(open(f"{t}.json"))["facts"].get("us-gaap", {})
        self.yil_sonu = self._yil_sonlari()

    def _sure(self, tag, unit="USD"):
        """Yıllık (≈1 yıl) dönem değerleri: {bitiş tarihi: değer}, en son dosyalanan kazanır."""
        out = {}
        for x in self.f.get(tag, {}).get("units", {}).get(unit, []):
            if x.get("form") not in ("10-K", "10-K/A") or "start" not in x: continue
            gun = (d(x["end"]) - d(x["start"])).days
            if 350 <= gun <= 380:
                if x["end"] not in out or x["filed"] > out[x["end"]][1]:
                    out[x["end"]] = (x["val"], x["filed"])
        return {k: v[0] for k, v in out.items()}

    def _an(self, tag, unit="USD"):
        out = {}
        for x in self.f.get(tag, {}).get("units", {}).get(unit, []):
            if x.get("form") not in ("10-K", "10-K/A") or "start" in x: continue
            if x["end"] not in out or x["filed"] > out[x["end"]][1]:
                out[x["end"]] = (x["val"], x["filed"])
        return {k: v[0] for k, v in out.items()}

    def _yil_sonlari(self):
        ends = set()
        for tg in ES["gelir"] + ES["faaliyet"]:
            ends |= set(self._sure(tg))
        return sorted(ends)[-6:]  # son 6 mali yıl

    def seri(self, kavram, unit="USD", anlik=False):
        """Her yıl için eş anlamlıları SIRAYLA dene; ilk bulunan. {yıl_sonu: (değer, isim)}"""
        tablolar = [(tg, (self._an if anlik else self._sure)(tg, unit)) for tg in ES[kavram]]
        out = {}
        for e in self.yil_sonu:
            for tg, tb in tablolar:
                if e in tb:
                    out[e] = (tb[e], tg); break
        return out

    def borc(self):
        out = {}
        for e in self.yil_sonu:
            parca, kaynak = 0.0, []
            for grup in BORC_UV:
                vals = [(tg, self._an(tg).get(e)) for tg in grup]
                vals = [(tg, v) for tg, v in vals if v is not None]
                if vals:
                    parca += sum(v for _, v in vals); kaynak += [tg for tg, _ in vals]; break
            for tg in BORC_KV:
                v = self._an(tg).get(e)
                if v: parca += v; kaynak.append(tg)
            out[e] = (parca, kaynak)
        return out


def cagr(a, b, n):
    if a is None or b is None or a <= 0 or b <= 0 or n <= 0: return None
    return (b / a) ** (1 / n) - 1


def renk(v, iyi, orta, ters=False):
    """iyi/orta eşikleri; ters=True ise küçük olan iyidir."""
    if v is None: return "·"
    if not ters: return "✅" if v >= iyi else ("➖" if v >= orta else "❌")
    return "✅" if v <= iyi else ("➖" if v <= orta else "❌")


def analiz(t, fiyat=None):
    s = Sirket(t)
    Y = s.yil_sonu
    g = lambda k, **kw: {e: v[0] for e, v in s.seri(k, **kw).items()}
    gelir, maliyet, brut = g("gelir"), g("maliyet"), g("brut")
    faal, vo, vergi, net = g("faaliyet"), g("vergi_oncesi"), g("vergi"), g("net")
    faiz_s = s.seri("faiz"); faiz = {e: v[0] for e, v in faiz_s.items()}
    on, yat = g("isletme_nakit"), g("yatirim")
    nakit, kvy, oz = g("nakit", anlik=True), g("kv_yatirim", anlik=True), g("ozkaynak", anlik=True)
    hisse = g("hisse", unit="shares"); tem = g("temettu"); hbk = g("hbk", unit="USD/shares")
    borc = s.borc()
    for e in Y:  # brüt kâr yoksa gelir − maliyet
        if e not in brut and e in gelir and e in maliyet: brut[e] = gelir[e] - maliyet[e]
    faal_kaynak = {}
    for e in Y:
        if e in faal: faal_kaynak[e] = "OperatingIncomeLoss"
        elif e in vo:
            faal[e] = vo[e] + (faiz.get(e) or 0); faal_kaynak[e] = "yaklaşık: vergi öncesi kâr + faiz"
    fcf = {e: on[e] - yat.get(e, 0) for e in Y if e in on}
    fcf3 = sum(fcf.get(e, 0) for e in Y[-3:]) / 3
    varlik, kvy_ = g("varlik", anlik=True), g("kv_yukumluluk", anlik=True)
    # hisse sayısı: ilk 10-K yılı atla (halka arz), tam kat sıçrama = bölünme → düzelt
    ilk_10k = min(x["fy"] for v in s.f.values() for u in v["units"].values() for x in u if x.get("form") == "10-K" and x.get("fy"))
    hy = [e for e in Y if e in hisse and int(e[:4]) > ilk_10k] if int(Y[0][:4]) <= ilk_10k else [e for e in Y if e in hisse]
    hy = hy[-6:]
    duz = dict(hisse); bolunme = []
    for a, b in zip(hy, hy[1:]):
        r = duz[b] / duz[a]
        for k in (2, 3, 4, 5, 8, 10, 20):
            if abs(r - k) / k < 0.06:
                for e in hy[:hy.index(b)]: duz[e] *= k
                bolunme.append(f"bölünme düzeltildi (×{k})"); break
    hisse_ilk = hy[0] if hy else None
    likit = {e: nakit.get(e, 0) + kvy.get(e, 0) for e in Y}
    son = Y[-1]
    i3 = Y[-4] if len(Y) >= 4 else Y[0]
    i5 = Y[-6] if len(Y) >= 6 else Y[0]
    n3 = len(Y[Y.index(i3):]) - 1; n5 = len(Y[Y.index(i5):]) - 1

    M, A = {}, {}  # ölçü değeri, açıklama
    # 1 gelir büyümesi (3 yıl)
    M[1] = cagr(gelir.get(i3), gelir.get(son), n3)
    # 2 brüt marj istikrarı (son yıl − 5 yıl ort.), yoksa faaliyet marjı
    gm = {e: brut[e] / gelir[e] for e in Y if e in brut and e in gelir and gelir[e]}
    taban, adi = (gm, "brüt") if len(gm) >= 3 else ({e: faal[e] / gelir[e] for e in Y if e in faal and e in gelir and gelir[e]}, "faaliyet")
    son5 = [taban[e] for e in Y[-5:] if e in taban]
    M[2] = (taban[son] - sum(son5) / len(son5)) * 100 if son in taban and son5 else None
    A[2] = f"{adi} marj {taban.get(son, 0)*100:.1f}% (5y ort {sum(son5)/len(son5)*100:.1f}%)" if son5 else ""
    # 3 faaliyet marjı
    M[3] = faal[son] / gelir[son] if son in faal and son in gelir else None
    # 4 sermaye getirisi (5 yıl ort.)
    roics = []
    for e in Y[-5:]:
        if e not in faal: continue
        vo_e, vg = vo.get(e), vergi.get(e)
        vr = min(max(vg / vo_e, 0), 0.35) if vo_e and vo_e > 0 and vg is not None else 0.21
        if e not in varlik or e not in kvy_: continue
        ic = varlik[e] - kvy_[e] - likit[e]
        if ic > 0: roics.append(faal[e] * (1 - vr) / ic)
    M[4] = sum(roics) / len(roics) if len(roics) >= 3 else None
    A[4] = f"{len(roics)} yıl"
    # 5 nakde dönüşüm (3 yıl)
    ny = Y[-3:]
    sn, sf = sum(net.get(e, 0) for e in ny), sum(fcf.get(e, 0) for e in ny)
    M[5] = sf / sn if sn > 0 else None
    A[5] = "net kâr ≤ 0 → anlamsız" if sn <= 0 else ""
    # 6 faiz karşılama
    net_nakit = likit[son] >= borc[son][0]
    if net_nakit: M[6], A[6] = "NN", "nakit > borç"
    elif faiz.get(son) and son in faal: M[6], A[6] = faal[son] / faiz[son], faiz_s[son][1]
    else: M[6], A[6] = None, "faiz bulunamadı"
    # 7 borcu kaç yılda öder
    nb = borc[son][0] - likit[son]
    if nb <= 0: M[7] = "NN"
    elif fcf3 <= 0: M[7] = "FCF-"
    else: M[7] = nb / fcf3
    A[7] = "+".join(borc[son][1]) or "borç ismi yok"
    # 8 hisse sayısı (5 yıl)
    M[8] = duz[son] / duz[hisse_ilk] - 1 if son in duz and hisse_ilk else None
    A[8] = f"{son[:4] if False else ''}{hisse_ilk[:4] if hisse_ilk else ''}→{son[:4]} " + ", ".join(bolunme)
    # 9 brüt kâr büyümesi (3 yıl)
    M[9] = cagr(brut.get(i3), brut.get(son), n3)
    if M[9] is None and brut.get(i3) is not None and brut.get(i3) <= 0 < brut.get(son, 0): M[9] = 'POZ'; A[9] = 'zarardan kâra döndü (yeni)'
    # 10 nakit kaç yıl yeter
    M[10] = "FCF+" if fcf3 >= 0 else likit[son] / -fcf3

    sek = SEKTOR[t]
    oi5 = [faal[e] for e in Y[-5:] if e in faal]
    kar_yili = sum(1 for v in oi5 if v > 0)
    dongusel = sek in ("Enerji", "Malzeme") or (any(v > 0 for v in oi5) and any(v < 0 for v in oi5))
    if dongusel: tur = "Döngüsel"
    elif M[1] is not None and M[1] >= .15: tur = "Hızlı büyüyen"
    elif kar_yili < 4: tur = "Kârsız"
    elif M[1] is not None and M[1] >= .05: tur = "İstikrarlı dev"
    else: tur = "Yavaş büyüyen"
    sert10 = tur == "Hızlı büyüyen" and fcf3 < 0
    R = {  # renkler
        1: renk(M[1], .15, .08), 2: renk(M[2], -1, -3),
        3: renk(M[3], .15, .05), 4: renk(M[4], .15, .08), 5: renk(M[5], .80, .50),
        6: "✅" if M[6] == "NN" else renk(M[6], 8, 3),
        7: "✅" if M[7] == "NN" else ("❌" if M[7] == "FCF-" else renk(M[7], 3, 5, ters=True)),
        8: renk(M[8], 0, .10, ters=True), 9: '➖' if M[9] == 'POZ' else renk(M[9], .20, .10),
        10: "✅" if M[10] == "FCF+" else (renk(M[10], 5, 3) if sert10 else renk(M[10], 3, 1.5)),
    }
    # temettü karşılama (3 yıl)
    y5 = Y[-5:]
    st = sum(tem.get(e, 0) for e in y5); sf5 = sum(fcf.get(e, 0) for e in y5)
    tem_r = "·" if st == 0 else ("✅" if sf5 >= st else "❌")
    # Borç (6+7 birleşik): faiz karşılamanın rengi; borç yılı ❌ ise bir basamak düşür
    sira = ["❌", "➖", "✅"]
    b6, b7 = R[6], R[7]
    borc_r = b6 if b6 != "·" else b7
    if borc_r != "·" and b7 == "❌" and b6 != "·": borc_r = sira[max(sira.index(borc_r) - 1, 0)]

    bel = {"İstikrarlı dev": [2, 3, 4, 5], "Hızlı büyüyen": [1, 9, 2, 10, 8],
           "Yavaş büyüyen": [2, 4, 5, "B", "T"], "Döngüsel": [4, "B", 8], "Kârsız": [2, 3, 4, 5]}[tur]
    br = [tem_r if b == "T" else (borc_r if b == "B" else R[b]) for b in bel]
    hesap = [x for x in br if x != "·"]
    kirmizi, yesil = br.count("❌"), br.count("✅")
    if len(hesap) * 2 < len(br): sinif = "BELİRSİZ"
    elif kirmizi >= 2: sinif = "ZAYIF"
    elif kirmizi == 0 and yesil * 2 >= len(br): sinif = "SAĞLAM"
    else: sinif = "ORTA"
    # küçülme kuralı: gelir 3 yıl üst üste düştüyse sağlam olamaz
    kuculme = M[1] is not None and M[1] < 0
    if kuculme and sinif == "SAĞLAM": sinif = "ORTA (küçülme kuralı)"

    A[3] = faal_kaynak.get(son, "")
    return dict(borc_r=borc_r, fcf3=fcf3, sert10=sert10, bolunme=bolunme, likit=likit, borc=borc, vo=vo, faiz=faiz,
                oz=oz, varlik=varlik, kvy_=kvy_, on=on, yat=yat, tem=tem, brut=brut, faal_kaynak=faal_kaynak, t=t, son=son, tur=tur, sek=sek, M=M, R=R, A=A, bel=bel, br=br, sinif=sinif, tem_r=tem_r,
                kuculme=kuculme, gelir=gelir, fcf=fcf, Y=Y, net=net, hisse=hisse, hbk=hbk, gm=gm, faal=faal)


def fmt(k, v):
    if v is None: return "hesaplanamadı"
    if v == "NN": return "nakit > borç"
    if v == "FCF-": return "nakit üretmiyor, borç var"
    if v == "FCF+": return "nakit üretiyor"
    if v == "POZ": return "zarardan kâra döndü"
    if k == 2: return f"{v:+.1f} puan"
    if k in (6, 7, 10): return f"{v:.1f}"
    return f"{v*100:+.1f}%" if k in (1, 8, 9) else f"{v*100:.1f}%"


AD = {1: "Gelir büyümesi (3y)", 2: "Marj istikrarı", 3: "Faaliyet marjı", 4: "Sermaye getirisi (5y, ROCE)",
      5: "Nakde dönüşüm (3y)", 6: "Faiz karşılama (kat)", 7: "Borcu öder (yıl)", 8: "Hisse sayısı (5y)",
      9: "Brüt kâr büyümesi (3y)", 10: "Nakit yeter (yıl)"}

if __name__ == "__main__":
    out = {}
    for t in sys.argv[1:]:
        r = analiz(t)
        out[t] = r
        print(f"\n===== {t} · {r['sek']} · son mali yıl {r['son']} · TÜR: {r['tur']} · SINIF: {r['sinif']}")
        for k in range(1, 11):
            isaret = "◆" if k in r["bel"] else " "
            print(f"  {isaret} {k:>2} {AD[k]:24s} {r['R'][k]} {fmt(k, r['M'][k]):28s} {r['A'].get(k, '')}")
        if "B" in r["bel"]: print(f"  ◆  B Borç (6+7 birleşik)          {r['borc_r']}")
        if "T" in r["bel"]: print(f"  ◆  T Temettü nakitle karşılanıyor (5y) {r['tem_r']}")
        print("     FCF (milyar $): " + "  ".join(f"{e[:4]}:{r['fcf'][e]/1e9:.1f}" for e in r["Y"] if e in r["fcf"]))
        print("     Gelir (milyar $): " + "  ".join(f"{e[:4]}:{r['gelir'][e]/1e9:.1f}" for e in r["Y"] if e in r["gelir"]))
        print(f"     belirleyiciler {r['bel']} → {r['br']}  küçülme={r['kuculme']}")
    json.dump({t: {"son": r["son"], "fcf_son": r["fcf"].get(r["son"]),
                   "hbk": {e: r["hbk"][e] for e in r["Y"] if e in r["hbk"]},
                   "hisse_son": r["hisse"].get(r["son"])} for t, r in out.items()}, open("ozet.json", "w"))
