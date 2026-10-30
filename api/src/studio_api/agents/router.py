from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from studio_api.agents import service
from studio_api.agents.browser_calls import build_browser_call
from studio_api.agents.schemas import (
    AgentCreate,
    AgentRead,
    AgentTemplate,
    AgentUpdate,
    BrowserCall,
    FromTemplateRequest,
    RuntimeAgentConfig,
)
from studio_api.agents.templates import build_templates
from studio_api.config import SettingsDep
from studio_api.database import SessionDep
from studio_api.security import RuntimeAuthDep

router = APIRouter(tags=["agents"])
runtime_router = APIRouter(prefix="/runtime", tags=["runtime"], dependencies=[RuntimeAuthDep])


def agent_not_found(agent_id: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"agent {agent_id} not found")


@router.get("/agent-templates")
async def list_templates(settings: SettingsDep) -> list[AgentTemplate]:
    return build_templates(settings)


@router.get("/agents")
async def list_agents(session: SessionDep) -> list[AgentRead]:
    return [AgentRead.model_validate(agent) for agent in await service.list_agents(session)]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreate, session: SessionDep) -> AgentRead:
    return AgentRead.model_validate(await service.create_agent(session, body))


@router.post("/agents/from-template", status_code=status.HTTP_201_CREATED)
async def create_agent_from_template(
    body: FromTemplateRequest, session: SessionDep, settings: SettingsDep
) -> AgentRead:
    try:
        agent = await service.create_agent_from_template(
            session, build_templates(settings), body.template_id, body.name
        )
    except service.TemplateNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"template {error} not found") from error
    return AgentRead.model_validate(agent)


@router.get("/agents/{agent_id}")
async def read_agent(agent_id: str, session: SessionDep) -> AgentRead:
    try:
        return AgentRead.model_validate(await service.get_agent(session, agent_id))
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error


@router.patch("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentUpdate, session: SessionDep) -> AgentRead:
    try:
        return AgentRead.model_validate(await service.update_agent(session, agent_id, body))
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
    except ValidationError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            error.errors(include_url=False, include_context=False, include_input=False),
        ) from error


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str, session: SessionDep) -> None:
    try:
        await service.delete_agent(session, agent_id)
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error


@router.post("/agents/{agent_id}/browser-calls", status_code=status.HTTP_201_CREATED)
async def start_browser_call(
    agent_id: str, session: SessionDep, settings: SettingsDep
) -> BrowserCall:
    try:
        agent = await service.get_agent(session, agent_id)
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
    return build_browser_call(settings, agent.id)


@runtime_router.get("/agents/{agent_id}")
async def read_runtime_agent_config(agent_id: str, session: SessionDep) -> RuntimeAgentConfig:
    try:
        return RuntimeAgentConfig.model_validate(await service.get_agent(session, agent_id))
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
