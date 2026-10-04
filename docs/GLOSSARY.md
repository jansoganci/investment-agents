---
belge: Sözlük (kilit)
tarih: 2026-10-03
durum: kilit
yayinla: hayir
---

# Sözlük — kilitli adlar

Dokümanlar İngilizceye dönerken **sağ sütun tek addır**. Aynı şeye ikinci bir İngilizce kelime yazılmaz.
Sol sütun eski Türkçe addır. `YOL_HARITASI_v2.md`, `TASINANLAR.md`, `BAGLAM.md`, `DIS_INCELEME_PROMPT.md` ve `AGENTS.md` sağ sütunu kullanır. `docs/reviews/review_prompt_v1_EN.md` modellere verilen ilk İngilizce metindir; gövdesi değiştirilmez. Dış inceleme cevapları `docs/reviews/` altında; aslı değiştirilmez, çeviri ayrı dosyaya.

Bu dosya sadece kilit. Klasörler, deneme kodu ve diğer dokümanlar bu adımda değişmedi.
Yeni kod sağ sütunu kullanır. Deneme kodu (`ajanlar/analiz/prototip/`, `ajanlar/teknik/backtest/`) bugünkü Türkçe dizgileri taşır; o dizgiler ayrı bir kod işinde değişir.

Bölüm numarası kalır. Dosyalar birbirine "3. bölüm" diye bağlanır, başlık cümlesiyle değil.

**Karar (2026-10-04): sistemin bütün çıktıları ve komutları İngilizce** (karne, rapor, Pazar özeti, Telegram). Dokümanlardaki Türkçe tırnaklı örnekler son tablodaki İngilizce karşılıklarıyla okunur.

Çevrilmeyen özel adlar: Emtia Defteri, Dragonomi, Hermes, Telegram, İş Bankası, BES, Selçuk Gönençler, SEC etiket adları (`Revenues` gibi).

## Hisse kartı — alanlar

Kart dosyası: `karne.md` → `card.md`. Drive kökü: `Yatirim/` → `Investing/`.

| Şimdi | İngilizce | Değerler |
|---|---|---|
| `hisse` | `ticker` | sembol, örn. XYZ |
| `sirket` | `company` | |
| `borsa` | `exchange` | NYSE, NASDAQ; ileride HKEX, SSE, SZSE |
| `ulke` | `country` | |
| `sektor` | `sector` | aşağıdaki 11 GICS adı |
| `alt_sektor` | `subsector` | |
| `durum` | `status` | `candidate` · `watching` · `archived` |
| `portfoyde` | `in_portfolio` | `yes` · `no` |
| `tur` | `lynch_type` | aşağıdaki Lynch türleri |
| `sinif` | `grade` | `solid` · `mid` · `weak` · `unclear` |
| `son_kayit` | `last_entry` | tarih |
| `tarih` | `opened` | ilk kayıt, değişmez |
| `yayinla` | `publish` | `yes` · `no` |

Eski değer → yeni değer: `aday` → `candidate` · `takipte` → `watching` · `arşivde` → `archived` · `evet` / `hayır` → `yes` / `no` · `sağlam` / `SAĞLAM` → `solid` · `orta` / `ORTA` → `mid` · `zayıf` / `ZAYIF` → `weak` · `belirsiz` / `BELİRSİZ` → `unclear`.

Yeşil liste ayrı alan değil: `status = watching` ve `grade = solid`.

`belirsiz` iki yere ayrıldı. Sınıf değeri `unclear` kalır. Karttaki eksik listesinin alan adı `gaps` olur (aşağıda).

## Kayıt başlığı

Kalıp: `## <date> · <record> · <who> [· <source>]`

Köşeli parantez isteğe bağlı. `fundamental` kaydında kaynak olur (ör. `2025 annual (10-K)`). `research` ve `note` kaydında olmaz.

| Şimdi | İngilizce |
|---|---|
| `araştırma` | `research` |
| `temel analiz` | `fundamental` |
| `not` | `note` |
| `2. ajan` | `agent_2` |
| `3. ajan` | `agent_3` |
| `kullanıcı` | `user` |
| Hikâye | Story |
| Özet | Summary |
| Tez — neden sahip olunur / tezi bozacak 3 şey | Thesis |
| Önceki kayda göre ne değişti | What changed |

