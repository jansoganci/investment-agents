---
belge: Yol Haritası v2
tarih: 2026-10-03
durum: taslak
yayinla: hayir
---

# Yol Haritası v2 — investment-agents

## 1. Amaç

10 yılda (43 yaşında) finansal özgürlük. Sistem bu yolda **danışman**dır:
okur, araştırır, analiz eder, önerir. **Kararı ve alım-satımı her zaman ben veririm / yaparım.**

- Başlangıç: 500 bin TL · Aylık: hisse 25–50 bin TL, BES ~9 bin TL, altın ~5 g
- Gider: 50–75 bin TL/ay · Acil durum fonu: 3 aylık gider
- Hedef: nominal ~30 milyon TL / 800 bin–1 milyon $ (bugünün parasıyla ~10–15 milyon TL)
- Piyasalar: ABD + Hong Kong + Çin A-hisseleri (İş Bankası üzerinden) · 5–10 hisse + ETF
- **1. sürüm sadece ABD borsası** (NYSE, NASDAQ; ADR'ler dahil). Hong Kong / Çin A-hisseleri sistem oturunca **ek** olarak gelir.

**Neden bu sistem:** Spekülatif al-sat değil, uzun vadeli yatırım. Ajanlar benim elle yaptığım işi
(hesap, veri kontrolü, haber takibi) kurallara göre yapar → haftalık harcadığım süre azalır.

**Çalışma ilkesi — "Think fast, iterate faster":** Basit tut. Kuralların 1. sürümü yeterince iyiyse
yaz, kur, çalıştır; hatayı gör, düzelt. Gereksiz uzun düşünüp hiçbir şey kurmamaktansa kurup düzeltmek.

## 2. Değişmez kurallar

1. Ajanlar sadece **öneri** verir. Aracı kurum / banka şifresi sisteme **asla** girmez.
2. Yeşil liste ≠ AL. Puan = **sıralama**; her puanın yanında zorunlu bir "neden" cümlesi olur.
3. Karne **sadece sona eklenir**, eski kayıt silinmez; her kayıt tarihlidir. Tek istisna: en üstteki **üst bilgi kartı** güncel durumu gösterir (`durum`, `portfoyde`) ve sadece kod tarafından güncellenir; her değişiklik ayrıca sona tarihli not olarak eklenir.
4. Ajanlar birbirini tanımaz; sadece dosya / veritabanı üzerinden haberleşir.
5. Önce basit olan: yeni özellik ancak mevcut adım "bitti" sayıldıktan sonra eklenir.

## 3. Dört ajan

| Ajan | Ne yapar | Sıklık | Çıktı | Ne yapmaz |
|---|---|---|---|---|
| **1. Göz** | Emtia Defteri + Dragonomi yeni yazılarını tamamen okur; ucuz modelle tek tarafsız cümle yazar; etiketleri hisse / emtia / sektöre çevirir | Günde 3 tur | `haberler` tablosu + `Gelen/` | Olumlu / olumsuz demez, yorum yapmaz, puanlamaz, saymaz |
| **1B. Sayaç** | Son 7 günde hangi hisse / sektör / emtia kaç yazıda geçti, sayar ve sıralar. Kod, yapay zekâ yok | 2. ajandan hemen önce + istendiğinde | sıralı liste | Puanlamaz, okumaz |
| **2. Araştırma** | Sayaç listesinin en üstündeki en çok 10 hisse: tam metni okur, web araması, puan + neden; **kartı açar** | Haftada bir (Pazar sabahı) | `puanlar` tablosu + kart (`karne.md`) + `Haftalik/` raporu | Temel analiz yapmaz, siteye gitmez |
| **3. Analiz** | **Takipteki** hisseler için finansal tablolardan karne çıkarır (ABD: SEC; HK/A: yüklenen PDF) + sınıf verir | Yeni bilanço gelince (aşağıya bkz.) | `finansallar` tablosu + `karne.md` + sınıf | Fiyat tahmini, AL/SAT demez |
| **4. Teknik** | Yeşil listedekiler için haftalık durum + piyasa filtresi | Haftalık | `sinyaller` tablosu + Telegram özeti | İşlem yapmaz |

**Karne = hisse kartı.** Her hissenin tek bir karnesi olur; tüm bilgisi oradadır. Kart **2. ajanda doğar**
(ilk kayıt: araştırma — puan, neden, haber özetleri); takibe alınınca 3. ajan temel analiz kayıtlarını aynı
dosyanın sonuna ekler. Çeyrekler geçtikçe sona yeni tarihli kayıt eklenerek büyür.

### Akış (mimari, karar: 2026-10-03)

```text
 1. GÖZ (günde 3 tur)     1B. SAYAÇ          2. ARAŞTIRMA (Pazar sabahı)
 İki siteyi okur   ──→   Son 7 gün   ──→    En çok 10 hisse: okur,
 haberler tablosu        sayar, sıralar     web araması, puan + neden
                                            puanlar tablosu + KART açılır (aday)
                                          │
                                          ▼
                              ┌─ BEN: "XYZ'yi takibe al" ─┐
                              ▼                           │
 3. ANALİZ (yeni bilanço gelince)                         │
 Sadece TAKİPTEKİ hisseler                                │
 finansallar tablosu + karne.md + sınıf                   │
 (sağlam / orta / zayıf / belirsiz)                       │
                                          │               │
                         sınıf = sağlam → YEŞİL LİSTE     │
                                          ▼               │
 4. TEKNİK (haftalık)                                     │
 Yeşil liste + piyasa filtresi                            │
 sinyaller tablosu → Pazar günü Telegram özeti ───────────┘
                                          │
                                          ▼
                              BEN: al / sat / bekle (aracı kurumda)
```

Süreç %100 otomatik değildir; ajan gereksiz yere çalışmaz.

### Hisse durumları

Her hisse `hisseler` tablosunda tek satırdır:

| Alan | Değerler | Kim değiştirir |
|---|---|---|
| `durum` | **aday** (2. ajan puanladı, kartı açıldı) · **takipte** (3. ajan karnesini tutar) · **arşivde** (karne durur, yeni analiz yok) | aday: 2. ajan · takipte / arşivde: **sadece ben** |
| `sinif` | sağlam · orta · zayıf · belirsiz (son karneden) | 3. ajan |
| `portfoyde` | evet / hayır | **sadece ben** (sistem aracı kuruma bağlanmaz, bilemez) |
| `borsa` | hissenin alınıp satıldığı yer: NYSE, NASDAQ (ileride HKEX, SSE, SZSE) | eşleme (1. ajan) |
| `ulke` | şirketin merkezi (örn. Alibaba: borsa NYSE, ülke Çin → ADR) | eşleme (1. ajan) |

- **Yeşil liste** ayrı bir durum değil: `durum = takipte` ve `sinif = sağlam` olan hisseler. Sağlam çıkan hisse **otomatik** girer, Telegram'dan haber gelir.
- `durum` ve `portfoyde` asıl olarak veritabanında tutulur; kod aynı anda karnenin üst bilgi kartını günceller ve karnenin sonuna tarihli not ekler (örn. `2026-10-10 · Portföye eklendi`).
- **Arşiv hatırlatması:** takipte + portföyde değil + son 2 karnede sağlam değil → Pazar özetinde "arşive alalım mı?". Karar benim.

### 1. ajan (Göz) kuralları (karar: 2026-10-03)

Siteler: Ghost altyapılı; günde toplam ~100–150 yazı (Emtia Defteri ~30–90, Dragonomi ~50–90), giderek artıyor.
RSS yok; **site haritası** (`/sitemap-posts.xml`) her yazının adresini ve saatini giriş gerektirmeden verir.
Başlık, tarih, etiketler herkese açık; yazının devamı üyelik girişi ister.

1. **Günde 3 tur:** 07:00, 13:00, 20:00 (`ayarlar.yaml`'dan değişir).
2. **Yeni yazıyı bulma:** site haritasından, önceki turdan beri çıkanlar (tek istek).
3. **Okuma:** benim üyelik oturumumla (Playwright, Air'de bir kez giriş) her yazının **tamamı** okunur.
4. **Siteyi yormama / engellenmeme:** sayfalar arası ~20–30 sn, her seferinde biraz farklı → tur ~20 dk, günde ~1 saat.
   Turda en fazla ~80 sayfa; kalanlar sonraki tura. Site "çok istek" / "erişim yok" derse tur **hemen durur**,
   ısrar etmez, Telegram'a hata gelir.
5. **Tek cümle:** ucuz model yazının tamamını okur, **tek, tarafsız** cümle yazar: sadece haberin söylediği;
   yorum, tavsiye, olumlu / olumsuz yok. Örnek: "Rio Tinto'nun X madeninde kaza oldu; haberde bunun bakır arzını
   daraltabileceği belirtiliyor." Amaç: hızlı bakışta ön bilgi.
6. **Kayıt:** sayfadan sadece yazının düz metni alınır (resim / menü yok). Adres, site, başlık, tarih, etiketler,
   tek cümle, **tam metin** (uzunluk sınırı yok — derin okumalar 15.000+ karakter), "detaylı okundu" ve "metin eksik"
   işaretleri → SQLite `haberler` (Air diski; ~1–2 MB / gün). Drive'a (`Gelen/`) sadece günlük liste gider: başlık,
   tek cümle, adres. Her yazı siteden **bir kez** indirilir; 2. ajan tam metni buradan okur, siteye tekrar gitmez.
7. **Etiket eşleme:** tüm etiketler tek eşleme tablosundan geçer → şirket (hisse kodu + borsa, örn. `union-pacific` → UNP,
   `rio-tinto` → RIO), **emtia** (petrol, lityum, kakao, buğday…) veya sektör; her satırda **sektör** de yazar
   (aşağıda "Sektör listesi"). Yeni etiketi ucuz model bir kez sınıflar, kaydedilir; yanlışsa ben düzeltirim.
8. **Alınmayanlar:** sadece sözlük yazıları ("Emtia Sözlüğü", "Yatırım Sözlüğü"). Gerisi alınır; işe yarayıp
   yaramadığına 2. ajan karar verir.
9. **Maliyet:** ~150 yazı / gün, ucuz model → kabaca 1–5 $ / ay (kesin hesap uygulama planında).

### Sektör listesi (karar: 2026-10-03)

İki seviye; yapay zekâ ikisini de **sadece listeden** seçer (serbest yazarsa "Enerji" / "Fosil Enerji" / "Petrol ve Gaz"
ayrı sayılır, sayım bölünür).

| Seviye | Liste | Değişir mi |
|---|---|---|
| **Ana sektör** | Dünyada en çok kullanılan GICS sınıflandırmasının 11 sektörü: Enerji · Malzeme · Sanayi · Zorunlu olmayan tüketim · Zorunlu tüketim · Sağlık · Finans · Bilgi teknolojisi · İletişim hizmetleri · Kamu hizmetleri · Gayrimenkul | Hiç |
| **Alt sektör / tema** | Birlikte yazacağımız liste (örn. Havacılık, Yarı iletken, Yapay zekâ, Lityum) | Sadece **benim onayımla** |

Hiçbiri uymazsa model "diğer" yazar; Pazar özetinde "Yeni alt sektör eklensin mi?" diye sorulur.

### 1B. Sayaç kuralları (karar: 2026-10-03)

1. Kod sayar, yapay zekâ yok, maliyet sıfır. 2. ajandan hemen önce çalışır; Hermes'e "bu hafta en çok ne geçti?" diye de sorulabilir.
2. **Kayan pencere:** her çalışmada o günden geriye son 7 gün; sayım birikmez, her seferinde sıfırdan. 30 günlük sayı bilgi olarak yanında.
3. Bir hisse aynı yazıda kaç kez geçerse geçsin **1** sayılır (farklı yazı sayısı). Sektörler ve emtialar da ayrıca sayılır.
4. **Puanlama sırasına sadece ABD borsasındaki hisseler girer** (ADR dahil). ABD dışı hisseler de sayılır ama Pazar
   özetinde sadece bilgi satırı olarak görünür: "ABD dışı çok geçenler" (Çin eki gelince veri hazır olur).
5. **Kartı olan hisse sıralamaya girmez** (tekrar puanlanmaz). Ama Pazar özetinde bir satır: "Kartı olup bu hafta çok
   geçenler: XYZ (12 yazı)" — tekrar puanlanıp puanlanmayacağına ben karar veririm.

### 2. ajan (Araştırma) kuralları (karar: 2026-10-03)

1. **Haftada bir** (Pazar sabahı), Sayaç listesinin en üstünden **en çok 10 hisse**. Gerekçe: uzun vadeli yatırım;
   kontrol bende kalsın. Bütçe / kota sıkışırsa sayı düşer.
2. **Siteye gitmez;** tam metni `haberler`'den okur. Tek istisna: "metin eksik" işaretli yazıyı siteden bir kez tekrar çeker.
3. **"Gerçekten okumak":** güçlü model + belirli sorulara göre okuma (şirket hakkında ne söyleniyor, hangi rakamlar var,
   olay mı genel yorum mu) + her iddiada **yazıdan alıntı**. Okunan yazıya "detaylı okundu" işareti; tekrar okunmaz.
4. **Emtia → hisse bağlantısı, şirketten emtiaya:** bir hisse ilk kez araştırılırken bir kez web araması: "Bu şirket hangi
   emtialara bağlı?" → `emtia_bagi` tablosu (şirket, emtia, **rol**: üretici / kullanıcı, kaynak). Rol önemli: kakao
   pahalanınca üreticiye iyi, çikolata üreticisine (kullanıcı) kötü. Sadece ilgilendiğimiz hisseler için tutulur.
   Kullanım: bir emtianın haberleri artınca bağlı hisselerin "sektör rüzgârı" puanına yansır; portföyümdeki hisseyi
   etkileyen emtia haberi Pazar özetinde görünür.
5. **Kart burada doğar:** Drive'da `Yatirim/Hisseler/<KOD> - <Şirket adı>/karne.md` açılır; ilk kayıt araştırma
   kaydıdır (puan, neden, haber özetleri). Hisse **aday** olur.
6. **Puan:** aşağıda.

### Puan kuralları (karar: 2026-10-03)

5 kriter × 0–2 = **10 puan**. Puan = **sıralama**, AL değil; her kriterin yanında zorunlu "neden" cümlesi.
İlke: **hesabı kod yapar**; yapay zekâ sadece etiket koyar (alıntıyla), puanı etiketlerden kod hesaplar.
Eşikler başlangıç değeri; ilk haftalarda sonuçlara bakıp ayarlanır.

| Kriter | Kim / veri | 0 puan | 1 puan | 2 puan |
|---|---|---|---|---|
| **1. Bahsedilme** | Kod · Sayaç (son 7 gün, farklı yazı) | 1–2 yazı | 3–5 yazı | 6+ yazı |
| **2. Ton** | Pahalı model her yazıya olumlu / olumsuz / nötr + alıntı; kod: net = olumlu − olumsuz | net ≤ −2 | net −1…+1 ("karışık") | net ≥ +2 |
| **3. Sektör rüzgârı** | Kod · Yahoo fiyatları (ücretsiz, yapay zekâ / web araması yok) | — | aşağıdaki 2 maddeden biri | ikisi de |
| **4. Son 1 yıl haber akışı** | Pahalı model + web araması; her olay kaynaklı, "şirkete özel / genel risk cümlesi" ayrımı | en az bir **ciddi olumsuz** olay | ciddi olumsuz yok | ciddi olumsuz yok **ve** en az bir önemli olumlu (büyük sözleşme, yeni ürün, beklenti yükseltme…) |
| **5. Hızlı sağlık** | Kod · SEC (ücretsiz) | 0–2 kontrol geçti | 3–4 geçti | 5'i de geçti |

**3. Sektör rüzgârı — 2 madde (her biri +1):**
- Hissenin **sektör fonu** (11 ana sektörün ABD fonu, örn. XLE enerji, XLK teknoloji) bugün **40 haftalık ortalamasının üstünde** (son ~9 ayda genel yükseliş = rüzgâr arkadan).
- **Bağlı emtia, şirketin rolüne göre lehte:** üreticiyse emtia fiyatı 40 haftalık ortalamanın üstünde; kullanıcıysa altında
  (petrol yükselişi üreticiye iyi, havayoluna kötü). Bağlı emtia yoksa / fiyat verisi yoksa: sektör fonu son 13 haftada S&P 500'den iyi.

**4. Ciddi olumsuz olay listesi (sabit):** muhasebe / denetçi sorunu · iflas riski / borç yapılandırması · şirkete özel
resmî soruşturma · kâr uyarısı + beklenti düşürme · CEO / CFO'nun ani ayrılışı.

**5. Hızlı sağlık — amaç:** "Temel analize para harcamaya değer mi?" ön elemesi; derin analiz 3. ajanda. Eşikler **bilerek
gevşek** (eski sistem fazla sıkıydı, hiçbir hisse yeşile girmedi). SEC'ten 7 rakam: gelir, faaliyet kârı, işletme nakit akışı,
yatırım harcaması, nakit, borç (cari kısım + convertible dahil), hisse sayısı.

| Kontrol | Geçer, eğer… |
|---|---|
| Kâr | son yıl faaliyet kârı > 0 |
| Nakit | serbest nakit akışı (işletme nakdi − yatırım harcaması) son 3 yılın en az 2'sinde > 0 |
| Küçülme | gelir 3 yılda yıllık ortalama > %0 büyümüş |
| Borç | net borç / serbest nakit akışı < 4 yıl, ya da borçtan fazla nakit |
| Sulanma | hisse sayısı 3 yılda %10'dan fazla **artmamış** (yeni hisse basılınca ortağın payı küçülür) |

**Veri yoksa — "belirsiz":** hesaplanamayan kontrol kaldı sayılmaz, hesaba katılmaz ("veri eksik ≠ kötü"). 3'ten az kontrol
hesaplanabildiyse sonuç **belirsiz → nötr 1 puan** ("ne ödül ne ceza"); kartta ve Pazar özetinde açıkça yazar
(örn. "Sağlık: belirsiz — serbest nakit akışı bulunamadı"). Aday aşamasında benden veri istenmez.

**SEC verisi:** ücretsiz, anahtar yok (istekte e-posta), saniyede 10 istek sınırı. ABD şirketleri 10-K (yıllık) + 10-Q
(çeyreklik); ADR'ler çoğunlukla sadece 20-F (yıllık) → ADR kartı yılda bir güncellenir. Şirketler aynı rakamı farklı isimle
raporlayabilir (ADR'lerde IFRS isimleri): kodda her rakam için olası isimler listesi; ilk bulunan kullanılır, yeni isim
görülünce listeye eklenir. ABD tarafı eski projede hazır (taşınacak).

### Para harcamayı önleyen kurallar

1. 3. ajan takvimle değil **olayla** çalışır: haftada bir SEC'e "yeni 10-Q / 10-K var mı?" diye sorar (ücretsiz); yoksa hiçbir şey yapmaz. HK / A: `raporlar/` klasörüne yeni PDF koyduğumda.
2. Arşivdeki hisse hiç analiz edilmez.
3. Her ajan her çalışmada `calismalar` tablosuna satır yazar (başlangıç, bitiş, tamam / hata, harcanan $).

### Telegram ve Hermes (tek muhatap)

Telegram'da tek muhatabım **Hermes**; 4 ajanla ayrı ayrı konuşmam. Hermes ajanları çalıştırır, sonuçları okur.

- **Mesaj ne zaman gelir:** Pazar günü tek özet (yeni adaylar, karnede değişenler, kartı olup bu hafta çok geçenler, ABD dışı çok geçenler, "belirsiz" kalan veriler, yeni alt sektör önerileri, teknik durum) · **hemen:** portföyümdeki hissenin sınıfı düşerse · **hemen:** bir ajan hata verirse · sağlam çıkıp yeşil listeye giren hisse. 1. ajanın günlük çıktısı Telegram'a gelmez, sadece `Gelen/`.
- **Yapabildikleri:** soru cevaplamak (veritabanı + karneleri okur: "XYZ'nin karnesi ne diyor?", "bu ay ne harcadık?") ve **tanımlı komut listesinden** komut çalıştırmak ("XYZ'yi takibe al", "ABC'yi portföye ekledim", "XYZ'yi şimdi analiz et", "XYZ'deki U1 uyarısını kapat, çünkü …"). Komut listesi uygulama planında yazılır.
- **Yapmadıkları:** veritabanı / dosyaları serbestçe değiştirmez (sadece komut listesi) · kod veya kural değiştirmez (o iş geliştirme Mac'inde) · işlem yapmaz.
- Hermes'le sohbet Codex aboneliğini kullanır: ek ücret yok, ama çok konuşma kotayı doldurabilir.
- 0. adımda (kurulum) Hermes'in bu şekilde çalıştığı denenerek doğrulanır.

## 4. Teknoloji kararları

| Konu | Karar |
|---|---|
| Dil | Python (tek dil) |
| Geliştirme | Ana Mac'te (Claude Code / Cursor); her ajan önce burada elle denenir. Köprü: GitHub |
| Çalıştıran | Hermes Agent, yedek MacBook Air M2 (16 GB) üzerinde, 7/24. Air'de kod yazılmaz: `git pull` ile güncellenir; `.env`, site oturumu ve gerçek SQLite orada durur. Hermes sadece zamanlar ve haber verir; hesap / analiz mantığı bizim kodumuzda |
| İletişim | Telegram'da tek muhatap Hermes (3. bölüm, "Telegram ve Hermes") + Drive klasörleri |
| Yapay zekâ | Pahalı işler (karne yazımı): Codex aboneliği (1 abonelik ajana ayrılır). Ucuz işler + web arama: OpenRouter, harcama limitiyle. Claude aboneliği Hermes'e **bağlanmaz** (kullanım şartları) |
| Site okuma | Playwright; ben bir kez giriş yaparım, oturum saklanır; günde 3 tur, yavaş (3. bölüm, "1. ajan kuralları"). Sayfa indirme adımında yapay zekâ yok; sadece okunan yazıya tek cümle için ucuz model. **İzin:** iki sitenin sahibi okumaya (scraping) şahsen izin verdi (2026-10-03); API yok; şart: siteyi yormamak / suistimal etmemek |
| Model seçimi | Tek yer: `ayarlar.yaml` |
| Bağımsızlık | Kod Hermes'i bilmez; her ajan elle de çalışır (`python -m ajanlar.analiz`) |
| Blog ihtimali | Tüm rapor/karneler Markdown + üst bilgi kartı (`yayinla: evet/hayir`). Web arayüzü şimdilik yok |

## 5. Saklama

| Yer | Ne | Kim okur |
|---|---|---|
| **Drive** (`Yatirim/`) | PDF, `karne.md`, sektör/hisse raporları, haftalık özetler | Ben |
| **SQLite** (Mac diski, Drive'da **değil**) | Rakamlar, puanlar, fiyatlar, sinyaller, listeler, çalışma kayıtları | Makine |

SQLite her gece Drive'a **yedek kopya** olarak atılır.

Tablolar: `hisseler`, `haberler` (tam metin dahil), `etiketler` (eşleme: tür, karşılık, borsa, ülke, ana sektör, alt sektör), `emtia_bagi`, `puanlar`, `finansallar`, `fiyatlar`, `sinyaller`, `calismalar` (harcanan $ dahil).

```text
Yatirim/                                   (Drive)
├── Gelen/                                 1. ajanın günlük listesi (başlık + tek cümle + adres)
├── Haftalik/                              haftalık özetler
├── Yedek/                                 gece SQLite kopyası
└── Hisseler/<KOD> - <Şirket adı>/         düz yapı; sektör kartın üst bilgisinde
    ├── karne.md                           2. ajanda doğar
    └── raporlar/                          HK / A-hisse PDF'leri (elle yüklerim)

investment-agents/                         (kod, Git)
├── ajanlar/goz/  sayac/  arastirma/  analiz/  teknik/
├── ortak/                                 yapay zekâ, SEC, fiyat, Drive yolları, veritabanı
├── ayarlar.yaml
└── docs/  YOL_HARITASI_v2.md  BAGLAM.md  TASINANLAR.md
```

## 6. Bütçe

- Yapay zekâ / API: **en fazla 25–30 $/ay** (beklenen: OpenRouter < 5 $ — bunun 1–5 $'ı 1. ajanın tek cümleleri — + mevcut Codex aboneliği)
- Emtia Defteri + Dragonomi abonelikleri bu bütçenin **dışında**
- OpenRouter'da sabit aylık limit; `calismalar` tablosu ile Telegram'dan "bu ay ne harcadık?"

## 7. Eski projeden (investment-intelligence, `v1-arsiv`) taşınacaklar

Toplu kopya yok; ihtiyaç anında, `TASINANLAR.md`'ye not düşerek:

- SEC istemcisi + companyfacts eşleme (convertible borç düzeltmesi dahil)
- Fiyat çekme (Yahoo / Stooq)
- Emtia Defteri veri formatı
- Backtest betikleri (5-8-13 günlük / haftalık)

Taşınmayacak: 9 aşamalı kapı sistemi, final FA renk mantığı, handoff dokümanları.

## 8. Adımlar

| Adım | İş | Bitti sayılır, eğer… |
|---|---|---|
| **0. Kurulum** | Mac ayarları (uyku kapalı, ayrı kullanıcı, FileVault), Hermes, Codex girişi, OpenRouter limiti, Drive masaüstü, Telegram botu | Telegram'dan mesajlaşabiliyorum ve zamanlanmış bir deneme işi Drive'a dosya yazıyor |
| **1. Analiz + karne** | `ortak/` + SQLite + 3. ajan, 3–5 ABD hissesi | 3 hissenin karnesi Drive'da; ikinci çalıştırma eski kaydı silmeden yeni tarihli kayıt ekliyor; **deneme seti testi geçiyor:** herkesin kaliteli kabul ettiği 3–5 şirket sağlam, zayıf olduğu bilinen 1–2 şirket sağlam **değil** çıkıyor (eski sistemde hiçbir hisse yeşile girememişti; kaliteliler sağlam çıkmıyorsa kurallar fazla sıkı, zayıflar sağlam çıkıyorsa fazla gevşek) |
| **2. Göz** | Playwright ile iki site, günde 3 tur | 1 hafta boyunca her tur `haberler` doluyor (tek cümle + tam metin + eşlenmiş etiketler) ve site bir kez bile "çok istek" / engel cevabı vermiyor |
| **3. Araştırma** | 1B Sayaç + 2. ajan: okuma + web araması + puan + neden + kart açma | Haftalık rapor Drive'da ve Telegram'da; aday hisselerin kartı Drive'da açılıyor |
| **4. Teknik** | Haftalık durum + piyasa filtresi | Pazar günü Telegram'a yeşil liste özeti geliyor |

## 9. Açık konular (kodlamadan önce birlikte karar verilecek)

**Karar sırası (2026-10-03):** önce tüm kararlar ve planlar, sonra kod.

1. ~~Genel çerçeve~~ ✅ (2026-10-03: karne = kart, çalışma ilkesi, site izni, geliştirme / çalıştırma ayrımı)
2. ~~Mimari~~ ✅ (2026-10-03: 3. bölüm — akış, hisse durumları, portföyde, olayla çalışma, Telegram / Hermes)
3. ~~1. ajan (Göz)~~ ✅ (2026-10-03: 3. bölüm, "1. ajan kuralları")
4. ~~2. ajan~~ ✅ (2026-10-03: Sayaç, sektör listesi, okuma, emtia bağı, kartın doğuşu, puan kuralları — 3. bölüm)
5. **3. ajan** — metrikler, sağlam / orta / zayıf ölçütü, karne formatı
6. **4. ajan** — teknik kurallar
7. **Uygulama planı** — model / bütçe dağılımı, Air kurulumu, kodlama sırası

Konu notları:

- ~~**2. ajan puan kuralları.**~~ ✅ 3. bölüm, "Puan kuralları".
- **Karne formatı.** Hangi metrikler, hangi kontroller, "neden" bölümü nasıl yazılır. Temel analiz sonucu 3 sınıf: **sağlam / orta / zayıf**; sadece sağlam olanlar teknik analize (yeşil liste) gider. **3. ajanda konuşulacak:** eksik veri olursa Hermes'in Telegram'dan benden veri istemesi (ben bulup veririm, ajan hesaba devam eder) — kontrol bende, iş ajanda.
- **4. ajan kuralları.** Backtest sonucu: günlük 5-8-13, 24 hissenin 24'ünde al-tut'un gerisinde kaldı. Mevcut öneri: yeşil liste + piyasa filtresi (SPY 40 haftalık ortalamanın üstünde); çıkış = hisse yeşil listeden düşerse.
- ~~**Site kullanım şartları.**~~ ✅ Site sahibi izin verdi (bkz. 4. bölüm, Site okuma).
- **HK / A-hisse verisi** (⏸ ertelendi — 1. sürüm sadece ABD). PDF'den hangi rakamlar elle / yapay zekâyla alınacak. Not: ABD için PDF / OCR gerekmez (SEC rakamları hazır tablo). HK / A PDF'lerinin çoğu metin içerir → ücretsiz Python kütüphanesiyle okunur; OCR sadece taranmış (resim) PDF'te, o da bilgisayarda ücretsiz.
