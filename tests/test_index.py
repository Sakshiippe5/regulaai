import re
import zlib

import numpy as np

from regulaai.rag.chunking import PolicyChunk
from regulaai.rag.index import PolicyIndex


class FakeEmbedder:
    """Word-hashing stand-in: texts sharing words get similar vectors."""

    DIM = 128

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.DIM, dtype="float32")
        for word in re.findall(r"[a-z]+", text.lower()):
            v[zlib.crc32(word.encode()) % self.DIM] += 1
        return v

    def embed_documents(self, texts):
        return np.array([self._vec(t) for t in texts])

    def embed_query(self, text):
        return self._vec(text)


def make_chunks():
    return [
        PolicyChunk(id="a:1", source="a.md", section="Vulnerability",
                    text="A vulnerability assessment is done once a year."),
        PolicyChunk(id="b:1", source="b.md", section="Incidents",
                    text="Incidents are reported to the CISO within 2 hours."),
    ]


def test_search_returns_most_relevant_chunk_first():
    index = PolicyIndex(FakeEmbedder())
    index.build(make_chunks())
    hits = index.search("how often is the vulnerability assessment done", k=2)
    assert hits[0].chunk.id == "a:1"
    assert hits[0].score > hits[1].score


def test_save_and_load_roundtrip(tmp_path):
    index = PolicyIndex(FakeEmbedder())
    index.build(make_chunks())
    index.save(tmp_path)
    loaded = PolicyIndex.load(tmp_path, FakeEmbedder())
    assert loaded.search("incidents reported to CISO", k=1)[0].chunk.id == "b:1"