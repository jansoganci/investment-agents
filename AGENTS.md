# AGENTS.md — investment-agents

Kişisel yatırım danışmanı sistemi: 4 ajan okur, araştırır, analiz eder, önerir.
**Kararı ve alım-satımı her zaman kullanıcı verir / yapar.**

## Her oturumun başında

1. `docs/YOL_HARITASI_v2.md` oku — amaç, kurallar, kararlar, adımlar, açık konular orada.
2. Bu dosyanın sonundaki **Şu anki durum** bölümünü oku.
   Profil, hedef hesabı, backtest sonuçları, eski sistemden dersler veya karne / puan / teknik kural konuşulurken `docs/BAGLAM.md` oku.
3. Kullanıcıya süreci yeniden anlattırma; eksik bilgi varsa tek, net bir soru sor.

## Değişmez kurallar

1. Ajanlar sadece **öneri** verir. Aracı kurum / banka şifresi sisteme asla girmez.
2. Yeşil liste ≠ AL. Puan = sıralama; her puanın yanında zorunlu bir "neden" cümlesi olur.
3. `karne.md` sadece sona eklenir; eski kayıt silinmez; her kayıt tarihlidir.
   Tek istisna: üst bilgi kartı güncel durumu gösterir (`durum`, `portfoyde`), sadece kod günceller; her değişiklik sona tarihli not olarak da eklenir.
4. Ajanlar birbirini tanımaz; sadece dosya / SQLite üzerinden haberleşir.
5. Yeni özellik ancak mevcut adım "bitti" sayıldıktan sonra eklenir.

## Çalışma şekli

- Dil: **Türkçe**, sade, yeni başlayan biri için anlaşılır. Gereksiz teknik jargon yok.
- Sadece istenen işi yap. Özellik ekleme / çıkarma, kapsam genişletme yok; emin değilsen sor.
- Karar kullanıcınındır: seçenek varsa önerini belirt, kararı ona bırak.
- Basitlik önce: bir şey karmaşık geliyorsa eklemeden önce sadeleştir.
- "Think fast, iterate faster": kuralın 1. sürümü yeterince iyiyse ilerle; mükemmeli bekleme, kur ve düzelt.
- Her ajan bağımsız modül; tekrar kullanılan kod `ortak/` altına.
- Kod Hermes'i bilmez; her ajan elle de çalışabilmeli (`python -m ajanlar.<ajan>`).
- Oturum sonunda **Şu anki durum** bölümünü güncelle.

## Proje haritası

```text
ajanlar/goz/        1. Göz — Emtia Defteri + Dragonomi okur, tek cümle yazar (günde 3 tur)
ajanlar/sayac/      1B. Sayaç — son 7 gün hisse / sektör / emtia sayımı (kod, yapay zekâ yok)
ajanlar/arastirma/  2. Araştırma — okuma + web araması + puan; kartı açar (haftalık, Pazar)
ajanlar/analiz/     3. Analiz — SEC / PDF → karne.md (çeyreklik / yıllık)
ajanlar/teknik/     4. Teknik — haftalık durum + piyasa filtresi; backtest/ burada
ortak/              yapay zekâ, SEC, fiyat, Drive yolları, SQLite
ayarlar.yaml        modeller, bütçe, saatler, hisse listesi
docs/               YOL_HARITASI_v2.md, BAGLAM.md, TASINANLAR.md
```

## Teknik

- Python, ortam yönetimi `uv`. Örnek: `uv run --with pytest pytest -q`
- Geliştirme ana Mac'te; çalıştırma yedek MacBook Air'de (Hermes). Köprü GitHub; Air'de kod yazılmaz.
- SQLite Mac diskinde durur, Drive klasörüne **konmaz** (senkron bozabilir); gece Drive'a yedeklenir.
- Rapor / karne: Markdown + üst bilgi kartı (`hisse`, `sektor`, `tarih`, `yayinla: hayir`; karnede ayrıca `durum`, `portfoyde`).
- Telegram'da kullanıcının tek muhatabı Hermes; Hermes sadece tanımlı komut listesini çalıştırır, kod / kural değiştirmez.
- Model ve bütçe ayarları tek yerde: `ayarlar.yaml`. Yapay zekâ bütçesi en fazla 25–30 $/ay.
- Sırlar (API anahtarları) `.env` içinde; asla commit edilmez.

