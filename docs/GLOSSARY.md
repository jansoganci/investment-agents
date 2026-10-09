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

Hisseyi kim ekledi (`added_by`): yazılardan geldi → `counter` · ben ekledim → `user` (ekranda "added by me").

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
| eski veri | `stale_data` | SEC'in verisi en yeni raporu henüz içermiyor: rakamlar bir önceki rapordan (yol haritası kural 43) |
| kira ağırlıklı | `lease_heavy` | bilgi satırı: kira dahil borç |
| satın almacı | `acquisitive` | bilgi satırı: satın almalara harcanan para |
| borçsuz | `debt_free` | bilgi satırı: borç kalemi bildirilmedi, borç 0 sayıldı (varsayım; kullanılmayan kredi limiti borç değildir) — kart YAML'ında `debt.parts.assumed` |

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

Kapsam dışı iş modeli etiketi: banka → `bank` · sigorta → `insurance` · REIT → `reit` · gelirsiz şirket → `pre_revenue` · kamu hizmetleri (dağıtım) → `utility`. Alan adı: `out_of_scope` (`stocks` tablosunda; boş = kapsamda; karar 2026-10-05).

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
| ana Mac'in deneme klasörü (yalnızca Mac yazar; gerçek `Investing/`'e yalnızca Air yazar) | `Investing-dev/` |

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

## Kod ve veritabanı adları (faz 0, 2026-10-04)

Faz 0'ın kodu bu adları getirdi. Türkçe karşılığı olmayan yeni adlar; sol sütun ne olduğunu söyler.

**Modüller (`shared/`):** `config` (settings.yaml + `.env`) · `clock` (UTC saklanır, Türkiye saatiyle gösterilir) · `db` (tablolar,
sürüm, yükseltme adımları; `python -m shared.db init | upgrade | info`) · `backup` (gece kopyası) · `runlog` (`runs` satırı) ·
`notify` (işin yazdırdığı mesaj) · `drive` (`Investing/` yolları; `python -m shared.drive test`) · `commands` (Hermes'in komut
listesi) · `ask` (serbest sorular için salt-okur yol).

**`.env` yolları:** Drive kökü → `DRIVE_DIR` · veri klasörü (isteğe bağlı) → `DATA_DIR`.

**Dosyalar:** veritabanı → `investment-agents.sqlite` · yedek → `Backup/investment-agents-YYYY-MM-DD.sqlite` · yükseltme öncesi
kopya → `<veri klasörü>/pre-upgrade/` · Drive test dosyası → `Inbox/drive-test-YYYY-MM-DD-HHMM.md` · `/setcommands` metni →
`docs/telegram_setcommands.txt`.

