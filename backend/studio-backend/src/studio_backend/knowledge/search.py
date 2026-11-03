"""Finding the chunks that answer a question: pgvector's nearest chunks, re-ranked by
cosine similarity plus `keyword_weight` × the share of the question's words each chunk contains.

The keyword part helps when chunks of one document embed alike (in clinic-voice-agent, every
"timings and location" chunk looked the same, so "address" alone missed the address chunk).
"""

import re
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_backend.knowledge.constants import STOP_WORDS
from studio_backend.knowledge.models import Chunk, Document
from studio_backend.knowledge.schemas import SearchHit

WORD = re.compile(r"\w+")


@dataclass(frozen=True)
class Candidate:
    document_id: str
    document_name: str
    text: str
    similarity: float


def content_words(text: str) -> set[str]:
    return {word for word in WORD.findall(text.lower()) if word not in STOP_WORDS}


def rerank(
    query: str, candidates: list[Candidate], keyword_weight: float, top_k: int
) -> list[SearchHit]:
    asked = content_words(query)
    hits = []
    for candidate in candidates:
        overlap = len(asked & content_words(candidate.text)) / max(len(asked), 1)
        hits.append(
            SearchHit(
                document_id=candidate.document_id,
                document_name=candidate.document_name,
                text=candidate.text,
                score=round(candidate.similarity + keyword_weight * overlap, 4),
                similarity=round(candidate.similarity, 4),
                keyword_overlap=round(overlap, 4),
            )
        )
    return sorted(hits, key=lambda hit: hit.score, reverse=True)[:top_k]


async def search_knowledge(
    session: AsyncSession,
    embeddings: Embeddings,
    knowledge_base_ids: list[str],
    query: str,
    *,
    top_k: int,
    candidate_count: int,
    keyword_weight: float,
) -> list[SearchHit]:
    if not knowledge_base_ids:
        return []
    distance = Chunk.embedding.cosine_distance(await embeddings.aembed_query(query))
    rows = await session.execute(
        select(Chunk.document_id, Document.name, Chunk.text, distance)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.knowledge_base_id.in_(knowledge_base_ids))
        .order_by(distance)
        .limit(candidate_count)
    )
    candidates = [
        Candidate(document_id, name, text, 1 - float(cosine_distance))
        for document_id, name, text, cosine_distance in rows
    ]
    return rerank(query, candidates, keyword_weight, top_k)