`### Thesis` altında iki parça olur: neden sahip olunduğu (en çok 3 madde) ve tezi bozacak 3 şey. Başlık kısa kalır; kod `### Thesis` satırını arar.

## Kartın içindeki YAML

| Şimdi | İngilizce | Not |
|---|---|---|
| `puan` | `score` | |
| `kriterler` | `criteria` | |
| `bahsedilme` | `mentions` | |
| `ton` | `tone` | |
| `neden` | `reason` | |
| `kaynak` | `source` | |
| `rapor` | `report` | |
| `donem_sonu` | `period_end` | |
| `adres` | `url` | |
| `veri_tarihi` | `as_of` | |
| `olculer` | `measures` | |
| `deger` | `value` | |
| `renk` | `mark` | `good` · `mid` · `weak` (`iyi` / `orta` / `zayif`) |
| `belirleyici` | `decisive` | `yes` · `no` |
| `birim` | `unit` | |
| `xbrl` | `xbrl` | SEC etiket adı, çevrilmez |
| `serbest_nakit` | `free_cash` | |
| `hisseyle_maas` | `stock_comp` | hisseyle ödenen maaş |
| `fiyat` | `price` | |
| `peg` | `peg` | |
| `lynch_temettu_orani` | `lynch_dividend_ratio` | |
| `nakit_verimi` | `fcf_yield` | |
| `uyarilar` | `warnings` | |
| `kod` | `code` | örn. U1 |
| `ad` | `name` | |
| `alinti` | `quote` | |
| uyarıdaki `tur` | `flag_kind` | `company_specific` · `general_risk` (`sirkete_ozel` / `genel_risk`) |
| uyarıdaki `durum` | `flag_status` | `open` · `closed` |
| `belirsiz` (liste) | `gaps` | sınıf değeri `unclear` ile aynı kelime değil |

Fiyat satırındaki yargı kelimeleri: `cazip` → `attractive` · `makul` → `fair` · `pahalı` → `expensive`. Hesaplanamayan ölçü: `not_computed`.

## 10 ölçü — alan adları

| # | Şimdi | İngilizce |
|---|---|---|
| 1 | Gelir büyümesi | `revenue_growth_3y` |
| 2 | Marj istikrarı | `margin_stability` |
| 3 | Faaliyet marjı | `operating_margin` |
| 4 | Sermaye getirisi | `capital_return` |
| 5 | Nakde dönüşüm | `cash_conversion` |
| 6 | Faiz karşılama | `interest_cover` |
| 7 | Borcu kaç yılda öder | `debt_years` |
| 8 | Hisse sayısı değişimi | `share_count` |
| 9 | Brüt kâr büyümesi | `gross_profit_growth` |
| 10 | Kasadaki para kaç yıl yeter | `cash_runway` |
| T | Temettü nakitle karşılanıyor | `dividend_cover` |
| — | Borç (6 + 7 birlikte) | `debt` |

## Lynch türü (`lynch_type`)

| Şimdi | İngilizce |
|---|---|
| Hızlı büyüyen | `fast_grower` |
| İstikrarlı dev | `stalwart` |
| Yavaş büyüyen | `slow_grower` |
| Döngüsel | `cyclical` |
| Kârsız | `unprofitable` |
| Toparlanan (1. sürümde yok) | `turnaround` |
| Varlık zengini (1. sürümde yok) | `asset_play` |

Küçülme notu bugün `ORTA (küçülme kuralı)`. Yeni ad: `mid` ve ayrıca `shrink_rule: yes`.

## Bayraklar (`flags`, sınıfı değiştirmez)

| Şimdi | İngilizce | Ne zaman |
|---|---|---|
| tek seferlik | `one_off` | işletme nakdi 2 yılda %30'dan çok düştü ama net kâr arttı; ya da satış kazancı faaliyet kârının çoğunu açıklıyor |
| nakit düşüyor | `fcf_falling` | son yıl serbest nakit eksi ve 3 yıldır düşüyor |
| veri kontrol | `data_check` | likit %50'den, borç %30'dan fazla değişti; borç adayları uyuşmuyor; bölünme Yahoo ile teyit edilmedi |
| sınırda | `borderline` | değer eşiğe %10'dan yakın |
| kira ağırlıklı | `lease_heavy` | bilgi satırı: kira dahil borç |
| satın almacı | `acquisitive` | bilgi satırı: satın almalara harcanan para |

