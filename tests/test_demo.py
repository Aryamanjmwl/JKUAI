from app.services.ingestion import parse_pdf

from scripts.demo import FIXTURES, build_pdf


def test_fixture_pdfs_are_deterministic_and_extractable():
    for fixture in FIXTURES:
        content = build_pdf(fixture["text"])
        assert content == build_pdf(fixture["text"])
        pages = parse_pdf(content)
        assert len(pages) == 1
        assert " ".join(pages[0].text.split()) == fixture["text"]
