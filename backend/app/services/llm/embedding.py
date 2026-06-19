import asyncio
from functools import lru_cache
from loguru import logger
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.services.llm.base import EmbeddingClient


class OpenAIEmbeddingClient(EmbeddingClient):
    def __init__(self):
        s = get_settings()
        self._client = AsyncOpenAI(
            api_key=s.effective_embedding_api_key,
            base_url=s.effective_embedding_base_url,
        )
        self._model = s.openai_embedding_model

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            input=text, model=self._model
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(
            input=texts, model=self._model
        )
        return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]


class VoyageEmbeddingClient(EmbeddingClient):
    def __init__(self):
        s = get_settings()
        import voyageai
        self._client = voyageai.AsyncClient(api_key=s.voyage_api_key)
        self._model = s.voyage_embedding_model

    async def embed(self, text: str) -> list[float]:
        result = await self._client.embed([text], model=self._model)
        return result.embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        result = await self._client.embed(texts, model=self._model)
        return result.embeddings


class LocalEmbeddingClient(EmbeddingClient):
    def __init__(self):
        s = get_settings()
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(s.local_embedding_model)

    async def embed(self, text: str) -> list[float]:
        return await asyncio.to_thread(
            lambda: self._model.encode(text).tolist()
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await asyncio.to_thread(
            lambda: self._model.encode(texts).tolist()
        )


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    provider = get_settings().embedding_provider
    logger.info(f"Embedding provider: {provider}")
    if provider == "voyage":
        return VoyageEmbeddingClient()
    if provider == "local":
        return LocalEmbeddingClient()
    return OpenAIEmbeddingClient()
