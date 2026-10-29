"""shared/bulletin/render: the approved template in Turkish — sections, source tags and numbers, code lines, warnings."""

from datetime import datetime, timezone

from shared.bulletin import render
from shared.bulletin.gather import Pack, Piece, StockInfo
from shared.bulletin.write import Draft, Item

NOW = datetime(2026, 10, 29, 5, 0, tzinfo=timezone.utc)          # 08:00 Turkey time, a Thursday
MARKET = "📊 RAKAMLAR (son kapanış)\nS&P 500 · 7.743,98 · 1 ay ▲ %0,8 · gün ▲ %0,3"


def pack(stocks=True):
    p = Pack(window_start="2026-10-28T05:15:00Z", window_end="2026-10-29T05:00:00Z")
    if stocks:
        p.stocks = [StockInfo("KO", "Coca-Cola", True, "2026-10-20", ("price war", "debt grows", "CEO leaves")),
                    StockInfo("NVDA", "Nvidia", False, None, ())]
    p.posts = [Piece("P1", "post", "SK Hynix", "x", "emtia", "2026-10-28T03:00:00Z", "https://emtia.example/p1"),
               Piece("P2", "post", "Çin verileri", "x", "dragonomi", "2026-10-28T02:00:00Z", "https://dragonomi.example/p2")]
    p.web = [Piece("W1", "web", "Brent tops $115", "x", "Reuters", "2026-10-28T01:00:00Z", "https://reuters.example/brent", topic="oil")]
    p.filings = [Piece("F1", "filing", "KO 10-Q", "x", "sec", "x", tickers=("KO",), data={"form": "10-Q", "filed": "2026-10-27", "items": []}),
                 Piece("F2", "filing", "KO 8-K", "x", "sec", "x", tickers=("KO",), data={"form": "8-K", "filed": "2026-10-28", "items": ["2.02"]})]
    p.earnings = [Piece("E1", "earnings", "KO earnings", "x", "yahoo", "2026-10-29", tickers=("KO",), data={"date": "2026-10-29"}),
                  Piece("E2", "earnings", "NVDA earnings", "x", "yahoo", "2026-10-30", tickers=("NVDA",), data={"date": "2026-10-30"}),
                  Piece("E3", "earnings", "FCX earnings", "x", "yahoo", "2027-01-21", tickers=("FCX",), data={"date": "2027-01-21"})]
    return p


def draft():
    d = Draft()
    d.items = [
        Item("calendar", "ECB rate decision today.", ("W1",), when="today", turkish="ECB faiz kararı bugün."),
        Item("calendar", "BoJ decides tomorrow.", ("W1",), when="tomorrow", turkish="BoJ yarın karar verecek."),
        Item("macro", "Brent at $115.47.", ("W1", "P1"), rank=1, turkish="Brent 115,47 $."),
        Item("macro", "Gas hit 100 euros.", ("P1",), turkish="Gaz 100 euroya çıktı."),
        Item("stocks", "KO raised prices 4%.", ("P1",), ticker="KO", thesis_point=2, rank=2, turkish="KO fiyatları %4 artırdı."),
        Item("interests", "HBM is sold out to 2029.", ("P2",), group="ai_infrastructure", rank=3, turkish="HBM 2029'a kadar tükendi."),
        Item("interests", "Phillips 66 profit rose.", ("P2",), group="other", turkish="Phillips 66 kârı arttı."),
    ]
    return d


def test_the_full_template_in_order():
    r = render.render(pack(), draft(), MARKET, NOW)
    text = r.text
    order = ["☀️ SABAH BÜLTENİ · 29 Ekim 2026, Perşembe", "📊 RAKAMLAR", "⚡ BUGÜNÜN 3 MADDESİ", "🗓 TAKVİM", "🌍 MAKRO", "💼 HİSSELERİM",
             "🔭 İLGİ KONULARI", "🔗 KAYNAKLAR"]
    assert [text.index(s) for s in order] == sorted(text.index(s) for s in order)
    assert "S&P 500 · 7.743,98 · 1 ay ▲ %0,8 · gün ▲ %0,3" in text
    assert "1. Brent 115,47 $. [W1, ED2]" in text                                    # the digest is ranked 1, 2, 3 and repeats the items
    assert "2. KO fiyatları %4 artırdı. [ED2]" in text and "3. HBM 2029'a kadar tükendi. [DR3]" in text


def test_the_calendar_has_the_writers_items_and_the_codes_lines():
    text = render.render(pack(), draft(), MARKET, NOW).text
    calendar = text.split("🗓 TAKVİM\n")[1].split("\n\n")[0]
    assert calendar.splitlines() == [
        "Bugün", "• ECB faiz kararı bugün. [W1]", "• 📌 KO bilançosu",
        "Yarın", "• BoJ yarın karar verecek. [W1]", "• 📌 NVDA bilançosu: 30 Ekim",
        "İleride", "• 📌 FCX bilançosu: 21 Ocak",
        "Yeni başvurular", "• 📌 KO 10-Q yayınladı (27 Ekim). 3. ajan Pazar günü okuyacak.",
        "• 📌 KO 8-K (28 Ekim): sonuçlarını açıkladı (madde 2.02)."]


