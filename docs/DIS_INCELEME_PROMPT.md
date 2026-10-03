---
belge: Dış inceleme promptu — 3. ajan (temel analiz) kuralları ve 10 hisselik deneme
tarih: 2026-10-03
durum: incelemeye gönderilecek
yayinla: hayir
---

# Dış inceleme promptu — 3. ajan

**Kullanım (bana not):** Aşağıdaki `PROMPT BAŞLANGICI` satırından dosyanın sonuna kadar her şeyi kopyala, iki farklı
modele **aynen** ver. İki cevap aynı tabloda geleceği için yan yana karşılaştırılabilir. Cevapları bu sohbete getir;
birlikte değerlendirip doğru bulduklarımızı kurallara işleriz.

---

## PROMPT BAŞLANGICI

### Rolün

Deneyimli bir **hisse analisti** ve **finansal veri mühendisi** olarak çalış. Görevin, aşağıda anlatılan temel analiz
kurallarımızı, hesaplama yöntemimizi ve 10 gerçek ABD şirketi üzerinde yaptığımız denemenin sonuçlarını **denetlemek**:
hesap hatası, veri hatası, kod hatası, mantık hatası ve gözden kaçan riskleri bulmak.

Cevabını **Türkçe** ver. Teknik terimin İngilizcesini parantez içinde yazabilirsin.

### Doğruluk için kurallar (lütfen dikkatle oku)

