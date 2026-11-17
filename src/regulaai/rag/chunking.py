import re
from pathlib import Path

from pydantic import BaseModel


class PolicyChunk(BaseModel):
    id: str  # e.g. "information_security_policy:2"
    source: str  # file name, used for citations
    section: str  # heading text
    text: str


def chunk_policy(path: str | Path) -> list[PolicyChunk]:
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    parts = re.split(r"^## ", content, flags=re.MULTILINE)
    chunks = []
    for n, part in enumerate(parts[1:], start=1):  # parts[0] is the title block
        heading, _, body = part.partition("\n")
        chunks.append(
            PolicyChunk(
                id=f"{path.stem}:{n}",
                source=path.name,
                section=heading.strip(),
                text=body.strip(),
            )
        )
    return chunks


def load_policies(directory: str | Path) -> list[PolicyChunk]:
    return [c for p in sorted(Path(directory).glob("*.md")) for c in chunk_policy(p)]