def test_my_stocks_show_the_thesis_tag_and_who_has_no_news():
    stocks = render.render(pack(), draft(), MARKET, NOW).text.split("💼 HİSSELERİM\n")[1].split("\n\n")[0]
    assert stocks.splitlines() == ['KO · KO fiyatları %4 artırdı. [ED2]', '     ↳ Tez bozucu 2 ile ilgili: "debt grows"', "Haber yok: NVDA"]


def test_a_thesis_point_the_card_does_not_have_is_not_shown():
    d = draft()
    d.of("stocks")[0].thesis_point = 3
    p = pack()
    p.stocks[0] = StockInfo("KO", "Coca-Cola", True, "2026-10-20", ("only one",))
    assert "Tez bozucu" not in render.render(p, d, MARKET, NOW).text


def test_interests_are_grouped_and_sources_are_numbered_in_order_of_first_use():
    r = render.render(pack(), draft(), MARKET, NOW)
    assert "🔭 İLGİ KONULARI\nŞirket haberleri\n• Phillips 66 kârı arttı. [DR3]" in r.text
    assert r.text.endswith("🔗 KAYNAKLAR\n1. [W] Reuters: Brent tops $115 — https://reuters.example/brent\n"
                           "2. [ED] SK Hynix — https://emtia.example/p1\n3. [DR] Çin verileri — https://dragonomi.example/p2")
    assert [(s["n"], s["tag"]) for s in r.sources] == [(1, "W"), (2, "ED"), (3, "DR")]


def test_a_translation_that_failed_shows_the_english_item_with_the_reason():
    d = draft()
    d.items[2].turkish, d.items[2].turkish_flag = None, "çeviri kontrolü: rakamlar uyuşmuyor"
    d.items[3].flags.append("numbers: 100")
    text = render.render(pack(), d, MARKET, NOW).text
    assert "1. Brent at $115.47. ⚠ çeviri kontrolü: rakamlar uyuşmuyor [W1, ED2]" in text
    assert "• Gaz 100 euroya çıktı. ⚠ rakam doğrulanamadı (100) [ED2]" in text


def test_no_stocks_an_empty_day_a_failed_writer_and_missing_sources():
    assert "💼 HİSSELERİM\nİzleme listesi boş: izlediğin ya da sahip olduğun hisse yok." in render.render(pack(stocks=False), draft(), MARKET, NOW).text
    empty = Pack(window_start="a", window_end="b")
    text = render.render(empty, Draft(), MARKET, NOW).text
    assert text.endswith("Kaynaklardan yeni bir haber gelmedi.") and "🔗" not in text and "🌍" not in text
    failed = render.render(empty, Draft(), MARKET, NOW, failed="AIError: no model answered").text
    assert "⚠ Haberler yazılamadı (AIError: no model answered)" in failed and "Kaynaklardan yeni" not in failed
    p = pack()
    p.notes = ["Web search 'oil' failed: HTTP 503", "SEC could not be asked for V: RuntimeError"]
    d = draft()
    d.notes = ["Translation failed (ValueError: x): the English items are shown.", "macro: 2 item(s) over the limit of 8 were left out"]
    assert render.render(p, d, MARKET, NOW).text.endswith("ℹ️ 3 kaynak ya da adım alınamadı (ayrıntı veritabanında).")


def test_a_shortened_address_is_not_shown_as_a_link():
    # DeepSeek's search returned "https://www.pcmag.com/news/sk-hyn...2029": it does not open, so the list shows the title only
    p = pack()
    p.posts[0] = Piece("P1", "post", "SK Hynix", "x", "emtia", "2026-10-28T03:00:00Z", "https://www.pcmag.com/news/sk-hyn...2029")
    r = render.render(p, draft(), MARKET, NOW)
    assert "2. [ED] SK Hynix\n" in r.text and "sk-hyn...2029" not in r.text
    assert [s["url"] for s in r.sources if s["n"] == 2] == [""]


def test_dates_in_turkish():
    from datetime import date
    assert render.date_tr(date(2026, 1, 5)) == "5 Ocak" and render.date_tr(date(2026, 8, 31)) == "31 Ağustos"
    assert render.header(datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc)) == "☀️ SABAH BÜLTENİ · 2 Kasım 2026, Pazartesi"


def test_ranked_items_are_printed_in_the_top_three_only_except_for_my_stocks():
    text = render.render(pack(), draft(), MARKET, NOW).text
    assert text.count("Brent 115,47 $.") == 1                                         # macro skips the ranked item
    assert "• Gaz 100 euroya çıktı." in text                                          # an unranked macro item stays
    assert text.count("HBM 2029'a kadar tükendi.") == 1 and "AI altyapısı" not in text   # interests skip it too; an empty group has no heading
    assert text.count("KO fiyatları %4 artırdı.") == 2                                # my stocks show all of theirs
