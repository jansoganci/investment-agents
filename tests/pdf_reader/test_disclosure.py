from agents.pdf_reader.disclosure import (
    find_start,
    is_caps_heading,
    is_disclosure_heading,
    normalize,
    sections_on_page,
)

BERNSTEIN = (
    "See the Disclosure Appendix of this report for important disclosures "
    "and analyst certifications."
)
JPM = (
    "See page 13 for analyst certification and important disclosures, "
    "including non-US analyst disclosures."
)
VALUATION_LINK = (
    "This research publication covers six or more companies. For valuation methodology "
    "and other company disclosures: Please visit: "
    "https://bernstein-autonomous.bluematrix.com/sellside/Disclosures.action. "
    "Or, you can also write to the Director of Compliance, Bernstein Institutional "
    "Services LLC, 245 Park Avenue, New York, NY 10167."
)
RISKS_LINK = (
    "This research publication covers six or more companies. For risks and other "
    "company disclosures: Please visit: "
    "https://bernstein-autonomous.bluematrix.com/sellside/Disclosures.action. "
    "Or, you can also write to the Director of Compliance, Bernstein Institutional "
    "Services LLC, 245 Park Avenue, New York, NY 10167."
)


def _words(n: int) -> str:
    return " ".join(f"word{i}" for i in range(n))


def test_normalize():
    assert normalize("  IMPORTANT   DISCLOSURES: ") == "important disclosures"


def test_headings_alone_are_headings():
    for line in (
        "DISCLOSURE APPENDIX",
        "Important Disclosures",
        "Analyst Certification",
        "Required Disclosures",
        "Important Disclosures:",
    ):
        assert is_disclosure_heading(line) is True


def test_bernstein_cover_sentence_is_not_a_start():
    assert is_disclosure_heading(BERNSTEIN) is False


def test_jpm_cover_sentence_is_not_a_start():
    assert is_disclosure_heading(JPM) is False


def test_appendix_alone_is_not_a_start():
    for line in (
        "Appendix",
        "APPENDIX – FINANCIAL FORECASTS",
        "Important disclosures follow",
    ):
        assert is_disclosure_heading(line) is False


def test_bookmark_first():
    found = find_start([("Important Disclosures", 5)], [])
    assert found["page"] == 5
    assert found["found_by"] == "bookmark"


def test_bookmark_on_page_one_ignored():
    assert find_start([("Important Disclosures", 1)], []) is None


def test_heading_after_sentences():
    pages = [
        [BERNSTEIN],
        [JPM],
        ["APPENDIX – FINANCIAL FORECASTS"],
        ["Disclosure Appendix"],
    ]
    found = find_start([], pages)
    assert found["page"] == 4
    assert found["found_by"] == "heading"
    assert found["text"] == "Disclosure Appendix"


def test_ratings_table_fallback():
    pages = [[], [], ["Distribution of Ratings/IB Services"]]
    found = find_start([], pages)
    assert found["page"] == 3
    assert found["found_by"] == "ratings_table"


def test_not_found():
    assert find_start([], [["Nothing here"], ["Still nothing"]]) is None


def test_sections_found():
    lines = [
        "SK hynix: Valuation Methodology",
        _words(30),
        "Risks",
        _words(30),
    ]
    assert sections_on_page(lines) == [
        {"section": "valuation", "line": 0, "only_link": False},
        {"section": "risks", "line": 2, "only_link": False},
    ]


def test_risks_only_link():
    found = sections_on_page(["Risks", "Please see www.example.com/risks for risks."])
    assert found == [{"section": "risks", "line": 0, "only_link": True}]


def test_valuation_only_link():
    found = sections_on_page(["Valuation methodology", "See https://example.com/valuation"])
    assert found[0]["only_link"] is True


def test_link_with_real_text_not_only_link():
    found = sections_on_page(["Risks", "See https://example.com/note " + _words(70)])
    assert found[0]["only_link"] is False


def test_risk_heading_forms():
    assert [row["section"] for row in sections_on_page(["Key Risks"])] == ["risks"]
    assert [row["section"] for row in sections_on_page(["Risks to our rating"])] == ["risks"]
    assert [row["section"] for row in sections_on_page(["Investment risks"])] == ["risks"]
    assert sections_on_page(["Risk factors include a weaker cycle."]) == []
    both = sections_on_page(["Valuation methodology and risks"])
    assert [row["section"] for row in both] == ["valuation", "risks"]
    assert both[0]["line"] == 0 and both[1]["line"] == 0


def test_bernstein_link_and_address_only_link():
    lines = [
        "VALUATION METHODOLOGY",
        VALUATION_LINK,
        "RISKS",
        RISKS_LINK,
        "RATINGS DEFINITIONS, BENCHMARKS AND DISTRIBUTION",
        _words(80),
    ]
    assert sections_on_page(lines) == [
        {"section": "valuation", "line": 0, "only_link": True},
        {"section": "risks", "line": 2, "only_link": True},
    ]


def test_caps_heading():
    assert is_caps_heading("RATINGS DEFINITIONS, BENCHMARKS AND DISTRIBUTION") is True
    assert is_caps_heading("NY 10167.") is False
    assert is_caps_heading("Risks") is False
    assert is_caps_heading("This is a sentence.") is False
