# Agent 3 Karne Denetimi: 10 Şirket, Kod ve Kurallar (veri tarihi 2026-10-03)

Bulduğum en önemli hata şu: likit varlık (nakit + kısa vadeli yatırım + menkul kıymet) yanlış toplanıyor. Kod, birbirine eklenmesi gereken kalemleri "ilk bulunan eş anlamlı" diye birbirinin yerine kullanıyor ve `OtherShortTermInvestments` etiketini hiç okumuyor. Kontrol ettiğim 4 şirketin 4'ünde de likit varlık eksik çıktı (KO, NVDA, NKE, PFE). Coca-Cola'da bu hata sınıfı değiştiriyor: doğru veriyle mevcut kurallar KO'ya ORTA değil **SAĞLAM** veriyor.

## TL;DR

- **Sınıfı değiştiren 2 bulgu var.** (1) KO likit varlık hatası: 10-K'da 15,8 milyar $ var, kod 10,27 milyar $ okuyor. Ölçü 7 5,3'ten (❌) 4,5'e (➖) iniyor, Borç ✅ oluyor, KO **SAĞLAM** (sınırda) çıkıyor. (2) Pfizer'in 5 yıllık ROCE'si (%12, ➖) 2021-22 Covid zirvesine dayanıyor; son 3 yıl ortalaması %5,1 (❌). "ROCE = 5y ve 3y'den kötü olanı" genel kuralıyla PFE **ZAYIF** oluyor, diğer 9 şirketin sınıfı değişmiyor.
- **Hesaplamada hata bulamadım.** Ek A'yı Ek B'den 10 şirketin hepsi için yeniden hesapladım. Ölçü 1, 2, 3, 5, 6, 7, 8, 9, 10 ve T yuvarlama farkı dışında birebir tutuyor. ROCE'yi 5 şirkette (KO, NVDA, NKE, SBUX, PFE) yeniden hesapladım, o da tutuyor. Sorunlar formülde değil; veri toplama (likit, borç, faaliyet kârı fallback'i, Dow net kârı) ve tek seferlik kalemlerde (KO'da 6,0 + 6,1 milyar $ nakit çıkışı, Boeing'de 9,6 milyar $ satış kazancı).
- **Önerdiğim 3 düzeltmeyle (likit toplama + ROCE 3y/5y'nin kötüsü + ölçü 2 koruması) sonuç:** KO SAĞLAM (sınırda), NVDA SAĞLAM, NKE ORTA (küçülme kuralı), SBUX ORTA, PFE ZAYIF, INTC/BA/SNAP/DOW/RIVN ZAYIF. Yani 2 güçlü, 8 orta/zayıf; başlangıçtaki beklentinizle aynı. Ancak güçlü çıkan ikinci şirket Nike/Starbucks değil, KO. Kira (lease) ayarlamasını kaba haliyle sınıfa sokmayın: SBUX'u ZAYIF yapıyor ama kira ödemesini iki kez sayıyor.

## 1. Bulgu tablosu (öncelik sırasıyla: a sınıf > b rakam > c mantık > d iyileştirme)

| # | Tür | Nerede | Sorun | Kanıt | Önem | Çözüm (en basit) | Nasıl biliyorum |
|---|---|---|---|---|---|---|---|
| 1 | veri / kod (a) | KO, likit varlık; `kv_yatirim` listesi, `likit = nakit + kvy`; ölçü 4, 6, 7, Borç | Kısa vadeli yatırım ve menkul kıymetler toplanmıyor. Liste alternatif gibi çalışıyor (ilk bulunan alınıyor), KO'nun kullandığı `OtherShortTermInvestments` listede yok. | KO FY2025 10-K bilançosu: nakit 10.270, kısa vadeli yatırım 3.602, menkul kıymet 1.934 milyon $. 10-K'daki ifade: "cash, cash equivalents, short-term investments and marketable securities totaled $15.8 billion".\[1\]\[2\] Ek B'deki 10,27 yalnızca nakde eşit; 2023 (9,37) ve 2024 (10,83) de yalnızca nakit.\[3\] Ölçü 7: (45,44 - 15,81) / 6,60 = **4,49 → ➖** (bizde 5,3 ❌). Faiz karşılama 8,34 ✅ kalıyor, Borç ➖'den ✅'ye çıkıyor. Belirleyiciler: 2 ✅, 4 ➖, 5 ➖, Borç ✅, T ✅ → 3 ✅, 0 ❌ → **SAĞLAM**. | Yüksek | Likiti bileşenlerin toplamı yap; `OtherShortTermInvestments` ekle; likit bir yılda %50'den fazla düşerse "veri kontrol" bayrağı koy (kod aşağıda). | kaynaktan doğrulandı (sec.gov ko-20251231.htm, KO FY2025 ARS bilançosu) + Ek B'den yeniden hesaplandı |
| 2 | kural (a) | PFE, ölçü 4 (ROCE, 5y) | 5 yıllık ortalama, Covid dönemindeki 2021-22 getirisini taşıyor; bugünkü getiri ❌. | Yaklaşık vergiyle (vergi öncesi - net, 0-%35'e kırpılmış) yıllık ROCE: 2021 %20,1 · 2022 %23,9 · 2023 %1,9 · 2024 %7,0 · 2025 %6,3. 5y ort %11,8 (➖, Ek A %12,0); 3y ort **%5,1 (❌)**. | Yüksek | Kural: ROCE rengi = min(5y ort, 3y ort). PFE: 2 ✅, 4 ❌, 5 ✅, Borç ❌, T ✅ → 2 ❌ → **ZAYIF**. Diğer 9 şirkette sınıf değişmiyor (bölüm 3). | Ek B'den yeniden hesaplandı |
| 3 | veri, tek seferlik (a/b) | KO, OCF 2024-2025; ölçü 5, 7, T, FCF verimi | İşletme nakit akışı iki tek seferlik çıkışla bastırılmış. | KO FY2025 10-K: "the activity in 2025 included $6.1 billion of the $6.2 billion final milestone payment for fairlife. The activity in 2024 included the $6.0 billion IRS Tax Litigation Deposit."\[4\] Bunlar hariç 3y FCF 31,9 milyar $ → ölçü 5 %92,6 (✅; bizde %57,4 ➖). Bulgu 1 düzeltilmeseydi KO'yu bu kalem tek başına SAĞLAM'a taşırdı. | Orta | v1'de otomatik düzeltme yapmayın. Bayrak koyun: "son 2 yılda OCF %30'dan fazla düştü, net kâr arttı" → AI'a 10-K'dan "neden?" sorulsun. | kaynaktan doğrulandı + Ek B'den yeniden hesaplandı |
| 4 | veri / kod (b) | NVDA FY2026 (Ocak 2026) likit | 10,61 okunuyor, doğrusu 62,56. | NVDA FY2026 bilançosu: nakit 10.605, menkul kıymet 51.951; basın bülteni: "Cash, cash equivalents and marketable securities $62,556".\[5\]\[6\] sec-api.io'ya göre menkul kıymet satırının etiketi `nvda:MarketableSecuritiesAndEquitySecuritiesFVNI`, yani şirkete özel bir uzantı (ikincil kaynak).\[7\] FY2026 ROCE paydası 164,0 yerine 112,1 olmalı; 5y ROCE %76'dan yaklaşık %82'ye çıkıyor. | Düşük (sınıf aynı) | Bulgu 1'deki YoY bayrağı bunu yakalar (43,2'den 10,6'ya düşüş). | kaynaktan doğrulandı (nvidianews, sec.gov nvda-20260125) + yeniden hesaplandı |
| 5 | veri / kod (b) | NKE, likit FY2022-FY2026 | Yalnızca nakit okunuyor. | Nike FY2026 bülteni: "Cash and equivalents and short-term investments were $9.0 billion";\[8\] Ek B 7,56. FY2021'deki 13,48 doğru (9,889 + 3,587),\[9\] sonraki yıllarda kısa vadeli yatırım kayboluyor. Nike'ın hangi etikete geçtiği doğrulanamadı. Doğru veriyle 9,0 > 7,94 borç olduğu için ölçü 6 ve 7 "nakit > borç". | Düşük | Bulgu 1 ile aynı. | kaynaktan doğrulandı (Nike 8-K / 10-K FY2026) |
| 6 | veri (b) | PFE 2025 likit | 10,32 okunuyor, doğrusu 13,60. | Pfizer FY2025 10-K XBRL: kısa vadeli yatırım 12.454 milyon $ `OtherShortTermInvestments` etiketinde.\[10\]\[11\] `MarketableSecuritiesCurrent` hiç kullanılmamış, `ShortTermInvestments` 2021'den sonra yok.\[12\] Kod büyük ihtimalle alt kalem `AvailableForSaleSecuritiesDebtSecuritiesCurrent`'i (yaklaşık 9,2) almış; bu kısım çıkarım. Ölçü 7: 6,9'dan 6,5'e iniyor, hâlâ ❌. | Düşük | Bulgu 1 ile aynı. | kaynaktan doğrulandı (data.sec.gov companyconcept) + akıl yürütme |
| 7 | veri / kod (b) | PFE 2020 borç; `BORC_UV` grup sırası | 4,56 okunuyor, doğrusu 39,84. Grup 1 (`LongTermDebt`) tek bir borç kalemini tutuyor ve önce geldiği için kazanıyor. | Pfizer XBRL 2020-12-31: `LongTermDebt` = 4,0 milyar (2017 sonrası tek değer); `DebtCurrent` 2,703 + `LongTermDebtNoncurrent` 37,133 = 39,836.\[13\]\[14\]\[15\] | Düşük (yalnızca son yıl kullanılıyor), ama mimari risk yüksek | `DebtCurrent` + `LongTermDebtNoncurrent` grubunu öne al; borç bir yılda %30'dan fazla değişirse bayrak koy. | kaynaktan doğrulandı (data.sec.gov LongTermDebt, DebtCurrent, LongTermDebtNoncurrent) |
| 8 | veri / kod (b) | Faaliyet kârı fallback'i (NKE; PFE ve DOW da aynı yolu kullanıyor) | Vergi öncesi kâra brüt faiz gideri ekleniyor, faiz geliri düşülmüyor. | Nike FY2026 10-K: EBIT 3.850 (FY2025: 3.778), "Interest (income) expense, net (50) / (107)".\[16\] Kod 4,22 / 4,27 buluyor, %10-13 fazla. Ölçü 3 %8,3 (bizde %9,1), ➖ kalıyor. Faiz karşılama yaklaşık 12,0 (bizde 13,1). | Orta | Fallback EBIT = vergi öncesi - net faiz geliri (net etiket varsa). | kaynaktan doğrulandı |
| 9 | veri / kod (b) | DOW, net kâr; ölçü 5 etiketi, PEG | `NetIncomeLoss` bulunamıyor, eksik değer 0 sayılıyor ve ekranda "net kâr ≤ 0 → anlamsız" yazıyor. | Dow XBRL'de "Net Income (Loss) Available to Common Stockholders, Basic" etiketi var (sec.gov R7).\[17\] FY2025 10-K: Dow Inc. ortaklarına düşen net zarar 2.623, toplam net zarar 2.444.\[18\]\[19\] Doğru veriyle 3y toplam 0,66 + 1,20 - 2,44 = -0,58 → yine hesaplanamıyor, ama bu kez doğru nedenle. | Düşük | Net kâr eş anlamlıları: `NetIncomeLossAvailableToCommonStockholdersBasic`, `ProfitLoss`. Eksik ≠ 0. | kaynaktan doğrulandı + yeniden hesaplandı |
| 10 | veri, tek seferlik (b) | BA 2025 faaliyet kârı; tür ataması | 4,28 milyar $'ın içinde 9,566 milyar $ Digital Aviation satış kazancı var; kazanç hariç yaklaşık -5,3. | Boeing FY2025 10-K: "primarily due to a 2025 gain on the Digital Aviation Solutions Divestiture of $9,566 million".\[20\] BA, 5 yılın tek pozitif yılı bu olduğu için Döngüsel sayılıyor. Kazanç hariç tür Kârsız olur: 2 ✅, 3 ❌, 4 ❌, 5 - → yine ZAYIF. 2025 "temettü" 0,33 aslında zorunlu dönüştürülebilir imtiyazlı hisse temettüsü (FY2025 10-K: "Dividends paid on Mandatory convertible preferred stock in 2025 and 2024 were $331 and $0"); adi hisse temettüsü değil. | Düşük (sınıf aynı) | v1: OI'yi büyük ölçüde açıklayan satış kazancı varsa ("GainLossOnSaleOfBusiness" vb.) bayrak. | kaynaktan doğrulandı + yeniden hesaplandı |
| 11 | kural (b) | SNAP, SBC; ölçü 7, 10, FCF verimi | FCF pozitif, ama SBC FCF'nin 2 katından fazla. | Snap FY2025: FCF 437,2 milyon $, hisse bazlı ödeme (SBC) 1.016,8 milyon $\[21\]\[22\] → FCF - SBC ≈ -0,58 milyar $. Ölçü 7'deki 2,8 yıl ✅ ve %4,6 FCF verimi yanıltıcı. | Düşük (Kârsız tür, zaten ZAYIF) | v1: FCF - SBC'yi ayrı satır olarak göster; FCF verimi ve ölçü 7/10'da SBC düşülmüş FCF kullan. | kaynaktan doğrulandı (Snap 10-K, Q4 bülteni) |
| 12 | kural (b/c) | SBUX, kiralar; ölçü 7, Borç | 10,54 milyar $ operasyonel kira yükümlülüğü borca dahil değil. | SBUX FY2025 bilançosu: kısa vadeli 1.564,5 + uzun vadeli 8.972,2.\[23\] Kaba yöntem: (16,07 + 10,54 - 3,47) / 3,15 = 7,35 → ❌ → Borç ❌ → ZAYIF. Ama FCF zaten kira ödemeleri düşülmüş halde; kira nakdi geri eklenirse (6 ayda 928,8 milyon $, yıllık yaklaşık 1,86)\[24\] 23,14 / 5,0 ≈ 4,6 → ➖ → ORTA. **Hipotez J kaba haliyle reddedildi:** kira ödemesini iki kez sayıyor. | Orta | v1: sınıfa sokma; "kira dahil borç / yıl" bilgi satırı ekle. | kaynaktan doğrulandı (SBUX 8-K / 10-K FY2025) + yeniden hesaplandı |
| 13 | veri (b) | KO borç | Satış amaçlı elde tutulan Afrika şişeleme operasyonunun borcu (398 + 850 = 1.248) ve 56 milyon $ diğer kısa vadeli borç eksik.\[1\]\[4\] | KO 10-K, held-for-sale notu. Eklenince ölçü 7 4,49'dan 4,68'e çıkıyor. Kira 1.722 (XBRL `OperatingLeaseLiability`)\[25\] de eklenirse 4,94: hâlâ ➖ ama eşiğe çok yakın. "Loans and notes payable" 1.551'in 1.495'i ticari senet; büyük kısmı yakalanıyor. | Düşük | `LiabilitiesHeldForSale` içindeki borcu ayrı satırda göster (v1'de gerekli değil). | kaynaktan doğrulandı (KO 10-K, data.sec.gov) |
| 14 | kural (c) | Ölçü 2 tanımı (bütün şirketler; NVDA, PFE) | 5 yıllık ortalama son yılı da içeriyor (düşüşü yaklaşık %20 sönümlüyor); ölçü istikrarı değil trendi ölçüyor. | NVDA FY2026 brüt marjı %71,1, önceki yıl %75,0, yani -3,9 puan;\[26\] Ek A yine de ✅ +2,9 gösteriyor çünkü FY2023 dibi ortalamada. PFE %58-74 arası dalgalanıyor ve ✅. | Orta | Ölçü 2 = min(son yıl - önceki 4 yılın ort., son yıl - önceki yıl). Etkisi: NVDA ❌ olur ama 4 ✅ / 1 ❌ ile SAĞLAM kalır; NKE ➖, SNAP ➖, SBUX/INTC/DOW ❌ zaten öyle. Sınıf değişmiyor. | kaynaktan doğrulandı (NVDA bülteni) + yeniden hesaplandı |
| 15 | kural (c) | RIVN, ölçü 2 (belirleyici) | +222,9 puan anlamsız. | 2021 brüt marjı yaklaşık -%800 (-0,47 / 0,06) ve 5y ortalamayı belirliyor. | Orta (sınıf yine ZAYIF: 10 ❌, 8 ❌) | Mutlak marjı %100'ü aşan ya da geliri son yılın %10'undan az olan yılları ortalamadan çıkar; 3 yıldan az kalırsa "-". | Ek B'den yeniden hesaplandı |
| 16 | kod (c) | `M[9]` (hızlı büyüyende belirleyici) | Brüt kâr hem 3 yıl önce hem bugün ≤ 0 ise `cagr` None dönüyor → "·" (hesaplanamadı), ❌ değil. | `cagr`: `a <= 0` → None; 'POZ' yalnızca `0 < brut[son]` iken. Brüt zararı süren bir hızlı büyüyen kırmızı yerine boş alır ve BELİRSİZ'e yaklaşır. | Orta | İki uç da ≤ 0 → ❌. | sadece akıl yürütme (kod okuma) |
| 17 | kod (c) | `fcf3`, `sn`, `sf`, `st`, `sf5`, `yat.get(e, 0)` | Eksik değer sessizce 0 sayılıyor. | Dow örneği (#9); capex eksikse FCF şişer. NVDA FY2021 capex eksik ama hiçbir pencerede değil (fcf3 = FY2024-26, T = FY2022-26), **etkisi yok**. | Orta | Eksik yıl varsa None + "veri eksik"; 2'den az yıl kalırsa hesaplama. | Ek B + kod okuma |
| 18 | kod (c) | Bölünme düzeltmesi | Ters bölünme (oran ≈ 1/k) yakalanmıyor; hisse sayısı %90 düşünce "geri alım" ✅ görünüyor. Birleşmeden gelen yaklaşık 2× sıçrama bölünme sanılabilir. | `for k in (2, 3, 4, 5, 8, 10, 20)` yalnızca r ≈ k'yi kontrol ediyor. | Orta | 1/k'yi de kontrol et; Yahoo bölünme listesinde karşılığı yoksa düzeltme yapma, bayrak koy. | sadece akıl yürütme |
| 19 | kod / kapsam (c) | ADR | Brief "ADR dahil" diyor ama kod yalnızca `us-gaap` ve 10-K okuyor. 20-F / `ifrs-full` dosyalayan ADR'ler boş gelir. | `["facts"].get("us-gaap", {})`, form filtresi `("10-K", "10-K/A")`. | Orta | v1: 20-F dosyalayanları "kapsam dışı (20-F)" diye etiketle; IFRS desteği sonra. | sadece akıl yürütme |
| 20 | kural (c) | Hızlı büyüyen belirleyici seti (1, 9, 2, 10, 8) | Kârlılık / getiri ölçüsü yok. Nakit yakan ama kasası dolu ve seyrelmesi düşük bir şirket SAĞLAM olabilir. | RIVN yalnızca 10 ve 8 nedeniyle ZAYIF. | Orta | Kural: hızlı büyüyende ölçü 3 ❌ ve fcf3 < 0 ise SAĞLAM olamaz (en fazla ORTA). 10 şirkette etkisi yok. | sadece akıl yürütme |
| 21 | kural (c) | Döngüsel tespiti | Enerji / Malzeme dışındaki zirvedeki döngüseller (konut, bellek çipi, denizcilik, otomotiv) 5 yılda zarar yılı yoksa Hızlı büyüyen → SAĞLAM olur. Tersine, tek değer düşüklüğü (impairment) yılı olan kaliteli bir şirket Döngüsel'e düşer. | Lynch'in One Up on Wall Street'te uyardığı tuzak ("Cyclicals are the most misunderstood of all the types of stocks"; ikincil kaynaktan alıntı); BA da yalnızca bir satış kazancı sayesinde Döngüsel (#10). | Orta | SEC submissions API'den SIC koduyla döngüsel sektör listesi. NVDA (SEC EDGAR'da SIC 3674 "Semiconductors & Related Devices") Döngüsel olursa 4 ✅, Borç ✅, 8 ✅ → yine SAĞLAM. | sadece akıl yürütme |
| 22 | kural (d) | Sınırda değerler | KO: ROCE yaklaşık %14,4 (eşik 15), faiz karşılama 8,34 (eşik 8), T marjı %1,6 (40,58'e karşı 39,96), ölçü 7 4,5-4,9 (eşik 5). SBUX gelir büyümesi %4,86 (İstikrarlı dev eşiği 5). | Ek B'den hesap | Düşük | Eşiğin %10 yakınındaki değerlere "sınırda" etiketi; sınıfı değiştirmesin. | Ek B'den yeniden hesaplandı |
| 23 | kod (d) | Yorumlar, ölü kod | "temettü karşılama (3 yıl)" yorumu var ama kod 5 yıl kullanıyor (kural da 5 yıl). Küçülme yorumu "3 yıl üst üste düştü" diyor ama kod 3y CAGR < 0'a bakıyor (kural da öyle). `A[8]` içinde `if False` ölü kodu var. `hbk` çekiliyor ama kullanılmıyor. | Kod satırları | Düşük | Yorumları kurala göre düzelt, ölü kodu sil. | kod okuma |
| 24 | kod (d) | Yıl sonu tespiti, sektör, kapsam dışı | Gelir ve OI etiketlerindeki bitiş tarihlerinin birleşimi, 52/53 haftalık yıllarda ya da mali yıl değişiminde neredeyse aynı iki yıl üretebilir. Sektör ve kapsam dışı listesi elle tutuluyor. | `_yil_sonlari`, `SEKTOR` | Düşük | 10 günden yakın bitiş tarihlerini birleştir; SIC'i submissions API'den çek. | sadece akıl yürütme |

## 2. Veri kontrolü (görev 2): son yıl, Ek B ile kaynak karşılaştırması

| Şirket | Kalem | Ek B | Kaynak (10-K / 8-K) | Durum |
|---|---|---|---|---|
| KO | Gelir / Faaliyet kârı | 47,94 / 13,76 | 47.941 / 13.762\[27\] | hata bulunamadı |
| KO | OCF / FCF / hisse | 7,41 / 5,30 / 4.313 | 7.408 / "$5.3 billion" / 4.313\[4\]\[28\]\[29\] | hata bulunamadı (capex 2,11, FCF'den türetildi) |
| KO | Borç | 45,44 | 42.119 + 1.822 + 1.551 = 45.492 (+1.248 satış amaçlı)\[2\]\[4\]\[29\] | büyük ölçüde doğru |
| KO | Likit | 10,27 | 15.806\[2\] | **hatalı** |
| NVDA | Gelir / OI / net kâr | 215,94 / 130,39 / 120,07 | 215.938 / 130.387 / 120.067\[6\] | hata bulunamadı |
| NVDA | Hisse | 24.514 | 120.067 / 4,90 HBK ≈ 24.500\[6\] | tutarlı (türetildi) |
| NVDA | Likit | 10,61 | 62.556\[6\] | **hatalı** |
| NKE | Gelir / OCF / net / vergi öncesi | 46,40 / 2,87 / 3,11 / 3,90 | 46,4 milyar / 2.868 / 3.108 / 3.900\[30\]\[31\]\[32\] | hata bulunamadı |
| NKE | Faaliyet kârı (fallback) | 4,22 | EBIT 3.850 | **hatalı (%10 fazla)** |
| NKE | Borç / likit | 7,94 / 7,56 | 7.942 (ikincil kaynak) / 9,0 milyar\[8\]\[33\] | borç doğru, likit **hatalı** |
| SBUX | OCF / varlık / KV yükümlülük / borç | 4,75 / 32,02 / 10,21 / 16,07 | 4.747,5 / 32.019,7 / 10.210,4 / 16.074,8\[23\] | hata bulunamadı |
| PFE | Borç | 64,64 | 3.154 + 61.641 = 64.795\[34\] | büyük ölçüde doğru |
| PFE | Likit | 10,32 | 1.142 + 12.454 = 13.596\[35\] | **hatalı** |
| BA | Gelir / OI / net | 89,46 / 4,28 / 2,23 | 89,5 milyar / 4.281 / 2.238\[36\]\[37\] | rakam doğru, OI tek seferlik kazanç içeriyor |
| SNAP | OCF / FCF / net | 0,66 / 0,44 / -0,46 | 656,2 / 437,2 / -460,5 milyon\[21\] | hata bulunamadı |
| DOW | Net kâr | - | -2.444 (ortaklara -2.623)\[19\] | **eksik** |

Doğrulayamadıklarım: NVDA OCF/capex/borç, NKE capex, PFE gelir (yalnızca ikincil kaynakta gördüm). SBUX geliri ise doğrulandı: FY2025 10-K'ya göre 37.184,4 milyon $ (Ek B 37,18).

## 3. Önerilen kuralların 10 şirkete etkisi

| Şirket | Mevcut | Likit düzeltmesi | + ROCE = min(3y, 5y) | Kira, kaba yöntem | Kira, tutarlı yöntem | T 3 yıl | Yeni ölçü 2 |
|---|---|---|---|---|---|---|---|
| KO | ORTA | **SAĞLAM** | SAĞLAM (ROCE 3y yaklaşık %15,2, 5y %14,4 → ➖) | SAĞLAM (4,94 ➖) | SAĞLAM | ORTA (T ❌, ama tek seferlikler yüzünden) | SAĞLAM |
| NVDA | SAĞLAM | SAĞLAM | SAĞLAM | SAĞLAM | SAĞLAM | SAĞLAM | SAĞLAM (2 ❌) |
| NKE | ORTA (k) | ORTA (k) | ORTA (k), 3y %23,9 | ORTA (k) | ORTA (k) | ORTA (k), 12,07 > 6,88 | ORTA (k) |
| SBUX | ORTA | ORTA | ORTA, 3y %20,5 | **ZAYIF** | ORTA | ORTA, 9,44 > 7,78 | ORTA |
| PFE | ORTA | ORTA | **ZAYIF** | ORTA | ORTA | **ZAYIF**, 23,7 < 28,5 | ORTA |
| INTC, BA, SNAP, DOW, RIVN | ZAYIF | ZAYIF | ZAYIF | ZAYIF | ZAYIF | ZAYIF | ZAYIF |

Ne öneriyorum, ne önermiyorum:
- **Öneriyorum:** likit düzeltmesi (bu bir hata düzeltmesi) ve ROCE = min(3y, 5y). Bu ikincisi ilkeli bir kural: Fundsmith'in (Terry Smith) ölçütü "sustainably high return on capital", yani getirinin sürmesi (MoneyWeek'in aktarımıyla). PFE'ye bakarken buldum ama tek bir şirkete göre kurulmuş değil.
- **Önermiyorum:** T'yi 3 yıla indirmek. KO'yu yalnızca IRS ve fairlife çıkışları yüzünden ❌ yapıyor; tek seferlikler hariç 31,9 > 25,1, yani karşılanıyor.
- **Önermiyorum:** kaba kira ayarlaması (kira ödemesini iki kez sayıyor).

## 4. 10 şirket: bizim sınıf ve benim sınıfım

| Şirket | Bizim sınıf | Benim sınıfım | Kısa gerekçe |
|---|---|---|---|
| Coca-Cola (KO) | ORTA | **SAĞLAM (sınırda)** | ORTA sonucu likit verisindeki hatadan geliyor; doğru veriyle mevcut kurallar SAĞLAM veriyor. İstikrarlı dev yolundan gitse de sonuç aynı (2 ✅, 3 ✅, 4 ➖, 5 ➖). "Kuralı KO için bükme" ilkesi iki yönde de geçerli: hatayla elde edilen ORTA'yı da korumayın. |
| Nvidia (NVDA) | SAĞLAM | SAĞLAM | Belirleyicilerin hepsi eşikten çok uzak. Yeni ölçü 2 ile bile 4 ✅ / 1 ❌. |
| Nike (NKE) | ORTA (küçülme) | ORTA | Doğru veriyle borç tarafı daha da iyi (nakit > borç). Zayıflık büyümede ve marjda; Yavaş büyüyen tipinde büyüme belirleyici değil, küçülme kuralı tavanı ORTA'da tutuyor. ZAYIF yapacak genel bir kural bulamadım. |
| Starbucks (SBUX) | ORTA | ORTA | Ölçü 2 ❌ (-6,1 puan; 892 milyon $ yeniden yapılanma\[38\] hariç da yaklaşık -3,7, ❌). Tutarlı kira ayarlamasında Borç ➖. Tek ❌ var. |
| Pfizer (PFE) | ORTA | **ZAYIF** | ROCE 3y %5,1 ❌ ve Borç ❌ (ölçü 7 doğru likitle 6,5). Covid zirvesi 5 yıllık ortalamayı taşıyor. |
| Intel (INTC) | ZAYIF | ZAYIF | ROCE %2,1, Borç ❌, temettü karşılanmıyor. |
| Boeing (BA) | ZAYIF | ZAYIF | 2025 kârı satış kazancından geliyor;\[39\] hangi türle bakılsa ZAYIF. |
| Snap (SNAP) | ZAYIF | ZAYIF | Kârsız; SBC düşülünce FCF negatif. |
| Dow (DOW) | ZAYIF | ZAYIF | ROCE %6,1, Borç ❌ (31 yıl), FCF trendi 2,8 → 0 → -1,4. |
| Rivian (RIVN) | ZAYIF | ZAYIF | Nakit ömrü 1,6 yıl ❌, seyrelme %29,9 ❌. Ölçü 2'deki ✅ anlamsız. |

## 5. Açık sorular (1-12)

1. **Prototip / kabul testi:** Mutlaka yapın. Bu denetimde kontrol ettiğim 4 şirketin 4'ünde likit hatalı çıktı. Kabul testi listesine "nakit + KV yatırım + menkul kıymet" ile "toplam borç"un bilanço satırlarıyla karşılaştırmasını açıkça yazın.
2. **Capex bulunamazsa 0:** Yanlış varsayım. O yılın FCF'si None olsun. NVDA FY2021'de etkisi yoktu, ama başka şirkette FCF'yi şişirir.
3. **Eksik yıl 0 sayılıp 3'e bölünüyor:** Mevcut yıllara bölün; 2'den az yıl varsa hesaplamayın.
4. **Dow ortalaması:** Ortalama, kötüleşmeyi saklıyor (2,8 → 0 → -1,4). v1'de sınıfı değiştirmeden bayrak koyun: "son yıl FCF < 0 ve 3 yıldır düşüyor" → AI'a "neden?" sorulsun.
5. **ROCE paydasında şerefiye:** Bırakın. Smith yaklaşımında ödenen bedel sermayedir; KO'nun %13,8'i satın alımlara ödenen fiyatın dürüst getirisidir. Bu oranın düşük kalmasının asıl nedeni likit hatasıydı (paydayı şişiriyordu).
6. **Fallback faaliyet kârı:** Net faiz kullanın (Nike örneği %10 sapma). `InterestPaidNet` kullanılırsa çıktıda "nakit faiz" diye işaretleyin.
7. **Borç bileşenleri / kiralar:** Asıl risk çakışmadan çok yanlış grup seçimi (PFE 2020). Kiraları v1'de yalnızca bilgi satırı olarak gösterin.
8. **PEG'de büyümeyi %25'le sınırlama:** Evet, basit ve Lynch ile uyumlu. NVDA'da F/K yaklaşık 30 (0,15 × 202) → PEG yaklaşık 1,2 ("makul"); 0,15'ten daha anlamlı.
9. **SBC:** FCF verimi ve ölçü 7/10 için düşün; ölçü 5'i değiştirmeyin. Snap'te FCF - SBC negatif.
10. **FCF verimi tutarlılığı:** Ana değer 3y ortalama FCF olsun, son yıl yanında görünsün. KO'da son yıl %1,4, 3y ortalamayla yaklaşık %1,7, tek seferlikler hariç yaklaşık %3,0. Tek yıl yanıltıcı.
11. **Gelir mi, kâr büyümesi mi:** v1'de gelirle kalın (daha az tek seferlik etkisi var), sınır için "sınırda" etiketi ekleyin. KO her iki tür yolundan da aynı sınıfa çıkıyor, bu yüzden acil değil.
12. **Mali yıl farkları:** 10 yıllık bir yatırımcı için önemsiz. Tek uyumsuzluk fiyat satırında: Yahoo F/K son 12 ay, FCF son mali yıl. Etiketleyin.

## 6. En önemli 3 bulgu

1. **Likit varlık toplama hatası (sistemik):** KO, NVDA, NKE ve PFE'de eksik. KO'nun sınıfını ORTA'dan SAĞLAM'a çeviriyor. Kök neden: eş anlamlı listesi toplanacak bileşenleri alternatif sayıyor, `OtherShortTermInvestments` listede yok, şirkete özel uzantı etiketler (`nvda:`) görülmüyor.
2. **Zaman penceresi kötüleşmeyi gizliyor (PFE):** 5 yıllık ROCE ➖, son 3 yıl ❌. "ROCE = min(3y, 5y)" kuralı yalnızca PFE'nin sınıfını değiştiriyor (ZAYIF).
3. **Tek seferlik kalemler ve fallback'ler rakamları bozuyor:** KO OCF'deki 12,1 milyar $ tek seferlik çıkış, Boeing'in 9,6 milyar $ kazancı, Nike'ta %10 şişkin EBIT fallback'i, Dow'da eksik net kârın 0 sayılması. Bu denemede sınıfı değiştirmediler, ama mekanizma her an değiştirebilir.

## 7. Kör noktalar (görev 7) ve tuzak şirket tipleri (görev 4)

En önemli 5 risk:
1. **Etiket toplama (bileşen mi, toplam mı):** Likit ve borç; şirketler etiket değiştiriyor, uzantı etiket kullanıyor. Tek bir yanlış "ilk bulunan" sınıfı değiştiriyor.
2. **Tek seferlik kalemler:** OCF'de vergi mevduatı ve kazanç-ödemesi (earn-out), OI'de satış kazancı veya yeniden yapılanma. Sistem bunları görmüyor; ne bayrak var ne AI sorusu.
3. **Yanlış tür:** Zirvedeki döngüseller "Hızlı büyüyen"; tek bir kazanç yılı türü değiştiriyor (BA); gelir/kâr ayrımı.
4. **Bilanço dışı ve gizli maliyetler:** SBC (Snap), kiralar (SBUX), satın almalar. FCF = OCF - capex satın almaları içermiyor, bu yüzden seri satın alıcıların (roll-up) ölçü 5 ve 7'si şişik görünür.
5. **Ortalamalar trendi gizliyor:** PFE ROCE, Dow FCF, ölçü 2'nin son yılı ortalamaya katması.

Tuzak tipler:
- **Zirvedeki döngüseller** (konut, bellek, denizcilik, otomotiv) → yanlışlıkla SAĞLAM.
- **Kasası dolu, nakit yakan hiper-büyüyenler** → hızlı büyüyen setinde kârlılık ölçüsü olmadığı için SAĞLAM.
- **Seri satın alıcılar** → FCF şişik.
- **Faktoring veya işletme sermayesiyle OCF'yi parlatanlar** (KO 10-K'sı 2024'teki alacak faktoring programının OCF'ye katkısını ayrıca anıyor).\[4\]
- **Ters bölünme yapan küçük şirketler** → ölçü 8 ✅.
- **Büyük varlık satışı yapanlar** → ölçü 3 ve tür bozuluyor.

## 8. Hata bulamadığım alanlar

- Ek A, Ek B'den 10 şirketin hepsinde yeniden üretiliyor: ölçü 1, 2, 3, 5, 6, 7, 8, 9, 10 ve T. Farklar yuvarlamadan: SNAP -8,9 / -9,0; BA hisse +33,9 / +34,1; NKE faiz karşılama 13,2 / 13,1; SBUX ölçü 2 -6,1 / -6,2. ROCE KO (13,8), NVDA (76,0), NKE (25,5), SBUX (21,5), PFE (yaklaşık 11,8-12,0) için tutuyor. INTC, BA, SNAP, DOW, RIVN'de ROCE'yi yeniden hesaplamadım; renkleri eşikten uzak.
- Eşik tablosu tutarlı ve tek yönlü. Sınıf kuralının kodu metinle aynı (`yesil * 2 >= len(br)`, `len(hesap) * 2 < len(br)`). Borç birleştirme mantığı kurala uyuyor.
- Tür atamaları kurala göre doğru. NVDA'da ×10 bölünme doğru düzeltilmiş (25.070 / 2.535 = 9,89). RIVN'de halka arz yılı doğru atlanmış (+%29,9). Küçülme kuralı doğru çalışıyor (NKE).
- KO (45,44'e karşı 45,49), PFE 2025 (64,64'e karşı 64,80), NKE (7,94) ve SBUX (16,07) son yıl borçları kaynakla uyumlu.\[2\]\[23\]\[33\]\[34\]
- NVDA FY2021'deki eksik capex'in hiçbir ölçüye etkisi yok.

## 9. Aksiyon adımları

1. **Bugün:** Likit toplamayı düzeltin ve 10 şirketi yeniden çalıştırın. Beklenen değişiklik yalnızca KO'nun SAĞLAM olması; NKE ve PFE'de rakamlar değişecek ama sınıf değişmeyecek. Ardından KO, NVDA, NKE ve PFE'nin likitini bu rapordaki kaynak değerlerle karşılaştırın (15,81 / 62,56 / yaklaşık 9,0 / 13,60).
2. **Bu hafta:** Net kâr eş anlamlıları, net faizli EBIT fallback'i, ters bölünme kontrolü ve "eksik ≠ 0" düzeltmelerini yapın. ROCE = min(3y, 5y) kuralını ekleyin; PFE'nin ZAYIF olması beklenir.
3. **20 hisselik kabul testi:** Her hisse için 3 bayrak koyun (likit veya borçta %50'den fazla YoY değişim, OCF ile net kâr ayrışması, OI'yi açıklayan satış kazancı) ve "sınırda" etiketi ekleyin. Bayraklı satırları elle 10-K ile kontrol edin.

```python
# 1) Liquid assets: sum components instead of first-found
STI_TAGS = ["ShortTermInvestments", "OtherShortTermInvestments"]          # same line item, alternatives
MS_TAGS = ["MarketableSecuritiesCurrent"]                                  # separate line item, additive
SUBSET_TAGS = ["AvailableForSaleSecuritiesDebtSecuritiesCurrent"]          # only if nothing else found

def first(s, tags, e):
    for t in tags:
        v = s._an(t).get(e)
        if v is not None:
            return v
    return None

def liquid(s, e):
    cash = first(s, ["CashAndCashEquivalentsAtCarryingValue"], e) or 0
    sti = first(s, STI_TAGS, e)
    ms = first(s, MS_TAGS, e)
    if sti is None and ms is None:
        sti = first(s, SUBSET_TAGS, e)
    return cash + (sti or 0) + (ms or 0)

def jump_flag(series, limit=0.5):
    ys = sorted(series)
    return [b for a, b in zip(ys, ys[1:]) if series[a] and abs(series[b] / series[a] - 1) > limit]

# 2) Net income synonyms; missing is None, never 0
ES["net"] = ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"]

# 3) Fallback EBIT with NET interest (income-positive tag)
NET_INT = ["InterestIncomeExpenseNonoperatingNet", "InterestIncomeExpenseNet"]
def ebit_fallback(pre_tax, net_int_income, gross_int_exp):
    if net_int_income is not None:
        return pre_tax - net_int_income
    return pre_tax + (gross_int_exp or 0)

# 4) Reverse splits
def split_factor(r):
    for k in (2, 3, 4, 5, 8, 10, 20):
        if abs(r - k) / k < 0.06:
            return k
        if abs(r - 1 / k) / (1 / k) < 0.06:
            return 1 / k
    return None   # adjust only if Yahoo split history confirms; else flag "possible merger"

# 5) ROCE = worse of 5y and 3y
def roce_rule(roce_by_year, years):
    r5 = [roce_by_year[e] for e in years[-5:] if e in roce_by_year]
    r3 = [roce_by_year[e] for e in years[-3:] if e in roce_by_year]
    if len(r5) < 3:
        return None
    return min(sum(r5) / len(r5), sum(r3) / len(r3)) if len(r3) >= 2 else sum(r5) / len(r5)
```

Örnek çıktı (düzeltilmiş KO): `◆ 7 Borcu öder (yıl) ➖ 4.5 · ◆ B Borç ✅ · SINIF: SAĞLAM (sınırda: 4, 6, T)`.

## Sources

1. [February 20, 2026 - 10-K: Annual report \[Section 13 and 15(d), not S-K Item 405\]](https://investors.coca-colacompany.com/filings-reports/all-sec-filings/content/0001628280-26-010047/ko-20251231.htm)
2. [COCA COLA CO - Form ARS - FY2025](https://www.sec.gov/Archives/edgar/data/21344/000110465926028252/tm263575d2_ars.pdf)
3. [ko-20241231](https://www.sec.gov/Archives/edgar/data/21344/000002134425000011/ko-20241231.htm)
4. [COCA COLA CO - Form 10-K - FY2025](https://www.sec.gov/Archives/edgar/data/21344/000162828026010047/ko-20251231.htm)
5. [NVIDIA : Annual Report for Fiscal Year Ending January 25, 2026 (Form 10-K)](https://www.marketscreener.com/news/nvidia-annual-report-for-fiscal-year-ending-january-25-2026-form-10-k-ce7e5cd8d18af32d)
6. [NVIDIA Announces Financial Results for Fourth Quarter and Fiscal 2026](https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-fourth-quarter-and-fiscal-2026)
7. [Multi-year income statement, balance sheet and financial ratios from 10-K annual reports](https://sec-api.io/financial-analysis-prompts/nvidia-financial-statements)
8. [NIKE, Inc. Reports Fiscal 2026 Fourth Quarter and Full Year Results —](https://about.nike.com/en/newsroom/releases/nike-inc-reports-fiscal-2026-fourth-quarter-and-full-year-results)
9. [Nike (NKE) Balance Sheet](https://stockanalysis.com/stocks/nke/financials/balance-sheet/)
10. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000078003/us-gaap/OtherShortTermInvestments.json>
11. [PFIZER INC - Form 10-K - FY2025](https://www.sec.gov/Archives/edgar/data/78003/000007800326000026/pfe-20251231.htm)
12. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000078003/us-gaap/ShortTermInvestments.json>
13. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000078003/us-gaap/DebtCurrent.json>
14. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000078003/us-gaap/LongTermDebtNoncurrent.json>
15. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000078003/us-gaap/LongTermDebt.json>
16. [NIKE, Inc. - Form 10-K - FY2026](https://www.sec.gov/Archives/edgar/data/0000320187/000032018726000088/nke-20260531.htm)
17. [XML 20 R7.htm IDEA: XBRL DOCUMENT v3.20.2](https://www.sec.gov/Archives/edgar/data/29915/000175178820000034/R7.htm)
18. [DOW INC. - Form 10-K - FY2025](https://www.sec.gov/Archives/edgar/data/1751788/000175178826000018/dow-20251231.htm)
19. [Dow reports fourth quarter 2025 results](https://investors.dow.com/en/news/news-details/2026/Dow-reports-fourth-quarter-2025-results/default.aspx)
20. [BOEING CO - Form 10-K - FY2025](https://www.sec.gov/Archives/edgar/data/12927/000162828026004357/ba-20251231.htm)
21. [Snap Inc - Form 10-K - FY2025](https://www.sec.gov/Archives/edgar/data/1564408/000156440826000013/snap-20251231.htm)
22. [Snap Inc. - Snap Inc. Announces Fourth Quarter and Full Year 2025 Financial Results](https://investor.snap.com/news/news-details/2026/Snap-Inc--Announces-Fourth-Quarter-and-Full-Year-2025-Financial-Results/default.aspx)
23. [Document](https://www.sec.gov/Archives/edgar/data/829224/000082922425000074/sbux-09282025xexhibit991.htm)
24. [STARBUCKS CORP (Form: 10-Q, Received: 04/29/2025 16:11:16)](https://content.edgar-online.com/ExternalLink/EDGAR/0000829224-25-000034.html?hash=ca38efd1b719d91b8334ca2d1680e4a11148abb51f5decff8951e06ca57449db&dest=sbux-20250330_htm)
25. <https://data.sec.gov/api/xbrl/companyconcept/CIK0000021344/us-gaap/OperatingLeaseLiability.json>
26. [Q4 FY26 CFO Commentary](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000019/q4fy26cfocommentary.htm)
27. [The Coca-Cola Company (via Public) / Annual Report for Fiscal Year Ending December 31, 2025 (Form 10-K)](https://www.publicnow.com/view/2720FC6181EA09D27E233A77A9C859FE95D852E8?1771602440=)
28. [Coca-Cola Reports Fourth Quarter and Full Year 2025 Results :: The Coca-Cola Company (KO)](https://investors.coca-colacompany.com/news-events/press-releases/detail/1151/coca-cola-reports-fourth-quarter-and-full-year-2025-results)
29. [February 10, 2026 - EX-99.1 - 8-K: Current report](https://investors.coca-colacompany.com/filings-reports/all-sec-filings/content/0001628280-26-006642/a2025q4earningsreleaseex-9.htm)
30. [NIKE, Inc. Reports Fiscal 2026 Fourth Quarter and Full Year Results](https://www.businesswire.com/news/home/20260630156660/en/NIKE-Inc.-Reports-Fiscal-2026-Fourth-Quarter-and-Full-Year-Results)
31. [NIKE, Inc. - Form ARS - FY2026](https://www.sec.gov/Archives/edgar/data/0000320187/000130817926000376/nke015577-ars.pdf)
32. [NIKE, Inc. Reports Fiscal 2026 Fourth Quarter and Full Year Results](https://www.nasdaq.com/press-release/nike-inc-reports-fiscal-2026-fourth-quarter-and-full-year-results-2026-06-30)
33. [Nike Inc. (NYSE:NKE)](https://www.stock-analysis-on.net/NYSE/Company/Nike-Inc/Ratios/Long-term-Debt-and-Solvency)
34. [Pfizer Inc. (NYSE:PFE)](https://www.stock-analysis-on.net/NYSE/Company/Pfizer-Inc/Analysis/Debt)
35. [Pfizer Inc. (NYSE:PFE)](https://www.stock-analysis-on.net/NYSE/Company/Pfizer-Inc/Financial-Statement/Assets)
36. [Boeing Posts Q4 Profit on Asset Sale, Higher Deliveries](https://avweb.com/aviation-news/boeing-q4-profit-asset-sale-deliveries/)
37. [Press Release issued by The Boeing Company dated](https://www.sec.gov/Archives/edgar/data/12927/000162828026003518/a202512dec318kprex991.htm)
38. [Starbucks Corporation (via Public) / Annual Report for Fiscal Year Ending 09/28, 2025 (Form 10-K)](https://www.publicnow.com/view/E381D5799FA9CFF60DAC328DAEE17A2B52E7BC27)
39. [Boeing Reports Positive 2025 Results, Boosted by a Divestment - Journal Aviation](https://www.journal-aviation.com/en/aerospace-news/boeing-reports-positive-2025-results-boosted-by-a-divestment-20260127.html)
