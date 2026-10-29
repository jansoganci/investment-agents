"""The bulletin's Turkish text (docs/BULLETIN_PLAN.md slice 5): the approved template filled from the checked draft. No model here.

    rendered = render.render(pack, draft, market_text, now)

Sections: figures · today's 3 items · calendar · macro · my stocks · interests · sources. The figures table, the earnings and SEC lines
(📌) and the fixed words are written by code in Turkish; the items are the writer's, in the translation that passed the number
check (else the English item with a note). Every item ends with its source tags and link numbers, `[ED1, W2]`: ED / DR = a post
of Emtia Defteri / Dragonomi, W = the web; the numbers refer to the list at the end. The top-3 digest repeats items.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from shared import clock, search
from shared.bulletin.gather import Pack
from shared.bulletin.write import Draft, Item

MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
DAYS = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
WHEN = (("today", "Bugün"), ("tomorrow", "Yarın"), ("week", "Bu hafta"), ("later", "İleride"))
GROUPS = (("ai_infrastructure", "AI altyapısı"), ("other", "Diğer"))
TAGS = {"emtia": "ED", "dragonomi": "DR"}
FORMS_READ_ON_SUNDAY = ("10-K", "10-Q", "20-F", "40-F", "10-K/A", "10-Q/A", "20-F/A", "40-F/A")
NOTE_STARTS = ("Web search", "SEC could not", "Yahoo has no", "Translation failed", "Writer failed")
MAX_SOURCES = 40

TR_8K = {"1.01": "önemli bir sözleşme yaptı", "1.02": "önemli bir sözleşmeyi bitirdi", "1.03": "iflas ya da kayyum", "2.01": "bir satın alma ya da varlık satışını tamamladı",
         "2.02": "sonuçlarını açıkladı", "2.03": "yeni bir mali yükümlülük üstlendi", "2.04": "bir borç vadesinden önce muaccel oldu",
         "2.05": "çıkış ya da yeniden yapılanma maliyeti duyurdu", "2.06": "önemli bir değer düşüklüğü kaydetti", "3.01": "borsadan çıkarma bildirimi aldı",
         "3.02": "kayıtsız hisse sattı", "3.03": "hissedar haklarını değiştirdi", "4.01": "denetçisini değiştirdi",
         "4.02": "önceki mali tablolara güvenilmemesi gerektiğini bildirdi", "5.01": "kontrol değişikliği", "5.02": "bir yönetici ya da yönetim kurulu üyesi ayrıldı ya da katıldı",
         "5.03": "esas sözleşmesini değiştirdi", "5.07": "hissedar oylamasının sonucunu bildirdi", "7.01": "kamuya açıklama yaptı", "8.01": "başka bir olay bildirdi"}


@dataclass
class Rendered:
    text: str
    sources: list = field(default_factory=list)     # [{"n", "tag", "title", "site", "url"}]


def date_tr(d: date) -> str:
    return f"{d.day} {MONTHS[d.month - 1]}"


def header(now: datetime) -> str:
    d = date.fromisoformat(clock.today_local(now))
    return f"☀️ SABAH BÜLTENİ · {date_tr(d)} {d.year}, {DAYS[d.weekday()]}"


class Sources:
    """Link numbers in the order the text first cites a piece."""

    def __init__(self, pieces: dict):
        self.pieces, self.order = pieces, {}

    @staticmethod
    def tag(piece) -> str:
        return "W" if piece.kind == "web" else TAGS.get(piece.site, "ED")

    def suffix(self, ids) -> str:
        labels = []
        for pid in ids:
            n = self.order.setdefault(pid, len(self.order) + 1)
            labels.append(f"{self.tag(self.pieces[pid])}{n}")
        return " [" + ", ".join(labels) + "]"

    def listing(self) -> list:
        out = []
        for pid, n in sorted(self.order.items(), key=lambda kv: kv[1])[:MAX_SOURCES]:
            p = self.pieces[pid]
            site = "" if p.kind == "post" else f"{p.site}: "
            # DeepSeek shortens some addresses with "..." (seen 2026-10-29: pcmag, digitaltoday): such a link does not open, so none is shown
            url = "" if "..." in (p.url or "") or "…" in (p.url or "") else (p.url or "")
            out.append({"n": n, "tag": self.tag(p), "title": f"{site}{p.title}"[:90], "site": p.site, "url": search.clean_url(url) if url else ""})
        return out


def _shown(item: Item) -> str:
    """The Turkish text if it passed its check; else the English one with the reason; a failed number check adds a warning."""
    if item.turkish and not item.turkish_flag:
        text = item.turkish
    else:
        text = item.text + (f" ⚠ {item.turkish_flag}" if item.turkish_flag else "")
    numbers = [n.strip() for f in item.flags if f.startswith("numbers:") for n in f.split(":", 1)[1].split(",")]
    return text + (f" ⚠ rakam doğrulanamadı ({', '.join(numbers)})" if numbers else "")


def _line(item: Item, sources: Sources) -> str:
    return _shown(item) + sources.suffix(item.sources)


def _bucket(d: date, today: date) -> str:
    return "today" if d <= today else "tomorrow" if d == today + timedelta(days=1) else "week" if d <= today + timedelta(days=7) else "later"


def _earnings_lines(pack: Pack, today: date) -> dict:
    out: dict = {key: [] for key, _ in WHEN}
    for p in pack.earnings:
        d = date.fromisoformat(p.data["date"])
        out[_bucket(d, today)].append(f"📌 {p.tickers[0]} bilançosu" + ("" if d == today else f": {date_tr(d)}"))
    return out


def _filing_lines(pack: Pack) -> list:
    lines = []
    for p in pack.filings:
        form, filed, items = p.data.get("form"), p.data.get("filed"), p.data.get("items") or []
        when = date_tr(date.fromisoformat(filed)) if filed else ""
        if form in FORMS_READ_ON_SUNDAY:
            lines.append(f"📌 {p.tickers[0]} {form} yayınladı ({when}). 3. ajan Pazar günü okuyacak.")
        elif form == "8-K":
            said = "; ".join(f"{TR_8K.get(x, 'başka bir kalem bildirdi')} (madde {x})" for x in items)
            lines.append(f"📌 {p.tickers[0]} 8-K ({when}): {said}.")
    return lines


def render(pack: Pack, draft: Draft, market_text: str, now: datetime | None = None, failed: str | None = None) -> Rendered:
    now = now or clock.now_utc()
    today = date.fromisoformat(clock.today_local(now))
    sources = Sources(pack.pieces())
    blocks = [header(now), market_text]
    if failed:
        blocks.append(f"⚠ Haberler yazılamadı ({failed[:120]}). Rakamlar ve takvim aşağıda; haberleri sonra tekrar deneyeceğim.")

    top = draft.top3()
    if top:
        blocks.append("⚡ BUGÜNÜN 3 MADDESİ\n" + "\n".join(f"{n}. {_line(i, sources)}" for n, i in enumerate(top, 1)))

    calendar = _earnings_lines(pack, today)
    rows = []
    for key, label in WHEN:
        lines = [f"• {_line(i, sources)}" for i in draft.of("calendar") if i.when == key] + [f"• {x}" for x in calendar[key]]
        if lines:
            rows.append(label + "\n" + "\n".join(lines))
    filings = _filing_lines(pack)
    if filings:
        rows.append("Yeni başvurular\n" + "\n".join(f"• {x}" for x in filings))
    if rows:
        blocks.append("🗓 TAKVİM\n" + "\n".join(rows))

    macro = draft.of("macro")
    if macro:
        blocks.append("🌍 MAKRO\n" + "\n".join(f"• {_line(i, sources)}" for i in macro))

    if pack.stocks:
        lines, quiet = [], []
        for s in pack.stocks:
            items = [i for i in draft.of("stocks") if i.ticker == s.ticker]
            quiet += [] if items else [s.ticker]
            for i in items:
                lines.append(f"{s.ticker} · {_line(i, sources)}")
                if i.thesis_point and i.thesis_point <= len(s.breaks):
                    lines.append(f"     ↳ Tez bozucu {i.thesis_point} ile ilgili: \"{s.breaks[i.thesis_point - 1]}\"")
        if quiet:
            lines.append("Haber yok: " + ", ".join(quiet))
        blocks.append("💼 HİSSELERİM\n" + "\n".join(lines))
    else:
        blocks.append("💼 HİSSELERİM\nİzleme listesi boş: izlediğin ya da sahip olduğun hisse yok.")

    parts = []
    for key, label in GROUPS:
        lines = [f"• {_line(i, sources)}" for i in draft.of("interests") if i.group == key]
        if lines:
            parts.append(label + "\n" + "\n".join(lines))
    if parts:
        blocks.append("🔭 İLGİ KONULARI\n" + "\n".join(parts))

    if not draft.items and not failed:
        blocks.append("Kaynaklardan yeni bir haber gelmedi.")

    listing = sources.listing()
    if listing:
        blocks.append("🔗 KAYNAKLAR\n" + "\n".join(f"{s['n']}. [{s['tag']}] {s['title']}" + (f" — {s['url']}" if s["url"] else "") for s in listing))

    missing = [n for n in pack.notes + draft.notes if n.startswith(NOTE_STARTS)]
    if missing:
        blocks.append(f"ℹ️ {len(missing)} kaynak ya da adım alınamadı (ayrıntı veritabanında).")
    return Rendered("\n\n".join(blocks), listing)
