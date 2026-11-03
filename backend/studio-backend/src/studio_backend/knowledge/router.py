from fastapi import APIRouter, HTTPException, UploadFile, status

from studio_backend.agents.service import AgentNotFoundError, get_agent
from studio_backend.config import SettingsDep
from studio_backend.database import SessionDep
from studio_backend.internal_auth import RuntimeAuthDep
from studio_backend.jobs import JobQueueDep
from studio_backend.knowledge import service
from studio_backend.knowledge.embeddings import EmbeddingsDep
from studio_backend.knowledge.schemas import (
    DocumentFromUrl,
    DocumentRead,
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    SearchHit,
    SearchRequest,
)
from studio_backend.knowledge.search import search_knowledge
from studio_backend.knowledge.storage import FileStoreDep

router = APIRouter(prefix="/knowledge-bases", tags=["knowledge"])
runtime_router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[RuntimeAuthDep])


def not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


@router.get("")
async def list_knowledge_bases(session: SessionDep) -> list[KnowledgeBaseRead]:
    return await service.list_knowledge_bases(session)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KnowledgeBaseCreate, session: SessionDep
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(await service.create_knowledge_base(session, body))


@router.delete("/{knowledge_base_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    knowledge_base_id: str, session: SessionDep, store: FileStoreDep
) -> None:
    try:
        await service.delete_knowledge_base(session, store, knowledge_base_id)
    except service.KnowledgeBaseNotFoundError as error:
        raise not_found(f"knowledge base {knowledge_base_id}") from error


@router.get("/{knowledge_base_id}/documents")
async def list_documents(knowledge_base_id: str, session: SessionDep) -> list[DocumentRead]:
    documents = await service.list_documents(session, knowledge_base_id)
    return [DocumentRead.model_validate(document) for document in documents]


@router.post("/{knowledge_base_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    knowledge_base_id: str,
    file: UploadFile,
    session: SessionDep,
    store: FileStoreDep,
    queue: JobQueueDep,
    settings: SettingsDep,
) -> DocumentRead:
    """Stores the file and queues it; the document turns `ready` once chunks are embedded."""
    file_name = file.filename or "upload"
    try:
        service.check_supported(file_name)
    except service.UnsupportedFileError as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from error
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"files up to {settings.max_upload_bytes // (1024 * 1024)} MB",
        )
    try:
        document = await service.add_uploaded_document(
            session,
            store,
            queue,
            knowledge_base_id,
            file_name,
            file.content_type or "application/octet-stream",
            data,
        )
    except service.KnowledgeBaseNotFoundError as error:
        raise not_found(f"knowledge base {knowledge_base_id}") from error
    return DocumentRead.model_validate(document)


@router.post("/{knowledge_base_id}/documents/from-url", status_code=status.HTTP_202_ACCEPTED)
async def add_url_document(
    knowledge_base_id: str, body: DocumentFromUrl, session: SessionDep, queue: JobQueueDep
) -> DocumentRead:
    try:
        document = await service.add_url_document(session, queue, knowledge_base_id, str(body.url))
    except service.KnowledgeBaseNotFoundError as error:
        raise not_found(f"knowledge base {knowledge_base_id}") from error
    return DocumentRead.model_validate(document)


@router.delete(
    "/{knowledge_base_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_document(
    knowledge_base_id: str, document_id: str, session: SessionDep, store: FileStoreDep
) -> None:
    try:
        await service.delete_document(session, store, knowledge_base_id, document_id)
    except service.DocumentNotFoundError as error:
        raise not_found(f"document {document_id}") from error


@router.post("/{knowledge_base_id}/search")
async def search(
    knowledge_base_id: str,
    body: SearchRequest,
    session: SessionDep,
    embeddings: EmbeddingsDep,
    settings: SettingsDep,
) -> list[SearchHit]:
    """What an agent would retrieve for this question (the console's "try a question")."""
    return await search_knowledge(
        session,
        embeddings,
        [knowledge_base_id],
        body.query,
        top_k=body.top_k or settings.knowledge_top_k,
        candidate_count=settings.knowledge_candidate_count,
        keyword_weight=settings.knowledge_keyword_weight,
    )


@runtime_router.post("/agents/{agent_id}/knowledge-search")
async def search_for_agent(
    agent_id: str,
    body: SearchRequest,
    session: SessionDep,
    embeddings: EmbeddingsDep,
    settings: SettingsDep,
) -> list[SearchHit]:
    """Searches every knowledge base attached to the agent."""
    try:
        agent = await get_agent(session, agent_id)
    except AgentNotFoundError as error:
        raise not_found(f"agent {agent_id}") from error
    return await search_knowledge(
        session,
        embeddings,
        agent.knowledge_base_ids,
        body.query,
        top_k=body.top_k or settings.knowledge_top_k,
        candidate_count=settings.knowledge_candidate_count,
        keyword_weight=settings.knowledge_keyword_weight,
    )
