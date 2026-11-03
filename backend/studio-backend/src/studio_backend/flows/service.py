from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from studio_backend.agents.service import get_agent
from studio_backend.flows.models import FlowVersion
from studio_backend.flows.schemas import Flow, FlowDraft, FlowIssue
from studio_backend.flows.validation import validate_flow
from studio_backend.integrations.credentials.service import secret_names


class FlowHasIssuesError(ValueError):
    def __init__(self, issues: list[FlowIssue]) -> None:
        super().__init__(f"{len(issues)} issues")
        self.issues = issues


class NoFlowError(LookupError):
    pass


def build_draft(
    flow_json: dict | None, published_version: int | None, saved_secrets: set[str] | None = None
) -> FlowDraft:
    if flow_json is None:
        return FlowDraft(flow=None, issues=[], published_version=published_version)
    flow = Flow.model_validate(flow_json)
    issues = validate_flow(flow, saved_secrets)
    return FlowDraft(flow=flow, issues=issues, published_version=published_version)


async def get_draft(session: AsyncSession, agent_id: str) -> FlowDraft:
    agent = await get_agent(session, agent_id)
    return build_draft(agent.flow, agent.published_flow_version, await secret_names(session))


async def save_draft(session: AsyncSession, agent_id: str, flow: Flow | None) -> FlowDraft:
    """Saves even with issues, so a half-built flow is never lost; publishing checks them."""
    agent = await get_agent(session, agent_id)
    agent.flow = flow.model_dump(mode="json") if flow is not None else None
    await session.commit()
    return build_draft(agent.flow, agent.published_flow_version, await secret_names(session))


async def publish(session: AsyncSession, agent_id: str) -> FlowDraft:
    agent = await get_agent(session, agent_id)
    if agent.flow is None:
        raise NoFlowError(agent_id)
    saved_secrets = await secret_names(session)
    draft = build_draft(agent.flow, agent.published_flow_version, saved_secrets)
    if draft.issues:
        raise FlowHasIssuesError(draft.issues)
    version = (agent.published_flow_version or 0) + 1
    session.add(FlowVersion(agent_id=agent.id, version=version, flow=agent.flow))
    agent.published_flow = agent.flow
    agent.published_flow_version = version
    await session.commit()
    return build_draft(agent.flow, version, saved_secrets)


async def list_versions(session: AsyncSession, agent_id: str) -> list[FlowVersion]:
    await get_agent(session, agent_id)
    result = await session.scalars(
        select(FlowVersion)
        .where(FlowVersion.agent_id == agent_id)
        .order_by(FlowVersion.version.desc())
    )
    return list(result)