Hızlı büyüyen güvenlik kuralı: `fast_grower_safety` (faaliyet marjı ❌ + nakit yakıyor → `solid` olamaz).

## 4. ajan ve çeyreklik

| Şimdi | İngilizce |
|---|---|
| son 4 çeyrek (kayan yıl) | `ttm` |
| yeni paranın yönü | `new_money_rank` |
| düşüş alarmı | `drop_alert` |
| pahalı | `expensive` (PEG > 3 veya nakit verimi < %1, 4 hafta) |
| portföydeki ağırlık | `weight` |
| pozisyonlar tablosu (defter) | `holdings` |
| piyasa filtresi | `market_filter` |
| satışı değerlendir | `consider_selling` |
| kıyas | `benchmark` |
| gölge portföy (SPY / altın) | `shadow` |
| alımları sayan yıllık getiri | `xirr` |
| toplam servet (hisse + altın + BES) | `total_wealth` |
| %25 kuralı yüzünden önerilmedi | `weight_cap` |

## Yapay zekâ denetçi

| Şimdi | İngilizce |
|---|---|
| denetçi | `auditor` |
| kural kartı | `rule card` (dosya: `shared/auditor/cards/`) |
| rakam denetimi · yorum denetimi · satış önerisi denetimi · olay denetimi | `figure audit` · `reading audit` · `sell audit` · `event audit` |
| tutuyor / tutmuyor / bulunamadı | `pass` / `fail` / `not_found` |
| doğrulanmadı (karnede işaret) | `unverified` |
| bilinen tuzaklar | `known traps` |
| büyük denetim (6 ayda bir) | `big review` |

## Puanın 5 kriteri

| Şimdi | İngilizce |
|---|---|
| Bahsedilme | `mentions` |
| Ton | `tone` |
| Sektör rüzgârı | `sector_tailwind` |
| Son 1 yıl haber akışı | `news_flow` |
| Hızlı sağlık | `quick_health` |

Hızlı sağlık hesaplanamazsa sonuç `unclear` (nötr 1 puan). Bu, sınıf değeriyle aynı kelimedir; alan adı `quick_health`.

## GICS 11 ana sektör

Resmî İngilizce ad. Hiçbiri uymazsa `other` (`diğer`).

| Şimdi | İngilizce |
|---|---|
| Enerji | Energy |
| Malzeme | Materials |
| Sanayi | Industrials |
| Zorunlu olmayan tüketim | Consumer Discretionary |
| Zorunlu tüketim | Consumer Staples |
| Sağlık | Health Care |
| Finans | Financials |
| Bilgi teknolojisi | Information Technology |
| İletişim hizmetleri | Communication Services |
| Kamu hizmetleri | Utilities |
| Gayrimenkul | Real Estate |

Alt sektör listesi henüz yazılmadı. Örnekler kilit: Havacılık → Aviation · Yarı iletken → Semiconductors · Yapay zekâ → Artificial intelligence · Lityum → Lithium.

Kapsam dışı iş modeli etiketi: banka → `bank` · sigorta → `insurance` · REIT → `reit` · gelirsiz şirket → `pre_revenue` · kamu hizmetleri (dağıtım) → `utility`.

## Ajanlar ve klasörler

Bugünkü klasör adı durur. Sağ sütun, çeviride ve yeni kodda kullanılacak ad. Yeni kod doğrudan sağ sütundaki klasörlere yazılır; `ajanlar/` arşiv olarak kalır (karar: 2026-10-04).

| Şimdi | İngilizce ad | İleride klasör |
|---|---|---|
| 1. Göz | Eye | `agents/eye` |
| 1B. Sayaç | Counter | `agents/counter` |
| 2. Araştırma | Research | `agents/research` |
| 3. Analiz | Analysis | `agents/analysis` |
| 4. Portföy (eski: Teknik) | Portfolio | `agents/portfolio` |
| `ortak/` | shared | `shared/` |
| `ajanlar/` | agents | `agents/` |
| `ayarlar.yaml` | settings | `settings.yaml` (dosya ilk kodla oluşturulur) |

## Tablolar

