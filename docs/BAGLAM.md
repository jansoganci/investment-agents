---
belge: Bağlam notları
tarih: 2026-10-03
durum: referans
yayinla: hayir
---

# BAĞLAM — kararların arkasındaki bilgi

`YOL_HARITASI_v2.md` **ne** yapacağımızı söyler; bu dosya **neden** öyle karar verdiğimizi.
Kaynak: 2–3 Ekim 2026 planlama sohbeti (eski proje içinde, Cursor).

## 1. Yatırımcı profili

- Eskiden sadece teknik analizle işlem yaptı; temeli zayıf hisselerde sert düşüşler yaşadı → artık **önce temel**.
- Tecrübe 3+ yıl. Sistemin rolü: **liste + gerekçe verir, karar ve işlem kullanıcıda.**
- %30 düşüşte: **bekler ama uykusu kaçar** → risk yönetimi ve sakin, az işlemli kurallar önemli.
- Odak: ABD + Çin hisseleri (HK + A-hisse İş Bankası üzerinden; komisyona razı, ~3–5 milyon TL'ye kadar premium kabul), sonra emtia. 5–10 hisse + ETF.
- Para akışı (aylık): hisse 25–50 bin TL · BES ~9 bin TL (maaştan kesilir) · altın ~5 g (~30 bin TL). Gider 50–75 bin TL. Acil fon: ~3 aylık gider var. Maaş şimdilik sabit.
- Yatırım kaynağı fikirleri: takip ettiği "abi"nin iki ücretli sitesi — **emtiadefteri.com** ve **dragonomi.com**. Bülten / RSS yok; içerik sadece sitede, giriş yapılarak okunuyor. Eskiden Grok Bot siteye girip yazıları tek tek okuyordu.

## 2. Hedef matematiği (bugünün parasıyla, "orta" senaryo)

Varsayım (enflasyon sonrası yıllık): hisse %7, altın %1,5, BES %3. Başlangıç 500 bin TL. Kur oranı kullanıcının: 30 milyon TL ≈ 800 bin $ (~37,5 TL/$).

| Aylık hisse | 10 yıl sonra toplam | %4 kuralıyla aylık gelir | Giderin (62,5 bin) ne kadarı |
|---|---|---|---|
| 25 bin TL | ~10,4 milyon TL | ~35 bin TL | %55 |
| 37,5 bin TL | ~12,5 milyon TL | ~42 bin TL | %67 |
| 50 bin TL | ~14,7 milyon TL | ~49 bin TL | %78 |

- Kötü (hisse %5) – iyi (hisse %10) aralığı: 9,5–16,6 milyon TL.
- Nominal TL hesapta 30 milyonu büyük ihtimalle geçer; alım gücü bugünün 10–17 milyonu kadar olur. **Hedef hep bugünün parasıyla düşünülür.**
- Hesaba katılmayanlar (hepsi lehte): mevcut BES ve altın birikimi, gelecekteki zamlar.
- Ana ders: hedefi taşıyan şey **aylık birikim**; sistemin işi parayı iyi şirketlere koymak ve büyük hatalardan korumak, mucize getiri değil.

## 3. Teknik analiz: Selçuk Gönençler 5-8-13 ve backtest sonuçları

### Kural (kullanıcının tarifi; kod: `ajanlar/teknik/backtest/gunluk_5_8_13.py`)

| Durum | Koşul (kapanış vs SMA5/8/13) | İşlem (hisse başı ayrılan para üzerinden) |
|---|---|---|
| TEYİTLİ AL | üçünün de üstünde | kalan parayla tamamla → %100 |
| TEMKİNLİ AL | önceki gün üçünün de altındaydı; bugün 5 ve 8 üstü, 13 altı | %40 al |
| TEMKİNLİ SAT | 5 altı; 8 ve 13 üstü | elindekinin %40'ını sat |
| RİSK / ÇIKIŞA HAZIRLAN | 5 ve 8 altı; 13 üstü | işlem yok |
| SAT | üçünün de altında | hepsini sat (elinde yoksa bir şey yapma) |
| Karışık | diğerleri | önceki durumu koru |

İşlem sadece durum **değiştiği gün** yapılır. Sinyal normal kapanıştan, getiri temettü dahil fiyattan; işlem başına %0,1 maliyet. Veri: Yahoo Finance (`yfinance`).

### Günlük sonuç (Ocak 2016 – Ekim 2026, 24 hisse eşit ağırlık)

| Yöntem | Yıllık getiri | En büyük düşüş |
|---|---|---|
| Al ve tut | %19,8 | -%28,6 |
| SPY | %14,9 | -%33,7 |
| %55 hisse + nakit, zamanlama yok | %10,9 | -%16,3 |
| **5-8-13 (%40 kuralı)** | **%4,9** | -%17,3 |

24 hissenin **24'ünde** kural al-tut'un gerisinde kaldı; hisse başı yılda ~57 işlem. Sebep: üç ortalama birbirine çok yakın → günlük gürültü sinyal üretiyor; düşüşten sonra satıp en iyi toparlanma günlerini kaçırıyor. "Az düşüş" zamanlama başarısı değil, piyasa dışında kalmanın sonucu.

### Haftalık sonuç (yıllık getiri / en büyük düşüş; kod: `haftalik.py`)

| Kural | 2006–2015 (2008 dahil) | 2016–2026 | Yılda işlem |
|---|---|---|---|
| Hisseleri al ve tut | %16,7 / -%42,3 | %19,9 / -%27,5 | – |
| SPY al ve tut | %7,4 / -%54,6 | %14,8 / -%31,8 | – |
| Haftalık 5-8-13 | %6,6 / -%23,8 | %8,6 / -%14,6 | 12 |
| MA8 + RSI>50, MA8 altında sat | %5,0 / -%16,3 | %7,4 / -%13,7 | 9 |
| Aynısı, sabırlı çıkış (MA8 altı **ve** RSI<50) | %9,2 / -%18,1 | %10,9 / -%17,8 | 4,6 |
| 40 haftalık ortalama üstündeyse tut | %10,0 / -%20,2 | %11,4 / -%16,9 | 3,9 |
| **SPY 40 haftalık üstündeyse hepsini tut** | **%10,5 / -%16,8** | **%14,3 / -%15,8** | 3,6 |

- Hiçbir kural getiride al-tut'u yenmedi; zamanlama = **sigorta** (daha az düşüş, daha az getiri).
- En ucuz sigorta: **piyasa filtresi** (SPY 40 haftalık). Bedeli: 2016–2026'da yıllık %19,9 → %14,3.
- Sınırlar: hisseler bugünden bakılarak seçildi (mutlak rakamlar iyimser, kıyas güvenilir); nakitte faiz ve vergi yok; çok kural denendikçe "geçmişe tesadüfen uyan" kural riski artar → kuralları değiştirmeden 3 ay sanal parayla izlemek önerildi.
- Önerilmiş ama çalıştırılmamış test: piyasa filtresi açıkken **girişi** haftalık 5-8-13 ile yapmak.

## 4. Eski sistemden dersler (karne tasarımında tekrarlanmasın)

Eski 3. adım 5 hissede (ROP, V, WM, APH, NET) test edildi; **hiçbiri GREEN almadı.** Sebepler şirketler değil, kurallardı:

1. **NET — yanlış hukuki alarm.** 10-K'daki "DOJ ve GSA *geçmişte* tedarikçilere dava açtı" genel risk cümlesi; "Department of Justice" kelimesi geçtiği için somut, açık bir dava sayıldı ("genel uyarı" filtresini ezdi). Yanlışlıkla "rekabet hukuku" etiketi aldı (aslında False Claims Act). Cümlede "pricing" geçtiği için "tezi etkiliyor" dendi. Anahtar kelime listesi önceki test şirketlerine göre ayarlanmıştı (Deere: farmer, dealer, right to repair; Visa: interchange, network rules).
   → **Ders:** Kelime eşleşmesiyle hukuki / anlamsal yargı yok. Yapay zekâ okursa, iddiasını rapordan **alıntıyla** desteklemeli; "genel risk uyarısı" ile "şirkete özel olay" ayrımı açıkça yapılmalı.
2. **WM — beraberlik zinciri.** Şirket türü sınıflandırmasında iki tür eşit puan aldı; listede önce gelen (A7, satın alarak büyüyen) seçildi → "REVIEW_REQUIRED" → otomatik "tez–sermaye gerilimi" bayrağı → ORANGE. Bulgu WM hakkında değil, sistemin kararsızlığıydı; bayrağın adı yanıltıcıydı. 4 aşama birden "insan baksın" dedi ama sinyal sessizce ORANGE'a eridi.
   → **Ders:** Sistem emin değilse bunu "**belirsiz**" diye açıkça söylesin; belirsizliği şirket hakkında olumsuz bulguya çevirmesin. Bayrak adları ne olduğunu söylesin.
3. **APH — aynı gerçek iki kez sayıldı, çıkış kapısı yok.** Kural: satın almalar dahil sermaye getirisi < hariç getirinin yarısı ise bayrak. APH: dahil %24,2 (mükemmel), hariç %57,6 → bayrak; aynı koşul ikinci bir bayrak daha yaktı. İnsan inceleme kuyruğu boştu → uyarıyı kaldırmanın yolu yoktu. Ters etki: şirketin kendi işi ne kadar iyiyse ceza ihtimali o kadar artıyor.
   → **Ders:** Oranın yanında **mutlak seviyeye** de bak; bir gerçek bir kez sayılsın; her uyarının bir "insan baktı, kapattı" yolu olsun.
4. **NET — convertible borç okunmuyordu.** Sadece ConvertibleDebt* etiketleriyle borç raporlayan şirketlerde borç ve şirket değeri boş kalıyordu. Düzeltildi (eski projede commit `c325d1d`): yedek olarak, sadece normal borç etiketi hiç yoksa. NET 2025: 1,974 + 1,291 = **3,265 milyar $**.
   Ek not: eski Stage 8 borç toplamı "uzun vadeli borcun cari kısmı"nı atlıyordu — yeni hesapta dahil edilmeli.

Genel ders: Eski 3. adımın **SEC veri çekme + kodla hesap** kısmı değerli (korunacak); kelime eşleşmesi ve 9 aşamalı kapı yapısı ağırdı (bırakıldı). Karne 5 dakikada okunabilen tek sayfa olmalı.

## 5. Platform ve abonelik kararlarının arkası

- MacBook Air 2022 = Apple **M2**, 16 GB RAM, 256 GB → Hermes destekli.
- Abonelikler: Cursor Pro (yıllık, Grok Bot dahil) · 2× OpenAI/Codex · 1× Claude.
- **Codex aboneliği** Hermes'te resmi olarak kullanılabilir (`hermes auth add openai-codex`), ek API ücreti yok. Risk: kota dolunca **habersiz 2–4 saat kilit** → işler parça parça kayıt almalı, gerekirse OpenRouter'a düşmeli; aboneliklerden biri sadece ajana ayrılmalı.
- **Claude aboneliği Hermes'e bağlanmaz:** Anthropic tüketici şartları Free/Pro/Max OAuth'u sadece Claude Code ve claude.ai'da izinli sayıyor; üçüncü taraf ajanda "ekstra kullanım" ücreti veya hesap riski. Claude, kişisel kullanım ve Claude Code ile kod yazmak için.
- Grok Bot: danışman / araştırma / kod yardımı olarak kalır; model seçimi yok, haftalık kota açık değil.
- Mac 7/24: şarja takılı, kapak açık, "ekran kapalıyken uykuyu engelle", optimize şarj; pil kısa elektrik kesintisinde UPS gibi çalışır.

## 6. Fikir kaynakları (eski proje — sadece fikir, kural değil)

- `../investment-intelligence/handoff_pack/01_INVESTMENT_PHILOSOPHY.md` — kullanıcının belgelenmiş yatırım felsefesi (sahip zihniyeti, evren / dikkat felsefesi, yanlış-pozitif örüntüleri, eksik kişisel felsefe listesi). **Karne formatı konuşulurken okunmalı.**
- `../investment-intelligence/handoff_pack/03_FA_STAGES_1_9.md` — eski 9 aşamanın hangi soruları sorduğu (karne metrikleri için soru havuzu).
- `../investment-intelligence/docs/AUDIT_REPORT.md` — eski sistemin teknik denetim raporu.

Bu dosyalardaki "LOCKED", "Plan §0", aşama kapıları gibi kurallar bu projeye **uygulanmaz**.
