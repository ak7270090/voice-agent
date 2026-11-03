"""The embedding model, chosen by a LangChain model string (provider-agnostic)."""

from typing import Annotated

from fastapi import Depends, Request
from langchain.embeddings import init_embeddings
from langchain_core.embeddings import Embeddings

from studio_backend.config import Settings


def create_embeddings(settings: Settings) -> Embeddings:
    return init_embeddings(settings.embedding_model)


def get_embeddings(request: Request) -> Embeddings:
    return request.app.state.embeddings


EmbeddingsDep = Annotated[Embeddings, Depends(get_embeddings)]
