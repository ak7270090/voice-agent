from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from studio_api.agents import service
from studio_api.agents.browser_calls import build_browser_call
from studio_api.agents.constants import FLOW_CHOICES, PUBLISHED_FLOW
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
from studio_api.flows.schemas import Flow
from studio_api.flows.validation import referenced_secrets
from studio_api.knowledge.service import KnowledgeBaseNotFoundError
from studio_api.secrets.service import SecretsKeyMissingError, secret_values
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


def secrets_not_saved(error: service.SecretsNotSavedError) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY, f"secrets not saved: {error} (Settings, Secrets)"
    )


@router.post("/agents", status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreate, session: SessionDep) -> AgentRead:
    try:
        return AgentRead.model_validate(await service.create_agent(session, body))
    except service.SecretsNotSavedError as error:
        raise secrets_not_saved(error) from error


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
    except KnowledgeBaseNotFoundError as error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"knowledge base {error} not found"
        ) from error
    except service.SecretsNotSavedError as error:
        raise secrets_not_saved(error) from error
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
async def read_runtime_agent_config(
    agent_id: str,
    session: SessionDep,
    settings: SettingsDep,
    flow: Literal[FLOW_CHOICES] = PUBLISHED_FLOW,
) -> RuntimeAgentConfig:
    """Console test calls ask for the draft flow; every other call runs the published one."""
    try:
        agent = await service.get_agent(session, agent_id)
    except service.AgentNotFoundError as error:
        raise agent_not_found(agent_id) from error
    config = RuntimeAgentConfig.model_validate(agent)
    if flow == PUBLISHED_FLOW:
        config.flow = Flow.model_validate(agent.published_flow) if agent.published_flow else None
        config.flow_version = agent.published_flow_version
    if config.flow is not None:
        try:
            config.secrets = await secret_values(session, settings, referenced_secrets(config.flow))
        except SecretsKeyMissingError:
            # Tools that need a secret then fail with "not set" rather than the call failing.
            config.secrets = {}
    return config
