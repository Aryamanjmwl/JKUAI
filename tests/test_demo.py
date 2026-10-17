from app.services.ingestion import parse_pdf

from scripts.demo import FIXTURES, build_pdf


def test_fixture_pdfs_are_deterministic_and_extractable():
    for fixture in FIXTURES:
        content = build_pdf(fixture["text"])
        assert content == build_pdf(fixture["text"])
        pages = parse_pdf(content)
        assert len(pages) == 1
        assert " ".join(pages[0].text.split()) == fixture["text"]


def test_cli_explains_how_to_enable_roles_before_uploading(monkeypatch, capsys):
    import sys
    from unittest.mock import Mock, patch

    import pytest

    from scripts.demo import main

    client = Mock()
    client.get.return_value.json.return_value = {"status": "ready", "demo_roles_enabled": False}
    monkeypatch.setattr(sys, "argv", ["demo.py", "--check"])
    with patch("scripts.demo.httpx.Client") as factory:
        factory.return_value.__enter__.return_value = client
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 2
    assert "ENABLE_DEMO_ROLES=true" in capsys.readouterr().err
    client.post.assert_not_called()
