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

**Neden bu sistem:** Spekülatif al-sat değil, uzun vadeli yatırım. Ajanlar benim elle yaptığım işi
(hesap, veri kontrolü, haber takibi) kurallara göre yapar → haftalık harcadığım süre azalır.

**Çalışma ilkesi — "Think fast, iterate faster":** Basit tut. Kuralların 1. sürümü yeterince iyiyse
yaz, kur, çalıştır; hatayı gör, düzelt. Gereksiz uzun düşünüp hiçbir şey kurmamaktansa kurup düzeltmek.

## 2. Değişmez kurallar

1. Ajanlar sadece **öneri** verir. Aracı kurum / banka şifresi sisteme **asla** girmez.
2. Yeşil liste ≠ AL. Puan = **sıralama**; her puanın yanında zorunlu bir "neden" cümlesi olur.
3. Karne **sadece sona eklenir**, eski kayıt silinmez; her kayıt tarihlidir.
4. Ajanlar birbirini tanımaz; sadece dosya / veritabanı üzerinden haberleşir.
5. Önce basit olan: yeni özellik ancak mevcut adım "bitti" sayıldıktan sonra eklenir.

## 3. Dört ajan

| Ajan | Ne yapar | Sıklık | Çıktı | Ne yapmaz |
|---|---|---|---|---|
| **1. Göz** | Emtia Defteri + Dragonomi yeni yazılarını okur; hisse adı, olumlu/olumsuz tek cümle, sektör çıkarır | Günlük | `haberler` tablosu + `Gelen/` | Yorum yapmaz, puanlamaz |
| **2. Araştırma** | Adaylar için son 1 yıl web araması; gruplar, puanlar | Haftalık | `puanlar` tablosu + `Haftalik/` raporu | Temel analiz yapmaz |
| **3. Analiz** | Finansal tablolardan karne çıkarır (ABD: SEC; HK/A: yüklenen PDF) | Çeyreklik / yıllık | `finansallar` tablosu + `karne.md` | Fiyat tahmini, AL/SAT demez |
| **4. Teknik** | Yeşil listedekiler için haftalık durum + piyasa filtresi | Haftalık | `sinyaller` tablosu + Telegram özeti | İşlem yapmaz |

**Karne = hisse kartı.** Her hissenin tek bir karnesi olur; tüm bilgisi oradadır. Çeyrekler geçtikçe
sona yeni tarihli kayıt eklenerek büyür.

**Takipte / arşivde (taslak, mimaride kesinleşecek):** Takibi bırakılan hisseye her çeyrekte boşuna
analiz ve para harcanmaz. 3. ajan sadece **takipteki** hisseleri analiz eder; arşivdeki hissenin
karnesi silinmez, sadece yeni kayıt eklenmez. Arşive alma / geri alma kararı benimdir; ajan sadece
hatırlatır (örnek: "XYZ 2 çeyrektir yeşil listede değil, arşive alalım mı?").

## 4. Teknoloji kararları

| Konu | Karar |
|---|---|
| Dil | Python (tek dil) |
| Geliştirme | Ana Mac'te (Claude Code / Cursor); her ajan önce burada elle denenir. Köprü: GitHub |
| Çalıştıran | Hermes Agent, yedek MacBook Air M2 (16 GB) üzerinde, 7/24. Air'de kod yazılmaz: `git pull` ile güncellenir; `.env`, site oturumu ve gerçek SQLite orada durur. Hermes sadece zamanlar ve haber verir; hesap / analiz mantığı bizim kodumuzda |
| İletişim | Telegram (Hermes üzerinden) + Drive klasörleri |
| Yapay zekâ | Pahalı işler (karne yazımı): Codex aboneliği (1 abonelik ajana ayrılır). Ucuz işler + web arama: OpenRouter, harcama limitiyle. Claude aboneliği Hermes'e **bağlanmaz** (kullanım şartları) |
| Site okuma | Playwright; ben bir kez giriş yaparım, oturum saklanır; günde 1 kez, az sayfa. Okuma adımında yapay zekâ yok. **İzin:** iki sitenin sahibi okumaya (scraping) şahsen izin verdi (2026-10-03); API yok; şart: siteyi yormamak / suistimal etmemek |
| Model seçimi | Tek yer: `ayarlar.yaml` |
| Bağımsızlık | Kod Hermes'i bilmez; her ajan elle de çalışır (`python -m ajanlar.analiz`) |
| Blog ihtimali | Tüm rapor/karneler Markdown + üst bilgi kartı (`yayinla: evet/hayir`). Web arayüzü şimdilik yok |

