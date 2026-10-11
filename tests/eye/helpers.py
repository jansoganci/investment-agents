"""Small pages built by hand in the shape the probe of 2026-10-11 found (no real post text is kept in git)."""

HEAD = """<html><head><title>Page title</title>
<meta property="og:title" content="{title}">
<meta property="article:published_time" content="{date}">
{tags}
{ld}
</head><body>
<nav><a href="/tag/petrol/">Petrol</a><a href="/tag/dogalgaz/">Doğalgaz</a></nav>
{body}
<footer>Twitter Bluesky Discord</footer></body></html>"""


def page(body, tags=("Petrol", "Asya"), title="Soya fasulyesi fiyatları yatay seyrediyor", date="2026-10-11T05:48:48.000Z", ld=""):
    meta = "\n".join(f'<meta property="article:tag" content="{t}">' for t in tags)
    return HEAD.format(title=title, date=date, tags=meta, ld=ld, body=body)


EMTIA_GATED = page(
    '<article class="ghost-content prose prose-lg prose-theme" data-preview>'
    '<div class="paywall-content-wrap"><aside class="gh-post-upgrade-cta paywall-dark">'
    '<div class="gh-post-upgrade-cta-content"><h2>Devamını okumak için lütfen giriş yapın</h2>'
    "<p>Hesabınız yoksa lütfen abone olun.</p></div></aside></div></article>"
)

EMTIA_FULL = page(
    '<article class="ghost-content prose prose-lg prose-theme" data-preview>'
    "<p>Soya fasulyesi vadeli işlemleri dün yatay kapandı.</p><p>Analistler&nbsp;arz tarafında risk görmüyor.</p>"
    "<ul><li>Stoklar yüksek</li><li>Talep zayıf</li></ul></article>"
)

DRAGONOMI_TEASER = page(
    '<div class="content post-sneak-peek">'
    '<div class="kg-card kg-audio-card"><div class="kg-audio-player"><span>Yazıyı dinle</span>'
    '<span>0:00 / 248</span><button>1×</button></div></div>'
    "<p>Yurt dışı en gelişmiş modellerin yeteneklerinin düşük fiyatlı segmentlere hızla inmesi, rekabeti gündeme getirdi.</p>"
    '<div class="content-cta paid"><h2 class="content-cta__title">Bu not Premium üyelere açık</h2>'
    '<p class="content-cta__price">Yıllık $96</p><a class="content-cta__btn" href="/signup/">Abone ol</a>'
    '<div class="content-cta__signin">Zaten üye misiniz?</div></div></div>',
    tags=("Şirketler", "Cummins", "Amerika Hisseleri"),
)

DRAGONOMI_FULL = page(
    '<div class="content"><div class="kg-audio-player"><span>Yazıyı dinle</span></div>'
    "<p>Cummins veri merkezi motor talebinin arttığını bildirdi.</p><h2>Üç ana sonuç</h2><p>Birinci sonuç burada.</p></div>",
    tags=("Şirketler", "Cummins"),
)

JSONLD = (
    '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Article",'
    '"keywords":["Bakır","Sanayi Metalleri"]}</script>'
)
