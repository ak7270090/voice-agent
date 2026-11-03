from fastapi import APIRouter, HTTPException, status

from studio_backend.agents.service import AgentNotFoundError
from studio_backend.database import SessionDep
from studio_backend.flows import service
from studio_backend.flows.schemas import Flow, FlowDraft, FlowVersionRead

router = APIRouter(prefix="/agents/{agent_id}/flow", tags=["flows"])


def agent_not_found(agent_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"agent {agent_id} not found")


@router.get("")
async def read_flow(agent_id: str, session: SessionDep) -> FlowDraft:
    try:
        return await service.get_draft(session, agent_id)
    except AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error


@router.put("")
async def save_flow(agent_id: str, flow: Flow, session: SessionDep) -> FlowDraft:
    try:
        return await service.save_draft(session, agent_id, flow)
    except AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error


@router.delete("")
async def remove_flow(agent_id: str, session: SessionDep) -> FlowDraft:
    """The agent goes back to prompt-only for test calls; the published flow stays until
    the next publish."""
    try:
        return await service.save_draft(session, agent_id, None)
    except AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error


@router.post("/publish")
async def publish_flow(agent_id: str, session: SessionDep) -> FlowDraft:
    try:
        return await service.publish(session, agent_id)
    except AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
    except service.NoFlowError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, "this agent has no flow") from error
    except service.FlowHasIssuesError as error:
        detail = [issue.model_dump() for issue in error.issues]
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail) from error


@router.get("/versions")
async def list_versions(agent_id: str, session: SessionDep) -> list[FlowVersionRead]:
    try:
        versions = await service.list_versions(session, agent_id)
    except AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
    return [FlowVersionRead.model_validate(version) for version in versions]
