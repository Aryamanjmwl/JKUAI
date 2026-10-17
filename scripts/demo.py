"""Seed reproducible, explicitly fictional university PDFs and check the live pipeline.

Run against a local instance with ENABLE_DEMO_ROLES=true. No OpenAI key is used.
"""

import argparse
import io
import json
import textwrap
from pathlib import Path

import httpx
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

FIXTURES = [
    {
        "file_name": "demo-course-guide.pdf",
        "title": "Demo University - Course Guide (fictional)",
        "visibility": "public",
        "allowed_groups": "",
        "text": "FICTIONAL DEMO DATA - not official university guidance. "
        "Advanced Machine Learning (AML-401) requires Introduction to Machine Learning "
        "and Linear Algebra. The course is worth 6 ECTS credits. Students must complete "
        "both prerequisite courses before enrolling in Advanced Machine Learning.",
    },
    {
        "file_name": "demo-exam-regulations.pdf",
        "title": "Demo University - Exam Regulations (fictional)",
        "visibility": "public",
        "allowed_groups": "",
        "text": "FICTIONAL DEMO DATA - not official university guidance. "
        "A student who misses an exam because of illness must notify the examination "
        "office within three working days and provide a medical certificate. "
        "The bachelor's programme requires 180 ECTS credits, including a 12 ECTS thesis.",
    },
    {
        "file_name": "demo-staff-operations.pdf",
        "title": "Demo University - Staff Operations (fictional, restricted)",
        "visibility": "restricted",
        "allowed_groups": "staff",
        "text": "FICTIONAL DEMO DATA - STAFF ONLY. The EXAM-OPS-42 procedure requires "
        "staff to submit exam incident reports to the internal review board within "
        "24 hours. The internal routing code is ORCHID-742. Students and public "
        "visitors must not receive this internal procedure or routing code.",
    },
]


def build_pdf(text: str) -> bytes:
    """Create a small text PDF using pypdf, keeping the seed independent of downloads."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    commands = ["BT /F1 11 Tf 50 740 Td 15 TL"]
    for line in textwrap.wrap(text, width=80):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj T*")
    commands.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def seed(client: httpx.Client, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    documents = {}
    for fixture in FIXTURES:
        content = build_pdf(fixture["text"])
        (output / fixture["file_name"]).write_bytes(content)
        response = client.post(
            "/documents",
            headers={"X-User-Groups": "staff"},
            data={key: fixture[key] for key in ("title", "visibility", "allowed_groups")},
            files={"file": (fixture["file_name"], content, "application/pdf")},
        )
        response.raise_for_status()
        documents[fixture["file_name"]] = response.json()["document_id"]
    manifest = {"documents": documents, "fictional": True}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def check(client: httpx.Client, manifest: dict) -> dict:
    documents = manifest["documents"]
    restricted = documents["demo-staff-operations.pdf"]
    cases = [
        ("What do I need before taking Advanced Machine Learning?", "", "demo-course-guide.pdf"),
        (
            "What happens if I miss an exam because of illness?",
            "students",
            "demo-exam-regulations.pdf",
        ),
        ("How many ECTS credits do I need to graduate?", "", "demo-exam-regulations.pdf"),
        ("What is the EXAM-OPS-42 internal routing code?", "staff", "demo-staff-operations.pdf"),
    ]
    checked = []
    for query, group, expected in cases:
        response = client.post(
            "/search/retrieval", json={"query": query}, headers={"X-User-Groups": group}
        )
        response.raise_for_status()
        result = response.json()
        ids = {source["document_id"] for source in result["sources"]}
        if documents[expected] not in ids:
            raise RuntimeError(f"Expected fixture missing for role {group or 'public'}: {expected}")
        if group != "staff" and restricted in ids:
            raise RuntimeError("Restricted document leaked into public/student retrieval")
        checked.append(
            {"question": query, "role": group or "public", "latency_ms": result["latency_ms"]}
        )
    for group in ("", "students", "admissions"):
        response = client.post(
            "/search/retrieval",
            json={"query": "EXAM-OPS-42 ORCHID-742"},
            headers={"X-User-Groups": group},
        )
        response.raise_for_status()
        result = response.json()
        if restricted in {
            source["document_id"] for source in result["sources"]
        } or "ORCHID-742" in json.dumps(result):
            raise RuntimeError(f"Restricted content leaked to {group or 'public'}")
    return {
        "status": "passed",
        "retrieval_cases": checked,
        "denied_roles": ["public", "students", "admissions"],
        "scope": "Synthetic fixture smoke test; not a retrieval quality benchmark or LLM evaluation",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--output", type=Path, default=Path("data/demo-output"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=180) as client:
        manifest = seed(client, args.output)
        report = check(client, manifest) if args.check else manifest
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
