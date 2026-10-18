"""Extract prose and ruled tables without flattening column relationships."""

import io
import re

import pdfplumber
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..chunking import TextPage


def _clean(value: str | None) -> str:
    return " ".join((value or "").split())


def _header(value: str | None) -> str:
    # Retain the original label while making common semester abbreviations searchable.
    value = _clean(value)
    ordinals = {
        "1": "first semester / erstes Semester",
        "2": "second semester / zweites Semester",
        "3": "third semester / drittes Semester",
        "4": "fourth semester / viertes Semester",
        "5": "fifth semester / fünftes Semester",
        "6": "sixth semester / sechstes Semester",
    }
    value = re.sub(
        r"\b([1-6])\.\s*Semester\b",
        lambda match: f"{match.group(0)} / {ordinals[match.group(1)]}",
        value,
    )
    value = re.sub(r"\bWS\b", "WS / Wintersemester / winter semester", value)
    return re.sub(r"\bSS\b", "SS / Sommersemester / summer semester", value)


def table_blocks(rows: list[list[str | None]]) -> list[str]:
    """Repeat column labels in each record; keep merged column groups together."""
    if not rows:
        return []
    if len(rows) == 1:
        return [" | ".join(_clean(cell) for cell in rows[0] if _clean(cell))]
    first = rows[0]
    # A merged top row followed by complete subheaders, e.g. semester -> course/ECTS.
    grouped = (
        None in first and bool(first[0]) and len(rows) > 2 and all(_clean(cell) for cell in rows[1])
    )
    if grouped:
        groups: list[tuple[str, list[int]]] = []
        for col, label in enumerate(first):
            if label is not None:
                groups.append((_clean(label), []))
            groups[-1][1].append(col)
        blocks = []
        for group, columns in groups:
            records = []
            for row in rows[2:]:
                fields = [
                    f"{_clean(rows[1][col])}: {_clean(row[col])}"
                    for col in columns
                    if col < len(row) and _clean(row[col])
                ]
                if fields:
                    records.append(f"{group} | " + "; ".join(fields))
            if records:
                blocks.append(_header(group) + "\n" + "\n".join(records))
        return blocks
    has_header = not any(re.fullmatch(r"[\d.,% +−-]+", _clean(cell)) for cell in first if cell)
    headers = [
        (_header(cell) if has_header else "") or f"Column {i + 1}" for i, cell in enumerate(first)
    ]
    records = [
        " | ".join(
            f"{headers[col]}: {_clean(cell)}"
            for col, cell in enumerate(row)
            if col < len(headers) and _clean(cell)
        )
        for row in (rows[1:] if has_header else rows)
        if any(_clean(cell) for cell in row)
    ]
    return ["\n".join(records)]


def parse_pdf(content: bytes) -> list[TextPage]:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported")
        blocks: list[TextPage] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for number, page in enumerate(pdf.pages, start=1):
                tables = page.find_tables()
                if not tables:
                    # Keep the existing prose extraction behavior for unruled pages.
                    blocks.append(TextPage(number, reader.pages[number - 1].extract_text() or ""))
                    continue
                # Remove table characters from prose so ambiguous flattened copies are not indexed.
                boxes = [table.bbox for table in tables]
                prose = (
                    page.filter(
                        lambda obj, boxes=boxes: (
                            not any(
                                x0 <= (obj.get("x0", 0) + obj.get("x1", 0)) / 2 <= x1
                                and top <= (obj.get("top", 0) + obj.get("bottom", 0)) / 2 <= bottom
                                for x0, top, x1, bottom in boxes
                            )
                        )
                    ).extract_text()
                    or ""
                )
                blocks.append(TextPage(number, prose))
                # Carry the page heading into table blocks, including recommended-plan qualifiers.
                table_top = min(t.bbox[1] for t in tables)
                heading = (
                    (page.crop((0, 0, page.width, table_top)).extract_text() or "")
                    if table_top > 0
                    else ""
                )
                heading = _clean(heading.split("\n")[0])[:200]
                heading = heading.replace(
                    "Empfohlener Studienverlauf",
                    "Empfohlener Studienverlauf / recommended study plan",
                )
                for table in tables:
                    for record in table_blocks(table.extract()):
                        blocks.append(TextPage(number, f"{heading}\n{record}"))
        return blocks
    except (PdfReadError, OSError, KeyError, TypeError) as exc:
        raise ValueError("The file could not be read as a PDF") from exc
