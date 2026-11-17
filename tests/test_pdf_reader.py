import pymupdf
import pytest

from regulaai.ingestion.pdf_reader import read_pdf


@pytest.fixture
def two_page_pdf(tmp_path):
    path = tmp_path / "test.pdf"
    doc = pymupdf.open()
    for text in ("First page text", "Second page text"):
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(path)
    return path


def test_reads_all_pages_with_numbers(two_page_pdf):
    parsed = read_pdf(two_page_pdf)
    assert [p.number for p in parsed.pages] == [1, 2]
    assert "Second page" in parsed.pages[1].text


def test_full_text_has_page_markers(two_page_pdf):
    assert "[Page 2]" in read_pdf(two_page_pdf).full_text


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        read_pdf("does_not_exist.pdf")