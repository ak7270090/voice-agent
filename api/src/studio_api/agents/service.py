from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_api.agents.models import Agent
from studio_api.agents.schemas import AgentFields, AgentTemplate, AgentUpdate


class AgentNotFoundError(LookupError):
    pass


class TemplateNotFoundError(LookupError):
    pass


async def list_agents(session: AsyncSession) -> list[Agent]:
    result = await session.scalars(select(Agent).order_by(Agent.created_at.desc()))
    return list(result)


async def get_agent(session: AsyncSession, agent_id: str) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise AgentNotFoundError(agent_id)
    return agent


async def create_agent(
    session: AsyncSession, fields: AgentFields, template: str | None = None
) -> Agent:
    agent = Agent(**fields.model_dump(), template=template)
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
    return await create_agent(session, fields, template=template.id)


async def update_agent(session: AsyncSession, agent_id: str, changes: AgentUpdate) -> Agent:
    """Applies the changed fields after checking the whole agent is still valid (e.g. a new
    language without voice settings is rejected). Raises pydantic's ValidationError."""
    agent = await get_agent(session, agent_id)
    changed = changes.model_dump(exclude_unset=True)
    current = AgentFields.model_validate(agent, from_attributes=True).model_dump()
    checked = AgentFields.model_validate({**current, **changed}).model_dump()
    for field, value in changed.items():
        setattr(agent, field, checked.get(field, value))
    await session.commit()
    return agent


async def delete_agent(session: AsyncSession, agent_id: str) -> None:
    await session.delete(await get_agent(session, agent_id))
    await session.commit()
