from agents.eye import extract
from agents.eye.sites import SITES

from .helpers import DRAGONOMI_FULL, DRAGONOMI_TEASER, EMTIA_FULL, EMTIA_GATED, JSONLD, page

EMTIA = SITES["emtia"]
DRAGONOMI = SITES["dragonomi"]


def test_emtia_page_for_a_visitor_is_gated_and_has_no_text():
    post = extract.parse_post(EMTIA_GATED, EMTIA)
    assert post.gated and post.text_missing
    assert post.text == ""                       # the CTA is a gate block, not post text
    assert post.body_selector == "article.ghost-content"
    assert post.title == "Soya fasulyesi fiyatları yatay seyrediyor"
    assert post.published_at == "2026-10-11T05:48:48.000Z"
    assert post.tags == ["Petrol", "Asya"]       # from the meta, not from the menu links


def test_emtia_full_page_gives_plain_text_with_line_breaks():
    post = extract.parse_post(EMTIA_FULL, EMTIA)
    assert not post.gated and not post.text_missing
    assert post.text.splitlines() == [
        "Soya fasulyesi vadeli işlemleri dün yatay kapandı.",
        "Analistler arz tarafında risk görmüyor.",
        "Stoklar yüksek",
        "Talep zayıf",
    ]


def test_dragonomi_teaser_is_flagged_and_loses_the_audio_player_and_the_gate_text():
    post = extract.parse_post(DRAGONOMI_TEASER, DRAGONOMI)
    assert post.gated and post.text_missing
    assert post.body_selector == "div.content.post-sneak-peek"
    assert post.text == "Yurt dışı en gelişmiş modellerin yeteneklerinin düşük fiyatlı segmentlere hızla inmesi, rekabeti gündeme getirdi."
    assert "Yazıyı dinle" not in post.text and "Premium" not in post.text


def test_dragonomi_full_page_falls_back_to_the_plain_content_selector():
    post = extract.parse_post(DRAGONOMI_FULL, DRAGONOMI)
    assert not post.text_missing
    assert post.body_selector == "div.content"
    assert post.text.splitlines() == [
        "Cummins veri merkezi motor talebinin arttığını bildirdi.",
        "Üç ana sonuç",
        "Birinci sonuç burada.",
    ]


def test_a_page_without_the_body_is_text_missing():
    post = extract.parse_post("<html><body><p>Hello</p></body></html>", EMTIA)
    assert post.body_selector is None and post.text_missing and post.text == ""


def test_tags_fall_back_to_json_ld_keywords_when_the_meta_has_none():
    html = page("<article class='ghost-content'><p>x</p></article>", tags=(), ld=JSONLD)
    assert extract.parse_post(html, EMTIA).tags == ["Bakır", "Sanayi Metalleri"]


def test_meta_tags_win_over_json_ld_and_repeats_are_dropped():
    html = page("<article class='ghost-content'><p>x</p></article>", tags=("Bakır", "Bakır", " Sanayi   Metalleri "), ld=JSONLD)
    assert extract.parse_post(html, EMTIA).tags == ["Bakır", "Sanayi Metalleri"]


def test_a_broken_json_ld_does_not_stop_the_page():
    html = page("<article class='ghost-content'><p>x</p></article>", tags=(), ld='<script type="application/ld+json">{oops</script>')
    assert extract.parse_post(html, EMTIA).tags == []


def test_glossary_post_is_found_by_the_tag_whatever_the_spelling():
    for site, tag in ((EMTIA, "Emtia Sözlüğü"), (DRAGONOMI, "Yatırım Sözlüğü")):
        html = page("<article class='ghost-content'><p>x</p></article>", tags=("Petrol", tag))
        assert extract.is_glossary(extract.parse_post(html, site), site)
    plain = page("<article class='ghost-content'><p>x</p></article>", tags=("Petrol",))
    assert not extract.is_glossary(extract.parse_post(plain, EMTIA), EMTIA)


def test_slugify_matches_ghost_for_turkish_names():
    assert extract.slugify("Doğalgaz") == "dogalgaz"
    assert extract.slugify("Yatırım Sözlüğü") == "yatirim-sozlugu"
    assert extract.slugify("İran") == "iran"
    assert extract.slugify("S&P 500") == "s-p-500"


def test_unclosed_paragraphs_and_stray_end_tags_do_not_break_the_tree():
    html = "<html><body><article class='ghost-content'><p>one<p>two</span></article></body></html>"
    assert extract.parse_post(html, EMTIA).text.splitlines() == ["one", "two"]