| Ne | Ad |
|---|---|
| her tabloda: kayıt zamanı (UTC) | `created_at` |
| hisseye bağlantı (iç numara) | `stock_id` (`commodity_links`'teki `company` budur) |
| kaydı yaratan komutun numarası | `command_id` |
| geri alındı mı / hangi komutla | `void` (0 / 1) · `voided_by` |
| `runs`: iş adı · başladı · bitti · dolar · hata | `job` · `started_at` · `ended_at` · `cost_usd` · `error` |
| `runs` durumu (yeni değer) | çalışıyor → `running` (`ok` / `error` aynı) |
| `command_log`: komut · argümanlar · ne değişti · hedef tablo / satır · durum | `command` · `args` · `summary` · `target_table` / `target_id` · `status` (`done` / `void`) |
| `articles`: site · başlık · yayın zamanı · tek cümle · tam metin | `site` · `title` · `published_at` · `sentence` · `full_text` |
| `tags` kaynağı | `source` (`ai` / `user`) |
| `scores`: hafta · toplam · gerekçeler (JSON) | `week` · `score` · `reasons` |
| `missing_data`: yıl · rakam · denenen adlar | `year` · `figure` · `names_tried` |
| `financials`: dönem sonu · dönem türü · form · rakam · değer · birim · etiket · başvuru no · kaynak | `period_end` · `period_type` (`annual` / `quarter` / `ttm`) · `form` · `figure` · `value` · `unit` · `xbrl` · `filing` · `source` (`sec` / `user`) |
| `prices`: sembol · gün · kapanış · düzeltilmiş kapanış · para birimi | `symbol` · `date` · `close` · `adj_close` · `currency` |
| `signals`: tür · gün · ayrıntı | `kind` · `date` · `detail` |
| `holdings`: adet · fiyat · masraf · tutar · bölünme oranı | `quantity` · `price` · `fee` · `amount` · `split_ratio` |
| `other_assets`: gram · TL gram fiyatı · TL ödeme · TL toplam · kur | `grams` · `price_try` · `payment_try` · `total_try` · `usdtry` |
| `snapshots`: hafta sonu · hisse değeri · konan · geri alınan · getiri % · SPY gölge · altın gölge · altın · BES · hedef payı | `week_end` · `stock_value` · `put_in` · `got_back` · `return_pct` · `spy_shadow` · `gold_shadow` · `gold_value` · `bes_value` · `goal_share` |
| `card_entries`: kayıt · kim | `record` · `who` (kayıt başlığındaki değerler) |
| `audits`: denetim türü · sonuç · model | `audit` (`figure` / `reading` / `sell` / `event`) · `result` · `model` |
| `settings` (Telegram'dan): anahtar · değer | `key` · `value` (en son geçerli satır kazanır; boş değer = varsayılana dön) |

## Kod ve veritabanı adları (faz 1, 2026-10-05)

**Modüller:** `shared/sec` (SEC istemcisi; `facts` rakamları izleriyle okur; `synonyms` eş ad listeleri ve borç grupları) ·
`shared/sectors` (SIC → sektör tablosu, döngüsel SIC listesi, kapsam dışı SIC listesi) · `shared/prices` (tek fiyat işi;
`yahoo` Yahoo istemcisi) · `agents/analysis` (`measures` 10 ölçü + tür + sınıf + bayraklar + fiyat satırı; `card` kart yazıcısı;
`run` uçtan uca çalıştırma ve haftalık "yeni rapor var mı?" kontrolü). Komutlar: `shared/commands/stocks.py`.
Örnek veri: `tests/fixtures/sec/`, `tests/fixtures/yahoo/` (her dosyada `_meta`: kaynak ve tarih).

**`settings.yaml`:** sektör düzeltmesi → `sector_overrides` (ticker: sektör).

**Rakam adları** (`financials.figure` ve `/data`): satış → `revenue` · satış maliyeti → `cost` · brüt kâr → `gross` ·
faaliyet kârı → `operating` · vergi öncesi kâr → `pretax` · vergi → `tax` · net kâr → `net` · faiz gideri → `interest` ·
net faiz geliri → `net_interest_income` · faiz geliri → `interest_income` · işletme nakdi → `op_cash` · yatırım harcaması → `capex` ·
hisseyle ödenen maaş → `stock_comp` · ödenen temettü → `dividends` · hisse başı kâr (seyreltilmiş) → `eps` ·
hisse sayısı (seyreltilmiş ortalama) → `shares` · satış kazancı → `gain_on_sale` · satın almalar → `acquisitions` · nakit → `cash` ·
kısa vadeli yatırımlar → `short_term_investments` · menkul kıymetler → `marketable_securities` · kısmi kısa vadeli yatırım adı →
`short_term_investments_partial` · toplam varlık → `assets` · kısa vadeli borçlar (yükümlülük) → `current_liabilities` ·
toplam yükümlülük → `liabilities` · kira yükümlülüğü → `leases` · borç (grup toplamı) → `debt` · likit varlık (parçaların toplamı) → `liquid`.

| Ne | Ad |
|---|---|
| `financials.period_type` için son 4 çeyrek | `ttm` (`annual` yıllık rapor) |
| eksik veri ve `/data` yıl adı | `2025` (yıllık) · `TTM 2026-06-28` (son 4 çeyrek) |
| `prices`: o günün temettüsü · bölünme oranı | `dividend` · `split_ratio` (10'a 1 → 10; 1'e 8 ters → 0.125) |
| `financials`: kaydı yaratan komut · geri alındı mı | `command_id` · `void` / `voided_by` |
| `card_entries`: kaydın dayandığı rapor (başvuru no) | `filing` |
| `command_log`: değişikliğin yerine geçtiği eski hâl (JSON) | `before` |
| kart kaydı başlığındaki kaynak | `2025 annual (10-K)` · `last 4 quarters to 2026-06-28 (10-Q)` |
| kart YAML'ı: ek alanlar | `source.filing` · `price.price` · `free_cash.currency` · `free_cash.path_5y` (son 5 yılın serbest nakdi) · `price.market_value` · `price.pe` · `price.fcf_yield_latest` · `price.verdict` · `free_cash.average_3y` · `liquid` / `debt` (`value` + `parts`) · `info` (bilgi satırları: `lease_heavy`, `acquisitive`, `debt_free`, Yahoo notları) · `warnings[].detail` · kapsam dışında `out_of_scope` + `sic` |
| hesaplanamayan değer (kartta) | `not_computed` |


## Kod ve veritabanı adları (faz 2, 2026-10-06)

**Modüller:** `shared/ai` (tek yapay zekâ istemcisi: sağlayıcı sırası, `/model` üstüne yazması, maliyet kaydı, aylık sınır; `fake` testler
için; `python -m shared.ai ping`) · `shared/auditor` (denetçi: ortak motor + `cards/figure.md`, `reading.md`, `sell.md` kural kartları;
`testset` hata kümeleri; `python -m shared.auditor testset`) · `shared/sec/filing` (bir raporun metni, alıntıyı kelimesi kelimesine
doğrulama, yapay zekâya gidecek parçalar) · `agents/analysis/ai` (neden cevapları, ilk tez, tez kontrolü, düşüş uyarısı kontrolü,
denetçi çağrıları) · `agents/analysis/sell` (satmayı düşün tetikleri) · `agents/analysis/ask` (eksik rakam isteği) ·
`agents/analysis/modeltest` (güçlü model testi). Komutlar: `shared/commands/cards.py`, `shared/commands/aicmds.py`.

**Veritabanı (sürüm 4):** `ai_calls` (her yapay zekâ çağrısı: `run_id`, `stock_id`, iş, sağlayıcı, model, `input_tokens`, `output_tokens`, `cost_usd`, `estimated` (varsayılan fiyatla sayıldı), `outcome` = `ok` / `refused` / `cut` (faturalanıp reddedilen çağrı)) ·
`audits.filing` · `card_entries.unverified` · `missing_data.asked_at` / `reminded_at`.

**Kart:** uyarı kodu (`U1`…) bir koşulu tanır ve her girişte aynı kalır; kapatılmış uyarı `flag_status: closed` · uyarının `kind` alanı
(`company_specific` / `general_risk`) yapay zekâ cevabından gelir · `thesis_status` (`intact` / `broken` / `watch`) · `unverified: yes`
(denetçi karşı çıktı) · `sell_suggestion` (`trigger`, `status: sent | held`) · `audits` özeti · `thesis_check`.
Satmayı düşün tetikleri: `thesis_broken` · `grade_weak` · `mid_after_solid`.

**`settings.yaml`:** `ai` (alıntı ve parça sınırları, denetim örneklemesi) · `pricing` (milyon token başına dolar) · `model_aliases`
(`opus-5.5` gibi kısa adlar). **`.env`:** `ANTHROPIC_API_KEY` · `DEEPSEEK_API_KEY` · `OPENAI_API_KEY` · `OPENROUTER_API_KEY`.

**Faz 2 denetimi sonrası eklenenler (2026-10-06):** kartta `warnings[].key` (uyarının kimliği: tutarlar maskelenir, yıllar kalır) ve
`warnings[].answer` / `quote` / `kind` · `measures.<ad>.why` (zayıf ölçünün cevabı) · `thesis_check` · `runs` iş adları: `analysis`,
`auditor_testset`, `modeltest` (ve `ai_calls.job = ping`) · `settings` tablosunda anahtar `model.<iş>` · `settings.yaml`: `pricing.default`
(fiyatı olmayan model için temkinli fiyat), `ai.excerpt_chars`, `ai.min_quote_chars`, `ai.audit_sample`, `ai.max_tokens`, `ai.timeout_s` ·
denetçi ve yazar **farklı model ailesinden** olur (`shared.ai.family`) · satış önerisi durumları: `sent` / `held` (nedenleri: denetçi karşı
çıktı · teyit edilemedi · denetim çalışamadı).

## Kod ve veritabanı adları (faz 3, 2026-10-09)

**Modüller (`agents/portfolio`):** `ledger` (defter: alım / satış satırları, kodun eklediği temettü ve bölünme, pozisyon ve ortalama
maliyet) · `marketdata` (`prices` satırları bugünün hisse sayısına göre; SPY'nin temettüyle yeniden yatırım endeksi; gram altın;
USD/TRY) · `value` (değer, ağırlık, kâr / zarar, gölgeler, getiri, toplam servet) · `watch` (düşüş alarmı, pahalılık takibi, yeni
para sıralaması) · `block` (portföy bloğu) · `run` (haftalık çalışma ve `/portfolio`). Komutlar: `shared/commands/portfolio.py`.
`python -m agents.portfolio` (haftalık) · `python -m agents.portfolio --show` (son kapanışlarla blok).

**Veritabanı (sürüm 5):** `valuations` (pahalılık takibinin haftalık rakamları: `week_end`, `close`, `peg`, `fcf_yield`,
`expensive` (0 / 1), `card_date` — rakamların geldiği kart kaydı).

| Ne | Ad |
|---|---|
| 4. ajan (kart notunda) | `agent_4` (`## <tarih> · note · agent_4`; yalnızca pahalılık uyarısı) |
| haftanın cuma günü (haftalık çalışmanın kapanışı) | `week_end` |
| hissenin şimdiki hisse sayısına göre fiyat | bugünün tabanı (today's basis) |
| SPY'nin temettüsü yeniden yatırılmış endeksi | toplam getiri endeksi (total-return index) |
| yeni para sıralamasının 3 şartı | `below_high` · `thesis_intact` · `price_fair` |
| `signals.detail` (yeni para) | `rank` · `would_rank` · `score` · `conditions` · `drop` · `weight` · `expensive_4_weeks` |
