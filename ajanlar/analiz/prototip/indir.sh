#!/usr/bin/env bash
# SEC verisini indirir (ücretsiz, anahtar yok). SEC, isteklerde iletişim bilgisi içeren bir User-Agent ister:
#   export SEC_UA="Ad Soyad eposta@ornek.com"
# Kullanım: bash indir.sh            → 10 deneme şirketinin companyfacts dosyaları
#           bash indir.sh frames     → kapsam ölçümü için "frames" dosyaları (tüm şirketler, 2024)
set -euo pipefail
cd "$(dirname "$0")"
UA="${SEC_UA:-investment-agents-research admin@example.com}"
if [ "${1:-}" = "frames" ]; then
  mkdir -p frames
  get(){ f="frames/$1_$2_$3.json"; [ -s "$f" ] || { curl -s -m 90 -A "$UA" "https://data.sec.gov/api/xbrl/frames/$1/$2/$3/$4.json" -o "$f"; sleep 0.3; }; }
  get us-gaap NetIncomeLoss USD CY2024; get us-gaap Assets USD CY2024Q4I; get us-gaap OperatingIncomeLoss USD CY2024
  for t in Revenues RevenueFromContractWithCustomerExcludingAssessedTax RevenueFromContractWithCustomerIncludingAssessedTax SalesRevenueNet \
           GrossProfit CostOfRevenue CostOfGoodsAndServicesSold CostOfGoodsSold NetCashProvidedByUsedInOperatingActivities \
           PaymentsToAcquirePropertyPlantAndEquipment PaymentsToAcquireProductiveAssets InterestExpense InterestExpenseNonoperating \
           InterestExpenseDebt InterestAndDebtExpense InterestPaidNet ShareBasedCompensation AllocatedShareBasedCompensationExpense; do
    get us-gaap "$t" USD CY2024; done
  for t in LongTermDebt LongTermDebtNoncurrent LongTermDebtAndCapitalLeaseObligations LongTermDebtCurrent ConvertibleDebtNoncurrent \
           ConvertibleNotesPayable LongTermNotesPayable DebtCurrent ShortTermBorrowings CommercialPaper; do
    get us-gaap "$t" USD CY2024Q4I; done
  get us-gaap WeightedAverageNumberOfDilutedSharesOutstanding shares CY2024
  get dei EntityCommonStockSharesOutstanding shares CY2024Q4I
  exit 0
fi
for c in KO:0000021344 NVDA:0001045810 NKE:0000320187 SBUX:0000829224 PFE:0000078003 INTC:0000050863 \
         BA:0000012927 SNAP:0001564408 DOW:0001751788 RIVN:0001874178 AAPL:0000320193 AMZN:0001018724 \
         NET:0001477333 V:0001403161 NVO:0000353278; do
  t=${c%%:*}; k=${c##*:}
  [ -s "$t.json" ] || { curl -s -m 60 -A "$UA" "https://data.sec.gov/api/xbrl/companyfacts/CIK$k.json" -o "$t.json"; sleep 0.4; }
done
echo "tamam"
