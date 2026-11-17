from pathlib import Path

import pymupdf
from pydantic import BaseModel


class Page(BaseModel):
    number: int  # 1-based, matches what a human sees in a PDF viewer
    text: str


class ParsedDocument(BaseModel):
    source: str  # file name, used later for citations
    pages: list[Page]

    @property
    def full_text(self) -> str:
        """All pages joined, each prefixed with its page number."""
        return "\n\n".join(f"[Page {p.number}]\n{p.text}" for p in self.pages)


def read_pdf(path: str | Path) -> ParsedDocument:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    pages = []
    with pymupdf.open(path) as doc:
        for number, page in enumerate(doc, start=1):
            pages.append(Page(number=number, text=page.get_text().strip()))
    return ParsedDocument(source=path.name, pages=pages)