| Şimdi | İngilizce |
|---|---|
| `hisseler` | `stocks` |
| `haberler` | `articles` |
| `etiketler` | `tags` |
| `emtia_bagi` | `commodity_links` |
| `puanlar` | `scores` |
| `eksik_veri` | `missing_data` |
| `finansallar` | `financials` |
| `fiyatlar` | `prices` |
| `sinyaller` | `signals` |
| `calismalar` | `runs` |
| haftalık portföy satırı | `snapshots` |
| altın / BES girişleri | `other_assets` |
| kart kayıtları (not + tez durumu) | `card_entries` |
| denetçi sonuçları | `audits` |
| komut kaydı | `command_log` |
| Telegram'dan ayarlar (ör. model) | `settings` |
| onaylı alt sektörler | `subsectors` |

`tags` satırı: tür → `kind` (`company` · `commodity` · `sector`) · karşılık → `maps_to` · borsa → `exchange` · ülke → `country` · ana sektör → `sector` · alt sektör → `subsector`.

`commodity_links`: şirket → `company` · emtia → `commodity` · rol → `role` (`producer` · `user`) · kaynak → `source`. Üretici → `producer`. Kullanıcı → `user`.

`missing_data` durum: `açık` → `open` · `isim eklendi` → `tag_added` · `gerçekten yok` → `absent`.

`runs` sonuç: `tamam` → `ok` · `hata` → `error`.

`articles` işaretleri: detaylı okundu → `read_deep` · metin eksik → `text_missing`.

`signals` durumu: bekliyor → `pending` · bitti → `done`.

`card_entries` tez durumu (`thesis_status`): sağlam → `intact` · bozuldu → `broken` · izle → `watch`.

`holdings` satır türü: alış → `buy` · satış → `sell` · temettü → `dividend` · bölünme → `split`.

Geri alınan satır (`/undo`) silinmez, işaretlenir: geçersiz → `void`.

`other_assets` türü: altın alımı (gram + TL gram fiyatı) → `gold` · BES (aylık ödeme + toplam tutar, TL) → `bes`.

## Drive yolları

| Şimdi | İngilizce |
|---|---|
| `Yatirim/` | `Investing/` |
| `Gelen/` | `Inbox/` |
| `Haftalik/` | `Weekly/` |
| `Yedek/` | `Backup/` |
| `Hisseler/<KOD> - <Şirket adı>/` | `Stocks/<TICKER> - <Company name>/` |
| `karne.md` | `card.md` |
| `raporlar/` | `filings/` |

## 5-8-13 sinyal kodları

Doküman İngilizce adı yazar. Backtest dosyası bugünkü kodu taşır; kod ayrı işte değişir.

| Bugünkü kod | İngilizce |
|---|---|
| `TEYITLI_AL` | `CONFIRMED_BUY` |
| `TEMKINLI_AL` | `CAUTIOUS_BUY` |
| `TEMKINLI_SAT` | `CAUTIOUS_SELL` |
| `RISK` | `PREPARE_EXIT` |
| `SAT` | `SELL` |

Karışık ayrı kod değil: durum değişmez, önceki pozisyon durur.

## Telegram komutları ve mesajları (İngilizce; önceki Türkçe örnekler)

| Ne | Eski Türkçe örnek | İngilizce |
|---|---|---|
| Takibe al | "XYZ'yi takibe al" | "watch XYZ" |
| Alım kaydı | "KO 10 adet 85,65$'dan aldım" | "bought 10 KO at 85.65" |
| Şimdi analiz et | "XYZ'yi şimdi analiz et" | "analyze XYZ now" (tek seferlik model: "analyze XYZ with opus-5.5") |
| Model değiştir | — | "set strong model to gpt-6-sol" |
| Uyarı kapat | "XYZ'deki U1 uyarısını kapat, çünkü …" | "close warning U1 on XYZ because …" |
| Arşiv sorusu | "arşive alalım mı?" | "archive it?" |
| Yeni alt sektör | "Yeni alt sektör eklensin mi?" | "add a new subsector?" |
| Portföy notu | "Portföye eklendi" | "Added to portfolio" |
| Harcama sorusu | "bu ay ne harcadık?" | "what did we spend this month?" |

Kesin komut listesi uygulama planında (yol haritası 10. bölüm) yazılır.
