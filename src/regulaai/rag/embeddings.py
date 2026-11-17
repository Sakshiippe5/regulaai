import numpy as np
from fastembed import TextEmbedding


class FastEmbedder:
    """Local embedding model. Runs on your CPU, no API key, no data leaves your machine."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return np.array(list(self._model.embed(texts)))

    def embed_query(self, text: str) -> np.ndarray:
        # bge models treat queries slightly differently from documents
        return np.array(next(iter(self._model.query_embed(text))))