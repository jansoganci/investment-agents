"""shared/sec/filing.py: text from HTML, the word-for-word quote check, the excerpts the AI reads."""

from shared import sec
from shared.sec import filing
from tests.fixtures.loader import filing_text, sec_submissions

HTML = """<html><head><title>x</title><style>p {color: red}</style></head><body>
<ix:header><ix:hidden>HIDDEN FACT</ix:hidden></ix:header>
<div><p>As of July 26, 2026, we had $33.5&nbsp;billion aggregate principal amount of senior notes outstanding.</p></div>
<table><tr><td>Total assets</td><td>$ 1,000</td></tr></table><script>var x = 1;</script>
<p>The company said it’s &quot;well positioned” — and growing.</p></body></html>"""


def test_html_to_text_drops_hidden_xbrl_scripts_and_styles():
    text = filing.html_to_text(HTML)
    assert "HIDDEN FACT" not in text and "var x" not in text and "color: red" not in text
    assert "$33.5 billion aggregate principal amount of senior notes outstanding." in text
    assert "Total assets $ 1,000" in text  # a table row is one line


def test_quote_must_appear_word_for_word_but_quotes_dashes_and_spacing_do_not_matter():
    text = filing.html_to_text(HTML)
    assert filing.quote_in(text, "we had $33.5 billion  aggregate principal amount of senior notes")
    assert filing.quote_in(text, "The company said it's \"well positioned\" - and growing")
    assert not filing.quote_in(text, "we had $35.5 billion aggregate principal amount of senior notes")  # a changed figure
    assert not filing.quote_in(text, "senior notes")  # too short to prove anything


def test_a_quote_from_a_real_filing_and_an_invented_one():
    text = filing_text("NVDA")["text"]
    real = "As of July 26, 2026, we had $33.5 billion aggregate principal amount of senior notes outstanding."
    assert filing.quote_in(text, real)
    assert not filing.quote_in(text, "As of July 26, 2026, we had $53.5 billion aggregate principal amount of senior notes outstanding.")
    assert not filing.quote_in(text, "NVIDIA announced a class action lawsuit about its senior notes in July 2026.")


def test_excerpts_pick_the_matching_paragraphs_within_the_limit():
    text = filing_text("NVDA")["text"]
    parts = filing.excerpts(text, ["senior notes", "commercial paper"], max_chars=3000)
    assert parts and sum(len(p) for p in parts) <= 3000
    assert any("aggregate principal amount of senior notes" in p for p in parts)
    assert filing.excerpts(text, ["zzzzqqqq"]) == []


def test_primary_document_and_url():
    subs = sec_submissions("NVDA")
    accn = subs["filings"]["recent"]["accessionNumber"][0]
    doc = sec.primary_document(subs, accn)
    assert doc and sec.primary_document(subs, "0000000000-00-000000") is None
    assert sec.filing_url("0001045810", "0001045810-26-000075", "x.htm") == \
        "https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/x.htm"


def test_a_short_table_row_with_a_number_is_kept_and_short_prose_is_not():
    text = "Long-term debt 32,366 7,469\nTotal assets 99,000 88,000\nSee the notes.\nDebt\nWe issued notes. " + "x" * 50
    parts = filing.excerpts(text, ["long-term debt", "debt", "see the notes"])
    assert "Long-term debt 32,366 7,469" in parts and "See the notes." not in parts and "Debt" not in parts
    real = filing.excerpts(filing_text("NVDA")["text"], ["long-term debt"], max_chars=3000)
    assert "Long-term debt 32,366 7,469" in real