## 5. Saklama

| Yer | Ne | Kim okur |
|---|---|---|
| **Drive** (`Yatirim/`) | PDF, `karne.md`, sektör/hisse raporları, haftalık özetler | Ben |
| **SQLite** (Mac diski, Drive'da **değil**) | Rakamlar, puanlar, fiyatlar, sinyaller, listeler, çalışma kayıtları | Makine |

SQLite her gece Drive'a **yedek kopya** olarak atılır.

Tablolar: `hisseler`, `haberler`, `puanlar`, `finansallar`, `fiyatlar`, `sinyaller`, `calismalar` (harcanan $ dahil).

```text
Yatirim/                                   (Drive)
├── Gelen/                                 1. ajanın günlük çıktısı
├── Haftalik/                              haftalık özetler
├── Yedek/                                 gece SQLite kopyası
└── Sektorler/<Sektör>/<HİSSE>/
    ├── karne.md
    └── raporlar/                          HK / A-hisse PDF'leri (elle yüklerim)

investment-agents/                         (kod, Git)
├── ajanlar/goz/  arastirma/  analiz/  teknik/
├── ortak/                                 yapay zekâ, SEC, fiyat, Drive yolları, veritabanı
├── ayarlar.yaml
└── docs/  YOL_HARITASI_v2.md  BAGLAM.md  TASINANLAR.md
```

## 6. Bütçe

- Yapay zekâ / API: **en fazla 25–30 $/ay** (beklenen: OpenRouter < 5 $ + mevcut Codex aboneliği)
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
| **1. Analiz + karne** | `ortak/` + SQLite + 3. ajan, 3–5 ABD hissesi | 3 hissenin karnesi Drive'da; ikinci çalıştırma eski kaydı silmeden yeni tarihli kayıt ekliyor |
| **2. Göz** | Playwright ile iki site | 1 hafta boyunca her gün `haberler` doluyor |
| **3. Araştırma** | Web araması + puan + neden | Haftalık rapor Drive'da ve Telegram'da |
| **4. Teknik** | Haftalık durum + piyasa filtresi | Pazar günü Telegram'a yeşil liste özeti geliyor |

## 9. Açık konular (kodlamadan önce birlikte karar verilecek)

**Karar sırası (2026-10-03):** önce tüm kararlar ve planlar, sonra kod.

1. ~~Genel çerçeve~~ ✅ (2026-10-03: karne = kart, çalışma ilkesi, site izni, geliştirme / çalıştırma ayrımı)
2. **Mimari** — hangi ajan neyi nereye yazar, sonraki ajan neyi okur; takipte / arşivde kuralı
3. **1. ajan (Göz)** — ne çıkaracak, sıklık
4. **2. ajan** — puan kuralları
5. **3. ajan** — metrikler, sağlam / orta / zayıf ölçütü, karne formatı
6. **4. ajan** — teknik kurallar
7. **Uygulama planı** — model / bütçe dağılımı, Air kurulumu, kodlama sırası

Konu notları:

- **2. ajan puan kuralları.** Taslak (her biri 0–2, toplam 10): bahsedilme, ton, sektör rüzgârı, son 1 yıl haber akışı, hızlı sağlık kontrolü (SEC'ten, kodla).
- **Karne formatı.** Hangi metrikler, hangi kontroller, "neden" bölümü nasıl yazılır. Temel analiz sonucu 3 sınıf: **sağlam / orta / zayıf**; sadece sağlam olanlar teknik analize (yeşil liste) gider.
- **4. ajan kuralları.** Backtest sonucu: günlük 5-8-13, 24 hissenin 24'ünde al-tut'un gerisinde kaldı. Mevcut öneri: yeşil liste + piyasa filtresi (SPY 40 haftalık ortalamanın üstünde); çıkış = hisse yeşil listeden düşerse.
- ~~**Site kullanım şartları.**~~ ✅ Site sahibi izin verdi (bkz. 4. bölüm, Site okuma).
- **HK / A-hisse verisi.** PDF'den hangi rakamlar elle / yapay zekâyla alınacak. Not: ABD için PDF / OCR gerekmez (SEC rakamları hazır tablo). HK / A PDF'lerinin çoğu metin içerir → ücretsiz Python kütüphanesiyle okunur; OCR sadece taranmış (resim) PDF'te, o da bilgisayarda ücretsiz.
