from groq import Groq
from pydantic import BaseModel, ValidationError

from regulaai.config import settings


class LLMClient:
    def __init__(self) -> None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing. Check your .env file.")
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        return response.choices[0].message.content

    def complete_structured[T: BaseModel](self, system: str, user: str, schema: type[T]) -> T:
        """Ask for JSON and validate it against a Pydantic model."""
        json_system = (
            f"{system}\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"{schema.model_json_schema()}"
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": json_system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        try:
            return schema.model_validate_json(raw)
        except ValidationError as e:
            raise ValueError(f"LLM returned invalid structure: {e}") from e