"""shared/bulletin/check: numbers read the English and the Turkish way, the source check, the translation check, the style guard."""

import pytest

from shared.bulletin import check


@pytest.mark.parametrize("token, values", [
    ("7.743,98", {7743.98}), ("7,743.98", {7743.98}), ("104,6", {104.6}), ("3.6", {3.6}), ("78", {78.0}),
    ("1.000", {1000.0, 1.0}), ("1,000", {1000.0, 1.0}), ("1,234,567", {1234567.0}), ("1.234.567", {1234567.0}),
    ("0.123", {0.123}), ("12,345", {12345.0, 12.345}), ("2.5", {2.5})])
def test_a_token_stands_for_the_values_it_can_mean(token, values):
    assert check.candidates(token) == frozenset(values)


def test_numbers_are_found_with_signs_units_and_words_around_them():
    tokens = [t for t, _v in check.numbers("Brent rose 3,1% to $115.20; S&P 500 at 7.743,98; Q3 and GPT-6; 08:15")]
    assert tokens == ["3,1", "115.20", "500", "7.743,98", "6"]       # Q3 is a name and 08:15 a time, not numbers


def test_a_number_the_sources_have_passes_in_either_notation():
    sources = ["Ciro 104,6 trilyon won, beklenti 98,6 trilyon wondu. Faaliyet kârı %7'den fazla aştı."]
    assert check.missing_in_sources("SK Hynix Q3 revenue 104.6 trillion won (expected 98.6), beating it by more than 7%.", sources) == []
    assert check.missing_in_sources("SK Hynix Q3 revenue 105.1 trillion won (expected 98.6).", sources) == ["105.1"]


def test_years_are_not_checked_but_other_numbers_are():
    assert check.missing_in_sources("Management sees a shortage until 2030.", ["No numbers here."]) == []
    assert check.missing_in_sources("Management sees 2031 HBM shortages in 12 months.", ["a text with 12 only"]) == []   # 2031 reads as a year
    assert check.missing_in_sources("Memory prices rose 40%.", ["a text with 14 only"]) == ["40"]


def test_a_number_may_come_from_any_cited_source():
    assert check.missing_in_sources("Brent 115 and WTI 101.", ["Brent topped 115", "WTI near 101"]) == []


def test_the_turkish_item_has_exactly_the_english_numbers():
    en = "Brent rose 3.1% to $115.20, WTI near $101 (2026)."
    assert check.same_numbers(en, "Brent %3,1 artarak 115,20 $'a yükseldi, WTI 101 $ civarında (2026).")
    assert not check.same_numbers(en, "Brent %3,1 artarak 115,20 $'a yükseldi, WTI 101 $ civarında.")           # a number left out
    assert not check.same_numbers(en, "Brent %3,1 artarak 115,20 $'a yükseldi, WTI 110 $ civarında (2026).")    # a number changed
    assert not check.same_numbers(en, "Brent %3,1 artarak 115,20 $'a yükseldi, WTI 101 $ (2026), 5 uçuş.")       # a number added
    assert check.same_numbers("No numbers.", "Rakam yok.")


def test_an_ordinal_is_a_word_not_a_number():
    assert check.same_numbers("SK Hynix Q3 revenue 104.6 trillion won (expected 98.6).",
                              "SK Hynix 3. çeyrek cirosu 104,6 trilyon won (beklenti 98,6).")
    assert check.same_numbers("The 3rd quarter and the 4th rate hike: 3.6%.", "3. çeyrek ve 4. faiz artırımı: %3,6.")
    assert not check.same_numbers("Revenue 104.6.", "Ciro 104,6. 5 yeni ürün.")        # a sentence that ends in a number is not an ordinal


def test_a_tenor_is_a_name_not_a_number():
    # seen in the first real draft: "2-year" was flagged although the 2-year yield was in the source ("2yr")
    item = "10-year Treasury yield rose to 5.036% from 5.020% and the 2-year fell to 4.702% from 4.770%."
    assert check.missing_in_sources(item, ["10yr 5.036% (5.020%), 2yr 4.702% (4.770%)"]) == []
    assert check.same_numbers(item, "10 yıllık Treasury getirisi %5,020'den %5,036'ya, 2 yıllık getiri %4,770'ten %4,702'ye.")
    assert check.missing_in_sources("Rates stay for 12 months.", ["Rates stay for 6 months."]) == ["12"]   # a plain count is still checked


def test_a_time_of_day_is_not_a_figure():
    # seen in the first scheduled bulletin: "TSİ 15:30" was flagged as the numbers 15 and 30
    assert check.missing_in_sources("US PCE data comes out at 15:30 Turkey time.", ["PCE is due today."]) == []
    assert check.same_numbers("PCE at 12:30 GMT.", "PCE TSİ 15:30'da.")
    assert check.missing_in_sources("Inflation was 3.6%.", ["Inflation was 3.2%."]) == ["3.6"]     # a decimal figure is still checked


@pytest.mark.parametrize("text, found", [
    ("Goldman upgraded NVDA to buy.", "upgraded"), ("Morgan Stanley set a price target of $200.", "price target"),
    ("You should buy the dip.", "you should"), ("Analysts expected revenue of 98.6 trillion won.", None),
    ("The bank cut its outlook.", None)])
def test_advice_ratings_and_targets_are_found(text, found):
    assert check.style_problem(text) == found
