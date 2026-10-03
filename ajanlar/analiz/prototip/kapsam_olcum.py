"""Eş anlamlılar listesinin kaç şirkette rakam bulduğunu ölçer (SEC "frames": bir isim, bütün şirketler, tek yıl).
Önce `bash indir.sh frames` çalıştır. Evren: 2024'te net kâr raporlayan, varlığı ≥ 1 milyar $ ve faaliyet kârı raporlayan şirketler.
Not: evren "faaliyet kârı raporlayan" diye seçildiği için faaliyet kârı oranı tanım gereği %100 çıkar (yanıltıcı)."""
import json

def ciks(name):
    try: return {x["cik"] for x in json.load(open(name))["data"]}
    except Exception: return set()

g = lambda t, u="USD": ciks(f"frames/us-gaap_{t}_{u}.json")
assets = {x["cik"]: x["val"] for x in json.load(open("frames/us-gaap_Assets_USD.json"))["data"]}
uni = g("NetIncomeLoss") & {c for c, v in assets.items() if v >= 1e9} & g("OperatingIncomeLoss")
print(f"Evren: {len(uni)} şirket")

def cov(label, sets):
    u = set().union(*sets)
    print(f"{label:44s} %{len(uni & u) / len(uni) * 100:.0f}")

rev = [g(t) for t in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                      "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"]]
cov("Gelir (4 isim)", rev)
cost = set().union(*[g(t) for t in ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"]])
cov("Brüt kâr (doğrudan veya gelir − maliyet)", [g("GrossProfit"), set().union(*rev) & cost])
cov("İşletme nakit akışı", [g("NetCashProvidedByUsedInOperatingActivities")])
cov("Yatırım harcaması (2 isim)", [g("PaymentsToAcquirePropertyPlantAndEquipment"), g("PaymentsToAcquireProductiveAssets")])
cov("Faiz gideri (5 isim)", [g(t) for t in ["InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt",
                                            "InterestAndDebtExpense", "InterestPaidNet"]])
cov("Borç parçalarından en az biri (10 isim)", [g(t) for t in [
    "LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligations", "LongTermDebtCurrent",
    "ConvertibleDebtNoncurrent", "ConvertibleNotesPayable", "LongTermNotesPayable", "DebtCurrent",
    "ShortTermBorrowings", "CommercialPaper"]])
cov("Hisse sayısı (2 isim)", [g("WeightedAverageNumberOfDilutedSharesOutstanding", "shares"),
                              ciks("frames/dei_EntityCommonStockSharesOutstanding_shares.json")])
cov("Hisseyle ödenen maaş (2 isim)", [g("ShareBasedCompensation"), g("AllocatedShareBasedCompensationExpense")])
