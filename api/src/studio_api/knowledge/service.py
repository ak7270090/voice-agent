from pathlib import PurePath

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.jobs import JobQueue
from studio_api.knowledge.constants import (
    DOCUMENT_KEY_PREFIX,
    INGEST_JOB_NAME,
    SUPPORTED_EXTENSIONS,
    UPLOAD_SOURCE,
    URL_SOURCE,
)
from studio_api.knowledge.models import Document, KnowledgeBase
from studio_api.knowledge.schemas import KnowledgeBaseCreate, KnowledgeBaseRead
from studio_api.storage import FileStore


class KnowledgeBaseNotFoundError(LookupError):
    pass


class DocumentNotFoundError(LookupError):
    pass


class UnsupportedFileError(ValueError):
    pass


async def create_knowledge_base(
    session: AsyncSession, fields: KnowledgeBaseCreate
) -> KnowledgeBase:
    knowledge_base = KnowledgeBase(**fields.model_dump())
    session.add(knowledge_base)
    await session.commit()
    return knowledge_base


async def get_knowledge_base(session: AsyncSession, knowledge_base_id: str) -> KnowledgeBase:
    knowledge_base = await session.get(KnowledgeBase, knowledge_base_id)
    if knowledge_base is None:
        raise KnowledgeBaseNotFoundError(knowledge_base_id)
    return knowledge_base


async def list_knowledge_bases(session: AsyncSession) -> list[KnowledgeBaseRead]:
    """With document and chunk counts, in one query."""
    document_count = func.count(Document.id.distinct())
    chunk_count = func.coalesce(func.sum(Document.chunk_count), 0)
    rows = await session.execute(
        select(KnowledgeBase, document_count, chunk_count)
        .outerjoin(Document, Document.knowledge_base_id == KnowledgeBase.id)
        .group_by(KnowledgeBase.id)
        .order_by(KnowledgeBase.created_at.desc())
    )
    return [
        KnowledgeBaseRead.model_validate(knowledge_base).model_copy(
            update={"document_count": documents, "chunk_count": chunks}
        )
        for knowledge_base, documents, chunks in rows
    ]


async def delete_knowledge_base(
    session: AsyncSession, store: FileStore, knowledge_base_id: str
) -> None:
    knowledge_base = await get_knowledge_base(session, knowledge_base_id)
    for document in await list_documents(session, knowledge_base_id):
        if document.storage_key:
            await store.delete(document.storage_key)
    await session.delete(knowledge_base)
    await session.commit()


async def list_documents(session: AsyncSession, knowledge_base_id: str) -> list[Document]:
    result = await session.scalars(
        select(Document)
        .where(Document.knowledge_base_id == knowledge_base_id)
        .order_by(Document.created_at.desc())
    )
    return list(result)


def check_supported(file_name: str) -> None:
    if PurePath(file_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"{file_name}: supported types are {', '.join(SUPPORTED_EXTENSIONS)}"
        )


async def add_uploaded_document(
    session: AsyncSession,
    store: FileStore,
    queue: JobQueue,
    knowledge_base_id: str,
    file_name: str,
    content_type: str,
    data: bytes,
) -> Document:
    await get_knowledge_base(session, knowledge_base_id)
    document = Document(
        knowledge_base_id=knowledge_base_id,
        name=file_name,
        source=UPLOAD_SOURCE,
        content_type=content_type,
        size_bytes=len(data),
    )
    session.add(document)
    await session.flush()
    document.storage_key = f"{DOCUMENT_KEY_PREFIX}/{document.id}/{PurePath(file_name).name}"
    await store.put(document.storage_key, data, content_type)
    await session.commit()
    await queue.enqueue(INGEST_JOB_NAME, document.id)
    return document


async def add_url_document(
    session: AsyncSession, queue: JobQueue, knowledge_base_id: str, url: str
) -> Document:
    await get_knowledge_base(session, knowledge_base_id)
    document = Document(
        knowledge_base_id=knowledge_base_id, name=url, source=URL_SOURCE, source_url=url
    )
    session.add(document)
    await session.commit()
    await queue.enqueue(INGEST_JOB_NAME, document.id)
    return document


async def delete_document(
    session: AsyncSession, store: FileStore, knowledge_base_id: str, document_id: str
) -> None:
    document = await session.get(Document, document_id)
    if document is None or document.knowledge_base_id != knowledge_base_id:
        raise DocumentNotFoundError(document_id)
    if document.storage_key:
        await store.delete(document.storage_key)
    await session.delete(document)
    await session.commit()
