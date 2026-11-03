from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_backend.agents.models import Agent
from studio_backend.agents.schemas import AgentFields, AgentTemplate, AgentUpdate
from studio_backend.credentials.service import secret_names
from studio_backend.flows.schemas import Flow
from studio_backend.knowledge.models import KnowledgeBase
from studio_backend.knowledge.service import KnowledgeBaseNotFoundError


class AgentNotFoundError(LookupError):
    pass


class TemplateNotFoundError(LookupError):
    pass


class SecretsNotSavedError(LookupError):
    """After-call actions name secrets that are not stored."""


async def check_action_secrets(session: AsyncSession, actions: list[dict]) -> None:
    missing = {action["secret"] for action in actions if action.get("secret")}
    missing -= await secret_names(session)
    if missing:
        raise SecretsNotSavedError(", ".join(sorted(missing)))


async def list_agents(session: AsyncSession) -> list[Agent]:
    result = await session.scalars(select(Agent).order_by(Agent.created_at.desc()))
    return list(result)


async def get_agent(session: AsyncSession, agent_id: str) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise AgentNotFoundError(agent_id)
    return agent


async def create_agent(
    session: AsyncSession,
    fields: AgentFields,
    template: str | None = None,
    flow: Flow | None = None,
) -> Agent:
    await check_action_secrets(session, fields.model_dump()["after_call_actions"])
    agent = Agent(
        **fields.model_dump(),
        template=template,
        flow=flow.model_dump(mode="json") if flow else None,
        # An explicit empty list, so reading it later never needs a lazy load.
        knowledge_bases=[],
    )
    session.add(agent)
    await session.commit()
    return agent


async def create_agent_from_template(
    session: AsyncSession, templates: list[AgentTemplate], template_id: str, name: str | None
) -> Agent:
    template = next((t for t in templates if t.id == template_id), None)
    if template is None:
        raise TemplateNotFoundError(template_id)
    fields = template.fields.model_copy(update={"name": name} if name else {})
    return await create_agent(session, fields, template=template.id, flow=template.flow)


async def update_agent(session: AsyncSession, agent_id: str, changes: AgentUpdate) -> Agent:
    """Applies the changed fields after checking the whole agent is still valid (e.g. a new
    language without voice settings is rejected). Raises pydantic's ValidationError."""
    agent = await get_agent(session, agent_id)
    changed = changes.model_dump(exclude_unset=True)
    knowledge_base_ids = changed.pop("knowledge_base_ids", None)
    current = AgentFields.model_validate(agent, from_attributes=True).model_dump()
    checked = AgentFields.model_validate({**current, **changed}).model_dump()
    if "after_call_actions" in changed:
        await check_action_secrets(session, checked["after_call_actions"])
    for field, value in changed.items():
        setattr(agent, field, checked.get(field, value))
    if knowledge_base_ids is not None:
        agent.knowledge_bases = await _knowledge_bases(session, knowledge_base_ids)
    await session.commit()
    return agent


async def _knowledge_bases(session: AsyncSession, ids: list[str]) -> list[KnowledgeBase]:
    found = list(await session.scalars(select(KnowledgeBase).where(KnowledgeBase.id.in_(ids))))
    missing = set(ids) - {knowledge_base.id for knowledge_base in found}
    if missing:
        raise KnowledgeBaseNotFoundError(", ".join(sorted(missing)))
    return found


async def delete_agent(session: AsyncSession, agent_id: str) -> None:
    await session.delete(await get_agent(session, agent_id))
    await session.commit()