## Eski proje

`../investment-intelligence` (git etiketi `v1-arsiv`) sadece kaynak kütüphanesidir.
Çalışma alanına ekleme; kurallarını / dokümanlarını bu projeye uygulama.
Bir dosya gerekiyorsa tam yolla oku, sadece gereken parçayı kopyala ve `docs/TASINANLAR.md`'ye satır ekle.

## Şu anki durum

- **Son güncelleme:** 2026-10-03
- **Yapıldı:** Proje açıldı; yol haritası + `BAGLAM.md` yazıldı; backtest betikleri taşındı.
  Karar sırası belirlendi (yol haritası 9. bölüm) ve 1. sıra **genel çerçeve** kapandı:
  karne = hisse kartı, "think fast, iterate faster", site sahibinden okuma izni alındı,
  geliştirme ana Mac / çalıştırma Air ayrımı.
  2. sıra **mimari** kapandı (yol haritası 3. bölüm): akış, hisse durumları (aday / takipte / arşivde,
  sınıf, portföyde), takibe alma manuel, sağlam → yeşil liste otomatik, 3. ajan olayla çalışır,
  Telegram'da tek muhatap Hermes + komut listesi, 3. ajan için deneme seti testi.
  3. sıra **1. ajan (Göz)** kapandı (yol haritası 3. bölüm, "1. ajan kuralları"): günde 3 tur, yavaş tarama
  (~20 dk / tur, engel cevabında dur), tam metin okunur + ucuz modelle tek tarafsız cümle, tam metin
  `haberler`'e kaydedilir, etiket eşleme tablosu (şirket / emtia / sektör), sözlük yazıları alınmaz.
  4. sıra **2. ajan** kapandı (yol haritası 3. bölüm): 1B Sayaç (kod, kayan 7 gün, kartı olan
  sıralamaya girmez), 2 seviyeli sabit sektör listesi (GICS 11 + onaylı alt sektör), 2. ajan haftada bir
  en çok 10 hisse, siteye gitmez, alıntılı okuma, emtia bağı (şirket → emtia, rol), kart 2. ajanda doğar,
  Drive düz yapı `Yatirim/Hisseler/<KOD> - <Şirket adı>/karne.md`, **puan kuralları** (5 kriter × 0–2,
  eşikli; veri yoksa belirsiz = 1 puan). **1. sürüm sadece ABD borsası (ADR dahil)**; HK / A sonra ek.
  5. sıra **3. ajan** kısmen kapandı (yol haritası 3. bölüm, "3. ajan kuralları"): kalite önce, Lynch türleri,
  kapsam dışı (şimdilik) banka / sigorta / gayrimenkul / gelirsiz şirket / kamu hizmetleri, değerleme = Lynch PEG + serbest nakit akışı verimi (gizli varlık / gerçek değer hesabı şimdilik yok), kod ölçer + soru işaretler + yapay zekâ alıntıyla nedenini yazar, 10 ölçü,
  SEC eş anlamlılar listesi (yıl yıl), `eksik_veri` kayıt defteri, borç ⚠ araştırma maddesi, UAT ≥ 20 hisse.
  Araştırma notları `docs/BAGLAM.md` 8. bölüm.
- **Sıradaki:** 3. ajanın kalanları — her ölçünün eşiği + türe göre sağlam / orta / zayıf / belirsiz kuralı,
  PEG ve nakit verimi eşikleri, karne formatı (`BAGLAM.md` 7. bölüm), eksik veri için
  Telegram'dan veri isteme. Yapay zekâ denetçi en son karar verilecek.
  Karne formatı taslağı `docs/BAGLAM.md` 7. bölümde (3. ajan sırasında kullanılacak).
- **Bekleyen sorular:** Yok.
- **Not:** Commit'ler GitHub'a henüz gönderilmedi; kullanıcı en sonda topluca göndermek istiyor.
