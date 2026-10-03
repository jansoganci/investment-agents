# AGENTS.md — investment-agents

Kişisel yatırım danışmanı sistemi: 4 ajan okur, araştırır, analiz eder, önerir.
**Kararı ve alım-satımı her zaman kullanıcı verir / yapar.**

## Her oturumun başında

1. `docs/YOL_HARITASI_v2.md` oku — amaç, kurallar, kararlar, adımlar, açık konular orada.
2. Bu dosyanın sonundaki **Şu anki durum** bölümünü oku.
3. Kullanıcıya süreci yeniden anlattırma; eksik bilgi varsa tek, net bir soru sor.

## Değişmez kurallar

1. Ajanlar sadece **öneri** verir. Aracı kurum / banka şifresi sisteme asla girmez.
2. Yeşil liste ≠ AL. Puan = sıralama; her puanın yanında zorunlu bir "neden" cümlesi olur.
3. `karne.md` sadece sona eklenir; eski kayıt silinmez; her kayıt tarihlidir.
4. Ajanlar birbirini tanımaz; sadece dosya / SQLite üzerinden haberleşir.
5. Yeni özellik ancak mevcut adım "bitti" sayıldıktan sonra eklenir.

## Çalışma şekli

- Dil: **Türkçe**, sade, yeni başlayan biri için anlaşılır. Gereksiz teknik jargon yok.
- Sadece istenen işi yap. Özellik ekleme / çıkarma, kapsam genişletme yok; emin değilsen sor.
- Karar kullanıcınındır: seçenek varsa önerini belirt, kararı ona bırak.
- Basitlik önce: bir şey karmaşık geliyorsa eklemeden önce sadeleştir.
- Her ajan bağımsız modül; tekrar kullanılan kod `ortak/` altına.
- Kod Hermes'i bilmez; her ajan elle de çalışabilmeli (`python -m ajanlar.<ajan>`).
- Oturum sonunda **Şu anki durum** bölümünü güncelle.

## Proje haritası

```text
ajanlar/goz/        1. Göz — Emtia Defteri + Dragonomi okur (günlük)
ajanlar/arastirma/  2. Araştırma — web araması + puan (haftalık)
ajanlar/analiz/     3. Analiz — SEC / PDF → karne.md (çeyreklik / yıllık)
ajanlar/teknik/     4. Teknik — haftalık durum + piyasa filtresi; backtest/ burada
ortak/              yapay zekâ, SEC, fiyat, Drive yolları, SQLite
ayarlar.yaml        modeller, bütçe, saatler, hisse listesi
docs/               YOL_HARITASI_v2.md, TASINANLAR.md
```

## Teknik

- Python, ortam yönetimi `uv`. Örnek: `uv run --with pytest pytest -q`
- SQLite Mac diskinde durur, Drive klasörüne **konmaz** (senkron bozabilir); gece Drive'a yedeklenir.
- Rapor / karne: Markdown + üst bilgi kartı (`hisse`, `sektor`, `tarih`, `yayinla: hayir`).
- Model ve bütçe ayarları tek yerde: `ayarlar.yaml`. Yapay zekâ bütçesi en fazla 25–30 $/ay.
- Sırlar (API anahtarları) `.env` içinde; asla commit edilmez.

## Eski proje

`../investment-intelligence` (git etiketi `v1-arsiv`) sadece kaynak kütüphanesidir.
Çalışma alanına ekleme; kurallarını / dokümanlarını bu projeye uygulama.
Bir dosya gerekiyorsa tam yolla oku, sadece gereken parçayı kopyala ve `docs/TASINANLAR.md`'ye satır ekle.

## Şu anki durum

- **Son güncelleme:** 2026-10-03
- **Yapıldı:** Proje açıldı; yol haritası yazıldı; backtest betikleri `ajanlar/teknik/backtest/` altına taşındı.
- **Sıradaki:** Kullanıcı yol haritasını okuyor. Sonra ya 9. bölümdeki açık konular (puan kuralları, karne formatı, 4. ajan kuralları) ya da 0. adım (Mac kurulumu).
- **Bekleyen sorular:** Emtia Defteri / Dragonomi kullanım şartları otomatik okumaya izin veriyor mu?