1. **Veri tarihi: 2026-10-03.** Rakamlar SEC'ten bu tarihte çekildi; çoğu şirkette son mali yıl 2025 (Nvidia: Ocak 2026,
   Nike: Mayıs 2026 biten mali yıl). Fiyatlar Yahoo'dan aynı gün alındı. **Bilgi kesim tarihin bundan eskiyse, bu yılların
   rakamlarını hafızandan "düzeltmeye" çalışma.** Sadece erişebildiğin bir kaynakla (SEC EDGAR, şirketin 10-K'sı)
   doğrulayabiliyorsan doğrula; doğrulayamıyorsan "doğrulayamadım" yaz.
2. **Hata bulamazsan "hata bulamadım" de.** Zorla hata üretme. Bulduğun her sorunda kanıt göster: hangi rakam, hangi
   formül, hangi satır.
3. Her bulgu için **nasıl emin olduğunu** yaz: "kaynakla doğruladım" / "Ek B'deki ham veriden yeniden hesapladım" /
   "akıl yürütme".
4. **Kapsamı genişletme.** Sistemin ilkeleri aşağıda; bunlara aykırı büyük öneriler (ör. tam DCF modeli, bankaları eklemek)
   yerine "1. sürüm için gerekli mi?" sorusunu cevapla. Bir öneri yapacaksan en basit hâlini öner.
5. Öncelik sırası: **(a) yanlış sınıf üreten hatalar > (b) yanlış rakam üreten hatalar > (c) mantık zaafları > (d) iyileştirme.**

### Sistem hakkında kısa bağlam

- Kişisel bir yatırım danışmanı sistemi. 4 yapay zekâ ajanı okur, araştırır, analiz eder, **öneri** verir;
  **kararı ve alım-satımı her zaman kullanıcı yapar.** Sistem asla AL / SAT demez.
- Kullanıcı yeni başlayan, uzun vadeli (10 yıl) bir yatırımcı; az işlem yapar; anlamadığı işe yatırım yapmaz.
- Yapay zekâ bütçesi ayda en fazla 25–30 $. İlke: **basit tut, kur, dene, düzelt** ("think fast, iterate faster").
- 1. sürüm **sadece ABD borsası** (NYSE, NASDAQ; ADR'ler dahil).
- **3. ajan** (incelemeni istediğimiz kısım): kullanıcının takibe aldığı hisselerin finansal tablolarından bir "karne"
  çıkarır ve şirkete bir sınıf verir: **SAĞLAM / ORTA / ZAYIF / BELİRSİZ**. Sağlam çıkanlar "yeşil liste"ye girer
  (yeşil liste ≠ AL; sadece teknik analize bakılacak liste).
- Yaklaşım: **kalite önce** (Buffett / Munger / Terry Smith), yapı **Peter Lynch**'ten (önce şirket türü, ölçüler türe
  göre okunur). Hesapları **kod** yapar; yapay zekâ rakam üretmez, sadece "neden?" sorularını rapordan alıntıyla cevaplar.
  Fiyat sınıfa **girmez**, ayrı satırda gösterilir.

### Veri kaynakları ve yöntem

**SEC (finansal rakamlar):** `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (ücretsiz, anahtar yok).
Sadece `us-gaap` sözlüğündeki isimler kullanıldı (deneme şirketlerinin hepsi us-gaap raporluyor).

- **Yıllık (dönem) rakamlar:** form `10-K` veya `10-K/A`; dönem uzunluğu 350–380 gün; bitiş tarihine göre anahtarlanır;
  aynı bitiş tarihi için birden çok kayıt varsa **en son dosyalanan** alınır (sonraki raporlardaki düzeltmeler yakalansın).
- **Anlık (bilanço) rakamlar:** form 10-K, başlangıç tarihi olmayan kayıtlar; bitiş tarihine göre; en son dosyalanan.
- **Mali yıl sonları:** gelir ve faaliyet kârı isimlerinde görülen bitiş tarihlerinin birleşimi; son 6 tanesi.
- **Eş anlamlılar yöntemi:** her rakam için bir isim listesi var; kod **her yıl için ayrı ayrı** listeyi sırayla dener,
  ilk bulunanı alır (şirket yıllar içinde isim değiştirebiliyor; örn. Coca-Cola borcu 2023'te `LongTermDebt`, 2024'te
  `LongTermDebtAndCapitalLeaseObligations`). Listeler:

| Rakam | Denenen XBRL isimleri (sırayla) |
|---|---|
| Gelir | Revenues · RevenueFromContractWithCustomerExcludingAssessedTax · RevenueFromContractWithCustomerIncludingAssessedTax · SalesRevenueNet |
| Satış maliyeti | CostOfRevenue · CostOfGoodsAndServicesSold · CostOfGoodsSold |
| Brüt kâr | GrossProfit; yoksa gelir − satış maliyeti |
| Faaliyet kârı | OperatingIncomeLoss; **yoksa vergi öncesi kâr + faiz gideri** (Nike, Pfizer, Dow faaliyet kârı raporlamıyor) |
| Vergi öncesi kâr | IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest · IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments |
| Vergi gideri | IncomeTaxExpenseBenefit |
| Net kâr | NetIncomeLoss |
| Faiz gideri | InterestExpense · InterestExpenseNonoperating · InterestExpenseDebt · InterestAndDebtExpense · InterestPaidNet (son seçenek nakit olarak ödenen faiz) |
| İşletme nakdi | NetCashProvidedByUsedInOperatingActivities |
| Yatırım harcaması | PaymentsToAcquirePropertyPlantAndEquipment · PaymentsToAcquireProductiveAssets |
| Nakit | CashAndCashEquivalentsAtCarryingValue · CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents |
| Kısa vadeli yatırım | MarketableSecuritiesCurrent · ShortTermInvestments · AvailableForSaleSecuritiesDebtSecuritiesCurrent |
| Özkaynak | StockholdersEquity · StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest (sadece bilgi; formüllerde kullanılmıyor) |
| Toplam varlık / kısa vadeli yükümlülük | Assets / LiabilitiesCurrent |
| Hisse sayısı | WeightedAverageNumberOfDilutedSharesOutstanding |
| Ödenen temettü | PaymentsOfDividends · PaymentsOfDividendsCommonStock · PaymentsOfOrdinaryDividends |

- **Borç:** uzun vadeli kısım için şu gruplardan **ilk bulunan grup** alınır ve grubun bulunan üyeleri toplanır:
  (1) LongTermDebt → (2) LongTermDebtNoncurrent + LongTermDebtCurrent → (3) LongTermDebtAndCapitalLeaseObligations +
  LongTermDebtAndCapitalLeaseObligationsCurrent → (4) ConvertibleDebtNoncurrent + ConvertibleDebtCurrent +
  ConvertibleNotesPayable + LongTermNotesPayable. Buna varsa **CommercialPaper** ve **ShortTermBorrowings** eklenir.
  Kiralama yükümlülükleri (operating lease) dahil değil. Borç bizde "araştırma maddesi": parçaların örtüşme ihtimali var.
- **Likit varlık** = nakit + kısa vadeli yatırım. **Serbest nakit (FCF)** = işletme nakdi − yatırım harcaması.
- **Hisse sayısı düzeltmeleri:** bir yıldan ötekine 2, 3, 4, 5, 8, 10 veya 20 kat (±%6) sıçrama **bölünme (split)** sayılır ve
  eski yıllar düzeltilir. Halka arz yılı atlanır (o yılın ağırlıklı ortalama hisse sayısı yanıltıcı).
- **Yahoo (fiyat):** son fiyat, piyasa değeri, F/K (trailing P/E). Kuralımıza göre bölünmeler Yahoo'nun bölünme geçmişiyle
  **sağlanacak**. Denemede yapılan sağlama: Nvidia için Yahoo 2021'de ×4 ve 2024'te ×10 gösteriyor; kod sadece ×10'u
  düzeltti çünkü SEC'in son raporları ×4'ü eski yıllarda zaten düzeltmiş. Pfizer için Yahoo 2020'de "×1,054" gösteriyor;
  bu bölünme değil, Viatris ayrılmasının fiyat düzeltmesi.
- **Sektör:** denemede GICS ana sektörü **elle** atandı.

### 10 ölçü — tanım ve formül

Hepsi her şirket için hesaplanır. "3y / 5y ort." = son 3 / 5 mali yıl.

| # | Ölçü | Formül |
|---|---|---|
| 1 | Gelir büyümesi | son 3 yılın yıllık bileşik büyümesi (CAGR): (gelir_son ÷ gelir_3 yıl önce)^(1/3) − 1 |
| 2 | Marj istikrarı | (son yıl marjı − son 5 yılın marj ortalaması [son yıl dahil]) × 100 → **puan**. Marj = brüt marj; brüt marj 3 yıldan az bulunursa **faaliyet marjı** |
| 3 | Faaliyet marjı | faaliyet kârı ÷ gelir (son yıl) |
| 4 | Sermaye getirisi (Terry Smith tarzı, ROCE) | 5 yıl ortalaması: faaliyet kârı × (1 − vergi oranı) ÷ (toplam varlık − kısa vadeli yükümlülük − likit). Vergi oranı = vergi ÷ vergi öncesi kâr, 0–%35 aralığına sıkıştırılır; vergi öncesi kâr ≤ 0 ise %21. Payda ≤ 0 olan yıl atlanır; en az 3 yıl gerekir |
| 5 | Nakde dönüşüm | son 3 yılın serbest nakit toplamı ÷ son 3 yılın net kâr toplamı; net kâr toplamı ≤ 0 ise hesaplanmaz |
| 6 | Faiz karşılama | likit ≥ borç ise "nakit > borç" (✅); değilse faaliyet kârı ÷ faiz gideri (son yıl) |
| 7 | Borcu kaç yılda öder | net borç = borç − likit; ≤ 0 ise "nakit > borç" (✅); serbest nakitin 3 yıl ortalaması ≤ 0 ise "işinden nakit üretmiyor, borcu var" (❌); değilse net borç ÷ 3 yıl ort. serbest nakit |
| 8 | Hisse sayısı değişimi | (son yıl ÷ ilk yıl) − 1; en fazla 5 yıllık aralık; bölünme düzeltmeli |
| 9 | Brüt kâr büyümesi | brüt kârın 3 yıllık CAGR'ı; 3 yıl önce ≤ 0 ve şimdi > 0 ise "zarardan kâra yeni döndü" (➖) |
| 10 | Kasadaki para kaç yıl yeter | 3 yıl ort. serbest nakit ≥ 0 ise "nakit üretiyor" (✅); değilse likit ÷ (−3 yıl ort. serbest nakit) |
| T | Temettü nakitle karşılanıyor mu | son 5 yılın serbest nakit toplamı ≥ son 5 yılın ödenen temettü toplamı |

### Eşikler

| # | Ölçü | ✅ iyi | ➖ orta | ❌ zayıf |
|---|---|---|---|---|
| 1 | Gelir büyümesi | ≥ %15 | %8–15 | < %8 |
| 2 | Marj istikrarı | düşüş ≤ 1 puan | 1–3 puan düşüş | > 3 puan düşüş |
| 3 | Faaliyet marjı | ≥ %15 | %5–15 | < %5 |
| 4 | Sermaye getirisi | ≥ %15 | %8–15 | < %8 |
| 5 | Nakde dönüşüm | ≥ %80 | %50–80 | < %50 |
| 6 | Faiz karşılama | ≥ 8 kat veya nakit > borç | 3–8 kat | < 3 kat |
| 7 | Borcu öder | ≤ 3 yıl veya nakit > borç | 3–5 yıl | > 5 yıl veya nakit üretmiyor + borç var |
| 8 | Hisse sayısı | ≤ %0 | %0–10 | > %10 |
| 9 | Brüt kâr büyümesi | ≥ %20 | %10–20 | < %10 |
| 10 | Kasadaki para | ≥ 3 yıl veya nakit üretiyor | 1,5–3 yıl | < 1,5 yıl |
| 10* | Aynısı, **hızlı büyüyen + 3 yıl ort. serbest nakit < 0** | ≥ 5 yıl | 3–5 yıl | < 3 yıl |
| T | Temettü | karşılanıyor | — | karşılanmıyor |

**Borç (sınıf kararında tek yargı):** 6'nın rengi esas alınır; 7 ❌ ise bir basamak düşürülür (✅→➖, ➖→❌). 6
hesaplanamazsa 7'nin rengi. Mantık: "borç iyi kullanılıyorsa (faiz rahat ödeniyorsa) sorun değil."

### Şirket türü (Lynch) — sırayla uygulanır

| Tür | Kural |
|---|---|
| Döngüsel | ana sektör Enerji veya Malzeme, **ya da** son 5 yılda faaliyet kârının hem artı hem eksi olduğu yıllar var |
| Hızlı büyüyen | gelir büyümesi (ölçü 1) ≥ %15 |
| Kârsız | son 5 yılın 4'ünden azında faaliyet kârı var (Lynch zarar edene "istikrarlı dev" demez) |
| İstikrarlı dev | ölçü 1 ≥ %5 |
| Yavaş büyüyen | geri kalan (< %5) |

### Belirleyici ölçüler ve sınıf kuralı

Sınıf kararında sadece türün **belirleyici** ölçülerine bakılır (forvet golüne, kaleci kurtarışına göre değerlendirilir).
Belirleyici olmayan bir ölçü ❌ alırsa karnede yapay zekâya "neden?" sorulur; sınıfı değiştirmez.

| Tür | Belirleyiciler |
|---|---|
| İstikrarlı dev | 2 · 3 · 4 · 5 |
| Hızlı büyüyen | 1 · 9 · 2 · 10 · 8 |
| Yavaş büyüyen | 2 · 4 · 5 · Borç · T |
| Döngüsel | 4 · Borç · 8 |
| Kârsız | 2 · 3 · 4 · 5 |

```text
BELİRSİZ = belirleyicilerin yarısından azı hesaplanabildi (ya da şirket kapsam dışı)
ZAYIF    = belirleyicilerden 2 veya daha fazlası ❌
SAĞLAM   = hiçbiri ❌ değil  VE  ✅ sayısı ≥ belirleyici sayısının yarısı
ORTA     = arada kalan
Küçülme  = ölçü 1 (3 yıllık gelir büyümesi) eksiyse SAĞLAM olamaz → ORTA
```

**Kapsam dışı (şimdilik):** banka, sigorta, gayrimenkul (REIT), henüz geliri olmayan şirketler, kamu hizmetleri;
toparlanan ve "varlık zengini" şirketler. Visa / Mastercard gibi ödeme şirketleri kapsam içinde.

### Fiyat satırı (sınıfa girmez)

- **PEG** = F/K (Yahoo trailing P/E) ÷ (net kârın 3 yıllık CAGR'ı × 100). Denemede hisse başı kâr değil **net kâr** büyümesi
  kullanıldı. Kâr yoksa / düşüyorsa "hesaplanamaz". ≤ 1 cazip · 1–2 makul · > 2 pahalı.
- **Serbest nakit akışı verimi** = son yıl serbest nakit ÷ piyasa değeri. ≥ %5 cazip · %2–5 makul · < %2 pahalı.

### Denenen 10 şirket ve kullanıcının beklentisi

Coca-Cola (KO), Nvidia (NVDA), Nike (NKE), Starbucks (SBUX), Pfizer (PFE), Intel (INTC), Boeing (BA), Snap (SNAP),
Dow (DOW), Rivian (RIVN). 2 tanesinin sağlam, 8'inin orta / zayıf çıkması beklendi. Kullanıcı sonuçları şöyle
değerlendirdi: Coca-Cola ORTA doğru (kural ona göre esnetilmesin), Nvidia SAĞLAM doğru, Intel / Boeing / Snap / Dow / Rivian
ZAYIF doğru; Nike / Starbucks / Pfizer'ı **zayıf** görüyor ama şimdilik ORTA kabul ediyor. Sonuçlar **Ek A**'da, ham
rakamlar **Ek B**'de, deneme kodu **Ek C**'de.

### Bildiğimiz sınırlamalar ve açık sorular (bunlar hakkında da görüşünü istiyoruz)

1. Deneme kodu bir **prototip**; rakamlar henüz 10-K'larla elle karşılaştırılmadı (kabul testinde en az 20 hissede yapılacak).
2. **Yatırım harcaması bulunamazsa 0 sayılıyor** → serbest nakit olduğundan yüksek çıkabilir.
3. 3 yıllık serbest nakit ortalamasında eksik yıl 0 sayılıyor (3'e bölünüyor).
4. **Dow:** son 3 yılın serbest nakiti 2,8 → 0 → −1,4 milyar $; ortalama artı olduğu için ölçü 10 "nakit üretiyor" diyor.
   Ortalama kullanmak tek seferlik ödemeleri yumuşatıyor ama kötüleşen eğilimi gizleyebilir.
5. Sermaye getirisinin paydasında şerefiye (goodwill) dahil; satın almayla büyüyen şirketlerde düşük çıkar (Coca-Cola %13,8).
6. Faaliyet kârı yedeği (vergi öncesi kâr + faiz) olağandışı kalemleri de içerir; faiz için nakit ödenen faiz (InterestPaidNet)
   kullanılabiliyor.
7. Borç parçalarının örtüşme riski; kiralama yükümlülükleri hariç.
8. **PEG:** Nvidia'da net kâr 3 yılda yıllık %202 büyüdüğü için PEG 0,15 çıkıyor (anlamsız). Öneri: büyüme en fazla %25
   alınsın (Lynch: daha hızlısı sürmez). Henüz karar verilmedi.
9. **Hisseyle ödenen maaş (stock-based compensation)** serbest nakitten düşülmüyor; Snap'in nakit verimi şişik görünüyor.
   Öneri: düşülsün. Henüz karar verilmedi.
10. Nakit veriminde son yıl serbest nakiti kullanılıyor; diğer ölçülerde 3 yıl ortalaması. Tutarlı olmalı mı?
11. Tür eşikleri (%5 / %15) gelir büyümesine göre; Lynch türleri kâr büyümesine göre ayırıyordu. Coca-Cola %3,7 ile
    "yavaş büyüyen" oldu (Lynch muhtemelen "istikrarlı dev" derdi).
12. Mali yıl sonları farklı (Nvidia Ocak, Nike Mayıs, Starbucks Eylül); karşılaştırmalar takvim yılına göre hizalı değil.

### Senden istenenler

1. **Hesap kontrolü:** Ek B'deki ham rakamlardan Ek A'daki ölçüleri yeniden hesapla (en az 4 şirket, mümkünse hepsi).
   Tutmayanları listele.
2. **Veri kontrolü:** Erişimin varsa en az 3 şirketin son yıl rakamlarını (gelir, faaliyet kârı, işletme nakdi, yatırım
   harcaması, borç, hisse sayısı) şirketin 10-K'sıyla karşılaştır. Özellikle **borç** toplamına bak.
3. **Kod kontrolü:** Ek C'deki kodda yukarıda yazılı kurallarla çelişen ya da hatalı bir yer var mı?
4. **Kural mantığı:** Eşikler, tür kuralları, belirleyiciler ve sınıf kuralı finansal açıdan tutarlı mı? Buffett / Munger /
   Smith / Lynch yaklaşımıyla çelişen bir yer var mı? Kuralın yanlış sınıf verebileceği **tuzak şirket tipleri** neler?
5. **Sınıf sonuçları:** 10 şirketin her birinin sınıfına katılıyor musun? Katılmıyorsan **hangi kural** yüzünden ve nasıl
   bir düzeltme önerirsin (tek bir şirket için kural esnetmek "geçmişe uydurma" olur; genel bir kural öner).
6. **Açık sorular:** Yukarıdaki 12 maddenin her birine kısa görüş.
7. **Gözden kaçanlar:** Sistemi yanıltabilecek en önemli 5 risk.

### Cevap formatı

Önce şu tabloyu doldur (her bulgu bir satır):

| # | Tür (hesap / veri / kod / kural / sınıf / eksik) | Nerede (şirket, ölçü, satır) | Sorun | Kanıt | Önem (yüksek / orta / düşük) | Öneri (en basit hâli) | Nasıl emin oldun (kaynak / yeniden hesap / akıl yürütme) |
|---|---|---|---|---|---|---|---|

Sonra:

- **10 şirket tablosu:** şirket · bizim sınıfımız · senin sınıfın · kısa gerekçe.
- **Açık sorular:** 1–12 her biri için 1–3 cümle.
- **En önemli 3 bulgu.**
- **Hata bulamadığın alanlar** (ör. "eşik tablosu tutarlı", "Coca-Cola hesapları doğru").

### Ek A — Sonuçlar (deneme kodunun çıktısı)

**Kalın** = o şirketin türüne göre belirleyici ölçü. "—" = hesaplanamadı. Renkler: ✅ iyi · ➖ orta · ❌ zayıf · `·` hesaplanamadı / yok.

| Ölçü | Coca-Cola (KO) | Nvidia (NVDA) | Nike (NKE) | Starbucks (SBUX) | Pfizer (PFE) |
|---|---|---|---|---|---|
| 1. Gelir büyümesi (3y) | ❌ +3.7% | **✅ +100.0%** | ❌ -3.2% | ❌ +4.9% | ❌ -14.8% |
| 2. Marj istikrarı | **✅ +1.5 puan** | **✅ +2.9 puan** | **➖ -1.0 puan** | **❌ -6.2 puan** | **✅ +7.8 puan** |
| 3. Faaliyet marjı | ✅ 28.7% | ✅ 60.4% | ➖ 9.1% | ➖ 7.9% | ✅ 16.3% |
| 4. Sermaye getirisi (5y, ROCE) | **➖ 13.8%** | ✅ 76.0% | **✅ 25.5%** | **✅ 21.5%** | **➖ 12.0%** |
| 5. Nakde dönüşüm (3y) | **➖ 57.4%** | ✅ 82.9% | **✅ 100.3%** | **✅ 96.9%** | **✅ 132.3%** |
| 6. Faiz karşılama (kat) | ✅ 8.3 | ✅ nakit > borç | ✅ 13.1 | ➖ 5.4 | ➖ 3.8 |
| 7. Borcu öder (yıl) | ❌ 5.3 | ✅ nakit > borç | ✅ 0.1 | ➖ 4.0 | ❌ 6.9 |
| 8. Hisse sayısı (5y) | ✅ -0.2% | **✅ -2.3%** | ✅ -8.0% | ✅ -3.6% | ➖ +1.4% |
| 9. Brüt kâr büyümesi (3y) | ❌ +5.7% | **✅ +115.4%** | ❌ -3.7% | · — | ❌ -11.4% |
| 10. Nakit yeter (yıl) | ✅ nakit üretiyor | **✅ nakit üretiyor** | ✅ nakit üretiyor | ✅ nakit üretiyor | ✅ nakit üretiyor |
| Borç (6+7 birleşik) | **➖** | ✅ | **✅** | **➖** | **❌** |
| T. Temettü (5y) | **✅** | ✅ | **✅** | **✅** | **✅** |
| Serbest nakit 3y ort. (milyar $) | 6.59 | 61.52 | 4.02 | 3.15 | 7.90 |
| **Tür → Sınıf** | Yavaş büyüyen → **ORTA** | Hızlı büyüyen → **SAĞLAM** | Yavaş büyüyen → **ORTA (küçülme kuralı)** | Yavaş büyüyen → **ORTA** | Yavaş büyüyen → **ORTA** |
| Fiyat satırı | PEG 2.32 · nakit verimi 1.4% | PEG 0.15 · nakit verimi 1.7% | PEG hesaplanamaz · nakit verimi 4.3% | PEG hesaplanamaz · nakit verimi 2.3% | PEG hesaplanamaz · nakit verimi 5.7% |

| Ölçü | Intel (INTC) | Boeing (BA) | Snap (SNAP) | Dow (DOW) | Rivian (RIVN) |
|---|---|---|---|---|---|
| 1. Gelir büyümesi (3y) | ❌ -5.7% | ➖ +10.3% | ➖ +8.8% | ❌ -11.1% | **✅ +48.1%** |
| 2. Marj istikrarı | ❌ -6.3 puan | ✅ +0.4 puan | **➖ -1.2 puan** | ❌ -6.2 puan | **✅ +222.9 puan** |
| 3. Faaliyet marjı | ❌ -4.2% | ❌ 4.8% | **❌ -9.0%** | ❌ -4.1% | ❌ -66.5% |
| 4. Sermaye getirisi (5y, ROCE) | **❌ 2.1%** | **❌ -6.2%** | **❌ -24.3%** | **❌ 6.1%** | ❌ -94.4% |
| 5. Nakde dönüşüm (3y) | · — | · — | **· —** | · — | · — |
| 6. Faiz karşılama (kat) | ❌ -2.0 | ❌ 1.5 | ❌ -4.4 | ❌ -1.9 | ✅ nakit > borç |
| 7. Borcu öder (yıl) | ❌ nakit üretmiyor, borç var | ❌ nakit üretmiyor, borç var | ✅ 2.8 | ❌ 31.3 | ✅ nakit > borç |
| 8. Hisse sayısı (5y) | **➖ +7.0%** | **❌ +34.1%** | ❌ +16.4% | **✅ -4.1%** | **❌ +29.9%** |
| 9. Brüt kâr büyümesi (3y) | ❌ -11.9% | ❌ +6.7% | ❌ +5.4% | ❌ -33.4% | **➖ zarardan kâra döndü** |
| 10. Nakit yeter (yıl) | ✅ 3.2 | ✅ 7.5 | ✅ nakit üretiyor | ✅ nakit üretiyor | **❌ 1.6** |
| Borç (6+7 birleşik) | **❌** | **❌** | ❌ | **❌** | ✅ |
| T. Temettü (5y) | ❌ | ❌ | · | ✅ | · |
| Serbest nakit 3y ort. (milyar $) | -11.63 | -3.92 | 0.23 | 0.46 | -3.75 |
| **Tür → Sınıf** | Döngüsel → **ZAYIF** | Döngüsel → **ZAYIF** | Kârsız → **ZAYIF** | Döngüsel → **ZAYIF** | Hızlı büyüyen → **ZAYIF** |
| Fiyat satırı | PEG hesaplanamaz · nakit verimi -0.8% | PEG hesaplanamaz · nakit verimi -1.2% | PEG hesaplanamaz · nakit verimi 4.6% | PEG hesaplanamaz · nakit verimi -7.2% | PEG hesaplanamaz · nakit verimi -12.0% |

### Ek B — Ham rakamlar (SEC, milyar $; hisse sayısı milyon, bölünme düzeltmesi **öncesi**)

Sütunlar mali yıl sonu tarihleri (yyyy-aa). "—" = eş anlamlılar listesinde bulunamadı.

#### Coca-Cola (KO) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Yavaş büyüyen · sınıf: ORTA

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 33.01 | 38.66 | 43.00 | 45.75 | 47.06 | 47.94 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 19.58 | 23.30 | 25.00 | 27.23 | 28.74 | 29.54 |
| Faaliyet kârı | 9.00 | 10.31 | 10.91 | 11.31 | 9.99 | 13.76 |
| Vergi öncesi kâr | 9.75 | 12.43 | 11.69 | 12.95 | 13.09 | 16.00 |
| Faiz gideri | 1.44 | 1.60 | 0.88 | 1.53 | 1.66 | 1.65 |
| Net kâr | 7.75 | 9.77 | 9.54 | 10.71 | 10.63 | 13.11 |
| İşletme nakdi | 9.84 | 12.62 | 11.02 | 11.60 | 6.80 | 7.41 |
| Yatırım harcaması | 1.18 | 1.37 | 1.48 | 1.85 | 2.06 | 2.11 |
| Serbest nakit | 8.67 | 11.26 | 9.53 | 9.75 | 4.74 | 5.30 |
| Nakit + kısa vadeli yatırım | 9.14 | 9.68 | 9.52 | 9.37 | 10.83 | 10.27 |
| Toplam varlık | 87.30 | 94.35 | 92.76 | 97.70 | 100.55 | 104.82 |
| Kısa vadeli yükümlülük | 14.60 | 19.95 | 19.72 | 23.57 | 25.25 | 21.28 |
| Özkaynak | 19.30 | 23.00 | 24.11 | 25.94 | 24.86 | 32.17 |
| Borç (toplam) | 44.12 | 45.22 | 41.30 | 41.72 | 44.16 | 45.44 |
| Ödenen temettü | 7.05 | 7.25 | 7.62 | 7.95 | 8.36 | 8.78 |
| Seyreltilmiş ort. hisse (milyon, ham) | 4,323 | 4,340 | 4,350 | 4,339 | 4,320 | 4,313 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebtAndCapitalLeaseObligations, LongTermDebtAndCapitalLeaseObligationsCurrent, CommercialPaper · faaliyet kârı kaynağı: OperatingIncomeLoss

#### Nvidia (NVDA) — mali yıl sonları: 2021-01-31, 2022-01-30, 2023-01-29, 2024-01-28, 2025-01-26, 2026-01-25 · tür: Hızlı büyüyen · sınıf: SAĞLAM

| Kalem (milyar $) | 2021-01 | 2022-01 | 2023-01 | 2024-01 | 2025-01 | 2026-01 |
|---|---|---|---|---|---|---|
| Gelir | 16.68 | 26.91 | 26.97 | 60.92 | 130.50 | 215.94 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 10.40 | 17.48 | 15.36 | 44.30 | 97.86 | 153.46 |
| Faaliyet kârı | 4.53 | 10.04 | 4.22 | 32.97 | 81.45 | 130.39 |
| Vergi öncesi kâr | 4.41 | 9.94 | 4.18 | 33.82 | 84.03 | 141.45 |
| Faiz gideri | 0.18 | 0.24 | 0.26 | 0.26 | 0.25 | 0.26 |
| Net kâr | 4.33 | 9.75 | 4.37 | 29.76 | 72.88 | 120.07 |
| İşletme nakdi | 5.82 | 9.11 | 5.64 | 28.09 | 64.09 | 102.72 |
| Yatırım harcaması | — | 0.98 | 1.83 | 1.07 | 3.24 | 6.04 |
| Serbest nakit | 5.82 | 8.13 | 3.81 | 27.02 | 60.85 | 96.68 |
| Nakit + kısa vadeli yatırım | 11.56 | 21.21 | 13.30 | 25.98 | 43.21 | 10.61 |
| Toplam varlık | 28.79 | 44.19 | 41.18 | 65.73 | 111.60 | 206.80 |
| Kısa vadeli yükümlülük | 3.92 | 4.33 | 6.56 | 10.63 | 18.05 | 32.16 |
| Özkaynak | 16.89 | 26.61 | 22.10 | 42.98 | 79.33 | 157.29 |
| Borç (toplam) | 6.96 | 10.95 | 10.95 | 9.71 | 8.46 | 8.47 |
| Ödenen temettü | 0.40 | 0.40 | 0.40 | 0.40 | 0.83 | 0.97 |
| Seyreltilmiş ort. hisse (milyon, ham) | 2,510 | 2,535 | 25,070 | 24,940 | 24,804 | 24,514 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt · faaliyet kârı kaynağı: OperatingIncomeLoss · hisse: bölünme düzeltildi (×10)

#### Nike (NKE) — mali yıl sonları: 2021-05-31, 2022-05-31, 2023-05-31, 2024-05-31, 2025-05-31, 2026-05-31 · tür: Yavaş büyüyen · sınıf: ORTA (küçülme kuralı)

| Kalem (milyar $) | 2021-05 | 2022-05 | 2023-05 | 2024-05 | 2025-05 | 2026-05 |
|---|---|---|---|---|---|---|
| Gelir | 44.54 | 46.71 | 51.22 | 51.36 | 46.31 | 46.40 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 19.96 | 21.48 | 22.29 | 22.89 | 19.79 | 19.91 |
| Faaliyet kârı | 6.95 | 6.94 | 6.55 | 7.08 | 4.27 | 4.22 |
| Vergi öncesi kâr | 6.66 | 6.65 | 6.20 | 6.70 | 3.88 | 3.90 |
| Faiz gideri | 0.29 | 0.29 | 0.35 | 0.38 | 0.39 | 0.32 |
| Net kâr | 5.73 | 6.05 | 5.07 | 5.70 | 3.22 | 3.11 |
| İşletme nakdi | 6.66 | 5.19 | 5.84 | 7.43 | 3.70 | 2.87 |
| Yatırım harcaması | 0.69 | 0.76 | 0.97 | 0.81 | 0.43 | 0.68 |
| Serbest nakit | 5.96 | 4.43 | 4.87 | 6.62 | 3.27 | 2.18 |
| Nakit + kısa vadeli yatırım | 13.48 | 8.57 | 7.44 | 9.86 | 7.46 | 7.56 |
| Toplam varlık | 37.74 | 40.32 | 37.53 | 38.11 | 36.58 | 38.41 |
| Kısa vadeli yükümlülük | 9.67 | 10.73 | 9.26 | 10.59 | 10.57 | 12.55 |
| Özkaynak | 12.77 | 15.28 | 14.00 | 14.43 | 13.21 | 14.87 |
| Borç (toplam) | 9.41 | 9.43 | 8.93 | 8.91 | 7.97 | 7.94 |
| Ödenen temettü | 1.64 | 1.84 | 2.01 | 2.17 | 2.30 | 2.41 |
| Seyreltilmiş ort. hisse (milyon, ham) | 1,609 | 1,611 | 1,570 | 1,530 | 1,488 | 1,481 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt · faaliyet kârı kaynağı: yaklaşık: vergi öncesi kâr + faiz

#### Starbucks (SBUX) — mali yıl sonları: 2020-09-27, 2021-10-03, 2022-10-02, 2023-10-01, 2024-09-29, 2025-09-28 · tür: Yavaş büyüyen · sınıf: ORTA

| Kalem (milyar $) | 2020-09 | 2021-10 | 2022-10 | 2023-10 | 2024-09 | 2025-09 |
|---|---|---|---|---|---|---|
| Gelir | 23.52 | 29.06 | 32.25 | 35.98 | 36.18 | 37.18 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | — | — | — | — | — | — |
| Faaliyet kârı | 1.56 | 4.87 | 4.62 | 5.87 | 5.41 | 2.94 |
| Vergi öncesi kâr | 1.16 | 5.36 | 4.23 | 5.40 | 4.97 | 2.51 |
| Faiz gideri | 0.44 | 0.47 | 0.48 | 0.55 | 0.56 | 0.54 |
| Net kâr | 0.93 | 4.20 | 3.28 | 4.12 | 3.76 | 1.86 |
| İşletme nakdi | 1.60 | 5.99 | 4.40 | 6.01 | 6.10 | 4.75 |
| Yatırım harcaması | 1.48 | 1.47 | 1.84 | 2.33 | 2.78 | 2.31 |
| Serbest nakit | 0.11 | 4.52 | 2.56 | 3.68 | 3.32 | 2.44 |
| Nakit + kısa vadeli yatırım | 4.63 | 6.62 | 3.18 | 3.95 | 3.54 | 3.47 |
| Toplam varlık | 29.37 | 31.39 | 27.98 | 29.45 | 31.34 | 32.02 |
| Kısa vadeli yükümlülük | 7.35 | 8.15 | 9.15 | 9.35 | 9.07 | 10.21 |
| Özkaynak | -7.81 | -5.32 | -8.71 | -7.99 | -7.45 | -8.10 |
| Borç (toplam) | 16.35 | 14.62 | 15.04 | 15.40 | 15.57 | 16.07 |
| Ödenen temettü | 1.92 | 2.12 | 2.26 | 2.43 | 2.58 | 2.77 |
| Seyreltilmiş ort. hisse (milyon, ham) | 1,182 | 1,186 | 1,158 | 1,151 | 1,137 | 1,140 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt · faaliyet kârı kaynağı: OperatingIncomeLoss

#### Pfizer (PFE) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Yavaş büyüyen · sınıf: ORTA

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 41.65 | 81.29 | 101.17 | 59.55 | 63.63 | 62.58 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 33.17 | 50.47 | 66.83 | 34.60 | 45.78 | 46.51 |
| Faaliyet kârı | 8.48 | 25.60 | 35.97 | 3.27 | 11.11 | 10.19 |
| Vergi öncesi kâr | 7.04 | 24.31 | 34.73 | 1.06 | 8.02 | 7.52 |
| Faiz gideri | 1.45 | 1.29 | 1.24 | 2.21 | 3.09 | 2.67 |
| Net kâr | 9.16 | 21.98 | 31.37 | 2.12 | 8.03 | 7.77 |
| İşletme nakdi | 14.40 | 32.58 | 29.27 | 8.70 | 12.74 | 11.70 |
| Yatırım harcaması | 2.23 | 2.71 | 3.24 | 3.91 | 2.91 | 2.63 |
| Serbest nakit | 12.18 | 29.87 | 26.03 | 4.79 | 9.84 | 9.07 |
| Nakit + kısa vadeli yatırım | 11.49 | 23.96 | 19.16 | 7.25 | 11.92 | 10.32 |
| Toplam varlık | 154.23 | 181.48 | 197.21 | 226.50 | 213.40 | 208.16 |
| Kısa vadeli yükümlülük | 25.92 | 42.67 | 42.14 | 47.79 | 42.99 | 36.98 |
| Özkaynak | 63.24 | 77.20 | 95.66 | 89.01 | 88.20 | 86.48 |
| Borç (toplam) | 4.56 | 37.83 | 35.44 | 71.76 | 63.60 | 64.64 |
| Ödenen temettü | 8.44 | 8.73 | 8.98 | 9.25 | 9.51 | 9.77 |
| Seyreltilmiş ort. hisse (milyon, ham) | 5,632 | 5,708 | 5,733 | 5,709 | 5,700 | 5,713 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebtNoncurrent, LongTermDebtCurrent · faaliyet kârı kaynağı: yaklaşık: vergi öncesi kâr + faiz

#### Intel (INTC) — mali yıl sonları: 2020-12-26, 2021-12-25, 2022-12-31, 2023-12-30, 2024-12-28, 2025-12-27 · tür: Döngüsel · sınıf: ZAYIF

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 77.87 | 79.02 | 63.05 | 54.23 | 53.10 | 52.85 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 43.61 | 43.81 | 26.87 | 21.71 | 17.34 | 18.38 |
| Faaliyet kârı | 23.68 | 19.46 | 2.33 | 0.09 | -11.68 | -2.21 |
| Vergi öncesi kâr | 25.08 | 21.70 | 7.77 | 0.76 | -11.21 | 1.56 |
| Faiz gideri | 0.63 | 0.60 | 0.50 | 0.88 | 1.03 | 1.09 |
| Net kâr | 20.90 | 19.87 | 8.01 | 1.69 | -18.76 | -0.27 |
| İşletme nakdi | 35.86 | 29.46 | 15.43 | 11.47 | 8.29 | 9.70 |
| Yatırım harcaması | 14.26 | 18.73 | 24.84 | 25.75 | 23.94 | 14.65 |
| Serbest nakit | 21.61 | 10.72 | -9.41 | -14.28 | -15.66 | -4.95 |
| Nakit + kısa vadeli yatırım | 8.16 | 29.25 | 28.34 | 25.03 | 22.06 | 37.42 |
| Toplam varlık | 153.09 | 168.41 | 182.10 | 191.57 | 196.49 | 211.43 |
| Kısa vadeli yükümlülük | 24.75 | 27.46 | 32.16 | 28.05 | 35.67 | 31.57 |
| Özkaynak | 81.04 | 95.39 | 101.42 | 105.59 | 99.27 | 114.28 |
| Borç (toplam) | 36.40 | 38.10 | 42.01 | 49.27 | 50.01 | 46.59 |
| Ödenen temettü | 5.57 | 5.64 | 6.00 | 3.09 | 1.60 | 0.00 |
| Seyreltilmiş ort. hisse (milyon, ham) | 4,232 | 4,090 | 4,123 | 4,212 | 4,280 | 4,530 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt · faaliyet kârı kaynağı: OperatingIncomeLoss

#### Boeing (BA) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Döngüsel · sınıf: ZAYIF

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 58.16 | 62.29 | 66.61 | 77.79 | 66.52 | 89.46 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | -5.68 | 3.05 | 3.53 | 7.72 | -1.99 | 4.29 |
| Faaliyet kârı | -12.77 | -2.87 | -3.52 | -0.77 | -10.71 | 4.28 |
| Vergi öncesi kâr | -14.48 | -5.03 | -5.02 | -2.00 | -12.21 | 2.63 |
| Faiz gideri | 2.16 | 2.71 | 2.56 | 2.46 | 2.73 | 2.77 |
| Net kâr | -11.87 | -4.20 | -4.93 | -2.22 | -11.82 | 2.23 |
| İşletme nakdi | -18.41 | -3.42 | 3.51 | 5.96 | -12.08 | 1.06 |
| Yatırım harcaması | 1.30 | 0.98 | 1.22 | 1.53 | 2.23 | 2.94 |
| Serbest nakit | -19.71 | -4.40 | 2.29 | 4.43 | -14.31 | -1.88 |
| Nakit + kısa vadeli yatırım | 25.59 | 16.24 | 17.22 | 15.96 | 26.28 | 29.40 |
| Toplam varlık | 152.14 | 138.55 | 137.10 | 137.01 | 156.36 | 168.24 |
| Kısa vadeli yükümlülük | 87.28 | 81.99 | 90.05 | 95.83 | 97.08 | 108.11 |
| Özkaynak | -18.32 | -15.00 | -15.88 | -17.23 | -3.91 | 5.45 |
| Borç (toplam) | 63.38 | 57.92 | 56.79 | 52.05 | 53.62 | 53.85 |
| Ödenen temettü | 1.16 | — | — | — | — | 0.33 |
| Seyreltilmiş ort. hisse (milyon, ham) | 569 | 588 | 595 | 606 | 647 | 762 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt · faaliyet kârı kaynağı: OperatingIncomeLoss

#### Snap (SNAP) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Kârsız · sınıf: ZAYIF

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 2.51 | 4.12 | 4.60 | 4.61 | 5.36 | 5.93 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 1.32 | 2.37 | 2.79 | 2.49 | 2.89 | 3.26 |
| Faaliyet kârı | -0.86 | -0.70 | -1.40 | -1.40 | -0.79 | -0.53 |
| Vergi öncesi kâr | -0.93 | -0.47 | -1.40 | -1.29 | -0.67 | -0.45 |
| Faiz gideri | 0.10 | 0.02 | 0.02 | 0.02 | 0.02 | 0.12 |
| Net kâr | -0.94 | -0.49 | -1.43 | -1.32 | -0.70 | -0.46 |
| İşletme nakdi | -0.17 | 0.29 | 0.18 | 0.25 | 0.41 | 0.66 |
| Yatırım harcaması | 0.06 | 0.07 | 0.13 | 0.21 | 0.19 | 0.22 |
| Serbest nakit | -0.23 | 0.22 | 0.06 | 0.03 | 0.22 | 0.44 |
| Nakit + kısa vadeli yatırım | 2.54 | 3.69 | 3.94 | 3.54 | 3.38 | 2.94 |
| Toplam varlık | 5.02 | 7.54 | 8.03 | 7.97 | 7.94 | 7.68 |
| Kısa vadeli yükümlülük | 0.67 | 0.85 | 1.22 | 1.13 | 1.24 | 1.29 |
| Özkaynak | 2.33 | 3.79 | 2.58 | 2.41 | 2.45 | 2.28 |
| Borç (toplam) | 1.68 | 2.25 | 3.74 | 3.75 | 3.68 | 3.58 |
| Ödenen temettü | — | — | — | — | — | — |
| Seyreltilmiş ort. hisse (milyon, ham) | 1,456 | 1,559 | 1,608 | 1,613 | 1,659 | 1,695 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebt, ShortTermBorrowings · faaliyet kârı kaynağı: OperatingIncomeLoss

#### Dow (DOW) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Döngüsel · sınıf: ZAYIF

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 38.54 | 54.97 | 56.90 | 44.62 | 42.96 | 39.97 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 5.20 | 10.78 | 8.56 | 4.88 | 4.61 | 2.53 |
| Faaliyet kârı | 2.90 | 8.88 | 6.75 | 1.40 | 2.41 | -1.65 |
| Vergi öncesi kâr | 2.07 | 8.14 | 6.09 | 0.66 | 1.60 | -2.51 |
| Faiz gideri | 0.83 | 0.73 | 0.66 | 0.75 | 0.81 | 0.86 |
| Net kâr | — | — | — | — | — | — |
| İşletme nakdi | 6.23 | 7.01 | 7.47 | 5.20 | 2.91 | 1.03 |
| Yatırım harcaması | 1.25 | 1.50 | 1.82 | 2.36 | 2.94 | 2.48 |
| Serbest nakit | 4.97 | 5.51 | 5.65 | 2.84 | -0.03 | -1.45 |
| Nakit + kısa vadeli yatırım | 5.10 | 2.99 | 3.89 | 2.99 | 2.19 | 3.82 |
| Toplam varlık | 61.47 | 62.99 | 60.60 | 57.97 | 57.31 | 58.54 |
| Kısa vadeli yükümlülük | 11.11 | 13.23 | 11.33 | 9.96 | 10.29 | 9.18 |
| Özkaynak | 12.44 | 18.16 | 20.72 | 18.61 | 17.36 | 16.01 |
| Borç (toplam) | 17.11 | 14.67 | 15.42 | 15.09 | 16.21 | 18.07 |
| Ödenen temettü | 2.07 | 2.07 | 2.01 | 1.97 | 1.97 | 1.49 |
| Seyreltilmiş ort. hisse (milyon, ham) | 742 | 749 | 726 | 709 | 705 | 712 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebtAndCapitalLeaseObligations, LongTermDebtAndCapitalLeaseObligationsCurrent · faaliyet kârı kaynağı: yaklaşık: vergi öncesi kâr + faiz

#### Rivian (RIVN) — mali yıl sonları: 2020-12-31, 2021-12-31, 2022-12-31, 2023-12-31, 2024-12-31, 2025-12-31 · tür: Hızlı büyüyen · sınıf: ZAYIF

| Kalem (milyar $) | 2020-12 | 2021-12 | 2022-12 | 2023-12 | 2024-12 | 2025-12 |
|---|---|---|---|---|---|---|
| Gelir | 0.00 | 0.06 | 1.66 | 4.43 | 4.97 | 5.39 |
| Brüt kâr (doğrudan ya da gelir−maliyet) | 0.00 | -0.47 | -3.12 | -2.03 | -1.20 | 0.14 |
| Faaliyet kârı | -1.02 | -4.22 | -6.86 | -5.74 | -4.69 | -3.58 |
| Vergi öncesi kâr | -1.02 | -4.69 | -6.75 | -5.43 | -4.74 | -3.62 |
| Faiz gideri | 0.01 | 0.03 | 0.10 | 0.22 | 0.32 | 0.27 |
| Net kâr | -1.02 | -4.69 | -6.75 | -5.43 | -4.75 | -3.65 |
| İşletme nakdi | -0.85 | -2.62 | -5.05 | -4.87 | -1.72 | -0.78 |
| Yatırım harcaması | 0.91 | 1.79 | 1.37 | 1.03 | 1.14 | 1.71 |
| Serbest nakit | -1.76 | -4.42 | -6.42 | -5.89 | -2.86 | -2.49 |
| Nakit + kısa vadeli yatırım | 2.98 | 18.13 | 11.57 | 9.37 | 7.70 | 6.08 |
| Toplam varlık | 4.60 | 22.29 | 17.88 | 16.78 | 15.41 | 14.86 |
| Kısa vadeli yükümlülük | 0.61 | 1.31 | 2.42 | 2.49 | 2.25 | 3.69 |
| Özkaynak | -1.38 | 19.51 | 13.80 | 9.14 | 6.56 | 4.59 |
| Borç (toplam) | 0.07 | 1.23 | 1.23 | 4.43 | 4.44 | 4.44 |
| Ödenen temettü | — | — | — | — | — | — |
| Seyreltilmiş ort. hisse (milyon, ham) | 101 | 204 | 913 | 947 | 1,013 | 1,186 |

Son yıl borç kaynağı (XBRL isimleri): LongTermDebtNoncurrent · faaliyet kârı kaynağı: OperatingIncomeLoss

### Ek C — Deneme kodu (Python, prototip)

`karne_deneme.py` — ölçüler, tür, sınıf:

```python
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
```

`fiyat.py` — fiyat satırı (Yahoo, `yfinance`):

```python
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
```

## PROMPT SONU
