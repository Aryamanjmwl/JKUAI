import io

from app.chunking import chunk_pages
from app.services.pdf import parse_pdf, table_blocks
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def ruled_pdf():
    """Two real PDF columns; blank cells encode distinct winter/summer associations."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    commands = []
    for x in [50, 300, 400, 500]:
        commands.append(f"{x} 600 m {x} 720 l S")
    for y in [600, 640, 680, 720]:
        commands.append(f"50 {y} m 500 {y} l S")
    for x, y, text in [
        (60, 740, "Recommended study plan"),
        (60, 695, "Course"),
        (310, 695, "ECTS WS"),
        (410, 695, "ECTS SS"),
        (60, 655, "Winter-only course"),
        (310, 655, "3"),
        (60, 615, "Summer-only course"),
        (410, 615, "6"),
    ]:
        commands.append(f"BT /F1 11 Tf {x} {y} Td ({text}) Tj ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_ruled_pdf_preserves_blank_semester_cells_and_does_not_index_flattened_copy():
    blocks = parse_pdf(ruled_pdf())
    chunks = chunk_pages(blocks)
    table = next(c.content for c in chunks if "Winter-only course" in c.content)
    assert "Course: Winter-only course | ECTS WS / Wintersemester / winter semester: 3" in table
    assert "Course: Summer-only course | ECTS SS / Sommersemester / summer semester: 6" in table
    assert all(c.page_number == 1 for c in chunks)
    assert sum(c.content.count("Winter-only course") for c in chunks) == 1


def test_merged_semester_headers_stay_with_their_own_course_credit_pairs():
    blocks = table_blocks(
        [
            ["1. Semester (WS)", None, "2. Semester (SS)", None],
            ["Course", "ECTS", "Course", "ECTS"],
            ["Winter course", "3", "Summer course", "6"],
        ]
    )
    assert len(blocks) == 2
    assert "Winter course; ECTS: 3" in blocks[0]
    assert "winter semester" in blocks[0]
    assert "first semester / erstes Semester" in blocks[0]
    assert "Summer course" not in blocks[0]
    assert "Summer course; ECTS: 6" in blocks[1]
    assert "summer semester" in blocks[1]
    assert "Winter course" not in blocks[1]


def test_headerless_numeric_table_retains_its_first_data_row():
    text = " ".join(table_blocks([["Mandatory courses", "163.5"], ["Electives", "9"]]))
    assert "Column 1: Mandatory courses | Column 2: 163.5" in text
    assert "Column 1: Electives | Column 2: 9" in text


def test_single_row_table_keeps_its_text():
    assert table_blocks([["Thesis", "25 ECTS"]]) == ["Thesis | 25 ECTS"]
