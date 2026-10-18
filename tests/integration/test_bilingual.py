"""Real-service checks with synthetic German university passages, without provider calls."""

import os

import httpx
import pytest

from scripts.demo import build_pdf

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="Set RUN_INTEGRATION=1 with the live stack running"
)


def test_english_and_german_questions_find_specific_german_instructions():
    # Keep evidence separate from a plausible but wrong generic support contact.
    passages = [
        (
            "Synthetic KUSSS prerequisite instructions",
            (
                "Eine positive Beurteilung einer vorausgesetzten Lehrveranstaltung fehlt in KUSSS. "
                "Wenden Sie sich an das zuständige Institut oder die LVA-Leitung. "
                "Eine im System hinterlegte vorläufige Beurteilung genügt. "
                "Die Voraussetzungsprüfung berücksichtigt nur eingegebene Beurteilungen."
            ),
        ),
        (
            "Synthetic KUSSS exam search instructions",
            (
                "Sie werden in der Lehrveranstaltung nicht als Teilnehmer geführt. "
                "Verwenden Sie die Prüfungssuche im Menüpunkt Prüfungen. Dort können Sie "
                "nach der LVA-Nummer oder dem Titel suchen. Alle verfügbaren Semester "
                "werden durchsucht. Die Suche ist auch ohne Teilnehmerstatus möglich."
            ),
        ),
        (
            "Synthetic KUSSS general support",
            (
                "Allgemeine technische Hilfe für KUSSS: Kontaktieren Sie den Support. "
                "Diese Seite enthält keine Anleitung für fehlende Beurteilungen oder die Prüfungssuche."
            ),
        ),
    ]
    with httpx.Client(
        base_url=os.getenv("TEST_API_URL", "http://localhost:8000"), timeout=180
    ) as api:
        document_ids = []
        for index, (title, content) in enumerate(passages):
            response = api.post(
                "/documents",
                data={"title": title, "visibility": "public"},
                files={
                    "file": (f"synthetic-kusss-{index}.pdf", build_pdf(content), "application/pdf")
                },
            )
            response.raise_for_status()
            document_ids.append(response.json()["document_id"])
        cases = [
            (
                "whom should I contact if a passed prerequisite grade has not yet been entered in KUSSS?",
                0,
                "Institut",
            ),
            ("Who can enter my missing course assessment in KUSSS?", 0, "Institut"),
            ("An wen wende ich mich bei einer fehlenden Beurteilung in KUSSS?", 0, "Institut"),
            (
                "how can I find an exam when I am not listed as a participant in the course?",
                1,
                "Prüfungssuche",
            ),
            (
                "Can I search for examinations without being a course participant?",
                1,
                "Prüfungssuche",
            ),
            ("Wie finde ich eine Prüfung ohne Teilnehmerstatus?", 1, "Prüfungssuche"),
        ]
        for question, expected, evidence in cases:
            response = api.post("/search/retrieval", json={"query": question})
            response.raise_for_status()
            sources = response.json()["sources"]
            assert any(
                s["document_id"] == document_ids[expected] and evidence in s["excerpt"]
                for s in sources
            ), (question, sources)
