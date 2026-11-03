"""Turning a document into searchable chunks: read → Markdown → chunks → embeddings.

MarkItDown reads PDF, Word, PowerPoint, Excel, HTML and text into Markdown (MIT licence).
Scanned PDFs have no text layer and come out empty; Docling with OCR is the upgrade for those.
"""

import asyncio
import io
from pathlib import PurePath

from langchain_core.embeddings import Embeddings
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from markitdown import MarkItDown, StreamInfo
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from studio_backend.core.config import Settings
from studio_backend.knowledge.constants import (
    FAILED_STATUS,
    PROCESSING_STATUS,
    READY_STATUS,
    UPLOAD_SOURCE,
)
from studio_backend.knowledge.models import Chunk, Document
from studio_backend.knowledge.storage import FileStore


class EmptyDocumentError(ValueError):
    pass


def to_markdown(data: bytes, file_name: str) -> str:
    extension = PurePath(file_name).suffix.lower()
    result = MarkItDown().convert_stream(
        io.BytesIO(data), stream_info=StreamInfo(extension=extension)
    )
    return result.markdown


def url_to_markdown(url: str) -> str:
    return MarkItDown().convert_uri(url).markdown


def split_into_chunks(markdown: str, settings: Settings) -> list[str]:
    splitter = RecursiveCharacterTextSplitter.from_language(
        Language.MARKDOWN,
        chunk_size=settings.chunk_size_chars,
        chunk_overlap=settings.chunk_overlap_chars,
    )
    return [chunk.strip() for chunk in splitter.split_text(markdown) if chunk.strip()]


async def read_document_text(document: Document, store: FileStore) -> str:
    if document.source == UPLOAD_SOURCE:
        data = await store.get(document.storage_key)
        return await asyncio.to_thread(to_markdown, data, document.name)
    return await asyncio.to_thread(url_to_markdown, document.source_url)


async def ingest_document(
    session_factory: async_sessionmaker[AsyncSession],
    store: FileStore,
    embeddings: Embeddings,
    settings: Settings,
    document_id: str,
) -> None:
    """Replaces the document's chunks; marks it ready, or failed with the reason."""
    async with session_factory() as session:
        document = await session.get(Document, document_id)
        if document is None:
            return
        document.status = PROCESSING_STATUS
        document.error = None
        await session.commit()
        try:
            texts = split_into_chunks(await read_document_text(document, store), settings)
            if not texts:
                raise EmptyDocumentError("no text found (a scanned PDF needs OCR)")
            vectors = await embeddings.aembed_documents(texts)
            await session.execute(delete(Chunk).where(Chunk.document_id == document.id))
            session.add_all(
                Chunk(
                    document_id=document.id,
                    knowledge_base_id=document.knowledge_base_id,
                    position=position,
                    text=text,
                    embedding=vector,
                )
                for position, (text, vector) in enumerate(zip(texts, vectors, strict=True))
            )
            document.chunk_count = len(texts)
            document.status = READY_STATUS
        except Exception as error:  # the reason is shown in the console
            await session.rollback()
            document = await session.get(Document, document_id)
            document.status = FAILED_STATUS
            document.error = f"{type(error).__name__}: {error}"[:500]
        await session.commit()
