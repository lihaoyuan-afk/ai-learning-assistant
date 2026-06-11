from openai import OpenAI

from app.core.config import settings

_client: OpenAI | None = None
_BATCH_SIZE = 20  # Ollama processes embeddings sequentially; batching avoids huge single requests


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.embedding_api_key or settings.openai_api_key or "ollama",
            base_url=settings.embedding_base_url or settings.openai_base_url,
        )
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _get_client()
    results: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        response = client.embeddings.create(
            input=batch,
            model=settings.openai_embedding_model,
        )
        results.extend(item.embedding for item in response.data)
    return results


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
